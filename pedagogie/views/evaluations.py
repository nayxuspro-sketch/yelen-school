"""Évaluations : liste paginée, création, saisie des notes.

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from ..models import Enseignement, Evaluation, Note, Resultat, Trimestre
from ..forms import EvaluationForm
from parametres.models import AnneeScolaire, Classe
from inscriptions.models import Inscription
from core.utils import filtre_enseignant
# Nombre de classes affichées par page dans la liste des évaluations
# (chaque classe regroupe toutes ses matières et évaluations : ~40 lignes
# par classe et par trimestre).
EVALUATIONS_CLASSES_PAR_PAGE = 4


def _trimestre_en_cours(trimestres):
    """Trimestre dont les dates encadrent aujourd'hui (None si aucun)."""
    aujourd_hui = timezone.localdate()
    return next(
        (t for t in trimestres if t.date_debut <= aujourd_hui <= t.date_fin),
        None,
    )


@login_required
def evaluation_list(request):
    """
    Liste des évaluations planifiées, groupée classe → matière, paginée par
    classe et filtrable (recherche, classe, trimestre). Un établissement de
    2 500 élèves compte ~6 000 évaluations par an : seules celles des classes
    de la page courante sont chargées.
    """
    from django.core.paginator import Paginator
    from django.db.models import Count

    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    query = request.GET.get('q', '').strip()
    classe_id = request.GET.get('classe', '').strip()
    # « trimestre » absent (premier affichage) → trimestre en cours ;
    # « trimestre= » vide (choix explicite « Tous ») → toute l'année.
    trimestre_id = request.GET.get('trimestre', '').strip()
    trimestre_par_defaut = 'trimestre' not in request.GET

    evaluations = Evaluation.objects.filter(enseignement__annee_scolaire=annee_courante)

    # Un enseignant ne voit que ses propres évaluations (cohérent avec le
    # contrôle d'autorisation de evaluation_saisie).
    if request.user.role == 'ENSEIGNANT':
        evaluations = evaluations.filter(enseignement__personnel=filtre_enseignant(request.user))

    # Listes des filtres : uniquement les classes/trimestres visibles par l'utilisateur
    classes = (
        Classe.objects
        .filter(enseignements__evaluations__in=evaluations.values('pk'))
        .distinct()
        .order_by('nom')
    )
    trimestres = Trimestre.objects.filter(annee_scolaire=annee_courante).order_by('numero', 'nom')

    classe_ids_valides = {str(c.pk) for c in classes}
    if classe_id not in classe_ids_valides:
        classe_id = ''
    trimestres = list(trimestres)
    trimestre_ids_valides = {str(t.pk) for t in trimestres}
    if trimestre_par_defaut:
        en_cours = _trimestre_en_cours(trimestres)
        trimestre_id = str(en_cours.pk) if en_cours else ''
    elif trimestre_id not in trimestre_ids_valides:
        trimestre_id = ''

    if classe_id:
        evaluations = evaluations.filter(enseignement__classe_id=classe_id)
    if trimestre_id:
        evaluations = evaluations.filter(trimestre_id=trimestre_id)
    if query:
        evaluations = evaluations.filter(
            Q(titre__icontains=query) |
            Q(enseignement__matiere__nom__icontains=query) |
            Q(enseignement__classe__nom__icontains=query)
        )

    # Pagination par classe : les classes ayant au moins une évaluation filtrée
    classes_filtrees = (
        Classe.objects
        .filter(enseignements__evaluations__in=evaluations.values('pk'))
        .distinct()
        .order_by('nom')
    )
    paginator = Paginator(classes_filtrees, EVALUATIONS_CLASSES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))
    classes_page = list(page_obj.object_list)
    total_evaluations = evaluations.count()

    # Nombre d'élèves actifs par classe (pour la progression)
    if annee_courante and classes_page:
        nb_eleves_map = {
            row['classe_id']: row['total']
            for row in Inscription.objects.filter(
                annee_scolaire=annee_courante,
                classe__in=classes_page,
            ).exclude(statut='ABANDON').values('classe_id').annotate(total=Count('id'))
        }
    else:
        nb_eleves_map = {}

    evaluations = list(
        evaluations
        .filter(enseignement__classe__in=classes_page)
        .select_related('enseignement__classe', 'enseignement__matiere', 'type_evaluation', 'trimestre')
        .annotate(nb_notes=Count('notes'))
        .order_by('enseignement__classe__nom', 'enseignement__matiere__nom', 'date_planifiee')
    ) if classes_page else []
    for ev in evaluations:
        ev.nb_eleves = nb_eleves_map.get(ev.enseignement.classe_id, 0)

    # Groupement : classe → matière → [évaluations], dans l'ordre de la page
    groupes = {classe: {} for classe in classes_page}
    for ev in evaluations:
        classe = ev.enseignement.classe
        matiere = ev.enseignement.matiere
        groupes.setdefault(classe, {}).setdefault(matiere, []).append(ev)

    groupes_liste = [
        {
            'classe': classe,
            'matieres': [
                {'matiere': mat, 'evaluations': evs}
                for mat, evs in matieres.items()
            ],
            'total': sum(len(evs) for evs in matieres.values()),
        }
        for classe, matieres in groupes.items()
        if matieres
    ]

    # Paramètres de filtre à conserver dans les liens de pagination
    # (le trimestre retenu est explicité pour que la page 2 montre la même chose)
    params = request.GET.copy()
    params.pop('page', None)
    params['trimestre'] = trimestre_id

    context = {
        'evaluation_list': evaluations,
        'groupes': groupes_liste,
        'query': query,
        'classe_id': classe_id,
        'trimestre_id': trimestre_id,
        'classes': classes,
        'trimestres': trimestres,
        'page_obj': page_obj,
        'total_evaluations': total_evaluations,
        'params': params.urlencode(),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'pedagogie/partials/evaluation_table.html', context)

    return render(request, 'pedagogie/evaluation_list.html', context)


