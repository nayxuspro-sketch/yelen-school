"""Vues de gestion des salaires, paie mensuelle, congés et absences du personnel."""
import logging
from datetime import date as date_module

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from urllib.parse import quote

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.utils import get_etablissement_context
from licences.decorators import requires_licence_feature
from parametres.models import AnneeScolaire

from ..forms import (AbsencePersonnelForm, CongePersonnelForm, ObservationAbsenceForm, SalairePersonnelForm)
from ..models import AbsencePersonnel, CongePersonnel, MembrePersonnel, ObservationAbsence, SalairePersonnel
from ..selectors import (
    absences_visibles, cycles_accessibles, filtrer_par_membres_visibles,
    membres_dans_cycle, membres_visibles,
)
from yelen_school.cycle_filter import get_cycle_ids

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# SALAIRES
# ═══════════════════════════════════════════════════════════════════

@login_required
@requires_licence_feature('gestion_personnel')
def salaire_list(request):
    """Liste des bulletins de salaire de l'établissement."""
    etab = getattr(request.user, 'etablissement', None)
    qs = SalairePersonnel.objects.select_related('personnel', 'annee_scolaire')
    if etab:
        qs = qs.filter(personnel__etablissement=etab)
    qs = filtrer_par_membres_visibles(qs, request)

    mois_filtre = request.GET.get('mois', '')
    annee_filtre = request.GET.get('annee', str(date_module.today().year))
    statut_filtre = request.GET.get('statut', '')
    personnel_id = request.GET.get('personnel', '')

    if mois_filtre:
        qs = qs.filter(mois=mois_filtre)
    if annee_filtre:
        qs = qs.filter(annee=annee_filtre)
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if personnel_id:
        qs = qs.filter(personnel__pk=personnel_id)

    context = {
        'salaires': qs,
        'mois_filtre': mois_filtre,
        'annee_filtre': annee_filtre,
        'statut_filtre': statut_filtre,
        'mois_choices': SalairePersonnel.MOIS_CHOICES,
        'statut_choices': SalairePersonnel.StatutChoices.choices,
        'annee_courante': date_module.today().year,
    }
    return render(request, 'personnel/salaire_list.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def salaire_create(request, pk=None):
    """Créer un bulletin de salaire (pour un membre spécifique ou depuis la liste)."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(membres_visibles(request), pk=pk) if pk else None
    cycle_ids = get_cycle_ids(request)

    today = date_module.today()
    annee_courante = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    initial = {
        'annee': today.year,
        'mois': today.month,
        'annee_scolaire': annee_courante,
    }
    if membre:
        initial['personnel'] = membre
        # Pré-calculer la prime d'ancienneté si salaire_base disponible
        dernier = SalairePersonnel.objects.filter(personnel=membre).order_by('-annee', '-mois').first()
        if dernier:
            initial['salaire_base'] = dernier.salaire_base
            initial['indemnite_transport'] = dernier.indemnite_transport
            initial['indemnite_logement'] = dernier.indemnite_logement
            initial['prime_anciennete'] = SalairePersonnel.calculer_prime_anciennete(
                membre, dernier.salaire_base
            )

    if request.method == 'POST':
        form = SalairePersonnelForm(request.POST, etablissement=etab, cycles_autorises=cycle_ids)
        if form.is_valid():
            salaire = form.save(commit=False)
            salaire.created_by = request.user
            salaire.save()
            messages.success(
                request,
                f"Bulletin de salaire de {salaire.personnel.get_nom_complet()} "
                f"({salaire.get_mois_display()} {salaire.annee}) enregistré."
            )
            return redirect('personnel:salaire_detail', pk=salaire.pk)
    else:
        form = SalairePersonnelForm(initial=initial, etablissement=etab, cycles_autorises=cycle_ids)

    return render(request, 'personnel/salaire_form.html', {
        'form': form,
        'membre': membre,
        'titre': 'Nouveau bulletin de salaire',
    })


@login_required
@requires_licence_feature('gestion_personnel')
def salaire_detail(request, pk):
    """Détail d'un bulletin de salaire (aperçu + PDF)."""
    salaire = get_object_or_404(
        filtrer_par_membres_visibles(
            SalairePersonnel.objects.select_related('personnel', 'annee_scolaire', 'created_by'), request,
        ),
        pk=pk,
    )
    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(salaire.personnel.etablissement, request)

    context = {'salaire': salaire, **etab_context}

    if request.GET.get('format') == 'pdf':
        try:
            from core.pdf import HTML
            from django.template.loader import render_to_string
            html_str = render_to_string('personnel/pdf/bulletin_salaire.html', context, request=request)
            pdf = HTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()
            nom = f"{salaire.personnel.nom}_{salaire.personnel.prenom}".replace(' ', '_')
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'inline; filename="salaire_{nom}_{salaire.mois:02d}_{salaire.annee}.pdf"'
            )
            return response
        except ImportError:
            messages.error(request, "WeasyPrint n'est pas installé.")

    return render(request, 'personnel/salaire_detail.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def salaire_update(request, pk):
    """Modifier un bulletin de salaire (seulement si BROUILLON)."""
    salaire = get_object_or_404(
        filtrer_par_membres_visibles(SalairePersonnel.objects.select_related('personnel'), request), pk=pk,
    )
    if salaire.statut != SalairePersonnel.StatutChoices.BROUILLON:
        messages.error(request, "Seuls les bulletins en brouillon peuvent être modifiés.")
        return redirect('personnel:salaire_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    cycle_ids = get_cycle_ids(request)
    if request.method == 'POST':
        form = SalairePersonnelForm(
            request.POST, instance=salaire, etablissement=etab, cycles_autorises=cycle_ids,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Bulletin mis à jour.")
            return redirect('personnel:salaire_detail', pk=pk)
    else:
        form = SalairePersonnelForm(
            instance=salaire, etablissement=etab, cycles_autorises=cycle_ids,
        )

    return render(request, 'personnel/salaire_form.html', {
        'form': form,
        'salaire': salaire,
        'titre': 'Modifier le bulletin de salaire',
    })


@login_required
@require_POST
def salaire_valider(request, pk):
    """Passer un bulletin de BROUILLON → VALIDE."""
    salaire = get_object_or_404(
        filtrer_par_membres_visibles(SalairePersonnel.objects.select_related('personnel'), request), pk=pk,
    )
    if salaire.statut == SalairePersonnel.StatutChoices.BROUILLON:
        salaire.statut = SalairePersonnel.StatutChoices.VALIDE
        salaire.save(update_fields=['statut'])
        messages.success(request, "Bulletin validé.")
    return redirect('personnel:salaire_detail', pk=pk)


@login_required
@require_POST
def salaire_payer(request, pk):
    """Passer un bulletin de VALIDE → PAYE."""
    salaire = get_object_or_404(
        filtrer_par_membres_visibles(SalairePersonnel.objects.select_related('personnel'), request), pk=pk,
    )
    if salaire.statut == SalairePersonnel.StatutChoices.VALIDE:
        salaire.statut = SalairePersonnel.StatutChoices.PAYE
        salaire.date_paiement = date_module.today()
        salaire.reference_paiement = request.POST.get('reference_paiement', '')
        salaire.save(update_fields=['statut', 'date_paiement', 'reference_paiement'])
        messages.success(request, "Paiement enregistré.")
    return redirect('personnel:salaire_detail', pk=pk)


@login_required
@require_POST
def salaire_delete(request, pk):
    """Supprimer un bulletin (seulement BROUILLON)."""
    salaire = get_object_or_404(
        filtrer_par_membres_visibles(SalairePersonnel.objects.select_related('personnel'), request), pk=pk,
    )
    if salaire.statut != SalairePersonnel.StatutChoices.BROUILLON:
        messages.error(request, "Seuls les bulletins en brouillon peuvent être supprimés.")
        return redirect('personnel:salaire_detail', pk=pk)
    membre_pk = salaire.personnel.pk
    salaire.delete()
    messages.success(request, "Bulletin supprimé.")
    return redirect('personnel:detail', pk=membre_pk)


# ═══════════════════════════════════════════════════════════════════
# CONGÉS
# ═══════════════════════════════════════════════════════════════════

@login_required
@requires_licence_feature('gestion_personnel')
def conge_list(request):
    """Liste des congés de l'établissement."""
    etab = getattr(request.user, 'etablissement', None)
    qs = CongePersonnel.objects.select_related('personnel', 'approuve_par')
    if etab:
        qs = qs.filter(personnel__etablissement=etab)
    qs = filtrer_par_membres_visibles(qs, request)

    statut_filtre = request.GET.get('statut', '')
    type_filtre = request.GET.get('type', '')
    personnel_id = request.GET.get('personnel', '')

    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if type_filtre:
        qs = qs.filter(type_conge=type_filtre)
    if personnel_id:
        qs = qs.filter(personnel__pk=personnel_id)

    context = {
        'conges': qs,
        'statut_filtre': statut_filtre,
        'type_filtre': type_filtre,
        'statut_choices': CongePersonnel.StatutChoices.choices,
        'type_choices': CongePersonnel.TypeCongeChoices.choices,
        'annee_courante': date_module.today().year,
    }
    return render(request, 'personnel/conge_list.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def conge_create(request, pk=None):
    """Créer une demande de congé."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(membres_visibles(request), pk=pk) if pk else None
    cycle_ids = get_cycle_ids(request)

    initial = {}
    if membre:
        initial['personnel'] = membre

    if request.method == 'POST':
        form = CongePersonnelForm(request.POST, etablissement=etab, cycles_autorises=cycle_ids)
        if form.is_valid():
            conge = form.save(commit=False)
            conge.created_by = request.user
            conge.save()
            messages.success(
                request,
                f"Congé de {conge.personnel.get_nom_complet()} enregistré "
                f"({conge.nombre_jours} jours ouvrables)."
            )
            if membre:
                return redirect('personnel:detail', pk=membre.pk)
            return redirect('personnel:conge_list')
    else:
        form = CongePersonnelForm(initial=initial, etablissement=etab, cycles_autorises=cycle_ids)

    annee = date_module.today().year
    jours_info = None
    if membre:
        jours_info = {
            'pris': CongePersonnel.jours_pris_annee(membre, annee),
            'restants': CongePersonnel.jours_restants(membre, annee),
            'droits': CongePersonnel.DROITS_ANNUELS,
            'annee': annee,
        }

    return render(request, 'personnel/conge_form.html', {
        'form': form,
        'membre': membre,
        'jours_info': jours_info,
        'titre': 'Nouvelle demande de congé',
    })


@login_required
@require_POST
def conge_approuver(request, pk):
    """Approuver une demande de congé dans un cycle accessible."""
    conge = get_object_or_404(
        filtrer_par_membres_visibles(CongePersonnel.objects.select_related('personnel'), request), pk=pk,
    )
    directeurs = membres_visibles(
        request,
        MembrePersonnel.objects.filter(
            etablissement=conge.personnel.etablissement, est_directeur=True, is_active=True,
        ),
    )
    directeur = directeurs.first()

    conge.statut = CongePersonnel.StatutChoices.APPROUVE
    conge.date_approbation = date_module.today()
    conge.approuve_par = directeur
    conge.save(update_fields=['statut', 'date_approbation', 'approuve_par'])
    messages.success(request, f"Congé de {conge.personnel.get_nom_complet()} approuvé.")
    return redirect('personnel:detail', pk=conge.personnel.pk)


@login_required
@requires_licence_feature('gestion_personnel')
def conge_autorisation_pdf(request, pk):
    """Génère le PDF d'autorisation de jouissance de congé."""
    conge = get_object_or_404(
        filtrer_par_membres_visibles(
            CongePersonnel.objects.select_related(
                'personnel', 'personnel__etablissement', 'approuve_par'
            ), request,
        ),
        pk=pk,
    )
    etab = conge.personnel.etablissement

    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(etab, request)
    identite = etab_context.get('identite')

    # ── Signataire configuré ──────────────────────────────────────
    from parametres.models import TypeDocument, SignataireDocument, AnneeScolaire
    type_doc, _ = TypeDocument.objects.get_or_create(
        code='CONGE_PERSONNEL',
        defaults={
            'libelle': 'Autorisation de Congé Personnel',
            'categorie': 'PERSONNEL',
            'actif': True,
        }
    )
    annee_courante = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first()
    signataire = SignataireDocument.objects.get_signataire(
        cycle=None,
        type_document=type_doc,
        annee_scolaire=annee_courante,
    )
    sig_membre = signataire.get_membre_personnel() if signataire else None

    # ── URLs signature et cachet (depuis IdentiteEtablissement) ──
    signature_url = None
    cachet_url = None
    if identite:
        if identite.signature_directeur:
            signature_url = request.build_absolute_uri(identite.signature_directeur.url)
        if identite.cachet_etablissement:
            cachet_url = request.build_absolute_uri(identite.cachet_etablissement.url)

    context = {
        'conge': conge,
        'today': date_module.today(),
        'signataire': signataire,
        'sig_membre': sig_membre,
        'signature_url': signature_url,
        'cachet_url': cachet_url,
        **etab_context,
    }

    try:
        from core.pdf import HTML
        from django.template.loader import render_to_string
        html_str = render_to_string(
            'personnel/pdf/autorisation_conge.html', context, request=request
        )
        pdf = HTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()
        nom = f"{conge.personnel.nom}_{conge.personnel.prenom}".replace(' ', '_')
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="autorisation_conge_{nom}.pdf"'
        )
        return response
    except ImportError:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('personnel:detail', pk=conge.personnel.pk)


@login_required
@require_POST
def conge_refuser(request, pk):
    """Refuser une demande de congé dans un cycle accessible."""
    conge = get_object_or_404(
        filtrer_par_membres_visibles(CongePersonnel.objects.select_related('personnel'), request), pk=pk,
    )
    directeurs = membres_visibles(
        request,
        MembrePersonnel.objects.filter(
            etablissement=conge.personnel.etablissement, est_directeur=True, is_active=True,
        ),
    )
    directeur = directeurs.first()

    conge.statut = CongePersonnel.StatutChoices.REFUSE
    conge.date_approbation = date_module.today()
    conge.approuve_par = directeur
    conge.observations = request.POST.get('motif_refus', conge.observations)
    conge.save(update_fields=['statut', 'date_approbation', 'approuve_par', 'observations'])
    messages.success(request, f"Congé de {conge.personnel.get_nom_complet()} refusé.")
    return redirect('personnel:detail', pk=conge.personnel.pk)



# ─── PAIE DU MOIS ──────────────────────────────────────────────────────

def _mois_annee(source):
    """(mois, année) demandés — par défaut le mois courant."""
    today = date_module.today()
    try:
        mois = int(source.get('mois', today.month))
    except (TypeError, ValueError):
        mois = today.month
    try:
        annee = int(source.get('annee', today.year))
    except (TypeError, ValueError):
        annee = today.year
    return (mois if 1 <= mois <= 12 else today.month), annee


def _url_paie(mois, annee):
    from django.urls import reverse
    return f"{reverse('personnel:paie_mois')}?mois={mois}&annee={annee}"


@login_required
@requires_licence_feature('gestion_personnel')
def paie_mois(request):
    """Paie du mois : bulletins du mois (statuts, totaux), agents sans bulletin, préparation et validation en masse,
    livre de paie et bulletins en lot."""
    from .. import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.GET)
    contexte = paie.livre(etab, mois, annee, request=request) if etab else {'salaires': [], 'sans_bulletin': [], 'totaux': {},
                                                            'par_statut': {}, 'mois': mois, 'annee': annee,
                                                            'libelle_mois': paie.MOIS[mois]}
    contexte.update({'mois_choices': SalairePersonnel.MOIS_CHOICES, 'annee_courante': date_module.today().year,
                     'annees': range(date_module.today().year - 3, date_module.today().year + 2)})
    return render(request, 'personnel/paie_mois.html', contexte)


@login_required
@require_POST
@requires_licence_feature('gestion_personnel')
def paie_preparer(request):
    """Crée les brouillons du mois pour tous les agents permanents sans bulletin."""
    from .. import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.POST)
    annee_scolaire = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    if etab is None or annee_scolaire is None:
        messages.error(request, "Aucune année scolaire courante : la paie ne peut pas être préparée.")
        return redirect(_url_paie(mois, annee))
    crees, sans_reference = paie.preparer(etab, mois, annee, annee_scolaire, request.user, request=request)
    texte = f"{len(crees)} bulletin{'s' if len(crees) > 1 else ''} de {paie.MOIS[mois]} {annee} préparé{'s' if len(crees) > 1 else ''} en brouillon."
    if sans_reference:
        texte += (f" {len(sans_reference)} agent{'s' if len(sans_reference) > 1 else ''} sans bulletin de référence à saisir "
                  f"à la main : {', '.join(m.get_nom_complet() for m in sans_reference[:5])}"
                  f"{'…' if len(sans_reference) > 5 else ''}.")
    messages.success(request, texte)
    return redirect(_url_paie(mois, annee))


@login_required
@require_POST
@requires_licence_feature('gestion_personnel')
def paie_valider(request):
    """Valide tous les brouillons du mois."""
    from .. import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.POST)
    nb = paie.valider_brouillons(etab, mois, annee, request=request) if etab else 0
    messages.success(request, f"{nb} bulletin{'s' if nb > 1 else ''} validé{'s' if nb > 1 else ''}." if nb else "Aucun brouillon à valider.")
    return redirect(_url_paie(mois, annee))


