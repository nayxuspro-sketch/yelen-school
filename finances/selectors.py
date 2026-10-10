"""
Requêtes de lecture partagées du module financier (aucune écriture).

Centralise la définition d'« inscription payable » afin que le formulaire
d'encaissement, la recherche HTMX et les contrôles de présélection parlent
tous de la même population d'élèves.
"""
from django.core.exceptions import ValidationError
from django.db.models import Q

from inscriptions.models import Inscription
from parametres.models import AnneeScolaire

# Nombre maximal d'élèves renvoyés par la recherche serveur du formulaire
# de paiement (la liste complète — 2 500 élèves — n'est plus jamais envoyée).
RESULTATS_RECHERCHE_MAX = 20
# Longueur minimale (hors espaces) avant d'interroger la base.
LONGUEUR_MIN_RECHERCHE = 2
# Nombre maximal de mots pris en compte dans une recherche.
MOTS_RECHERCHE_MAX = 5


def annee_de_reference(etab):
    """Année courante de l'établissement, sinon la plus récente, sinon None."""
    if etab is None:
        return None
    return (
        AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
        or AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut').first()
    )


def inscriptions_payables(etab, annee):
    """Inscriptions pouvant recevoir un encaissement (ni exonérées, ni abandonnées)."""
    if etab is None or annee is None:
        return Inscription.objects.none()
    return (
        Inscription.objects
        .select_related('eleve', 'classe', 'annee_scolaire', 'statut_eleve')
        .filter(annee_scolaire=annee, classe__etablissement=etab)
        .exclude(est_exonere=True)
        .exclude(statut='ABANDON')
        .order_by('eleve__nom', 'eleve__prenom')
    )


def terme_recherche_valide(terme):
    """Vrai si le terme saisi est assez long pour lancer une recherche."""
    return len((terme or '').replace(' ', '')) >= LONGUEUR_MIN_RECHERCHE


def rechercher_inscriptions_payables(etab, annee, terme, limite=RESULTATS_RECHERCHE_MAX):
    """
    Recherche multi-mots : chaque mot doit apparaître dans le nom, le prénom,
    le matricule ou la classe (« traore 6e » → les TRAORE de 6e).
    """
    if not terme_recherche_valide(terme):
        return Inscription.objects.none()
    queryset = inscriptions_payables(etab, annee)
    for mot in terme.split()[:MOTS_RECHERCHE_MAX]:
        queryset = queryset.filter(
            Q(eleve__nom__icontains=mot)
            | Q(eleve__prenom__icontains=mot)
            | Q(eleve__matricule__icontains=mot)
            | Q(classe__nom__icontains=mot)
        )
    return queryset[:limite]


def inscription_payable_ou_none(etab, annee, pk):
    """Inscription présélectionnée (lien « Encaisser ») si elle est payable, sinon None."""
    if not pk:
        return None
    try:
        return inscriptions_payables(etab, annee).get(pk=pk)
    except (Inscription.DoesNotExist, ValueError, ValidationError):
        return None
