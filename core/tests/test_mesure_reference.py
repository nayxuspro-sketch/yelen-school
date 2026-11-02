"""Mesures de référence (P1-9, 5.47.2) : les six écrans du quotidien sont chronométrés à chaque livraison."""
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from model_bakery import baker

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    from datetime import date
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
               date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    baker.make('parametres.Classe', etablissement=etab, nom='6e A', actif=True)
    return baker.make('accounts.User', username='directeur', is_superuser=True, is_active=True,
                      role='SUPER_ADMIN', etablissement=etab, must_change_password=False)


def test_mesure_affiche_les_six_pages(admin, capsys):
    """Le tableau liste les six écrans de référence avec durée et nombre de requêtes."""
    call_command('mesure_reference', repeter=1)
    sortie = capsys.readouterr().out
    for libelle in ('Accueil', 'Élèves', 'Évaluations (notes)', 'Redevables', 'Paiements', 'Bulletins'):
        assert libelle in sortie
    assert 'Durée (ms)' in sortie and 'Requêtes' in sortie
    assert 'Seuil' in sortie


def test_mesure_json_exploitable(admin, capsys):
    """La sortie --json est un document valide (supervision) portant chaque page et son statut."""
    call_command('mesure_reference', repeter=1, json=True)
    document = json.loads(capsys.readouterr().out)
    assert document['version']
    assert len(document['pages']) == 6
    assert {p['page'] for p in document['pages']} >= {'Accueil', 'Bulletins'}
    for page in document['pages']:
        assert page['statut'] == 200 and page['duree_ms'] is not None and page['requetes'] >= 0


def test_mesure_echoue_au_dela_du_seuil(admin):
    """Un seuil impossible fait échouer la commande : utilisable comme garde-fou planifié."""
    with pytest.raises(CommandError) as erreur:
        call_command('mesure_reference', repeter=1, seuil_ms=0)
    assert 'seuil' in str(erreur.value)


def test_mesure_utilisateur_inconnu(admin):
    with pytest.raises(CommandError):
        call_command('mesure_reference', utilisateur='personne')


def test_mesure_sans_super_admin():
    """Sans Super Admin actif, la commande demande explicitement un compte plutôt que d'échouer obscurément."""
    with pytest.raises(CommandError) as erreur:
        call_command('mesure_reference', repeter=1)
    assert 'Super Admin' in str(erreur.value)


def test_mesure_repetitions_invalides(admin):
    with pytest.raises(CommandError):
        call_command('mesure_reference', repeter=0)
