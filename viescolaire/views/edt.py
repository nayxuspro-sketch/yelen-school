"""Emploi du temps : configuration, grille par classe et par professeur, génération, PDF."""
import logging
import io
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils.dateparse import parse_time
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)
from django.contrib import messages
from django.views.decorators.http import require_POST

from parametres.models import AnneeScolaire, Classe, Salle, SignataireDocument, TypeDocument
from pedagogie.models import Enseignement
from core.utils import get_etablissement_context
from ..forms import ConfigEDTForm
from ..edt_conflits import conflits_classe, conflits_seance
from ..models import (
    SeanceCours, JourSemaine, ConfigEDT,
)
from .commun import WeasyHTML, _get_etab


def _jours_grille(config, seances):
    """Colonnes de la grille : jours de classe configurés, plus ceux portant déjà des séances."""
    return sorted(set(config.get_jours_actifs()) | {s.jour for s in seances})


@login_required
def edt_config(request):
    """Horaires de cours et jours de classe de l'établissement."""
    etab = _get_etab(request)
    if etab is None:
        return redirect('viescolaire:emploi_du_temps_index')
    config = ConfigEDT.pour(etab)
    form = ConfigEDTForm(request.POST or None, instance=config)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Horaires et jours de classe enregistrés.")
        return redirect('viescolaire:emploi_du_temps_index')
    config = ConfigEDT.pour(etab)  # valeurs effectives : un formulaire invalide ne modifie pas l'aperçu
    return render(request, 'viescolaire/edt_config.html', {
        'form': form, 'config': config, 'creneaux': config.creneaux(),
    })


@login_required
def emploi_du_temps_index(request):
    """Sélecteur de classe pour accéder à l'emploi du temps."""
    etab = _get_etab(request)
    classes = (
        Classe.objects
        .filter(etablissement=etab, actif=True)
        .select_related('cycle')
        .order_by('cycle__ordre', 'cycle__nom', 'nom')
    ) if etab else Classe.objects.none()

    # Grouper par cycle
    cycles = {}
    for c in classes:
        key = c.cycle.pk
        if key not in cycles:
            cycles[key] = {'cycle': c.cycle, 'classes': []}
        cycles[key]['classes'].append(c)

    return render(request, 'viescolaire/emploi_du_temps_index.html', {
        'cycles': sorted(cycles.values(), key=lambda x: x['cycle'].ordre if hasattr(x['cycle'], 'ordre') else 0),
    })


@login_required
def emploi_du_temps(request, classe_id):
    """Grille hebdomadaire des séances de cours d'une classe."""
    etab = _get_etab(request)
    classe = get_object_or_404(Classe, pk=classe_id)

    annee_id = request.GET.get('annee')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    else:
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')

    enseignements = (
        Enseignement.objects
        .filter(classe=classe, annee_scolaire=annee, est_actif=True)
        .select_related('matiere', 'personnel')
        .order_by('matiere__nom')
    ) if annee else Enseignement.objects.none()

    seances = (
        SeanceCours.objects
        .filter(enseignement__in=enseignements)
        .select_related('enseignement__matiere', 'enseignement__personnel')
        .order_by('jour', 'heure_debut')
    )

    # Index couleur par enseignement (8 couleurs en rotation)
    color_map = {ens.pk: i % 8 for i, ens in enumerate(enseignements)}

    # Grille horaire : lignes = créneaux uniques, colonnes = jours de classe configurés
    config = ConfigEDT.pour(etab)
    JOURS = _jours_grille(config, seances)
    jours_labels = [JourSemaine(j).label for j in JOURS]

    slots: dict = {}
    for s in seances:
        key = (s.heure_debut, s.heure_fin)
        slots.setdefault(key, {})[s.jour] = s

    grille_creneaux = [
        {
            'heure_debut': hd,
            'heure_fin': hf,
            'jours': [
                {
                    'seance': slot_jours.get(j),
                    'color_idx': color_map.get(slot_jours[j].enseignement_id, 0)
                    if j in slot_jours else None,
                }
                for j in JOURS
            ],
        }
        for (hd, hf), slot_jours in sorted(slots.items())
    ]

    enseignements_avec_couleur = [
        (ens, i % 8) for i, ens in enumerate(enseignements)
    ]
    conflits = conflits_classe(classe, annee)

    return render(request, 'viescolaire/emploi_du_temps.html', {
        'classe': classe,
        'annee': annee,
        'annees': annees,
        'enseignements': enseignements,
        'enseignements_avec_couleur': enseignements_avec_couleur,
        'grille_creneaux': grille_creneaux,
        'jours_labels': jours_labels,
        'jours_choices': config.jours_choices(),
        'config': config,
        'conflits': conflits,
        'salles': Salle.objects.filter(etablissement=etab, actif=True) if etab else Salle.objects.none(),
    })


