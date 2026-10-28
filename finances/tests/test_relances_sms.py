"""SMS de relance : redevables calculés comme au formulaire de paiement (et identiques au compteur et au PDF),
un SMS nominatif par élève — nom, rubrique, reste de CET élève — au numéro de SA fiche, modèle toujours rendu."""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from model_bakery import baker

from core.models import SmsSortant
from finances.models import HistoriqueRelance
from finances.redevables import inscriptions_relancables, redevables_rubrique
from parametres.models import ModeleMessage

D = Decimal
DEFAUT = "Bonjour, un rappel de paiement : {rubrique} de {montant} FCFA pour {nom_eleve} est en attente. Contactez Lycée Yelen."


class EspionPdf:
    documents = []

    def __init__(self, string='', **kwargs):
        EspionPdf.documents.append(string)

    def write_pdf(self, target=None, **kwargs):
        target.write(b'%PDF-1.4 espion')


@pytest.fixture
def ecole(db):
    etab = baker.make('etablissements.Etablissement', nom='Lycée Yelen')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='6EME', nom='6e A')
    statut = baker.make('parametres.StatutEleve', etablissement=etab)
    scol = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, nom='Scolarité', code='SCOL')
    cantine = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, nom='Cantine', code='CANT')
    for rubrique, montant in ((scol, '50000'), (cantine, '20000')):
        baker.make('parametres.TarifScolarite', etablissement=etab, classe=classe, annee_scolaire=annee,
                   statut_eleve=statut, rubrique=rubrique, montant=D(montant), actif=True)
    comptable = baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False)
    return dict(etab=etab, annee=annee, classe=classe, statut=statut, scol=scol, cantine=cantine, comptable=comptable)


def _inscrire(ecole, nom, prenom, telephone_parent='', statut=True, **champs):
    eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, telephone_parent=telephone_parent, **champs)
    return baker.make('inscriptions.Inscription', eleve=eleve, classe=ecole['classe'], annee_scolaire=ecole['annee'],
                      statut_eleve=ecole['statut'] if statut else None, statut='AFFECTE')


def _redevables(ecole, rubrique):
    return redevables_rubrique(inscriptions_relancables(ecole['etab'], ecole['annee']), rubrique)


class TestRedevablesRubrique:
    def test_tarif_de_la_situation_de_l_eleve_paiements_et_remboursements(self, ecole):
        awa = _inscrire(ecole, 'OUEDRAOGO', 'Awa')                  # 50 000 dû − (20 000 − 5 000 remboursés)
        ali = _inscrire(ecole, 'KABORE', 'Ali')                     # à jour
        _inscrire(ecole, 'SAWADOGO', 'Issa', statut=False)          # sans statut : aucun tarif applicable
        paiement = baker.make('finances.Paiement', inscription=awa, rubrique=ecole['scol'], montant=D('20000'))
        baker.make('finances.Remboursement', paiement=paiement, montant=D('5000'))
        baker.make('finances.Paiement', inscription=ali, rubrique=ecole['scol'], montant=D('50000'))
        # Tarifs étrangers à la situation de l'élève (autre statut, inactif sur une classe du même niveau,
        # autre année) : jamais retenus
        commun = dict(etablissement=ecole['etab'], classe=ecole['classe'], rubrique=ecole['scol'])
        baker.make('parametres.TarifScolarite', annee_scolaire=ecole['annee'], montant=D('999999'), actif=True,
                   statut_eleve=baker.make('parametres.StatutEleve', etablissement=ecole['etab']), **commun)
        jumelle = baker.make('parametres.Classe', etablissement=ecole['etab'], cycle=ecole['classe'].cycle, niveau='6EME', nom='6e B')
        baker.make('parametres.TarifScolarite', annee_scolaire=ecole['annee'], statut_eleve=ecole['statut'],
                   montant=D('1'), actif=False, **dict(commun, classe=jumelle))
        baker.make('parametres.TarifScolarite', annee_scolaire=baker.make('parametres.AnneeScolaire', etablissement=ecole['etab']),
                   statut_eleve=ecole['statut'], montant=D('2'), actif=True, **commun)

        redevables = _redevables(ecole, ecole['scol'])

        assert [(r.inscription, r.montant_du, r.verse, r.reste) for r in redevables] == [(awa, D('50000'), D('15000'), D('35000'))]

    def test_creances_bourses_ciblees_et_plafond_du_reste_global(self, ecole):
        sans_statut = _inscrire(ecole, 'ZONGO', 'Paul', statut=False)
        baker.make('finances.Creance', inscription=sans_statut, rubrique=ecole['cantine'], montant=D('8000'), actif=True)
        type_bourse = baker.make('finances.TypeBourse', etablissement=ecole['etab'], valeur_reduction=D('50000'))
        boursiere = _inscrire(ecole, 'ILBOUDO', 'Mariam')           # bourse ciblée Scolarité : rien à relancer dessus
        baker.make('finances.BourseEleve', inscription=boursiere, type_bourse=type_bourse, montant_accorde=D('50000'),
                   rubrique=ecole['scol'], actif=True)
        global_ = _inscrire(ecole, 'TRAORE', 'Moussa')               # bourse globale 60 000 sur 70 000 dus : reste 10 000
        baker.make('finances.BourseEleve', inscription=global_, type_bourse=type_bourse, montant_accorde=D('60000'), actif=True)

        scolarite = {r.eleve.nom: r.reste for r in _redevables(ecole, ecole['scol'])}
        cantine = {r.eleve.nom: r.reste for r in _redevables(ecole, ecole['cantine'])}

        assert scolarite == {'TRAORE': D('10000')}
        assert cantine == {'ILBOUDO': D('20000'), 'TRAORE': D('10000'), 'ZONGO': D('8000')}

    def test_nombre_de_requetes_constant(self, ecole, django_assert_max_num_queries):
        for i in range(4):
            _inscrire(ecole, f'ELEVE{i}', 'Test')
        inscriptions = list(inscriptions_relancables(ecole['etab'], ecole['annee']))
        with django_assert_max_num_queries(13):  # 7 agrégats de la rubrique + 6 de la situation globale
            assert len(redevables_rubrique(inscriptions, ecole['scol'])) == 4


