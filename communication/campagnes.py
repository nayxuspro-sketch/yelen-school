"""Campagnes SMS ciblées : public, destinataires dédoublonnés par numéro, message personnalisé par variables, mise en
file par lot (un seul fil d'envoi) et suivi par campagne."""
import threading
from dataclasses import dataclass, field
from datetime import date

from django.db import transaction
from django.utils import timezone

from core.models import CampagneSms, SmsSortant
from core.sms import _normaliser_numero, _numero_valide
from core.tasks import _vider_file, mettre_en_file_lot
from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.models import ModeleMessage
from personnel.models import MembrePersonnel
from presences.models import Presence

LONGUEUR_SMS = 160
VARIABLES = (
    ('{eleve}', "nom de l'élève (ou des enfants joints sur ce numéro)"),
    ('{classe}', "classe de l'élève"),
    ('{reste}', "reste à payer de la famille, en FCFA"),
    ('{etablissement}', "sigle ou nom de l'établissement"),
    ('{nom}', "nom de l'agent (campagne personnel)"),
)


@dataclass
class Destinataire:
    numero: str
    nom: str
    variables: dict = field(default_factory=dict)
    enfants: list = field(default_factory=list)


def _montant(valeur):
    return f"{int(valeur):,}".replace(',', ' ')


def _telephone_parent(eleve):
    """Premier numéro de parent valide de la fiche élève, normalisé ; '' s'il n'y en a pas."""
    return eleve.telephone_parent_valide()


def _inscriptions(etab, annee, cible, criteres):
    qs = (Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=etab)
          .exclude(statut=StatutInscriptionChoices.ABANDON)
          .select_related('eleve', 'classe').order_by('classe__nom', 'eleve__nom', 'eleve__prenom'))
    if cible == CampagneSms.Cible.PARENTS_CLASSES:
        qs = qs.filter(classe_id__in=criteres.get('classes') or [])
    elif cible == CampagneSms.Cible.PARENTS_ABSENTS:
        jour = criteres.get('date') or date.today().isoformat()
        absents = Presence.objects.filter(appel__date=jour, statut=Presence.StatutChoices.ABSENT).values('inscription_id')
        qs = qs.filter(pk__in=absents)
    return list(qs)


def destinataires(etab, annee, cible, criteres, sigle=''):
    """Destinataires dédoublonnés par numéro et compteurs ``{'sans_numero': n}`` (élèves ou agents injoignables).
    Un numéro partagé par plusieurs enfants reçoit un seul SMS ; {eleve} et {classe} y énumèrent les enfants."""
    groupes, sans_numero = {}, 0
    if cible == CampagneSms.Cible.PERSONNEL:
        for membre in MembrePersonnel.objects.filter(etablissement=etab, is_active=True).order_by('nom', 'prenom'):
            brut = (membre.telephone or '').strip()
            if not (brut and _numero_valide(brut)):
                sans_numero += 1
                continue
            numero = _normaliser_numero(brut)
            if numero not in groupes:
                groupes[numero] = Destinataire(numero, membre.get_nom_complet(),
                                               {'nom': membre.get_nom_complet(), 'etablissement': sigle})
        return list(groupes.values()), {'sans_numero': sans_numero}

    inscriptions = _inscriptions(etab, annee, cible, criteres)
    restes = {}
    if cible == CampagneSms.Cible.PARENTS_RETARD:
        from finances.views.commun import _situations_financieres_en_lot
        situations = _situations_financieres_en_lot(inscriptions)
        restes = {pk: s['reste_a_payer'] for pk, s in situations.items() if s['reste_a_payer'] > 0}
        inscriptions = [ins for ins in inscriptions if ins.pk in restes]
    for ins in inscriptions:
        numero = _telephone_parent(ins.eleve)
        if not numero:
            sans_numero += 1
            continue
        groupe = groupes.get(numero)
        if groupe is None:
            groupe = groupes[numero] = Destinataire(numero, '', {'etablissement': sigle})
        groupe.enfants.append(ins)
    for groupe in groupes.values():
        noms = [ins.eleve.get_nom_complet() for ins in groupe.enfants]
        classes = list(dict.fromkeys(ins.classe.nom for ins in groupe.enfants))
        groupe.nom = ', '.join(noms)
        groupe.variables.update({
            'eleve': ', '.join(noms), 'classe': ', '.join(classes),
            'reste': _montant(sum(restes.get(ins.pk, 0) for ins in groupe.enfants)),
        })
    return list(groupes.values()), {'sans_numero': sans_numero}


def rendre(modele, variables):
    """Remplace les variables connues ; une variable inconnue reste telle quelle (visible à l'aperçu)."""
    return ModeleMessage.rendre(modele, variables).strip()


def apercu(modele, liste):
    """Messages rendus pour l'aperçu : [(destinataire, texte, longueur)] et la longueur du plus long."""
    rendus = [(d, rendre(modele, d.variables)) for d in liste]
    return [(d, texte, len(texte)) for d, texte in rendus], max((len(t) for _, t in rendus), default=len(modele))


def lancer(etab, annee, titre, modele, cible, criteres, liste, par):
    """Crée la campagne et met ses SMS en file (un seul fil d'envoi) ; retourne la campagne."""
    with transaction.atomic():
        campagne = CampagneSms.objects.create(
            etablissement=etab, annee_scolaire=annee, titre=titre, message=modele, cible=cible, criteres=criteres,
            nb_destinataires=len(liste), envoyee_par=par,
        )
        mettre_en_file_lot([(d.numero, rendre(modele, d.variables), d.nom) for d in liste], campagne=campagne)
    return campagne


def renvoyer_echecs(campagne):
    """Remet en file les SMS en échec définitif de la campagne ; retourne leur nombre."""
    nb = campagne.sms.filter(statut=SmsSortant.Statut.ECHEC).update(
        statut=SmsSortant.Statut.EN_ATTENTE, tentatives=0, prochaine_tentative=timezone.now(), derniere_erreur='',
    )
    if nb:
        transaction.on_commit(lambda: threading.Thread(target=_vider_file, daemon=True).start())
    return nb
