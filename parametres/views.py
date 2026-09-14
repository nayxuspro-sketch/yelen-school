from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django import db
from django.db import models
from django.db.models.deletion import ProtectedError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from .forms import (
    TypeDocumentForm, SignataireForm,
    AnneeScolaireForm, CycleForm, ClasseForm, PosteForm, LocalisationPosteForm,
    StatutEleveForm, RubriquePaiementForm, AppreciationMoyenneSecondaireForm,
    AppreciationMoyennePrimaireForm, CategorieDisciplineForm, DisciplineForm,
    PeriodeEvaluationForm, TypeSanctionForm, TitreFonctionForm,
    TitreHonorifiquePersonnelForm, TypeEvaluationForm,
    EvenementCalendrierForm, IdentiteEtablissementForm,
)
from .models import (
    Cycle, AnneeScolaire, TypeDocument, SignataireDocument,
    Classe, Poste, LocalisationPoste, StatutEleve, RubriquePaiement, TarifScolarite,
    AppreciationMoyenneSecondaire, AppreciationMoyennePrimaire, PeriodeEvaluation, Discipline,
    CategorieDiscipline, TypeSanction, TitreFonction, TitreHonorifiquePersonnel,
    EvenementCalendrier, ModeleMessage,
)
from personnel.models import MembrePersonnel
from etablissements.models import Etablissement


def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


# ─── INDEX ───────────────────────────────────────────────────────────

@login_required
def parametres_index(request):
    etab = _get_etab(request)

    def count(model):
        return model.objects.filter(etablissement=etab).count() if etab else 0

    context = {
        'nb_annees':      count(AnneeScolaire),
        'nb_cycles':      count(Cycle),
        'nb_classes':     count(Classe),
        'nb_postes':      count(Poste),
        'nb_statuts':     count(StatutEleve),
        'nb_rubriques':   count(RubriquePaiement),
        'nb_tarifs':      count(TarifScolarite),
        'nb_appreciations': count(AppreciationMoyenneSecondaire),
        'nb_disciplines': count(Discipline),
        'nb_periodes':    count(PeriodeEvaluation),
        'nb_titres_fonctions':    TitreFonction.objects.count(),
        'nb_titres_honorifiques': TitreHonorifiquePersonnel.objects.count(),
        'nb_localisations': count(LocalisationPoste),
    }
    return render(request, 'parametres/index.html', context)


# ─── ANNÉES SCOLAIRES ────────────────────────────────────────────────

@login_required
def annee_list(request):
    etab = _get_etab(request)
    annees = AnneeScolaire.objects.filter(etablissement=etab) if etab else AnneeScolaire.objects.none()
    tpl = 'parametres/partials/annee_list.html' if request.headers.get('HX-Request') else 'parametres/annees.html'
    return render(request, tpl, {'annees': annees})


@login_required
def annee_form(request, pk=None):
    etab = _get_etab(request)
    annee = get_object_or_404(AnneeScolaire, pk=pk, etablissement=etab) if pk else None

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/annee_form.html', {
                'annee': annee,
                'error': "Votre compte n'est pas associé à un établissement.",
            })
        form = AnneeScolaireForm(request.POST, instance=annee)
        if form.is_valid():
            instance = form.save(commit=False)
            if not annee:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/annee_form.html', {
            'annee': annee, 'error': form.errors.as_text(),
        })

    return render(request, 'parametres/partials/annee_form.html', {'annee': annee})


@login_required
def annee_set_courante(request, pk):
    etab = _get_etab(request)
    annee = get_object_or_404(AnneeScolaire, pk=pk, etablissement=etab)
    annee.est_courante = True
    annee.save()
    return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})


# ─── CYCLES ──────────────────────────────────────────────────────────

@login_required
def cycle_list(request):
    etab = _get_etab(request)
    cycles = Cycle.objects.filter(etablissement=etab).prefetch_related('classes').order_by('ordre', 'nom') if etab else Cycle.objects.none()
    tpl = 'parametres/partials/cycle_tree.html' if request.headers.get('HX-Request') else 'parametres/cycles.html'
    return render(request, tpl, {'cycles': cycles})


@login_required
def cycle_form(request, pk=None):
    etab = _get_etab(request)
    cycle = get_object_or_404(Cycle, pk=pk, etablissement=etab) if pk else None
    ctx = {'cycle': cycle, 'code_choices': Cycle.CODE_CHOICES}

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/cycle_form.html', {**ctx, 'error': "Votre compte n'est pas associé à un établissement."})
        form = CycleForm(request.POST, instance=cycle)
        if form.is_valid():
            instance = form.save(commit=False)
            if not cycle:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/cycle_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/cycle_form.html', ctx)


# ─── CLASSES ─────────────────────────────────────────────────────────

@login_required
def classe_list(request):
    etab = _get_etab(request)
    query = request.GET.get('q', '')
    page_number = request.GET.get('page', 1)

    classes = (
        Classe.objects.filter(etablissement=etab)
        .select_related('cycle')
        .order_by('cycle__ordre', 'nom')
        if etab else Classe.objects.none()
    )
    if query:
        classes = classes.filter(
            Q(nom__icontains=query) | Q(cycle__nom__icontains=query)
        )

    paginator = Paginator(classes, 30)
    page_obj = paginator.get_page(page_number)

    ctx = {'classes': page_obj, 'page_obj': page_obj, 'query': query}
    tpl = 'parametres/partials/classe_list.html' if request.headers.get('HX-Request') else 'parametres/classes.html'
    return render(request, tpl, ctx)


@login_required
def classe_form(request, pk=None):
    etab = _get_etab(request)
    classe = get_object_or_404(Classe, pk=pk, etablissement=etab) if pk else None
    cycles = Cycle.objects.filter(etablissement=etab, actif=True) if etab else Cycle.objects.none()
    ctx = {
        'classe': classe, 'cycles': cycles,
        'type_examen_choices': Classe._meta.get_field('type_examen').choices,
        'serie_bac_choices': Classe._meta.get_field('serie_bac').choices,
    }

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/classe_form.html', {**ctx, 'error': "Votre compte n'est pas associé à un établissement."})
        form = ClasseForm(request.POST, instance=classe, etablissement=etab)
        if form.is_valid():
            instance = form.save(commit=False)
            if not classe:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/classe_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/classe_form.html', ctx)


# ─── POSTES ──────────────────────────────────────────────────────────

@login_required
def poste_list(request):
    etab = _get_etab(request)
    postes = Poste.objects.filter(etablissement=etab) if etab else Poste.objects.none()
    tpl = 'parametres/partials/poste_list.html' if request.headers.get('HX-Request') else 'parametres/postes.html'
    return render(request, tpl, {'postes': postes})


@login_required
def poste_form(request, pk=None):
    etab = _get_etab(request)
    poste = get_object_or_404(Poste, pk=pk, etablissement=etab) if pk else None
    ctx = {'poste': poste, 'categorie_choices': Poste._meta.get_field('categorie').choices}

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/poste_form.html', {**ctx, 'error': "Votre compte n'est pas associé à un établissement."})
        form = PosteForm(request.POST, instance=poste)
        if form.is_valid():
            instance = form.save(commit=False)
            if not poste:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/poste_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/poste_form.html', ctx)


