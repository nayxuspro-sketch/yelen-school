"""Encaissements : liste, recherche élève (HTMX), saisie, reçus, remboursements.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection, transaction
from django.db.models import Sum, Count, Q, OuterRef, Subquery
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import io
from ..models import Paiement, Echeancier, ModePaiement, Remboursement
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, TarifScolarite, RubriquePaiement
from core.utils import get_etablissement_context
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES, FINANCE_APPROVER_ROLES
from ..selectors import (
    RESULTATS_RECHERCHE_MAX,
    annee_de_reference,
    inscription_payable_ou_none,
    rechercher_inscriptions_payables,
    terme_recherche_valide,
)
from .commun import (
    WeasyHTML,
    _require_finance_role,
    _require_same_establishment,
    _calcul_situation_financiere,
    _payment_overage_errors,
)


@login_required
def paiement_list(request):
    """Tableau de bord financier : dernière transaction par élève."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    from django.core.cache import cache

    etab = request.user.etablissement
    is_htmx = bool(request.headers.get('HX-Request'))

    # annee_courante : rarement modifiée — cache 5 min par établissement
    cache_key = f'annee_courante_{etab.pk}' if etab else 'annee_courante_none'
    annee_courante = cache.get(cache_key)
    if annee_courante is None:
        annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first() if etab else None
        cache.set(cache_key, annee_courante, 300)

    query = request.GET.get('q', '').strip()

    # Dernière transaction par inscription — requête portable (PostgreSQL + SQLite).
    # Remplace l'ancien `.distinct('inscription_id')` (DISTINCT ON, PostgreSQL uniquement)
    # par une sous-requête corrélée : on ne garde que le paiement le plus récent
    # (date_paiement, puis created_at) de chaque inscription.
    dernier_paiement = (
        Paiement.objects
        .filter(inscription=OuterRef('inscription'))
        .order_by('-date_paiement', '-created_at')
        .values('pk')[:1]
    )
    qs = (
        Paiement.objects
        .filter(inscription__annee_scolaire=annee_courante)
        .filter(pk=Subquery(dernier_paiement))
        .select_related('inscription__eleve', 'inscription__classe', 'rubrique')
        .order_by('-date_paiement', '-created_at')
    )

    if query:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=query) |
            Q(inscription__eleve__prenom__icontains=query) |
            Q(inscription__eleve__matricule__icontains=query) |
            Q(inscription__classe__nom__icontains=query)
        )

    # Stats globales : une seule requête agrégée, ignorée pour HTMX (partiel ne les affiche pas)
    total_encaisse = 0
    nb_transactions = 0
    if not is_htmx and annee_courante:
        stats = (
            Paiement.objects
            .filter(inscription__annee_scolaire=annee_courante)
            .aggregate(total=Sum('montant'), nb=Count('id'))
        )
        total_encaisse = stats['total'] or 0
        nb_transactions = stats['nb'] or 0

    # Pagination (50 élèves par page) : sans elle, la page pesait 5,4 Mo de HTML
    # pour 2 500 élèves et mettait ~1 s à se générer à chaque recherche.
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'paiements': page_obj.object_list,
        'page_obj': page_obj,
        'total_encaisse': total_encaisse,
        'nb_transactions': nb_transactions,
        'annee_courante': annee_courante,
        'query': query,
    }

    if is_htmx:
        return render(request, 'finances/partials/paiement_table.html', context)

    return render(request, 'finances/paiement_list.html', context)


@login_required
def paiement_recherche_eleve(request):
    """
    Fragment HTMX du formulaire d'encaissement : élèves correspondant à la
    recherche (20 au plus). Remplace l'ancien <select> qui embarquait toutes
    les inscriptions de l'année (≈ 600 Ko de HTML pour 2 500 élèves).
    """
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = request.user.etablissement
    terme = request.GET.get('q', '').strip()
    annee = annee_de_reference(etab)
    resultats = list(rechercher_inscriptions_payables(etab, annee, terme))
    return render(request, 'finances/partials/paiement_recherche_eleve.html', {
        'terme': terme,
        'resultats': resultats,
        'trop_court': not terme_recherche_valide(terme),
        'limite': RESULTATS_RECHERCHE_MAX,
        'tronque': len(resultats) >= RESULTATS_RECHERCHE_MAX,
    })


