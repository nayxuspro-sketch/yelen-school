"""
Utilitaires d'analyse pédagogique — 100 % hors ligne, aucune dépendance externe.
Génère des commentaires et recommandations basés sur des règles statistiques.
"""
import datetime


def _niveau_moyenne(moy):
    """Retourne le niveau qualitatif d'une moyenne /20."""
    if moy is None:
        return None
    if moy < 8:
        return 'insuffisant'
    if moy < 10:
        return 'faible'
    if moy < 12:
        return 'passable'
    if moy < 14:
        return 'assez_bien'
    if moy < 16:
        return 'bien'
    return 'tres_bien'


def _niveau_taux(taux):
    """Retourne le niveau qualitatif d'un taux de réussite (%)."""
    if taux is None:
        return None
    if taux < 30:
        return 'tres_faible'
    if taux < 50:
        return 'faible'
    if taux < 65:
        return 'moyen'
    if taux < 80:
        return 'bon'
    return 'excellent'


def _commentaire(s):
    """Génère un commentaire pédagogique en une ou deux phrases."""
    moy   = s.get('moy_classe')
    taux  = s.get('taux')
    maxi  = s.get('moy_max')
    mini  = s.get('moy_min')
    niv_m = _niveau_moyenne(moy)
    niv_t = _niveau_taux(taux)

    # Calcul de l'écart (disparité)
    ecart = None
    if maxi is not None and mini is not None:
        ecart = maxi - mini

    phrases = []

    # Phrase 1 — appréciation globale
    if niv_m == 'tres_bien':
        phrases.append(
            f"La classe affiche d'excellents résultats avec une moyenne de {moy:.2f}/20."
        )
    elif niv_m == 'bien':
        phrases.append(
            f"Les résultats sont bons avec une moyenne de {moy:.2f}/20."
        )
    elif niv_m == 'assez_bien':
        phrases.append(
            f"Les résultats sont satisfaisants avec une moyenne de {moy:.2f}/20."
        )
    elif niv_m == 'passable':
        phrases.append(
            f"Les résultats sont passables avec une moyenne de {moy:.2f}/20 ; "
            "des efforts supplémentaires sont nécessaires."
        )
    elif niv_m == 'faible':
        phrases.append(
            f"Les résultats sont insuffisants avec une moyenne de {moy:.2f}/20 ; "
            "la situation nécessite une attention immédiate."
        )
    elif niv_m == 'insuffisant':
        phrases.append(
            f"La classe est en grande difficulté avec une moyenne de {moy:.2f}/20 ; "
            "une intervention pédagogique urgente s'impose."
        )
    else:
        phrases.append("Les données ne permettent pas d'évaluer la moyenne de la classe.")

    # Phrase 2 — taux de réussite
    if taux is not None:
        if niv_t == 'excellent':
            phrases.append(
                f"Le taux de réussite de {taux:.1f}% témoigne d'un très bon niveau général."
            )
        elif niv_t == 'bon':
            phrases.append(
                f"Le taux de réussite de {taux:.1f}% est encourageant."
            )
        elif niv_t == 'moyen':
            phrases.append(
                f"Le taux de réussite de {taux:.1f}% reste perfectible."
            )
        elif niv_t == 'faible':
            phrases.append(
                f"Avec seulement {taux:.1f}% de réussite, la majorité des élèves "
                "est en difficulté."
            )
        else:
            phrases.append(
                f"Le taux de réussite de {taux:.1f}% est très préoccupant."
            )

    # Phrase 3 — disparité
    if ecart is not None:
        if ecart >= 12:
            phrases.append(
                f"L'écart de {ecart:.1f} points entre le meilleur et le plus faible élève "
                "révèle une très grande hétérogénéité au sein de la classe."
            )
        elif ecart >= 8:
            phrases.append(
                f"Un écart de {ecart:.1f} points indique une classe assez hétérogène."
            )

    return " ".join(phrases)