# ─── LOCALISATIONS ───────────────────────────────────────────────────

@login_required
def localisation_list(request):
    etab = _get_etab(request)
    localisations = LocalisationPoste.objects.filter(etablissement=etab).order_by('type_localisation', 'nom') if etab else LocalisationPoste.objects.none()
    tpl = 'parametres/partials/localisation_list.html' if request.headers.get('HX-Request') else 'parametres/localisations.html'
    return render(request, tpl, {'localisations': localisations})


@login_required
def localisation_form(request, pk=None):
    etab = _get_etab(request)
    localisation = get_object_or_404(LocalisationPoste, pk=pk, etablissement=etab) if pk else None
    ctx = {
        'localisation': localisation,
        'type_choices': LocalisationPoste._meta.get_field('type_localisation').choices,
    }

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/localisation_form.html', {**ctx, 'error': "Votre compte n'est pas associé à un établissement."})
        form = LocalisationPosteForm(request.POST, instance=localisation)
        if form.is_valid():
            instance = form.save(commit=False)
            if not localisation:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/localisation_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/localisation_form.html', ctx)


@login_required
@require_POST
def localisation_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(LocalisationPoste, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


# ─── STATUTS ÉLÈVE ───────────────────────────────────────────────────

@login_required
def statut_list(request):
    etab = _get_etab(request)
    statuts = StatutEleve.objects.filter(etablissement=etab) if etab else StatutEleve.objects.none()
    tpl = 'parametres/partials/statut_list.html' if request.headers.get('HX-Request') else 'parametres/statuts.html'
    return render(request, tpl, {'statuts': statuts})


@login_required
def statut_form(request, pk=None):
    etab = _get_etab(request)
    statut = get_object_or_404(StatutEleve, pk=pk, etablissement=etab) if pk else None

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/statut_form.html', {'statut': statut, 'error': "Votre compte n'est pas associé à un établissement."})
        form = StatutEleveForm(request.POST, instance=statut)
        if form.is_valid():
            instance = form.save(commit=False)
            if not statut:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/statut_form.html', {'statut': statut, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/statut_form.html', {'statut': statut})


# ─── RUBRIQUES PAIEMENT ──────────────────────────────────────────────

@login_required
def rubrique_list(request):
    etab = _get_etab(request)
    rubriques = RubriquePaiement.objects.filter(etablissement=etab) if etab else RubriquePaiement.objects.none()
    tpl = 'parametres/partials/rubrique_list.html' if request.headers.get('HX-Request') else 'parametres/rubriques.html'
    return render(request, tpl, {'rubriques': rubriques})


@login_required
def rubrique_form(request, pk=None):
    etab = _get_etab(request)
    if not etab:
        return render(request, "parametres/partials/rubrique_form.html", {"rubrique": None, "error": "Aucun établissement trouvé pour votre compte."})
    rubrique = get_object_or_404(RubriquePaiement, pk=pk, etablissement=etab) if pk else None

    if request.method == 'POST':
        form = RubriquePaiementForm(request.POST, instance=rubrique)
        if form.is_valid():
            instance = form.save(commit=False)
            if not rubrique:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/rubrique_form.html', {'rubrique': rubrique, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/rubrique_form.html', {'rubrique': rubrique})


@login_required
def rubrique_toggle_actif(request, pk):
    etab = _get_etab(request)
    rubrique = get_object_or_404(RubriquePaiement, pk=pk, etablissement=etab)
    rubrique.actif = not rubrique.actif
    rubrique.save(update_fields=['actif'])
    return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})


# ─── TARIFS SCOLARITÉ ────────────────────────────────────────────────

@login_required
def tarif_toggle_actif(request, pk):
    """Toggle actif/inactif pour TOUS les tarifs du même groupe (annee × niveau × statut × rubrique)."""
    etab = _get_etab(request)
    tarif = get_object_or_404(TarifScolarite, pk=pk, etablissement=etab)
    nouvel_actif = not tarif.actif
    # Appliquer à tous les tarifs du même groupe
    TarifScolarite.objects.filter(
        etablissement=etab,
        annee_scolaire=tarif.annee_scolaire,
        classe__niveau=tarif.classe.niveau,
        statut_eleve=tarif.statut_eleve,
        rubrique=tarif.rubrique,
    ).update(actif=nouvel_actif)
    return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})

@login_required
def tarif_list(request):
    etab = _get_etab(request)
    tarifs = (
        TarifScolarite.objects.filter(etablissement=etab)
        .select_related('annee_scolaire', 'classe', 'statut_eleve', 'rubrique')
        .order_by('annee_scolaire__libelle', 'classe__niveau', 'statut_eleve__nom', 'rubrique__ordre')
        if etab else TarifScolarite.objects.none()
    )
    annee_id = request.GET.get('annee')
    niveau_filter = request.GET.get('niveau')
    if annee_id:
        tarifs = tarifs.filter(annee_scolaire_id=annee_id)
    if niveau_filter:
        tarifs = tarifs.filter(classe__niveau=niveau_filter)

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle') if etab else []
    niveaux = list(
        Classe.objects.filter(etablissement=etab)
        .values_list('niveau', flat=True).order_by('niveau').distinct()
    ) if etab else []

    # Regrouper par niveau
    groups_by_niveau = defaultdict(list)
    for t in tarifs:
        groups_by_niveau[t.classe.niveau or ''].append(t)

    # Trier les tarifs à l'intérieur de chaque groupe
    for grp in groups_by_niveau.values():
        grp.sort(key=lambda t: (
            t.classe.nom,
            t.statut_eleve.nom if t.statut_eleve else '',
            t.rubrique.ordre if hasattr(t.rubrique, 'ordre') else 0,
        ))

    # Trier les groupes par niveau puis paginer (5 niveaux par page)
    grouped_tarifs_all = sorted(groups_by_niveau.items(), key=lambda x: x[0])
    page_number = request.GET.get('page', 1)
    paginator = Paginator(grouped_tarifs_all, 5)
    page_obj = paginator.get_page(page_number)
    grouped_tarifs = list(page_obj.object_list)

    ctx = {
        'grouped_tarifs': grouped_tarifs,
        'page_obj': page_obj,
        'annees': annees,
        'niveaux': niveaux,
        'selected_annee': annee_id,
        'selected_niveau': niveau_filter,
    }
    # Ajouter csrf_token pour les boutons HTMX POST
    from django.middleware.csrf import get_token
    ctx['csrf_token'] = get_token(request)
    
    tpl = 'parametres/partials/tarif_list.html' if request.headers.get('HX-Request') else 'parametres/tarifs.html'
    return render(request, tpl, ctx)


