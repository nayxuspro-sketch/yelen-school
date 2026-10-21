"""Demandes de paiement Mobile Money : confirmation et paiement en ligne (CinetPay).

Circuit connecté : la demande reçoit un lien de paiement CinetPay (Orange Money / Moov Money)
envoyé par SMS. Le serveur de l'école n'étant pas joignable depuis Internet, aucune
notification n'est attendue : YELEN interroge lui-même l'API de contrôle (bouton
« Vérifier », commande ``verifier_paiements_mobiles``) et confirme la demande.
"""
import json
import re
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from .models import CanalRelance, DemandePaiementMobile, HistoriqueRelance, ModePaiement, Paiement

EN_ATTENTE = DemandePaiementMobile.StatutChoices.EN_ATTENTE
CONFIRME = DemandePaiementMobile.StatutChoices.CONFIRME
ANNULE = DemandePaiementMobile.StatutChoices.ANNULE
_CODES_REFUS = ('600', '627')      # PAYMENT_FAILED, TRANSACTION_CANCEL


class ErreurPasserelle(Exception):
    """Réponse ou réseau invalide côté CinetPay (message lisible pour l'utilisateur)."""


# ── Confirmation (guichet, passerelle) ──────────────────────────────────────

def confirmer_demande(demande, utilisateur, reference, raison):
    """Crée le paiement d'une demande en attente et la passe à Confirmé (appelant sous verrou)."""
    paiement = Paiement(
        inscription=demande.inscription, rubrique=demande.rubrique, montant=demande.montant,
        mode_paiement=ModePaiement.MOBILE_MONEY, reference=(reference or demande.reference)[:100],
        encaisse_par=utilisateur, statut_eleve=demande.inscription.statut_eleve,
    )
    paiement._audit_reason = raison
    paiement.save()
    demande._audit_reason = raison
    demande.statut, demande.paiement = CONFIRME, paiement
    demande.confirme_le, demande.confirme_par, demande.updated_by = timezone.now(), utilisateur, utilisateur
    demande.save(update_fields=['statut', 'confirme_le', 'confirme_par', 'paiement', 'updated_by', 'updated_at'])
    return paiement


# ── CinetPay ────────────────────────────────────────────────────────────────

def cinetpay_configure():
    return bool(settings.CINETPAY_API_KEY and settings.CINETPAY_SITE_ID and settings.CINETPAY_URL_PUBLIQUE)


