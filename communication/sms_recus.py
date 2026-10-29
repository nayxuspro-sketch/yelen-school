"""Réception des SMS des parents (Parent-SMS Direct).

Deux chemins amènent un SMS reçu par le téléphone passerelle jusqu'ici :
  - le webhook de l'app Android SMS Gateway (push, instantané — exige que le téléphone joigne YELEN en HTTPS) ;
  - la relève de la boîte de réception du téléphone par le serveur (GET /inbox de l'app, pull toutes les
    quelques secondes — n'exige que ce que l'envoi exige déjà : joindre le téléphone sur le réseau local).
Les deux passent par ``traiter_sms_recu`` ; l'identifiant du message (même empreinte des deux côtés) évite
qu'un SMS arrivé par les deux chemins soit traité, et donc répondu, deux fois.
"""
import json
import logging
import re
import urllib.error

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

CLE_ETAT_RELEVE = 'sms:releve:etat'          # dernier bilan de relève (page Configuration SMS)
CLE_REPERE_RELEVE = 'sms:releve:repere'      # createdAt (horloge du téléphone) du dernier SMS pris en compte
DUREE_CACHE_RELEVE = 90 * 24 * 3600


def identifiant_message(brut):
    """Empreinte commune d'un SMS reçu : le webhook envoie ``messageId`` = hashCode non signé en hexadécimal,
    la boîte de réception ``id`` = « text:<hashCode signé décimal> » — ramenés à la même forme."""
    brut = str(brut or '').strip()
    if ':' in brut:
        prefixe, _, valeur = brut.partition(':')
        if prefixe in ('text', 'data', 'mms', 'mms-header') and re.fullmatch(r'-?\d+', valeur):
            return f'{int(valeur) & 0xFFFFFFFF:x}'
    return brut.lower()[:64]