@login_required
def tarif_form(request, pk=None):
    etab = _get_etab(request)
    tarif = get_object_or_404(TarifScolarite, pk=pk, etablissement=etab) if pk else None

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle') if etab else []
    cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre') if etab else []
    niveaux = list(
        Classe.objects.filter(etablissement=etab, actif=True)
        .values_list('niveau', flat=True).order_by('niveau').distinct()
    ) if etab else []
    statuts = StatutEleve.objects.filter(etablissement=etab, actif=True).order_by('ordre') if etab else []
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom') if etab else []

    ctx = {
        'tarif': tarif,
        'annees': annees,
        'cycles': cycles,
        'niveaux': niveaux,
        'statuts': statuts,
        'rubriques': rubriques,
    }

    if request.method == 'POST':
        if not etab:
            ctx['error'] = "Votre compte n'est pas associé à un établissement."
            return render(request, 'parametres/partials/tarif_form.html', ctx)
        d = request.POST
        try:
            annee = get_object_or_404(AnneeScolaire, pk=d['annee_scolaire'], etablissement=etab)
            rub = get_object_or_404(RubriquePaiement, pk=d['rubrique'], etablissement=etab)
            montant = Decimal(str(d.get('montant') or '0').replace(',', '.'))
            cycle_val = d.get('cycle', '').strip()
            
            if tarif:
                # Modification : mise à jour du tarif existant
                niveau_val = d.get('niveau', '').strip()
                statut_val = d.get('statut_eleve', '').strip()
                
                # Gérer le niveau (peut être __all__ pour tous les niveaux)
                if niveau_val and niveau_val != '__all__':
                    # Si un niveau spécifique est sélectionné, vérifier qu'il correspond à la classe
                    if tarif.classe.niveau != niveau_val:
                        # Trouver une classe du même niveau
                        classe_same_niveau = Classe.objects.filter(
                            etablissement=etab, niveau=niveau_val, actif=True
                        ).first()
                        if classe_same_niveau:
                            tarif.classe = classe_same_niveau
                
                # Gérer le statut (peut être __all__ pour tous les statuts)
                if statut_val and statut_val != '__all__':
                    tarif.statut_eleve = get_object_or_404(StatutEleve, pk=statut_val, etablissement=etab)
                # Si __all__, garder le statut existant
                
                tarif.annee_scolaire = annee
                tarif.rubrique = rub
                tarif.montant = montant
                tarif.actif = 'actif' in d
                # Mettre à jour le cycle si fourni
                if cycle_val and cycle_val != '__all__':
                    tarif.cycle = get_object_or_404(Cycle, pk=cycle_val, etablissement=etab)
                else:
                    tarif.cycle = None
                # Vérifier doublon avant sauvegarde
                duplicate = TarifScolarite.objects.filter(
                    classe=tarif.classe,
                    statut_eleve=tarif.statut_eleve,
                    rubrique=rub,
                    annee_scolaire=annee,
                ).exclude(pk=tarif.pk).first()
                if duplicate:
                    raise ValueError(
                        f"Un tarif existe déjà pour cette combinaison "
                        f"({tarif.classe.nom} / {tarif.statut_eleve.nom} / {rub.nom} / {annee.libelle})."
                    )
                tarif.save()
            else:
                # Création : résoudre niveaux et statuts cibles
                niveau = d.get('niveau', '').strip()
                statut_val = d.get('statut_eleve', '').strip()
                if not niveau:
                    raise ValueError("Le niveau est obligatoire.")
                if not statut_val:
                    raise ValueError("Le statut élève est obligatoire.")

                # Filtrer par cycle si sélectionné
                if cycle_val and cycle_val != '__all__':
                    cycle_obj = get_object_or_404(Cycle, pk=cycle_val, etablissement=etab)
                    classes_cibles = (
                        Classe.objects.filter(etablissement=etab, actif=True, cycle=cycle_obj)
                        if niveau == '__all__'
                        else Classe.objects.filter(etablissement=etab, actif=True, cycle=cycle_obj, niveau=niveau)
                    )
                else:
                    classes_cibles = (
                        Classe.objects.filter(etablissement=etab, actif=True)
                        if niveau == '__all__'
                        else Classe.objects.filter(etablissement=etab, actif=True, niveau=niveau)
                    )
                statuts_cibles = (
                    StatutEleve.objects.filter(etablissement=etab, actif=True)
                    if statut_val == '__all__'
                    else StatutEleve.objects.filter(pk=statut_val, etablissement=etab)
                )
                if not classes_cibles.exists():
                    raise ValueError("Aucune classe active trouvée.")
                if not statuts_cibles.exists():
                    raise ValueError("Aucun statut élève actif trouvé.")

                # Récupérer l'objet cycle si sélectionné
                cycle_obj = None
                if cycle_val and cycle_val != '__all__':
                    cycle_obj = get_object_or_404(Cycle, pk=cycle_val, etablissement=etab)

                for classe in classes_cibles:
                    for statut in statuts_cibles:
                        TarifScolarite.objects.update_or_create(
                            etablissement=etab,
                            classe=classe,
                            statut_eleve=statut,
                            rubrique=rub,
                            annee_scolaire=annee,
                            defaults={
                                'montant': montant, 
                                'actif': True,
                                'cycle': cycle_obj,
                            },
                        )
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        except Exception as e:
            ctx['error'] = str(e)
            return render(request, 'parametres/partials/tarif_form.html', ctx)

    return render(request, 'parametres/partials/tarif_form.html', ctx)


# ─── APPRÉCIATIONS CONDUITE ──────────────────────────────────────────

@login_required
def appreciation_list(request):
    etab = _get_etab(request)
    appreciations = AppreciationMoyenneSecondaire.objects.filter(etablissement=etab) if etab else AppreciationMoyenneSecondaire.objects.none()
    tpl = 'parametres/partials/appreciation_list.html' if request.headers.get('HX-Request') else 'parametres/appreciations.html'
    return render(request, tpl, {'appreciations': appreciations})


@login_required
def appreciation_form(request, pk=None):
    etab = _get_etab(request)
    appr = get_object_or_404(AppreciationMoyenneSecondaire, pk=pk, etablissement=etab) if pk else None

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/appreciation_form.html', {'appr': appr, 'error': "Votre compte n'est pas associé à un établissement."})
        form = AppreciationMoyenneSecondaireForm(request.POST, instance=appr)
        if form.is_valid():
            instance = form.save(commit=False)
            if not appr:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/appreciation_form.html', {'appr': appr, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/appreciation_form.html', {'appr': appr})


# ─── APPRÉCIATIONS MOYENNE PRIMAIRE ─────────────────────────────────────

@login_required
def appreciation_primaire_list(request):
    etab = _get_etab(request)
    appreciations = AppreciationMoyennePrimaire.objects.filter(etablissement=etab) if etab else AppreciationMoyennePrimaire.objects.none()
    tpl = 'parametres/partials/appreciation_primaire_list.html' if request.headers.get('HX-Request') else 'parametres/appreciations_primaire.html'
    return render(request, tpl, {'appreciations': appreciations})


