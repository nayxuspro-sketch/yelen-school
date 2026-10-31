"""Plafonds réglementaires des frais de scolarité (décret n° 2026-0761) : grille, bilan de conformité,
refus à la saisie d'un tarif, page et attestation PDF."""
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from parametres import plafonds
from parametres.models import TarifScolarite

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))
    identite = baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='Collège Yelen',
                          numero_agrement_mena='AG-042', categorie_reglementaire=1, zone_implantation=1)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='POST', nom='Post-primaire', actif=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A', niveau='6e', actif=True)
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Nouveau', actif=True)
    scol = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité', code='SCOL', actif=True)
    insc = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Inscription', code='INSC', actif=True)
    cant = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Cantine', code='CANT', actif=True,
                      soumise_plafond=False)
    return dict(etab=etab, identite=identite, annee=annee, classe=classe, statut=statut, scol=scol, insc=insc, cant=cant)


def _tarif(e, rubrique, montant):
    return baker.make('parametres.TarifScolarite', etablissement=e['etab'], annee_scolaire=e['annee'], classe=e['classe'],
                      statut_eleve=e['statut'], rubrique=rubrique, montant=Decimal(montant), actif=True)


def test_grille_du_decret(ecole):
    identite = ecole['identite']
    assert plafonds.plafond(identite, 'PRES') == 50000 and plafonds.plafond(identite, 'POST') == 90000
    identite.categorie_reglementaire, identite.zone_implantation = 3, 3
    assert plafonds.plafond(identite, 'SEC') == 140000 and plafonds.plafond(identite, 'PRIM') == 60000
    identite.categorie_reglementaire = None
    assert plafonds.plafond(identite, 'SEC') is None and plafonds.plafond(None, 'SEC') is None
    assert plafonds.plafond(ecole['identite'], 'INCONNU') is None


def test_bilan_de_conformite_exclut_les_rubriques_hors_plafond(ecole):
    _tarif(ecole, ecole['scol'], 80000)
    _tarif(ecole, ecole['insc'], 15000)
    _tarif(ecole, ecole['cant'], 30000)   # service annexe : hors plafond
    bilan = plafonds.conformite(ecole['etab'], ecole['annee'])
    (ligne,) = bilan['lignes']
    assert ligne['plafonne'] == 95000 and ligne['hors_plafond'] == 30000 and ligne['plafond'] == 90000
    assert ligne['ecart'] == -5000 and not ligne['conforme'] and bilan['nb_non_conformes'] == 1
    TarifScolarite.objects.filter(rubrique=ecole['insc']).update(montant=10000)
    bilan = plafonds.conformite(ecole['etab'], ecole['annee'])
    assert bilan['tout_conforme'] and bilan['lignes'][0]['ecart'] == 0


def test_saisie_refusee_au_dela_du_plafond(client, ecole):
    _tarif(ecole, ecole['scol'], 80000)
    donnees = {'annee_scolaire': ecole['annee'].pk, 'rubrique': ecole['insc'].pk, 'niveau': '6e',
               'statut_eleve': ecole['statut'].pk, 'montant': '15000'}
    reponse = client.post(reverse('parametres:tarif_create'), donnees)
    assert reponse.status_code == 200 and 'Plafond réglementaire dépassé' in reponse.content.decode()
    assert not TarifScolarite.objects.filter(rubrique=ecole['insc']).exists()
    reponse = client.post(reverse('parametres:tarif_create'), {**donnees, 'montant': '10000'})
    assert reponse.status_code == 204 and TarifScolarite.objects.get(rubrique=ecole['insc']).montant == 10000
    # Rubrique hors plafond : jamais bloquée. Établissement non classé : aucun contrôle.
    assert client.post(reverse('parametres:tarif_create'), {**donnees, 'rubrique': ecole['cant'].pk, 'montant': '50000'}).status_code == 204
    ecole['identite'].categorie_reglementaire = None
    ecole['identite'].save(update_fields=['categorie_reglementaire'])
    tarif = TarifScolarite.objects.get(rubrique=ecole['insc'])
    assert client.post(reverse('parametres:tarif_edit', args=[tarif.pk]), {**donnees, 'montant': '40000'}).status_code == 204


def test_page_et_attestation(client, ecole, mocker):
    _tarif(ecole, ecole['scol'], 85000)
    page = client.get(reverse('parametres:tarif_conformite')).content.decode()
    assert 'Catégorie 1' in page and 'Conforme' in page and reverse('parametres:tarif_conformite_pdf') in page
    rendu = mocker.patch('core.pdf.HTML')
    rendu.return_value.write_pdf.return_value = b'%PDF-1.4'
    reponse = client.get(reverse('parametres:tarif_conformite_pdf'), {'annee': ecole['annee'].pk})
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    html = rendu.call_args.kwargs['string'].replace('\xa0', ' ').replace('\u202f', ' ')
    assert 'Attestation de conformité tarifaire' in html and '85 000' in html and '90 000' in html
    # Dépassement : plus de bouton, l'attestation n'est pas délivrée
    _tarif(ecole, ecole['insc'], 10000)
    page = client.get(reverse('parametres:tarif_conformite')).content.decode()
    assert 'Dépassement' in page and reverse('parametres:tarif_conformite_pdf') not in page
    assert client.get(reverse('parametres:tarif_conformite_pdf')).status_code == 302


def test_identite_et_rubrique_enregistrent_les_nouveaux_champs(client, ecole):
    page = client.get(reverse('parametres:identite_etablissement')).content.decode()
    assert 'id_categorie_reglementaire' in page and 'id_zone_implantation' in page
    reponse = client.post(reverse('parametres:rubrique_edit', args=[ecole['scol'].pk]),
                          {'nom': 'Scolarité', 'code': 'SCOL', 'montant': '0', 'ordre': 1, 'actif': 'on'})
    assert reponse.status_code == 204
    ecole['scol'].refresh_from_db()
    assert ecole['scol'].soumise_plafond is False
