"""Nomenclatures simples : postes, localisations, statuts, appréciations, disciplines, types, distinctions, titres."""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q
from django.views.decorators.http import require_POST

from ..forms import (
    TypeDocumentForm, PosteForm, LocalisationPosteForm,
    StatutEleveForm, AppreciationMoyenneSecondaireForm,
    AppreciationMoyennePrimaireForm, CategorieDisciplineForm, DisciplineForm,
    TypeSanctionForm, DistinctionForm, TitreFonctionForm,
    TitreHonorifiquePersonnelForm, SalleForm,
)
from ..models import (
    Cycle, TypeDocument, Poste, LocalisationPoste, StatutEleve, AppreciationMoyenneSecondaire, AppreciationMoyennePrimaire, Discipline,
    CategorieDiscipline, TypeSanction, Distinction, TitreFonction, TitreHonorifiquePersonnel, Salle,
    SignataireDocument, AnneeScolaire,
)

from .commun import _get_etab, _delete_view
from personnel.selectors import cycles_accessibles
from yelen_school.cycle_filter import get_cycle_ids


def _types_documents_visibles(request, etab):
    """Types globaux ou rattachés aux cycles accessibles de l'établissement."""
    types = TypeDocument.objects.all()
    if etab is not None:
        types = types.filter(Q(cycle__isnull=True) | Q(cycle__etablissement=etab))
    if get_cycle_ids(request) is not None:
        types = types.filter(Q(cycle__isnull=True) | Q(cycle__in=cycles_accessibles(request, etab)))
    return types


def _types_documents_modifiables(request, etab):
    """Les types par cycle sont modifiables par les comptes ayant accès à ce cycle.

    Les types généraux (cycle nul) ont une portée transversale : seul un compte sans restriction
    de cycle peut les modifier ou les supprimer.
    """
    types = _types_documents_visibles(request, etab)
    if get_cycle_ids(request) is not None:
        types = types.filter(cycle__in=cycles_accessibles(request, etab))
    return types


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


# ─── TYPES DE DOCUMENTS ─────────────────────────────────────────────────

@login_required
def type_document_list(request):
    etab = _get_etab(request)
    types_documents = _types_documents_visibles(request, etab).select_related('cycle').order_by(
        'cycle__nom', 'categorie', 'libelle'
    )
    tpl = 'parametres/partials/type_document_list.html' if request.headers.get('HX-Request') else 'parametres/types_documents.html'
    return render(request, tpl, {'types_documents': types_documents})


@login_required
def type_document_form(request, pk=None):
    etab = _get_etab(request)
    types_modifiables = _types_documents_modifiables(request, etab)
    type_doc = get_object_or_404(types_modifiables, pk=pk) if pk else None
    cycles = cycles_accessibles(request, etab).order_by('ordre', 'nom')

    if request.method == 'POST':
        form = TypeDocumentForm(request.POST, instance=type_doc)
        form.fields['cycle'].queryset = cycles
        if get_cycle_ids(request) is not None:
            form.fields['cycle'].required = True
            form.fields['cycle'].empty_label = None
        if form.is_valid():
            type_doc = form.save()
            # À la création d'un type de document : pré-enregistrer un signataire
            # (membre à renseigner ensuite dans la grille matricielle) pour
            # chaque cycle applicable (le cycle du type, ou tous les cycles).
            if not pk:
                cycles_cibles = (
                    [type_doc.cycle] if type_doc.cycle_id
                    else list(cycles.filter(actif=True))
                )
                annee = AnneeScolaire.objects.get_annee_courante(etablissement=etab)
                if annee is not None:
                    for cycle in cycles_cibles:
                        SignataireDocument.objects.get_or_create(
                            cycle=cycle,
                            type_document=type_doc,
                            annee_scolaire=annee,
                            defaults={
                                'membre_personnel_id': None,
                                'fonction': 'Le Directeur',
                                'titre_honorifique': '',
                                'titres_honorifiques': [],
                                'actif': True,
                            },
                        )
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
    else:
        form = TypeDocumentForm(instance=type_doc)

    form.fields['cycle'].queryset = cycles
    if get_cycle_ids(request) is not None:
        form.fields['cycle'].required = True
        form.fields['cycle'].empty_label = None

    return render(request, 'parametres/partials/type_document_form.html', {
        'type_doc': type_doc,
        'form': form,
        'cycles': cycles,
    })


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


# ─── MENTIONS / DISTINCTIONS ──────────────────────────────────────

@login_required
def distinction_list(request):
    distinctions = Distinction.objects.all()
    tpl = 'parametres/partials/distinction_list.html' if request.headers.get('HX-Request') else 'parametres/mentions_distinctions.html'
    return render(request, tpl, {'distinctions': distinctions})


@login_required
def distinction_form(request, pk=None):
    distinction = get_object_or_404(Distinction, pk=pk) if pk else None

    if request.method == 'POST':
        form = DistinctionForm(request.POST, instance=distinction)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/distinction_form.html', {'distinction': distinction, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/distinction_form.html', {'distinction': distinction})


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


# ─── SALLES ───────────────────────────────────────────────────────

@login_required
def salle_list(request):
    salles = Salle.objects.filter(etablissement=_get_etab(request))
    tpl = 'parametres/partials/salle_list.html' if request.headers.get('HX-Request') else 'parametres/salles.html'
    return render(request, tpl, {'salles': salles})


@login_required
def salle_form(request, pk=None):
    etab = _get_etab(request)
    salle = get_object_or_404(Salle, pk=pk, etablissement=etab) if pk else None
    if request.method == 'POST':
        form = SalleForm(request.POST, instance=salle, etablissement=etab)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/salle_form.html', {'salle': salle, 'error': form.errors.as_text()})
    return render(request, 'parametres/partials/salle_form.html', {'salle': salle})


@login_required
@require_POST
def salle_delete(request, pk):
    obj = get_object_or_404(Salle, pk=pk, etablissement=_get_etab(request))
    return _delete_view(request, obj)


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
def type_document_delete(request, pk):
    obj = get_object_or_404(
        _types_documents_modifiables(request, _get_etab(request)), pk=pk,
    )
    return _delete_view(request, obj)


@login_required
@require_POST
def type_sanction_delete(request, pk):
    obj = get_object_or_404(TypeSanction, pk=pk)
    return _delete_view(request, obj)


@login_required
@require_POST
def distinction_delete(request, pk):
    obj = get_object_or_404(Distinction, pk=pk)
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
