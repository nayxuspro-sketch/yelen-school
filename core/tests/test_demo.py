"""Jeu de démonstration (5.41.0) : un établissement complet en une commande, rejouable et réinitialisable."""
import pytest
from django.core.management import call_command

from core.demarrage import avancement, etapes
from etablissements.models import Etablissement
from finances.models import Paiement
from inscriptions.models import Eleve, Inscription
from parametres.models import (
    AnneeScolaire, Classe, IdentiteEtablissement, RubriquePaiement, SignataireDocument, TarifScolarite,
)
from pedagogie.models import Evaluation, Matiere, MoyenneGenerale, Note

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def hachage_rapide(settings):
    """La commande crée dix comptes : le hachage PBKDF2 réel coûterait plusieurs secondes par test."""
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


def charger(eleves=8):
    call_command('charger_demo', '--eleves', str(eleves), verbosity=0)
    return Etablissement.objects.get(code='DEMO')


def test_etablissement_complet_en_une_commande():
    etab = charger()
    courante = AnneeScolaire.objects.get(etablissement=etab, est_courante=True)
    assert Eleve.objects.count() == 8 and Inscription.objects.filter(annee_scolaire=courante).count() == 8
    assert Inscription.objects.exclude(annee_scolaire=courante).count() == 8      # année précédente : historique
    assert Classe.objects.filter(etablissement=etab).count() == 8
    assert RubriquePaiement.objects.filter(etablissement=etab).count() == 4
    assert TarifScolarite.objects.filter(etablissement=etab).count() > 20
    identite = IdentiteEtablissement.objects.get(etablissement=etab)
    assert (identite.categorie_reglementaire, identite.zone_implantation) == (2, 1)
    assert SignataireDocument.objects.filter(cycle__etablissement=etab).count() == 9
    assert Note.objects.filter(inscription__annee_scolaire=courante).exists()
    assert Evaluation.objects.filter(trimestre__annee_scolaire=courante).exists()
    assert MoyenneGenerale.objects.filter(inscription__annee_scolaire=courante, moyenne__isnull=False).count() == 8
    assert Paiement.objects.filter(inscription__annee_scolaire=courante).count() >= 8
    assert Matiere.objects.count() >= 10


def test_les_tarifs_respectent_les_plafonds():
    from parametres.plafonds import conformite
    etab = charger()
    courante = AnneeScolaire.objects.get(etablissement=etab, est_courante=True)
    controle = conformite(etab, courante)
    assert controle['classe_connue'] and controle['tout_conforme']


def test_assistant_de_demarrage_complet():
    etab = charger()
    liste = etapes(etab)
    assert {e['cle']: e['fait'] for e in liste} == dict.fromkeys({e['cle'] for e in liste}, True)
    assert avancement(liste)['termine']


def test_commande_rejouable_sans_doublon():
    etab = charger()
    comptes = (Eleve.objects.count(), Inscription.objects.count(), Note.objects.count(), Paiement.objects.count())
    call_command('charger_demo', '--eleves', '8', verbosity=0)
    assert (Eleve.objects.count(), Inscription.objects.count(), Note.objects.count(),
            Paiement.objects.count()) == comptes
    assert IdentiteEtablissement.objects.filter(etablissement=etab).count() == 1


def test_reset_recree_l_etablissement():
    etab = charger()
    ancienne_identite = IdentiteEtablissement.objects.get(etablissement=etab).pk
    call_command('charger_demo', '--eleves', '8', '--reset', verbosity=0)
    nouveau = Etablissement.objects.get(code='DEMO')
    assert nouveau.pk != etab.pk                                    # établissement recréé, pas complété
    assert IdentiteEtablissement.objects.get(etablissement=nouveau).pk != ancienne_identite
    assert Eleve.objects.count() == 8 and not Etablissement.objects.filter(code='DEMO').count() > 1


def test_refuse_moins_d_eleves_que_de_classes():
    with pytest.raises(SystemExit):
        call_command('charger_demo', '--eleves', '3', verbosity=0)
