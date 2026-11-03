"""
Assistant IA YELEN SCHOOL — Moteur de requêtes par mots-clés
Analyse le langage naturel et interroge la base de données Django en temps réel.
Répond aussi aux questions fonctionnelles grâce à la base de connaissances du guide.
Aucune API externe requise — fonctionne hors ligne et sans abonnement.
"""

import logging
import re

from .guide import _GUIDE_KB
from .requetes import (
    _get_annee as _get_annee,
    _inscrits as _inscrits,
    _extract_classe,
    _extract_trimestre,
    _extract_seuil,
    _extract_nom,
    _SANS_ANNEE as _SANS_ANNEE,
    _req_effectifs,
    _req_finances,
    _req_absences,
    _dernier_trimestre as _dernier_trimestre,
    _req_difficultes,
    _req_moyennes,
    _req_progression,
    _req_eleve,
    _fcfa as _fcfa,
    _fmt_effectifs,
    _fmt_finances,
    _fmt_absences,
    _fmt_difficultes,
    _fmt_moyennes,
    _fmt_progression,
    _fmt_eleve,
)

logger = logging.getLogger(__name__)


def _search_guide(query: str):
    """Recherche dans la base de connaissances du guide le topic le plus pertinent.
    Score = somme des longueurs des mots-clés correspondants (les plus spécifiques l'emportent)."""
    m = query.lower()
    best_topic = None
    best_score = 0
    for topic in _GUIDE_KB:
        # Score = longueur totale des keywords matchés (favorise les correspondances précises)
        score = sum(len(kw) for kw in topic["mots"] if kw in m)
        if score > best_score:
            best_score = score
            best_topic = topic
    if best_score == 0:
        # Fallback : mots significatifs de la requête vs fragments de keywords
        query_words = [w for w in re.split(r'\W+', m) if len(w) >= 4]
        for topic in _GUIDE_KB:
            score = sum(
                len(kw) for qw in query_words for kw in topic["mots"]
                if qw in kw or kw.startswith(qw)
            )
            if score > best_score:
                best_score = score
                best_topic = topic
    return best_topic if best_score > 0 else None


def _intent(msg: str) -> str:
    m = msg.lower()

    # Indicateurs de questions sur le fonctionnement de l'application (guide)
    is_howto = any(k in m for k in [
        'comment', 'aide', 'aide-moi', 'utiliser', 'faire', 'créer', 'générer',
        'configurer', 'paramétrer', 'accéder', 'étapes', 'procédure', 'tutoriel',
        'expliquer', 'guide', 'fonctionnement', 'à quoi sert', 'comment ça marche',
    ])

    # Mots-clés fonctionnels du guide (non liés aux données)
    is_guide_topic = any(k in m for k in [
        'connexion', 'login', 'mot de passe', 'compte utilisateur', 'rôle',
        'inscription', 'enregistrer élève', 'matricule', 'bulletin', 'générer',
        'relance', 'bourse', 'exonéré', 'certificat', 'attestation', 'convocation',
        'circulaire', 'signataire', 'signer', 'mobile money', 'orange money',
        'sms', 'notification', 'portail parent', 'portail', 'pwa',
        'sanction', 'discipline', 'appel', 'pointage', 'qr code',
        'examen', 'bac', 'bepc', 'cep', 'vacation', 'personnel',
        'année scolaire', 'trimestre', 'paramètre', 'sauvegarde', 'backup',
        'lent', 'lenteur', 'problème', 'erreur message',
    ])

    # Les requêtes de données priment sur le guide
    if any(k in m for k in ['cherche', 'recherche', 'trouve', 'fiche', 'renseigne']):
        return 'eleve'
    if any(k in m for k in ['recouvrement', 'encaissé', 'budget']) and not is_howto:
        return 'finances'
    if any(k in m for k in ['taux', 'montant encaissé', 'montant payé']) and not is_howto:
        return 'finances'
    if any(k in m for k in ['combien', 'effectif', 'nombre d\'inscrits', 'par classe']) and not is_howto:
        return 'effectifs'
    if any(k in m for k in ['baisse', 'hausse', 'régress', 'augment']) and not is_howto:
        return 'progression'
    if any(k in m for k in ['difficulté', 'faible', 'sous', 'inférieur', 'moins de']) \
            and any(k in m for k in ['/20', 'moyenne', 'note']) and not is_howto:
        return 'difficultes'
    if any(k in m for k in ['moyenne de la', 'moyennes de la', 'résultats de la', 'notes de la']) and not is_howto:
        return 'moyennes'
    if any(k in m for k in ['absen', 'assiduité', 'justifi']) \
            and any(k in m for k in ['liste', 'top', 'résumé', 'bilan', 'combien']) and not is_howto:
        return 'absences'
    if any(k in m for k in ['financ', 'paiement', 'payé', 'frais']) \
            and any(k in m for k in ['liste', 'rapport', 'résumé', 'bilan', 'combien', 'taux']) and not is_howto:
        return 'finances'

    # Guide si question fonctionnelle détectée
    if is_howto or is_guide_topic:
        return 'guide'

    return 'inconnu'


