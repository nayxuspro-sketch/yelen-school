"""
Services pour le module Paramètres
=====================================
YELEN SCHOOL — Logique métier des paramètres généraux.
"""

import logging
from datetime import date

from django.utils import timezone

logger = logging.getLogger(__name__)


def auto_generer_annee_scolaire(etablissement=None, force=False):
    """
    Génère automatiquement la nouvelle année scolaire pour chaque
    établissement à partir du 5 juillet.

    Règles métier :
    - Si la date courante >= 5 juillet, on crée l'année ``YYYY-YYYY+1``
    - ``date_debut`` = 1er octobre de l'année en cours
    - ``date_fin``   = 30 juin de l'année suivante
    - L'ancienne année courante passe à ``est_courante=False``
    - Si l'année existe déjà pour un établissement, on ne la crée pas

    Args:
        etablissement: Instance ou None (tous les établissements actifs)
        force: Ignorer la date (pour usage manuel via la commande)

    Returns:
        list[AnneeScolaire]: Nouvelles années créées
    """
    from etablissements.models import Etablissement
    from parametres.models import AnneeScolaire

    today = timezone.now().date()
    an = today.year

    # Vérification : à partir du 5 juillet uniquement
    if not force and (today.month < 7 or (today.month == 7 and today.day < 5)):
        return []

    # Libellé de la prochaine année scolaire
    debut_an = an
    fin_an = an + 1
    libelle = f"{debut_an}-{fin_an}"

    etablissements = Etablissement.objects.filter(is_active=True)
    if etablissement is not None:
        etablissements = etablissements.filter(pk=etablissement.pk)

    created = []
    for etab in etablissements:
        if AnneeScolaire.objects.filter(
            etablissement=etab, libelle=libelle
        ).exists():
            logger.info(
                "Année %s déjà existante pour %s — ignorée", libelle, etab.nom
            )
            continue

        date_debut = date(debut_an, 10, 1)
        date_fin = date(fin_an, 6, 30)

        AnneeScolaire.objects.filter(
            etablissement=etab, est_courante=True
        ).update(est_courante=False)

        nouvelle = AnneeScolaire.objects.create(
            etablissement=etab,
            libelle=libelle,
            date_debut=date_debut,
            date_fin=date_fin,
            est_courante=True,
            cloturee=False,
        )

        logger.info(
            "Nouvelle année scolaire créée : %s pour %s", libelle, etab.nom
        )
        created.append(nouvelle)

    return created
