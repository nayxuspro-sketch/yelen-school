"""Ordre officiel des niveaux d'enseignement (préscolaire → terminale).

Le niveau d'une classe est un libellé libre (« 6ème », « 6e A », « Tle D », « CM2 »…) : ces helpers le ramènent
à une clé canonique pour trier les niveaux et proposer la classe de passage.
"""
import re
import unicodedata

NIVEAUX = ['PS', 'MS', 'GS', 'CP1', 'CP2', 'CE1', 'CE2', 'CM1', 'CM2', '6', '5', '4', '3', '2', '1', 'T']


def cle_niveau(niveau):
    """Clé canonique d'un libellé (« 6ème A » → '6', « Terminale D » → 'T', « CM2 » → 'CM2') ; un libellé
    inconnu est renvoyé normalisé (majuscules, sans accents)."""
    cle = unicodedata.normalize('NFKD', niveau or '').encode('ascii', 'ignore').decode().upper().strip()
    if cle.startswith('TERM') or cle.startswith('TLE'):
        return 'T'
    chiffre = re.match(r'(\d+)', cle)
    if chiffre and not re.match(r'(CP|CE|CM)\d', cle):
        return chiffre.group(1)
    return cle


def rang_niveau(niveau):
    """Clé de tri : ordre officiel des niveaux, puis les libellés inconnus par ordre alphabétique."""
    cle = cle_niveau(niveau)
    return (NIVEAUX.index(cle), '') if cle in NIVEAUX else (len(NIVEAUX), cle)


def niveau_suivant(niveau):
    """Clé du niveau immédiatement supérieur, ou None (niveau inconnu ou terminal)."""
    cle = cle_niveau(niveau)
    if cle not in NIVEAUX or cle == NIVEAUX[-1]:
        return None
    return NIVEAUX[NIVEAUX.index(cle) + 1]