def _recommandations(s):
    """Génère une liste de 2 à 4 recommandations pratiques."""
    moy   = s.get('moy_classe')
    taux  = s.get('taux')
    maxi  = s.get('moy_max')
    mini  = s.get('moy_min')
    niv_m = _niveau_moyenne(moy)
    niv_t = _niveau_taux(taux)
    ecart = (maxi - mini) if (maxi is not None and mini is not None) else None

    recs = []

    # Recommandations selon le niveau de la moyenne
    if niv_m in ('insuffisant', 'faible'):
        recs.append(
            "Organiser des séances de remédiation ciblées sur les lacunes "
            "identifiées dans les matières les plus faibles."
        )
        recs.append(
            "Renforcer le suivi individuel des élèves en difficulté et "
            "associer les parents à la démarche de soutien."
        )
    elif niv_m == 'passable':
        recs.append(
            "Mettre en place des exercices de consolidation pour "
            "ancrer les notions mal assimilées."
        )
        recs.append(
            "Encourager l'entraide entre élèves (tutorat par les pairs) "
            "pour améliorer la compréhension collective."
        )
    elif niv_m in ('bien', 'tres_bien'):
        recs.append(
            "Maintenir la dynamique positive en proposant des activités "
            "d'approfondissement et d'enrichissement."
        )
        recs.append(
            "Valoriser les réussites des élèves lors des conseils de classe "
            "pour entretenir leur motivation."
        )

    # Recommandations selon le taux
    if niv_t in ('tres_faible', 'faible') and len(recs) < 3:
        recs.append(
            "Revoir la progression pédagogique et adapter le rythme "
            "d'enseignement au niveau réel de la classe."
        )

    # Recommandations selon l'hétérogénéité
    if ecart is not None and ecart >= 8:
        recs.append(
            "Pratiquer la pédagogie différenciée : proposer des activités "
            "adaptées aux différents profils d'élèves (soutien / approfondissement)."
        )

    # Recommandation générale toujours pertinente si liste courte
    if len(recs) < 2:
        recs.append(
            "Assurer un suivi régulier des progrès de chaque élève et "
            "communiquer les résultats aux familles en fin de période."
        )

    return recs[:4]  # Maximum 4 recommandations


def generer_analyse_bilan(periodes_stats):
    """
    Génère des commentaires pédagogiques pour le bilan trimestriel.

    periodes_stats : liste de dicts :
        {
            'cle': str,
            'classe_nom': str,
            'cycle_nom': str,
            'periode_nom': str,
            'nb_eleves': int,
            'moy_classe': float|None,
            'moy_max': float|None,
            'moy_min': float|None,
            'taux': float|None,
            'nb_admis': int,
        }

    Retourne : dict { cle: {'commentaire': str, 'recommandations': [str, ...]} }
    """
    resultat = {}
    for s in periodes_stats:
        resultat[s['cle']] = {
            'commentaire':      _commentaire(s),
            'recommandations':  _recommandations(s),
        }
    return resultat


# ═══════════════════════════════════════════════════════════════════
# ANALYSE INDIVIDUELLE D'UN ÉLÈVE (BULLETIN)
# ═══════════════════════════════════════════════════════════════════