@login_required
def appreciation_primaire_form(request, pk=None):
    etab = _get_etab(request)
    appr = get_object_or_404(AppreciationMoyennePrimaire, pk=pk, etablissement=etab) if pk else None

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/appreciation_primaire_form.html', {'appr': appr, 'error': "Votre compte n'est pas associé à un établissement."})
        form = AppreciationMoyennePrimaireForm(request.POST, instance=appr)
        if form.is_valid():
            instance = form.save(commit=False)
            if not appr:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/appreciation_primaire_form.html', {'appr': appr, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/appreciation_primaire_form.html', {'appr': appr})


# ─── CATÉGORIES DISCIPLINES ───────────────────────────────────────────

@login_required
def categorie_discipline_list(request):
    etab = _get_etab(request)
    categories = CategorieDiscipline.objects.filter(etablissement=etab) if etab else CategorieDiscipline.objects.none()
    tpl = 'parametres/partials/categorie_discipline_list.html' if request.headers.get('HX-Request') else 'parametres/categories_disciplines.html'
    return render(request, tpl, {'categories': categories})


@login_required
def categorie_discipline_form(request, pk=None):
    etab = _get_etab(request)
    categorie = get_object_or_404(CategorieDiscipline, pk=pk, etablissement=etab) if pk else None

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/categorie_discipline_form.html', {'categorie': categorie, 'error': "Votre compte n'est pas associé à un établissement."})
        form = CategorieDisciplineForm(request.POST, instance=categorie)
        if form.is_valid():
            instance = form.save(commit=False)
            if not categorie:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/categorie_discipline_form.html', {'categorie': categorie, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/categorie_discipline_form.html', {'categorie': categorie})


# ─── DISCIPLINES ─────────────────────────────────────────────────────

@login_required
def discipline_list(request):
    etab = _get_etab(request)
    disciplines = Discipline.objects.filter(etablissement=etab).select_related('cycle', 'categorie') if etab else Discipline.objects.none()
    tpl = 'parametres/partials/discipline_list.html' if request.headers.get('HX-Request') else 'parametres/disciplines.html'
    return render(request, tpl, {'disciplines': disciplines})


@login_required
def discipline_form(request, pk=None):
    etab = _get_etab(request)
    discipline = get_object_or_404(Discipline, pk=pk, etablissement=etab) if pk else None
    cycles = Cycle.objects.filter(etablissement=etab, actif=True) if etab else Cycle.objects.none()
    categories = CategorieDiscipline.objects.filter(etablissement=etab, actif=True) if etab else CategorieDiscipline.objects.none()
    ctx = {'discipline': discipline, 'cycles': cycles, 'categories': categories}

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/discipline_form.html', {**ctx, 'error': "Votre compte n'est pas associé à un établissement."})
        form = DisciplineForm(request.POST, instance=discipline, etablissement=etab)
        if form.is_valid():
            instance = form.save(commit=False)
            if not discipline:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/discipline_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/discipline_form.html', ctx)


# ─── PÉRIODES ÉVALUATION ─────────────────────────────────────────────

@login_required
def periode_list(request):
    etab = _get_etab(request)
    periodes = PeriodeEvaluation.objects.filter(etablissement=etab).select_related('annee_scolaire') if etab else PeriodeEvaluation.objects.none()
    tpl = 'parametres/partials/periode_list.html' if request.headers.get('HX-Request') else 'parametres/periodes.html'
    return render(request, tpl, {'periodes': periodes})


@login_required
def periode_form(request, pk=None):
    etab = _get_etab(request)
    periode = get_object_or_404(PeriodeEvaluation, pk=pk, etablissement=etab) if pk else None
    annees = AnneeScolaire.objects.filter(etablissement=etab) if etab else AnneeScolaire.objects.none()
    ctx = {'periode': periode, 'annees': annees, 'type_choices': PeriodeEvaluation.TYPE_CHOICES}

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/periode_form.html', {**ctx, 'error': "Votre compte n'est pas associé à un établissement."})
        form = PeriodeEvaluationForm(request.POST, instance=periode, etablissement=etab)
        if form.is_valid():
            instance = form.save(commit=False)
            if not periode:
                instance.etablissement = etab
            instance.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/periode_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/periode_form.html', ctx)


# ─── SIGNATAIRES ─────────────────────────────────────────────────────

@login_required
def signataire_config(request):
    """
    Interface tabulaire : onglet par cycle × cartes par catégorie de documents.
    GET  : affiche la grille de configuration.
    POST : enregistre le signataire pour un cycle × catégorie × année.
    """
    etab = _get_etab(request)
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_id = request.GET.get('annee') or request.POST.get('annee_id')
    annee = AnneeScolaire.objects.filter(id=annee_id, etablissement=etab).first() \
            if annee_id else AnneeScolaire.objects.get_annee_courante(etablissement=etab)

    if request.method == 'POST':
        annee_id = request.POST.get('annee_id')
        annee = AnneeScolaire.objects.filter(id=annee_id, etablissement=etab).first() \
            if annee_id else AnneeScolaire.objects.get_annee_courante(etablissement=etab)
        cycle_id = request.POST.get('cycle_id')
        categorie = request.POST.get('categorie')

        form = SignataireForm(request.POST, etablissement=etab)
        if form.is_valid() and cycle_id and categorie and annee:
            membre = form.cleaned_data['membre_personnel']
            fonction = form.cleaned_data['fonction'] or 'Le Directeur'
            titre_h = form.cleaned_data['titre_honorifique']
            try:
                cycle = Cycle.objects.get(id=cycle_id, etablissement=etab)
                types = TypeDocument.objects.filter(
                    Q(cycle=cycle) | Q(cycle__isnull=True),
                    categorie=categorie,
                    actif=True,
                )
                for td in types:
                    SignataireDocument.objects.update_or_create(
                        cycle=cycle,
                        type_document=td,
                        annee_scolaire=annee,
                        defaults={
                            'membre_personnel_id': membre.id,
                            'fonction': fonction,
                            'titre_honorifique': titre_h,
                            'titres_honorifiques': [titre_h] if titre_h else [],
                            'actif': True,
                        }
                    )
                messages.success(request, f"Signataire enregistré pour {cycle.nom} · {categorie}.")
            except Exception as e:
                messages.error(request, f"Erreur : {e}")
        return redirect(f"{request.path}?annee={annee.id if annee else ''}")

    # ── Construction des données pour le template ──
    cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre')
    personnel = MembrePersonnel.objects.filter(etablissement=etab, is_active=True).order_by('nom', 'prenom')
    categories = TypeDocument.CategorieChoices.choices

    cycles_data = []
    for cycle in cycles:
        total_configured = 0
        total_docs = 0
        categories_data = []
        for cat_val, cat_label in categories:
            type_docs = list(TypeDocument.objects.filter(
                Q(cycle=cycle) | Q(cycle__isnull=True),
                categorie=cat_val,
                actif=True,
            ))
            if not type_docs:
                continue
            sigs = {}
            if annee:
                for td in type_docs:
                    sig = SignataireDocument.objects.filter(
                        cycle=cycle, type_document=td, annee_scolaire=annee, actif=True
                    ).first()
                    sigs[str(td.id)] = sig
            configured = sum(1 for s in sigs.values() if s)
            total_configured += configured
            total_docs += len(type_docs)

            # Signataire "représentatif" pour pré-remplir le formulaire
            sig_ref = next((s for s in sigs.values() if s), None)
            categories_data.append({
                'value':      cat_val,
                'label':      cat_label,
                'type_docs':  type_docs,
                'configured': configured,
                'total':      len(type_docs),
                'sig_ref':    sig_ref,
            })
        cycles_data.append({
            'cycle':             cycle,
            'categories':        categories_data,
            'total_configured':  total_configured,
            'total_docs':        total_docs,
        })

    return render(request, 'parametres/signataire_config_tabs.html', {
        'annees':              annees,
        'annee':               annee,
        'cycles_data':         cycles_data,
        'personnel':           personnel,
        'fonctions':           TitreFonction.objects.filter(actif=True).order_by('nom'),
        'titres_honorifiques': TitreHonorifiquePersonnel.objects.filter(actif=True).order_by('nom'),
    })

