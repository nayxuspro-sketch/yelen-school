"""Rubriques de paiement, tarifs de scolarité et simulation."""
import logging
from collections import defaultdict
from decimal import Decimal

from django.db import DatabaseError
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ..forms import (
    RubriquePaiementForm,
)
from ..models import (
    Cycle, AnneeScolaire, Classe, StatutEleve, RubriquePaiement, TarifScolarite,
)

logger = logging.getLogger(__name__)
from .commun import _get_etab, _delete_view


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
        except (DatabaseError, ValidationError, ValueError) as e:
            logger.exception("Enregistrement du tarif impossible")
            ctx['error'] = str(e)
            return render(request, 'parametres/partials/tarif_form.html', ctx)

    return render(request, 'parametres/partials/tarif_form.html', ctx)


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
    etab = _get_etab(request)
    classe_id = request.GET.get('classe', '').strip()
    statut_id = request.GET.get('statut', '').strip()
    annee_id = request.GET.get('annee', '').strip()

    if not (classe_id and statut_id and annee_id):
        return render(request, 'parametres/partials/simulation_result.html', {
            'vide': True,
        })

    classe = Classe.objects.filter(pk=classe_id, etablissement=etab).first()
    statut = StatutEleve.objects.filter(pk=statut_id, etablissement=etab).first()
    annee = AnneeScolaire.objects.filter(pk=annee_id, etablissement=etab).first()

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