def generer_commentaire_eleve(mg, nb_eleves, moy_avg_classe, resultats_annotes, sanctions_conduite=None):
    """
    Génère un commentaire pédagogique personnalisé pour le bulletin d'un élève.

    Paramètres :
        mg                : MoyenneGenerale (moyenne, rang, nb_matieres_validees, nb_matieres_total)
        nb_eleves         : int — effectif total de la classe
        moy_avg_classe    : Decimal|float|None — moyenne de la classe
        resultats_annotes : list of (Resultat, appr) — résultats par matière
        sanctions_conduite: list of SanctionDisciplinaire (ou None)

    Retourne : str — commentaire en une à trois phrases.
    """
    if mg is None or mg.moyenne is None:
        return ""

    moyenne = float(mg.moyenne)
    rang    = mg.rang
    sanctions = sanctions_conduite or []

    # ── Matières en difficulté et points forts ──────────────────────
    matieres_faibles = []
    matieres_fortes  = []
    for r in resultats_annotes:
        if r.dispense or r.moyenne is None:
            continue
        m = float(r.moyenne)
        nom = r.enseignement.matiere.nom
        if m < 10:
            matieres_faibles.append((nom, m))
        elif m >= 14:
            matieres_fortes.append((nom, m))

    # Trier : faibles du plus bas au plus haut, forts du plus haut au plus bas
    matieres_faibles.sort(key=lambda x: x[1])
    matieres_fortes.sort(key=lambda x: x[1], reverse=True)

    phrases = []

    # ── Phrase 1 : niveau global ─────────────────────────────────────
    if moyenne >= 16:
        p1 = f"Excellent travail ce trimestre avec une moyenne remarquable de {moyenne:.2f}/20."
    elif moyenne >= 14:
        p1 = f"Très bon travail ce trimestre avec une moyenne de {moyenne:.2f}/20."
    elif moyenne >= 12:
        p1 = f"Bon travail ce trimestre, avec une moyenne satisfaisante de {moyenne:.2f}/20."
    elif moyenne >= 10:
        p1 = f"Résultats passables ce trimestre avec une moyenne de {moyenne:.2f}/20 ; des progrès sont possibles."
    elif moyenne >= 8:
        p1 = f"Trimestre difficile avec une moyenne insuffisante de {moyenne:.2f}/20 ; un effort soutenu est nécessaire."
    else:
        p1 = f"Résultats très insuffisants ce trimestre avec une moyenne de {moyenne:.2f}/20 ; une remise en question sérieuse s'impose."
    phrases.append(p1)

    # ── Phrase 2 : position dans la classe ──────────────────────────
    if rang and nb_eleves and nb_eleves > 1:
        pct_rang = rang / nb_eleves
        if pct_rang <= 0.15:
            phrases.append(f"L'élève se distingue parmi les meilleurs de la classe (rang {rang}/{nb_eleves}).")
        elif pct_rang <= 0.40:
            phrases.append(f"L'élève se situe dans le bon tiers de la classe (rang {rang}/{nb_eleves}).")
        elif pct_rang <= 0.65:
            if moy_avg_classe and moyenne < float(moy_avg_classe):
                phrases.append(f"L'élève est en dessous de la moyenne de classe de {float(moy_avg_classe):.2f}/20 (rang {rang}/{nb_eleves}).")
            else:
                phrases.append(f"L'élève se situe dans la moyenne de la classe (rang {rang}/{nb_eleves}).")
        else:
            phrases.append(f"L'élève est dans la partie basse du classement (rang {rang}/{nb_eleves}) et doit redoubler d'efforts.")

    # ── Phrase 3 : points forts et matières à améliorer ─────────────
    if matieres_fortes and matieres_faibles:
        noms_forts  = ", ".join(n for n, _ in matieres_fortes[:2])
        noms_faibles = ", ".join(n for n, _ in matieres_faibles[:2])
        phrases.append(
            f"L'élève s'illustre particulièrement en {noms_forts} "
            f"mais doit impérativement combler ses lacunes en {noms_faibles}."
        )
    elif matieres_faibles:
        noms_faibles = ", ".join(n for n, _ in matieres_faibles[:2])
        nb_faibles = len(matieres_faibles)
        if nb_faibles == 1:
            phrases.append(f"Un effort particulier est attendu en {noms_faibles}.")
        else:
            phrases.append(
                f"Des lacunes importantes sont constatées en {noms_faibles}"
                f"{'...' if nb_faibles > 2 else ''} ; un travail régulier de rattrapage s'impose."
            )
    elif matieres_fortes:
        noms_forts = ", ".join(n for n, _ in matieres_fortes[:2])
        phrases.append(f"L'élève excelle en {noms_forts} ; il convient de maintenir cet élan sur toutes les matières.")

    # ── Phrase 4 : conduite (si sanctions confirmées) ───────────────
    if sanctions:
        pts_total = sum(float(s.points) for s in sanctions if s.points)
        if pts_total < 0:
            phrases.append(
                f"La conduite de l'élève a été sanctionnée ce trimestre "
                f"({abs(pts_total):.0f} point{'s' if abs(pts_total) > 1 else ''} retirés) ; "
                "un comportement plus respectueux des règles de vie scolaire est impérativement attendu."
            )
        else:
            phrases.append("Des manquements à la discipline ont été signalés ce trimestre.")

    return " ".join(phrases)


