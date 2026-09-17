"""
Module Vie Scolaire - Views
============================
YELEN SCHOOL v3.5
"""

import io

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
try:
    from weasyprint import HTML as WeasyHTML
except Exception:  # ImportError ou OSError (libpango/cairo absents)
    WeasyHTML = None
from django.contrib import messages
from django.views.decorators.http import require_POST

from parametres.models import AnneeScolaire, Classe, TypeSanction, SignataireDocument
from pedagogie.models import Trimestre, Enseignement, MoyenneGenerale
from inscriptions.models import Inscription
from core.utils import get_etablissement_context
from .models import (
    ConseilClasse, DecisionConseil, AppelDecision,
    SanctionDisciplinaire,
    ActiviteParascolaire, ParticipationActivite,
    SeanceCours, JourSemaine,
    ConfigDiscipline,
)


# ─── Conseils de classe ───────────────────────────────────────────────────────

@login_required
def conseil_list(request):
    """Liste des conseils de classe (tous trimestres)."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    trimestres = Trimestre.objects.filter(annee_scolaire=annee_courante).order_by('numero') if annee_courante else []

    trimestre_id = request.GET.get('trimestre')
    trimestre_selectionne = None
    if trimestre_id:
        trimestre_selectionne = Trimestre.objects.filter(pk=trimestre_id).first()

    conseils = ConseilClasse.objects.select_related(
        'classe', 'trimestre', 'president'
    ).order_by('date_conseil')
    if trimestre_selectionne:
        conseils = conseils.filter(trimestre=trimestre_selectionne)
    elif annee_courante:
        conseils = conseils.filter(trimestre__annee_scolaire=annee_courante)

    return render(request, 'viescolaire/conseil_list.html', {
        'conseils': conseils,
        'trimestres': trimestres,
        'trimestre_selectionne': trimestre_selectionne,
        'annee_courante': annee_courante,
    })


@login_required
def conseil_detail(request, conseil_id):
    """Détail d'un conseil + décisions individuelles."""
    conseil = get_object_or_404(
        ConseilClasse.objects.select_related('classe', 'trimestre', 'president'),
        pk=conseil_id
    )
    decisions = conseil.decisions.select_related(
        'inscription__eleve'
    ).order_by('inscription__eleve__nom')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'mark_tenu':
            conseil.tenu = True
            conseil.save(update_fields=['tenu'])
            messages.success(request, "Conseil marqué comme tenu.")

        elif action == 'save_decisions':
            for decision in decisions:
                key_decision = f'decision_{decision.pk}'
                key_appreciation = f'appreciation_{decision.pk}'
                key_mention = f'mention_{decision.pk}'
                key_encouragements = f'encouragements_{decision.pk}'
                key_felicitations = f'felicitations_{decision.pk}'
                if key_decision in request.POST:
                    decision.decision = request.POST[key_decision]
                    decision.appreciation = request.POST.get(key_appreciation, '')
                    decision.mention_honneur = key_mention in request.POST
                    decision.encouragements = key_encouragements in request.POST
                    decision.felicitations = key_felicitations in request.POST
                    decision.save(update_fields=[
                        'decision', 'appreciation',
                        'mention_honneur', 'encouragements', 'felicitations'
                    ])
            messages.success(request, "Décisions enregistrées.")

        return redirect('viescolaire:conseil_detail', conseil_id=conseil.pk)

    return render(request, 'viescolaire/conseil_detail.html', {
        'conseil': conseil,
        'decisions': decisions,
        'decision_choices': DecisionConseil.DecisionChoices.choices,
    })


