"""Assistant de première configuration (5.38.0) : état de chaque étape, avancement, accès et lien depuis les Paramètres."""
from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker

from core import demarrage

pytestmark = pytest.mark.django_db


@pytest.fixture
def etab(client):
    etablissement = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etablissement, must_change_password=False))
    return etablissement


def test_etapes_vides_puis_completes(etab):
    liste = demarrage.etapes(etab)
    assert [e['cle'] for e in liste] == ['identite', 'annee', 'cycles', 'tarifs', 'personnel', 'comptes', 'eleves', 'signataires']
    assert not any(e['fait'] for e in liste) and demarrage.avancement(liste)['pourcentage'] == 0
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='Collège Yelen',
               numero_agrement_mena='AG-1', devise='Travail')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='POST', actif=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, actif=True)
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, code='SCOL', actif=True)
    baker.make('parametres.TarifScolarite', etablissement=etab, annee_scolaire=annee, classe=classe, rubrique=rubrique,
               statut_eleve=baker.make('parametres.StatutEleve', etablissement=etab), montant=50000, actif=True)
    baker.make('personnel.MembrePersonnel', etablissement=etab)
    baker.make('accounts.User', etablissement=etab, role='SECRETAIRE', must_change_password=False)
    eleve = baker.make('inscriptions.Eleve', date_naissance=date(2012, 1, 1), photo='')
    baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
    liste = demarrage.etapes(etab)
    etats = {e['cle']: e['fait'] for e in liste}
    assert etats == {'identite': True, 'annee': True, 'cycles': True, 'tarifs': True, 'personnel': True,
                     'comptes': True, 'eleves': True, 'signataires': False}
    avancement = demarrage.avancement(liste)
    assert (avancement['faits'], avancement['pourcentage'], avancement['termine']) == (7, 88, False)


def test_page_assistant(client, etab):
    reponse = client.get(reverse('core:demarrage'))
    assert reponse.status_code == 200
    html = reponse.content.decode()
    assert 'Assistant de démarrage' in html and '0 / 8 étapes' in html
    for titre in ("Fiche de l", "Cycles et classes", "Signataires des documents"):
        assert titre in html, titre
    assert reverse('parametres:etablissement') in html and reverse('inscriptions:eleve_list') in html
    # Carte d'accès depuis les Paramètres, réservée aux rôles ayant accès aux paramètres
    assert reverse('core:demarrage') in client.get(reverse('parametres:index')).content.decode()
    client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, must_change_password=False))
    assert client.get(reverse('core:demarrage')).status_code in (302, 403)