@login_required
@require_POST
def seance_create(request, classe_id):
    """Ajoute une séance de cours (HTMX POST)."""
    etab = _get_etab(request)
    classe = get_object_or_404(Classe, pk=classe_id)

    annee_id = request.POST.get('annee')
    annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)

    enseignement_id = request.POST.get('enseignement')
    enseignement = get_object_or_404(
        Enseignement, pk=enseignement_id, classe=classe, annee_scolaire=annee
    )

    jour = request.POST.get('jour', '').strip()
    heure_debut = request.POST.get('heure_debut', '').strip()
    heure_fin = request.POST.get('heure_fin', '').strip()
    salle = Salle.canonique(etab, request.POST.get('salle', ''))

    heure_debut, heure_fin = parse_time(heure_debut), parse_time(heure_fin)
    if not (jour.isdigit() and heure_debut and heure_fin):
        return HttpResponse("Jour, heure de début et heure de fin sont obligatoires.", status=400)

    if heure_fin <= heure_debut:
        return HttpResponse("L'heure de fin doit être postérieure à l'heure de début.", status=400)

    from django.urls import reverse
    url = reverse('viescolaire:emploi_du_temps', kwargs={'classe_id': classe.pk})
    config = ConfigEDT.pour(etab)
    if int(jour) not in config.get_jours_actifs():
        libelle = dict(JourSemaine.choices).get(int(jour), f"Le jour {jour}")
        messages.error(request, f"{libelle} n'est pas un jour de classe configuré.")
        return redirect(f"{url}?annee={annee.pk}")
    if not config.couvre(heure_debut, heure_fin):
        messages.error(request, f"Horaire hors des heures de cours configurées ({config.plages_libelle()}).")
        return redirect(f"{url}?annee={annee.pk}")

    conflits = conflits_seance(enseignement, int(jour), heure_debut, heure_fin, salle)
    if conflits:
        messages.error(request, "Séance non ajoutée : " + " ; ".join(conflits) + ".")
        return redirect(f"{url}?annee={annee.pk}")

    try:
        SeanceCours.objects.create(
            enseignement=enseignement,
            jour=int(jour),
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            salle=salle,
        )
    except IntegrityError:
        messages.error(request, "Une séance existe déjà pour ce créneau (même matière, même jour, même heure).")
        return redirect(f"{url}?annee={annee.pk}")

    depassement = _depassement_capacite(etab, salle, classe, annee)
    if depassement:
        messages.warning(request, depassement)
    return redirect(f"{url}?annee={annee.pk}")


def _depassement_capacite(etab, salle, classe, annee):
    """Avertissement si l'effectif de la classe dépasse la capacité déclarée de la salle ; '' sinon."""
    from inscriptions.models import Inscription, StatutInscriptionChoices
    if not salle or etab is None:
        return ''
    fiche = Salle.objects.filter(etablissement=etab, nom=salle, capacite__isnull=False).first()
    if fiche is None:
        return ''
    effectif = (Inscription.objects.filter(classe=classe, annee_scolaire=annee)
                .exclude(statut=StatutInscriptionChoices.ABANDON).count())
    if effectif <= fiche.capacite:
        return ''
    return (f"Attention : la salle {fiche.nom} compte {fiche.capacite} places pour {effectif} élèves en {classe.nom} "
            f"(séance ajoutée malgré tout).")