@login_required
def conseil_create(request):
    """Créer un conseil de classe pour une classe/trimestre."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    classes = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')
    trimestres = Trimestre.objects.filter(annee_scolaire=annee_courante).order_by('numero') if annee_courante else []

    if request.method == 'POST':
        classe_id = request.POST.get('classe')
        trimestre_id = request.POST.get('trimestre')
        date_conseil = request.POST.get('date_conseil')
        president_id = request.POST.get('president') or None

        classe = get_object_or_404(Classe, pk=classe_id)
        trimestre = get_object_or_404(Trimestre, pk=trimestre_id)

        conseil, created = ConseilClasse.objects.get_or_create(
            classe=classe,
            trimestre=trimestre,
            defaults={
                'date_conseil': date_conseil,
                'president_id': president_id,
            }
        )
        if not created:
            messages.warning(request, "Un conseil existe déjà pour cette classe et ce trimestre.")
            return redirect('viescolaire:conseil_detail', conseil_id=conseil.pk)

        # Créer les décisions pour tous les élèves de la classe
        inscriptions = Inscription.objects.filter(
            classe=classe, annee_scolaire=trimestre.annee_scolaire
        ).exclude(statut='ABANDON').select_related('eleve')
        DecisionConseil.objects.bulk_create([
            DecisionConseil(conseil=conseil, inscription=ins)
            for ins in inscriptions
        ], ignore_conflicts=True)

        messages.success(request, f"Conseil créé pour {classe} — {trimestre} ({inscriptions.count()} élèves).")
        return redirect('viescolaire:conseil_detail', conseil_id=conseil.pk)

    return render(request, 'viescolaire/conseil_create.html', {
        'classes': classes,
        'trimestres': trimestres,
    })


@login_required
def conseil_pv_pdf(request, conseil_id):
    """Génère le PV du conseil de classe en PDF."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur ce serveur.")
        return redirect('viescolaire:conseil_detail', conseil_id=conseil_id)
    conseil = get_object_or_404(
        ConseilClasse.objects.select_related('classe', 'trimestre', 'president'),
        pk=conseil_id
    )
    decisions = conseil.decisions.select_related(
        'inscription__eleve'
    ).order_by('inscription__eleve__nom', 'inscription__eleve__prenom')

    # Moyennes générales pour affichage dans le PV
    mg_par_ins = {
        mg.inscription_id: mg
        for mg in MoyenneGenerale.objects.filter(
            trimestre=conseil.trimestre,
            inscription__in=[d.inscription for d in decisions]
        )
    }

    # Enrichir chaque décision avec la moyenne
    lignes = []
    for d in decisions:
        lignes.append({
            'decision': d,
            'mg': mg_par_ins.get(d.inscription_id),
        })

    # Statistiques récapitulatives
    from django.db.models import Count
    stats_decisions = {}
    for val, label in DecisionConseil.DecisionChoices.choices:
        stats_decisions[val] = {
            'label': label,
            'count': sum(1 for d in decisions if d.decision == val),
        }
    nb_felicitations = sum(1 for d in decisions if d.felicitations)
    nb_encouragements = sum(1 for d in decisions if d.encouragements)
    nb_mentions = sum(1 for d in decisions if d.mention_honneur)

    etab = getattr(request.user, 'etablissement', None)
    etab_ctx = get_etablissement_context(etab, request=request)

    html_string = render_to_string('viescolaire/pdf/conseil_pv.html', {
        'conseil': conseil,
        'lignes': lignes,
        'stats_decisions': stats_decisions,
        'nb_felicitations': nb_felicitations,
        'nb_encouragements': nb_encouragements,
        'nb_mentions': nb_mentions,
        'nb_total': len(lignes),
        **etab_ctx,
    })

    pdf = WeasyHTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    nom_fichier = (
        f"PV_conseil_{conseil.classe.nom}_{conseil.trimestre.nom}"
        .replace(' ', '_').replace('/', '-') + '.pdf'
    )
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
    return response


# ─── Sanctions disciplinaires ─────────────────────────────────────────────────

@login_required
def sanction_list(request):
    """Liste des sanctions disciplinaires, regroupées par classe."""
    from django.db.models import Q
    
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    qs = SanctionDisciplinaire.objects.select_related(
        'inscription__eleve', 'inscription__classe__cycle', 'prononcee_par', 'trimestre', 'type_sanction'
    ).order_by('inscription__classe__cycle__ordre', 'inscription__classe__nom', '-date_sanction')
    if annee_courante:
        qs = qs.filter(inscription__annee_scolaire=annee_courante)

    type_filtre = request.GET.get('type')
    if type_filtre:
        qs = qs.filter(type_sanction_id=type_filtre)

    statut_filtre = request.GET.get('statut')
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)

    classe_filtre = request.GET.get('classe')
    if classe_filtre:
        qs = qs.filter(inscription__classe_id=classe_filtre)

    date_min = request.GET.get('date_min')
    if date_min:
        qs = qs.filter(date_sanction__gte=date_min)

    eleve_q = request.GET.get('eleve')
    if eleve_q:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=eleve_q) |
            Q(inscription__eleve__prenom__icontains=eleve_q) |
            Q(inscription__eleve__matricule__icontains=eleve_q)
        )

    etab = getattr(request.user, 'etablissement', None)
    if etab:
        classes = Classe.objects.filter(etablissement=etab).select_related('cycle').order_by('cycle__ordre', 'nom')
    else:
        classes = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')

    groupes = {}
    for s in qs:
        classe = s.inscription.classe
        if classe.pk not in groupes:
            groupes[classe.pk] = {'classe': classe, 'sanctions': []}
        groupes[classe.pk]['sanctions'].append(s)

    types_sanction = TypeSanction.objects.filter(actif=True).order_by('libelle')

    return render(request, 'viescolaire/sanction_list.html', {
        'groupes': list(groupes.values()),
        'total': qs.count(),
        'nb_confirmees': qs.filter(statut='CONFIRME').count(),
        'nb_en_cours': qs.filter(statut='EN_COURS').count(),
        'nb_levees': qs.filter(statut='LEVEE').count(),
        'nb_avec_points': qs.exclude(points=0).count(),
        'annee_courante': annee_courante,
        'types_sanction': types_sanction,
        'type_filtre': type_filtre,
        'statut_filtre': statut_filtre,
        'classe_filtre': classe_filtre,
        'date_min_filtre': date_min,
        'eleve_filtre': eleve_q,
        'classes': classes,
    })


