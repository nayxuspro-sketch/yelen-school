from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import csv
import io
import json
try:
    from weasyprint import HTML as WeasyHTML
except ImportError:
    WeasyHTML = None
from .models import FraisScolarite, Paiement, Echeancier, ModePaiement, Remboursement, BourseEleve, TypeBourse, TypeReduction
from .forms import FraisScolariteForm, EcheancierForm
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe, TarifScolarite, RubriquePaiement
from core.utils import get_etablissement_context
import re as _re


def _numero_valide(numero):
    """Vérifie qu'un numéro ressemble à un numéro mobile valide (BF ou international)."""
    n = _re.sub(r'[\s\-\.]', '', numero or '')
    # +226XXXXXXXX ou 00226XXXXXXXX ou 8 chiffres commençant par 0,5,6,7
    return bool(_re.fullmatch(r'(\+226|00226)?\d{8}', n) and
                _re.search(r'\d{8}$', n))


def _calcul_situation_financiere(inscription):
    """
    Calcule Total DÛ, Total payé, Reste à payer pour une inscription.

    - Total DÛ  : somme des tarifs actifs niveau × statut_eleve × annee,
                  dédoublonnés par rubrique. 0 si statut_eleve non configuré.
                  Les bourses/aides actives sont déduites du total dû.
    - Total payé: somme de tous les paiements enregistrés pour l'inscription.
    - Reste     : Total DÛ net – Total payé (jamais négatif pour le reste affiché).
    """
    etablissement = inscription.classe.etablissement
    paiements = Paiement.objects.filter(inscription=inscription).select_related('rubrique')
    total_verse = paiements.aggregate(s=Sum('montant'))['s'] or Decimal('0')
    total_rembourse = (
        Remboursement.objects
        .filter(paiement__inscription=inscription)
        .aggregate(s=Sum('montant'))['s'] or Decimal('0')
    )
    total_paye = total_verse - total_rembourse

    # Bourses actives pour cette inscription
    bourses = BourseEleve.objects.filter(
        inscription=inscription, actif=True,
    ).select_related('type_bourse', 'rubrique')

    # Sans statut_eleve, impossible de déterminer les frais — total_du = 0
    if not inscription.statut_eleve_id:
        total_reduction = bourses.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')
        return {
            'total_du': Decimal('0'),
            'total_paye': total_paye,
            'total_rembourse': total_rembourse,
            'total_reduction': total_reduction,
            'reste_a_payer': Decimal('0'),
            'frais_details': [],
            'use_tarifs': False,
            'paiements': paiements,
            'bourses': bourses,
        }

    tarifs_qs = TarifScolarite.objects.filter(
        etablissement=etablissement,
        classe__niveau=inscription.classe.niveau,
        annee_scolaire=inscription.annee_scolaire,
        statut_eleve=inscription.statut_eleve,
        actif=True,
    ).select_related('rubrique').order_by('rubrique__ordre', 'rubrique__nom')

    # Dédoublonner par rubrique (plusieurs classes peuvent partager le même niveau)
    seen = set()
    frais_details = []
    total_du = Decimal('0')
    for t in tarifs_qs:
        if t.rubrique_id not in seen:
            seen.add(t.rubrique_id)
            frais_details.append(t)
            total_du += t.montant

    # Déduire les bourses/aides scolaires
    total_reduction = bourses.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')
    total_du_net = max(total_du - total_reduction, Decimal('0'))

    reste_a_payer = max(total_du_net - total_paye, Decimal('0'))

    return {
        'total_du': total_du_net,
        'total_du_brut': total_du,
        'total_paye': total_paye,
        'total_rembourse': total_rembourse,
        'total_reduction': total_reduction,
        'reste_a_payer': reste_a_payer,
        'frais_details': frais_details,
        'use_tarifs': bool(frais_details),
        'paiements': paiements,
        'bourses': bourses,
    }


@login_required
def paiement_list(request):
    """Tableau de bord financier : dernière transaction par élève."""
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

    # Dernière transaction par inscription (DISTINCT ON PostgreSQL)
    qs = (
        Paiement.objects
        .filter(inscription__annee_scolaire=annee_courante)
        .select_related('inscription__eleve', 'inscription__classe', 'rubrique')
        .order_by('inscription_id', '-date_paiement', '-created_at')
        .distinct('inscription_id')
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

    context = {
        'paiements': qs,
        'total_encaisse': total_encaisse,
        'nb_transactions': nb_transactions,
        'annee_courante': annee_courante,
        'query': query,
    }

    if is_htmx:
        return render(request, 'finances/partials/paiement_table.html', context)

    return render(request, 'finances/paiement_list.html', context)

@login_required
def paiement_create(request):
    """Enregistrement d'un paiement multi-rubriques."""
    etab = request.user.etablissement
    annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first() if etab else None
    inscriptions = (
        Inscription.objects
        .select_related('eleve', 'classe', 'annee_scolaire', 'statut_eleve')
        .filter(annee_scolaire=annee_courante, classe__etablissement=etab)
        .exclude(est_exonere=True)
        .exclude(statut='ABANDON')
        .order_by('eleve__nom', 'eleve__prenom')
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

        # Inscription
        inscription = None
        if not inscription_id:
            errors.append("L'inscription est obligatoire.")
        else:
            try:
                inscription = Inscription.objects.get(pk=inscription_id)
            except Inscription.DoesNotExist:
                errors.append("Inscription introuvable.")

        # Mode de paiement
        valid_modes = {m[0] for m in ModePaiement.choices}
        if not mode_paiement or mode_paiement not in valid_modes:
            errors.append("Le mode de paiement est obligatoire.")

        # Référence obligatoire si ≠ Espèces
        if mode_paiement and mode_paiement != ModePaiement.ESPECES and not reference:
            errors.append("La référence de transaction est obligatoire pour ce mode de paiement.")

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

            if montant < 0:
                errors.append(f"Le montant ne peut pas être négatif (rubrique #{i + 1}).")
                continue
            if montant == 0:
                errors.append(f"Le montant ne peut pas être nul (rubrique #{i + 1}).")
                continue

            try:
                rubrique = RubriquePaiement.objects.get(pk=rid)
            except RubriquePaiement.DoesNotExist:
                errors.append(f"Rubrique #{rid} introuvable.")
                continue

            echeance = echeances_raw[i] if i < len(echeances_raw) else None
            lignes.append((rubrique, montant, echeance or None))

        if not lignes:
            errors.append("Veuillez renseigner au moins une rubrique avec un montant valide.")

        # Vérifier que le montant versé ne dépasse pas le reste à payer par rubrique
        if not errors and inscription:
            etablissement = inscription.classe.etablissement
            for rubrique, montant, _echeance in lignes:
                deja_verse = (
                    Paiement.objects.filter(inscription=inscription, rubrique=rubrique)
                    .aggregate(Sum('montant'))['montant__sum'] or Decimal('0')
                )
                tarif_qs = TarifScolarite.objects.filter(
                    etablissement=etablissement,
                    classe__niveau=inscription.classe.niveau,
                    annee_scolaire=inscription.annee_scolaire,
                    actif=True,
                    rubrique=rubrique,
                )
                if inscription.statut_eleve_id:
                    tarif_qs = tarif_qs.filter(statut_eleve=inscription.statut_eleve)
                tarif = tarif_qs.first()
                if tarif:
                    reste = Decimal(str(tarif.montant)) - deja_verse
                    if montant > reste:
                        errors.append(
                            f"« {rubrique.nom} » : montant versé {montant:,.0f} FCFA "
                            f"dépasse le reste à payer {max(reste, Decimal('0')):,.0f} FCFA."
                        )

        if not errors and inscription:
            paiement_ids = []
            for rubriq, montant, echeance in lignes:
                paiement = Paiement.objects.create(
                    inscription=inscription,
                    rubrique=rubriq,
                    montant=montant,
                    date_paiement=date_paiement or date.today(),
                    mode_paiement=mode_paiement,
                    reference=reference,
                    echeance=echeance,
                    observation=observation,
                    encaisse_par=request.user,
                    statut_eleve=inscription.statut_eleve,
                )
                paiement_ids.append(paiement.pk)
            
            total = sum(m for _, m, _e in lignes)
            request.session['paiement_ids'] = [str(pk) for pk in paiement_ids]
            request.session['paiement_inscription_id'] = str(inscription.pk)
            messages.success(
                request,
                f"{len(lignes)} paiement(s) enregistré(s) pour {inscription.eleve} — Total : {total:,.0f} FCAF"
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
            'inscriptions': inscriptions,
            'mode_choices': ModePaiement.choices,
            'errors': errors,
            'post_data': request.POST,
            'submitted_lines': submitted_lines,
        })

    # GET
    inscription_id = request.GET.get('inscription')
    return render(request, 'finances/paiement_form.html', {
        'title': "Encaisser un paiement",
        'inscriptions': inscriptions,
        'mode_choices': ModePaiement.choices,
        'selected_inscription_id': inscription_id,
        'submitted_lines': [],
    })

@login_required
def situation_eleve(request, inscription_id):
    """Vue détaillée de la situation financière d'un élève."""
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('finances:paiement_list')

    sit = _calcul_situation_financiere(inscription)

    echeancier_list = Echeancier.objects.filter(inscription=inscription).order_by('date_limite')
    echeancier_total = echeancier_list.aggregate(s=Sum('montant_du'))['s'] or Decimal('0')
    echeancier_paye = echeancier_list.filter(paye=True).aggregate(s=Sum('montant_du'))['s'] or Decimal('0')

    total_du = sit['total_du']
    total_paye = sit['total_paye']
    total_rembourse = sit['total_rembourse']
    pourcentage_paye = int(min(total_paye / total_du * 100, 100)) if total_du > 0 else 0

    # Remboursements liés à cette inscription (pour affichage dans la page)
    remboursements = (
        Remboursement.objects
        .filter(paiement__inscription=inscription)
        .select_related('paiement__rubrique', 'rembourse_par')
        .order_by('-date_remboursement')
    )

    from datetime import date as _date
    from .models import HistoriqueRelance
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
    })