@login_required
@requires_licence_feature('gestion_personnel')
def livre_paie_pdf(request):
    """Livre de paie du mois (A4 paysage) : une ligne par agent, totaux, signataire."""
    from core.pdf import HTML
    from .. import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.GET)
    if etab is None:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('personnel:salaire_list')
    contexte = {
        **paie.livre(etab, mois, annee, request=request),
        **get_etablissement_context(etab, request), 'now': timezone.now(),
    }
    html_str = render_to_string('personnel/pdf/livre_paie.html', contexte, request=request)
    pdf = HTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="livre_paie_{annee}_{mois:02d}.pdf"'
    return response


@login_required
@requires_licence_feature('gestion_personnel')
def bulletins_paie_lot_pdf(request):
    """Tous les bulletins de salaire du mois dans un seul PDF (un bulletin par page, même gabarit que l'unitaire)."""
    from core.pdf import HTML
    from .. import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.GET)
    if etab is None:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('personnel:salaire_list')
    etab_context = get_etablissement_context(etab, request)
    fragments = [
        render_to_string('personnel/pdf/bulletin_salaire.html', {'salaire': salaire, **etab_context}, request=request)
        for salaire in paie.salaires_du_mois(etab, mois, annee, request=request)
    ]
    pdf = HTML.lot(fragments, base_url=request.build_absolute_uri('/'))
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="bulletins_salaire_{annee}_{mois:02d}.pdf"'
    return response


