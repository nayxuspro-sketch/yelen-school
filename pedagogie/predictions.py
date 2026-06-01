"""
pedagogie/predictions.py — Service de prédiction de réussite aux examens officiels

Algorithme sans ML : formule pondérée basée sur :
  - Moyenne générale du dernier trimestre (base 70 %)
  - Tendance inter-trimestrielle (±10 pts)
  - Absences non justifiées (malus jusqu'à -15 pts)
"""
from decimal import Decimal


def _examen_pour_cycle(cycle_nom):
    """Détermine l'examen officiel ciblé selon le nom du cycle."""
    from .models import PredictionReussiteExamen as P
    n = (cycle_nom or '').lower()
    if 'secondaire' in n:
        return P.ExamenChoices.BAC
    if 'post' in n or 'college' in n or 'collège' in n:
        return P.ExamenChoices.BEPC
    if 'primaire' in n:
        return P.ExamenChoices.CEP
    return P.ExamenChoices.AUTRE


def calculer_prediction(inscription):
    """
    Calcule ou met à jour la PredictionReussiteExamen pour une inscription.

    Retourne l'instance (créée ou mise à jour).
    """
    from .models import MoyenneGenerale, PredictionReussiteExamen as P
    from presences.models import Presence

    moyennes = list(
        MoyenneGenerale.objects.filter(inscription=inscription)
        .select_related('trimestre')
        .order_by('trimestre__numero')
    )

    if not moyennes:
        return None

    derniere_mg = moyennes[-1]
    mg_val = float(derniere_mg.moyenne or 0)

    # ── Score de base (0-100) ─────────────────────────────────────────
    score_base = (mg_val / 20) * 100
    facteurs = [
        {
            'libelle': f"Moyenne générale ({derniere_mg.trimestre.nom})",
            'detail': f"{mg_val:.2f}/20",
            'points': round(score_base, 1),
        }
    ]

    # ── Tendance ──────────────────────────────────────────────────────
    bonus_tendance = 0
    tendance = None
    if len(moyennes) >= 2:
        avant_derniere = moyennes[-2]
        if avant_derniere.moyenne and derniere_mg.moyenne:
            tendance = float(derniere_mg.moyenne) - float(avant_derniere.moyenne)
            if tendance >= 2:
                bonus_tendance = 10
            elif tendance >= 0.5:
                bonus_tendance = 5
            elif tendance >= -0.5:
                bonus_tendance = 0
            elif tendance >= -2:
                bonus_tendance = -5
            else:
                bonus_tendance = -10
            facteurs.append({
                'libelle': "Tendance inter-trimestrielle",
                'detail': f"{tendance:+.2f} pts ({derniere_mg.trimestre.nom} vs {avant_derniere.trimestre.nom})",
                'points': bonus_tendance,
            })

    # ── Assiduité ─────────────────────────────────────────────────────
    malus_presence = 0
    abs_nj = 0
    try:
        abs_nj = Presence.objects.filter(
            inscription=inscription,
            statut='ABSENT',
            justifie=False,
        ).count()
        if abs_nj > 30:
            malus_presence = -15
        elif abs_nj > 20:
            malus_presence = -10
        elif abs_nj > 10:
            malus_presence = -5
    except Exception:
        pass

    if abs_nj > 0:
        facteurs.append({
            'libelle': "Assiduité",
            'detail': f"{abs_nj} absence(s) non justifiée(s)",
            'points': malus_presence,
        })

    # ── Score final ───────────────────────────────────────────────────
    score = max(0, min(100, round(score_base + bonus_tendance + malus_presence)))
    pronostic = P.pronostic_pour_score(score)

    # ── Examen cible ──────────────────────────────────────────────────
    cycle_nom = getattr(inscription.classe.cycle, 'nom', '') if hasattr(inscription.classe, 'cycle') else ''
    examen = _examen_pour_cycle(cycle_nom)

    # ── Persist ───────────────────────────────────────────────────────
    obj, _ = P.objects.update_or_create(
        inscription=inscription,
        defaults={
            'examen_cible': examen,
            'score': score,
            'pronostic': pronostic,
            'mg_actuelle': Decimal(str(round(mg_val, 2))),
            'tendance': Decimal(str(round(tendance, 2))) if tendance is not None else None,
            'nb_absences_nj': abs_nj,
            'facteurs': facteurs,
        },
    )
    return obj


def calculer_predictions_classe(classe, annee_scolaire):
    """Calcule les prédictions pour toutes les inscriptions d'une classe."""
    from inscriptions.models import Inscription
    inscriptions = Inscription.objects.filter(
        classe=classe,
        annee_scolaire=annee_scolaire,
    ).exclude(statut='ABANDON').select_related('eleve', 'classe__cycle')

    resultats = []
    for ins in inscriptions:
        pred = calculer_prediction(ins)
        if pred:
            resultats.append(pred)
    return resultats