def _resolve_trimestre(periode):
    """
    À partir d'une PeriodeEvaluation, trouve ou crée le pedagogie.Trimestre
    correspondant (même annee_scolaire + même numero).
    """
    trimestre, _ = Trimestre.objects.get_or_create(
        annee_scolaire=periode.annee_scolaire,
        numero=periode.numero,
        defaults={
            'nom': periode.nom,
            'type_periode': 'TRIMESTRE' if periode.type_periode == 'TRIMESTRE' else 'SEMESTRE',
            'date_debut': periode.date_debut,
            'date_fin': periode.date_fin,
        },
    )
    # Mettre à jour le nom si la PeriodeEvaluation a changé
    if trimestre.nom != periode.nom:
        trimestre.nom = periode.nom
        trimestre.save(update_fields=['nom'])
    return trimestre


@login_required
def evaluation_create(request):
    """Création d'une nouvelle évaluation."""
    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.trimestre = _resolve_trimestre(form.cleaned_data['periode'])
            evaluation.save()
            messages.success(request, f"Évaluation '{evaluation.titre}' planifiée.")
            return redirect('pedagogie:evaluation_list')
    else:
        form = EvaluationForm()

    return render(request, 'pedagogie/evaluation_form.html', {
        'form': form,
        'title': "Planifier une évaluation"
    })


@login_required
def evaluation_update(request, pk):
    """Modification d'une évaluation."""
    evaluation = get_object_or_404(
        Evaluation.objects.select_related('enseignement__classe'), pk=pk
    )
    etab = getattr(request.user, 'etablissement', None)

    if etab and evaluation.enseignement.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette évaluation n'appartient pas à votre établissement.")
        return redirect('pedagogie:evaluation_list')
    
    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.trimestre = _resolve_trimestre(form.cleaned_data['periode'])
            evaluation.save()
            messages.success(request, f"Évaluation mise à jour.")
            return redirect('pedagogie:evaluation_list')
    else:
        form = EvaluationForm(instance=evaluation)

    return render(request, 'pedagogie/evaluation_form.html', {
        'form': form,
        'title': "Modifier l'évaluation",
        'evaluation': evaluation
    })