@login_required
def paiement_create(request):
    """Enregistrement d'un paiement multi-rubriques."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = request.user.etablissement
    annee_courante = annee_de_reference(etab)

    # L'élève est choisi via la recherche serveur (paiement_recherche_eleve) ;
    # seule l'inscription retenue est renvoyée au gabarit.
    inscription_selectionnee = inscription_payable_ou_none(
        etab, annee_courante, (request.POST.get('inscription') or request.GET.get('inscription') or '').strip()
    )

    if request.method == 'POST':
        inscription_id = request.POST.get('inscription', '').strip()
        date_paiement  = request.POST.get('date_paiement', '').strip() or None
        mode_paiement  = request.POST.get('mode_paiement', '').strip()
        reference      = request.POST.get('reference', '').strip()
        observation    = request.POST.get('observation', '').strip()
        rubrique_ids   = request.POST.getlist('rubrique_ids[]')
        montants_raw   = request.POST.getlist('montants[]')
        echeances_raw  = request.POST.getlist('echeances[]')

        errors = []
        if date_paiement:
            from datetime import date as _date
            try:
                date_paiement = _date.fromisoformat(date_paiement)
            except ValueError:
                errors.append("La date de paiement est invalide.")
                date_paiement = None

        # Inscription
        inscription = None
        if not inscription_id:
            errors.append("L'inscription est obligatoire.")
        else:
            try:
                inscription = Inscription.objects.select_related('classe', 'annee_scolaire', 'statut_eleve').get(pk=inscription_id)
                if (
                    request.user.etablissement_id is not None
                    and inscription.classe.etablissement_id != request.user.etablissement_id
                ):
                    errors.append("Cette inscription appartient à un autre établissement.")
            except (Inscription.DoesNotExist, ValueError, ValidationError):
                errors.append("Inscription introuvable.")

        # Mode de paiement
        valid_modes = {m[0] for m in ModePaiement.choices}
        if not mode_paiement or mode_paiement not in valid_modes:
            errors.append("Le mode de paiement est obligatoire.")

        # Référence obligatoire si ≠ Espèces et bornée par le modèle.
        if mode_paiement and mode_paiement != ModePaiement.ESPECES and not reference:
            errors.append("La référence de transaction est obligatoire pour ce mode de paiement.")
        if len(reference) > 100:
            errors.append("La référence de transaction ne peut pas dépasser 100 caractères.")

        # Lignes rubriques
        lignes = []
        for i, (rid, m_raw) in enumerate(zip(rubrique_ids, montants_raw)):
            if not rid or not m_raw:
                continue
            try:
                montant = Decimal(str(m_raw).replace(',', '.'))
            except InvalidOperation:
                errors.append(f"Montant invalide pour la rubrique #{i + 1}.")
                continue

            if not montant.is_finite() or montant <= 0:
                errors.append(f"Le montant doit être strictement positif (rubrique #{i + 1}).")
                continue

            try:
                rubrique_qs = RubriquePaiement.objects.filter(pk=rid)
                if inscription is not None:
                    rubrique_qs = rubrique_qs.filter(etablissement=inscription.classe.etablissement)
                rubrique = rubrique_qs.get()
            except (RubriquePaiement.DoesNotExist, ValueError, ValidationError):
                errors.append(f"Rubrique #{rid} introuvable ou hors établissement.")
                continue

            echeance_raw = echeances_raw[i].strip() if i < len(echeances_raw) else ''
            echeance = None
            if echeance_raw:
                from datetime import date as _date
                try:
                    echeance = _date.fromisoformat(echeance_raw)
                except ValueError:
                    errors.append(f"Échéance invalide pour la rubrique #{i + 1}.")
                    continue
            lignes.append((rubrique, montant, echeance))

        if not lignes:
            errors.append("Veuillez renseigner au moins une rubrique avec un montant valide.")

        # Le contrôle est répété sous verrou de ligne : deux encaissements
        # concurrents ne peuvent pas dépasser le tarif restant.
        if not errors and inscription:
            try:
                with transaction.atomic():
                    locked_inscription = (
                        Inscription.objects.select_for_update(of=('self',))
                        .select_related('classe', 'annee_scolaire', 'statut_eleve', 'eleve')
                        .get(pk=inscription.pk)
                    )
                    errors.extend(_payment_overage_errors(locked_inscription, lignes))
                    if errors:
                        raise ValueError('payment_validation_failed')
                    inscription = locked_inscription
                    paiement_ids = []
                    for rubriq, montant, echeance in lignes:
                        paiement = Paiement(
                            inscription=inscription,
                            rubrique=rubriq,
                            montant=montant,
                            date_paiement=date_paiement or timezone.now().date(),
                            mode_paiement=mode_paiement,
                            reference=reference,
                            echeance=echeance,
                            observation=observation,
                            encaisse_par=request.user,
                            statut_eleve=inscription.statut_eleve,
                        )
                        paiement._audit_reason = 'Encaissement saisi depuis le module financier'
                        paiement.save()
                        paiement_ids.append(paiement.pk)
            except ValueError:
                paiement_ids = []
            else:
                total = sum(m for _, m, _e in lignes)
                request.session['paiement_ids'] = [str(pk) for pk in paiement_ids]
                request.session['paiement_inscription_id'] = str(inscription.pk)
                messages.success(
                    request,
                    f"{len(lignes)} paiement(s) enregistré(s) pour {inscription.eleve} — Total : {total:,.0f} FCFA"
                )
                return redirect('finances:paiement_confirmation')

        # Re-render avec erreurs — données soumises pour repopulation JS
        submitted_lines = [
            {'id': rid, 'montant': m_raw, 'echeance': echeances_raw[i] if i < len(echeances_raw) else ''}
            for i, (rid, m_raw) in enumerate(zip(rubrique_ids, montants_raw))
            if rid
        ]
        return render(request, 'finances/paiement_form.html', {
            'title': "Encaisser un paiement",
            'inscription_selectionnee': inscription_selectionnee,
            'mode_choices': ModePaiement.choices,
            'errors': errors,
            'post_data': request.POST,
            'submitted_lines': submitted_lines,
        })

    # GET
    inscription_id = request.GET.get('inscription')
    return render(request, 'finances/paiement_form.html', {
        'title': "Encaisser un paiement",
        'inscription_selectionnee': inscription_selectionnee,
        'mode_choices': ModePaiement.choices,
        'selected_inscription_id': inscription_id,
        'submitted_lines': [],
    })


@login_required
def situation_eleve(request, inscription_id):
    """Vue détaillée de la situation financière d'un élève."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    _require_same_establishment(request, inscription)
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('finances:paiement_list')

    sit = _calcul_situation_financiere(inscription)

    echeancier_list = Echeancier.objects.filter(
        inscription=inscription, is_active=True
    ).order_by('date_limite')
    echeancier_total = echeancier_list.aggregate(s=Sum('montant_du'))['s'] or Decimal('0')
    echeancier_paye = echeancier_list.filter(paye=True).aggregate(s=Sum('montant_du'))['s'] or Decimal('0')

    total_du = sit['total_du']
    total_paye = sit['total_paye']
    total_rembourse = sit['total_rembourse']
    pourcentage_paye = int(min(total_paye / total_du * 100, 100)) if total_du > 0 else 0

    # Remboursements liés à cette inscription (pour affichage dans la page)
    remboursements = (
        Remboursement.objects
        .filter(paiement__inscription=inscription, is_active=True)
        .select_related('paiement__rubrique', 'rembourse_par')
        .order_by('-date_remboursement')
    )

    from datetime import date as _date
    from ..models import HistoriqueRelance
    relances_eleve = (
        HistoriqueRelance.objects
        .filter(inscription=inscription)
        .select_related('rubrique', 'envoye_par')
        .order_by('-date_relance', '-created_at')
    )

    return render(request, 'finances/situation_eleve.html', {
        'inscription': inscription,
        'paiements': sit['paiements'],
        'total_paye': total_paye,
        'total_du': total_du,
        'total_rembourse': total_rembourse,
        'reste_a_payer': sit['reste_a_payer'],
        'frais_details': sit['frais_details'],
        'use_tarifs': sit['use_tarifs'],
        'pourcentage_paye': pourcentage_paye,
        'today': _date.today().isoformat(),
        'echeancier_list': echeancier_list,
        'echeancier_total': echeancier_total,
        'echeancier_paye': echeancier_paye,
        'echeancier_restant': echeancier_total - echeancier_paye,
        'remboursements': remboursements,
        'relances_eleve': relances_eleve,
        'bourses': sit.get('bourses', []),
    })


