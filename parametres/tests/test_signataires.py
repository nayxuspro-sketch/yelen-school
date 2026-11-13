"""Résolution du signataire d'un document : repli par catégorie et reprise des configurations existantes
sur les types ajoutés au catalogue (migration 0036)."""
import datetime
from importlib import import_module

import pytest
from django.apps import apps
from model_bakery import baker

from parametres.models import SignataireDocument, TypeDocument

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexte():
    etab = baker.make('etablissements.Etablissement', code='SIG', nom='Ets Signataires')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire', ordre=1, actif=True)
    return {'etab': etab, 'annee': annee, 'cycle': cycle}


def _signataire(contexte, code, nom, fonction):
    membre = baker.make('personnel.MembrePersonnel', etablissement=contexte['etab'], nom=nom, prenom='Salimata')
    return baker.make('parametres.SignataireDocument', cycle=contexte['cycle'], annee_scolaire=contexte['annee'],
                      type_document=TypeDocument.objects.get(code=code), membre_personnel_id=membre.id,
                      fonction=fonction, actif=True)


def test_repli_sur_le_signataire_de_la_meme_categorie(contexte):
    """Type jamais configuré (ex. contrat de travail) : son document reprend le signataire de sa catégorie
    (Personnel), pas le signataire Finance pourtant plus récent."""
    _signataire(contexte, 'LISTE_PERSONNEL', 'KABORE', 'Le Directeur')
    _signataire(contexte, 'LISTE_REDEVABLES', 'ZONGO', "L'Intendante")

    sig = SignataireDocument.objects.get_signataire(
        cycle=contexte['cycle'], type_document=TypeDocument.objects.get(code='CONTRAT_TRAVAIL'),
        annee_scolaire=contexte['annee'],
    )
    assert sig.fonction == 'Le Directeur' and sig.get_membre_personnel().nom == 'KABORE'


def test_migration_0036_reprend_les_signataires_configures_par_categorie(contexte):
    """Établissement configuré avant 5.5.14 : chaque type ajouté reçoit, par cycle et année, le signataire
    déjà choisi pour sa catégorie — sans action de l'utilisateur."""
    _signataire(contexte, 'LISTE_PERSONNEL', 'KABORE', 'Le Directeur')
    _signataire(contexte, 'LISTE_REDEVABLES', 'ZONGO', "L'Intendante")

    import_module('parametres.migrations.0036_typedocument_documents_signes_2').ajouter_types(apps, None)

    def fonction(code):
        return SignataireDocument.objects.get(type_document__code=code, cycle=contexte['cycle'],
                                              annee_scolaire=contexte['annee']).fonction

    assert fonction('CONTRAT_TRAVAIL') == fonction('BULLETIN_SALAIRE') == fonction('BULLETIN_VACATION') == 'Le Directeur'
    assert fonction('LISTE_BOURSIERS') == "L'Intendante"
    # Catégories jamais configurées (Scolarité, Pédagogie) : rien n'est inventé
    assert not SignataireDocument.objects.filter(type_document__code__in=('PV_CONSEIL', 'DOSSIER_TRANSFERT')).exists()
    # Rejouable sans doublon
    import_module('parametres.migrations.0036_typedocument_documents_signes_2').ajouter_types(apps, None)
    assert SignataireDocument.objects.filter(type_document__code='CONTRAT_TRAVAIL').count() == 1


def test_signataire_dont_le_membre_a_ete_supprime_est_ignore(contexte):
    """Le signataire exact du document pointe vers un membre supprimé : le document ne reste pas muet, il se
    replie sur le signataire suivant du cycle (ici celui de la même catégorie)."""
    from personnel.models import MembrePersonnel
    exact = _signataire(contexte, 'CERT_SCOL', 'TRAORE', 'La Directrice')
    _signataire(contexte, 'CARTE_ID', 'KABORE', 'Le Directeur')
    MembrePersonnel.objects.filter(pk=exact.membre_personnel_id).delete()

    sig = SignataireDocument.objects.get_signataire(
        cycle=contexte['cycle'], type_document=TypeDocument.objects.get(code='CERT_SCOL'),
        annee_scolaire=contexte['annee'],
    )
    assert sig.get_membre_personnel().nom == 'KABORE'
    assert SignataireDocument.objects.get_signataire(cycle=None, type_document=None, annee_scolaire=None) == sig


def test_commande_verifier_signataires(contexte, settings, tmp_path):
    """`manage.py verifier_signataires` : signataire réellement imprimé par type et cycle, replis et anomalies
    (membre supprimé, fichier de signature absent)."""
    import io
    from django.core.files.base import ContentFile
    from django.core.management import call_command
    from personnel.models import MembrePersonnel
    settings.MEDIA_ROOT = str(tmp_path)
    sig = _signataire(contexte, 'LISTE_PERSONNEL', 'KABORE', 'Le Directeur')
    membre = sig.get_membre_personnel()
    membre.signature.save('kabore.png', ContentFile(b'\x89PNG\r\n\x1a\n'), save=True)
    orphelin = _signataire(contexte, 'CARTE_ID', 'TRAORE', 'La Directrice')
    MembrePersonnel.objects.filter(pk=orphelin.membre_personnel_id).delete()

    sortie = io.StringIO()
    call_command('verifier_signataires', stdout=sortie)
    texte = sortie.getvalue()
    assert 'Établissement : Ets Signataires — année courante : 2026-2027' in texte and 'Cycle Secondaire' in texte
    assert 'LISTE_PERSONNEL        Le Directeur — KABORE Salimata · signature scannée : oui' in texte
    assert 'CONTRAT_TRAVAIL        Le Directeur — KABORE Salimata · signature scannée : oui (repli : LISTE_PERSONNEL · Secondaire)' in texte
    assert 'CARTE_ID · Secondaire pointe vers un membre du personnel supprimé' in texte
    assert texte.rstrip().endswith('1 anomalie(s).')

    (tmp_path / membre.signature.name).unlink()
    sortie = io.StringIO()
    call_command('verifier_signataires', stdout=sortie)
    assert 'ANOMALIE : fichier de signature absent' in sortie.getvalue()


def test_migration_0051_cree_le_type_liste_des_eleves(contexte):
    """La liste générale des élèves a son propre type : elle se configure sans toucher aux listes de
    classe et se rejoue sans doublon."""
    from importlib import import_module
    migration = import_module('parametres.migrations.0051_typedocument_liste_eleves')

    # Migration déjà appliquée à la base de test : le type existe, on vérifie qu'elle le complète sans doublon.
    migration.ajouter_type(apps, None)
    type_doc = TypeDocument.objects.get(code='LISTE_ELEVES')
    assert type_doc.libelle == 'Liste des Élèves' and type_doc.categorie == 'SCOLARITE' and type_doc.actif

    migration.ajouter_type(apps, None)
    assert TypeDocument.objects.filter(code='LISTE_ELEVES').count() == 1
