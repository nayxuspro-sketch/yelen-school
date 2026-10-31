"""Lot J — fiche individuelle de l'élève (PDF A4 portrait signé) : identité, famille, santé, personnes autorisées, parcours."""
from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    user = baker.make('accounts.User', etablissement=etab, role='SECRETAIRE', must_change_password=False)
    client.force_login(user)
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    ancienne = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026', est_courante=False,
                          date_debut=date(2025, 10, 1), date_fin=date(2026, 6, 30))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    eleve = baker.make('inscriptions.Eleve', nom='TRAORE', prenom='Awa', genre='F', photo='', date_naissance=date(2012, 5, 3),
                       lieu_naissance='Ouagadougou', nom_pere='TRAORE Moussa', telephone_parent='70 11 22 33',
                       tuteur_nom='SAWADOGO Alima', groupe_sanguin='O+', allergies='Arachide',
                       personnes_autorisees='KONE Fatou (tante) 76 00 00 00\nZONGO Ali (oncle)')
    baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=ancienne, statut='ACTIF',
               classe=baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A'))
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee, statut='ACTIF',
                             classe=baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='5e A'))
    return {'etab': etab, 'eleve': eleve, 'inscription': inscription, 'client': client}


def test_la_fiche_reprend_identite_famille_sante_personnes_et_parcours(ecole, mocker):
    weasy = mocker.patch('inscriptions.views.documents._WeasyHTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    reponse = ecole['client'].get(reverse('inscriptions:eleve_fiche_pdf', args=[ecole['eleve'].pk]))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert 'Fiche_TRAORE_Awa.pdf' in reponse['Content-Disposition']
    html = weasy.call_args.kwargs['string']
    assert '@page { size: A4 portrait' in html and "Fiche individuelle de l'élève" in html
    for attendu in ('TRAORE', 'Awa', '03/05/2012', 'Ouagadougou', 'TRAORE Moussa', '70 11 22 33', 'SAWADOGO Alima',
                    'O+', 'Arachide', 'KONE Fatou (tante) 76 00 00 00', 'ZONGO Ali (oncle)', '5e A', '6e A', '2025-2026'):
        assert attendu in html, attendu
    assert html.index('5e A') < html.index('6e A'), 'parcours du plus récent au plus ancien'


def test_la_fiche_est_accessible_depuis_le_dossier_de_l_eleve(ecole):
    html = ecole['client'].get(reverse('inscriptions:eleve_detail', args=[ecole['eleve'].pk])).content.decode()
    assert reverse('inscriptions:eleve_fiche_pdf', args=[ecole['eleve'].pk]) in html
    assert 'Fiche individuelle' in html


def test_un_eleve_d_un_autre_etablissement_est_refuse(ecole):
    autre = baker.make('etablissements.Etablissement', nom='AUTRE')
    etranger = baker.make('inscriptions.Eleve', nom='AILLEURS', prenom='Sita', photo='', date_naissance=date(2012, 1, 1))
    baker.make('inscriptions.Inscription', eleve=etranger, classe=baker.make('parametres.Classe', etablissement=autre),
               annee_scolaire=baker.make('parametres.AnneeScolaire', etablissement=autre))
    reponse = ecole['client'].get(reverse('inscriptions:eleve_fiche_pdf', args=[etranger.pk]))
    assert reponse.status_code == 302 and reponse.url == reverse('inscriptions:eleve_list')


def test_la_fiche_sans_inscription_ni_personnes_autorisees(ecole, mocker):
    weasy = mocker.patch('inscriptions.views.documents._WeasyHTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    eleve = baker.make('inscriptions.Eleve', nom='NOUVEAU', prenom='Venu', photo='', date_naissance=date(2013, 2, 2),
                       personnes_autorisees='')
    reponse = ecole['client'].get(reverse('inscriptions:eleve_fiche_pdf', args=[eleve.pk]))
    assert reponse.status_code == 200
    html = weasy.call_args.kwargs['string']
    assert 'NOUVEAU' in html and 'aucune personne déclarée' in html
