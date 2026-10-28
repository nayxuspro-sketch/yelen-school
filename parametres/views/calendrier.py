"""Calendrier scolaire et événements."""
from datetime import date

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ..forms import (
    EvenementCalendrierForm,
)
from ..models import (
    AnneeScolaire, EvenementCalendrier,
)

from .commun import _get_etab


# ─── CALENDRIER SCOLAIRE ─────────────────────────────────────────────

@login_required
def calendrier(request):
    """Vue principale du calendrier scolaire — affichage mensuel."""
    from datetime import timedelta
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