@login_required
def occupation_salles(request):
    """Occupation hebdomadaire des salles : une ligne par salle (référentiel et salles saisies à la main), une
    colonne par jour de classe, les séances de l'année dans chaque case — pour trouver une salle libre."""
    etab = _get_etab(request)
    annee_id = request.GET.get('annee')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    else:
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    config = ConfigEDT.pour(etab)
    jours = config.get_jours_actifs()
    labels = dict(JourSemaine.choices)
    seances = (
        SeanceCours.objects
        .filter(enseignement__annee_scolaire=annee, enseignement__classe__etablissement=etab, enseignement__est_actif=True)
        .exclude(salle='')
        .select_related('enseignement__classe', 'enseignement__matiere')
        .order_by('salle', 'jour', 'heure_debut')
    ) if (annee and etab) else SeanceCours.objects.none()
    fiches = {s.nom: s for s in Salle.objects.filter(etablissement=etab)} if etab else {}
    lignes = {}
    for nom in fiches:
        lignes[nom] = {'nom': nom, 'fiche': fiches[nom], 'jours': {j: [] for j in jours}, 'nb': 0, 'heures': 0.0}
    for s in seances:
        ligne = lignes.setdefault(s.salle, {'nom': s.salle, 'fiche': fiches.get(s.salle), 'jours': {j: [] for j in jours},
                                            'nb': 0, 'heures': 0.0})
        if s.jour in ligne['jours']:
            ligne['jours'][s.jour].append(s)
        ligne['nb'] += 1
        ligne['heures'] += (datetime.combine(datetime.min, s.heure_fin) - datetime.combine(datetime.min, s.heure_debut)).total_seconds() / 3600
    for ligne in lignes.values():
        ligne['cases'] = [ligne['jours'][j] for j in jours]
        ligne['heures'] = round(ligne['heures'], 2)
    return render(request, 'viescolaire/occupation_salles.html', {
        'annee': annee,
        'annees': AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else [],
        'jours_labels': [labels[j] for j in jours],
        'lignes': sorted(lignes.values(), key=lambda l: l['nom'].casefold()),
    })


@login_required
@require_POST
def seance_delete(request, seance_id):
    """Retire une séance de cours, puis revient à la grille d'origine (classe, ou professeur si ``retour=prof``)."""
    from django.urls import reverse
    seance = get_object_or_404(
        SeanceCours.objects.select_related('enseignement__matiere', 'enseignement__classe'),
        pk=seance_id, enseignement__classe__etablissement=_get_etab(request),
    )
    enseignement = seance.enseignement
    seance.delete()
    messages.success(request, f"Séance retirée : {enseignement.matiere.nom} — {JourSemaine(seance.jour).label} "
                              f"{seance.heure_debut:%H:%M}–{seance.heure_fin:%H:%M} ({enseignement.classe.nom}).")
    if request.POST.get('retour') == 'prof' and enseignement.personnel_id:
        url = reverse('viescolaire:emploi_du_temps_prof', kwargs={'personnel_id': enseignement.personnel_id})
    else:
        url = reverse('viescolaire:emploi_du_temps', kwargs={'classe_id': enseignement.classe_id})
    return redirect(f"{url}?annee={enseignement.annee_scolaire_id}")


@login_required
def edt_generer(request, classe_id):
    """Génération automatique d'EDT — formulaire, aperçu et application."""
    import json as _json
    from ..services import GenerateurEDT

    etab = _get_etab(request)
    classe = get_object_or_404(Classe, pk=classe_id)

    annee_id = request.GET.get('annee') or request.POST.get('annee')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    else:
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()

    # Sans configuration enregistrée, le générateur garde ses créneaux par défaut (pause de 10 h incluse).
    config = ConfigEDT.objects.filter(etablissement=etab).first()

    if request.method == 'GET':
        return render(request, 'viescolaire/partials/edt_generation_form.html', {
            'classe': classe,
            'annee': annee,
            'config': config,
        })

    action = request.POST.get('action', 'preview')
    mode = request.POST.get('mode', 'remplacer')

    if action == 'preview':
        gen = GenerateurEDT(classe, annee, config)
        resultat = gen.generer()
        request.session[f'edt_preview_{classe.pk}'] = resultat.to_json()
        return render(request, 'viescolaire/partials/edt_apercu.html', {
            'classe': classe,
            'annee': annee,
            'resultat': resultat,
            'mode': mode,
        })

    if action == 'appliquer':
        seances_data = []
        try:
            raw = request.session.pop(f'edt_preview_{classe.pk}', '[]')
            seances_data = _json.loads(raw)
        except (ValueError, TypeError):
            pass

        if mode == 'remplacer':
            SeanceCours.objects.filter(
                enseignement__classe=classe,
                enseignement__annee_scolaire=annee,
            ).delete()

        ignorees = []
        for s in seances_data:
            try:
                ens = Enseignement.objects.select_related('classe').get(pk=s['enseignement_id'], classe=classe)
                hd, hf = parse_time(s['heure_debut']), parse_time(s['heure_fin'])
                conflits = conflits_seance(ens, s['jour'], hd, hf)
                if conflits:   # créneau pris entre-temps, ou mode « compléter » : on ne crée jamais un chevauchement
                    ignorees.append(f"{ens.matiere.nom} ({conflits[0]})")
                    continue
                SeanceCours.objects.get_or_create(
                    enseignement=ens,
                    jour=s['jour'],
                    heure_debut=hd,
                    defaults={'heure_fin': hf},
                )
            except (IntegrityError, ValidationError):
                logger.exception("Génération EDT : séance non créée (enseignement %s)", s.get('enseignement_id'))
        if ignorees:
            messages.error(request, f"{len(ignorees)} séance(s) non placée(s) pour éviter un conflit : "
                                    + " ; ".join(ignorees[:5]) + ("…" if len(ignorees) > 5 else "") + ".")

        return HttpResponse('', headers={'HX-Refresh': 'true'})

    return HttpResponse('Action inconnue.', status=400)