@login_required
def signataires_list(request):
    etab = _get_etab(request)
    cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre')
    context = {
        'cycles': cycles,
        'active_cycle': cycles.first(),
    }
    return render(request, 'parametres/signataires_config.html', context)


@login_required
def signataires_list_detail(request, cycle_id):
    cycle = get_object_or_404(Cycle, id=cycle_id)
    etab = cycle.etablissement
    annee = AnneeScolaire.objects.get_annee_courante(etablissement=etab)

    if not annee:
        return HttpResponse(
            '<div class="p-12 text-center text-slate-500">'
            'Aucune année scolaire active trouvée.'
            '</div>',
            status=400
        )

    types_documents = TypeDocument.objects.filter(
        Q(cycle=cycle) | Q(cycle__isnull=True),
        actif=True,
    )
    signataires = {
        s.type_document_id: s
        for s in SignataireDocument.objects.filter(cycle=cycle, annee_scolaire=annee)
    }

    docs_config = [
        {'type': td, 'signataire': signataires.get(td.id)}
        for td in types_documents
    ]

    return render(request, 'parametres/partials/signataires_list_detail.html', {
        'cycle': cycle,
        'docs_config': docs_config,
    })


_TITRES_HONORIFIQUES_PREDEFINED = [
    "M. le Directeur",
    "Mme la Directrice",
    "M. le Proviseur",
    "Mme la Proviseure",
    "M. le Censeur",
    "Mme la Censeure",
    "M. le Sous-Directeur",
    "Mme la Sous-Directrice",
    "M. le Chef d'Établissement",
    "Mme la Chef d'Établissement",
    "Le Directeur",
    "La Directrice",
    "Le Proviseur",
    "Dr.",
    "Pr.",
    "M.",
    "Mme",
]


@login_required
def signataire_edit(request, cycle_id, document_type_id):
    cycle = get_object_or_404(Cycle, id=cycle_id)
    doc_type = get_object_or_404(TypeDocument, id=document_type_id)
    etab = cycle.etablissement
    annee = AnneeScolaire.objects.get_annee_courante(etablissement=etab)

    if not annee:
        return HttpResponse('Aucune année scolaire active trouvée.', status=400)

    signataire = SignataireDocument.objects.filter(
        cycle=cycle, type_document=doc_type, annee_scolaire=annee
    ).first()

    initial = {}
    if signataire:
        membre = signataire.get_membre_personnel()
        initial = {
            'membre_personnel': membre,
            'fonction': signataire.fonction,
            'titre_honorifique': signataire.titre_honorifique,
        }

    if request.method == 'POST':
        form = SignataireForm(request.POST, etablissement=etab)
        if form.is_valid():
            membre = form.cleaned_data['membre_personnel']
            fonction = form.cleaned_data['fonction']
            titre = form.cleaned_data['titre_honorifique']
            if signataire:
                signataire.set_membre_personnel(membre)
                signataire.fonction = fonction
                signataire.titre_honorifique = titre
                signataire.titres_honorifiques = [titre] if titre else []
                signataire.save()
            else:
                SignataireDocument.objects.create(
                    cycle=cycle,
                    type_document=doc_type,
                    annee_scolaire=annee,
                    membre_personnel_id=membre.id,
                    fonction=fonction,
                    titre_honorifique=titre,
                    titres_honorifiques=[titre] if titre else [],
                )
            return HttpResponse(status=204, headers={'HX-Trigger': 'signataireUpdated'})
    else:
        form = SignataireForm(initial=initial, etablissement=etab)

    return render(request, 'parametres/partials/signataire_form.html', {
        'cycle': cycle,
        'doc_type': doc_type,
        'signataire': signataire,
        'form': form,
        'fonctions': TitreFonction.objects.filter(actif=True).order_by('nom'),
        'titres_honorifiques': list(
            TitreHonorifiquePersonnel.objects.filter(actif=True).values_list('nom', flat=True)
        ),
    })


# ─── ÉTABLISSEMENT ────────────────────────────────────────────────────

@login_required
def etablissement_edit(request):
    etab = _get_etab(request)
    
    if not etab and request.user.is_superuser:
        etab = Etablissement.objects.first()
    
    if not etab and request.user.is_superuser:
        etab = Etablissement.objects.create(
            nom="Mon Établissement",
            code="ETAB001",
            pays="Burkina Faso"
        )
        request.user.etablissement = etab
        request.user.save()
    
    if not etab:
        return render(request, 'parametres/etablissement.html', {
            'etablissement': None,
            'error': "Votre compte n'est pas associé à un établissement.",
        })

    if request.method == 'POST':
        d = request.POST
        try:
            etab.nom = d.get('nom', etab.nom)
            etab.code = d.get('code', etab.code)
            etab.adresse = d.get('adresse', etab.adresse)
            etab.telephone = d.get('telephone', etab.telephone)
            etab.email = d.get('email', etab.email)
            etab.ville = d.get('ville', etab.ville)
            etab.pays = d.get('pays', etab.pays)
            if 'logo' in request.FILES:
                etab.logo = request.FILES['logo']
            etab.save()
            return render(request, 'parametres/etablissement.html', {
                'etablissement': etab,
                'success': "Établissement mis à jour avec succès.",
            })
        except Exception as e:
            return render(request, 'parametres/etablissement.html', {
                'etablissement': etab,
                'error': str(e),
            })

    return render(request, 'parametres/etablissement.html', {'etablissement': etab})