@login_required
def sanction_create(request):
    """Enregistrer une nouvelle sanction disciplinaire."""
    # Vérification de rôle - seul le personnel autorisé peut créer des sanctions
    from core.models import RoleChoices
    if request.user.role not in (
        RoleChoices.DIRECTEUR, RoleChoices.CENSEUR, RoleChoices.AVS, RoleChoices.SECRETAIRE
    ):
        messages.error(request, "Vous n'êtes pas autorisé à enregistrer des sanctions.")
        return redirect('viescolaire:sanction_list')
    
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    
    # Filtrer les classes par établissement de l'utilisateur
    etab = request.user.etablissement
    if etab:
        classes = Classe.objects.filter(etablissement=etab).select_related('cycle').order_by('cycle__ordre', 'nom')
    else:
        classes = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')
        
    trimestres = Trimestre.objects.filter(
        annee_scolaire=annee_courante
    ).order_by('numero') if annee_courante else []

    if request.method == 'POST':
        inscription_id = request.POST.get('inscription')
        inscription = get_object_or_404(Inscription, pk=inscription_id)
        
        # IDOR - Vérifier que l'inscription appartient à l'établissement de l'utilisateur
        if etab and inscription.classe.etablissement != etab:
            messages.error(request, "Vous n'avez pas accès à cet élève.")
            return redirect('viescolaire:sanction_create')
        
        trimestre_id = request.POST.get('trimestre') or None
        trimestre = Trimestre.objects.filter(pk=trimestre_id).first() if trimestre_id else None
        points_raw = request.POST.get('points', '0').strip() or '0'

        type_sanction = get_object_or_404(TypeSanction, pk=request.POST['type_sanction'])

        sanction = SanctionDisciplinaire.objects.create(
            inscription=inscription,
            type_sanction=type_sanction,
            date_sanction=request.POST['date_sanction'],
            motif=request.POST['motif'],
            duree_jours=request.POST.get('duree_jours') or 0,
            date_retour=request.POST.get('date_retour') or None,
            prononcee_par=request.user,
            statut=request.POST.get('statut', SanctionDisciplinaire.StatutChoices.EN_COURS),
            observations=request.POST.get('observations', ''),
            parents_convoques='parents_convoques' in request.POST,
            date_convocation=request.POST.get('date_convocation') or None,
            trimestre=trimestre,
            points=points_raw,
            appreciation_conduite=request.POST.get('appreciation_conduite', ''),
        )

        # Recalculer la moyenne si des points sont appliqués et le trimestre est défini
        if sanction.a_impact_points:
            from pedagogie.utils import CalculateurMoyenne
            CalculateurMoyenne.calculer_moyenne_generale(inscription, trimestre)
            CalculateurMoyenne.calculer_rangs(inscription.classe, trimestre)
            messages.success(
                request,
                f"Sanction enregistrée — {float(sanction.points):+g} pts appliqués au trimestre {trimestre}.",
            )
        else:
            messages.success(request, "Sanction enregistrée.")

        return redirect('viescolaire:sanction_list')

    classe_id = request.GET.get('classe')
    inscriptions = []
    if classe_id and annee_courante:
        inscriptions = Inscription.objects.filter(
            classe_id=classe_id, annee_scolaire=annee_courante
        ).exclude(statut='ABANDON').select_related('eleve').order_by('eleve__nom')

    import json
    types_qs = TypeSanction.objects.filter(actif=True).order_by('libelle')
    types_sanction_json = json.dumps({
        str(t.pk): str(t.points_defaut) for t in types_qs
    })
    etab = getattr(request.user, 'etablissement', None)
    config_disc = ConfigDiscipline.get_or_default(etab) if etab else None

    return render(request, 'viescolaire/sanction_create.html', {
        'classes': classes,
        'inscriptions': inscriptions,
        'trimestres': trimestres,
        'types_sanction': types_qs,
        'types_sanction_json': types_sanction_json,
        'statut_choices': SanctionDisciplinaire.StatutChoices.choices,
        'classe_id': classe_id,
        'annee_courante': annee_courante,
        'config_disc': config_disc,
    })


@login_required
@require_POST
def sanction_delete(request, sanction_id):
    """Supprime une sanction disciplinaire (POST uniquement)."""
    sanction = get_object_or_404(SanctionDisciplinaire, pk=sanction_id)

    # Si la sanction avait un impact sur la moyenne, recalculer après suppression
    avait_impact = sanction.a_impact_points
    inscription = sanction.inscription
    trimestre = sanction.trimestre

    sanction.delete()

    if avait_impact:
        from pedagogie.utils import CalculateurMoyenne
        CalculateurMoyenne.calculer_moyenne_generale(inscription, trimestre)
        CalculateurMoyenne.calculer_rangs(inscription.classe, trimestre)

    messages.success(request, "Sanction supprimée.")
    return redirect('viescolaire:sanction_list')


