"""Relevés Mobile Money : lecture du fichier, import, rapprochement automatique, validation, droits."""
import io
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from model_bakery import baker

from finances.models import DemandePaiementMobile, LigneReleve, ModePaiement, Paiement, ReleveMobileMoney
from finances.releves import FichierInvalide, _decimal, _detecter_colonnes, importer_releve, lire_releve

EN_TETE = 'Date;ID Transaction;Montant;Frais;Numéro client;Nom client;Motif\n'


def _csv(contenu, nom='releve.csv', encodage='utf-8'):
    return SimpleUploadedFile(nom, contenu.encode(encodage), content_type='text/csv')


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def annee(etab):
    return baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)


@pytest.fixture
def classe(etab):
    return baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab),
                      niveau='6EME', nom='6e A')


@pytest.fixture
def comptable(etab):
    return baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False)


@pytest.fixture
def comptable_client(client, comptable):
    client.force_login(comptable)
    return client


@pytest.fixture
def rubrique(etab):
    return baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, code='SCOL', nom='Scolarité')


def _inscrire(annee, classe, nom, matricule, telephone='', statut_eleve=None):
    eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Awa', matricule=matricule, tuteur_telephone=telephone)
    return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee,
                      statut='AFFECTE', est_exonere=False, statut_eleve=statut_eleve)


def _tarif(etab, classe, annee, rubrique, montant):
    statut = baker.make('parametres.StatutEleve', etablissement=etab)
    baker.make('parametres.TarifScolarite', etablissement=etab, classe=classe, annee_scolaire=annee,
               statut_eleve=statut, rubrique=rubrique, montant=Decimal(montant), actif=True)
    return statut


class TestLectureFichier:
    def test_detection_des_colonnes_par_en_tetes_libres(self):
        colonnes = _detecter_colonnes(['Date/Heure', 'Référence', 'Libellé', 'Montant (FCFA)', 'Commission', 'Expéditeur'])
        assert colonnes == {'date_operation': 0, 'numero_transaction': 1, 'motif': 2, 'montant': 3,
                            'frais': 4, 'telephone_payeur': 5}

    @pytest.mark.parametrize('brut, attendu', [
        ('25 000', '25000'), ('25.000', '25000'), ('25 000,00 FCFA', '25000.00'), ('1,250,000.50', '1250000.50'),
        ('25000.0', '25000.0'), (25000, '25000'), ('-5 000', '-5000'), ('abc', None),
    ])
    def test_montants_fcfa(self, brut, attendu):
        assert _decimal(brut) == (Decimal(attendu) if attendu is not None else None)

    def test_bloc_de_titre_avant_les_en_tetes_et_point_virgule(self):
        colonnes, lignes = lire_releve(_csv('Relevé marchand;;\nPériode;01/10/2026;31/10/2026\n\n' + EN_TETE
                                            + '02/10/2026 09:15;OM1;25 000;375;70123456;SAWADOGO;ETAB-2026-01\n'))
        assert colonnes['numero_transaction'] == 1 and lignes == [
            ['02/10/2026 09:15', 'OM1', '25 000', '375', '70123456', 'SAWADOGO', 'ETAB-2026-01']]

    def test_colonnes_obligatoires_absentes(self):
        with pytest.raises(FichierInvalide, match='Colonnes obligatoires'):
            lire_releve(_csv('Nom;Prénom;Classe\nA;B;C\n'))

    def test_format_non_pris_en_charge(self):
        with pytest.raises(FichierInvalide, match='CSV ou Excel'):
            lire_releve(SimpleUploadedFile('releve.pdf', b'%PDF', content_type='application/pdf'))

    def test_classeur_excel(self):
        classeur = openpyxl.Workbook()
        feuille = classeur.active
        feuille.append(['Transaction', 'Date', 'Montant', 'Téléphone'])
        feuille.append(['MV77', datetime(2026, 10, 3, 8, 0), 15000, 76000001])
        tampon = io.BytesIO()
        classeur.save(tampon)
        colonnes, lignes = lire_releve(SimpleUploadedFile('releve.xlsx', tampon.getvalue()))
        assert lignes[0][0] == 'MV77' and lignes[0][2] == 15000


