"""Portails parent et élève : données d'un enfant (emploi du temps, assiduité, justificatifs, notes, devoirs, cahier de
textes) et dépôt d'un justificatif d'absence par le parent."""
from datetime import date, timedelta

from django.db.models import Count
from django.utils import timezone

from core.validators import validate_piece_jointe
from pedagogie.models import CahierTextes, Note, Resultat
from presences.models import Justification, Presence
from viescolaire.models import ConfigEDT, JourSemaine, SanctionDisciplinaire, SeanceCours

DUREE_MAX_JUSTIFICATION = 31   # jours couverts au plus par un justificatif


def emploi_du_temps(inscription):
    """Séances de la classe par jour : [{'jour', 'aujourdhui', 'seances'}] sur les jours de classe configurés."""
    seances = list(
        SeanceCours.objects.filter(enseignement__classe=inscription.classe,
                                   enseignement__annee_scolaire=inscription.annee_scolaire,
                                   enseignement__est_actif=True)
        .select_related('enseignement__matiere', 'enseignement__personnel').order_by('jour', 'heure_debut')
    )
    config = ConfigEDT.pour(inscription.classe.etablissement)
    jours = sorted(set(config.get_jours_actifs()) | {s.jour for s in seances})
    aujourdhui = timezone.localdate().isoweekday()
    return [{'jour': JourSemaine(j).label, 'aujourdhui': j == aujourdhui, 'seances': [s for s in seances if s.jour == j]}
            for j in jours]


def assiduite(inscription, limite=30):
    """Compteurs de l'année (absences, excusées, retards) et dernières absences / retards."""
    qs = Presence.objects.filter(inscription=inscription).exclude(statut=Presence.StatutChoices.PRESENT)
    compteurs = {'absences': 0, 'excusees': 0, 'retards': 0}
    for statut, nb in qs.order_by().values_list('statut').annotate(n=Count('pk')):
        compteurs[{'ABSENT': 'absences', 'EXCUSE': 'excusees', 'RETARD': 'retards'}[statut]] = nb
    recentes = list(qs.select_related('appel__matiere').order_by('-appel__date', '-appel__heure_debut')[:limite])
    return compteurs, recentes


def justifications(inscription, limite=10):
    return list(Justification.objects.filter(inscription=inscription).order_by('-date_debut', '-created_at')[:limite])


def sanctions(inscription, limite=10):
    """Sanctions de l'année visibles par le parent (les annulées sont exclues)."""
    return list(SanctionDisciplinaire.objects.filter(inscription=inscription)
                .exclude(statut=SanctionDisciplinaire.StatutChoices.ANNULE)
                .select_related('type_sanction').order_by('-date_sanction')[:limite])


def notes_recentes(inscription, limite=15):
    return list(
        Note.objects.filter(inscription=inscription)
        .select_related('evaluation__enseignement__matiere', 'evaluation__type_evaluation')
        .order_by('-evaluation__date_planifiee', '-created_at')[:limite]
    )


def moyennes_par_periode(inscription):
    """[(trimestre, [résultats par matière])] dans l'ordre des périodes."""
    resultats = (Resultat.objects.filter(inscription=inscription)
                 .select_related('trimestre', 'enseignement__matiere')
                 .order_by('trimestre__numero', 'enseignement__matiere__nom'))
    periodes = {}
    for r in resultats:
        periodes.setdefault(r.trimestre, []).append(r)
    return list(periodes.items())


def prets_en_cours(inscription):
    """Ouvrages et manuels non rendus de l'élève, échéance la plus proche d'abord (prêts en retard signalés)."""
    from manuels.models import AttributionManuel
    prets = (
        AttributionManuel.objects
        .filter(inscription=inscription, date_retour__isnull=True)
        .select_related('exemplaire__manuel')
        .order_by('date_retour_prevue', 'date_attribution')
    )
    return [{'pret': p, 'titre': p.exemplaire.manuel.titre, 'code': p.exemplaire.code_exemplaire,
             'echeance': p.date_retour_prevue, 'en_retard': p.est_en_retard, 'retard': p.jours_de_retard}
            for p in prets]


def devoirs_a_venir(inscription, limite=5):
    """Devoirs de la classe non encore échus, par date de remise."""
    today = timezone.localdate()
    return list(
        CahierTextes.objects.filter(enseignement__classe=inscription.classe,
                                    enseignement__annee_scolaire=inscription.annee_scolaire,
                                    date_remise_devoirs__gte=today, devoirs__gt='')
        .select_related('enseignement__matiere').order_by('date_remise_devoirs')[:limite]
    )


def cahier_de_textes(inscription, jours=30):
    """Cours des ``jours`` derniers jours de la classe (contenu traité, devoirs donnés), du plus récent au plus ancien."""
    today = timezone.localdate()
    return list(
        CahierTextes.objects.filter(enseignement__classe=inscription.classe,
                                    enseignement__annee_scolaire=inscription.annee_scolaire,
                                    date__lte=today, date__gte=today - timedelta(days=jours))
        .select_related('enseignement__matiere').order_by('-date', '-heure_debut', '-created_at')
    )


def deposer_justification(inscription, par, date_debut, date_fin, motif, document=None):
    """Crée un justificatif « En attente » déposé par le parent ; lève ValueError si la demande est incomplète."""
    try:
        debut, fin = date.fromisoformat(date_debut or ''), date.fromisoformat(date_fin or '')
    except ValueError:
        raise ValueError("Indiquez les dates de début et de fin de l'absence.")
    motif = ' '.join((motif or '').split())
    if fin < debut:
        raise ValueError("La date de fin ne peut pas être antérieure à la date de début.")
    if fin - debut > timedelta(days=DUREE_MAX_JUSTIFICATION - 1):
        raise ValueError(f"Un justificatif couvre au plus {DUREE_MAX_JUSTIFICATION} jours.")
    if debut > timezone.localdate():
        raise ValueError("Une absence à venir se signale au secrétariat ; le justificatif se dépose après l'absence.")
    if not motif:
        raise ValueError("Indiquez le motif de l'absence.")
    if document:
        validate_piece_jointe(document)
    return Justification.objects.create(inscription=inscription, date_debut=debut, date_fin=fin, motif=motif[:500],
                                        document=document, deposee_par=par)