def traiter_sms_recu(sender_number, message_text, message_id=''):
    """Interprète un SMS reçu (AIDE / NOTE / SOLDE / ABS, ou message libre), le journalise et met la réponse en file.
    Retourne ``(journal, créé)`` ; ``créé`` est faux si ce message avait déjà été traité (autre chemin)."""
    from inscriptions.models import Eleve, Inscription, StatutInscriptionChoices
    from pedagogie.models import MoyenneGenerale
    from presences.models import Presence
    from finances.views import _calcul_situation_financiere
    from core.sms import _normaliser_numero
    from core.tasks import envoyer_sms_async
    from .models import IncomingSMSLog

    if message_id:
        existant = IncomingSMSLog.objects.filter(message_id=message_id).first()
        if existant is not None:
            return existant, False

    try:
        sender_normalized = _normaliser_numero(sender_number)
    except (AttributeError, TypeError, ValueError):
        logger.warning("SMS reçu : numéro expéditeur illisible : %r", sender_number)
        sender_normalized = sender_number

    clean_msg = re.sub(r'\s+', ' ', message_text).strip().upper()

    command_type = 'INVALID'
    eleve = None
    response_text = ""
    is_authorized = False
    processed_successfully = False
    error_message = ""

    help_pattern = re.compile(r'^(HELP|AIDE)$')
    note_pattern = re.compile(r'^NOTE\s+([A-Z0-9\-]+)(?:\s+(T\d+|\d+))?$')
    solde_pattern = re.compile(r'^SOLDE\s+([A-Z0-9\-]+)$')
    abs_pattern = re.compile(r'^ABS(?:ENCE)?\s+([A-Z0-9\-]+)$')

    if help_pattern.match(clean_msg):
        command_type = 'HELP'
        response_text = "Yelen - Commandes: NOTE <matricule> [trimestre] (ex: NOTE BF-2026-0001 T1), SOLDE <matricule> (situation finance), ABS <matricule> (absences)."
        is_authorized = True
        processed_successfully = True
    else:
        match_note = note_pattern.match(clean_msg)
        match_solde = solde_pattern.match(clean_msg)
        match_abs = abs_pattern.match(clean_msg)

        matricule = ""
        trim_str = ""

        if match_note:
            command_type = 'NOTE'
            matricule = match_note.group(1)
            trim_str = match_note.group(2) or ""
        elif match_solde:
            command_type = 'SOLDE'
            matricule = match_solde.group(1)
        elif match_abs:
            command_type = 'ABS'
            matricule = match_abs.group(1)

        if command_type != 'INVALID':
            eleve = Eleve.objects.filter(matricule__iexact=matricule).first()
            if not eleve:
                error_message = f"Eleve avec le matricule {matricule} introuvable."
                response_text = f"Yelen - Eleve avec le matricule {matricule} introuvable."
            else:
                candidate_numbers = [
                    eleve.telephone_parent,
                    eleve.tuteur_telephone,
                    eleve.telephone_urgence,
                    eleve.telephone if hasattr(eleve, 'telephone') else ''
                ]
                normalized_candidates = []
                for c in candidate_numbers:
                    if c and str(c).strip():
                        try:
                            normalized_candidates.append(_normaliser_numero(str(c)))
                        except (AttributeError, TypeError, ValueError):
                            logger.warning("SMS reçu : numéro parent illisible : %r", c)

                master_numbers = getattr(settings, 'MASTER_SMS_NUMBERS', [])
                for mn in master_numbers:
                    if mn:
                        try:
                            normalized_candidates.append(_normaliser_numero(str(mn)))
                        except (AttributeError, TypeError, ValueError):
                            logger.warning("SMS reçu : numéro parent illisible : %r", mn)

                if sender_normalized in normalized_candidates:
                    is_authorized = True
                    inscription = Inscription.objects.filter(eleve=eleve, annee_scolaire__est_courante=True).first()
                    if not inscription:
                        inscription = Inscription.objects.filter(eleve=eleve).order_by('-annee_scolaire__date_debut').first()

                    if not inscription:
                        error_message = "Aucune inscription trouvee pour cet eleve."
                        response_text = f"Yelen - {eleve.prenom} {eleve.nom} n'est inscrit dans aucune classe."
                    else:
                        if command_type == 'NOTE':
                            trim_num = None
                            if trim_str:
                                digits = re.findall(r'\d+', trim_str)
                                if digits:
                                    trim_num = int(digits[0])

                            mg_qs = MoyenneGenerale.objects.filter(inscription=inscription)
                            if trim_num is not None:
                                mg = mg_qs.filter(trimestre__numero=trim_num).first()
                                trim_label = f"T{trim_num}"
                            else:
                                mg = mg_qs.order_by('-trimestre__numero').first()
                                trim_label = mg.trimestre.nom if mg else "Trimestre"

                            if mg and mg.moyenne is not None:
                                total_eleves = Inscription.objects.filter(
                                    classe=inscription.classe,
                                    annee_scolaire=inscription.annee_scolaire
                                ).exclude(statut=StatutInscriptionChoices.ABANDON).count()

                                rang_str = f"{mg.rang}/{total_eleves}" if mg.rang else "N/A"
                                response_text = f"Yelen - {eleve.prenom} {eleve.nom} ({inscription.classe.nom}) - {trim_label}: Moy: {mg.moyenne}/20, Rang: {rang_str}."
                                processed_successfully = True
                            else:
                                error_message = f"Aucune moyenne trouvee pour la periode {trim_label}."
                                response_text = f"Yelen - Aucune moyenne trouvee pour {eleve.prenom} {eleve.nom} ({trim_label})."

                        elif command_type == 'SOLDE':
                            try:
                                sit = _calcul_situation_financiere(inscription)
                                total_du = sit['total_du']
                                total_paye = sit['total_paye']
                                reste = sit['reste_a_payer']

                                response_text = f"Yelen - {eleve.prenom} {eleve.nom} ({inscription.classe.nom}): Du {int(total_du)} FCFA, Paye {int(total_paye)} FCFA, Reste {int(reste)} FCFA."
                                processed_successfully = True
                            except Exception as e:
                                logger.exception("SMS reçu : calcul du solde impossible (inscription %s)", inscription.pk)
                                error_message = f"Erreur calcul solde: {str(e)}"
                                response_text = f"Yelen - Erreur lors de la recuperation du solde de {eleve.prenom} {eleve.nom}."

                        elif command_type == 'ABS':
                            try:
                                total_abs = Presence.objects.filter(inscription=inscription, statut=Presence.StatutChoices.ABSENT).count()
                                abs_justifiees = Presence.objects.filter(inscription=inscription, statut=Presence.StatutChoices.EXCUSE).count()
                                response_text = f"Yelen - {eleve.prenom} {eleve.nom} ({inscription.classe.nom}): {total_abs} absence(s) non justifiee(s), {abs_justifiees} excusee(s) cette annee."
                                processed_successfully = True
                            except Exception as e:
                                logger.exception("SMS reçu : calcul de l'assiduité impossible (inscription %s)", inscription.pk)
                                error_message = f"Erreur assiduite: {str(e)}"
                                response_text = f"Yelen - Erreur lors de la recuperation des absences de {eleve.prenom} {eleve.nom}."
                else:
                    error_message = f"Sender {sender_normalized} not authorized for matricule {matricule}."
                    response_text = "Yelen - Ce numero de telephone n'est pas autorise a consulter les informations de cet eleve."
        else:
            error_message = f"Commande invalide: '{message_text}'"
            response_text = "Yelen - Commande invalide. Envoyez AIDE pour obtenir la liste des commandes disponibles."

    log = IncomingSMSLog.objects.create(
        sender_number=sender_number,
        message_text=message_text,
        message_id=message_id,
        command_type=command_type,
        eleve=eleve,
        response_text=response_text[:160],
        is_authorized=is_authorized,
        processed_successfully=processed_successfully,
        error_message=error_message,
    )

    if response_text:
        envoyer_sms_async(sender_number, response_text[:160])
    return log, True


