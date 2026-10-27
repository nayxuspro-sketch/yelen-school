"""
bulletins/services.py — Services métier pour les bulletins
=====================================================
YELEN SCHOOL v3.4

Ce module contient la logique de calcul pour :
- Bulletin trimestriel (workflow de publication)
- Bulletin annuel de notes (calcul de la moyenne de passage)
"""

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from pedagogie.models import Resultat, Trimestre

logger = logging.getLogger(__name__)

CHAMPS_ASSIDUITE = ('absences_justifiees', 'absences_non_justifiees', 'retards')


def assiduite_depuis_presences(trimestre, inscriptions):
    """Assiduité relevée dans Présences entre les dates du trimestre, par inscription :
    ``{inscription_id: {'absences_justifiees': h, 'absences_non_justifiees': h, 'retards': n}}``.
    Absence excusée → justifiée, absence simple → non justifiée, en heures (durée de la séance, une heure si
    l'appel n'a pas d'horaire, arrondi au plus proche) ; les retards sont comptés en nombre."""
    from presences.models import Presence

    statuts = Presence.StatutChoices
    cles = {statuts.EXCUSE: 'absences_justifiees', statuts.ABSENT: 'absences_non_justifiees'}
    cumuls = {}
    lignes = Presence.objects.filter(
        inscription__in=inscriptions, statut__in=(statuts.ABSENT, statuts.EXCUSE, statuts.RETARD),
        appel__date__range=(trimestre.date_debut, trimestre.date_fin),
    ).values_list('inscription_id', 'statut', 'appel__heure_debut', 'appel__heure_fin')
    for inscription_id, statut, debut, fin in lignes:
        cumul = cumuls.setdefault(inscription_id, {c: Decimal('0') for c in CHAMPS_ASSIDUITE})
        if statut == statuts.RETARD:
            cumul['retards'] += 1
            continue
        heures = Decimal('1')
        if debut and fin and fin > debut:
            heures = Decimal((fin.hour * 60 + fin.minute) - (debut.hour * 60 + debut.minute)) / 60
        cumul[cles[statut]] += heures
    return {
        pk: {c: int(v.quantize(Decimal('1'), rounding=ROUND_HALF_UP)) for c, v in cumul.items()}
        for pk, cumul in cumuls.items()
    }


def assiduite_bulletin(fiche, trimestre, inscription, releve=None):
    """Valeurs imprimées sur le bulletin : celles de la fiche si elle existe, sinon le relevé de Présences
    (``releve`` : résultat de ``assiduite_depuis_presences`` déjà calculé pour la classe)."""
    if fiche is not None:
        return {c: getattr(fiche, c) for c in CHAMPS_ASSIDUITE}
    if releve is None:
        releve = assiduite_depuis_presences(trimestre, [inscription])
    return releve.get(inscription.pk) or dict.fromkeys(CHAMPS_ASSIDUITE, 0)


