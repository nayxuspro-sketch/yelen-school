"""Index, années scolaires, cycles, classes, périodes d'évaluation et types d'évaluation."""

import json

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods, require_POST

from ..droits import autorise_url

from ..forms import (
    AnneeScolaireForm, CycleForm, ClasseForm, PeriodeEvaluationForm, TypeEvaluationForm,
)
from ..models import (
    Cycle, AnneeScolaire, Classe, Poste, LocalisationPoste, StatutEleve, RubriquePaiement, TarifScolarite,
    AppreciationMoyenneSecondaire, PeriodeEvaluation, Discipline,
    TitreFonction, TitreHonorifiquePersonnel, Salle,
)

from .commun import _get_etab, _delete_view


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
        'nb_salles':              count(Salle),
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
    if annee.cloturee:
        return _toast('error', f"{annee.libelle} est clôturée : rouvrez-la avant de la définir comme courante.")
    annee.est_courante = True
    annee.save()
    return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})


def _toast(type_, message, rafraichir=False):
    """Réponse HTMX sans contenu : affiche un toast et, si demandé, recharge les listes de paramètres."""
    declencheurs = {'showToast': {'type': type_, 'message': message}}
    if rafraichir:
        declencheurs['parametreUpdated'] = True
    return HttpResponse(status=204, headers={'HX-Trigger': json.dumps(declencheurs)})


@login_required
@require_POST
def annee_cloture(request, pk):
    """Clôture ou rouvre une année scolaire. Clôturer verrouille ses inscriptions (création, modification,
    transfert, abandon, réinscription) et clôture toutes ses périodes d'évaluation (notes) ; les encaissements
    d'arriérés restent possibles. Rouvrir ne rouvre pas les périodes (Paramètres → Périodes)."""
    from pedagogie.models import Trimestre
    etab = _get_etab(request)
    annee = get_object_or_404(AnneeScolaire, pk=pk, etablissement=etab)
    if annee.cloturee:
        annee.cloturee = False
        annee.save(update_fields=['cloturee', 'updated_at'])
        return _toast('success', f"{annee.libelle} rouverte : les inscriptions sont de nouveau modifiables "
                                 "(les périodes restent clôturées).", rafraichir=True)
    if annee.est_courante:
        return _toast('error', "Impossible de clôturer l'année courante : définissez d'abord la nouvelle année "
                               "comme courante.")
    for periode in PeriodeEvaluation.objects.filter(annee_scolaire=annee).filter(Q(cloturee=False) | Q(derogation_ouverte=True)):
        Trimestre.objects.pour_periode(periode).cloturer(
            ouvert=False, utilisateur=request.user, motif=f"Clôture de l'année {annee.libelle}",
        )
        periode.cloturee = True
        periode.derogation_ouverte = False
        periode.save(update_fields=['cloturee', 'derogation_ouverte', 'updated_at'])
    annee.cloturee = True
    annee.save(update_fields=['cloturee', 'updated_at'])
    return _toast('success', f"{annee.libelle} clôturée : inscriptions et notes verrouillées.", rafraichir=True)


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


# ─── PÉRIODES ÉVALUATION ─────────────────────────────────────────────

@login_required
def periode_list(request):
    from pedagogie.models import Trimestre
    etab = _get_etab(request)
    periodes = list(PeriodeEvaluation.objects.filter(etablissement=etab).select_related('annee_scolaire')) if etab else []
    journaux = {
        (t.annee_scolaire_id, t.numero): t.journal_cloture
        for t in Trimestre.objects.filter(annee_scolaire__etablissement=etab).only('annee_scolaire_id', 'numero', 'journal_cloture')
    } if etab else {}
    for p in periodes:
        lignes = [ligne for ligne in journaux.get((p.annee_scolaire_id, p.numero), '').splitlines() if ligne.strip()]
        p.dernier_acte = lignes[-1] if lignes else ''
    tpl = 'parametres/partials/periode_list.html' if request.headers.get('HX-Request') else 'parametres/periodes.html'
    return render(request, tpl, {'periodes': periodes})