# ═══════════════════════════════════════════════════════════════════
# SCORING DE RISQUE DE DÉCROCHAGE SCOLAIRE
# Algorithme 100 % hors ligne — basé sur 5 signaux pondérés
#
# Signal                          Poids max
# ─────────────────────────────────────────
# 1. Taux d'absence non justifiée    35 pts
# 2. Tendance des moyennes           30 pts
# 3. Matières sous 8/20             20 pts
# 4. Sanctions disciplinaires        10 pts
# 5. Échéances impayées > 30 j        5 pts
# ─────────────────────────────────────────
# Total                             100 pts
# ═══════════════════════════════════════════════════════════════════

def calculer_score_risque(inscription, annee):
    """
    Calcule le score de risque de décrochage (0–100) pour une inscription.

    Paramètres :
        inscription : inscriptions.models.Inscription
        annee       : parametres.models.AnneeScolaire

    Retourne : (score: int, facteurs: list[dict])
        facteurs = [{'libelle': str, 'points': int, 'detail': str}, ...]
    """
    from presences.models import Presence
    from pedagogie.models import MoyenneGenerale, Resultat
    from viescolaire.models import SanctionDisciplinaire
    from finances.models import Echeancier

    score = 0
    facteurs = []
    aujourd_hui = datetime.date.today()

    # ── 1. TAUX D'ABSENCE NON JUSTIFIÉE (max 35 pts) ────────────────
    presences = Presence.objects.filter(inscription=inscription)
    total_appels = presences.count()
    if total_appels > 0:
        nb_absences = presences.filter(
            statut=Presence.StatutChoices.ABSENT
        ).count()
        nb_justifiees = presences.filter(
            statut=Presence.StatutChoices.EXCUSE
        ).count()
        nb_injustifiees = max(nb_absences - nb_justifiees, 0)
        taux = nb_injustifiees / total_appels

        if taux >= 0.30:
            pts = 35
            detail = f"{nb_injustifiees} absences injustifiées sur {total_appels} séances ({taux*100:.0f}%)"
        elif taux >= 0.20:
            pts = 25
            detail = f"{nb_injustifiees} absences injustifiées ({taux*100:.0f}%)"
        elif taux >= 0.10:
            pts = 15
            detail = f"{nb_injustifiees} absences injustifiées ({taux*100:.0f}%)"
        elif taux >= 0.05:
            pts = 7
            detail = f"{nb_injustifiees} absences injustifiées ({taux*100:.0f}%)"
        else:
            pts = 0
            detail = ""

        if pts > 0:
            score += pts
            facteurs.append({'libelle': "Absences injustifiées", 'points': pts, 'detail': detail})

    # ── 2. TENDANCE DES MOYENNES (max 30 pts) ───────────────────────
    moyennes = list(
        MoyenneGenerale.objects
        .filter(inscription=inscription, trimestre__annee_scolaire=annee)
        .order_by('trimestre__numero')
        .values_list('moyenne', flat=True)
    )
    moyennes = [float(m) for m in moyennes if m is not None]

    if len(moyennes) >= 2:
        derniere = moyennes[-1]
        premiere = moyennes[0]
        chute = premiere - derniere

        if derniere < 8:
            pts, detail = 30, f"Moyenne critique : {derniere:.2f}/20"
        elif derniere < 10 and chute > 2:
            pts, detail = 22, f"Moyenne insuffisante en chute ({premiere:.1f} -> {derniere:.1f}/20)"
        elif derniere < 10:
            pts, detail = 15, f"Moyenne insuffisante : {derniere:.2f}/20"
        elif chute > 3:
            pts, detail = 12, f"Chute marquée ({premiere:.1f} -> {derniere:.1f}/20)"
        elif chute > 1.5:
            pts, detail = 6, f"Baisse de la moyenne ({premiere:.1f} -> {derniere:.1f}/20)"
        else:
            pts, detail = 0, ""

        if pts > 0:
            score += pts
            facteurs.append({'libelle': "Tendance des moyennes", 'points': pts, 'detail': detail})

    elif len(moyennes) == 1 and moyennes[0] < 8:
        pts = 20
        score += pts
        facteurs.append({
            'libelle': "Moyenne critique (T1)",
            'points': pts,
            'detail': f"Moyenne du 1er trimestre : {moyennes[0]:.2f}/20",
        })

    # ── 3. MATIÈRES SOUS 8/20 (max 20 pts) ─────────────────────────
    dernier_trimestre_id = (
        MoyenneGenerale.objects
        .filter(inscription=inscription, trimestre__annee_scolaire=annee)
        .order_by('-trimestre__numero')
        .values_list('trimestre_id', flat=True)
        .first()
    )
    if dernier_trimestre_id:
        nb_critiques = Resultat.objects.filter(
            inscription=inscription,
            trimestre_id=dernier_trimestre_id,
            dispense=False,
            moyenne_sur_20__lt=8,
        ).count()

        if nb_critiques >= 4:
            pts = 20
        elif nb_critiques == 3:
            pts = 14
        elif nb_critiques == 2:
            pts = 8
        elif nb_critiques == 1:
            pts = 4
        else:
            pts = 0

        if pts > 0:
            score += pts
            facteurs.append({
                'libelle': "Matières en grande difficulté",
                'points': pts,
                'detail': f"{nb_critiques} matière(s) avec moyenne < 8/20",
            })

    # ── 4. SANCTIONS DISCIPLINAIRES CONFIRMÉES (max 10 pts) ─────────
    nb_sanctions = SanctionDisciplinaire.objects.filter(
        inscription=inscription,
        statut=SanctionDisciplinaire.StatutChoices.CONFIRME,
        trimestre__annee_scolaire=annee,
    ).count()

    if nb_sanctions >= 4:
        pts = 10
    elif nb_sanctions == 3:
        pts = 7
    elif nb_sanctions == 2:
        pts = 4
    elif nb_sanctions == 1:
        pts = 2
    else:
        pts = 0

    if pts > 0:
        score += pts
        facteurs.append({
            'libelle': "Sanctions disciplinaires",
            'points': pts,
            'detail': f"{nb_sanctions} sanction(s) confirmée(s) cette année",
        })

    # ── 5. ÉCHÉANCES IMPAYÉES > 30 JOURS (max 5 pts) ───────────────
    seuil_retard = aujourd_hui - datetime.timedelta(days=30)
    nb_retards = Echeancier.objects.filter(
        inscription=inscription,
        paye=False,
        date_limite__lt=seuil_retard,
    ).count()

    if nb_retards >= 2:
        pts = 5
    elif nb_retards == 1:
        pts = 3
    else:
        pts = 0

    if pts > 0:
        score += pts
        facteurs.append({
            'libelle': "Retards de paiement",
            'points': pts,
            'detail': f"{nb_retards} échéance(s) impayée(s) depuis plus de 30 jours",
        })

    return min(score, 100), facteurs
