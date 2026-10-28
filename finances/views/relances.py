"""Relances de paiement (courrier, PDF, SMS) et historique.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import connections, transaction
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal
import io
import threading
from ..models import CanalRelance, HistoriqueRelance
from ..paiements_mobiles import cinetpay_configure, relancer_avec_lien
from ..redevables import inscriptions_relancables, redevables_rubrique
from parametres.models import AnneeScolaire, Classe, ModeleMessage, RubriquePaiement
from core.sms import sms_actifs
from core.tasks import mettre_en_file_lot
from core.utils import get_etablissement_context
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from .commun import WeasyHTML, _require_finance_role

logger = logging.getLogger(__name__)


def _selection(etab, params):
    """(année, classe — None pour « toutes les classes » —, rubrique) de la sélection ; Http404 si un élément
    n'appartient pas à l'établissement."""
    annee = get_object_or_404(AnneeScolaire, pk=params.get('annee'), etablissement=etab)
    rubrique = get_object_or_404(RubriquePaiement, pk=params.get('rubrique'), etablissement=etab)
    classe_id = params.get('classe')
    classe = None if classe_id == 'all' else get_object_or_404(Classe, pk=classe_id, etablissement=etab)
    return annee, classe, rubrique


def _redevables(etab, annee, classe, rubrique):
    """Redevables de la rubrique pour la sélection — même calcul pour le compteur, le PDF et les SMS."""
    return redevables_rubrique(inscriptions_relancables(etab, annee, classe), rubrique)


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
    if not (etab and request.GET.get('annee') and request.GET.get('classe') and request.GET.get('rubrique')):
        return HttpResponse('')
    try:
        annee, classe, rubrique = _selection(etab, request.GET)
    except (Http404, ValueError, ValidationError):
        return HttpResponse('')

    count = len(_redevables(etab, annee, classe, rubrique))

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

    annee, classe, rubrique = _selection(etab, request.GET)
    date_echeance = request.GET.get('date_echeance', '')

    etab_context = get_etablissement_context(etab, request)

    # Signataire : même résolution (avec repli progressif) que les autres documents PDF
    from parametres.models import SignataireDocument, TypeDocument
    signataire = SignataireDocument.objects.get_signataire(
        cycle=classe.cycle if classe else None,
        type_document=TypeDocument.objects.filter(code='RELANCE', actif=True).first(),
        annee_scolaire=annee,
    )
    sig_membre = signataire.get_membre_personnel() if signataire else None

    relances = [{
        'inscription': r.inscription,
        'eleve': r.eleve,
        'classe': r.inscription.classe,
        'montant_du': r.montant_du,
        'verse': r.verse,
        'reste': r.reste,
        'date_echeance': date_echeance or (r.echeance.strftime('%d/%m/%Y') if r.echeance else ''),
    } for r in _redevables(etab, annee, classe, rubrique)]

    html_string = render_to_string('finances/pdf/relance_paiement.html', {
        'relances': relances,
        'annee': annee,
        'classe': classe,
        'rubrique': rubrique,
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'date_impression': timezone.now().strftime('%d/%m/%Y'),
        'signataire': signataire,
        'sig_membre': sig_membre,
    }, request=request)

    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Relances_{classe.nom if classe else 'toutes'}_{rubrique.nom}.pdf".replace(" ", "_")

    # Traçabilité : enregistrer une ligne HistoriqueRelance par élève redevable
    aujourd_hui = timezone.localdate()
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
    """Envoie aux parents des élèves redevables de la rubrique un SMS de relance nominatif : nom de l'élève,
    rubrique et reste à payer de cet élève, au numéro de sa propre fiche (parent, tuteur, puis urgence)."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)

    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:relance_paiement')
    if not sms_actifs():
        messages.error(request, "Envoi de SMS désactivé : activez-le dans Paramètres → SMS avant de relancer.")
        return redirect('finances:relance_paiement')

    annee, classe, rubrique = _selection(etab, request.POST)

    envois, nb_sans_numero = [], 0
    for redevable in _redevables(etab, annee, classe, rubrique):
        eleve = redevable.eleve
        numero = eleve.telephone_parent_valide()
        if not numero:
            nb_sans_numero += 1
            continue
        message = ModeleMessage.get_contenu(etab, 'PAIEMENT', {
            'nom_eleve': eleve.get_nom_complet(),
            'montant': f"{redevable.reste:,.0f}".replace(',', ' '),
            'rubrique': rubrique.nom,
            'etablissement': etab.nom,
        })
        envois.append({'inscription': redevable.inscription, 'rubrique': rubrique, 'montant': redevable.reste,
                       'telephone': numero, 'message': message, 'destinataire': f"{eleve.get_nom_complet()} — {rubrique.nom}"})

    # Avec la passerelle, chaque SMS reçoit un lien de paiement : création des liens hors requête.
    avec_lien = bool(envois) and cinetpay_configure()
    with transaction.atomic():
        for envoi in envois:
            HistoriqueRelance.objects.create(
                inscription=envoi['inscription'], rubrique=rubrique, canal=CanalRelance.SMS,
                montant_reclame=envoi['montant'], envoye_par=request.user, date_relance=timezone.localdate(),
                succes=True, detail=envoi['telephone'], created_by=request.user,
            )
        if envois and not avec_lien:
            # Un SMS par élève, tracé dans le journal SMS au nom de l'élève et de la rubrique
            mettre_en_file_lot([(e['telephone'], e['message'], e['destinataire']) for e in envois])
    if avec_lien:
        _en_arriere_plan(relancer_avec_lien, envois, request.user)

    if envois:
        messages.success(request, f"{len(envois)} SMS de relance envoyé(s)." + (" Lien de paiement en ligne inclus." if avec_lien else ""))
    if nb_sans_numero:
        messages.warning(request, f"{nb_sans_numero} élève(s) sans numéro valide — non contacté(s).")
    if not envois and not nb_sans_numero:
        messages.info(request, "Aucun élève redevable trouvé pour cette sélection.")

    return redirect('finances:relance_paiement')


def _en_arriere_plan(fonction, *args):
    """Exécute ``fonction`` dans un fil dédié (sa connexion à la base est refermée à la fin)."""
    def _executer():
        try:
            fonction(*args)
        finally:
            connections.close_all()
    threading.Thread(target=_executer, daemon=True).start()


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