def _appeler(chemin, donnees):
    """POST JSON vers l'API CinetPay ; renvoie la réponse décodée (codes métier inclus, même en HTTP 4xx)."""
    corps = json.dumps({'apikey': settings.CINETPAY_API_KEY, 'site_id': settings.CINETPAY_SITE_ID, **donnees}).encode()
    requete = urllib.request.Request(
        f"{settings.CINETPAY_URL_API}{chemin}", data=corps, method='POST',
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(requete, timeout=settings.CINETPAY_TIMEOUT) as reponse:
            return json.loads(reponse.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode('utf-8'))
        except ValueError:
            raise ErreurPasserelle(f"réponse HTTP {exc.code} de la passerelle") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise ErreurPasserelle(f"passerelle injoignable ({getattr(exc, 'reason', None) or exc})") from exc


def _sans_accents(texte):
    return unicodedata.normalize('NFKD', texte).encode('ascii', 'ignore').decode()


def montant_eligible(montant):
    """CinetPay n'accepte qu'un montant entier, multiple de 5, de 100 FCFA au moins."""
    return montant == int(montant) and int(montant) >= 100 and int(montant) % 5 == 0


def creer_lien(demande):
    """Crée le lien de paiement CinetPay (Mobile Money, XOF) de la demande et l'enregistre."""
    if not montant_eligible(demande.montant):
        raise ErreurPasserelle("le montant doit être un multiple de 5 d'au moins 100 FCFA")
    montant = int(demande.montant)
    eleve = demande.inscription.eleve
    rubrique = demande.rubrique.nom if demande.rubrique else 'Scolarite'
    reponse = _appeler('/payment', {
        'transaction_id': demande.reference, 'amount': montant, 'currency': 'XOF',
        'description': re.sub(r'[#/$_&]', ' ', _sans_accents(f"{rubrique} {eleve.nom} {eleve.prenom} {demande.reference}"))[:100],
        'channels': 'MOBILE_MONEY', 'lang': 'fr', 'metadata': str(demande.pk),
        'notify_url': settings.CINETPAY_URL_PUBLIQUE, 'return_url': settings.CINETPAY_URL_PUBLIQUE,
        'customer_name': _sans_accents(eleve.nom)[:50], 'customer_surname': _sans_accents(eleve.prenom)[:50],
        'invoice_data': {'Eleve': _sans_accents(f"{eleve.nom} {eleve.prenom}")[:50],
                         'Matricule': eleve.matricule, 'Rubrique': _sans_accents(rubrique)[:50]},
    })
    donnees = reponse.get('data') or {}
    if str(reponse.get('code')) != '201' or not donnees.get('payment_url'):
        raise ErreurPasserelle(
            f"{reponse.get('code', '')} {reponse.get('message', '')} {reponse.get('description', '')}".strip()
        )
    demande.lien_paiement = str(donnees['payment_url'])[:300]
    demande.jeton_paiement = str(donnees.get('payment_token', ''))[:200]
    demande.message_passerelle = 'Lien de paiement créé'
    demande.save(update_fields=['lien_paiement', 'jeton_paiement', 'message_passerelle', 'updated_at'])
    return demande.lien_paiement


def _montant(valeur):
    try:
        return Decimal(str(valeur))
    except (InvalidOperation, TypeError, ValueError):
        return None


def verifier_paiement(demande, utilisateur=None):
    """Interroge CinetPay et met la demande à jour. Renvoie (état, message) ;
    état ∈ CONFIRME, EN_ATTENTE, REFUSE, ERREUR."""
    try:
        reponse = _appeler('/payment/check', {'transaction_id': demande.reference})
    except ErreurPasserelle as exc:
        return 'ERREUR', str(exc)
    donnees = reponse.get('data') or {}
    code, statut = str(reponse.get('code', '')), str(donnees.get('status', '')).upper()
    libelle = f"{code} {reponse.get('message', '')}".strip()
    with transaction.atomic():
        demande = (
            DemandePaiementMobile.objects.select_for_update(of=('self',))
            .select_related('inscription__eleve', 'inscription__statut_eleve', 'rubrique').get(pk=demande.pk)
        )
        if demande.statut != EN_ATTENTE:
            return ('CONFIRME' if demande.statut == CONFIRME else 'REFUSE'), "Demande déjà traitée."
        demande.verifie_le = timezone.now()
        champs = ['verifie_le', 'message_passerelle', 'updated_at']
        if code == '00' and statut == 'ACCEPTED':
            recu = _montant(donnees.get('amount'))
            if recu is not None and recu != demande.montant:
                demande.message_passerelle = (
                    f"Montant reçu {recu:.0f} FCFA différent de {demande.montant:.0f} FCFA : à traiter manuellement"
                )
                demande.save(update_fields=champs)
                return 'ERREUR', demande.message_passerelle
            demande.message_passerelle = (
                f"Paiement accepté ({donnees.get('payment_method', '')} {donnees.get('payment_date', '')})".strip()[:255]
            )
            demande.save(update_fields=champs)
            paiement = confirmer_demande(
                demande, utilisateur, str(donnees.get('operator_id') or demande.reference),
                "Paiement confirmé par la passerelle CinetPay",
            )
            _sms_recu(demande, paiement)
            return 'CONFIRME', f"Paiement {demande.reference} confirmé, reçu {paiement.numero_recu}."
        if statut == 'REFUSED' or code in _CODES_REFUS:
            demande._audit_reason = "Paiement refusé ou annulé sur la passerelle CinetPay"
            demande.statut = ANNULE
            demande.observations = f"Paiement refusé ou annulé sur la passerelle ({libelle}). Créer une nouvelle demande si besoin."
            demande.message_passerelle = f"Refusé ({libelle})"[:255]
            demande.save(update_fields=champs + ['statut', 'observations'])
            return 'REFUSE', f"Paiement {demande.reference} refusé ou annulé sur la passerelle."
        demande.message_passerelle = f"En attente du paiement ({libelle})"[:255]
        demande.save(update_fields=champs)
        return 'EN_ATTENTE', f"Paiement {demande.reference} toujours en attente ({libelle})."


def verifier_en_attente(etablissement=None, utilisateur=None, limite=50, jours=7):
    """Vérifie les demandes en attente munies d'un lien (créées ou relancées depuis moins de ``jours`` jours).
    Renvoie le décompte par état."""
    if not cinetpay_configure():
        return {}
    depuis = timezone.now() - timedelta(days=jours)
    demandes = DemandePaiementMobile.objects.filter(
        Q(created_at__gte=depuis) | Q(relance_le__gte=depuis), statut=EN_ATTENTE,
    ).exclude(lien_paiement='').order_by('created_at')
    if etablissement is not None:
        demandes = demandes.filter(inscription__classe__etablissement=etablissement)
    compteur = Counter()
    for demande in demandes[:limite]:
        compteur[verifier_paiement(demande, utilisateur)[0]] += 1
    return dict(compteur)


def _sms_recu(demande, paiement):
    try:
        from core.sms import envoyer_sms
        eleve = demande.inscription.eleve
        envoyer_sms(
            demande.telephone,
            f"YELEN SCHOOL - Paiement de {int(paiement.montant)} FCFA recu pour {eleve.nom} {eleve.prenom}. "
            f"Recu {paiement.numero_recu}. Merci.",
        )
    except Exception:
        pass


# ── Relances ───────────────────────────────────────────────────────────────

def demande_pour_relance(inscription, rubrique, montant, telephone, utilisateur):
    """Demande en attente munie d'un lien pour cette créance : réutilisée si récente, sinon créée.
    Renvoie (demande, créée) ; (None, False) si la passerelle n'est pas configurée ou si le montant
    n'est pas éligible ; propage ErreurPasserelle (demande supprimée) si le lien ne peut pas être créé."""
    if not cinetpay_configure() or not montant_eligible(montant):
        return None, False
    demande = DemandePaiementMobile.objects.filter(
        inscription=inscription, rubrique=rubrique, montant=montant, statut=EN_ATTENTE,
        created_at__gte=timezone.now() - timedelta(days=7),
    ).exclude(lien_paiement='').order_by('-created_at').first()
    if demande is not None:
        return demande, False
    demande = DemandePaiementMobile.objects.create(
        inscription=inscription, rubrique=rubrique, montant=montant, telephone=telephone, cree_par=utilisateur,
    )
    try:
        creer_lien(demande)
    except ErreurPasserelle:
        demande.delete()
        raise
    return demande, True


def enregistrer_relance(demande, utilisateur, succes=True, historique=True):
    """Compte la relance sur la demande et, sauf si l'appelant la trace déjà, l'ajoute à l'historique des relances."""
    demande.nb_relances += 1
    demande.relance_le = timezone.now()
    demande.save(update_fields=['nb_relances', 'relance_le', 'updated_at'])
    if historique:
        HistoriqueRelance.objects.create(
            inscription=demande.inscription, rubrique=demande.rubrique, canal=CanalRelance.SMS,
            montant_reclame=demande.montant, envoye_par=utilisateur, date_relance=timezone.localdate(),
            succes=succes, detail=demande.telephone,
        )


def relancer_avec_lien(envois, utilisateur):
    """Envoie les SMS d'une campagne de relance en y ajoutant un lien de paiement (exécuté hors requête).
    ``envois`` : dicts inscription, rubrique, montant, telephone, message. Au premier échec de la
    passerelle, les SMS suivants partent sans lien. Renvoie le nombre de SMS munis d'un lien."""
    from core.sms import envoyer_sms

    avec_lien, passerelle_active = 0, True
    for envoi in envois:
        demande, creee = None, False
        if passerelle_active:
            try:
                demande, creee = demande_pour_relance(envoi['inscription'], envoi['rubrique'], envoi['montant'],
                                                      envoi['telephone'], utilisateur)
            except ErreurPasserelle:
                passerelle_active = False
        if demande is None:
            envoyer_sms(envoi['telephone'], envoi['message'])
            continue
        ok, _ = envoyer_sms(envoi['telephone'], f"{envoi['message']}\nPayer en ligne: {demande.lien_paiement}", limite=320)
        if not creee:
            enregistrer_relance(demande, utilisateur, succes=ok, historique=False)
        elif ok:
            demande.sms_envoye = True
            demande.save(update_fields=['sms_envoye'])
        avec_lien += 1
    return avec_lien
