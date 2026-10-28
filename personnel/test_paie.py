"""Lot H — paie du mois : préparation en masse des brouillons (reprise du dernier bulletin, ancienneté recalculée),
validation en masse, livre de paie, bulletins en lot (un PDF)."""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from personnel import paie
from personnel.models import SalairePersonnel

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    ancien = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salif',
                        date_embauche=date(2018, 10, 1), est_vacataire=False, is_active=True)
    nouveau = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZIDA', prenom='Aline',
                         date_embauche=date(2026, 9, 1), est_vacataire=False, is_active=True)
    baker.make('personnel.MembrePersonnel', etablissement=etab, nom='VACA', prenom='Taire', est_vacataire=True, is_active=True)
    baker.make('personnel.MembrePersonnel', etablissement=etab, nom='PARTI', prenom='Loin', est_vacataire=False, is_active=False)
    baker.make('personnel.SalairePersonnel', personnel=ancien, annee_scolaire=annee, mois=9, annee=2026,
               salaire_base=Decimal('200000'), indemnite_transport=Decimal('15000'), indemnite_logement=Decimal('25000'),
               prime_anciennete=Decimal('0'), autres_primes=Decimal('30000'), retenue_cnss=Decimal('11000'),
               retenue_iuts=Decimal('9000'), autres_retenues=Decimal('5000'), statut='PAYE')
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'annee': annee, 'ancien': ancien, 'nouveau': nouveau, 'user': user}


def test_preparer_reprend_le_dernier_bulletin_et_recalcule_l_anciennete(ecole):
    e = ecole
    crees, sans_reference = paie.preparer(e['etab'], 10, 2026, e['annee'], e['user'])
    assert [s.personnel for s in crees] == [e['ancien']] and sans_reference == [e['nouveau']]
    s = crees[0]
    assert (s.mois, s.annee, s.statut, s.annee_scolaire, s.created_by) == (10, 2026, 'BROUILLON', e['annee'], e['user'])
    assert (s.salaire_base, s.indemnite_transport, s.indemnite_logement) == (Decimal('200000'), Decimal('15000'), Decimal('25000'))
    assert (s.retenue_cnss, s.retenue_iuts) == (Decimal('11000'), Decimal('9000'))
    assert (s.autres_primes, s.autres_retenues) == (0, 0), 'exceptionnels remis à zéro'
    assert s.prime_anciennete == Decimal('20000'), '8 ans → 10 % du salaire de base'
    assert s.salaire_net == Decimal('240000')

    # Idempotent : relancer ne crée rien de plus
    assert paie.preparer(e['etab'], 10, 2026, e['annee'], e['user']) == ([], [e['nouveau']])
    assert SalairePersonnel.objects.filter(mois=10, annee=2026).count() == 1


def test_ecran_preparation_validation_et_livre(client, ecole):
    e = ecole
    url = reverse('personnel:paie_mois') + '?mois=10&annee=2026'
    page = client.get(url)
    assert page.status_code == 200 and page.context['salaires'] == []
    assert page.context['sans_bulletin'] == [e['ancien'], e['nouveau']]

    reponse = client.post(reverse('personnel:paie_preparer'), {'mois': '10', 'annee': '2026'}, follow=True)
    assert reponse.redirect_chain[-1][0] == url
    html = reponse.content.decode()
    assert '1 bulletin de Octobre 2026 préparé en brouillon.' in html and 'ZIDA Aline' in html
    assert reponse.context['par_statut'] == {'BROUILLON': 1, 'VALIDE': 0, 'PAYE': 0}
    assert reponse.context['totaux']['net'] == Decimal('240000') and reponse.context['sans_bulletin'] == [e['nouveau']]

    reponse = client.post(reverse('personnel:paie_valider'), {'mois': '10', 'annee': '2026'}, follow=True)
    assert '1 bulletin validé.' in reponse.content.decode()
    assert reponse.context['par_statut'] == {'BROUILLON': 0, 'VALIDE': 1, 'PAYE': 0}
    assert SalairePersonnel.objects.get(mois=10, annee=2026).statut == 'VALIDE'

    livre = paie.livre(e['etab'], 10, 2026)
    assert (livre['libelle_mois'], len(livre['salaires'])) == ('Octobre', 1)
    assert livre['totaux'] == {'base': Decimal('200000'), 'indemnites': Decimal('40000'), 'primes': Decimal('20000'),
                               'brut': Decimal('260000'), 'cnss': Decimal('11000'), 'iuts': Decimal('9000'),
                               'autres_retenues': Decimal('0'), 'retenues': Decimal('20000'), 'net': Decimal('240000')}


def test_pdfs_livre_et_bulletins_en_lot(client, ecole, mocker):
    e = ecole
    paie.preparer(e['etab'], 10, 2026, e['annee'], e['user'])
    baker.make('personnel.SalairePersonnel', personnel=e['nouveau'], annee_scolaire=e['annee'], mois=10, annee=2026,
               salaire_base=Decimal('120000'), statut='BROUILLON')
    html = mocker.patch('core.pdf.HTML')
    html.return_value.write_pdf.return_value = b'%PDF-livre'
    html.lot.return_value = b'%PDF-lot'

    livre = client.get(reverse('personnel:livre_paie_pdf') + '?mois=10&annee=2026')
    assert livre.status_code == 200 and livre.content == b'%PDF-livre'
    assert livre['Content-Disposition'] == 'inline; filename="livre_paie_2026_10.pdf"'
    source = html.call_args.kwargs['string']
    assert 'Livre de paie' in source and 'KABORE Salif' in source and 'ZIDA Aline' in source and '360' in source

    lot = client.get(reverse('personnel:bulletins_paie_lot_pdf') + '?mois=10&annee=2026')
    assert lot.status_code == 200 and lot.content == b'%PDF-lot'
    fragments = html.lot.call_args.args[0]
    assert len(fragments) == 2 and all('BULLETIN DE SALAIRE' in f.upper() for f in fragments)
    assert 'KABORE Salif' in fragments[0] and 'ZIDA Aline' in fragments[1]


def test_mois_invalide_retombe_sur_le_mois_courant(client, ecole):
    page = client.get(reverse('personnel:paie_mois') + '?mois=13&annee=abc')
    assert page.status_code == 200 and (page.context['mois'], page.context['annee']) == (date.today().month, date.today().year)


def test_sans_annee_scolaire_courante(client, ecole):
    ecole['annee'].est_courante = False
    ecole['annee'].save()
    reponse = client.post(reverse('personnel:paie_preparer'), {'mois': '10', 'annee': '2026'}, follow=True)
    assert 'Aucune année scolaire courante' in reponse.content.decode() and not SalairePersonnel.objects.filter(mois=10).exists()