@login_required
def evaluation_saisie(request, pk):
    """Saisie groupée des notes pour une évaluation."""
    import decimal
    from inscriptions.models import Inscription

    evaluation = get_object_or_404(
        Evaluation.objects.select_related(
            'enseignement__classe__cycle',
            'enseignement__matiere',
            'enseignement__annee_scolaire',
            'type_evaluation',
            'trimestre',
        ),
        pk=pk,
    )
    classe = evaluation.enseignement.classe
    enseignement = evaluation.enseignement
    trimestre = evaluation.trimestre

    # Vérification de sécurité - vérifier que l'enseignant enseigne cette matière
    if request.user.role == 'ENSEIGNANT':
        from pedagogie.models import Enseignement
        authorized = Enseignement.objects.filter(
            id=enseignement.pk,
            personnel=filtre_enseignant(request.user)
        ).exists()
        if not authorized and getattr(classe, 'professeur_principal_id', None) != getattr(filtre_enseignant(request.user), 'pk', object()):
            messages.error(request, "Vous n'êtes pas autorisé à saisir les notes de cette évaluation.")
            return redirect('pedagogie:evaluation_list')

    inscriptions = Inscription.objects.filter(
        classe=classe,
        annee_scolaire=enseignement.annee_scolaire,
    ).exclude(statut='ABANDON').select_related('eleve').order_by('eleve__nom', 'eleve__prenom')

    if request.method == 'POST':
        updated_count = 0
        errors = []

        for ins in inscriptions:
            dispense_vals = request.POST.getlist(f'disp_{ins.id}')
            est_dispense = 'on' in dispense_vals

            if est_dispense:
                Resultat.objects.update_or_create(
                    inscription=ins,
                    enseignement=enseignement,
                    trimestre=trimestre,
                    defaults={'dispense': True, 'moyenne': None, 'nb_notes': 0,
                              'coefficient_utilise': enseignement.get_coefficient()},
                )
                Note.objects.filter(inscription=ins, evaluation=evaluation).delete()
                continue

            # Désactive le dispense si la case est décochée
            Resultat.objects.filter(
                inscription=ins, enseignement=enseignement, trimestre=trimestre,
            ).update(dispense=False)

            # Gestion "Absent" : note = 0, observation = ABS
            absent_vals = request.POST.getlist(f'abs_{ins.id}')
            est_absent = 'on' in absent_vals
            
            note_vals = request.POST.getlist(f'note_{ins.id}')
            note_val = next((v.strip() for v in note_vals if v.strip() != ''), '')
            
            obs_vals = request.POST.getlist(f'obs_{ins.id}')
            obs_val = next((v.strip() for v in obs_vals if v.strip() != ''), '')

            if est_absent:
                valeur = decimal.Decimal('0.00')
                obs_val = obs_val or 'ABS'
            elif note_val:
                try:
                    valeur = decimal.Decimal(note_val.replace(',', '.'))
                except (decimal.InvalidOperation, ValueError):
                    errors.append(f"Valeur invalide pour {ins.eleve.nom}")
                    continue
                if valeur < 0:
                    errors.append(f"{ins.eleve.nom} : la note ne peut pas être négative.")
                    continue
                if valeur > evaluation.bareme:
                    errors.append(
                        f"{ins.eleve.nom} : note {valeur} dépasse le barème {evaluation.bareme}. "
                        f"Corrigez et re-soumettez."
                    )
                    continue
            else:
                continue  # Champ vide → on ne touche pas la note

            note, created = Note.objects.get_or_create(
                inscription=ins,
                evaluation=evaluation,
                defaults={'valeur': valeur, 'observation': obs_val},
            )
            if not created:
                note.valeur = valeur
                note.observation = obs_val
                note.save()
            updated_count += 1

        if errors:
            for e in errors:
                messages.warning(request, e)

        if updated_count > 0:
            evaluation.statut = 'TERMINEE'
            evaluation.save(update_fields=['statut'])
            messages.success(request, f"{updated_count} note(s) enregistrée(s).")

        return redirect('pedagogie:evaluation_saisie', pk=pk)

    # GET — préparer les données
    notes_dict = {
        n.inscription_id: n
        for n in Note.objects.filter(evaluation=evaluation)
    }

    dispenses_ids = set(
        Resultat.objects.filter(
            enseignement=enseignement,
            trimestre=trimestre,
            dispense=True,
        ).values_list('inscription_id', flat=True)
    )

    eleves_data = []
    for ins in inscriptions:
        note = notes_dict.get(ins.id)
        eleves_data.append({
            'inscription': ins,
            'note': note,
            'est_absent': note is not None and note.observation == 'ABS' and note.valeur == 0,
            'est_dispense': ins.id in dispenses_ids,
        })

    nb_total = len(eleves_data)
    nb_saisies = sum(1 for d in eleves_data if d['note'] is not None and not d['est_dispense'])

    return render(request, 'pedagogie/note_saisie.html', {
        'evaluation': evaluation,
        'eleves_data': eleves_data,
        'nb_total': nb_total,
        'nb_saisies': nb_saisies,
    })


@login_required
def saisie_rapide_classe(request, class_id):
    """Page de saisie rapide : sélection évaluation depuis une classe."""
    from inscriptions.models import Inscription
    from django.db.models import Count

    classe = get_object_or_404(Classe, pk=class_id)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    nb_eleves = Inscription.objects.filter(
        classe=classe, annee_scolaire=annee_courante,
    ).exclude(statut='ABANDON').count() if annee_courante else 0

    # Évaluations de la classe, annotées avec le nb de notes saisies
    evaluations = (
        Evaluation.objects
        .filter(enseignement__classe=classe, enseignement__annee_scolaire=annee_courante)
        .select_related('enseignement__matiere', 'type_evaluation', 'trimestre')
        .annotate(nb_notes=Count('notes'))
        .order_by('trimestre__numero', 'enseignement__matiere__nom', '-date_planifiee')
    )

    # Grouper par matière
    from collections import defaultdict
    par_matiere = defaultdict(list)
    for ev in evaluations:
        par_matiere[ev.enseignement.matiere].append(ev)

    return render(request, 'pedagogie/saisie_rapide_classe.html', {
        'classe': classe,
        'annee_courante': annee_courante,
        'nb_eleves': nb_eleves,
        'par_matiere': dict(par_matiere),
    })


@login_required
def saisie_classe_select(request):
    """Sélection de la classe pour la saisie des notes."""
    classes = Classe.objects.all().order_by('cycle__ordre', 'nom')
    return render(request, 'pedagogie/saisie_classe_select.html', {'classes': classes})