@login_required
def remboursement_create(request, paiement_id):
    """Enregistrer un remboursement (total ou partiel) pour un paiement."""
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    paiement = get_object_or_404(
        Paiement.objects.select_related('inscription__eleve', 'rubrique'),
        pk=paiement_id,
    )
    inscription = paiement.inscription
    _require_same_establishment(request, inscription)

    # Montant déjà remboursé pour ce paiement
    deja_rembourse = (
        Remboursement.objects.filter(paiement=paiement, is_active=True)
        .aggregate(s=Sum('montant'))['s'] or Decimal('0')
    )
    remboursable = paiement.montant - deja_rembourse

    if remboursable <= 0:
        messages.error(request, "Ce paiement a déjà été intégralement remboursé.")
        return redirect('finances:situation_eleve', inscription_id=inscription.pk)

    if request.method == 'POST':
        montant_raw = request.POST.get('montant', '').strip().replace(',', '.')
        motif = request.POST.get('motif', '').strip()
        date_raw = request.POST.get('date_remboursement', '').strip()

        errors = []
        if not motif:
            errors.append("Le motif du remboursement est obligatoire.")
        montant = None
        try:
            montant = Decimal(montant_raw)
            if not montant.is_finite() or montant <= 0:
                errors.append("Le montant doit être supérieur à 0.")
            elif montant > remboursable:
                errors.append(
                    f"Le montant remboursable est au maximum {remboursable:,.0f} FCFA "
                    f"(paiement {paiement.montant:,.0f} FCFA − déjà remboursé {deja_rembourse:,.0f} FCFA)."
                )
        except (InvalidOperation, ValueError):
            errors.append("Montant invalide.")

        from datetime import date as _date
        date_remb = None
        if date_raw:
            try:
                date_remb = _date.fromisoformat(date_raw)
            except ValueError:
                errors.append("La date de remboursement est invalide.")
        else:
            date_remb = _date.today()

        if not errors:
            with transaction.atomic():
                locked_paiement = Paiement.objects.select_for_update().get(pk=paiement.pk)
                locked_deja_rembourse = (
                    Remboursement.objects.filter(
                        paiement=locked_paiement, is_active=True
                    ).aggregate(s=Sum('montant'))['s'] or Decimal('0')
                )
                locked_remboursable = locked_paiement.montant - locked_deja_rembourse
                if montant > locked_remboursable:
                    errors.append(
                        f"Le montant remboursable est désormais limité à "
                        f"{max(locked_remboursable, Decimal('0')):,.0f} FCFA."
                    )
                else:
                    remboursement = Remboursement(
                        paiement=locked_paiement,
                        montant=montant,
                        motif=motif,
                        date_remboursement=date_remb,
                        rembourse_par=request.user,
                    )
                    remboursement._audit_reason = motif or 'Remboursement financier'
                    remboursement.save()
            if not errors:
                messages.success(
                    request,
                    f"Remboursement de {montant:,.0f} FCFA enregistré pour "
                    f"{inscription.eleve.get_nom_complet()}."
                )
                return redirect('finances:situation_eleve', inscription_id=inscription.pk)

        return render(request, 'finances/remboursement_form.html', {
            'paiement': paiement,
            'inscription': inscription,
            'remboursable': remboursable,
            'deja_rembourse': deja_rembourse,
            'errors': errors,
            'post_data': request.POST,
        })

    from datetime import date as _date
    return render(request, 'finances/remboursement_form.html', {
        'paiement': paiement,
        'inscription': inscription,
        'remboursable': remboursable,
        'deja_rembourse': deja_rembourse,
        'errors': [],
        'post_data': {},
    })


