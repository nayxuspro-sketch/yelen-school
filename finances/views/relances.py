"""Relances de paiement (courrier, PDF, SMS) et historique.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.template.loader import render_to_string
from decimal import Decimal
import io
from ..models import Paiement
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe, TarifScolarite, RubriquePaiement
from core.utils import get_etablissement_context
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from .commun import WeasyHTML, _numero_valide, _require_finance_role


@login_required
def relance_paiement(request):
    """Sélecteur pour la génération des relances de paiement."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
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
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    annee_id    = request.GET.get('annee')
    classe_id   = request.GET.get('classe')
    rubrique_id = request.GET.get('rubrique')

    if not (annee_id and classe_id and rubrique_id and etab):
        return HttpResponse('')

    try:
        annee = AnneeScolaire.objects.filter(pk=annee_id, etablissement=etab).first()
        rubrique = RubriquePaiement.objects.filter(
            pk=rubrique_id, etablissement=etab
        ).first()
    except (ValueError, ValidationError):
        return HttpResponse('')

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
    _require_finance_role(request, FINANCE_VIEW_ROLES)
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
    from ..models import HistoriqueRelance, CanalRelance
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
        # Ne pas utiliser bulk_create : les signaux d'audit doivent tracer
        # chaque relance et conserver son contexte utilisateur.
        with transaction.atomic():
            for relance in historique_bulk:
                relance.created_by = request.user
                relance.save()

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
@require_POST
def relance_sms(request):
    """Envoie des SMS de relance paiement aux parents des élèves redevables."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
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

        try:
            sms_msg = ModeleMessage.get_contenu(etab, 'PAIEMENT', {
                'nom_eleve': eleve.get_nom_complet(),
                'montant': f"{reste:,.0f}".replace(',', ' '),
                'rubrique': rubrique.nom,
                'etablissement': etab.nom,
            })
        except Exception:
            sms_msg = f"Bonjour, votre enfant {eleve.nom} {eleve.prenom} a un reste à payer de {reste:,.0f} F pour la rubro {rubrique.nom}. Merci de regler au plus vite. {etab.nom}"

        envoyer_sms_async(numero, sms_msg)
        nb_envoyes += 1

        from ..models import HistoriqueRelance, CanalRelance
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
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    from ..models import HistoriqueRelance

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