@login_required
def remboursement_create(request, paiement_id):
    """Enregistrer un remboursement (total ou partiel) pour un paiement."""
    paiement = get_object_or_404(
        Paiement.objects.select_related('inscription__eleve', 'rubrique'),
        pk=paiement_id,
    )
    inscription = paiement.inscription

    # Montant déjà remboursé pour ce paiement
    deja_rembourse = (
        Remboursement.objects.filter(paiement=paiement)
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
        montant = None
        try:
            montant = Decimal(montant_raw)
            if montant <= 0:
                errors.append("Le montant doit être supérieur à 0.")
            elif montant > remboursable:
                errors.append(
                    f"Le montant remboursable est au maximum {remboursable:,.0f} FCFA "
                    f"(paiement {paiement.montant:,.0f} FCFA − déjà remboursé {deja_rembourse:,.0f} FCFA)."
                )
        except InvalidOperation:
            errors.append("Montant invalide.")

        from datetime import date as _date
        try:
            date_remb = _date.fromisoformat(date_raw) if date_raw else _date.today()
        except ValueError:
            date_remb = _date.today()

        if not errors:
            Remboursement.objects.create(
                paiement=paiement,
                montant=montant,
                motif=motif,
                date_remboursement=date_remb,
                rembourse_par=request.user,
            )
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
    """Annuler (supprimer) un remboursement."""
    remb = get_object_or_404(
        Remboursement.objects.select_related('paiement__inscription'),
        pk=remboursement_id,
    )
    inscription_id = remb.paiement.inscription.pk
    if request.method == 'POST':
        remb.delete()
        messages.success(request, "Remboursement annulé.")
    return redirect('finances:situation_eleve', inscription_id=inscription_id)


@login_required
def api_rubriques_inscription(request, inscription_id):
    """
    Retourne en JSON les rubriques disponibles et leur montant
    pour une inscription donnée (classe × statut × année scolaire).
    Utilisé par le formulaire de paiement pour le remplissage automatique.
    """
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    etablissement = inscription.classe.etablissement

    # Calcul du total deja verse par rubrique pour cette inscription (doit etre AVANT le return)
    totaux = (
        Paiement.objects
        .filter(inscription=inscription)
        .values('rubrique_id')
        .annotate(total=Sum('montant'))
    )
    totaux_map = {str(t['rubrique_id']): t['total'] for t in totaux}

    # ── Vérification : le code paiement (statut_eleve) doit être renseigné ──────
    if not inscription.statut_eleve_id:
        statut = inscription.statut_eleve  # None
        return JsonResponse({
            'rubriques': [],
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
        return JsonResponse({
            'rubriques': [],
            'statut_eleve': {
                'nom': statut.nom,
                'code': statut.code,
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

    rubriques = [
        {
            'id': rid,
            'nom': nom,
            'code': code,
            'montant': str(montant),
            'total_verse': str(totaux_map.get(rid) or 0),
        }
        for rid, nom, code, montant in rubriques_data
    ]

    statut = inscription.statut_eleve
    return JsonResponse({
        'rubriques': rubriques,
        'statut_eleve': {
            'nom': statut.nom if statut else None,
            'code': statut.code if statut else None,
            'couleur': statut.couleur if statut else None,
        },
    })


@login_required
def recu_pdf(request, paiement_id):
    """Génère le reçu de paiement en PDF via WeasyPrint.
    Regroupe toutes les rubriques payées de l'inscription dans un tableau."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:paiement_list')
    paiement = get_object_or_404(Paiement, pk=paiement_id)
    inscription = paiement.inscription
    etablissement = inscription.classe.etablissement
    
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
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:paiement_list')
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    etablissement = inscription.classe.etablissement

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
    
    paiements = Paiement.objects.filter(pk__in=paiement_ids).select_related(
        'inscription__eleve', 'rubrique', 'encaisse_par'
    )
    etab = inscription.classe.etablissement
    
    etab_context = get_etablissement_context(etab, request)
    
    return render(request, 'finances/paiement_confirmation.html', {
        'paiements': paiements,
        'inscription': inscription,
        'total': sum(p.montant for p in paiements),
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
    })


@login_required
def liste_redevables(request):
    """Liste des élèves redevables (ayant un reste à payer > 0)."""
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    
    annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    if not annee_courante:
        messages.warning(request, "Aucune année scolaire active.")
        return redirect('finances:paiement_list')
    
    query = request.GET.get('q', '').strip()
    
    # Toutes les inscriptions de l'année
    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee_courante,
        classe__etablissement=etab,
    ).exclude(statut='ABANDON').select_related('eleve', 'classe', 'classe__cycle', 'statut_eleve')
    
    if query:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=query) |
            Q(eleve__prenom__icontains=query) |
            Q(eleve__matricule__icontains=query) |
            Q(classe__nom__icontains=query)
        )
    
    # Regrouper par cycle puis par classe
    cycles_dict = {}
    total_redevable = Decimal('0')
    nb_redevables = 0
    
    for inscr in inscriptions:
        classe = inscr.classe
        cycle = classe.cycle

        sit = _calcul_situation_financiere(inscr)
        total_du = sit['total_du']
        total_paye = sit['total_paye']
        reste = sit['reste_a_payer']

        if reste > 0:
            nb_redevables += 1
            total_redevable += reste

            # Ajouter au cycle
            if cycle.nom not in cycles_dict:
                cycles_dict[cycle.nom] = {
                    'cycle': cycle,
                    'classes': {},
                    'total': Decimal('0'),
                }
            
            # Ajouter à la classe
            if classe.nom not in cycles_dict[cycle.nom]['classes']:
                cycles_dict[cycle.nom]['classes'][classe.nom] = {
                    'classe': classe,
                    'eleves': [],
                    'total': Decimal('0'),
                }
            
            cycles_dict[cycle.nom]['classes'][classe.nom]['eleves'].append({
                'inscription': inscr,
                'total_du': total_du,
                'total_paye': total_paye,
                'reste': reste,
                'derniere_relance': None,  # rempli après la boucle
            })
            cycles_dict[cycle.nom]['classes'][classe.nom]['total'] += reste
            cycles_dict[cycle.nom]['total'] += reste

    # Enrichir chaque élève avec sa dernière relance
    from .models import HistoriqueRelance
    inscription_ids = [
        item['inscription'].pk
        for c in cycles_dict.values()
        for cl in c['classes'].values()
        for item in cl['eleves']
    ]
    if inscription_ids:
        from django.db.models import Max
        relances_map = {
            r['inscription_id']: r['date_relance__max']
            for r in HistoriqueRelance.objects.filter(inscription_id__in=inscription_ids)
            .values('inscription_id')
            .annotate(date_relance__max=Max('date_relance'))
        }
        for c in cycles_dict.values():
            for cl in c['classes'].values():
                for item in cl['eleves']:
                    item['derniere_relance'] = relances_map.get(item['inscription'].pk)

    # Convertir en liste triée
    cycles_list = []
    for cycle_nom in sorted(cycles_dict.keys()):
        cycle_data = cycles_dict[cycle_nom]
        classes_list = []
        for classe_nom in sorted(cycle_data['classes'].keys()):
            classe_data = cycle_data['classes'][classe_nom]
            # Trier les élèves par reste décroissant
            classe_data['eleves'].sort(key=lambda x: (x['inscription'].eleve.nom, x['inscription'].eleve.prenom))
            classes_list.append(classe_data)
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })
    
    context = {
        'cycles_list': cycles_list,
        'total_redevable': total_redevable,
        'nb_redevables': nb_redevables,
        'annee_courante': annee_courante,
        'query': query,
    }
    return render(request, 'finances/liste_redevables.html', context)


def _bilan_paiements_qs(etab, annee_id, date_debut, date_fin, rub_id):
    """
    Retourne (annee_selected, rub_selected, paiements_qs) selon les filtres GET.
    Factorise la logique commune aux vues bilan HTML, PDF et CSV.
    """
    annee_selected = None
    if annee_id:
        annee_selected = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)

    rub_selected = None
    if rub_id:
        rub_selected = get_object_or_404(RubriquePaiement, pk=rub_id, etablissement=etab)

    paiements = (
        Paiement.objects
        .filter(inscription__classe__etablissement=etab)
        .select_related(
            'inscription__eleve',
            'inscription__classe__cycle',
            'rubrique',
        )
        .order_by('-date_paiement', '-created_at')
    )
    if annee_selected:
        paiements = paiements.filter(inscription__annee_scolaire=annee_selected)
    if date_debut:
        paiements = paiements.filter(date_paiement__gte=date_debut)
    if date_fin:
        paiements = paiements.filter(date_paiement__lte=date_fin)
    if rub_selected:
        paiements = paiements.filter(rubrique=rub_selected)

    return annee_selected, rub_selected, paiements


@login_required
def bilan_encaissements(request):
    """Bilan des encaissements par année scolaire et période."""
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle')
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('nom')

    annee_id = request.GET.get('annee')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    rub_id = request.GET.get('rubrique')

    # Année courante par défaut
    if not annee_id:
        annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
        if annee_courante:
            annee_id = annee_courante.pk

    annee_selected, rub_selected, paiements = _bilan_paiements_qs(
        etab, annee_id, date_debut, date_fin, rub_id
    )
    
    # Statistiques
    total_encaissement = paiements.aggregate(Sum('montant'))['montant__sum'] or 0
    nb_paiements = paiements.count()

    # Par mode de paiement (agrégation ORM sur le queryset filtré)
    par_mode = {
        (row['mode_paiement'] or 'Non défini'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
        }
        for row in paiements
        .values('mode_paiement')
        .annotate(count=Count('id'), total=Sum('montant'))
    }

    # Par jour (agrégation ORM)
    par_jour = {
        row['jour'].strftime('%d/%m/%Y'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
            'date': row['jour'],
        }
        for row in paiements
        .annotate(jour=TruncDate('date_paiement'))
        .values('jour')
        .annotate(count=Count('id'), total=Sum('montant'))
        .order_by('-jour')
    }
    
    # Par cycle et classe (une seule passe sur les paiements déjà chargés)
    cycles_dict = {}
    for p in paiements:
        cycle = p.inscription.classe.cycle if p.inscription.classe else None
        classe = p.inscription.classe
        if not cycle or not classe:
            continue

        cycle_key = cycle.pk
        if cycle_key not in cycles_dict:
            cycles_dict[cycle_key] = {
                'cycle': cycle,
                'ordre': cycle.ordre if hasattr(cycle, 'ordre') else 0,
                'classes': {},
                'total': Decimal('0'),
            }

        classe_key = classe.pk
        if classe_key not in cycles_dict[cycle_key]['classes']:
            cycles_dict[cycle_key]['classes'][classe_key] = {
                'classe': classe,
                'paiements': [],
                'total': Decimal('0'),
            }

        cycles_dict[cycle_key]['classes'][classe_key]['paiements'].append(p)
        cycles_dict[cycle_key]['classes'][classe_key]['total'] += p.montant
        cycles_dict[cycle_key]['total'] += p.montant

    cycles_list = []
    for cycle_data in sorted(cycles_dict.values(), key=lambda c: (c['ordre'], c['cycle'].nom)):
        classes_list = sorted(
            cycle_data['classes'].values(),
            key=lambda c: c['classe'].nom,
        )
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })
    
    context = {
        'annees': annees,
        'rubriques': rubriques,
        'annee_selected': annee_selected,
        'rub_selected': rub_selected,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'cycles_list': cycles_list,
        'total_encaissement': total_encaissement,
        'nb_paiements': nb_paiements,
        'par_mode': par_mode,
        'par_jour': par_jour,
    }
    return render(request, 'finances/bilan_encaissements.html', context)


@login_required
def bilan_encaissements_pdf(request):
    """Génère un PDF du bilan des encaissements."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:bilan_encaissements')
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    etab_context = get_etablissement_context(etab, request)

    annee_id = request.GET.get('annee')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    rub_id = request.GET.get('rubrique')

    annee_selected, rub_selected, paiements = _bilan_paiements_qs(
        etab, annee_id, date_debut, date_fin, rub_id
    )

    total_encaissement = paiements.aggregate(Sum('montant'))['montant__sum'] or 0
    nb_paiements = paiements.count()

    par_mode = {
        (row['mode_paiement'] or 'Non défini'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
        }
        for row in paiements
        .values('mode_paiement')
        .annotate(count=Count('id'), total=Sum('montant'))
    }

    par_jour = {
        row['jour'].strftime('%d/%m/%Y'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
            'date': row['jour'],
        }
        for row in paiements
        .annotate(jour=TruncDate('date_paiement'))
        .values('jour')
        .annotate(count=Count('id'), total=Sum('montant'))
        .order_by('-jour')
    }

    # Par cycle et classe (clé par PK pour éviter les collisions de noms)
    cycles_dict = {}
    for p in paiements:
        cycle = p.inscription.classe.cycle if p.inscription.classe else None
        classe = p.inscription.classe
        if not cycle or not classe:
            continue

        cycle_key = cycle.pk
        if cycle_key not in cycles_dict:
            cycles_dict[cycle_key] = {
                'cycle': cycle,
                'ordre': cycle.ordre if hasattr(cycle, 'ordre') else 0,
                'classes': {},
                'total': Decimal('0'),
            }

        classe_key = classe.pk
        if classe_key not in cycles_dict[cycle_key]['classes']:
            cycles_dict[cycle_key]['classes'][classe_key] = {
                'classe': classe,
                'paiements': [],
                'total': Decimal('0'),
            }

        cycles_dict[cycle_key]['classes'][classe_key]['paiements'].append(p)
        cycles_dict[cycle_key]['classes'][classe_key]['total'] += p.montant
        cycles_dict[cycle_key]['total'] += p.montant

    cycles_list = []
    for cycle_data in sorted(cycles_dict.values(), key=lambda c: (c['ordre'], c['cycle'].nom)):
        classes_list = sorted(
            cycle_data['classes'].values(),
            key=lambda c: c['classe'].nom,
        )
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })

    html_string = render_to_string('finances/pdf/bilan_encaissements.html', {
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'annee_selected': annee_selected,
        'rub_selected': rub_selected,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'cycles_list': cycles_list,
        'total_encaissement': total_encaissement,
        'nb_paiements': nb_paiements,
        'par_mode': par_mode,
        'par_jour': par_jour,
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Bilan_Encaissements_{annee_selected.libelle if annee_selected else 'Tous'}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def bilan_encaissements_csv(request):
    """Export CSV du bilan des encaissements (mêmes filtres que la vue HTML)."""
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annee_id = request.GET.get('annee')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    rub_id = request.GET.get('rubrique')

    annee_selected, rub_selected, paiements = _bilan_paiements_qs(
        etab, annee_id, date_debut, date_fin, rub_id
    )

    nom_fichier = f"bilan_encaissements_{annee_selected.libelle if annee_selected else 'tous'}.csv".replace(' ', '_')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Date', 'Élève', 'Matricule', 'Classe', 'Cycle', 'Rubrique', 'Montant (FCFA)', 'Mode de paiement'])

    for p in paiements:
        eleve = p.inscription.eleve
        classe = p.inscription.classe
        writer.writerow([
            p.date_paiement.strftime('%d/%m/%Y') if p.date_paiement else '',
            f"{eleve.nom} {eleve.prenom}",
            eleve.matricule or '',
            classe.nom if classe else '',
            classe.cycle.nom if classe and classe.cycle else '',
            p.rubrique.nom if p.rubrique else '',
            str(p.montant),
            p.mode_paiement or '',
        ])

    return response


@login_required
def liste_redevables_pdf(request):
    """Génère un PDF de la liste des élèves redevables."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:liste_redevables')
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    
    annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    if not annee_courante:
        messages.warning(request, "Aucune année scolaire active.")
        return redirect('finances:paiement_list')
    
    etab_context = get_etablissement_context(etab, request)
    
    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee_courante,
        classe__etablissement=etab,
    ).exclude(statut='ABANDON').select_related('eleve', 'classe', 'classe__cycle', 'statut_eleve')

    cycles_dict = {}
    total_redevable = Decimal('0')
    nb_redevables = 0
    
    for inscr in inscriptions:
        classe = inscr.classe
        cycle = classe.cycle

        sit = _calcul_situation_financiere(inscr)
        total_du = sit['total_du']
        total_paye = sit['total_paye']
        reste = sit['reste_a_payer']

        if reste > 0:
            nb_redevables += 1
            total_redevable += reste

            if cycle.nom not in cycles_dict:
                cycles_dict[cycle.nom] = {
                    'cycle': cycle,
                    'classes': {},
                    'total': Decimal('0'),
                }
            
            if classe.nom not in cycles_dict[cycle.nom]['classes']:
                cycles_dict[cycle.nom]['classes'][classe.nom] = {
                    'classe': classe,
                    'eleves': [],
                    'total': Decimal('0'),
                }
            
            cycles_dict[cycle.nom]['classes'][classe.nom]['eleves'].append({
                'inscription': inscr,
                'total_du': total_du,
                'total_paye': total_paye,
                'reste': reste,
            })
            cycles_dict[cycle.nom]['classes'][classe.nom]['total'] += reste
            cycles_dict[cycle.nom]['total'] += reste
    
    cycles_list = []
    for cycle_nom in sorted(cycles_dict.keys()):
        cycle_data = cycles_dict[cycle_nom]
        classes_list = []
        for classe_nom in sorted(cycle_data['classes'].keys()):
            classe_data = cycle_data['classes'][classe_nom]
            classe_data['eleves'].sort(key=lambda x: (x['inscription'].eleve.nom, x['inscription'].eleve.prenom))
            classes_list.append(classe_data)
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })
    
    html_string = render_to_string('finances/pdf/liste_redevables.html', {
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'cycles_list': cycles_list,
        'total_redevable': total_redevable,
        'nb_redevables': nb_redevables,
        'annee_courante': annee_courante,
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Redevables_{annee_courante.libelle}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def liste_exoneres(request):
    """Liste des élèves exonérés de paiement, regroupés par classe."""
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle')
    annee_id = request.GET.get('annee')
    annee = None
    if annee_id:
        annee = annees.filter(pk=annee_id).first()
    if not annee:
        annee = annees.filter(est_courante=True).first() or annees.first()

    query = request.GET.get('q', '').strip()

    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee,
        classe__etablissement=etab,
        est_exonere=True,
    ).select_related('eleve', 'classe', 'classe__cycle').order_by(
        'classe__cycle__ordre', 'classe__nom', 'eleve__nom', 'eleve__prenom'
    )

    if query:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=query) |
            Q(eleve__prenom__icontains=query) |
            Q(eleve__matricule__icontains=query)
        )

    # Regrouper par classe
    classes_dict = {}
    for inscr in inscriptions:
        key = str(inscr.classe_id)
        if key not in classes_dict:
            classes_dict[key] = {
                'classe': inscr.classe,
                'cycle': inscr.classe.cycle,
                'eleves': [],
            }
        classes_dict[key]['eleves'].append(inscr)

    groupes = sorted(classes_dict.values(), key=lambda g: (
        g['cycle'].ordre if g['cycle'] else 99,
        g['classe'].nom,
    ))

    return render(request, 'finances/liste_exoneres.html', {
        'annees': annees,
        'annee': annee,
        'groupes': groupes,
        'total': inscriptions.count(),
        'query': query,
    })


@login_required
def liste_exoneres_pdf(request):
    """Génère le PDF de la liste des élèves exonérés, regroupés par classe."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:liste_exoneres')
    etab = request.user.etablissement
    if not etab:
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle')
    annee_id = request.GET.get('annee')
    annee = None
    if annee_id:
        annee = annees.filter(pk=annee_id).first()
    if not annee:
        annee = annees.filter(est_courante=True).first() or annees.first()

    etab_context = get_etablissement_context(etab, request)

    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee,
        classe__etablissement=etab,
        est_exonere=True,
    ).select_related('eleve', 'classe', 'classe__cycle').order_by(
        'classe__cycle__ordre', 'classe__nom', 'eleve__nom', 'eleve__prenom'
    )

    classes_dict = {}
    for inscr in inscriptions:
        key = str(inscr.classe_id)
        if key not in classes_dict:
            classes_dict[key] = {
                'classe': inscr.classe,
                'cycle': inscr.classe.cycle,
                'eleves': [],
            }
        classes_dict[key]['eleves'].append(inscr)

    groupes = sorted(classes_dict.values(), key=lambda g: (
        g['cycle'].ordre if g['cycle'] else 99,
        g['classe'].nom,
    ))

    html_string = render_to_string('finances/pdf/liste_exoneres.html', {
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'groupes': groupes,
        'total': inscriptions.count(),
        'annee': annee,
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Exoneres_{annee.libelle if annee else 'liste'}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def relance_paiement(request):
    """Sélecteur pour la génération des relances de paiement."""
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_id = request.GET.get('annee') or request.POST.get('annee')
    annee = AnneeScolaire.objects.filter(pk=annee_id, etablissement=etab).first() if annee_id else \
            annees.filter(est_courante=True).first()

    classes = Classe.objects.filter(etablissement=etab).order_by('cycle__ordre', 'niveau', 'nom') if annee else []
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')

    return render(request, 'finances/relance_selector.html', {
        'annees': annees,
        'annee': annee,
        'classes': classes,
        'rubriques': rubriques,
    })


@login_required
def relance_count(request):
    """Retourne en HTML le nombre d'élèves redevables pour les relances (usage HTMX)."""
    etab = request.user.etablissement
    annee_id    = request.GET.get('annee')
    classe_id   = request.GET.get('classe')
    rubrique_id = request.GET.get('rubrique')

    if not (annee_id and classe_id and rubrique_id and etab):
        return HttpResponse('')

    annee    = AnneeScolaire.objects.filter(pk=annee_id, etablissement=etab).first()
    rubrique = RubriquePaiement.objects.filter(pk=rubrique_id, etablissement=etab).first()

    if not (annee and rubrique):
        return HttpResponse('')

    insc_qs = Inscription.objects.filter(
        annee_scolaire=annee,
    ).exclude(statut='ABANDON').select_related('eleve', 'statut_eleve', 'classe')

    if classe_id == 'all':
        insc_qs = insc_qs.filter(classe__etablissement=etab)
        classe = None
    else:
        classe = Classe.objects.filter(pk=classe_id, etablissement=etab).first()
        if not classe:
            return HttpResponse('')
        insc_qs = insc_qs.filter(classe=classe)

    inscriptions = insc_qs

    count = 0
    for inscr in inscriptions:
        if not inscr.statut_eleve_id:
            continue
        tarif = TarifScolarite.objects.filter(
            etablissement=etab,
            classe__niveau=inscr.classe.niveau,
            annee_scolaire=annee,
            statut_eleve=inscr.statut_eleve,
            rubrique=rubrique,
            actif=True,
        ).first()
        montant_du = tarif.montant if tarif else Decimal('0')
        verse = Paiement.objects.filter(
            inscription=inscr, rubrique=rubrique
        ).aggregate(s=Sum('montant'))['s'] or Decimal('0')
        if max(montant_du - verse, Decimal('0')) > 0:
            count += 1

    if count == 0:
        html = (
            '<div style="display:flex;align-items:center;gap:.5rem;padding:.75rem 1rem;'
            'background:#fef2f2;border:1px solid #fecaca;border-radius:8px;color:#b91c1c;font-size:.875rem;">'
            '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
            '</svg>'
            '<span>Aucun élève redevable pour cette sélection.</span>'
            '</div>'
        )
    else:
        label = 'élève redevable' if count == 1 else 'élèves redevables'
        html = (
            f'<div style="display:flex;align-items:center;gap:.5rem;padding:.75rem 1rem;'
            f'background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;color:#15803d;font-size:.875rem;">'
            f'<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
            f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>'
            f'</svg>'
            f'<strong>{count}</strong>&nbsp;{label} — {count} relance{"s" if count > 1 else ""} seront générées.'
            f'</div>'
        )
    return HttpResponse(html)


@login_required
def relance_paiement_pdf(request):
    """Génère le PDF des relances de paiement pour une classe et une rubrique."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:relance_paiement')
    etab = request.user.etablissement
    if not etab:
        return redirect('finances:paiement_list')

    annee_id   = request.GET.get('annee')
    classe_id  = request.GET.get('classe')
    rubrique_id = request.GET.get('rubrique')
    date_echeance = request.GET.get('date_echeance', '')

    annee    = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    rubrique = get_object_or_404(RubriquePaiement, pk=rubrique_id, etablissement=etab)

    # classe_id peut être 'all' → toutes les classes de l'établissement
    if classe_id == 'all':
        classe = None
        insc_qs = Inscription.objects.filter(
            annee_scolaire=annee,
            classe__etablissement=etab,
        )
    else:
        classe = get_object_or_404(Classe, pk=classe_id, etablissement=etab)
        insc_qs = Inscription.objects.filter(
            annee_scolaire=annee,
            classe=classe,
        )

    etab_context = get_etablissement_context(etab, request)

    # Signataire
    from parametres.models import SignataireDocument, TypeDocument
    type_doc = TypeDocument.objects.filter(code='RELANCE').first()
    signataire = None
    sig_membre = None
    if type_doc:
        cycle_filter = classe.cycle if classe else None
        if cycle_filter:
            signataire = SignataireDocument.objects.filter(
                type_document=type_doc,
                cycle=cycle_filter,
                annee_scolaire=annee,
            ).first()
        if not signataire:
            signataire = SignataireDocument.objects.filter(
                type_document=type_doc,
                annee_scolaire=annee,
            ).first()
    if signataire:
        sig_membre = signataire.get_membre_personnel()

    # Inscriptions triées par classe puis par élève
    inscriptions = insc_qs.exclude(statut='ABANDON').select_related(
        'eleve', 'classe', 'classe__cycle', 'statut_eleve'
    ).order_by('classe__nom', 'eleve__nom', 'eleve__prenom')

    # Pour chaque inscription, calculer le reste à payer pour la rubrique sélectionnée
    relances = []
    for inscr in inscriptions:
        if not inscr.statut_eleve_id:
            continue

        # Tarif pour cette rubrique × niveau × statut
        tarif_qs = TarifScolarite.objects.filter(
            etablissement=etab,
            classe__niveau=inscr.classe.niveau,
            annee_scolaire=annee,
            statut_eleve=inscr.statut_eleve,
            rubrique=rubrique,
            actif=True,
        )
        tarif = tarif_qs.first()
        montant_du = tarif.montant if tarif else Decimal('0')

        # Montant versé pour cette rubrique
        verse = Paiement.objects.filter(
            inscription=inscr, rubrique=rubrique
        ).aggregate(s=Sum('montant'))['s'] or Decimal('0')

        reste = max(montant_du - verse, Decimal('0'))
        if reste <= 0:
            continue  # Élève à jour pour cette rubrique

        # Dernière date d'échéance configurée pour cet élève
        derniere_echeance = Paiement.objects.filter(
            inscription=inscr, rubrique=rubrique, echeance__isnull=False
        ).order_by('-echeance').values_list('echeance', flat=True).first()

        eleve = inscr.eleve
        contact_nom = eleve.tuteur_nom or eleve.nom_pere or ''
        contact_tel = eleve.tuteur_telephone or getattr(eleve, 'telephone_parent', '') or ''
        relances.append({
            'inscription': inscr,
            'eleve': eleve,
            'classe': inscr.classe,
            'montant_du': montant_du,
            'verse': verse,
            'reste': reste,
            'date_echeance': date_echeance or (derniere_echeance.strftime('%d/%m/%Y') if derniere_echeance else ''),
            'contact_nom': contact_nom,
            'contact_tel': contact_tel,
        })

    from django.utils import timezone as tz
    html_string = render_to_string('finances/pdf/relance_paiement.html', {
        'relances': relances,
        'annee': annee,
        'classe': classe,
        'rubrique': rubrique,
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'date_impression': tz.now().strftime('%d/%m/%Y'),
        'signataire': signataire,
        'sig_membre': sig_membre,
    }, request=request)

    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Relances_{classe.nom if classe else 'toutes'}_{rubrique.nom}.pdf".replace(" ", "_")

    # Traçabilité : enregistrer une ligne HistoriqueRelance par élève redevable
    from .models import HistoriqueRelance, CanalRelance
    import datetime as _dt
    aujourd_hui = _dt.date.today()
    historique_bulk = [
        HistoriqueRelance(
            inscription=r['inscription'],
            rubrique=rubrique,
            canal=CanalRelance.PDF,
            montant_reclame=r['reste'],
            envoye_par=request.user,
            date_relance=aujourd_hui,
            succes=True,
            detail=nom,
        )
        for r in relances
    ]
    if historique_bulk:
        HistoriqueRelance.objects.bulk_create(historique_bulk)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def echeancier_create(request, inscription_id):
    """Créer un échéancier pour un élève."""
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    
    if request.method == 'POST':
        form = EcheancierForm(request.POST)
        if form.is_valid():
            echeancier = form.save(commit=False)
            echeancier.inscription = inscription
            echeancier.save()
            messages.success(request, f"Échéance '{echeancier.libelle}' créée avec succès.")
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)
    else:
        form = EcheancierForm()
    
    return render(request, 'finances/echeancier_form.html', {
        'form': form,
        'inscription': inscription,
        'title': "Créer une échéance",
    })


@login_required
def echeancier_edit(request, echeancier_id):
    """Modifier une échéance existante."""
    echeancier = get_object_or_404(Echeancier, pk=echeancier_id)
    inscription = echeancier.inscription
    
    if request.method == 'POST':
        form = EcheancierForm(request.POST, instance=echeancier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Échéance '{echeancier.libelle}' mise à jour.")
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)
    else:
        form = EcheancierForm(instance=echeancier)
    
    return render(request, 'finances/echeancier_form.html', {
        'form': form,
        'inscription': inscription,
        'echeancier': echeancier,
        'title': "Modifier l'échéance",
    })


@login_required
def echeancier_delete(request, echeancier_id):
    """Supprimer une échéance."""
    echeancier = get_object_or_404(Echeancier, pk=echeancier_id)
    inscription = echeancier.inscription
    
    if request.method == 'POST':
        echeancier_name = echeancier.libelle
        echeancier.delete()
        messages.success(request, f"Échéance '{echeancier_name}' supprimée.")
        return redirect('finances:situation_eleve', inscription_id=inscription.pk)
    
    return render(request, 'finances/echeancier_confirm_delete.html', {
        'echeancier': echeancier,
        'inscription': inscription,
    })


@login_required
def certificat_non_redevabilite(request, inscription_id):
    """Génère le certificat de non-redevabilité en PDF."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:paiement_list')
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    etablissement = inscription.classe.etablissement
    
    etab_context = get_etablissement_context(etablissement, request)
    
    sit = _calcul_situation_financiere(inscription)
    total_paye = sit['total_paye']
    total_du = sit['total_du']
    reste_a_payer = sit['reste_a_payer']
    est_regulier = reste_a_payer <= 0
    
    html_string = render_to_string('finances/pdf/certificat_non_redevabilite.html', {
        'inscription': inscription,
        'etablissement': etablissement,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'total_du': total_du,
        'total_paye': total_paye,
        'reste_a_payer': reste_a_payer,
        'est_regulier': est_regulier,
        'annee_scolaire': inscription.annee_scolaire,
        'date_du_jour': timezone.now().strftime('%d/%m/%Y'),
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Certificat_Non_Redevabilite_{inscription.eleve.nom}_{inscription.id.hex[:8]}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
@require_POST
def relance_sms(request):
    """Envoie des SMS de relance paiement aux parents des élèves redevables."""
    from core.notifications import notifier_relance_paiement

    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:relance_paiement')

    annee_id    = request.POST.get('annee')
    classe_id   = request.POST.get('classe')
    rubrique_id = request.POST.get('rubrique')

    annee    = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    rubrique = get_object_or_404(RubriquePaiement, pk=rubrique_id, etablissement=etab)

    if classe_id == 'all':
        insc_qs = Inscription.objects.filter(
            annee_scolaire=annee, classe__etablissement=etab,
        )
    else:
        classe = get_object_or_404(Classe, pk=classe_id, etablissement=etab)
        insc_qs = Inscription.objects.filter(annee_scolaire=annee, classe=classe)

    inscriptions = insc_qs.exclude(statut='ABANDON').select_related('eleve', 'classe')

    nb_envoyes = 0
    nb_sans_numero = 0

    from parametres.models import ModeleMessage
    from core.tasks import envoyer_sms_async

    for inscr in inscriptions:
        # Calculer le reste à payer pour cette rubrique
        tarif = TarifScolarite.objects.filter(
            etablissement=etab, rubrique=rubrique,
        ).first()
        montant_du = tarif.montant if tarif else Decimal('0')
        montant_paye = Paiement.objects.filter(
            inscription=inscr, rubrique=rubrique,
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        reste = montant_du - montant_paye

        if reste <= 0:
            continue  # à jour — pas de relance

        eleve = inscr.eleve

        # Chercher un numéro valide (Burkina : 8 chiffres ou +226XXXXXXXX)
        for champ in ('telephone_parent', 'tuteur_telephone', 'telephone_urgence'):
            candidat = (getattr(eleve, champ, '') or '').strip()
            if _numero_valide(candidat):
                numero = candidat
                break
        else:
            nb_sans_numero += 1
            continue

        sms_msg = ModeleMessage.get_contenu(etab, 'PAIEMENT', {
            'nom_eleve': eleve.get_nom_complet(),
            'montant': f"{reste:,.0f}".replace(',', ' '),
            'rubrique': rubrique.nom,
            'etablissement': etab.nom,
        })
        envoyer_sms_async(numero, sms_msg)
        nb_envoyes += 1

        from .models import HistoriqueRelance, CanalRelance
        import datetime as _dt
        HistoriqueRelance.objects.create(
            inscription=inscr,
            rubrique=rubrique,
            canal=CanalRelance.SMS,
            montant_reclame=max(reste, Decimal('0')),
            envoye_par=request.user,
            date_relance=_dt.date.today(),
            succes=True,
            detail=numero,
        )

    if nb_envoyes:
        messages.success(request, f"{nb_envoyes} SMS de relance envoyé(s).")
    if nb_sans_numero:
        messages.warning(request, f"{nb_sans_numero} élève(s) sans numéro valide — non contacté(s).")
    if not nb_envoyes and not nb_sans_numero:
        messages.info(request, "Aucun élève redevable trouvé pour cette sélection.")

    return redirect('finances:relance_paiement')


@login_required
def historique_relances(request):
    """Vue globale de l'historique des relances envoyées, avec filtres."""
    from .models import HistoriqueRelance

    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    classes = Classe.objects.filter(etablissement=etab).order_by('cycle__ordre', 'niveau', 'nom')
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')

    # Filtres GET
    annee_id    = request.GET.get('annee', '')
    classe_id   = request.GET.get('classe', '')
    rubrique_id = request.GET.get('rubrique', '')
    canal       = request.GET.get('canal', '')
    date_debut  = request.GET.get('date_debut', '')
    date_fin    = request.GET.get('date_fin', '')
    q           = request.GET.get('q', '').strip()

    qs = (
        HistoriqueRelance.objects
        .filter(inscription__classe__etablissement=etab)
        .select_related(
            'inscription__eleve',
            'inscription__classe__cycle',
            'rubrique',
            'envoye_par',
        )
        .order_by('-date_relance', '-created_at')
    )

    if annee_id:
        qs = qs.filter(inscription__annee_scolaire_id=annee_id)
    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if rubrique_id:
        qs = qs.filter(rubrique_id=rubrique_id)
    if canal:
        qs = qs.filter(canal=canal)
    if date_debut:
        qs = qs.filter(date_relance__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_relance__lte=date_fin)
    if q:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=q) |
            Q(inscription__eleve__prenom__icontains=q) |
            Q(inscription__eleve__matricule__icontains=q)
        )

    total_reclame = qs.aggregate(s=Sum('montant_reclame'))['s'] or Decimal('0')

    return render(request, 'finances/historique_relances.html', {
        'relances': qs,
        'total_reclame': total_reclame,
        'nb_relances': qs.count(),
        'annees': annees,
        'classes': classes,
        'rubriques': rubriques,
        # valeurs sélectionnées
        'f_annee': annee_id,
        'f_classe': classe_id,
        'f_rubrique': rubrique_id,
        'f_canal': canal,
        'f_date_debut': date_debut,
        'f_date_fin': date_fin,
        'f_q': q,
    })


# ── Bourses et Aides Scolaires ────────────────────────────────────────────────

@login_required
def bourse_create(request, inscription_id):
    """Attribuer une bourse ou aide scolaire à une inscription."""
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    etab = inscription.classe.etablissement

    types_bourses = TypeBourse.objects.filter(etablissement=etab, actif=True).order_by('nom')
    from parametres.models import RubriquePaiement
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')

    if request.method == 'POST':
        type_bourse_id = request.POST.get('type_bourse')
        montant_raw = request.POST.get('montant_accorde', '').replace(',', '.').strip()
        rubrique_id = request.POST.get('rubrique') or None
        date_attr = request.POST.get('date_attribution') or str(timezone.now().date())
        date_exp = request.POST.get('date_expiration') or None
        reference = request.POST.get('reference_document', '').strip()
        observation = request.POST.get('observation', '').strip()

        errors = []
        type_bourse = None
        montant = None

        try:
            type_bourse = TypeBourse.objects.get(pk=type_bourse_id, etablissement=etab)
        except TypeBourse.DoesNotExist:
            errors.append("Type de bourse invalide.")

        try:
            montant = Decimal(montant_raw)
            if montant <= 0:
                errors.append("Le montant doit être positif.")
        except (InvalidOperation, ValueError):
            errors.append("Montant invalide.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            rubrique = None
            if rubrique_id:
                from parametres.models import RubriquePaiement as RP
                rubrique = RP.objects.filter(pk=rubrique_id, etablissement=etab).first()

            BourseEleve.objects.create(
                inscription=inscription,
                type_bourse=type_bourse,
                montant_accorde=montant,
                rubrique=rubrique,
                date_attribution=date_attr,
                date_expiration=date_exp or None,
                reference_document=reference,
                observation=observation,
                attribue_par=request.user,
                actif=True,
            )
            messages.success(
                request,
                f"Bourse \u00ab\u00a0{type_bourse.nom}\u00a0\u00bb de {montant:,.0f} FCFA attribuee a "
                f"{inscription.eleve.get_nom_complet()}."
            )
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)

    return render(request, 'finances/bourse_form.html', {
        'inscription': inscription,
        'types_bourses': types_bourses,
        'rubriques': rubriques,
        'today': timezone.now().date().isoformat(),
    })


@login_required
def bourse_edit(request, bourse_id):
    """Modifier une bourse attribuee."""
    bourse = get_object_or_404(BourseEleve, pk=bourse_id)
    inscription = bourse.inscription
    etab = inscription.classe.etablissement

    types_bourses = TypeBourse.objects.filter(etablissement=etab, actif=True).order_by('nom')
    from parametres.models import RubriquePaiement
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')

    if request.method == 'POST':
        type_bourse_id = request.POST.get('type_bourse')
        montant_raw = request.POST.get('montant_accorde', '').replace(',', '.').strip()
        rubrique_id = request.POST.get('rubrique') or None
        date_attr = request.POST.get('date_attribution') or str(timezone.now().date())
        date_exp = request.POST.get('date_expiration') or None
        reference = request.POST.get('reference_document', '').strip()
        observation = request.POST.get('observation', '').strip()
        actif = request.POST.get('actif') == 'on'

        errors = []
        type_bourse = None
        montant = None

        try:
            type_bourse = TypeBourse.objects.get(pk=type_bourse_id, etablissement=etab)
        except TypeBourse.DoesNotExist:
            errors.append("Type de bourse invalide.")

        try:
            montant = Decimal(montant_raw)
            if montant <= 0:
                errors.append("Le montant doit etre positif.")
        except (InvalidOperation, ValueError):
            errors.append("Montant invalide.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            rubrique = None
            if rubrique_id:
                from parametres.models import RubriquePaiement as RP
                rubrique = RP.objects.filter(pk=rubrique_id, etablissement=etab).first()

            bourse.type_bourse = type_bourse
            bourse.montant_accorde = montant
            bourse.rubrique = rubrique
            bourse.date_attribution = date_attr
            bourse.date_expiration = date_exp or None
            bourse.reference_document = reference
            bourse.observation = observation
            bourse.actif = actif
            bourse.save()
            messages.success(request, "Bourse mise a jour.")
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)

    return render(request, 'finances/bourse_form.html', {
        'inscription': inscription,
        'bourse': bourse,
        'types_bourses': types_bourses,
        'rubriques': rubriques,
        'today': timezone.now().date().isoformat(),
    })


@login_required
@require_POST
def bourse_delete(request, bourse_id):
    """Supprimer une bourse attribuee."""
    bourse = get_object_or_404(BourseEleve, pk=bourse_id)
    inscription_id = bourse.inscription_id
    nom = bourse.type_bourse.nom
    bourse.delete()
    messages.success(request, f"Bourse {nom!r} supprimee.")
    return redirect('finances:situation_eleve', inscription_id=inscription_id)


@login_required
def boursiers_list(request):
    """Liste globale de tous les eleves beneficiant d'une bourse ou aide scolaire."""
    etab = request.user.etablissement
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    source = request.GET.get('source', '')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('nom')

    qs = BourseEleve.objects.filter(
        inscription__annee_scolaire=annee_sel,
        inscription__classe__etablissement=etab,
        actif=True,
    ).select_related(
        'inscription__eleve', 'inscription__classe',
        'type_bourse', 'rubrique',
    ).order_by('inscription__classe__nom', 'inscription__eleve__nom')

    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if source:
        qs = qs.filter(type_bourse__source=source)

    total_reduction = qs.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')

    from .models import SourceBourse
    return render(request, 'finances/boursiers_list.html', {
        'bourses': qs,
        'annees': annees,
        'annee_sel': annee_sel,
        'classes': classes,
        'classe_id': classe_id,
        'source_sel': source,
        'source_choices': SourceBourse.choices,
        'total_reduction': total_reduction,
    })


@login_required
def boursiers_pdf(request):
    """PDF - Liste des boursiers/beneficiaires d'aides."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur ce serveur.")
        return redirect('finances:boursiers_list')
    etab = request.user.etablissement
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    source = request.GET.get('source', '')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    qs = BourseEleve.objects.filter(
        inscription__annee_scolaire=annee_sel,
        inscription__classe__etablissement=etab,
        actif=True,
    ).select_related(
        'inscription__eleve', 'inscription__classe',
        'type_bourse', 'rubrique',
    ).order_by('inscription__classe__nom', 'inscription__eleve__nom')

    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if source:
        qs = qs.filter(type_bourse__source=source)

    total_reduction = qs.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')

    etab_context = get_etablissement_context(etab, request)
    html_string = render_to_string('finances/pdf/liste_boursiers.html', {
        'bourses': qs,
        'annee_sel': annee_sel,
        'total_reduction': total_reduction,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'now': timezone.now(),
    }, request=request)

    buffer = io.BytesIO()
    WeasyHTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="boursiers.pdf"'
    return response


@login_required
def type_bourse_list(request):
    """Gerer les types de bourses de l'etablissement."""
    etab = request.user.etablissement
    types = TypeBourse.objects.filter(etablissement=etab).order_by('nom')
    return render(request, 'finances/type_bourse_list.html', {'types': types})


@login_required
def type_bourse_form(request, type_id=None):
    """Creer ou modifier un type de bourse."""
    etab = request.user.etablissement
    instance = get_object_or_404(TypeBourse, pk=type_id, etablissement=etab) if type_id else None

    from parametres.models import RubriquePaiement
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')
    from .models import SourceBourse

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()
        source = request.POST.get('source', SourceBourse.ETABLISSEMENT)
        type_reduction = request.POST.get('type_reduction', TypeReduction.POURCENTAGE)
        valeur_raw = request.POST.get('valeur_reduction', '').replace(',', '.').strip()
        rubrique_id = request.POST.get('rubrique') or None
        actif = request.POST.get('actif') == 'on'

        errors = []
        valeur = None

        if not nom:
            errors.append("Le nom est obligatoire.")
        if not code:
            errors.append("Le code est obligatoire.")
        try:
            valeur = Decimal(valeur_raw)
            if valeur <= 0:
                errors.append("La valeur de reduction doit etre positive.")
            if type_reduction == TypeReduction.POURCENTAGE and valeur > 100:
                errors.append("Un pourcentage ne peut pas depasser 100.")
        except (InvalidOperation, ValueError):
            errors.append("Valeur de reduction invalide.")

        if not errors:
            qs_code = TypeBourse.objects.filter(etablissement=etab, code=code)
            if instance:
                qs_code = qs_code.exclude(pk=instance.pk)
            if qs_code.exists():
                errors.append(f"Le code {code!r} est deja utilise.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            rubrique = None
            if rubrique_id:
                from parametres.models import RubriquePaiement as RP
                rubrique = RP.objects.filter(pk=rubrique_id, etablissement=etab).first()

            if instance:
                instance.nom = nom
                instance.code = code
                instance.description = description
                instance.source = source
                instance.type_reduction = type_reduction
                instance.valeur_reduction = valeur
                instance.rubrique = rubrique
                instance.actif = actif
                instance.save()
                messages.success(request, f"Type de bourse {nom!r} mis a jour.")
            else:
                TypeBourse.objects.create(
                    etablissement=etab, nom=nom, code=code, description=description,
                    source=source, type_reduction=type_reduction, valeur_reduction=valeur,
                    rubrique=rubrique, actif=actif,
                )
                messages.success(request, f"Type de bourse {nom!r} cree.")
            return redirect('finances:type_bourse_list')

    return render(request, 'finances/type_bourse_form.html', {
        'instance': instance,
        'rubriques': rubriques,
        'source_choices': SourceBourse.choices,
        'type_reduction_choices': TypeReduction.choices,
    })


@login_required
@require_POST
def type_bourse_delete(request, type_id):
    """Supprimer un type de bourse (si aucune attribution active)."""
    etab = request.user.etablissement
    tb = get_object_or_404(TypeBourse, pk=type_id, etablissement=etab)
    if tb.attributions.filter(actif=True).exists():
        messages.error(request, "Impossible de supprimer : des bourses actives utilisent ce type.")
    else:
        nom = tb.nom
        tb.delete()
        messages.success(request, f"Type {nom!r} supprime.")
    return redirect('finances:type_bourse_list')


@login_required
def api_calculer_bourse(request):
    """AJAX - Calcule le montant d'une bourse a partir du type et du total du."""
    type_id = request.GET.get('type_bourse')
    total_du_raw = request.GET.get('total_du', '0').replace(',', '.')
    try:
        total_du = Decimal(total_du_raw)
    except (InvalidOperation, ValueError):
        total_du = Decimal('0')

    try:
        tb = TypeBourse.objects.get(pk=type_id)
    except TypeBourse.DoesNotExist:
        return JsonResponse({'montant': '0'})

    if tb.type_reduction == TypeReduction.POURCENTAGE:
        montant = (total_du * tb.valeur_reduction / 100).quantize(Decimal('1'))
    else:
        montant = min(tb.valeur_reduction, total_du)

    return JsonResponse({
        'montant': str(montant),
        'type_reduction': tb.type_reduction,
        'valeur': str(tb.valeur_reduction),
        'description': tb.description,
    })
