# licences/services.py
# ================================================================
# Services de contrôle des licences — logique métier hors middlewares/vues.
#
# Fournit le calcul des usages réels de l'établissement (élèves,
# enseignants, classes) comparés aux plafonds du niveau de licence.
# Portable PostgreSQL / SQLite (aucune fonctionnalité spécifique moteur).
from __future__ import annotations



def _annee_courante(etablissement):
    """Année scolaire courante de l'établissement (ou None)."""
    from parametres.models import AnneeScolaire
    return (
        AnneeScolaire.objects
        .filter(etablissement=etablissement, est_courante=True)
        .first()
    )


def compter_eleves(etablissement) -> int:
    """Nombre d'élèves distincts inscrits dans l'année scolaire courante
    (tous statuts sauf ABANDON)."""
    from inscriptions.models import Inscription

    annee = _annee_courante(etablissement)
    if annee is None:
        return 0
    return (
        Inscription.objects
        .filter(classe__etablissement=etablissement, annee_scolaire=annee)
        .exclude(statut='ABANDON')
        .values('eleve_id')
        .distinct()
        .count()
    )


def compter_enseignants(etablissement) -> int:
    """Nombre d'enseignants distincts actifs dans l'année scolaire courante
    (inscription du personnel validée, poste de catégorie Enseignement)."""
    from personnel.models import InscriptionPersonnel

    annee = _annee_courante(etablissement)
    if annee is None:
        return 0
    return (
        InscriptionPersonnel.objects
        .filter(
            cycle__etablissement=etablissement,
            annee_scolaire=annee,
            est_actif=True,
            is_active=True,
            poste__categorie='ENSEIGNEMENT',
        )
        .values('personnel_id')
        .distinct()
        .count()
    )


def compter_classes(etablissement) -> int:
    """Nombre de classes actives de l'établissement."""
    from parametres.models import Classe
    return Classe.objects.filter(etablissement=etablissement, actif=True).count()


def get_usage_limites(licence) -> dict:
    """
    Compare l'usage réel de l'établissement aux plafonds de sa licence.

    Args:
        licence: instance de licences.Licence

    Returns:
        dict {
            'usage':       {'eleves': int, 'enseignants': int, 'classes': int},
            'limites':     {'max_eleves': int, 'max_enseignants': int,
                            'max_classes': int},
            'depassements': [{'champ': str, 'usage': int, 'max': int,
                              'message': str}, ...],
        }
    """
    from .models import LIMITES_LICENCES

    etab = licence.etablissement
    limites = LIMITES_LICENCES.get(licence.type_licence, {})

    usage = {
        'eleves': compter_eleves(etab),
        'enseignants': compter_enseignants(etab),
        'classes': compter_classes(etab),
    }

    depassements = []
    for champ, max_cle, libelle in (
        ('eleves', 'max_eleves', 'élèves inscrits'),
        ('enseignants', 'max_enseignants', 'enseignants actifs'),
        ('classes', 'max_classes', 'classes actives'),
    ):
        mx = limites.get(max_cle)
        if mx and usage[champ] > mx:
            depassements.append({
                'champ': champ,
                'usage': usage[champ],
                'max': mx,
                'message': (
                    f"Limite de licence dépassée : {usage[champ]} {libelle} "
                    f"pour un maximum de {mx} "
                    f"(licence {licence.get_type_licence_display()})."
                ),
            })

    return {
        'usage': usage,
        'limites': limites,
        'depassements': depassements,
    }


# ── Activation hors ligne par jeton signé (v3) ──────────────────────────────

def activer_jeton(texte: str, etablissement, acteur=None, ip_address=None):
    """
    Active la licence de l'établissement à partir d'un code de licence YELEN3
    émis par l'éditeur : signature Ed25519 vérifiée avec LICENCE_PUBLIC_KEY,
    établissement et serveur contrôlés, puis licence créée ou remplacée.

    Args:
        texte: jeton tel que collé par l'administrateur
        etablissement: établissement de l'utilisateur connecté
        acteur: utilisateur ayant saisi le code (journal d'audit)
        ip_address: adresse IP du client (journal d'audit)

    Returns:
        licences.Licence activée

    Raises:
        licences.jeton.JetonInvalide: code illisible, signature fausse,
            établissement ou serveur différent, licence déjà expirée.
    """
    from datetime import date, datetime

    from django.conf import settings
    from django.db import IntegrityError, transaction
    from django.utils import timezone

    from .binding import empreinte_serveur
    from .jeton import JetonInvalide, charger_cle_publique, normaliser_jeton, verifier_jeton
    from .models import Licence, LicenceAuditLog, StatutLicence, TypeLicence

    payload = verifier_jeton(texte, charger_cle_publique(getattr(settings, 'LICENCE_PUBLIC_KEY', '')))

    if payload['etablissement'] != str(etablissement.pk):
        raise JetonInvalide("Ce code de licence a été émis pour un autre établissement.")
    if payload['type'] not in TypeLicence.values:
        raise JetonInvalide("Type de licence inconnu.")
    try:
        expiration = date.fromisoformat(payload['date_expiration'])
        activation = datetime.fromisoformat(payload['date_activation'])
    except (TypeError, ValueError) as exc:
        raise JetonInvalide("Dates du code de licence invalides.") from exc
    if timezone.is_naive(activation):
        activation = timezone.make_aware(activation, timezone.get_default_timezone())
    if expiration < timezone.now().date():
        raise JetonInvalide(
            f"Ce code de licence est déjà expiré (le {expiration.strftime('%d/%m/%Y')})."
        )
    attendue = payload['empreinte_serveur']
    if attendue and attendue != empreinte_serveur():
        raise JetonInvalide("Ce code de licence a été émis pour un autre serveur.")

    try:
        with transaction.atomic():
            licence = Licence.objects.filter(etablissement=etablissement).first()
            if licence is None:
                licence = Licence(etablissement=etablissement)
            licence.cle_licence = payload['cle']
            licence.type_licence = payload['type']
            licence.date_expiration = expiration
            licence.date_activation = activation
            licence.statut = StatutLicence.ACTIVE
            licence.jeton_signe = normaliser_jeton(texte)
            licence.empreinte_serveur = attendue
            licence.signature_ed25519 = ''
            licence.save()
    except IntegrityError as exc:
        raise JetonInvalide("Cette clé de licence est déjà utilisée par un autre établissement.") from exc

    LicenceAuditLog.objects.create(
        licence=licence,
        action='ACTIVATION',
        description=(
            f"Activation par code de licence signé — {licence.type_licence}, "
            f"expire le {expiration.strftime('%d/%m/%Y')}, "
            f"serveur {attendue[:16] + '…' if attendue else 'non lié'}"
        ),
        acteur_user=acteur if (acteur is not None and acteur.is_authenticated) else None,
        acteur_systeme=acteur is None,
        ip_address=ip_address,
    )
    return licence