@login_required
def emploi_du_temps_pdf(request, classe_id):
    """Génère un PDF de l'emploi du temps via WeasyPrint."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur ce serveur.")
        return redirect('viescolaire:emploi_du_temps_index')
    etab = _get_etab(request)
    classe = get_object_or_404(Classe, pk=classe_id)

    annee_id = request.GET.get('annee')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    else:
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()

    enseignements = (
        Enseignement.objects
        .filter(classe=classe, annee_scolaire=annee, est_actif=True)
        .select_related('matiere', 'personnel')
        .order_by('matiere__nom')
    ) if annee else Enseignement.objects.none()

    seances = (
        SeanceCours.objects
        .filter(enseignement__in=enseignements)
        .select_related('enseignement__matiere', 'enseignement__personnel')
        .order_by('jour', 'heure_debut')
    )

    jours = _jours_grille(ConfigEDT.pour(etab), seances)
    jours_dict = {j: [] for j in jours}
    for s in seances:
        jours_dict[s.jour].append(s)

    grille = [
        {'jour_num': j, 'jour_label': JourSemaine(j).label, 'seances': jours_dict[j]}
        for j in jours
    ]

    from core.utils import get_etablissement_context
    etab_ctx = get_etablissement_context(etab, request) if etab else {}

    signataire = SignataireDocument.objects.get_signataire(
        cycle=classe.cycle,
        type_document=TypeDocument.objects.filter(code='EMPLOI_DU_TEMPS').first(),
        annee_scolaire=annee,
    ) if annee else None

    html_string = render_to_string('viescolaire/pdf/emploi_du_temps.html', {
        'classe': classe,
        'annee': annee,
        'grille': grille,
        'etab': etab,
        'identite': etab_ctx.get('identite'),
        'signataire': signataire,
    }, request=request)

    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Emploi_du_temps_{classe.nom}_{annee.libelle if annee else 'inconnu'}.pdf".replace(' ', '_')
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


# ─── Emploi du temps — par professeur ─────────────────────────────────────────

@login_required
def emploi_du_temps_prof_index(request):
    """Liste des professeurs avec sélecteur d'année scolaire."""
    from django.db.models import Count, Q
    from personnel.models import MembrePersonnel

    etab = _get_etab(request)
    annees = (
        AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
        if etab else AnneeScolaire.objects.none()
    )
    annee_id = request.GET.get('annee')
    annee = (
        annees.filter(pk=annee_id).first()
        if annee_id else annees.filter(est_courante=True).first()
    )

    personnel_qs = (
        MembrePersonnel.objects
        .filter(etablissement=etab, is_active=True)
        .order_by('nom', 'prenom')
        if etab else MembrePersonnel.objects.none()
    )
    if annee:
        personnel_qs = personnel_qs.annotate(
            nb_enseignements=Count(
                'enseignements',
                filter=Q(
                    enseignements__annee_scolaire=annee,
                    enseignements__est_actif=True,
                ),
            )
        )

    return render(request, 'viescolaire/emploi_du_temps_prof_index.html', {
        'personnel_list': personnel_qs,
        'annees': annees,
        'annee': annee,
    })