@login_required
def identite_etablissement(request):
    """Vue pour configurer l'identité de l'établissement (logo, adresse, contacts, signature)."""
    from parametres.models import IdentiteEtablissement
    
    etab = _get_etab(request)
    
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('core:index')
    
    identite = IdentiteEtablissement.objects.filter(etablissement=etab).first()
    
    if request.method == 'POST':
        form = IdentiteEtablissementForm(request.POST, request.FILES, instance=identite)
        if form.is_valid():
            instance = form.save(commit=False)
            if not identite:
                instance.etablissement = etab
            instance.save()
            messages.success(request, "Identité de l'établissement mise à jour avec succès.")
        else:
            messages.error(request, form.errors.as_text())

    return render(request, 'parametres/identite_etablissement.html', {
        'identite': identite,
        'etablissement': etab,
    })


# ─── TYPES DE DOCUMENTS ─────────────────────────────────────────────────

@login_required
def type_document_list(request):
    types_documents = TypeDocument.objects.all().select_related('cycle').order_by('cycle__nom', 'categorie', 'libelle')
    tpl = 'parametres/partials/type_document_list.html' if request.headers.get('HX-Request') else 'parametres/types_documents.html'
    return render(request, tpl, {'types_documents': types_documents})


@login_required
def type_document_form(request, pk=None):
    type_doc = get_object_or_404(TypeDocument, pk=pk) if pk else None

    if request.method == 'POST':
        form = TypeDocumentForm(request.POST, instance=type_doc)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
    else:
        form = TypeDocumentForm(instance=type_doc)

    return render(request, 'parametres/partials/type_document_form.html', {
        'type_doc': type_doc,
        'form': form,
    })


@login_required
def signataire_formulaire(request):
    """
    Page standalone pour créer/modifier un signataire avec 5 sélecteurs.
    Accessible directement depuis le menu latéral.
    """
    etab = _get_etab(request)
    if not etab:
        return render(request, 'parametres/signataire_formulaire.html', {
            'error': "Votre compte n'est pas associé à un établissement.",
        })

    annee_courante = AnneeScolaire.objects.get_annee_courante(etablissement=etab)
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    cycles = Cycle.objects.filter(etablissement=etab).order_by('ordre', 'nom')
    personnel = MembrePersonnel.objects.filter(etablissement=etab).order_by('nom', 'prenom')

    titres_fonctions = TitreFonction.objects.filter(actif=True).order_by('nom')
    titres_honorifiques = list(
        TitreHonorifiquePersonnel.objects.filter(actif=True).values_list('nom', flat=True)
    )

    annee = annee_courante
    selected_annee_id = str(annee.id) if annee else ''

    context = {
        'annees': annees,
        'cycles': cycles,
        'categories': TypeDocument.CategorieChoices.choices,
        'personnel': personnel,
        'fonctions': titres_fonctions,
        'titres_honorifiques': titres_honorifiques,
        'annee': annee,
        'selected_annee_id': selected_annee_id,
        'selected_cycle_id': '',
        'selected_categorie': '',
        'selected_fonction': '',
        'selected_membre_id': '',
        'selected_titre': '',
    }

    if request.method == 'POST':
        annee_id = request.POST.get('annee_id')
        cycle_id = request.POST.get('cycle_id')
        categorie = request.POST.get('categorie')

        if annee_id:
            try:
                annee = AnneeScolaire.objects.get(id=annee_id, etablissement=etab)
                selected_annee_id = str(annee.id)
            except AnneeScolaire.DoesNotExist:
                annee = annee_courante
                selected_annee_id = str(annee.id) if annee else ''

        form = SignataireForm(request.POST, etablissement=etab)
        context.update({
            'form': form,
            'annee': annee,
            'selected_annee_id': selected_annee_id,
            'selected_cycle_id': cycle_id or '',
            'selected_categorie': categorie or '',
        })

        if not form.is_valid() or not all([cycle_id, categorie, annee]):
            if not all([cycle_id, categorie]):
                context['error'] = "Le cycle et la catégorie sont obligatoires."
            elif not annee:
                context['error'] = "Aucune année scolaire active trouvée."
            return render(request, 'parametres/signataire_formulaire.html', context)

        membre = form.cleaned_data['membre_personnel']
        fonction = form.cleaned_data['fonction']
        titre = form.cleaned_data['titre_honorifique']

        try:
            cycles_cibles = (
                list(Cycle.objects.filter(etablissement=etab))
                if cycle_id == 'all'
                else [Cycle.objects.get(id=cycle_id, etablissement=etab)]
            )
            results = []
            for cycle in cycles_cibles:
                types_docs = TypeDocument.objects.filter(
                    actif=True, categorie=categorie
                ).filter(Q(cycle=cycle) | Q(cycle__isnull=True))
                for td in types_docs:
                    _, created = SignataireDocument.objects.update_or_create(
                        cycle=cycle,
                        type_document=td,
                        annee_scolaire=annee,
                        defaults={
                            'membre_personnel_id': str(membre.id),
                            'fonction': fonction,
                            'titre_honorifique': titre,
                            'titres_honorifiques': [titre] if titre else [],
                            'actif': True,
                        }
                    )
                    results.append(created)
            created_count = sum(1 for c in results if c)
            updated_count = len(results) - created_count
            messages.success(
                request,
                f"{created_count} signataire(s) créé(s), {updated_count} mis à jour."
            )
            return redirect('parametres:signataires_list')
        except Exception as e:
            context['error'] = f"Erreur : {str(e)}"
    else:
        context['form'] = SignataireForm(etablissement=etab)

    return render(request, 'parametres/signataire_formulaire.html', context)


@login_required
def type_sanction_list(request):
    types_sanctions = TypeSanction.objects.all()
    tpl = 'parametres/partials/type_sanction_list.html' if request.headers.get('HX-Request') else 'parametres/types_sanctions.html'
    return render(request, tpl, {'types_sanctions': types_sanctions})


@login_required
def type_sanction_form(request, pk=None):
    type_sanction = get_object_or_404(TypeSanction, pk=pk) if pk else None

    if request.method == 'POST':
        form = TypeSanctionForm(request.POST, instance=type_sanction)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/type_sanction_form.html', {'type_sanction': type_sanction, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/type_sanction_form.html', {'type_sanction': type_sanction})


# ─── TITRES FONCTIONS ─────────────────────────────────────────────

@login_required
def titre_fonction_list(request):
    titres = TitreFonction.objects.all()
    tpl = 'parametres/partials/titre_fonction_list.html' if request.headers.get('HX-Request') else 'parametres/titres_fonctions.html'
    return render(request, tpl, {'titres': titres})


@login_required
def titre_fonction_form(request, pk=None):
    titre = get_object_or_404(TitreFonction, pk=pk) if pk else None

    if request.method == 'POST':
        form = TitreFonctionForm(request.POST, instance=titre)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/titre_fonction_form.html', {'titre': titre, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/titre_fonction_form.html', {'titre': titre})


# ─── TITRES HONORIFIQUES ──────────────────────────────────────────

@login_required
def titre_honorifique_list(request):
    titres = TitreHonorifiquePersonnel.objects.all()
    tpl = 'parametres/partials/titre_honorifique_list.html' if request.headers.get('HX-Request') else 'parametres/titres_honorifiques.html'
    return render(request, tpl, {'titres': titres})


