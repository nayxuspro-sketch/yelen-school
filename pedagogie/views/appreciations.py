"""Appréciations par matière : l'enseignant titulaire (ou la direction) rédige, pour chaque élève et chaque période,
l'appréciation imprimée sur le bulletin en regard de sa discipline (à défaut, la grille des moyennes s'applique)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import filtre_enseignant
from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.models import AnneeScolaire
from ..models import Enseignement, Resultat, Trimestre
from .evaluations import _refus_enseignant

LONGUEUR_MAX = 200

SUGGESTIONS = (
    "Excellent travail, félicitations.", "Très bon trimestre, continuez ainsi.", "Bon travail, résultats satisfaisants.",
    "Ensemble satisfaisant, peut encore progresser.", "Résultats moyens, des efforts à poursuivre.",
    "Travail irrégulier, plus de rigueur attendue.", "Résultats insuffisants, doit se ressaisir.",
    "Participe bien en classe, à confirmer à l'écrit.", "Manque de travail personnel.", "En net progrès.",
)


def _enseignements_visibles(request, annee):
    qs = (Enseignement.objects.filter(annee_scolaire=annee, est_actif=True, classe__etablissement=request.user.etablissement)
          .select_related('classe', 'matiere', 'personnel').order_by('classe__cycle__ordre', 'classe__nom', 'matiere__nom'))
    if request.user.role == 'ENSEIGNANT':
        qs = qs.filter(personnel=filtre_enseignant(request.user))
    return qs


@login_required
def appreciations_index(request):
    """Mes enseignements de l'année (tous pour la direction) : nombre d'appréciations saisies par période."""
    etab = request.user.etablissement
    annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    trimestres = list(Trimestre.objects.filter(annee_scolaire=annee).order_by('numero')) if annee else []
    enseignements = list(_enseignements_visibles(request, annee)) if annee else []
    saisies = {
        (ligne['enseignement_id'], ligne['trimestre_id']): ligne['nb']
        for ligne in Resultat.objects.filter(enseignement__in=enseignements).exclude(appreciation='').order_by()
        .values('enseignement_id', 'trimestre_id').annotate(nb=Count('pk'))
    }
    effectifs = {
        ligne['classe_id']: ligne['n']
        for ligne in Inscription.objects.filter(classe__in={e.classe_id for e in enseignements}, annee_scolaire=annee)
        .exclude(statut=StatutInscriptionChoices.ABANDON).order_by().values('classe_id').annotate(n=Count('pk'))
    } if annee else {}
    lignes = [{
        'enseignement': ens,
        'effectif': effectifs.get(ens.classe_id, 0),
        'periodes': [{'trimestre': t, 'nb': saisies.get((ens.pk, t.pk), 0)} for t in trimestres],
    } for ens in enseignements]
    return render(request, 'pedagogie/appreciations_index.html', {
        'annee': annee, 'trimestres': trimestres, 'lignes': lignes,
    })


@login_required
def appreciations_saisir(request, enseignement_id, trimestre_id):
    """Saisie des appréciations d'une discipline pour une période : un champ par élève, moyenne en regard."""
    enseignement = get_object_or_404(
        Enseignement.objects.select_related('classe', 'matiere', 'personnel', 'annee_scolaire'),
        pk=enseignement_id, classe__etablissement=request.user.etablissement,
    )
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id, annee_scolaire=enseignement.annee_scolaire)
    refus = _refus_enseignant(request, enseignement)
    if refus:
        messages.error(request, f"Saisie des appréciations refusée : {refus}")
        return redirect('pedagogie:appreciations_index')

    inscriptions = list(
        Inscription.objects.filter(classe=enseignement.classe, annee_scolaire=enseignement.annee_scolaire)
        .exclude(statut=StatutInscriptionChoices.ABANDON).select_related('eleve').order_by('eleve__nom', 'eleve__prenom')
    )
    resultats = {r.inscription_id: r for r in Resultat.objects.filter(enseignement=enseignement, trimestre=trimestre)}

    if request.method == 'POST':
        if trimestre.verrouille:
            messages.error(request, f"Saisie des appréciations refusée : {trimestre.message_verrouillage}")
            return redirect('pedagogie:appreciations_saisir', enseignement_id=enseignement.pk, trimestre_id=trimestre.pk)
        modifies = 0
        for ins in inscriptions:
            texte = ' '.join(request.POST.get(f'appr_{ins.pk}', '').split())[:LONGUEUR_MAX]
            resultat = resultats.get(ins.pk)
            if resultat is None:
                if not texte:
                    continue
                resultat = Resultat(inscription=ins, enseignement=enseignement, trimestre=trimestre,
                                    coefficient_utilise=enseignement.get_coefficient())
            if resultat.appreciation != texte:
                resultat.appreciation = texte
                resultat.save()
                modifies += 1
        messages.success(request, f"{modifies} appréciation{'s' if modifies > 1 else ''} enregistrée"
                                  f"{'s' if modifies > 1 else ''} — {enseignement.matiere.nom}, {enseignement.classe.nom}, "
                                  f"{trimestre.nom}." if modifies else "Aucune modification.")
        return redirect('pedagogie:appreciations_saisir', enseignement_id=enseignement.pk, trimestre_id=trimestre.pk)

    lignes = [{'inscription': ins, 'resultat': resultats.get(ins.pk)} for ins in inscriptions]
    autres_periodes = Trimestre.objects.filter(annee_scolaire=enseignement.annee_scolaire).order_by('numero')
    return render(request, 'pedagogie/appreciations_saisie.html', {
        'enseignement': enseignement, 'trimestre': trimestre, 'lignes': lignes, 'periodes': autres_periodes,
        'suggestions': SUGGESTIONS, 'longueur_max': LONGUEUR_MAX,
        'nb_saisies': sum(1 for r in resultats.values() if r.appreciation),
        'nb_sans_moyenne': sum(1 for ins in inscriptions if resultats.get(ins.pk) is None
                               or resultats[ins.pk].moyenne is None and not resultats[ins.pk].dispense),
    })