class TestRelanceSms:
    @pytest.fixture(autouse=True)
    def _sms_actifs(self, settings):
        settings.SMS_ENABLED = True

    @staticmethod
    def _campagne(client, ecole, rubrique=None, classe='all'):
        client.force_login(ecole['comptable'])
        return client.post(reverse('finances:relance_sms'), {
            'annee': str(ecole['annee'].pk), 'classe': classe, 'rubrique': str((rubrique or ecole['scol']).pk)}, follow=True)

    def test_un_sms_nominatif_par_eleve_redevable_au_numero_de_sa_fiche(self, client, ecole):
        awa = _inscrire(ecole, 'OUEDRAOGO', 'Awa', telephone_parent='70 11 22 33')
        ali = _inscrire(ecole, 'KABORE', 'Ali', telephone_parent='71000000')                         # à jour
        issa = _inscrire(ecole, 'SAWADOGO', 'Issa', telephone_parent='', tuteur_telephone='76554433')  # joint via le tuteur
        baker.make('finances.Paiement', inscription=awa, rubrique=ecole['scol'], montant=D('35000'))
        baker.make('finances.Paiement', inscription=ali, rubrique=ecole['scol'], montant=D('50000'))
        baker.make('finances.Paiement', inscription=issa, rubrique=ecole['cantine'], montant=D('20000'))  # autre rubrique

        reponse = self._campagne(client, ecole)

        sms = {s.numero: s for s in SmsSortant.objects.all()}
        assert set(sms) == {'+22670112233', '+22676554433'}
        assert sms['+22670112233'].message == DEFAUT.format(rubrique='Scolarité', montant='15 000', nom_eleve='OUEDRAOGO AWA')
        assert sms['+22676554433'].message == DEFAUT.format(rubrique='Scolarité', montant='50 000', nom_eleve='SAWADOGO ISSA')
        assert sms['+22670112233'].destinataire == 'OUEDRAOGO AWA — Scolarité'
        historique = {h.inscription_id: (h.montant_reclame, h.detail) for h in HistoriqueRelance.objects.filter(canal='SMS')}
        assert historique == {awa.pk: (D('15000'), '+22670112233'), issa.pk: (D('50000'), '+22676554433')}
        assert '2 SMS de relance envoyé(s).' in reponse.content.decode()

    def test_compteur_pdf_et_sms_designent_les_memes_eleves(self, client, ecole):
        _inscrire(ecole, 'OUEDRAOGO', 'Awa', telephone_parent='70112233')
        ali = _inscrire(ecole, 'KABORE', 'Ali', telephone_parent='71000000')
        baker.make('finances.Paiement', inscription=ali, rubrique=ecole['scol'], montant=D('50000'))
        selection = {'annee': str(ecole['annee'].pk), 'classe': str(ecole['classe'].pk), 'rubrique': str(ecole['scol'].pk)}
        client.force_login(ecole['comptable'])

        compteur = client.get(reverse('finances:relance_count'), selection).content.decode()
        EspionPdf.documents.clear()
        with patch('finances.views.relances.WeasyHTML', EspionPdf):
            assert client.get(reverse('finances:relance_paiement_pdf'), selection).status_code == 200
        self._campagne(client, ecole, classe=str(ecole['classe'].pk))

        assert '<strong>1</strong>&nbsp;élève redevable' in compteur
        assert EspionPdf.documents[0].count('OUEDRAOGO') == 1 and 'KABORE' not in EspionPdf.documents[0]
        assert [s.numero for s in SmsSortant.objects.all()] == ['+22670112233']
        assert HistoriqueRelance.objects.filter(canal='PDF').count() == HistoriqueRelance.objects.filter(canal='SMS').count() == 1

    def test_eleve_sans_numero_valide_signale_et_non_trace(self, client, ecole):
        _inscrire(ecole, 'ZONGO', 'Paul', telephone_parent='12', tuteur_telephone='abc', telephone_urgence='')

        html = self._campagne(client, ecole).content.decode()

        assert not SmsSortant.objects.exists() and not HistoriqueRelance.objects.exists()
        assert '1 élève(s) sans numéro valide' in html

    def test_sms_desactives_rien_n_est_envoye_ni_trace(self, client, ecole, settings):
        settings.SMS_ENABLED = False
        _inscrire(ecole, 'OUEDRAOGO', 'Awa', telephone_parent='70112233')

        html = self._campagne(client, ecole).content.decode()

        assert 'Envoi de SMS désactivé' in html and 'envoyé(s)' not in html
        assert not SmsSortant.objects.exists() and not HistoriqueRelance.objects.exists()

    def test_modele_personnalise_rendu_avec_les_donnees_de_l_eleve(self, client, ecole):
        ModeleMessage.objects.create(etablissement=ecole['etab'], type='PAIEMENT', actif=True,
                                     contenu_sms='{etablissement} : {nom_eleve} doit {montant} FCFA ({rubrique}).')
        _inscrire(ecole, 'OUEDRAOGO', 'Awa', telephone_parent='70112233')

        self._campagne(client, ecole)

        assert SmsSortant.objects.get().message == 'Lycée Yelen : OUEDRAOGO AWA doit 50 000 FCFA (Scolarité).'

    def test_modele_a_variable_inconnue_remplace_par_le_texte_par_defaut(self, client, ecole):
        """Un modèle citant {eleve} ou {reste} partait tel quel au parent (accolades comprises)."""
        ModeleMessage.objects.create(etablissement=ecole['etab'], type='PAIEMENT', actif=True,
                                     contenu_sms='Cher parent, {eleve} doit {reste} F pour {rubrique}.')
        _inscrire(ecole, 'OUEDRAOGO', 'Awa', telephone_parent='70112233')

        self._campagne(client, ecole)

        assert SmsSortant.objects.get().message == DEFAUT.format(rubrique='Scolarité', montant='50 000', nom_eleve='OUEDRAOGO AWA')