# ─── Activités parascolaires ──────────────────────────────────────────────────

@login_required
def activite_list(request):
    """Liste des activités parascolaires filtrées par établissement."""
    etab = getattr(request.user, 'etablissement', None)

    annee_qs = AnneeScolaire.objects.filter(est_courante=True)
    if etab:
        annee_qs = annee_qs.filter(etablissement=etab)
    annee_courante = annee_qs.first()

    activites = ActiviteParascolaire.objects.select_related(
        'annee_scolaire', 'responsable'
    ).prefetch_related('participations').order_by('type_activite', 'nom')

    if etab:
        activites = activites.filter(annee_scolaire__etablissement=etab)
    if annee_courante:
        activites = activites.filter(annee_scolaire=annee_courante)

    return render(request, 'viescolaire/activite_list.html', {
        'activites': activites,
        'annee_courante': annee_courante,
        'type_choices': ActiviteParascolaire.TypeActiviteChoices.choices,
    })


@login_required
def activite_detail(request, activite_id):
    """Détail d'une activité + liste des participants."""
    activite = get_object_or_404(
        ActiviteParascolaire.objects.select_related('annee_scolaire', 'responsable'),
        pk=activite_id
    )
    participations = activite.participations.select_related(
        'inscription__eleve', 'inscription__classe'
    ).filter(is_active=True).order_by('inscription__eleve__nom')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'inscrire':
            inscription_id = request.POST.get('inscription')
            inscription = get_object_or_404(Inscription, pk=inscription_id)
            _, created = ParticipationActivite.objects.get_or_create(
                activite=activite, inscription=inscription
            )
            if created:
                messages.success(request, f"{inscription.eleve} inscrit(e) à {activite.nom}.")
            else:
                messages.info(request, "Cet élève est déjà inscrit.")
        elif action == 'retirer':
            part_id = request.POST.get('participation_id')
            ParticipationActivite.objects.filter(pk=part_id).update(is_active=False)
            messages.success(request, "Élève retiré de l'activité.")
        return redirect('viescolaire:activite_detail', activite_id=activite.pk)

    # Élèves disponibles pour inscription (année scolaire de l'activité)
    inscrits_ids = participations.values_list('inscription_id', flat=True)
    inscriptions_dispo = Inscription.objects.filter(
        annee_scolaire=activite.annee_scolaire, is_active=True
    ).exclude(pk__in=inscrits_ids).exclude(statut='ABANDON').select_related('eleve', 'classe').order_by('eleve__nom')

    return render(request, 'viescolaire/activite_detail.html', {
        'activite': activite,
        'participations': participations,
        'inscriptions_dispo': inscriptions_dispo,
    })


@login_required
def activite_create(request):
    """Créer une activité parascolaire."""
    etab = getattr(request.user, 'etablissement', None)
    annee_qs = AnneeScolaire.objects.filter(est_courante=True)
    if etab:
        annee_qs = annee_qs.filter(etablissement=etab)
    annee_courante = annee_qs.first()

    from django.contrib.auth import get_user_model
    User = get_user_model()
    responsables = User.objects.filter(is_active=True).order_by('last_name', 'first_name')

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom de l'activité est obligatoire.")
        elif not annee_courante:
            messages.error(request, "Aucune année scolaire courante définie.")
        else:
            try:
                ActiviteParascolaire.objects.create(
                    annee_scolaire=annee_courante,
                    nom=nom,
                    type_activite=request.POST.get('type_activite', ActiviteParascolaire.TypeActiviteChoices.CLUB),
                    description=request.POST.get('description', '').strip(),
                    responsable_id=request.POST.get('responsable') or None,
                    capacite_max=int(request.POST.get('capacite_max') or 30),
                    jour_reunion=request.POST.get('jour_reunion') or None,
                    heure_debut=request.POST.get('heure_debut') or None,
                )
                messages.success(request, f"Activité « {nom} » créée.")
                return redirect('viescolaire:activite_list')
            except ValueError as e:
                messages.error(request, str(e))

    return render(request, 'viescolaire/activite_form.html', {
        'titre': 'Nouvelle activité parascolaire',
        'submit_label': 'Créer l\'activité',
        'type_choices': ActiviteParascolaire.TypeActiviteChoices.choices,
        'jour_choices': JourSemaine.choices,
        'responsables': responsables,
        'annee_courante': annee_courante,
    })