# ── Relève de la boîte de réception du téléphone passerelle ──────────────────────────────────────────────────

def _lire_boite_reception(limite):
    """Derniers SMS reçus par le téléphone (plus récents d'abord) via l'API locale de l'app SMS Gateway."""
    from core.sms import adresse_passerelle, get_sms_val, requete_passerelle
    base = adresse_passerelle()
    if not base:
        return None, ("La réception des SMS n'est possible qu'avec la passerelle WiFi (app Android SMS Gateway)."
                      if str(get_sms_val('SMS_BACKEND')).lower() != 'http'
                      else "Renseignez d'abord l'URL de la passerelle (SMS_HTTP_URL).")
    try:
        with requete_passerelle('GET', f'{base}/inbox?type=SMS&limit={int(limite)}', timeout=10) as reponse:
            messages = json.loads(reponse.read().decode('utf-8') or '[]')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "Boîte de réception indisponible : mettre à jour l'app SMS Gateway (version 1.59 ou plus récente)."
        return None, f"HTTP {e.code} : {e.read().decode('utf-8', 'replace')[:200]}"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, f"Impossible de joindre la passerelle SMS ({base}) : {getattr(e, 'reason', e)}"
    if not isinstance(messages, list):
        return None, "Réponse inattendue de la passerelle SMS."
    return messages, ''


def relever_boite_reception(limite=30):
    """Relève les SMS reçus par le téléphone depuis la dernière relève et les traite comme s'ils étaient arrivés par
    le webhook. La première relève ne fait que poser le repère : les SMS déjà présents ne reçoivent pas de réponse
    tardive. Retourne le bilan {'ok', 'motif', 'nouveaux', 'ignores'} (aussi mémorisé pour Configuration SMS)."""
    from core.sms import sms_actifs

    bilan = {'ok': False, 'motif': '', 'nouveaux': 0, 'ignores': 0, 'quand': timezone.now().isoformat()}
    if not sms_actifs():
        bilan['motif'] = "SMS désactivés (Paramètres → Configuration SMS)."
    else:
        messages, motif = _lire_boite_reception(limite)
        if messages is None:
            bilan['motif'] = motif
        else:
            bilan.update(_traiter_releve(messages), ok=True)
    cache.set(CLE_ETAT_RELEVE, bilan, DUREE_CACHE_RELEVE)
    return bilan


def _traiter_releve(messages):
    repere = cache.get(CLE_REPERE_RELEVE)
    recus = sorted((m for m in messages if isinstance(m, dict) and m.get('createdAt')), key=lambda m: m['createdAt'])
    if repere is None:
        # Première relève : les SMS déjà dans le téléphone sont antérieurs à la mise en service.
        if recus:
            cache.set(CLE_REPERE_RELEVE, recus[-1]['createdAt'], DUREE_CACHE_RELEVE)
        return {'nouveaux': 0, 'ignores': len(recus)}
    nouveaux = ignores = 0
    for m in recus:
        if m['createdAt'] <= repere:
            continue
        expediteur = str(m.get('sender') or '').strip()
        texte = str(m.get('contentPreview') or '').strip()
        if expediteur and texte:
            _, cree = traiter_sms_recu(expediteur, texte, identifiant_message(m.get('id')))
            nouveaux += cree
            ignores += not cree
        cache.set(CLE_REPERE_RELEVE, m['createdAt'], DUREE_CACHE_RELEVE)
    return {'nouveaux': nouveaux, 'ignores': ignores}


def etat_releve():
    """Dernier bilan de relève mémorisé, ou None si aucune relève n'a encore eu lieu."""
    return cache.get(CLE_ETAT_RELEVE)