@pytest.mark.django_db
class TestImportEtRapprochement:
    def test_import_rapproche_selon_les_quatre_niveaux(self, etab, annee, classe, comptable, rubrique):
        statut = _tarif(etab, classe, annee, rubrique, '100000')
        guichet = _inscrire(annee, classe, 'GUICHET', 'ETAB-2026-01')
        paiement_guichet = baker.make('finances.Paiement', inscription=guichet, montant=Decimal('25000'),
                                      mode_paiement=ModePaiement.MOBILE_MONEY, reference='om1')
        demandeur = _inscrire(annee, classe, 'DEMANDE', 'ETAB-2026-02')
        demande = DemandePaiementMobile.objects.create(inscription=demandeur, montant=Decimal('30000'),
                                                       telephone='70000002', rubrique=rubrique)
        matricule = _inscrire(annee, classe, 'MATRICULE', 'ETAB-2026-03')
        telephone = _inscrire(annee, classe, 'TELEPHONE', 'ETAB-2026-04', telephone='+226 70 12 34 56', statut_eleve=statut)
        _inscrire(annee, classe, 'JUMEAU1', 'ETAB-2026-05', telephone='70999999')
        _inscrire(annee, classe, 'JUMEAU2', 'ETAB-2026-06', telephone='70999999')

        releve = importer_releve(etab, 'ORANGE', _csv(
            EN_TETE
            + '02/10/2026 09:15;OM1;25 000;375;70000001;A;\n'
            + f'02/10/2026 09:20;OM2;30 000;450;70000002;B;Scolarite {demande.reference}\n'
            + '02/10/2026 09:25;OM3;10 000;150;70000003;C;frais etab-2026-03 tranche 1\n'
            + '02/10/2026 09:30;OM4;40 000;600;22670123456;D;\n'
            + '02/10/2026 09:35;OM5;5 000;75;70999999;E;\n'
            + '02/10/2026 09:40;OM6;-25 000;0;70000001;A;Remboursement\n'
            + '02/10/2026 09:45;OM1;25 000;375;70000001;A;doublon dans le fichier\n'
            + 'TOTAL;;110 000;;;;\n'
        ), comptable, rubrique)

        assert (releve.nb_lignes_fichier, releve.nb_doublons, releve.nb_rejets) == (8, 1, 2)
        lignes = {l.numero_transaction: l for l in releve.lignes.all()}
        assert set(lignes) == {'OM1', 'OM2', 'OM3', 'OM4', 'OM5'}
        assert (lignes['OM1'].statut, lignes['OM1'].methode, lignes['OM1'].paiement) == ('RAPPROCHE', 'TRANSACTION', paiement_guichet)
        assert (lignes['OM2'].statut, lignes['OM2'].methode, lignes['OM2'].inscription) == ('PROPOSE', 'DEMANDE', demandeur)
        assert (lignes['OM3'].statut, lignes['OM3'].methode, lignes['OM3'].inscription) == ('PROPOSE', 'MATRICULE', matricule)
        assert (lignes['OM4'].statut, lignes['OM4'].methode, lignes['OM4'].inscription) == ('A_CONFIRMER', 'TELEPHONE', telephone)
        assert (lignes['OM5'].statut, lignes['OM5'].inscription) == ('NON_IDENTIFIE', None)
        assert lignes['OM4'].frais == Decimal('600') and lignes['OM4'].telephone_payeur == '22670123456'

    def test_reimport_sans_doublon_et_isolation_par_operateur(self, etab, annee, classe, comptable):
        contenu = EN_TETE + '02/10/2026;OM1;25 000;0;;;\n'
        premier = importer_releve(etab, 'ORANGE', _csv(contenu), comptable)
        second = importer_releve(etab, 'ORANGE', _csv(contenu), comptable)
        moov = importer_releve(etab, 'MOOV', _csv(contenu), comptable)
        assert (premier.lignes.count(), second.lignes.count(), second.nb_doublons, moov.lignes.count()) == (1, 0, 1, 1)

    def test_transaction_du_guichet_avec_montant_different_non_rapprochee(self, etab, annee, classe, comptable):
        inscription = _inscrire(annee, classe, 'GUICHET', 'ETAB-2026-01')
        baker.make('finances.Paiement', inscription=inscription, montant=Decimal('25000'),
                   mode_paiement=ModePaiement.MOBILE_MONEY, reference='OM1')
        releve = importer_releve(etab, 'ORANGE', _csv(EN_TETE + '02/10/2026;OM1;20 000;0;;;\n'), comptable)
        assert releve.lignes.get().statut == 'NON_IDENTIFIE'
        assert Paiement.objects.filter(ligne_releve__isnull=True).count() == 1