class TestModeleMessage:
    @pytest.fixture
    def directeur_client(self, client, ecole):
        client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=ecole['etab'], must_change_password=False))
        return client

    def test_rendu_sans_exception(self, db):
        etab = baker.make('etablissements.Etablissement', nom='Lycée Yelen')
        ModeleMessage.objects.create(etablissement=etab, type='PAIEMENT', actif=True,
                                     contenu_sms='Accolade {orpheline et {nom_eleve} : {montant} F ({rubrique}) }')

        texte = ModeleMessage.get_contenu(etab, 'PAIEMENT', {
            'nom_eleve': 'OUEDRAOGO AWA', 'montant': '50 000', 'rubrique': 'Scolarité', 'etablissement': 'Lycée Yelen'})

        assert texte == 'Accolade {orpheline et OUEDRAOGO AWA : 50 000 F (Scolarité) }'

    @pytest.mark.parametrize('contenu, attendu', [
        ('{eleve} doit {montant} F.', 'variable(s) inconnue(s) pour ce type : {eleve}'),
        ('{nom_eleve doit {montant} F.', 'accolade isolée'),
        ('Rappel : {rubrique} de {montant} FCFA pour {nom_eleve}. ' + 'x' * 100, 'message trop long'),
    ])
    def test_formulaire_refuse_les_modeles_invalides(self, directeur_client, ecole, contenu, attendu):
        url = reverse('parametres:modele_message_form', kwargs={'type_msg': 'PAIEMENT'})

        html = directeur_client.post(url, {'contenu_sms': contenu, 'actif': 'on'}, follow=True).content.decode()

        assert 'non enregistré : ' + attendu in html
        assert ModeleMessage.objects.get(etablissement=ecole['etab'], type='PAIEMENT').contenu_sms == ModeleMessage.DEFAUTS['PAIEMENT']

    def test_formulaire_accepte_un_modele_valide_et_signale_les_anciens_modeles_ignores(self, directeur_client, ecole):
        ModeleMessage.objects.create(etablissement=ecole['etab'], type='ABSENCE', actif=True, contenu_sms='{eleve} absent le {date}.')

        liste = directeur_client.get(reverse('parametres:modeles_messages')).content.decode()
        html = directeur_client.post(reverse('parametres:modele_message_form', kwargs={'type_msg': 'PAIEMENT'}),
                                     {'contenu_sms': 'Yelen : {nom_eleve} doit {montant} FCFA ({rubrique}).', 'actif': 'on'},
                                     follow=True).content.decode()

        assert liste.count('Ignoré — variable inconnue') == 1
        assert 'Modèle « Relance paiement » enregistré.' in html
        assert ModeleMessage.objects.get(etablissement=ecole['etab'], type='PAIEMENT').contenu_sms == \
            'Yelen : {nom_eleve} doit {montant} FCFA ({rubrique}).'