@login_required
def periode_form(request, pk=None):
    from pedagogie.models import Trimestre
    etab = _get_etab(request)
    periode = get_object_or_404(PeriodeEvaluation, pk=pk, etablissement=etab) if pk else None
    etait_verrouillee = periode.verrouillee if periode else False
    ancienne_date_fin = periode.date_fin if periode else None
    annees = AnneeScolaire.objects.filter(etablissement=etab) if etab else AnneeScolaire.objects.none()
    ctx = {'periode': periode, 'annees': annees, 'type_choices': PeriodeEvaluation.TYPE_CHOICES}

    if request.method == 'POST':
        if not etab:
            return render(request, 'parametres/partials/periode_form.html', {**ctx, 'error': "Votre compte n'est pas associé à un établissement."})
        form = PeriodeEvaluationForm(request.POST, instance=periode, etablissement=etab)
        if form.is_valid():
            if etait_verrouillee and form.cleaned_data['date_fin'] != ancienne_date_fin and not autorise_url(request, 'parametres:periode_cloture'):
                return render(request, 'parametres/partials/periode_form.html', {
                    **ctx, 'error': "Seule la direction peut modifier l'échéance d'une période clôturée.",
                })
            instance = form.save(commit=False)
            if not periode:
                instance.etablissement = etab
            if not instance.echue and instance.derogation_ouverte:
                instance.derogation_ouverte = False
            instance.save()
            trimestre = Trimestre.objects.filter(annee_scolaire=instance.annee_scolaire, numero=instance.numero).first()
            if trimestre is not None:
                trimestre.nom = instance.nom
                trimestre.type_periode = 'TRIMESTRE' if instance.type_periode == 'TRIMESTRE' else 'SEMESTRE'
                trimestre.date_debut = instance.date_debut
                trimestre.date_fin = instance.date_fin
                if not trimestre.echue and trimestre.derogation_ouverte:
                    trimestre.derogation_ouverte = False
                trimestre.save(update_fields=['nom', 'type_periode', 'date_debut', 'date_fin', 'derogation_ouverte', 'updated_at'])
            return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
        return render(request, 'parametres/partials/periode_form.html', {**ctx, 'error': form.errors.as_text()})

    return render(request, 'parametres/partials/periode_form.html', ctx)


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
def periode_delete(request, pk):
    etab = _get_etab(request)
    obj = get_object_or_404(PeriodeEvaluation, pk=pk, etablissement=etab)
    return _delete_view(request, obj)


@login_required
@require_http_methods(['GET', 'POST'])
def periode_cloture(request, pk):
    """Clôture une période ouverte (POST) ou accorde une dérogation motivée sur une période verrouillée (GET modale + POST).
    Chaque ouverture et refermeture consigne l'auteur et le motif, en plus du journal d'audit."""
    from pedagogie.models import Trimestre
    etab = _get_etab(request)
    periode = get_object_or_404(PeriodeEvaluation.objects.select_related('annee_scolaire'), pk=pk, etablissement=etab)
    trimestre = Trimestre.objects.pour_periode(periode)
    ouvrir = trimestre.verrouille or periode.verrouillee
    lignes_journal = list(reversed([ligne for ligne in trimestre.journal_cloture.splitlines() if ligne.strip()]))

    if request.method == 'GET':
        return render(request, 'parametres/partials/periode_reouverture_modal.html', {
            'periode': periode, 'trimestre': trimestre, 'lignes_journal': lignes_journal,
        })

    motif = ' '.join(request.POST.get('motif', '').split())
    if ouvrir and not motif:
        if request.headers.get('HX-Target') == 'modal-container':
            return render(request, 'parametres/partials/periode_reouverture_modal.html', {
                'periode': periode, 'trimestre': trimestre, 'lignes_journal': lignes_journal,
                'error': "Le motif de réouverture est obligatoire.",
            })
        return HttpResponse("Le motif de réouverture est obligatoire.", status=400)

    trimestre.cloturer(ouvert=ouvrir, utilisateur=request.user, motif=motif)
    periode.cloturee = trimestre.notes_saisies
    periode.derogation_ouverte = trimestre.derogation_ouverte
    periode.save(update_fields=['cloturee', 'derogation_ouverte', 'updated_at'])
    etat = 'rouvert par dérogation' if (ouvrir and trimestre.echue) else ('rouvert' if ouvrir else 'clôturé')
    messages.success(request, f"{periode.nom} {etat} : les notes sont "
                              f"{'de nouveau modifiables' if ouvrir else 'verrouillées'}.")
    return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})


@login_required
@require_POST
def type_evaluation_delete(request, pk):
    from pedagogie.models import TypeEvaluation
    obj = get_object_or_404(TypeEvaluation, pk=pk)
    return _delete_view(request, obj)