@login_required
def activite_edit(request, activite_id):
    """Modifier une activité parascolaire."""
    activite = get_object_or_404(ActiviteParascolaire, pk=activite_id)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    responsables = User.objects.filter(is_active=True).order_by('last_name', 'first_name')

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom est obligatoire.")
        else:
            try:
                activite.nom = nom
                activite.type_activite = request.POST.get('type_activite', activite.type_activite)
                activite.description = request.POST.get('description', '').strip()
                activite.responsable_id = request.POST.get('responsable') or None
                activite.capacite_max = int(request.POST.get('capacite_max') or 30)
                activite.jour_reunion = request.POST.get('jour_reunion') or None
                activite.heure_debut = request.POST.get('heure_debut') or None
                activite.save(update_fields=[
                    'nom', 'type_activite', 'description', 'responsable',
                    'capacite_max', 'jour_reunion', 'heure_debut', 'updated_at',
                ])
                messages.success(request, f"Activité « {activite.nom} » mise à jour.")
                return redirect('viescolaire:activite_detail', activite_id=activite.pk)
            except ValueError as e:
                messages.error(request, str(e))

    return render(request, 'viescolaire/activite_form.html', {
        'activite': activite,
        'titre': f'Modifier — {activite.nom}',
        'submit_label': 'Enregistrer',
        'type_choices': ActiviteParascolaire.TypeActiviteChoices.choices,
        'jour_choices': JourSemaine.choices,
        'responsables': responsables,
    })


@login_required
def activite_delete(request, activite_id):
    """Supprimer une activité parascolaire."""
    activite = get_object_or_404(ActiviteParascolaire, pk=activite_id)
    if request.method == 'POST':
        nb = activite.participations.filter(is_active=True).count()
        nom = activite.nom
        activite.delete()
        messages.success(request, f"Activité « {nom} » supprimée ({nb} participant(s) retiré(s)).")
        return redirect('viescolaire:activite_list')
    return render(request, 'viescolaire/activite_confirm_delete.html', {'activite': activite})


# ─── Emploi du temps ──────────────────────────────────────────────────────────

