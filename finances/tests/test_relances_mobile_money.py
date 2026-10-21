"""Relances Mobile Money : campagne de relances avec lien de paiement, relance d'une demande, avis de paiement (QR)."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from finances.models import DemandePaiementMobile, HistoriqueRelance
from finances.paiements_mobiles import ErreurPasserelle, verifier_en_attente

CONFIG = dict(CINETPAY_API_KEY='cle', CINETPAY_SITE_ID='123', CINETPAY_URL_PUBLIQUE='https://ecole.bf/')
LIEN = 'https://checkout.cinetpay.com/payment/jeton-abc'
REPONSE_LIEN = {'code': '201', 'message': 'CREATED', 'data': {'payment_token': 'jeton-abc', 'payment_url': LIEN}}
INLINE = lambda fonction, *args: fonction(*args)  # noqa: E731 — exécute la campagne dans la requête


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def comptable(etab):
    return baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False)


@pytest.fixture
def comptable_client(client, comptable):
    client.force_login(comptable)
    return client


@pytest.fixture
def configure(settings):
    for cle, valeur in CONFIG.items():
        setattr(settings, cle, valeur)


@pytest.fixture
def creance(etab):
    """Une classe, une rubrique tarifée 25 000 FCFA et un élève redevable joignable au 70123456."""
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, nom='Scolarité')
    baker.make('parametres.TarifScolarite', etablissement=etab, classe=classe, annee_scolaire=annee, rubrique=rubrique,
               montant=Decimal('25000'), actif=True)
    eleve = baker.make('inscriptions.Eleve', nom='OUÉDRAOGO', prenom='Awa', matricule='ETAB-2026-07', telephone_parent='70123456')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut='AFFECTE')
    return {'annee': annee, 'classe': classe, 'rubrique': rubrique, 'inscription': inscription}


@pytest.fixture
def demande(creance, comptable):
    return DemandePaiementMobile.objects.create(
        inscription=creance['inscription'], rubrique=creance['rubrique'], montant=Decimal('25000'),
        telephone='70123456', cree_par=comptable, lien_paiement=LIEN, jeton_paiement='jeton-abc',
    )


def _campagne(client, creance):
    return client.post(reverse('finances:relance_sms'), {
        'annee': str(creance['annee'].pk), 'classe': 'all', 'rubrique': str(creance['rubrique'].pk)}, follow=True)


@pytest.mark.django_db
class TestCampagneDeRelances:
    def test_sms_avec_lien_puis_reutilisation_de_la_demande(self, configure, comptable_client, comptable, creance):
        with patch('finances.views.relances._en_arriere_plan', INLINE), \
                patch('finances.paiements_mobiles._appeler', return_value=REPONSE_LIEN) as appel, \
                patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            reponse = _campagne(comptable_client, creance)
        demande = DemandePaiementMobile.objects.get()
        assert (demande.montant, demande.telephone, demande.rubrique, demande.cree_par, demande.lien_paiement, demande.sms_envoye) == (
            Decimal('25000'), '70123456', creance['rubrique'], comptable, LIEN, True)
        assert appel.call_args.args[1]['amount'] == 25000
        numero, texte = sms.call_args.args
        assert numero == '70123456' and texte.endswith(f'\nPayer en ligne: {LIEN}') and sms.call_args.kwargs == {'limite': 320}
        assert HistoriqueRelance.objects.filter(canal='SMS', montant_reclame=Decimal('25000')).count() == 1
        assert '1 SMS de relance envoyé(s). Lien de paiement en ligne inclus.' in reponse.content.decode()

        # Seconde campagne : la demande récente est réutilisée (pas de nouveau lien) et comptée comme relance.
        with patch('finances.views.relances._en_arriere_plan', INLINE), \
                patch('finances.paiements_mobiles._appeler') as appel, \
                patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            _campagne(comptable_client, creance)
        demande.refresh_from_db()
        assert not appel.called and DemandePaiementMobile.objects.count() == 1
        assert (demande.nb_relances, demande.relance_le is not None) == (1, True)
        assert LIEN in sms.call_args.args[1] and HistoriqueRelance.objects.count() == 2

    def test_passerelle_en_panne_un_seul_essai_et_sms_sans_lien(self, configure, comptable_client, creance):
        autre = baker.make('inscriptions.Eleve', nom='KABORÉ', prenom='Ali', telephone_parent='71000000')
        baker.make('inscriptions.Inscription', eleve=autre, classe=creance['classe'], annee_scolaire=creance['annee'], statut='AFFECTE')
        with patch('finances.views.relances._en_arriere_plan', INLINE), \
                patch('finances.paiements_mobiles._appeler', side_effect=ErreurPasserelle('passerelle injoignable')) as appel, \
                patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            _campagne(comptable_client, creance)
        assert appel.call_count == 1 and not DemandePaiementMobile.objects.exists()
        assert sms.call_count == 2 and all('Payer en ligne' not in c.args[1] and not c.kwargs for c in sms.call_args_list)
        assert HistoriqueRelance.objects.count() == 2

    def test_montant_non_eligible_sms_sans_lien(self, configure, comptable_client, creance):
        baker.make('finances.Paiement', inscription=creance['inscription'], rubrique=creance['rubrique'], montant=Decimal('23998'))
        with patch('finances.views.relances._en_arriere_plan', INLINE), \
                patch('finances.paiements_mobiles._appeler') as appel, \
                patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            _campagne(comptable_client, creance)
        assert not appel.called and not DemandePaiementMobile.objects.exists()
        assert '1 002' in sms.call_args.args[1] and 'Payer en ligne' not in sms.call_args.args[1]

    def test_sans_passerelle_comportement_inchange(self, comptable_client, creance):
        with patch('core.tasks.envoyer_sms_async') as envoi:
            reponse = _campagne(comptable_client, creance)
        assert envoi.call_args.args[0] == '70123456' and not DemandePaiementMobile.objects.exists()
        html = reponse.content.decode()
        assert '1 SMS de relance envoyé(s).' in html and 'Lien de paiement' not in html


@pytest.mark.django_db
class TestRelanceDUneDemande:
    def test_renvoie_le_sms_et_trace_la_relance(self, comptable_client, comptable, demande):
        with patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            reponse = comptable_client.post(reverse('finances:mobile_money_relancer', args=[demande.pk]), follow=True)
        assert LIEN in sms.call_args.args[1] and sms.call_args.kwargs == {'limite': 320}
        demande.refresh_from_db()
        assert (demande.nb_relances, demande.relance_le is not None, demande.sms_envoye) == (1, True, True)
        trace = HistoriqueRelance.objects.get()
        assert (trace.inscription, trace.rubrique, trace.canal, trace.montant_reclame, trace.envoye_par, trace.detail, trace.succes) == (
            demande.inscription, demande.rubrique, 'SMS', Decimal('25000'), comptable, '70123456', True)
        html = reponse.content.decode()
        assert f'Relance envoyée au 70123456 pour la demande {demande.reference}' in html and 'Relancé 1 fois' in html

    def test_demande_traitee_non_relancable(self, comptable_client, demande):
        demande.statut = 'CONFIRME'
        demande.save(update_fields=['statut'])
        with patch('core.sms.envoyer_sms') as sms:
            reponse = comptable_client.post(reverse('finances:mobile_money_relancer', args=[demande.pk]), follow=True)
        assert not sms.called and 'Seule une demande en attente peut être relancée.' in reponse.content.decode()
        assert not HistoriqueRelance.objects.exists()

    def test_demande_relancee_de_nouveau_verifiee(self, configure, comptable, demande):
        DemandePaiementMobile.objects.filter(pk=demande.pk).update(created_at=timezone.now() - timedelta(days=10))
        with patch('finances.paiements_mobiles._appeler', return_value={'code': '662', 'message': 'WAITING_CUSTOMER_PAYMENT'}) as appel:
            assert verifier_en_attente() == {}
            DemandePaiementMobile.objects.filter(pk=demande.pk).update(relance_le=timezone.now())
            assert verifier_en_attente() == {'EN_ATTENTE': 1} and appel.call_count == 1

    def test_droits_et_isolation(self, client, etab, demande):
        url = reverse('finances:mobile_money_relancer', args=[demande.pk])
        client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, must_change_password=False))
        with patch('core.sms.envoyer_sms') as sms:
            assert client.post(url).status_code in (302, 403)
            client.force_login(baker.make('accounts.User', role='COMPTABLE', must_change_password=False,
                                          etablissement=baker.make('etablissements.Etablissement')))
            assert client.post(url).status_code == 403
            assert client.get(reverse('finances:mobile_money_avis_pdf', args=[demande.pk])).status_code == 403
        assert not sms.called


class EspionPdf:
    """Remplace WeasyPrint : capture le HTML rendu."""
    documents = []

    def __init__(self, string='', **kwargs):
        EspionPdf.documents.append(string)

    def write_pdf(self, target=None, **kwargs):
        target.write(b'%PDF-1.4 espion')


@pytest.mark.django_db
class TestAvisDePaiement:
    def test_avis_pdf_avec_qr_code(self, comptable_client, demande):
        EspionPdf.documents.clear()
        with patch('finances.views.mobile_money.WeasyHTML', EspionPdf):
            reponse = comptable_client.get(reverse('finances:mobile_money_avis_pdf', args=[demande.pk]))
        assert reponse['Content-Type'] == 'application/pdf' and f'Avis_{demande.reference}.pdf' in reponse['Content-Disposition']
        html = EspionPdf.documents[0]
        for attendu in ('Avis de paiement', demande.reference, 'OUÉDRAOGO Awa', 'ETAB-2026-07', '25000 FCFA',
                        'data:image/png;base64,', LIEN, '*144#'):
            assert attendu in html, attendu

    def test_avis_sans_lien_sans_qr(self, comptable_client, demande):
        demande.lien_paiement = ''
        demande.save(update_fields=['lien_paiement'])
        EspionPdf.documents.clear()
        with patch('finances.views.mobile_money.WeasyHTML', EspionPdf):
            comptable_client.get(reverse('finances:mobile_money_avis_pdf', args=[demande.pk]))
        html = EspionPdf.documents[0]
        assert 'data:image/png;base64,' not in html and 'Payer en ligne' not in html and '*144#' in html

    def test_page_parent_et_tableau_de_bord(self, client, comptable_client, demande):
        html = client.get(reverse('finances:mobile_money_confirmation_parent', args=[demande.token])).content.decode()
        assert 'data:image/png;base64,' in html and 'scannez ce code' in html
        html = comptable_client.get(reverse('finances:mobile_money_list')).content.decode()
        assert reverse('finances:mobile_money_avis_pdf', args=[demande.pk]) in html
        assert reverse('finances:mobile_money_relancer', args=[demande.pk]) in html