@login_required
def remboursement_delete(request, remboursement_id):
    """Annuler un remboursement par désactivation, sans effacer l'historique."""
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    remb = get_object_or_404(
        Remboursement.objects.select_related('paiement__inscription'),
        pk=remboursement_id,
    )
    inscription_id = remb.paiement.inscription.pk
    _require_same_establishment(request, remb.paiement.inscription)
    if request.method == 'POST':
        reason = request.POST.get('motif', '').strip()
        if not reason:
            messages.error(request, "Le motif d'annulation est obligatoire.")
            return redirect('finances:situation_eleve', inscription_id=inscription_id)
        with transaction.atomic():
            remb = (
                Remboursement.objects.select_for_update()
                .select_related('paiement__inscription')
                .get(pk=remb.pk)
            )
            if not remb.is_active:
                messages.error(request, "Ce remboursement est déjà annulé.")
                return redirect('finances:situation_eleve', inscription_id=inscription_id)
            _require_same_establishment(request, remb.paiement.inscription)
            # Le trigger PostgreSQL refuse toute désactivation non justifiée,
            # y compris une mise à jour SQL hors du code métier.
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('yelen.refund_cancel_reason', %s, true)",
                        [reason],
                    )
            remb._audit_reason = reason
            remb.is_active = False
            remb.updated_by = request.user
            remb.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, "Remboursement annulé et conservé dans l'historique.")
    return redirect('finances:situation_eleve', inscription_id=inscription_id)


