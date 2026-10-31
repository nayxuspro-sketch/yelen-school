"""Cycle de vie des données personnelles (loi n° 001-2021/AN portant protection des personnes à l'égard du
traitement des données à caractère personnel) : élèves sortis depuis plus de N années anonymisés, comptes
parents orphelins fermés, dossier d'un élève exportable (droit d'accès)."""
from datetime import date

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.audit import record_audit
from inscriptions.models import Eleve, PreInscription
from parametres.models import PolitiqueDonnees

CHAMPS_EFFACES = {
    'nom': 'ANONYMISÉ', 'prenom': '—', 'lieu_naissance': '', 'lieu_residence': '', 'telephone_urgence': '',
    'email': '', 'nom_pere': '', 'profession_pere': '', 'nom_mere': '', 'profession_mere': '',
    'telephone_parent': '', 'tuteur_nom': '', 'tuteur_telephone': '', 'tuteur_adresse': '', 'etablissement_origine': '',
    'groupe_sanguin': '', 'allergies': '', 'informations_medicales': '', 'medecin_traitant': '', 'personnes_autorisees': '',
}

# Registre des traitements (article 20 de la loi) : finalité, données, personnes, durée, destinataires.
REGISTRE = (
    ('Gestion de la scolarité', 'identité, naissance, photo, parents et tuteur, contacts, santé (allergies, médecin, personnes autorisées)',
     'élèves, parents', 'durée de conservation paramétrée après la dernière inscription', 'direction, secrétariat, enseignants (leurs classes)'),
    ('Évaluation et bulletins', 'notes, moyennes, appréciations, décisions de conseil', 'élèves', 'idem scolarité',
     'direction, enseignants, parents (portail), tutelle (statistiques anonymes)'),
    ('Présences et discipline', 'appels, absences, justificatifs, sanctions', 'élèves, parents', 'idem scolarité',
     'vie scolaire, direction, parents (portail)'),
    ('Frais de scolarité et paiements', 'tarifs, paiements, reçus, relances, Mobile Money (numéro du payeur)', 'élèves, parents',
     '10 ans (pièces comptables)', 'comptabilité, direction, comptable externe'),
    ('Communication', 'téléphones, SMS envoyés et reçus, messages et réponses, notifications', 'parents, personnel',
     'idem scolarité', 'direction, secrétariat'),
    ('Gestion du personnel', 'état civil, contrat, salaire, congés, absences, photo, signature', 'personnel',
     '10 ans après le départ', 'direction, comptabilité'),
    ('Comptes et sécurité', 'identifiants, rôles, journal d\u2019audit, adresses IP', 'personnel, parents, élèves',
     'durée du compte ; journal d\u2019audit 10 ans', 'super administrateur'),
)


def politique_de(etablissement):
    politique, _ = PolitiqueDonnees.objects.get_or_create(etablissement=etablissement)
    return politique


def date_limite(annees, aujourdhui=None):
    """Fin d'année scolaire la plus récente admise : tout élève dont la dernière inscription s'achève avant est sorti."""
    aujourdhui = aujourdhui or timezone.localdate()
    try:
        return aujourdhui.replace(year=aujourdhui.year - annees)
    except ValueError:                                   # 29 février
        return date(aujourdhui.year - annees, 2, 28)


def eleves_a_anonymiser(etablissement, annees=None):
    """Élèves de l'établissement dont toutes les années d'inscription sont terminées depuis plus de N ans."""
    annees = annees or politique_de(etablissement).duree_conservation_annees
    return (
        Eleve.objects.filter(inscriptions__classe__etablissement=etablissement, anonymise_le__isnull=True)
        .annotate(fin_derniere=Max('inscriptions__annee_scolaire__date_fin'))
        .filter(fin_derniere__lt=date_limite(annees))
        .distinct().order_by('nom', 'prenom')
    )


def _effacer_fichier(champ):
    if champ:
        champ.delete(save=False)
        return 1
    return 0