# ═══════════════════════════════════════════════════════════════════
# ABSENCES DU PERSONNEL
# ═══════════════════════════════════════════════════════════════════

def _mois_demande(request):
    """(mois, année) du paramètre ``mois=AAAA-MM`` ; mois courant par défaut."""
    valeur = request.GET.get('mois', '')
    try:
        annee, mois = (int(v) for v in valeur.split('-'))
        if not 1 <= mois <= 12:
            raise ValueError
        return mois, annee
    except (TypeError, ValueError):
        today = date_module.today()
        return today.month, today.year


def _date_parametre(valeur):
    """Date ``AAAA-MM-JJ`` d'un paramètre d'URL, ou ``None`` si elle est absente ou illisible."""
    from datetime import datetime
    try:
        return datetime.strptime((valeur or '').strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def _periode_demandee(request):
    """Intervalle imprimé/affiché : ``du``/``au`` s'ils sont saisis, sinon le mois ``AAAA-MM``."""
    du, au = _date_parametre(request.GET.get('du')), _date_parametre(request.GET.get('au'))
    if du or au:
        du, au = du or au, au or du
        return min(du, au), max(du, au)
    import calendar
    mois, annee = _mois_demande(request)
    return date_module(annee, mois, 1), date_module(annee, mois, calendar.monthrange(annee, mois)[1])


def _bilan_absences(etab, debut, fin, request=None):
    """Bilan des absences de la période, limité aux agents et cycles autorisés."""
    lignes = {}
    absences = AbsencePersonnel.objects.filter(
        personnel__etablissement=etab, date_debut__lte=fin, date_fin__gte=debut,
    )
    if request is not None:
        absences = absences_visibles(absences, request)
    for a in absences.select_related('personnel').order_by('personnel__nom', 'personnel__prenom'):
        ligne = lignes.setdefault(a.personnel_id, {'membre': a.personnel, 'absences': 0, 'jours': 0, 'non_justifies': 0, 'retenus': 0})
        jours = (min(a.date_fin, fin) - max(a.date_debut, debut)).days + 1
        ligne['absences'] += 1
        ligne['jours'] += jours
        if not a.justifiee:
            ligne['non_justifies'] += jours
            if a.retenue:
                ligne['retenus'] += jours
    return list(lignes.values())


def _absences_de_la_periode(request, etab):
    """Absences de la période demandée (et de l'agent filtré), avec le bilan par agent sur la même période."""
    debut, fin = _periode_demandee(request)
    qs = AbsencePersonnel.objects.filter(personnel__etablissement=etab)
    qs = absences_visibles(qs, request).select_related(
        'personnel', 'created_by', 'classe', 'matiere'
    ).order_by('-date_debut', 'personnel__nom')
    membre_id = request.GET.get('personnel')
    membres = membres_visibles(request, MembrePersonnel.objects.filter(etablissement=etab))
    membre = membres.filter(pk=membre_id).first() if membre_id else None
    if membre_id:
        qs = qs.filter(personnel=membre) if membre else qs.none()
    # Intervalle explicitement demandé, ou aucune période : bornes appliquées. Un agent choisi sans bornes garde
    # son historique complet (comportement de la fiche).
    if membre is None or request.GET.get('du') or request.GET.get('au'):
        qs = qs.filter(date_debut__lte=fin, date_fin__gte=debut)
    return qs, membre, debut, fin, _bilan_absences(etab, debut, fin, request=request)


@login_required
def absence_list(request):
    """Absences du personnel : liste du mois ou d'un intervalle de dates, et bilan par agent."""
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_demande(request)
    if etab:
        qs, membre, debut, fin, bilan = _absences_de_la_periode(request, etab)
    else:
        qs, membre, debut, fin, bilan = AbsencePersonnel.objects.none(), None, None, None, []
    parametres = request.GET.copy()
    parametres.pop('format', None)
    parametres['format'] = 'pdf'
    return render(request, 'personnel/absence_list.html', {
        'absences': qs[:300], 'bilan': bilan, 'membre': membre,
        'mois_param': f"{annee:04d}-{mois:02d}", 'mois_libelle': date_module(annee, mois, 1),
        'periode': {'debut': debut, 'fin': fin, 'du': request.GET.get('du', ''), 'au': request.GET.get('au', '')},
        'lien_impression': f"{reverse('personnel:absence_pdf')}?{parametres.urlencode()}",
    })


@login_required
def absence_pdf(request):
    """Impression des absences d'une période (`du`/`au` ou mois), avec le bilan par agent. A4 portrait signé."""
    from core.pdf import HTML as WeasyPrint

    etab = getattr(request.user, 'etablissement', None)
    qs, membre, debut, fin, bilan = _absences_de_la_periode(request, etab) if etab else (
        AbsencePersonnel.objects.none(), None, None, None, [])
    absences = list(qs[:500])
    contexte = {
        'absences': absences, 'bilan': bilan, 'membre': membre, 'debut': debut, 'fin': fin,
        'total_heures': round(sum(a.nombre_heures for a in absences), 2),
        'etablissement': etab, 'today': date_module.today(),
        # Un agent choisi sans bornes garde son historique complet : l'en-tête ne borne pas la période.
        'periode_bornee': bool(request.GET.get('du') or request.GET.get('au')) or membre is None,
        'annee_scolaire': (AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
                           if etab else None),
        **get_etablissement_context(etab, request),
    }
    html = render_to_string('personnel/pdf/absences_periode.html', contexte, request=request)
    pdf = WeasyPrint(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="absences_{debut:%Y%m%d}_{fin:%Y%m%d}.pdf"'
    return response


@login_required
def absence_create(request, pk=None):
    """Enregistrer une absence (depuis la liste ou la fiche de l'agent).

    Le **cycle** restreint la liste des agents (primaire, post-prinaire / secondaire) ; l'**observation** se
    choisit dans une liste déroulante que le bouton « + » du formulaire permet de compléter (5.57.0).
    """
    etab = getattr(request.user, 'etablissement', None)
    cycle_ids = get_cycle_ids(request)
    membres = membres_visibles(request, MembrePersonnel.objects.filter(etablissement=etab))
    membre = get_object_or_404(membres, pk=pk) if pk else None
    cycle = _cycle_demande(request, etab)
    if membre and cycle is not None:
        get_object_or_404(membres_dans_cycle(membres, cycle), pk=membre.pk)
    if request.method == 'POST':
        form = AbsencePersonnelForm(
            request.POST, etablissement=etab, cycle=cycle, cycles_autorises=cycle_ids,
        )
        if membre:
            form.fields['personnel'].queryset = form.fields['personnel'].queryset.filter(pk=membre.pk)
        if form.is_valid():
            absence = form.save(commit=False)
            absence.created_by = request.user
            absence.save()
            messages.success(request, f"Absence de {absence.personnel.get_nom_complet()} enregistrée "
                                      f"({absence.nombre_jours} jour(s){', retenue proposée sur la paie' if absence.a_retenir else ''}).")
            return redirect('personnel:detail', pk=membre.pk) if membre else redirect('personnel:absence_list')
    else:
        observation = request.GET.get('observation') or ''
        classe = request.GET.get('classe') or ''
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first() if etab else None
        initial = {'personnel': membre, 'date': date_module.today(), 'classe': classe}
        if observation:
            initial['observation'] = observation
        form = AbsencePersonnelForm(
            initial=initial, etablissement=etab, cycle=cycle, annee_scolaire=annee,
            cycles_autorises=cycle_ids,
        )
        if membre:
            form.fields['personnel'].queryset = form.fields['personnel'].queryset.filter(pk=membre.pk)
    return render(request, 'personnel/absence_form.html', {
        'form': form, 'membre': membre, 'titre': "Saisie des absences quotidiennes des professeurs",
        'cycle': cycle,
        'cycles': cycles_accessibles(request, etab).order_by('ordre', 'nom'),
        'annee_scolaire': (AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
                           if etab else None),
    })


def _cycle_demande(request, etab):
    """Cycle choisi dans le formulaire d'absence, validé contre les cycles autorisés du compte."""
    valeur = request.POST.get('cycle') or request.GET.get('cycle') or ''
    if not valeur:
        return None
    return cycles_accessibles(request, etab).filter(pk=valeur).first()


@login_required
@requires_licence_feature('gestion_personnel')
def observation_absence_create(request):
    """Ajoute une observation manquante au champ déroulant du formulaire d'absence, puis y revient (5.57.0)."""
    etab = getattr(request.user, 'etablissement', None)
    if request.method == 'POST':
        form = ObservationAbsenceForm(request.POST)
        if form.is_valid():
            observation = form.save(commit=False)
            observation.etablissement = etab
            observation.save()
            messages.success(request, f"Observation « {observation.libelle} » ajoutée à la liste.")
            suivant = reverse('personnel:absence_create')
            if request.POST.get('membre'):
                suivant = reverse('personnel:absence_create_pour', args=[request.POST['membre']])
            return redirect(f"{suivant}?observation={quote(observation.libelle)}")
    else:
        form = ObservationAbsenceForm()
    return render(request, 'personnel/observation_absence_form.html', {
        'form': form, 'titre': "Nouvelle observation d'absence",
        'membre': request.GET.get('membre') or '', 'cycle': request.GET.get('cycle') or '',
        'observations': ObservationAbsence.disponibles(etab),
    })


@login_required
@require_POST
@requires_licence_feature('gestion_personnel')
def absence_delete(request, pk):
    etab = getattr(request.user, 'etablissement', None)
    absences = absences_visibles(AbsencePersonnel.objects.select_related('personnel', 'classe'), request)
    if etab is not None:
        absences = absences.filter(personnel__etablissement=etab)
    absence = get_object_or_404(absences, pk=pk)
    membre_id = absence.personnel_id
    absence.delete()
    messages.success(request, "Absence supprimée.")
    suivant = request.POST.get('suivant')
    return redirect('personnel:detail', pk=membre_id) if suivant == 'fiche' else redirect('personnel:absence_list')
