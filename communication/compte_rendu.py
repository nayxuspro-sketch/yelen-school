"""Compte rendu quotidien du promoteur par SMS : encaissements, caisse et absences du jour en un seul SMS
(≤ 160 caractères, sans caractère hors du jeu GSM : pas de ç ni d'accent circonflexe).

Déclencheur ``DeclencheurSMS`` de type ``COMPTE_RENDU`` (Paramètres → SMS automatiques) : numéros du promoteur
et heure d'envoi. Le SMS du jour part par le service SMS (``sms_recus --boucle``, ``envoyer_comptes_rendus_dus``)
dès que l'heure est passée, une seule fois par jour ; le bouton « Tester » envoie le compte rendu du moment sans
entamer l'envoi du jour (``envoyer``). Les chiffres sont ceux des écrans Journal de caisse, Dépenses et Appels.
"""
import logging
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

LIMITE = 160


def _montant(valeur):
    return f"{Decimal(valeur or 0):,.0f}".replace(',', ' ') + ' F'


def _sigle(etab):
    from parametres.models import IdentiteEtablissement
    identite = IdentiteEtablissement.objects.filter(etablissement=etab).only('sigle').first()
    return ((identite.sigle if identite else '') or etab.code or 'YELEN')[:12]


def chiffres_du_jour(etab, jour):
    """Agrégats du compte rendu (mêmes calculs que le journal de caisse, la liste des dépenses et les appels)."""
    from finances.caisse import caissiers_du_jour, paiements_du_jour, remboursements_du_jour, totaux_journee
    from finances.models import ClotureCaisse, Depense, StatutDepense
    from presences.models import Presence

    paiements = paiements_du_jour(etab, jour)
    totaux = totaux_journee(paiements, remboursements_du_jour(etab, jour))
    depenses = Depense.objects.filter(annee_scolaire__etablissement=etab, date_depense=jour,
                                      statut=StatutDepense.VALIDEE).aggregate(total=Sum('montant'), nb=Count('pk'))
    clotures = ClotureCaisse.objects.filter(etablissement=etab, date=jour).aggregate(nb=Count('pk'), ecart=Sum('ecart'))
    presences = Presence.objects.filter(appel__classe__etablissement=etab, appel__date=jour)

    def eleves(statut):
        return presences.filter(statut=statut).values('inscription').distinct().count()

    return {
        'encaisse': totaux['total'], 'nb_paiements': paiements.count(),
        'rembourse': totaux['total_rembourse'], 'especes': totaux['especes_theoriques'],
        'depenses': depenses['total'] or Decimal('0'), 'nb_depenses': depenses['nb'],
        'caissiers': len(caissiers_du_jour(etab, jour)), 'caisses_arretees': clotures['nb'],
        'ecart': clotures['ecart'] or Decimal('0'),
        'appels': presences.order_by().values('appel').distinct().count(),
        'absents': eleves(Presence.StatutChoices.ABSENT), 'retards': eleves(Presence.StatutChoices.RETARD),
    }


def composer(etab, jour, chiffres=None):
    """Texte du compte rendu de ``jour``. Au-delà de 160 caractères (gros montants, remboursement et écart le
    même jour), les précisions sont retirées dans l'ordre : retards, nombre de reçus, espèces et écart."""
    c = chiffres or chiffres_du_jour(etab, jour)
    for niveau in range(4):
        encaisse = f"Encaisse {_montant(c['encaisse'])}"
        if niveau < 2:
            encaisse += f" ({c['nb_paiements']} recus)"
        if c['rembourse']:
            encaisse += f", rembourse {_montant(c['rembourse'])}"
        if c['caissiers'] and niveau < 3:
            encaisse += f", especes {_montant(c['especes'])}"
        phrases = [encaisse, f"Depenses {_montant(c['depenses'])}"]
        if c['caissiers']:
            caisse = f"Caisses arretees {c['caisses_arretees']}/{c['caissiers']}"
            if c['ecart'] and niveau < 3:
                caisse += f", ecart {'+' if c['ecart'] > 0 else '-'}{_montant(abs(c['ecart']))}"
            phrases.append(caisse)
        if c['appels']:
            absences = f"Absents {c['absents']}"
            if niveau < 1:
                absences += f", retards {c['retards']}"
            absences += f" ({c['appels']} appel{'s' if c['appels'] > 1 else ''})"
        else:
            absences = "Aucun appel saisi"
        phrases.append(absences)
        texte = f"{_sigle(etab)} {jour:%d/%m}: " + '. '.join(phrases) + '.'
        if len(texte) <= LIMITE:
            break
    return texte


def envoyer(declencheur, jour=None, dry_run=False):
    """Met en file le compte rendu de ``jour`` (défaut : aujourd'hui) pour chaque numéro configuré.
    Retourne le nombre de SMS (0 sans destinataire)."""
    numeros = declencheur.liste_destinataires()
    if not numeros:
        return 0
    texte = composer(declencheur.etablissement, jour or timezone.localdate())
    if not dry_run:
        from core.tasks import envoyer_sms_async
        for numero in numeros:
            envoyer_sms_async(numero, texte)
    logger.info("Compte rendu quotidien %s → %s destinataire(s)%s", declencheur.etablissement_id, len(numeros),
                ' (simulé)' if dry_run else '')
    return len(numeros)


def envoyer_comptes_rendus_dus(maintenant=None):
    """Service SMS : envoie les comptes rendus actifs dont l'heure est passée et qui ne sont pas encore partis
    aujourd'hui (``last_run`` du jour). Retourne le nombre de SMS mis en file."""
    from core.sms import sms_actifs
    from parametres.models import DeclencheurSMS

    if not sms_actifs():
        return 0
    maintenant = timezone.localtime(maintenant)
    total = 0
    dus = (DeclencheurSMS.objects.filter(type_declencheur=DeclencheurSMS.TypeChoices.COMPTE_RENDU, actif=True,
                                         heure_envoi__lte=maintenant.time())
           .exclude(destinataires='').select_related('etablissement'))
    for declencheur in dus:
        if declencheur.last_run and timezone.localtime(declencheur.last_run).date() >= maintenant.date():
            continue
        nb = envoyer(declencheur, maintenant.date())
        declencheur.last_run = maintenant
        declencheur.nb_envoyes_total = (declencheur.nb_envoyes_total or 0) + nb
        declencheur.save(update_fields=['last_run', 'nb_envoyes_total'])
        total += nb
    return total
