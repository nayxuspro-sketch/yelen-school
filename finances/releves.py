"""Relevés Mobile Money : lecture du fichier, import, rapprochement automatique, validation.

Circuit hors ligne : les parents paient au numéro marchand de l'école ; le relevé (CSV ou
Excel) téléchargé depuis l'espace marchand est importé ici, puis chaque transaction est
rapprochée d'un paiement YELEN — déjà saisi au guichet, ou créé à la validation.
"""
import logging
import csv
import io
import re
import unicodedata
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from inscriptions.models import Inscription
from .models import DemandePaiementMobile, LigneReleve, ModePaiement, Paiement, ReleveMobileMoney
from .selectors import annee_de_reference, inscriptions_payables

logger = logging.getLogger(__name__)

TAILLE_MAX_FICHIER = 5 * 1024 * 1024
LIGNES_MAX = 10_000
STATUTS_A_TRAITER = (LigneReleve.Statut.PROPOSE, LigneReleve.Statut.A_CONFIRMER, LigneReleve.Statut.NON_IDENTIFIE)
STATUTS_VALIDABLES = (LigneReleve.Statut.PROPOSE, LigneReleve.Statut.A_CONFIRMER)

# En-têtes reconnus (normalisés : minuscules, sans accent ni ponctuation), par ordre de priorité.
_COLONNES = (
    ('numero_transaction', ('idtransaction', 'transactionid', 'idtrans', 'numerotransaction', 'ntransaction',
                            'numtransaction', 'txnid', 'transaction', 'identifiant', 'reference', 'ref', 'id')),
    ('date_operation', ('dateheure', 'datetime', 'dateoperation', 'datetransaction', 'horodatage', 'date')),
    ('montant', ('montantrecu', 'montant', 'amount', 'credit', 'valeur')),
    ('frais', ('frais', 'commission', 'fees', 'fee')),
    ('telephone_payeur', ('telephonepayeur', 'telephoneclient', 'numeroclient', 'msisdn', 'expediteur', 'payeur',
                          'telephone', 'mobile', 'numero', 'compte', 'from', 'tel')),
    ('nom_payeur', ('nompayeur', 'nomclient', 'client', 'nom', 'name')),
    ('motif', ('motif', 'libelle', 'description', 'commentaire', 'narration', 'message', 'objet', 'details', 'note')),
)
_OBLIGATOIRES = ('numero_transaction', 'date_operation', 'montant')
_FORMATS_DATE = (
    '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M', '%d-%m-%Y',
    '%d/%m/%y %H:%M:%S', '%d/%m/%y %H:%M', '%d/%m/%y',
)
_REFERENCE_DEMANDE = re.compile(r'MM-\d{4}-\d+', re.I)
_TOKEN_MATRICULE = re.compile(r'[A-Z0-9]+(?:-[A-Z0-9]+)+', re.I)
MESSAGE_COLONNES = (
    "Colonnes obligatoires introuvables : N° de transaction, Date et Montant. "
    "Exporter le relevé depuis l'espace marchand, ou préparer un fichier avec les en-têtes "
    "« Transaction ; Date ; Montant ; Frais ; Téléphone ; Nom ; Motif »."
)


class FichierInvalide(Exception):
    """Le fichier ne peut pas être lu comme un relevé."""


# ── Lecture du fichier ──────────────────────────────────────────────────────

