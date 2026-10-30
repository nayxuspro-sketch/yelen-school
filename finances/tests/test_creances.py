"""Créances individuelles (manuel non rendu, …) : situation financière, plafonds, encaissement, annulation."""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from finances.models import Creance, OrigineCreance, Paiement
from finances.views.commun import _calcul_situation_financiere, _payment_overage_errors, _situations_financieres_en_lot


@pytest.fixture
def ecole():
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A', niveau='6e', actif=True)
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Manuel non rendu', code='MNR', actif=True)
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut_eleve=None,
                             eleve__nom='OUEDRAOGO', eleve__prenom='Awa', eleve__date_naissance=date(2014, 5, 3))
    creance = Creance.objects.create(inscription=inscription, rubrique=rubrique, origine=OrigineCreance.MANUEL,
                                     libelle='Manuel non rendu : Mathématiques 6e (MAT-0001)', montant=4500)
    return {'etab': etab, 'annee': annee, 'classe': classe, 'rubrique': rubrique, 'inscription': inscription,
            'creance': creance}


def _connecter(client, ecole, role):
    client.force_login(baker.make('accounts.User', etablissement=ecole['etab'], role=role, must_change_password=False))
    return client


@pytest.mark.django_db
def test_creance_due_puis_encaissee_puis_annulee(ecole):
    """La créance compte dans le total dû (unitaire et en lot) comme une rubrique à payer ; un paiement sur sa
    rubrique la solde ; annulée, elle ne compte plus."""
    ins = ecole['inscription']
    sit = _calcul_situation_financiere(ins)
    assert (sit['total_du'], sit['total_paye'], sit['reste_a_payer']) == (4500, 0, 4500)
    assert [(f.libelle, f.montant) for f in sit['frais_details']] == [('Manuel non rendu : Mathématiques 6e (MAT-0001)', 4500)]
    assert _situations_financieres_en_lot([ins])[ins.pk]['reste_a_payer'] == 4500

    baker.make('finances.Paiement', inscription=ins, rubrique=ecole['rubrique'], montant=4500)
    assert _calcul_situation_financiere(ins)['reste_a_payer'] == 0
    assert _situations_financieres_en_lot([ins])[ins.pk]['reste_a_payer'] == 0

    ecole['creance'].annuler('Manuel rendu le 15/06/2027')
    sit = _calcul_situation_financiere(ins)
    assert sit['total_du'] == 0 and sit['frais_details'] == []
    assert Creance.objects.get(pk=ecole['creance'].pk).observation == 'Manuel rendu le 15/06/2027'


@pytest.mark.django_db
def test_plafond_et_rubriques_encaissables(client, ecole):
    """Sans tarif, la créance ouvre sa rubrique à l'encaissement et plafonne les versements ; avec un tarif sur la
    même rubrique, les deux s'additionnent."""
    ins, rubrique = ecole['inscription'], ecole['rubrique']
    assert _payment_overage_errors(ins, [(rubrique, Decimal('4500'), None)]) == []
    erreurs = _payment_overage_errors(ins, [(rubrique, Decimal('4501'), None)])
    assert len(erreurs) == 1 and 'dépasse le reste à payer 4\xa0500 FCFA' in erreurs[0]

    _connecter(client, ecole, 'COMPTABLE')
    data = client.get(reverse('finances:api_rubriques', kwargs={'inscription_id': ins.pk})).json()
    assert 'error' not in data
    assert [(r['code'], r['montant'], r['reste']) for r in data['rubriques']] == [('MNR', '4500', '4500')]
    assert data['situation'] == {'total_du': '4500', 'total_paye': '0', 'reste': '4500'}

    statut = baker.make('parametres.StatutEleve')
    baker.make('parametres.TarifScolarite', etablissement=ecole['etab'], classe=ecole['classe'], annee_scolaire=ecole['annee'],
               statut_eleve=statut, rubrique=rubrique, montant=1000, actif=True)
    ins.statut_eleve = statut
    ins.save()
    assert _payment_overage_errors(ins, [(rubrique, Decimal('5500'), None)]) == []
    assert len(_payment_overage_errors(ins, [(rubrique, Decimal('5501'), None)])) == 1
    data = client.get(reverse('finances:api_rubriques', kwargs={'inscription_id': ins.pk})).json()
    assert [(r['code'], r['montant']) for r in data['rubriques']] == [('MNR', '5500')]


@pytest.mark.django_db
def test_situation_eleve_redevables_et_annulation(client, ecole):
    """La créance est visible sur la situation de l'élève et dans les redevables ; l'annulation est un acte
    d'approbation (Direction), hors de portée du comptable."""
    ins, creance = ecole['inscription'], ecole['creance']
    situation = reverse('finances:situation_eleve', kwargs={'inscription_id': ins.pk})
    annuler = reverse('finances:creance_annuler', kwargs={'pk': creance.pk})

    _connecter(client, ecole, 'COMPTABLE')
    html = client.get(situation).content.decode()
    assert html.count('Manuel non rendu : Mathématiques 6e (MAT-0001)') >= 2      # rubrique à payer + carte créances
    assert 'Créances individuelles' in html and annuler not in html
    assert client.post(annuler).status_code == 302 and Creance.objects.get(pk=creance.pk).actif
    assert 'OUEDRAOGO' in client.get(reverse('finances:liste_redevables')).content.decode()

    _connecter(client, ecole, 'DIRECTEUR')
    assert annuler in client.get(situation).content.decode()
    reponse = client.post(annuler)
    assert reponse.status_code == 302 and reponse.url == situation
    creance.refresh_from_db()
    assert not creance.actif and creance.observation.startswith('Annulée le ')
    assert client.post(annuler).status_code == 404                              # déjà annulée
    html = client.get(situation).content.decode()
    assert 'Créances individuelles' not in html and _calcul_situation_financiere(ins)['total_du'] == 0
    assert not Paiement.objects.filter(inscription=ins).exists(), "annuler n'invente aucun paiement"

    autre = baker.make('inscriptions.Inscription', classe=baker.make('parametres.Classe'), annee_scolaire=ecole['annee'],
                       eleve__date_naissance=date(2014, 1, 1))
    etrangere = Creance.objects.create(inscription=autre, rubrique=ecole['rubrique'], libelle='Ailleurs', montant=100)
    assert client.post(reverse('finances:creance_annuler', kwargs={'pk': etrangere.pk})).status_code == 403
