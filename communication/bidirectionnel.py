"""Communication bidirectionnelle par SMS : texte du SMS envoyé au parent pour un ``MessageParent`` et
enregistrement de sa réponse reçue par SMS (``ReponseParent``).

Le serveur de l'école n'étant en général pas joignable depuis l'extérieur (adresse du réseau local), le parent
ne peut pas ouvrir le lien /repondre/ : le message lui est envoyé en clair dans le SMS, et il répond en
répondant au SMS. Le lien reste disponible sur la fiche du message pour les établissements qui en ont l'usage."""
import re
from datetime import date, timedelta

from django.utils import timezone

from core.sms import _normaliser_numero

from .models import MessageParent, ReponseParent

LONGUEUR_SMS = 160
ACCUSE_RECEPTION = "Yelen - Reponse bien recue, merci. L'ecole en est informee."
DELAI_REPONSE = timedelta(days=30)
_DATE = re.compile(r'(?<!\d)(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2}|\d{4}))?(?!\d)')


def instruction(msg):
    """Consigne de réponse ajoutée au SMS selon le type de message."""
    if msg.type == MessageParent.TYPE_CONVOCATION and msg.creneaux_proposes:
        choix = ' '.join(f"{i}) {c}" for i, c in enumerate(msg.creneaux_proposes, 1))
        return f"Repondez {', '.join(str(i) for i in range(1, len(msg.creneaux_proposes) + 1))}: {choix}"
    return {
        MessageParent.TYPE_CONVOCATION: "Repondez a ce SMS pour confirmer.",
        MessageParent.TYPE_AVERTISSEMENT: "Repondez OK pour accuser reception.",
        MessageParent.TYPE_JUSTIFICATIF: "Repondez a ce SMS avec le motif de l'absence.",
        MessageParent.TYPE_RELANCE: "Repondez avec la date de reglement prevue (ex: 15/11).",
    }.get(msg.type, "Repondez a ce SMS.")


def texte_sms(msg, sigle=''):
    """SMS envoyé au parent : sigle, objet, contenu et consigne de réponse (sans lien)."""
    entete = f"{sigle} - " if sigle else ''
    return f"{entete}{msg.objet}. {msg.contenu} {instruction(msg)}".strip()


def _numeros(*valeurs):
    numeros = set()
    for valeur in valeurs:
        if valeur and str(valeur).strip():
            try:
                numeros.add(_normaliser_numero(str(valeur)))
            except (AttributeError, TypeError, ValueError):
                continue
    return numeros


def message_en_attente(sender_normalized):
    """Dernier message envoyé par SMS à ce numéro depuis moins de 30 jours (numéro utilisé pour l'envoi ou
    numéro du parent / tuteur / urgence de la fiche élève) : c'est à lui que répond un SMS libre du parent."""
    candidats = (MessageParent.objects.filter(sms_envoye=True, created_at__gte=timezone.now() - DELAI_REPONSE)
                 .select_related('eleve').order_by('-created_at')[:200])
    for msg in candidats:
        eleve = msg.eleve
        if sender_normalized in _numeros(msg.telephone_utilise, eleve.telephone_parent, eleve.tuteur_telephone,
                                         eleve.telephone_urgence):
            return msg
    return None


def _date_reglement(texte):
    m = _DATE.search(texte)
    if not m:
        return None
    jour, mois, annee = int(m.group(1)), int(m.group(2)), m.group(3)
    aujourd_hui = timezone.localdate()
    annee = int(annee) + (2000 if annee and len(annee) == 2 else 0) if annee else aujourd_hui.year
    try:
        prevue = date(annee, mois, jour)
    except ValueError:
        return None
    if not m.group(3) and prevue < aujourd_hui:   # « 15/01 » envoyé en novembre : janvier prochain
        prevue = prevue.replace(year=annee + 1)
    return prevue


def _creneau_choisi(texte, creneaux):
    nombres = re.findall(r'\d+', texte)
    if len(nombres) == 1 and 1 <= int(nombres[0]) <= len(creneaux):   # « 2 », « je prends le 2 »
        return creneaux[int(nombres[0]) - 1]
    if len(texte) >= 4:                                                 # « lundi 12 mai » ⊂ « Lundi 12 mai à 10h00 »
        return next((c for c in creneaux if texte.upper() in c.upper()), None)
    return None


def enregistrer_reponse(msg, texte):
    """Crée (ou complète) la réponse du parent à partir du SMS reçu, selon le type du message : numéro ou
    libellé du créneau pour une convocation, accusé de réception pour un avertissement (toute réponse vaut
    réception), date pour une relance ; le texte intégral est conservé en commentaire. Le message passe à
    « Répondu »."""
    texte = ' '.join((texte or '').split())
    reponse = getattr(msg, 'reponse', None) or ReponseParent(message=msg)

    if msg.type == MessageParent.TYPE_CONVOCATION and msg.creneaux_proposes:
        choix = _creneau_choisi(texte, msg.creneaux_proposes)
        if choix:
            reponse.creneau_choisi = choix[:200]
    elif msg.type == MessageParent.TYPE_AVERTISSEMENT:
        reponse.accuse_reception = True
    elif msg.type == MessageParent.TYPE_RELANCE:
        prevue = _date_reglement(texte)
        if prevue:
            reponse.date_reglement_prevue = prevue

    horodatage = timezone.localtime().strftime('%d/%m %H:%M')
    ligne = f"[SMS {horodatage}] {texte}"
    reponse.commentaire = f"{reponse.commentaire}\n{ligne}".strip() if reponse.commentaire else ligne
    reponse.save()
    if msg.statut != MessageParent.STATUT_REPONDU:
        msg.statut = MessageParent.STATUT_REPONDU
        msg.save(update_fields=['statut'])
    return reponse