@login_required
def api_rubriques_inscription(request, inscription_id):
    """
    Retourne en JSON les rubriques disponibles et leur montant
    pour une inscription donnée (classe × statut × année scolaire).
    Utilisé par le formulaire de paiement pour le remplissage automatique.
    """
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    _require_same_establishment(request, inscription)
    etab = getattr(request.user, 'etablissement', None)
    if etab and inscription.classe.etablissement_id != etab.pk:
        from django.http import JsonResponse as _JsonResponse
        return _JsonResponse({'erreur': 'Accès refusé.'}, status=403)
    etablissement = inscription.classe.etablissement

    # Total versé par rubrique
    totaux = (
        Paiement.objects
        .filter(inscription=inscription)
        .values('rubrique_id')
        .annotate(total=Sum('montant'))
    )
    totaux_map = {str(t['rubrique_id']): t['total'] for t in totaux}

    # Total remboursé par rubrique (pour calcul du reste réel)
    totaux_rembourses = (
        Remboursement.objects
        .filter(paiement__inscription=inscription, is_active=True)
        .values('paiement__rubrique_id')
        .annotate(total=Sum('montant'))
    )
    rembourses_map = {str(t['paiement__rubrique_id']): t['total'] for t in totaux_rembourses}

    # Données élève incluses dans toutes les réponses (succès ou erreur)
    eleve_data = {
        'nom':      inscription.eleve.nom,
        'prenom':   inscription.eleve.prenom,
        'matricule': inscription.eleve.matricule,
        'classe':   inscription.classe.nom,
    }

    # ── Vérification : le code paiement (statut_eleve) doit être renseigné ──────
    if not inscription.statut_eleve_id:
        return JsonResponse({
            'rubriques': [],
            'eleve': eleve_data,
            'situation': {'total_du': '0', 'total_paye': '0', 'reste': '0'},
            'statut_eleve': {'nom': None, 'code': None, 'couleur': None},
            'error': (
                "Aucun code paiement (statut élève) n'est configuré pour cette inscription. "
                "Veuillez modifier l'inscription et sélectionner un statut élève."
            ),
        })

    # ── Tarifs filtrés par niveau × année × statut_eleve ────────────────────────
    # Le tarif est défini au niveau (ex: 5ème), pas à la classe individuelle.
    tarifs_qs = TarifScolarite.objects.filter(
        etablissement=etablissement,
        classe__niveau=inscription.classe.niveau,
        annee_scolaire=inscription.annee_scolaire,
        statut_eleve=inscription.statut_eleve,
        actif=True,
        rubrique__actif=True,
    ).select_related('rubrique').order_by('rubrique__ordre', 'rubrique__nom')

    if not tarifs_qs.exists():
        statut = inscription.statut_eleve
        sit = _calcul_situation_financiere(inscription)
        return JsonResponse({
            'rubriques': [],
            'eleve': eleve_data,
            'situation': {
                'total_du':   str(sit['total_du']),
                'total_paye': str(sit['total_paye']),
                'reste':      str(sit['reste_a_payer']),
            },
            'statut_eleve': {
                'nom':    statut.nom,
                'code':   statut.code,
                'couleur': statut.couleur,
            },
            'error': (
                f"Aucun tarif configuré pour le niveau « {inscription.classe.niveau} » "
                f"avec le statut « {statut.nom} ». "
                "Veuillez configurer les tarifs dans les paramètres."
            ),
        })

    # Dédoublonner par rubrique (sécurité)
    seen = set()
    rubriques_data = []
    for t in tarifs_qs:
        rid = str(t.rubrique.pk)
        if rid not in seen:
            seen.add(rid)
            rubriques_data.append((rid, t.rubrique.nom, t.rubrique.code, t.montant))

    rubriques = []
    for rid, nom, code, montant in rubriques_data:
        verse      = Decimal(str(totaux_map.get(rid) or 0))
        rembourse  = Decimal(str(rembourses_map.get(rid) or 0))
        reste      = max(montant - verse + rembourse, Decimal('0'))
        rubriques.append({
            'id':           rid,
            'nom':          nom,
            'code':         code,
            'montant':      str(montant),
            'total_verse':  str(verse),
            'reste':        str(reste),
        })

    # Situation financière globale de l'inscription
    sit = _calcul_situation_financiere(inscription)

    statut = inscription.statut_eleve
    return JsonResponse({
        'rubriques': rubriques,
        'eleve': {
            'nom':      inscription.eleve.nom,
            'prenom':   inscription.eleve.prenom,
            'matricule': inscription.eleve.matricule,
            'classe':   inscription.classe.nom,
        },
        'situation': {
            'total_du':   str(sit['total_du']),
            'total_paye': str(sit['total_paye']),
            'reste':      str(sit['reste_a_payer']),
        },
        'statut_eleve': {
            'nom':    statut.nom if statut else None,
            'code':   statut.code if statut else None,
            'couleur': statut.couleur if statut else None,
        },
    })