@login_required
def titre_honorifique_form(request, pk=None):
    titre = get_object_or_404(TitreHonorifiquePersonnel, pk=pk) if pk else None

    if request.method == 'POST':
        form = TitreHonorifiquePersonnelForm(request.POST, instance=titre)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/titre_honorifique_form.html', {'titre': titre, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/titre_honorifique_form.html', {'titre': titre})


# ─── TYPES D'ÉVALUATION ──────────────────────────────────────────────────────

@login_required
def type_evaluation_list(request):
    from pedagogie.models import TypeEvaluation
    types_eval = TypeEvaluation.objects.all().order_by('ordre', 'code')
    tpl = 'parametres/partials/type_evaluation_list.html' if request.headers.get('HX-Request') else 'parametres/types_evaluations.html'
    return render(request, tpl, {'types_eval': types_eval})


@login_required
def type_evaluation_form(request, pk=None):
    from pedagogie.models import TypeEvaluation
    type_eval = get_object_or_404(TypeEvaluation, pk=pk) if pk else None

    if request.method == 'POST':
        form = TypeEvaluationForm(request.POST, instance=type_eval)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/type_evaluation_form.html', {'type_eval': type_eval, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/type_evaluation_form.html', {'type_eval': type_eval})


# ═══════════════════════════════════════════════════════════════════
# VUES DE SUPPRESSION
# ═══════════════════════════════════════════════════════════════════

def _delete_view(request, obj):
    """Helper : supprime l'objet sur POST, renvoie 204 + HX-Trigger."""
    if request.method != 'POST':
        return HttpResponse(status=405)
    try:
        obj.delete()
        return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
    except ProtectedError as e:
        nb = len(e.protected_objects)
        return HttpResponse(
            f"Suppression impossible : {nb} enregistrement(s) lié(s) l'utilisent encore.",
            status=400,
        )
    except Exception as e:
        return HttpResponse(str(e), status=400)


@login_required
@require_POST
def annee_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(AnneeScolaire, pk=pk, etablissement=etab)
    n = obj.inscriptions.count()
    if n:
        return HttpResponse(
            f"Suppression impossible : {n} inscription(s) rattachée(s) à cette année scolaire.",
            status=400,
        )
    return _delete_view(request, obj)


@login_required
@require_POST
def cycle_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(Cycle, pk=pk, etablissement=etab)
    n = obj.classes.count()
    if n:
        return HttpResponse(
            f"Suppression impossible : {n} classe(s) appartiennent à ce cycle.",
            status=400,
        )
    return _delete_view(request, obj)


@login_required
@require_POST
def classe_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(Classe, pk=pk, etablissement=etab)
    n = obj.inscriptions.count()
    if n:
        return HttpResponse(
            f"Suppression impossible : {n} élève(s) inscrit(s) dans cette classe.",
            status=400,
        )
    return _delete_view(request, obj)