@transaction.atomic
def anonymiser(etablissement, user=None, request=None, annees=None):
    """Efface les données personnelles des élèves sortis (identité, contacts, santé, photo, justificatifs, PDF
    archivés, nom du payeur) et ferme les comptes parent/élève qui n'ont plus d'élève identifiable.
    Les données scolaires et financières (inscriptions, notes, paiements — registre immuable) restent, désormais anonymes."""
    from documents.models import Document
    from finances.models import DemandePaiementMobile, LigneReleve
    from presences.models import Justification
    politique = politique_de(etablissement)
    annees = annees or politique.duree_conservation_annees
    maintenant = timezone.now()
    nb_eleves = nb_fichiers = nb_comptes = 0
    for eleve in list(eleves_a_anonymiser(etablissement, annees)):
        for champ, valeur in CHAMPS_EFFACES.items():
            setattr(eleve, champ, valeur)
        nb_fichiers += _effacer_fichier(eleve.photo)
        eleve.photo = ''
        eleve.anonymise_le = maintenant
        eleve.is_active = False
        eleve.save()
        inscriptions = eleve.inscriptions.all()
        for justification in Justification.objects.filter(inscription__in=inscriptions).exclude(document=''):
            nb_fichiers += _effacer_fichier(justification.document)
            justification.document = ''
            justification.save(update_fields=['document'])
        for document in Document.objects.filter(inscription__in=inscriptions).exclude(fichier=''):
            nb_fichiers += _effacer_fichier(document.fichier)
            document.fichier = ''
            document.save(update_fields=['fichier'])
        DemandePaiementMobile.objects.filter(inscription__in=inscriptions).exclude(telephone='').update(telephone='')
        LigneReleve.objects.filter(paiement__inscription__in=inscriptions) \
            .exclude(nom_payeur='', telephone_payeur='').update(nom_payeur='', telephone_payeur='')
        for compte in eleve.utilisateurs_lies.all():
            if not compte.eleves_lies.filter(anonymise_le__isnull=True).exists():
                compte.first_name, compte.last_name, compte.email, compte.telephone = 'Compte', 'anonymisé', '', ''
                compte.username = f'anonyme-{compte.pk.hex[:12]}'
                compte.is_active = False
                compte.set_unusable_password()
                compte.save()
                nb_comptes += 1
        nb_eleves += 1
    nb_preinscriptions, _ = PreInscription.objects.filter(
        etablissement=etablissement, annee_scolaire__date_fin__lt=date_limite(annees)).delete()
    politique.derniere_anonymisation = maintenant
    politique.save(update_fields=['derniere_anonymisation'])
    bilan = {'eleves': nb_eleves, 'comptes': nb_comptes, 'fichiers': nb_fichiers, 'preinscriptions': nb_preinscriptions}
    record_audit(instance=politique, action='DELETE', changes=bilan, user=user, request=request,
                 reason=f'Anonymisation des élèves sortis depuis plus de {annees} ans')
    return bilan


def _valeur(v):
    from decimal import Decimal
    from django.db.models import Model
    from django.db.models.fields.files import FieldFile
    if isinstance(v, Model):
        return str(v)
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, FieldFile):
        return v.name or ''
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    return v


def _serialiser(obj, exclure=('id', 'created_by', 'is_active')):
    return {f.name: _valeur(getattr(obj, f.name)) for f in obj._meta.concrete_fields if f.name not in exclure}


def exporter_dossier(eleve):
    """Toutes les données détenues sur un élève (droit d'accès et de portabilité), prêtes pour un JSON."""
    from documents.models import Document
    from finances.models import Paiement
    from pedagogie.models import Note
    from presences.models import Justification, Presence
    from viescolaire.models import SanctionDisciplinaire
    inscriptions = eleve.inscriptions.select_related('annee_scolaire', 'classe').order_by('annee_scolaire__date_debut')
    return {
        'exporte_le': timezone.now().isoformat(),
        'eleve': _serialiser(eleve),
        'inscriptions': [_serialiser(i) for i in inscriptions],
        'paiements': [_serialiser(p) for p in Paiement.objects.filter(inscription__in=inscriptions).order_by('created_at')],
        'notes': [_serialiser(n) for n in Note.objects.filter(inscription__in=inscriptions).select_related('evaluation')],
        'presences': [_serialiser(p) for p in Presence.objects.filter(inscription__in=inscriptions).select_related('appel')],
        'justifications': [_serialiser(j) for j in Justification.objects.filter(inscription__in=inscriptions)],
        'sanctions': [_serialiser(s) for s in SanctionDisciplinaire.objects.filter(inscription__in=inscriptions)],
        'parcours': [_serialiser(e) for e in eleve.evenements_parcours.all()],
        'documents_generes': [_serialiser(d) for d in Document.objects.filter(inscription__in=inscriptions)],
        'comptes_lies': [{'identifiant': u.username, 'role': u.role, 'actif': u.is_active} for u in eleve.utilisateurs_lies.all()],
    }