@login_required
def recu_pdf(request, paiement_id):
    """Génère le reçu de paiement en PDF via WeasyPrint.
    Regroupe toutes les rubriques payées de l'inscription dans un tableau."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:paiement_list')
    paiement = get_object_or_404(Paiement, pk=paiement_id)
    inscription = paiement.inscription
    _require_same_establishment(request, inscription)
    etablissement = inscription.classe.etablissement
    etab = getattr(request.user, 'etablissement', None)
    if etab and etablissement.pk != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('finances:paiement_list')

    etab_context = get_etablissement_context(etablissement, request)

    # Tous les paiements de l'inscription
    tous_paiements = list(
        Paiement.objects.filter(inscription=inscription).select_related('rubrique')
    )
    total_paye = sum((Decimal(str(p.montant)) for p in tous_paiements), Decimal('0'))

    # Grouper par rubrique_id → {rid_str: Decimal}
    verse_par_rubrique: dict[str, Decimal] = {}
    rubrique_obj: dict[str, RubriquePaiement] = {}
    verse_sans_rubrique = Decimal('0')

    for p in tous_paiements:
        m = Decimal(str(p.montant))
        if p.rubrique_id is None:
            verse_sans_rubrique = verse_sans_rubrique + m
        else:
            rid_str = str(p.rubrique_id)
            prev_str = str(verse_par_rubrique.get(rid_str) or '0')
            verse_par_rubrique[rid_str] = Decimal(prev_str) + m
            if rid_str not in rubrique_obj and p.rubrique is not None:
                rubrique_obj[rid_str] = p.rubrique

    # Tarifs configurés pour déterminer le montant dû par rubrique.
    # On utilise le statut_eleve figé sur le paiement (snapshot au moment du versement).
    # Si plusieurs paiements ont des statuts différents, on prend le premier disponible.
    statut_pour_tarif = paiement.statut_eleve
    if statut_pour_tarif is None:
        # Fallback : statut actuel de l'inscription (paiements antérieurs à la migration)
        statut_pour_tarif = inscription.statut_eleve

    # Tous les tarifs configurés pour niveau × statut × année (pas uniquement les rubriques payées)
    tarifs_qs = TarifScolarite.objects.filter(
        etablissement=etablissement,
        classe__niveau=inscription.classe.niveau,
        annee_scolaire=inscription.annee_scolaire,
        actif=True,
    ).select_related('rubrique').order_by('rubrique__ordre', 'rubrique__nom')
    if statut_pour_tarif:
        tarifs_qs = tarifs_qs.filter(statut_eleve=statut_pour_tarif)

    # Dédoublonner par rubrique (plusieurs classes au même niveau)
    seen_rids: set = set()
    tarif_map: dict[str, Decimal] = {}
    tarif_rubriques: dict[str, RubriquePaiement] = {}
    for t in tarifs_qs:
        rid_str = str(t.rubrique_id)
        if rid_str not in seen_rids:
            seen_rids.add(rid_str)
            tarif_map[rid_str] = t.montant
            tarif_rubriques[rid_str] = t.rubrique

    # Si aucun tarif configuré → fallback sur les rubriques payées seules
    if not tarif_map:
        for rid_str, rubrique in rubrique_obj.items():
            tarif_rubriques[rid_str] = rubrique

    # Construction du tableau : toutes les rubriques tarifées + celles payées sans tarif
    all_rids = list(dict.fromkeys(list(tarif_rubriques.keys()) + list(rubrique_obj.keys())))
    lignes_rubriques = []
    total_du = Decimal('0')
    for rid_str in all_rids:
        rubrique = tarif_rubriques.get(rid_str) or rubrique_obj.get(rid_str)
        verse: Decimal = verse_par_rubrique.get(rid_str, Decimal('0'))
        du: Decimal = tarif_map.get(rid_str, Decimal('0'))
        reste: Decimal = max(du - verse, Decimal('0'))
        total_du += du
        lignes_rubriques.append({
            'rubrique': rubrique,
            'montant_du': du,
            'verse': verse,
            'reste': reste,
        })
    if verse_sans_rubrique:
        lignes_rubriques.append({
            'rubrique': None,
            'montant_du': Decimal('0'),
            'verse': verse_sans_rubrique,
            'reste': Decimal('0'),
        })

    reste_total: Decimal = max(total_du - total_paye, Decimal('0'))
    
    html_string = render_to_string('finances/pdf/recu_paiement.html', {
        'paiement': paiement,
        'inscription': inscription,
        'etablissement': etablissement,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'lignes_rubriques': lignes_rubriques,
        'total_paye': total_paye,
        'total_du': total_du,
        'reste_total': reste_total,
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Recu_{inscription.eleve.nom}_{paiement.id.hex[:8]}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def historique_pdf(request, inscription_id):
    """Génère l'historique de versements en PDF via WeasyPrint."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:paiement_list')
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    _require_same_establishment(request, inscription)
    etablissement = inscription.classe.etablissement
    etab = getattr(request.user, 'etablissement', None)
    if etab and etablissement.pk != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('finances:paiement_list')

    etab_context = get_etablissement_context(etablissement, request)
    sit = _calcul_situation_financiere(inscription)

    html_string = render_to_string('finances/pdf/historique_versements.html', {
        'inscription': inscription,
        'etablissement': etablissement,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'paiements': sit['paiements'],
        'total_paye': sit['total_paye'],
        'total_du': sit['total_du'],
        'reste_a_payer': sit['reste_a_payer'],
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Historique_{inscription.eleve.nom}_{inscription.id.hex[:8]}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def paiement_confirmation(request):
    """Page de confirmation après un paiement avec option d'impression du reçu."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    paiement_ids = request.session.get('paiement_ids', [])
    inscription_id = request.session.get('paiement_inscription_id')
    
    if not paiement_ids or not inscription_id:
        messages.error(request, "Aucune donnée de paiement trouvée.")
        return redirect('finances:paiement_list')
    
    try:
        inscription = Inscription.objects.get(pk=inscription_id)
    except (Inscription.DoesNotExist, ValueError):
        messages.error(request, "Inscription introuvable.")
        return redirect('finances:paiement_list')
    
    _require_same_establishment(request, inscription)
    try:
        paiements = Paiement.objects.filter(
            pk__in=paiement_ids,
            inscription=inscription,
        ).select_related('inscription__eleve', 'rubrique', 'encaisse_par')
    except (ValueError, ValidationError):
        paiements = Paiement.objects.none()
    if not paiements.exists():
        messages.error(request, "Aucun paiement correspondant à cette inscription.")
        return redirect('finances:paiement_list')
    etab = inscription.classe.etablissement

    etab_context = get_etablissement_context(etab, request)
    
    return render(request, 'finances/paiement_confirmation.html', {
        'paiements': paiements,
        'inscription': inscription,
        'total': sum(p.montant for p in paiements),
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
    })