def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


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

    # Grille horaire : lignes = créneaux uniques, colonnes = jours (Lun–Sam)
    JOURS = list(range(1, 7))
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

    return render(request, 'viescolaire/emploi_du_temps.html', {
        'classe': classe,
        'annee': annee,
        'annees': annees,
        'enseignements': enseignements,
        'enseignements_avec_couleur': enseignements_avec_couleur,
        'grille_creneaux': grille_creneaux,
        'jours_labels': jours_labels,
        'jours_choices': JourSemaine.choices,
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
    salle = request.POST.get('salle', '').strip()

    if not all([jour, heure_debut, heure_fin]):
        return HttpResponse("Jour, heure de début et heure de fin sont obligatoires.", status=400)

    if heure_fin <= heure_debut:
        return HttpResponse("L'heure de fin doit être postérieure à l'heure de début.", status=400)

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

    from django.urls import reverse
    url = reverse('viescolaire:emploi_du_temps', kwargs={'classe_id': classe.pk})
    return redirect(f"{url}?annee={annee.pk}")


@login_required
@require_POST
def seance_delete(request, seance_id):
    """Supprime une séance de cours."""
    from django.urls import reverse
    seance = get_object_or_404(
        SeanceCours.objects.select_related('enseignement'),
        pk=seance_id,
    )
    classe_id = seance.enseignement.classe_id
    annee_id = seance.enseignement.annee_scolaire_id
    seance.delete()
    url = reverse('viescolaire:emploi_du_temps', kwargs={'classe_id': classe_id})
    return redirect(f"{url}?annee={annee_id}")


@login_required
def edt_generer(request, classe_id):
    """Génération automatique d'EDT — formulaire, aperçu et application."""
    import json as _json
    from .models import ConfigEDT
    from .services import GenerateurEDT

    etab = _get_etab(request)
    classe = get_object_or_404(Classe, pk=classe_id)

    annee_id = request.GET.get('annee') or request.POST.get('annee')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    else:
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()

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

        for s in seances_data:
            try:
                ens = Enseignement.objects.get(pk=s['enseignement_id'])
                SeanceCours.objects.get_or_create(
                    enseignement=ens,
                    jour=s['jour'],
                    heure_debut=s['heure_debut'],
                    defaults={'heure_fin': s['heure_fin']},
                )
            except Exception:
                pass

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

    jours_dict = {j: [] for j in range(1, 8)}
    for s in seances:
        jours_dict[s.jour].append(s)

    grille = [
        {'jour_num': j, 'jour_label': JourSemaine(j).label, 'seances': jours_dict[j]}
        for j in range(1, 7)
    ]

    from core.utils import get_etablissement_context
    etab_ctx = get_etablissement_context(etab, request) if etab else {}

    signataire = SignataireDocument.objects.get_signataire(
        cycle=classe.cycle,
        type_document=None,
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

    JOURS = list(range(1, 7))
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

    from datetime import datetime
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

    jours_dict = {j: [] for j in range(1, 7)}
    for s in seances:
        jours_dict[s.jour].append(s)
    grille = [
        {'jour_num': j, 'jour_label': JourSemaine(j).label, 'seances': jours_dict[j]}
        for j in range(1, 7)
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
            cycle=None, type_document=None, annee_scolaire=annee,
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


# ─── Fiche de suivi individuelle ──────────────────────────────────────────────

@login_required
def fiche_suivi_eleve(request, inscription_id):
    """
    Vue unifiee : presences + notes + sanctions + retards + activites
    pour un eleve donne (scope : une inscription = annee + eleve + classe).
    """
    from django.db.models import Count, Q
    from presences.models import Presence
    from pedagogie.models import Resultat

    inscription = get_object_or_404(
        Inscription.objects.select_related(
            'eleve', 'classe', 'annee_scolaire', 'statut_eleve'
        ),
        pk=inscription_id,
    )

    # ── 1. Presences ──────────────────────────────────────────────────────────
    presences_qs = (
        Presence.objects
        .filter(inscription=inscription)
        .select_related('appel__matiere')
        .order_by('-appel__date')
    )
    nb_absences     = presences_qs.filter(statut='ABSENT').count()
    nb_retards      = presences_qs.filter(statut='RETARD').count()
    nb_excuses      = presences_qs.filter(statut='EXCUSE').count()
    nb_presents     = presences_qs.filter(statut='PRESENT').count()
    nb_total_appels = presences_qs.count()

    absences  = presences_qs.filter(statut__in=['ABSENT', 'EXCUSE'])
    retards   = presences_qs.filter(statut='RETARD')

    # ── 2. Notes / Resultats ──────────────────────────────────────────────────
    trimestres = (
        Trimestre.objects
        .filter(annee_scolaire=inscription.annee_scolaire)
        .order_by('numero')
    )

    # Moyennes generales par trimestre
    moyennes = (
        MoyenneGenerale.objects
        .filter(inscription=inscription)
        .select_related('trimestre')
        .order_by('trimestre__numero')
    )
    moyennes_par_tri = {mg.trimestre_id: mg for mg in moyennes}

    # Resultats par trimestre
    resultats_qs = (
        Resultat.objects
        .filter(inscription=inscription)
        .select_related('enseignement__matiere', 'trimestre')
        .order_by('trimestre__numero', 'enseignement__matiere__nom')
    )

    resultats_par_tri = {}
    for r in resultats_qs:
        tid = r.trimestre_id
        resultats_par_tri.setdefault(tid, []).append(r)

    periodes = []
    for tri in trimestres:
        periodes.append({
            'trimestre': tri,
            'moyenne': moyennes_par_tri.get(tri.pk),
            'resultats': resultats_par_tri.get(tri.pk, []),
        })

    # ── 3. Sanctions ──────────────────────────────────────────────────────────
    sanctions = (
        SanctionDisciplinaire.objects
        .filter(inscription=inscription)
        .select_related('type_sanction', 'prononcee_par', 'trimestre')
        .order_by('-date_sanction')
    )
    nb_sanctions_actives = sanctions.exclude(statut='ANNULE').count()

    # ── 4. Decisions de conseil ───────────────────────────────────────────────
    decisions = (
        DecisionConseil.objects
        .filter(inscription=inscription)
        .select_related('conseil__trimestre', 'conseil__classe')
        .order_by('-conseil__trimestre__numero')
    )

    # ── 5. Activites parascolaires ────────────────────────────────────────────
    participations = (
        ParticipationActivite.objects
        .filter(inscription=inscription, is_active=True)
        .select_related('activite')
        .order_by('activite__type_activite', 'activite__nom')
    )
    nb_activites = participations.count()

    # ── Onglets (label + badge count) ────────────────────────────────────────
    tabs_def = [
        ('presences',  'Présences & Retards',      nb_absences + nb_retards if (nb_absences + nb_retards) else None),
        ('notes',      'Notes & Résultats',         None),
        ('sanctions',  'Sanctions',                  nb_sanctions_actives if nb_sanctions_actives else None),
        ('conseil',    'Conseil de classe',          decisions.count() or None),
        ('activites',  'Activités parascolaires',   nb_activites if nb_activites else None),
    ]

    # ── 6. Capital points discipline ─────────────────────────────────────────
    etab = getattr(request.user, 'etablissement', None)
    config_disc = ConfigDiscipline.get_or_default(etab) if etab else None
    capital = _calcul_capital_points(inscription, config_disc) if config_disc else None

    return render(request, 'viescolaire/fiche_suivi_eleve.html', {
        'inscription':          inscription,
        'nb_absences':          nb_absences,
        'nb_retards':           nb_retards,
        'nb_excuses':           nb_excuses,
        'nb_presents':          nb_presents,
        'nb_total_appels':      nb_total_appels,
        'absences':             absences,
        'retards':              retards,
        'periodes':             periodes,
        'sanctions':            sanctions,
        'nb_sanctions_actives': nb_sanctions_actives,
        'decisions':            decisions,
        'participations':       participations,
        'tabs_def':             tabs_def,
        'capital':              capital,
        'config_disc':          config_disc,
    })


# ─── Liste / recherche des fiches de suivi ────────────────────────────────────

@login_required
def fiches_suivi_list(request):
    """
    Page de recherche permettant d'acceder a la fiche de suivi
    de n'importe quel eleve de l'etablissement.
    """
    etab = request.user.etablissement
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    q = request.GET.get('q', '').strip()

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('nom')

    inscriptions = (
        Inscription.objects
        .filter(annee_scolaire=annee_sel, classe__etablissement=etab)
        .exclude(statut='ABANDON')
        .select_related('eleve', 'classe', 'statut_eleve')
        .order_by('classe__nom', 'eleve__nom', 'eleve__prenom')
    )

    if classe_id:
        inscriptions = inscriptions.filter(classe_id=classe_id)

    if q:
        from django.db.models import Q
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__matricule__icontains=q)
        )

    return render(request, 'viescolaire/fiches_suivi_list.html', {
        'inscriptions': inscriptions,
        'annees': annees,
        'annee_sel': annee_sel,
        'classes': classes,
        'classe_id': classe_id or '',
        'q': q,
    })


# ─── Discipline — helper capital points ───────────────────────────────────────

def _calcul_capital_points(inscription, config):
    """
    Retourne le solde de points de discipline pour une inscription.

    solde = points_depart  +  SUM(sanctions confirmees avec impact)
    Les sanctions avec points < 0 retirent, points > 0 ajoutent.
    """
    from decimal import Decimal
    from django.db.models import Sum, Q

    agg = (
        SanctionDisciplinaire.objects
        .filter(
            inscription=inscription,
            statut=SanctionDisciplinaire.StatutChoices.CONFIRME,
        )
        .exclude(points=0)
        .aggregate(total=Sum('points'))
    )
    total_sanctions = agg['total'] or Decimal('0')
    solde = Decimal(str(config.points_depart)) + total_sanctions
    return {
        'solde': solde,
        'statut': config.statut_solde(solde),
        'points_depart': config.points_depart,
        'total_sanctions': total_sanctions,
    }


# ─── Discipline — configuration ───────────────────────────────────────────────

@login_required
def config_discipline(request):
    """Paramétrer les seuils du système de points de discipline."""
    etab = getattr(request.user, 'etablissement', None)
    if not etab:
        messages.error(request, "Aucun établissement associé à votre compte.")
        return redirect('core:home')

    config = ConfigDiscipline.get_or_default(etab)

    if request.method == 'POST':
        config.points_depart = int(request.POST.get('points_depart', 20))
        config.seuil_alerte = int(request.POST.get('seuil_alerte', 5))
        config.seuil_conseil = int(request.POST.get('seuil_conseil', 2))
        config.seuil_exclusion = int(request.POST.get('seuil_exclusion', 0))
        config.message_alerte = request.POST.get('message_alerte', '').strip()
        config.save()
        messages.success(request, "Configuration de discipline enregistrée.")
        return redirect('viescolaire:config_discipline')

    return render(request, 'viescolaire/config_discipline.html', {'config': config})


# ─── Discipline — tableau de bord capital points ──────────────────────────────

@login_required
def capital_points_list(request):
    """
    Tableau de bord : liste des élèves avec leur solde de points de discipline,
    triés par statut (EXCLUSION → CONSEIL → ALERTE → NORMAL).
    """
    etab = getattr(request.user, 'etablissement', None)
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('nom')

    config = ConfigDiscipline.get_or_default(etab) if etab else None

    inscriptions_qs = (
        Inscription.objects
        .filter(annee_scolaire=annee_sel, classe__etablissement=etab)
        .exclude(statut='ABANDON')
        .select_related('eleve', 'classe')
        .order_by('classe__nom', 'eleve__nom')
    )
    if classe_id:
        inscriptions_qs = inscriptions_qs.filter(classe_id=classe_id)

    # Calcul du solde pour chaque élève
    ORDER = {'EXCLUSION': 0, 'CONSEIL': 1, 'ALERTE': 2, 'NORMAL': 3}
    lignes = []
    for inscr in inscriptions_qs:
        if config:
            cap = _calcul_capital_points(inscr, config)
        else:
            cap = {'solde': 20, 'statut': 'NORMAL', 'points_depart': 20, 'total_sanctions': 0}
        lignes.append({
            'inscription': inscr,
            'solde': cap['solde'],
            'statut': cap['statut'],
            'total_sanctions': cap['total_sanctions'],
        })

    lignes.sort(key=lambda x: ORDER.get(x['statut'], 9))

    nb_exclusion = sum(1 for l in lignes if l['statut'] == 'EXCLUSION')
    nb_conseil   = sum(1 for l in lignes if l['statut'] == 'CONSEIL')
    nb_alerte    = sum(1 for l in lignes if l['statut'] == 'ALERTE')

    return render(request, 'viescolaire/capital_points_list.html', {
        'lignes': lignes,
        'config': config,
        'annees': annees,
        'annee_sel': annee_sel,
        'classes': classes,
        'classe_id': classe_id or '',
        'nb_exclusion': nb_exclusion,
        'nb_conseil': nb_conseil,
        'nb_alerte': nb_alerte,
    })


# ─── Appels de décision ────────────────────────────────────────────────────────

@login_required
def appel_decision_list(request):
    """Liste de tous les appels de décision de l'établissement."""
    etab = request.user.etablissement
    if not etab:
        return redirect('viescolaire:conseil_list')

    qs = (
        AppelDecision.objects
        .filter(decision_conseil__conseil__classe__etablissement=etab)
        .select_related(
            'decision_conseil__inscription__eleve',
            'decision_conseil__conseil__classe',
            'decision_conseil__conseil__trimestre',
            'depose_par',
            'traite_par',
        )
        .order_by('-date_depot')
    )

    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        qs = qs.filter(statut=statut_filter)

    return render(request, 'viescolaire/appel_decision_list.html', {
        'appels': qs,
        'statut_filter': statut_filter,
        'statut_choices': AppelDecision.StatutChoices.choices,
        'nb_en_attente': qs.filter(statut=AppelDecision.StatutChoices.EN_ATTENTE).count(),
    })


@login_required
def appel_decision_create(request, decision_id):
    """Déposer un appel contre une décision de conseil de classe."""
    etab = request.user.etablissement
    decision = get_object_or_404(
        DecisionConseil,
        pk=decision_id,
        conseil__classe__etablissement=etab,
    )

    # Une décision ne peut être contestée qu'une seule fois
    if hasattr(decision, 'appel'):
        messages.warning(request, "Cette décision a déjà fait l'objet d'un appel.")
        return redirect('viescolaire:conseil_detail', conseil_id=decision.conseil_id)

    # Seules certaines décisions sont contestables
    contestables = [
        DecisionConseil.DecisionChoices.REDOUBLEMENT,
        DecisionConseil.DecisionChoices.ORIENTATION,
        DecisionConseil.DecisionChoices.EXCLUSION,
    ]
    if decision.decision not in contestables:
        messages.error(request, "Cette décision ne peut pas être contestée.")
        return redirect('viescolaire:conseil_detail', conseil_id=decision.conseil_id)

    if request.method == 'POST':
        motif      = request.POST.get('motif', '').strip()
        date_depot = request.POST.get('date_depot', '')
        if not motif:
            messages.error(request, "Le motif de contestation est obligatoire.")
        else:
            import datetime
            try:
                date_obj = datetime.date.fromisoformat(date_depot) if date_depot else datetime.date.today()
            except ValueError:
                date_obj = datetime.date.today()

            AppelDecision.objects.create(
                decision_conseil=decision,
                motif=motif,
                date_depot=date_obj,
                depose_par=request.user,
                statut=AppelDecision.StatutChoices.EN_ATTENTE,
            )
            messages.success(request, "Appel enregistré — la commission sera saisie.")
            return redirect('viescolaire:conseil_detail', conseil_id=decision.conseil_id)

    import datetime
    return render(request, 'viescolaire/appel_decision_form.html', {
        'decision': decision,
        'today': datetime.date.today().isoformat(),
    })


@login_required
def appel_decision_traiter(request, appel_id):
    """Instruire et clôturer un appel de décision."""
    etab = request.user.etablissement
    appel = get_object_or_404(
        AppelDecision,
        pk=appel_id,
        decision_conseil__conseil__classe__etablissement=etab,
    )

    if appel.est_traite:
        messages.info(request, "Cet appel est déjà traité.")
        return redirect('viescolaire:appel_decision_list')

    if request.method == 'POST':
        issue                  = request.POST.get('issue', '')
        nouvelle_decision      = request.POST.get('nouvelle_decision', '') or None
        observations           = request.POST.get('observations_commission', '').strip()
        statut_form            = request.POST.get('statut', AppelDecision.StatutChoices.EN_INSTRUCTION)

        if not issue and statut_form == AppelDecision.StatutChoices.TRAITE:
            messages.error(request, "L'issue est obligatoire pour clôturer l'appel.")
        else:
            import datetime
            appel.statut                 = statut_form
            appel.observations_commission = observations
            if issue:
                appel.issue = issue
            if issue == AppelDecision.IssueChoices.MODIFIE and nouvelle_decision:
                appel.nouvelle_decision = nouvelle_decision
                # Mettre à jour la décision effective si modifiée
                appel.decision_conseil.decision = nouvelle_decision
                appel.decision_conseil.save(update_fields=['decision'])
            if statut_form == AppelDecision.StatutChoices.TRAITE:
                appel.traite_par      = request.user
                appel.date_traitement = datetime.date.today()
            appel.save()
            messages.success(request, "Appel mis à jour.")
            return redirect('viescolaire:appel_decision_list')

    return render(request, 'viescolaire/appel_decision_traiter.html', {
        'appel': appel,
        'issue_choices': AppelDecision.IssueChoices.choices,
        'decision_choices': DecisionConseil.DecisionChoices.choices,
        'statut_choices': AppelDecision.StatutChoices.choices,
    })