def calculer_bulletin_annuel(inscription, annee_scolaire):
    """
    Calcule (ou recalcule) le bulletin annuel d'un élève pour une année scolaire.
    
    Crée ou met à jour l'enregistrement BulletinAnnuel correspondant.
    
    Règles de calcul :
    - moyenne_periode  = Σ(note × coefficient) / Σ(coefficient) pour chaque période
    - moyenne_annuelle = Σ(moyenne_periode) / nombre_periodes
    - est_admis        = moyenne_annuelle >= 10.00
    
    Args:
        inscription: Instance d'Inscription
        annee_scolaire: Instance d'AnneeScolaire
        
    Returns:
        Instance de BulletinAnnuel
    """
    from bulletins.models import BulletinAnnuel
    
    # Récupérer les trimestres pour cette année scolaire
    trimestres = Trimestre.objects.filter(
        annee_scolaire=annee_scolaire,
    ).order_by('numero')
    
    donnees_periodes = []
    somme_moyennes = Decimal("0.00")
    
    for trimestre in trimestres:
        # Récupérer les résultats (moyennes par matière) pour ce trimestre
        # select_related évite les requêtes N+1 sur enseignement → matière
        resultats = Resultat.objects.filter(
            inscription=inscription,
            trimestre=trimestre,
        ).select_related('enseignement__matiere')

        if not resultats.exists():
            continue

        # Construction de la liste des matières avec notes
        matieres_data = []
        total_coeff = Decimal("0.00")
        total_points = Decimal("0.00")

        for idx, resultat in enumerate(resultats):
            if resultat.dispense:
                continue

            coeff = resultat.coefficient_utilise or Decimal("1.00")
            note = resultat.moyenne_sur_20

            if note is not None:
                note_ponderee = note * coeff
                # Accès au nom de la matière via enseignement (relation correcte)
                try:
                    matiere_nom = resultat.enseignement.matiere.nom
                except Exception:
                    logger.warning("Bulletin annuel : matière introuvable (résultat %s)", resultat.pk, exc_info=True)
                    matiere_nom = f"Matière {idx + 1}"
                
                matieres_data.append({
                    'nom': matiere_nom,
                    'coefficient': int(coeff),
                    'note': float(note),
                    'note_ponderee': float(note_ponderee),
                })
                total_coeff += coeff
                total_points += note_ponderee
        
        if total_coeff > 0:
            moy_periode = (total_points / total_coeff).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            moy_periode = Decimal("0.00")
        
        somme_moyennes += moy_periode
        donnees_periodes.append({
            'id': str(trimestre.pk),
            'nom': trimestre.nom,
            'numero': trimestre.numero,
            'matieres': matieres_data,
            'total_coefficients': int(total_coeff),
            'total_points': float(total_points),
            'moyenne_periode': float(moy_periode),
        })
    
    # Calcul de la moyenne annuelle
    n = len(donnees_periodes)
    if n > 0:
        moy_annuelle = (somme_moyennes / n).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        moy_annuelle = Decimal("0.00")
    
    est_admis = moy_annuelle >= Decimal("10.00")
    
    # Calcul des statistiques de classe
    stats_classe = calculer_statistiques_classe(
        inscription.classe, annee_scolaire
    )
    
    # Calcul du rang annuel
    rang_annuel = calculer_rang_annuel(
        inscription, annee_scolaire, moy_annuelle
    )
    
    donnees_json = {
        'periodes': donnees_periodes,
        'nombre_periodes': n,
        'somme_moyennes_periodes': float(somme_moyennes),
        'moyenne_annuelle': float(moy_annuelle),
        'seuil_passage': 10.00,
        'est_admis': est_admis,
        'decision': "Admis en classe supérieure" if est_admis else "Redouble en classe",
    }
    
    # Mise à jour ou création du bulletin
    bulletin, _ = BulletinAnnuel.objects.update_or_create(
        inscription=inscription,
        annee_scolaire=annee_scolaire,
        defaults={
            'donnees_json': donnees_json,
            'moyenne_annuelle': moy_annuelle,
            'est_admis': est_admis,
            'rang_annuel': rang_annuel,
            'effectif_classe': stats_classe['effectif'],
            'moyenne_max_classe': stats_classe['moyenne_max'],
            'moyenne_min_classe': stats_classe['moyenne_min'],
            'moyenne_classe': stats_classe['moyenne_classe'],
            'date_signature': date.today(),
            'lieu_signature': inscription.classe.etablissement.ville if inscription.classe.etablissement else '',
        },
    )
    return bulletin


def calculer_statistiques_classe(classe, annee_scolaire):
    """
    Calcule les statistiques (min, max, moyenne) pour une classe donnée.
    
    Args:
        classe: Instance de Classe
        annee_scolaire: Instance d'AnneeScolaire
        
    Returns:
        Dict avec 'effectif', 'moyenne_max', 'moyenne_min', 'moyenne_classe'
    """
    from bulletins.models import BulletinAnnuel
    
    bulletins = BulletinAnnuel.objects.filter(
        inscription__classe=classe,
        annee_scolaire=annee_scolaire,
    )
    
    stats = bulletins.aggregate(
        effectif=models.Count('id'),
        moyenne_max=models.Max('moyenne_annuelle'),
        moyenne_min=models.Min('moyenne_annuelle'),
        moyenne_classe=models.Avg('moyenne_annuelle'),
    )
    
    return {
        'effectif': stats['effectif'] or 0,
        'moyenne_max': stats['moyenne_max'],
        'moyenne_min': stats['moyenne_min'],
        'moyenne_classe': stats['moyenne_classe'],
    }


def calculer_rang_annuel(inscription, annee_scolaire, moyenne_annuelle):
    """
    Calcule le rang annuel de l'élève dans sa classe.
    
    Args:
        inscription: Instance d'Inscription
        annee_scolaire: Instance d'AnneeScolaire
        moyenne_annuelle: Decimal - moyenne de l'élève
        
    Returns:
        Integer - rang de l'élève
    """
    from bulletins.models import BulletinAnnuel
    
    # Compter le nombre d'élèves avec une moyenne supérieure à celle de l'élève
    rang = BulletinAnnuel.objects.filter(
        inscription__classe=inscription.classe,
        annee_scolaire=annee_scolaire,
        moyenne_annuelle__gt=moyenne_annuelle,
    ).count() + 1
    
    return rang


def generer_bulletins_annuels_classe(classe, annee_scolaire):
    """
    Génère les bulletins annuels pour tous les élèves d'une classe.
    
    Args:
        classe: Instance de Classe
        annee_scolaire: Instance d'AnneeScolaire
        
    Returns:
        Liste des bulletins générés
    """
    from inscriptions.models import Inscription
    
    inscriptions = Inscription.objects.filter(
        classe=classe,
        statut__in=['actif', 'former'],
        annee_scolaire=annee_scolaire,
    )
    
    bulletins = []
    for inscription in inscriptions:
        bulletin = calculer_bulletin_annuel(inscription, annee_scolaire)
        bulletins.append(bulletin)
    
    return bulletins