@login_required
@require_POST
def poste_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(Poste, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def statut_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(StatutEleve, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def rubrique_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(RubriquePaiement, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def tarif_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(TarifScolarite, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
def tarif_simulation(request):
    """Page de simulation tarifaire : sélectionner classe + statut → voir le total dû."""
    etab = _get_etab(request)
    annee_courante = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle') if etab else []
    classes = (
        Classe.objects.filter(etablissement=etab, actif=True)
        .select_related('cycle').order_by('cycle__ordre', 'nom')
        if etab else []
    )
    statuts = StatutEleve.objects.filter(etablissement=etab, actif=True).order_by('nom') if etab else []

    return render(request, 'parametres/simulation_tarifaire.html', {
        'annees': annees,
        'annee_courante': annee_courante,
        'classes': classes,
        'statuts': statuts,
        'etab': etab,
    })


@login_required
def tarif_simulation_resultat(request):
    """Partial HTMX : résultat de la simulation tarifaire."""
    import logging
    logger = logging.getLogger(__name__)
    
    etab = _get_etab(request)
    classe_id = request.GET.get('classe', '').strip()
    statut_id = request.GET.get('statut', '').strip()
    annee_id = request.GET.get('annee', '').strip()
    
    logger.error(f"SIMULATION - classe={classe_id}, statut={statut_id}, annee={annee_id}, etab={etab}")

    if not (classe_id and statut_id and annee_id):
        return render(request, 'parametres/partials/simulation_result.html', {
            'vide': True,
        })

    classe = Classe.objects.filter(pk=classe_id, etablissement=etab).first()
    statut = StatutEleve.objects.filter(pk=statut_id, etablissement=etab).first()
    annee = AnneeScolaire.objects.filter(pk=annee_id).first()
    
    logger.error(f"SIMULATION - trouve: classe={classe}, statut={statut}, annee={annee}")

    if not (classe and statut and annee):
        return render(request, 'parametres/partials/simulation_result.html', {
            'erreur': "Classe, statut ou année introuvable.",
        })

    tarifs = (
        TarifScolarite.objects
        .filter(etablissement=etab, classe=classe, statut_eleve=statut, annee_scolaire=annee, actif=True)
        .select_related('rubrique')
        .order_by('rubrique__ordre', 'rubrique__nom')
    )
    
    logger.error(f"SIMULATION - tarifs trouves: {tarifs.count()}")

    total = sum(t.montant for t in tarifs)

    return render(request, 'parametres/partials/simulation_result.html', {
        'classe': classe,
        'statut': statut,
        'annee': annee,
        'tarifs': tarifs,
        'total': total,
        'vide': False,
        'aucun_tarif': not tarifs.exists(),
    })


@login_required
@require_POST
def appreciation_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(AppreciationMoyenneSecondaire, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def appreciation_primaire_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(AppreciationMoyennePrimaire, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def categorie_discipline_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(CategorieDiscipline, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def discipline_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(Discipline, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def periode_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(PeriodeEvaluation, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_POST
def type_document_delete(request, pk):
    obj = get_object_or_404(TypeDocument, pk=pk)
    return _delete_view(request, obj)


@login_required
@require_POST
def type_sanction_delete(request, pk):
    obj = get_object_or_404(TypeSanction, pk=pk)
    return _delete_view(request, obj)


@login_required
@require_POST
def titre_fonction_delete(request, pk):
    obj = get_object_or_404(TitreFonction, pk=pk)
    return _delete_view(request, obj)


@login_required
@require_POST
def titre_honorifique_delete(request, pk):
    obj = get_object_or_404(TitreHonorifiquePersonnel, pk=pk)
    return _delete_view(request, obj)


@login_required
@require_POST
def type_evaluation_delete(request, pk):
    from pedagogie.models import TypeEvaluation
    obj = get_object_or_404(TypeEvaluation, pk=pk)
    return _delete_view(request, obj)


# ─── CALENDRIER SCOLAIRE ─────────────────────────────────────────────

@login_required
def calendrier(request):
    """Vue principale du calendrier scolaire — affichage mensuel."""
    from datetime import date, timedelta
    import calendar as cal

    etab = _get_etab(request)

    # Année scolaire : celle passée en GET ou la courante
    annee_id = request.GET.get('annee')
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else AnneeScolaire.objects.none()
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    else:
        annee = annees.filter(est_courante=True).first() or annees.first()

    # Mois affiché
    today = date.today()
    try:
        mois = int(request.GET.get('mois', today.month))
        annee_cal = int(request.GET.get('annee_cal', today.year))
    except (ValueError, TypeError):
        mois, annee_cal = today.month, today.year

    mois = max(1, min(12, mois))

    # Navigation mois précédent / suivant
    premier_du_mois = date(annee_cal, mois, 1)
    if mois == 1:
        mois_prec, annee_prec = 12, annee_cal - 1
    else:
        mois_prec, annee_prec = mois - 1, annee_cal
    if mois == 12:
        mois_suiv, annee_suiv = 1, annee_cal + 1
    else:
        mois_suiv, annee_suiv = mois + 1, annee_cal

    # Événements du mois
    dernier_du_mois = date(annee_cal, mois, cal.monthrange(annee_cal, mois)[1])
    evenements_mois = []
    if annee:
        evenements_mois = EvenementCalendrier.objects.filter(
            etablissement=etab,
            annee_scolaire=annee,
            date_debut__lte=dernier_du_mois,
            date_fin__gte=premier_du_mois,
        ).order_by('date_debut')

    # Grille calendrier : semaines (lundi → dimanche)
    premier_lundi = premier_du_mois - timedelta(days=premier_du_mois.weekday())
    semaines = []
    jour = premier_lundi
    while jour <= dernier_du_mois or len(semaines) < 6:
        semaine = []
        for _ in range(7):
            evts_jour = [e for e in evenements_mois if e.date_debut <= jour <= e.date_fin]
            semaine.append({'date': jour, 'hors_mois': jour.month != mois, 'evenements': evts_jour})
            jour += timedelta(days=1)
        semaines.append(semaine)
        if jour > dernier_du_mois and len(semaines) >= 4:
            break

    # Tous les événements de l'année pour la liste latérale
    tous_evenements = []
    if annee:
        tous_evenements = EvenementCalendrier.objects.filter(
            etablissement=etab, annee_scolaire=annee,
        ).order_by('date_debut')

    return render(request, 'parametres/calendrier.html', {
        'annee': annee,
        'annees': annees,
        'semaines': semaines,
        'mois_nom': [
            '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
        ][mois],
        'mois': mois,
        'annee_cal': annee_cal,
        'mois_prec': mois_prec,
        'annee_prec': annee_prec,
        'mois_suiv': mois_suiv,
        'annee_suiv': annee_suiv,
        'tous_evenements': tous_evenements,
        'types': EvenementCalendrier.TypeChoices.choices,
        'jours_semaine': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
        'today_iso': today.isoformat(),
    })


@login_required
def evenement_form(request, pk=None):
    """Création / modification d'un événement calendrier (modale HTMX)."""
    etab = _get_etab(request)
    evt = get_object_or_404(EvenementCalendrier, pk=pk, etablissement=etab) if pk else None

    annees = AnneeScolaire.objects.filter(etablissement=etab)
    ctx = {
        'evt': evt,
        'annees': annees,
        'types': EvenementCalendrier.TypeChoices.choices,
    }

    if request.method == 'POST':
        form = EvenementCalendrierForm(request.POST, instance=evt, etablissement=etab)
        if form.is_valid():
            instance = form.save(commit=False)
            if not evt:
                instance.etablissement = etab
            instance.save()
            return HttpResponse('', headers={'HX-Refresh': 'true'})
        return render(request, 'parametres/partials/evenement_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/evenement_form.html', ctx)


@login_required
@require_POST
def evenement_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(EvenementCalendrier, pk=pk, etablissement=etab)
    obj.delete()
    return HttpResponse('', headers={'HX-Refresh': 'true'})


# ─── MODÈLES DE MESSAGES ──────────────────────────────────────────────────────

@login_required
def modeles_messages_list(request):
    """Liste et édition des modèles de messages SMS personnalisables."""
    etab = _get_etab(request)
    types = ModeleMessage.TypeChoices.choices
    modeles = {m.type: m for m in ModeleMessage.objects.filter(etablissement=etab)}
    items = []
    for code, label in types:
        modele = modeles.get(code)
        items.append({
            'code': code,
            'label': label,
            'modele': modele,
            'defaut': ModeleMessage.DEFAUTS.get(code, ''),
            'variables': _variables_par_type(code),
        })
    return render(request, 'parametres/modeles_messages.html', {
        'items': items,
        'etab': etab,
    })


@login_required
def modele_message_form(request, type_msg):
    """Sauvegarde (création ou mise à jour) d'un modèle de message."""
    etab = _get_etab(request)
    if type_msg not in dict(ModeleMessage.TypeChoices.choices):
        return HttpResponse('Type invalide', status=400)

    modele, _ = ModeleMessage.objects.get_or_create(
        etablissement=etab,
        type=type_msg,
        defaults={'contenu_sms': ModeleMessage.DEFAUTS.get(type_msg, '')},
    )

    if request.method == 'POST':
        contenu = request.POST.get('contenu_sms', '').strip()
        actif = 'actif' in request.POST
        if contenu:
            modele.contenu_sms = contenu
            modele.actif = actif
            modele.save(update_fields=['contenu_sms', 'actif', 'updated_at'])
            messages.success(request, f"Modèle « {modele.get_type_display()} » enregistré.")
        return redirect('parametres:modeles_messages')

    return render(request, 'parametres/partials/modele_message_form.html', {
        'modele': modele,
        'type_msg': type_msg,
        'label': dict(ModeleMessage.TypeChoices.choices).get(type_msg, ''),
        'defaut': ModeleMessage.DEFAUTS.get(type_msg, ''),
        'variables': _variables_par_type(type_msg),
    })


@login_required
@require_POST
def modele_message_reset(request, type_msg):
    """Réinitialise un modèle au contenu par défaut."""
    etab = _get_etab(request)
    defaut = ModeleMessage.DEFAUTS.get(type_msg, '')
    ModeleMessage.objects.filter(etablissement=etab, type=type_msg).update(
        contenu_sms=defaut
    )
    messages.success(request, "Modèle réinitialisé au contenu par défaut.")
    return redirect('parametres:modeles_messages')


def _variables_par_type(type_msg):
    """Retourne la liste des variables disponibles pour un type de message."""
    return {
        'BULLETIN': ['{nom_eleve}', '{classe}', '{trimestre}', '{etablissement}'],
        'ABSENCE':  ['{nom_eleve}', '{date}', '{matiere}', '{etablissement}'],
        'RETARD':   ['{nom_eleve}', '{date}', '{matiere}', '{etablissement}'],
        'PAIEMENT': ['{nom_eleve}', '{montant}', '{rubrique}', '{etablissement}'],
        'REUNION':  ['{date}', '{heure}', '{lieu}', '{objet}', '{etablissement}'],
    }.get(type_msg, [])
