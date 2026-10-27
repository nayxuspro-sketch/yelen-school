"""Conflits d'emploi du temps : une classe, un enseignant ou une salle ne peuvent pas être occupés deux fois au
même moment. Utilisé à la saisie d'une séance, à l'application d'une génération automatique et pour signaler
les chevauchements déjà présents dans la grille d'une classe."""
from .models import JourSemaine, SeanceCours


def _chevauche(a_debut, a_fin, b_debut, b_fin):
    """Deux plages se chevauchent si l'une commence avant la fin de l'autre (séances enchaînées : aucun conflit)."""
    return a_debut < b_fin and a_fin > b_debut


def _motif(enseignement, salle, autre):
    """Raison pour laquelle ``autre`` (séance déjà en place) interdit la séance de ``enseignement`` ; None sinon."""
    e = autre.enseignement
    plage = f"{JourSemaine(autre.jour).label.lower()} {autre.heure_debut:%H:%M}–{autre.heure_fin:%H:%M}"
    if e.classe_id == enseignement.classe_id:
        return f"la classe {e.classe.nom} a déjà {e.matiere.nom} le {plage}"
    if enseignement.personnel_id and e.personnel_id == enseignement.personnel_id:
        return f"{e.personnel.get_nom_complet()} enseigne déjà {e.matiere.nom} en {e.classe.nom} le {plage}"
    if salle and autre.salle and autre.salle.strip().casefold() == salle.strip().casefold():
        return f"la salle {salle.strip()} est déjà occupée par {e.classe.nom} ({e.matiere.nom}) le {plage}"
    return None


def _seances_de_l_annee(enseignement):
    return (
        SeanceCours.objects
        .filter(enseignement__annee_scolaire_id=enseignement.annee_scolaire_id,
                enseignement__classe__etablissement_id=enseignement.classe.etablissement_id,
                enseignement__est_actif=True)
        .select_related('enseignement__matiere', 'enseignement__classe', 'enseignement__personnel')
    )


def conflits_seance(enseignement, jour, heure_debut, heure_fin, salle='', exclure_pk=None):
    """Motifs interdisant de placer la séance proposée (liste vide : aucun conflit)."""
    candidates = (
        _seances_de_l_annee(enseignement)
        .filter(jour=int(jour), heure_debut__lt=heure_fin, heure_fin__gt=heure_debut)
        .exclude(pk=exclure_pk)
        .order_by('heure_debut')
    )
    motifs = [_motif(enseignement, salle, autre) for autre in candidates]
    return [m for m in motifs if m]


def conflits_classe(classe, annee):
    """Chevauchements touchant les séances d'une classe : ``[(seance, motif), …]`` (chaque paire une seule fois)."""
    if annee is None:
        return []
    seances = list(
        SeanceCours.objects
        .filter(enseignement__annee_scolaire=annee, enseignement__classe__etablissement_id=classe.etablissement_id,
                enseignement__est_actif=True)
        .select_related('enseignement__matiere', 'enseignement__classe', 'enseignement__personnel')
        .order_by('jour', 'heure_debut')
    )
    resultats, vus = [], set()
    for seance in seances:
        if seance.enseignement.classe_id != classe.pk:
            continue
        for autre in seances:
            if autre.pk == seance.pk or autre.jour != seance.jour or frozenset((seance.pk, autre.pk)) in vus:
                continue
            if not _chevauche(seance.heure_debut, seance.heure_fin, autre.heure_debut, autre.heure_fin):
                continue
            motif = _motif(seance.enseignement, seance.salle, autre)
            if motif:
                vus.add(frozenset((seance.pk, autre.pk)))
                resultats.append((seance, motif))
    return resultats