@login_required
def emploi_du_temps_prof(request, personnel_id):
    """Grille hebdomadaire de toutes les séances d'un professeur."""
    from personnel.models import MembrePersonnel

    etab = _get_etab(request)
    personnel = get_object_or_404(MembrePersonnel, pk=personnel_id, etablissement=etab)

    annees = (
        AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
        if etab else AnneeScolaire.objects.none()
    )
    annee_id = request.GET.get('annee')
    annee = (
        annees.filter(pk=annee_id).first()
        if annee_id else annees.filter(est_courante=True).first()
    )

    enseignements = (
        Enseignement.objects
        .filter(personnel=personnel, annee_scolaire=annee, est_actif=True)
        .select_related('matiere', 'classe')
        .order_by('classe__nom', 'matiere__nom')
    ) if annee else Enseignement.objects.none()

    seances = (
        SeanceCours.objects
        .filter(enseignement__in=enseignements)
        .select_related('enseignement__matiere', 'enseignement__classe')
        .order_by('jour', 'heure_debut')
    )

    JOURS = _jours_grille(ConfigEDT.pour(etab), seances)
    jours_labels = [JourSemaine(j).label for j in JOURS]

    slots: dict = {}
    for s in seances:
        key = (s.heure_debut, s.heure_fin)
        slots.setdefault(key, {})[s.jour] = s

    grille_creneaux = [
        {
            'heure_debut': hd,
            'heure_fin': hf,
            'jours': [{'seance': slot_jours.get(j)} for j in JOURS],
        }
        for (hd, hf), slot_jours in sorted(slots.items())
    ]

    return render(request, 'viescolaire/emploi_du_temps_prof.html', {
        'personnel': personnel,
        'annee': annee,
        'annees': annees,
        'enseignements': enseignements,
        'grille_creneaux': grille_creneaux,
        'jours_labels': jours_labels,
    })


@login_required
def emploi_du_temps_prof_pdf(request, personnel_id):
    """Génère le PDF de l'emploi du temps d'un professeur (WeasyPrint)."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur ce serveur.")
        return redirect('viescolaire:emploi_du_temps_prof_index')

    from personnel.models import MembrePersonnel

    etab = _get_etab(request)
    personnel = get_object_or_404(MembrePersonnel, pk=personnel_id, etablissement=etab)

    annees = (
        AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
        if etab else AnneeScolaire.objects.none()
    )
    annee_id = request.GET.get('annee')
    annee = (
        annees.filter(pk=annee_id).first()
        if annee_id else annees.filter(est_courante=True).first()
    )

    enseignements = list(
        Enseignement.objects
        .filter(personnel=personnel, annee_scolaire=annee, est_actif=True)
        .select_related('matiere', 'classe')
        .order_by('classe__nom', 'matiere__nom')
    ) if annee else []

    seances = list(
        SeanceCours.objects
        .filter(enseignement__in=enseignements)
        .select_related('enseignement__matiere', 'enseignement__classe')
        .order_by('jour', 'heure_debut')
    )

    jours = _jours_grille(ConfigEDT.pour(etab), seances)
    jours_dict = {j: [] for j in jours}
    for s in seances:
        jours_dict[s.jour].append(s)
    grille = [
        {'jour_num': j, 'jour_label': JourSemaine(j).label, 'seances': jours_dict[j]}
        for j in jours
    ]

    total_minutes = sum(
        int((
            datetime.combine(datetime.today(), s.heure_fin)
            - datetime.combine(datetime.today(), s.heure_debut)
        ).total_seconds() / 60)
        for s in seances
    )
    total_heures = total_minutes // 60
    total_minutes_reste = total_minutes % 60

    etab_ctx = get_etablissement_context(etab, request) if etab else {}
    signataire = (
        SignataireDocument.objects.get_signataire(
            cycle=None, type_document=TypeDocument.objects.filter(code='EMPLOI_DU_TEMPS').first(),
            annee_scolaire=annee,
        )
        if annee else None
    )

    html_string = render_to_string('viescolaire/pdf/emploi_du_temps_prof.html', {
        'personnel': personnel,
        'annee': annee,
        'grille': grille,
        'enseignements': enseignements,
        'total_heures': total_heures,
        'total_minutes_reste': total_minutes_reste,
        'etab': etab,
        'identite': etab_ctx.get('identite'),
        'signataire': signataire,
    }, request=request)

    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = (
        f"EDT_{personnel.nom}_{personnel.prenom}_{annee.libelle if annee else 'inconnu'}.pdf"
        .replace(' ', '_')
    )
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response