def _normaliser(texte):
    texte = unicodedata.normalize('NFKD', str(texte or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', texte.lower())


def _detecter_colonnes(entetes):
    """Associe chaque champ à l'indice de sa colonne : égalité d'abord, puis inclusion d'un mot-clé."""
    normalises = [_normaliser(e) for e in entetes]
    colonnes, utilisees = {}, set()
    for champ, mots in _COLONNES:
        for exact in (True, False):
            for mot in mots:
                if not exact and len(mot) < 4:
                    continue
                for i, entete in enumerate(normalises):
                    if i in utilisees or not entete:
                        continue
                    if entete == mot if exact else mot in entete:
                        colonnes[champ] = i
                        utilisees.add(i)
                        break
                if champ in colonnes:
                    break
            if champ in colonnes:
                break
    return colonnes


def _lire_csv(fichier):
    brut = fichier.read()
    texte = None
    for encodage in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            texte = brut.decode(encodage)
            break
        except UnicodeDecodeError:
            continue
    premieres = [l for l in texte.splitlines() if l.strip()][:30]
    separateur = max(';,\t|', key=lambda s: sum(l.count(s) for l in premieres))
    return list(csv.reader(io.StringIO(texte), delimiter=separateur))


def _lire_xlsx(fichier):
    import openpyxl
    try:
        classeur = openpyxl.load_workbook(fichier, read_only=True, data_only=True)
    except Exception as exc:
        raise FichierInvalide("Classeur Excel illisible.") from exc
    try:
        return [list(ligne) for ligne in classeur.worksheets[0].iter_rows(values_only=True)]
    finally:
        classeur.close()


def lire_releve(fichier):
    """Retourne (colonnes détectées, lignes de données) d'un CSV ou d'un classeur Excel (1re feuille)."""
    if fichier.size > TAILLE_MAX_FICHIER:
        raise FichierInvalide("Fichier trop volumineux (5 Mo maximum).")
    nom = (fichier.name or '').lower()
    if nom.endswith(('.xlsx', '.xlsm')):
        lignes = _lire_xlsx(fichier)
    elif nom.endswith(('.csv', '.txt')):
        lignes = _lire_csv(fichier)
    else:
        raise FichierInvalide("Format non pris en charge : fournir un fichier CSV ou Excel (.xlsx).")
    # Les exports marchands commencent souvent par un bloc de titre : la ligne d'en-têtes
    # est la première contenant les trois colonnes obligatoires.
    for i, ligne in enumerate(lignes[:30]):
        colonnes = _detecter_colonnes(ligne)
        if all(champ in colonnes for champ in _OBLIGATOIRES):
            return colonnes, lignes[i + 1:i + 1 + LIGNES_MAX]
    raise FichierInvalide(MESSAGE_COLONNES)


def _texte(valeur, longueur):
    if isinstance(valeur, float) and valeur.is_integer():
        valeur = int(valeur)
    return str(valeur if valeur is not None else '').strip()[:longueur]


def _decimal(valeur):
    """Montant FCFA : « 25 000 », « 25.000 », « 25 000,00 FCFA », 25000.0 → Decimal, sinon None."""
    if valeur is None or valeur == '':
        return None
    if isinstance(valeur, (int, float, Decimal)):
        return Decimal(str(valeur))
    t = re.sub(r'(?i)\s|\u202f|\xa0|fcfa|xof|cfa|\+', '', str(valeur))
    t = re.sub(r'(?i)f$', '', t)
    if ',' in t and '.' in t:
        t = t.replace('.', '').replace(',', '.') if t.rfind(',') > t.rfind('.') else t.replace(',', '')
    elif ',' in t:
        t = t.replace(',', '.') if re.search(r',\d{1,2}$', t) else t.replace(',', '')
    elif t.count('.') > 1 or re.search(r'\.\d{3}$', t):
        t = t.replace('.', '')
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def _date(valeur):
    if isinstance(valeur, datetime):
        dt = valeur
    elif isinstance(valeur, date):
        dt = datetime.combine(valeur, time.min)
    else:
        t = str(valeur or '').strip()
        for fmt in _FORMATS_DATE:
            try:
                dt = datetime.strptime(t, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def _chiffres(valeur):
    return re.sub(r'\D', '', _texte(valeur, 40))


def _cle_telephone(valeur):
    """Huit derniers chiffres d'un numéro (avec ou sans indicatif 226)."""
    chiffres = _chiffres(valeur)
    return chiffres[-8:] if len(chiffres) >= 8 else ''


# ── Rapprochement automatique ───────────────────────────────────────────────

class _Contexte:
    """Données de l'établissement chargées une fois par import."""

    def __init__(self, etablissement):
        self.etablissement = etablissement
        self.payables = inscriptions_payables(etablissement, annee_de_reference(etablissement))
        self.paiements_pris = set()
        self.telephones = {}
        champs = ('eleve__telephone_parent', 'eleve__tuteur_telephone', 'eleve__telephone_urgence')
        for pk, *numeros in self.payables.values_list('pk', *champs):
            for cle in {_cle_telephone(n) for n in numeros if n}:
                if cle:
                    self.telephones.setdefault(cle, set()).add(pk)


def _rapprocher(ligne, ctx):
    """Renseigne statut / méthode / inscription / paiement de la ligne (sans l'enregistrer)."""
    Statut, Methode = LigneReleve.Statut, LigneReleve.Methode

    # 1. Paiement saisi au guichet avec ce n° de transaction (et ce montant) : preuve directe.
    paiement = (
        Paiement.objects.filter(
            mode_paiement=ModePaiement.MOBILE_MONEY, inscription__classe__etablissement=ctx.etablissement,
            reference__iexact=ligne.numero_transaction, montant=ligne.montant, ligne_releve__isnull=True,
        ).exclude(pk__in=ctx.paiements_pris).select_related('inscription').first()
    )
    if paiement is not None:
        ctx.paiements_pris.add(paiement.pk)
        ligne.statut, ligne.methode = Statut.RAPPROCHE, Methode.TRANSACTION
        ligne.paiement, ligne.inscription = paiement, paiement.inscription
        return

    # 2. Référence d'une demande Mobile Money (MM-2026-0012) dans le motif.
    reference = _REFERENCE_DEMANDE.search(ligne.motif)
    if reference:
        demande = (
            DemandePaiementMobile.objects.filter(
                reference__iexact=reference.group(0), inscription__classe__etablissement=ctx.etablissement,
            ).select_related('inscription', 'paiement').first()
        )
        if demande is not None:
            if demande.statut == DemandePaiementMobile.StatutChoices.EN_ATTENTE:
                ligne.statut, ligne.methode, ligne.inscription = Statut.PROPOSE, Methode.DEMANDE, demande.inscription
                return
            if (demande.paiement_id and demande.paiement.montant == ligne.montant
                    and demande.paiement_id not in ctx.paiements_pris
                    and not LigneReleve.objects.filter(paiement_id=demande.paiement_id).exists()):
                ctx.paiements_pris.add(demande.paiement_id)
                ligne.statut, ligne.methode = Statut.RAPPROCHE, Methode.DEMANDE
                ligne.paiement, ligne.inscription = demande.paiement, demande.inscription
                return

    # 3. Matricule présent dans le motif.
    for jeton in _TOKEN_MATRICULE.findall(ligne.motif):
        inscription = ctx.payables.filter(eleve__matricule__iexact=jeton).first()
        if inscription is not None:
            ligne.statut, ligne.methode, ligne.inscription = Statut.PROPOSE, Methode.MATRICULE, inscription
            return

    # 4. Téléphone du payeur = téléphone d'un (seul) tuteur, montant compatible avec le reste dû.
    candidats = ctx.telephones.get(_cle_telephone(ligne.telephone_payeur), ())
    if len(candidats) == 1:
        from .views.commun import _calcul_situation_financiere
        inscription = ctx.payables.get(pk=next(iter(candidats)))
        if _calcul_situation_financiere(inscription)['reste_a_payer'] >= ligne.montant:
            ligne.statut, ligne.methode, ligne.inscription = Statut.A_CONFIRMER, Methode.TELEPHONE, inscription
            return

    ligne.statut, ligne.methode, ligne.inscription = Statut.NON_IDENTIFIE, '', None


# ── Import ──────────────────────────────────────────────────────────────────

@transaction.atomic
def importer_releve(etablissement, operateur, fichier, utilisateur, rubrique=None):
    """Crée le relevé et ses lignes (sans doublon de transaction), rapprochées automatiquement."""
    colonnes, brutes = lire_releve(fichier)

    def cellule(ligne, champ):
        i = colonnes.get(champ)
        return ligne[i] if i is not None and i < len(ligne) else None

    releve = ReleveMobileMoney(
        etablissement=etablissement, operateur=operateur, nom_fichier=_texte(fichier.name, 255),
        rubrique=rubrique, importe_par=utilisateur, created_by=utilisateur,
    )
    numeros = {_texte(cellule(l, 'numero_transaction'), 64) for l in brutes}
    deja = set(
        LigneReleve.objects.filter(operateur=operateur, numero_transaction__in=numeros)
        .values_list('numero_transaction', flat=True)
    )
    ctx = _Contexte(etablissement)
    nouvelles, vus = [], set()
    for brute in brutes:
        if not any(_texte(c, 1) for c in brute):
            continue
        releve.nb_lignes_fichier += 1
        numero = _texte(cellule(brute, 'numero_transaction'), 64)
        montant, date_operation = _decimal(cellule(brute, 'montant')), _date(cellule(brute, 'date_operation'))
        if not numero or montant is None or montant <= 0 or date_operation is None:
            releve.nb_rejets += 1          # débits, annulations, lignes de total ou illisibles
            continue
        if numero in deja or numero in vus:
            releve.nb_doublons += 1
            continue
        vus.add(numero)
        ligne = LigneReleve(
            releve=releve, operateur=operateur, numero_transaction=numero, date_operation=date_operation,
            montant=montant, frais=abs(_decimal(cellule(brute, 'frais')) or Decimal('0')),
            telephone_payeur=_texte(cellule(brute, 'telephone_payeur'), 20),
            nom_payeur=_texte(cellule(brute, 'nom_payeur'), 120), motif=_texte(cellule(brute, 'motif'), 255),
            created_by=utilisateur,
        )
        _rapprocher(ligne, ctx)
        nouvelles.append(ligne)
    releve.save()
    LigneReleve.objects.bulk_create(nouvelles)
    return releve


# ── Traitement des lignes ───────────────────────────────────────────────────

def valider_lignes(releve, identifiants, utilisateur):
    """Crée un paiement Mobile Money pour chaque ligne proposée / à confirmer sélectionnée.

    Retourne (nombre de paiements créés, messages d'erreur)."""
    from .views.commun import _payment_overage_errors
    Statut = LigneReleve.Statut
    crees, erreurs = 0, []
    selection = releve.lignes.filter(pk__in=identifiants, statut__in=STATUTS_VALIDABLES, inscription__isnull=False)
    for pk in list(selection.values_list('pk', flat=True)):
        with transaction.atomic():
            ligne = LigneReleve.objects.select_for_update().get(pk=pk)
            if ligne.statut not in STATUTS_VALIDABLES or ligne.inscription_id is None:
                continue
            inscription = (
                Inscription.objects.select_for_update(of=('self',))
                .select_related('classe', 'statut_eleve', 'eleve').get(pk=ligne.inscription_id)
            )
            demande, rubrique = None, releve.rubrique
            if ligne.methode == LigneReleve.Methode.DEMANDE:
                reference = _REFERENCE_DEMANDE.search(ligne.motif)
                demande = DemandePaiementMobile.objects.select_for_update().filter(
                    reference__iexact=reference.group(0) if reference else '', inscription=inscription,
                    statut=DemandePaiementMobile.StatutChoices.EN_ATTENTE,
                ).first()
                if demande is not None and demande.rubrique_id:
                    rubrique = demande.rubrique
            if rubrique is not None:
                depassement = _payment_overage_errors(inscription, [(rubrique, ligne.montant, None)])
                if depassement:
                    erreurs.append(f"{ligne.numero_transaction} ({inscription.eleve}) : {' '.join(depassement)}")
                    continue
            paiement = Paiement(
                inscription=inscription, rubrique=rubrique, montant=ligne.montant,
                date_paiement=timezone.localtime(ligne.date_operation).date(),
                mode_paiement=ModePaiement.MOBILE_MONEY, reference=ligne.numero_transaction,
                observation=f"Relevé {releve.get_operateur_display()} importé le {releve.created_at:%d/%m/%Y}",
                encaisse_par=utilisateur, statut_eleve=inscription.statut_eleve,
            )
            paiement._audit_reason = "Rapprochement d'un relevé Mobile Money"
            paiement.save()
            if demande is not None:
                demande._audit_reason = "Paiement confirmé par le relevé Mobile Money"
                demande.statut = DemandePaiementMobile.StatutChoices.CONFIRME
                demande.confirme_le, demande.confirme_par, demande.paiement = timezone.now(), utilisateur, paiement
                demande.updated_by = utilisateur
                demande.save(update_fields=['statut', 'confirme_le', 'confirme_par', 'paiement', 'updated_by', 'updated_at'])
            ligne.paiement, ligne.statut, ligne.updated_by = paiement, Statut.RAPPROCHE, utilisateur
            ligne.save(update_fields=['paiement', 'statut', 'updated_by', 'updated_at'])
            crees += 1
            _sms_confirmation(ligne, paiement)
    return crees, erreurs


def affecter_ligne(ligne, matricule, utilisateur):
    """Affecte manuellement la ligne à l'élève de ce matricule (inscription payable de l'année)."""
    if ligne.statut == LigneReleve.Statut.RAPPROCHE:
        return False, "Cette transaction est déjà rapprochée."
    etablissement = ligne.releve.etablissement
    inscription = (
        inscriptions_payables(etablissement, annee_de_reference(etablissement))
        .filter(eleve__matricule__iexact=(matricule or '').strip()).first()
    )
    if inscription is None:
        return False, f"Aucun élève inscrit cette année avec le matricule « {matricule} »."
    ligne.inscription, ligne.statut, ligne.methode = inscription, LigneReleve.Statut.PROPOSE, LigneReleve.Methode.MANUEL
    ligne.motif_ignore, ligne.updated_by = '', utilisateur
    ligne.save(update_fields=['inscription', 'statut', 'methode', 'motif_ignore', 'updated_by', 'updated_at'])
    return True, f"Transaction {ligne.numero_transaction} affectée à {inscription.eleve} — à valider."


def ignorer_ligne(ligne, motif, utilisateur):
    """Exclut la ligne du rapprochement (hors frais de scolarité, erreur, remboursement…)."""
    if ligne.statut == LigneReleve.Statut.RAPPROCHE:
        return False, "Cette transaction est déjà rapprochée."
    if not (motif or '').strip():
        return False, "Le motif d'exclusion est obligatoire."
    ligne.statut, ligne.methode, ligne.inscription = LigneReleve.Statut.IGNORE, '', None
    ligne.motif_ignore, ligne.updated_by = motif.strip()[:255], utilisateur
    ligne.save(update_fields=['statut', 'methode', 'inscription', 'motif_ignore', 'updated_by', 'updated_at'])
    return True, f"Transaction {ligne.numero_transaction} exclue du rapprochement."


def _sms_confirmation(ligne, paiement):
    """SMS de reçu au payeur (sans effet si la passerelle est désactivée ou le numéro absent)."""
    if not ligne.telephone_payeur:
        return
    try:
        from core.sms import envoyer_sms
        eleve = paiement.inscription.eleve
        envoyer_sms(
            ligne.telephone_payeur,
            f"YELEN SCHOOL - Paiement de {int(paiement.montant)} FCFA recu pour {eleve.nom} {eleve.prenom} "
            f"({ligne.get_operateur_display()} {ligne.numero_transaction}). Recu {paiement.numero_recu}.",
        )
    except Exception:
        logger.exception("SMS de confirmation non envoyé (paiement %s)", paiement.pk)