@pytest.mark.django_db
class TestValidationEtEcrans:
    def _releve(self, etab, annee, classe, comptable, rubrique=None, contenu=None):
        inscription = _inscrire(annee, classe, 'MATRICULE', 'ETAB-2026-03', telephone='70000003')
        releve = importer_releve(etab, 'ORANGE', _csv(
            contenu or EN_TETE + '02/10/2026 09:25;OM3;10 000;150;70000003;C;etab-2026-03\n'
        ), comptable, rubrique)
        return inscription, releve

    def test_validation_cree_le_paiement_avec_recu_et_confirme_la_demande(self, etab, annee, classe, comptable_client, comptable, rubrique):
        inscription, releve = self._releve(etab, annee, classe, comptable, rubrique)
        demandeur = _inscrire(annee, classe, 'DEMANDE', 'ETAB-2026-02')
        demande = DemandePaiementMobile.objects.create(inscription=demandeur, montant=Decimal('30000'), telephone='70000002')
        releve2 = importer_releve(etab, 'ORANGE', _csv(EN_TETE + f'02/10/2026;OM2;30 000;0;70000002;;{demande.reference}\n'),
                                  comptable)
        ligne, ligne2 = releve.lignes.get(), releve2.lignes.get()

        reponse = comptable_client.post(reverse('finances:releve_valider', args=[releve.pk]), {'lignes': [str(ligne.pk)]})
        assert reponse.status_code == 302
        ligne.refresh_from_db()
        assert ligne.statut == 'RAPPROCHE' and ligne.paiement is not None
        paiement = ligne.paiement
        assert (paiement.inscription, paiement.montant, paiement.mode_paiement, paiement.reference, paiement.rubrique,
                paiement.encaisse_par, str(paiement.date_paiement)) == (
            inscription, Decimal('10000'), 'MOBILE_MONEY', 'OM3', rubrique, comptable, '2026-10-02')
        assert paiement.numero_recu.startswith('REC-')

        comptable_client.post(reverse('finances:releve_valider', args=[releve2.pk]), {'lignes': [str(ligne2.pk)]})
        demande.refresh_from_db()
        ligne2.refresh_from_db()
        assert demande.statut == 'CONFIRME' and demande.paiement == ligne2.paiement and demande.confirme_par == comptable

    def test_validation_refuse_le_depassement_du_reste_du(self, etab, annee, classe, comptable_client, comptable, rubrique):
        statut = _tarif(etab, classe, annee, rubrique, '5000')
        inscription, releve = self._releve(etab, annee, classe, comptable, rubrique)
        inscription.statut_eleve = statut
        inscription.save(update_fields=['statut_eleve'])
        ligne = releve.lignes.get()
        reponse = comptable_client.post(reverse('finances:releve_valider', args=[releve.pk]), {'lignes': [str(ligne.pk)]}, follow=True)
        ligne.refresh_from_db()
        assert ligne.statut == 'PROPOSE' and ligne.paiement is None
        assert 'dépasse le reste à payer' in reponse.content.decode()

    def test_affecter_puis_ignorer_une_ligne(self, etab, annee, classe, comptable_client, comptable):
        inscription, releve = self._releve(etab, annee, classe, comptable,
                                           contenu=EN_TETE + '02/10/2026;OM9;10 000;0;;;inconnu\n')
        ligne = releve.lignes.get()
        assert ligne.statut == 'NON_IDENTIFIE'

        comptable_client.post(reverse('finances:releve_ligne_affecter', args=[ligne.pk]), {'matricule': 'etab-2026-03'})
        ligne.refresh_from_db()
        assert (ligne.statut, ligne.methode, ligne.inscription) == ('PROPOSE', 'MANUEL', inscription)

        comptable_client.post(reverse('finances:releve_ligne_affecter', args=[ligne.pk]), {'matricule': 'XXX'}, follow=True)
        ligne.refresh_from_db()
        assert ligne.inscription == inscription

        comptable_client.post(reverse('finances:releve_ligne_ignorer', args=[ligne.pk]), {'motif': ''})
        ligne.refresh_from_db()
        assert ligne.statut == 'PROPOSE'
        comptable_client.post(reverse('finances:releve_ligne_ignorer', args=[ligne.pk]), {'motif': 'Vente de tenues'})
        ligne.refresh_from_db()
        assert (ligne.statut, ligne.inscription, ligne.motif_ignore) == ('IGNORE', None, 'Vente de tenues')

    def test_import_par_la_vue_et_ecrans(self, etab, annee, classe, comptable_client, comptable, rubrique):
        _inscrire(annee, classe, 'MATRICULE', 'ETAB-2026-03')
        reponse = comptable_client.post(reverse('finances:releve_import'), {
            'operateur': 'MOOV', 'rubrique': str(rubrique.pk),
            'fichier': _csv(EN_TETE + '02/10/2026;MV1;10 000;0;;;etab-2026-03\n', encodage='cp1252'),
        })
        releve = ReleveMobileMoney.objects.get()
        assert reponse.status_code == 302 and reponse.url == reverse('finances:releve_detail', args=[releve.pk])
        assert (releve.operateur, releve.rubrique, releve.importe_par) == ('MOOV', rubrique, comptable)

        html = comptable_client.get(reponse.url).content.decode()
        assert 'MV1' in html and 'Proposé' in html and 'Valider les lignes cochées' in html
        html = comptable_client.get(reverse('finances:releve_list')).content.decode()
        assert 'releve.csv' in html and 'Importer un relevé' in html

        reponse = comptable_client.post(reverse('finances:releve_import'), {
            'operateur': 'ORANGE', 'fichier': _csv('Nom;Prénom\nA;B\n'),
        }, follow=True)
        assert 'Colonnes obligatoires introuvables' in reponse.content.decode()
        assert ReleveMobileMoney.objects.count() == 1

    def test_badge_a_rapprocher_et_liste_du_guichet(self, etab, annee, classe, comptable_client, comptable):
        inscription = _inscrire(annee, classe, 'GUICHET', 'ETAB-2026-01')
        baker.make('finances.Paiement', inscription=inscription, montant=Decimal('25000'),
                   mode_paiement=ModePaiement.MOBILE_MONEY, reference='OM1')
        assert 'À rapprocher' in comptable_client.get(reverse('finances:situation_eleve', args=[inscription.pk])).content.decode()
        assert 'OM1' in comptable_client.get(reverse('finances:releve_list')).content.decode()

        importer_releve(etab, 'ORANGE', _csv(EN_TETE + '02/10/2026;OM1;25 000;0;;;\n'), comptable)
        html = comptable_client.get(reverse('finances:situation_eleve', args=[inscription.pk])).content.decode()
        assert 'Rapproché' in html and 'À rapprocher' not in html
        assert 'Tous les paiements Mobile Money saisis au guichet sont confirmés' in comptable_client.get(
            reverse('finances:releve_list')).content.decode()

    def test_droits_et_isolation_par_etablissement(self, client, etab, annee, classe, comptable):
        inscription, releve = self._releve(etab, annee, classe, comptable)
        ligne = releve.lignes.get()
        enseignant = baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, must_change_password=False)
        client.force_login(enseignant)
        for url in (reverse('finances:releve_list'), reverse('finances:releve_import'),
                    reverse('finances:releve_detail', args=[releve.pk])):
            assert client.get(url).status_code in (302, 403)
        assert client.post(reverse('finances:releve_valider', args=[releve.pk]), {'lignes': [str(ligne.pk)]}).status_code in (302, 403)
        ligne.refresh_from_db()
        assert ligne.statut == 'PROPOSE'

        autre = baker.make('accounts.User', role='COMPTABLE', etablissement=baker.make('etablissements.Etablissement'),
                           must_change_password=False)
        client.force_login(autre)
        assert client.get(reverse('finances:releve_detail', args=[releve.pk])).status_code == 403
        assert client.post(reverse('finances:releve_ligne_ignorer', args=[ligne.pk]), {'motif': 'x'}).status_code == 403
        assert 'releve.csv' not in client.get(reverse('finances:releve_list')).content.decode()
        assert LigneReleve.objects.get(pk=ligne.pk).statut == 'PROPOSE'

    def test_les_dates_sont_stockees_en_heure_locale(self, etab, annee, classe, comptable):
        _, releve = self._releve(etab, annee, classe, comptable)
        assert releve.lignes.get().date_operation == datetime(2026, 10, 2, 9, 25, tzinfo=dt_timezone.utc)
