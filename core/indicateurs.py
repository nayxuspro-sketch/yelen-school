"""Historisation pluriannuelle des indicateurs (5.39.0) : effectifs, résultats, recouvrement et assiduité de chaque
année scolaire, figés dans ``IndicateurAnnee`` par la commande ``historiser_indicateurs`` (ou à la demande depuis
la page). Les statistiques annuelles deviennent une tendance sur le tableau de bord."""
from decimal import Decimal

from django.db.models import Avg
from django.utils import timezone

from inscriptions.models import Inscription, StatutInscriptionChoices
from pedagogie.models import MoyenneGenerale
from presences.models import Presence

CHAMPS = (
    'effectif', 'effectif_filles', 'effectif_garcons', 'moyenne_generale', 'taux_reussite',
    'taux_recouvrement', 'taux_absenteisme',
)


def _taux(part, total):
    return round(100 * part / total, 2) if total else None


def calculer(etablissement, annee):
    """Indicateurs de ``annee`` : dict des six mesures (+ détails chiffrés utiles à l'écran)."""
    from finances.views.commun import _situations_financieres_en_lot
    inscriptions = list(
        Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=etablissement)
        .select_related('eleve', 'statut_eleve')
    )
    actives = [i for i in inscriptions if i.statut != StatutInscriptionChoices.ABANDON]
    filles = sum(1 for i in actives if i.eleve.genre == 'F')
    situations = _situations_financieres_en_lot(actives) if actives else {}
    attendu = sum((s['total_du'] for s in situations.values()), Decimal('0'))
    encaisse = sum((s['total_paye'] for s in situations.values()), Decimal('0'))
    # Agrégats sur `moyenne_sur_20` : les moyennes sont stockées sur le barème du cycle (10 au primaire),
    # les additionner avec des classes sur 20 fausserait la moyenne et le taux de réussite de l'établissement.
    moyennes_classe = MoyenneGenerale.objects.filter(inscription__in=actives, moyenne_sur_20__isnull=False)
    moyenne = moyennes_classe.aggregate(m=Avg('moyenne_sur_20'))['m']
    reussite = moyennes_classe.filter(moyenne_sur_20__gte=10).count()
    avec_moyenne = moyennes_classe.count()
    presences = Presence.objects.filter(appel__annee_scolaire=annee, inscription__in=actives)
    pointages = presences.count()
    absences = presences.filter(statut='ABSENT').count()
    return {
        'effectif': len(actives), 'effectif_filles': filles, 'effectif_garcons': len(actives) - filles,
        'moyenne_generale': round(moyenne, 2) if moyenne is not None else None,
        'taux_reussite': _taux(reussite, avec_moyenne),
        'taux_recouvrement': _taux(encaisse, attendu),
        'taux_absenteisme': _taux(absences, pointages),
        'details': {'attendu': attendu, 'encaisse': encaisse, 'pointages': pointages, 'absences': absences,
                    'eleves_avec_moyenne': avec_moyenne, 'eleves_admis': reussite},
    }


def mettre_a_jour(etablissement, annees=None):
    """Crée ou met à jour la ligne d'indicateurs de chaque année demandée (toutes par défaut)."""
    from parametres.models import AnneeScolaire
    from .models import IndicateurAnnee
    if annees is None:
        annees = AnneeScolaire.objects.filter(etablissement=etablissement).order_by('date_debut')
    lignes = []
    for annee in annees:
        mesures = calculer(etablissement, annee)
        details = mesures.pop('details')
        ligne, _ = IndicateurAnnee.objects.update_or_create(
            etablissement=etablissement, annee_scolaire=annee,
            defaults={**mesures, 'details': {k: str(v) for k, v in details.items()},
                      'calcule_le': timezone.now()},
        )
        lignes.append(ligne)
    return lignes


def evolution(etablissement, limite=None):
    """Lignes d'indicateurs triées par année croissante, avec l'écart de chaque mesure par rapport à l'année
    précédente (points de pourcentage ou effectif) — None quand il n'y a pas d'année précédente."""
    from .models import IndicateurAnnee
    qs = IndicateurAnnee.objects.filter(etablissement=etablissement).select_related('annee_scolaire') \
        .order_by('annee_scolaire__date_debut')
    lignes = list(qs)
    precedent = None
    for ligne in lignes:
        ligne.ecarts = {}
        for champ in CHAMPS:
            valeur = getattr(ligne, champ)
            avant = getattr(precedent, champ) if precedent else None
            ligne.ecarts[champ] = (round(valeur - avant, 2) if valeur is not None and avant is not None else None)
        precedent = ligne
    return lignes[-limite:] if limite else lignes