_AIDE = (
    "Je ne comprends pas la question. Voici ce que je sais faire :\n\n"
    "📊 Données en temps réel :\n"
    "  • Taux de recouvrement des frais de scolarité\n"
    "  • Effectifs par classe\n"
    "  • Résumé des absences\n"
    "  • Élèves en difficulté (ex : « sous 8/20 »)\n"
    "  • Élèves en baisse ou en hausse entre trimestres\n"
    "  • Moyennes d'une classe (ex : « moyennes de la 3ème A »)\n"
    "  • Rechercher un élève par nom\n\n"
    "📖 Guide d'utilisation (dites « comment » ou posez une question) :\n"
    "  • Comment enregistrer un paiement ?\n"
    "  • Comment générer un bulletin ?\n"
    "  • Comment faire l'appel ?\n"
    "  • Comment créer un compte utilisateur ?\n"
    "  • Comment configurer les signataires ?\n"
    "  • Comment envoyer des relances de paiement ?\n"
    "  • Comment attribuer une bourse ?\n"
    "  • Comment utiliser le portail parent ?\n\n"
    "Reformulez votre question en mentionnant l'un de ces thèmes."
)


def _process(user_message: str, etab) -> str:
    try:
        intent = _intent(user_message)
        classe = _extract_classe(user_message)
        trimestre = _extract_trimestre(user_message)

        if intent == 'eleve':
            nom, prenom = _extract_nom(user_message)
            return _fmt_eleve(_req_eleve(etab, nom=nom, prenom=prenom))

        if intent == 'finances':
            return _fmt_finances(_req_finances(etab, classe_nom=classe))

        if intent == 'absences':
            return _fmt_absences(_req_absences(etab, classe_nom=classe))

        if intent == 'progression':
            m = user_message.lower()
            sens = "hausse" if any(k in m for k in ['hausse', 'améliore', 'augment', 'progress']) else "baisse"
            return _fmt_progression(_req_progression(etab, classe_nom=classe, sens=sens))

        if intent == 'difficultes':
            seuil = _extract_seuil(user_message, default=10.0)
            return _fmt_difficultes(_req_difficultes(etab, classe_nom=classe, seuil=seuil, trimestre_numero=trimestre))

        if intent == 'moyennes':
            if not classe:
                return "Précisez la classe, par exemple : « Moyennes de la 3ème A »."
            return _fmt_moyennes(_req_moyennes(etab, classe_nom=classe, trimestre_numero=trimestre))

        if intent == 'effectifs':
            return _fmt_effectifs(_req_effectifs(etab, classe_nom=classe))

        if intent == 'guide':
            topic = _search_guide(user_message)
            if topic:
                return topic["réponse"]
            # Si aucun topic précis trouvé, proposer la liste
            return (
                "Je n'ai pas trouvé de réponse précise dans le guide pour cette question.\n\n"
                "Voici les sujets documentés :\n"
                + "\n".join(f"  • {t['titre']}" for t in _GUIDE_KB)
                + "\n\nPosez votre question avec des mots-clés plus précis."
            )

        return _AIDE

    except Exception:   # l'assistant ne doit jamais casser la page : on journalise et on répond proprement
        logger.exception("Erreur chatbot")
        return "Une erreur est survenue lors de la requête ; elle a été journalisée pour l'administrateur."


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée — interface avec la vue Django
# ─────────────────────────────────────────────────────────────────────────────

def chat(messages_history: list, user_message: str, etab) -> tuple[str, list]:
    """
    Traite un message pour l'établissement de l'utilisateur et retourne (réponse, historique_mis_à_jour).
    L'historique utilise le format {'role': ..., 'text': ...} directement.
    """
    response = _process(user_message, etab)
    updated = list(messages_history) + [
        {"role": "user", "text": user_message},
        {"role": "assistant", "text": response},
    ]
    if len(updated) > 20:
        updated = updated[-20:]
    return response, updated
