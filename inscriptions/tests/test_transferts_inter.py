"""Transferts inter-établissements : demande, décision, dossier PDF (couverture 5.47.1).

Un transfert sortant ferme un dossier et conditionne le devenir de l'élève : les tests suivent
la chaîne complète (demande → approuver/refuser → dossier PDF) et vérifient surtout que
l'approbation laisse une trace retrouvable dans le parcours de l'élève.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from inscriptions.models import EvenementParcours, Inscription, TransfertEleve
from inscriptions.views import transferts as vues_transferts

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='LE SAVOIR')
    directeur = baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, is_superuser=True,
                           must_change_password=False)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Post-primaire', code='PP')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    eleve = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Awa', photo='',
                       date_naissance=date(2011, 1, 1))
    inscription = baker.make(Inscription, eleve=eleve, classe=classe, annee_scolaire=annee, statut='AFFECTE')
    client.force_login(directeur)
    return {'client': client, 'etab': etab, 'annee': annee, 'classe': classe,
            'eleve': eleve, 'inscription': inscription, 'directeur': directeur}


def _transfert(ecole, **extra):
    champs = {'inscription': ecole['inscription'], 'etablissement_destination': 'Lycée Bogodogo',
              'motif': 'Rapprochement familial', 'demandeur': ecole['directeur']}
    champs.update(extra)
    return baker.make(TransfertEleve, **champs)


# ── Liste et demande ────────────────────────────────────────────────────────

def test_transfert_list_filtre_et_compte_les_attentes(ecole):
    """La liste reste dans l'établissement, se filtre par statut et par recherche, et pagine."""
    en_attente = _transfert(ecole)
    approuve = _transfert(ecole, etablissement_destination='Lycée Ziniaré',
                          statut='APPROUVE', date_traitement=date(2026, 10, 20))
    autre_etab = baker.make('etablissements.Etablissement', nom='AILLEURS')
    baker.make(TransfertEleve,
               inscription=baker.make(Inscription, annee_scolaire=ecole['annee'], eleve__photo='',
                                      classe=baker.make('parametres.Classe', etablissement=autre_etab,
                                                        nom='6e A')),
               etablissement_destination='Hors périmètre')

    url = reverse('inscriptions:transfert_inter_list')
    reponse = ecole['client'].get(url)
    assert reponse.status_code == 200
    assert {t.pk for t in reponse.context['page_obj']} == {en_attente.pk, approuve.pk}
    assert reponse.context['nb_en_attente'] == 1

    par_statut = ecole['client'].get(url, {'statut': 'APPROUVE'})
    assert [t.pk for t in par_statut.context['page_obj']] == [approuve.pk]
    assert par_statut.context['nb_en_attente'] == 0

    par_destination = ecole['client'].get(url, {'q': 'ziniaré'})
    assert [t.pk for t in par_destination.context['page_obj']] == [approuve.pk]

    par_eleve = ecole['client'].get(url, {'q': 'ouedraogo'})
    assert {t.pk for t in par_eleve.context['page_obj']} == {en_attente.pk, approuve.pk}


def test_transfert_demander_cree_une_demande_et_refuse_le_doublon(ecole):
    """Une demande sans destination est refusée ; la seconde demande en attente est bloquée."""
    url = reverse('inscriptions:transfert_inter_demander',
                  kwargs={'inscription_id': ecole['inscription'].pk})
    assert ecole['client'].get(url).status_code == 200

    ecole['client'].post(url, {'etablissement_destination': '   ', 'motif': 'x'})
    assert not TransfertEleve.objects.exists()

    creation = ecole['client'].post(url, {'etablissement_destination': 'Lycée Bogodogo',
                                          'motif': 'Rapprochement familial'})
    transfert = TransfertEleve.objects.get()
    assert creation.status_code == 302
    assert creation.url == reverse('inscriptions:transfert_inter_detail', kwargs={'pk': transfert.pk})
    assert transfert.demandeur == ecole['directeur'] and transfert.statut == 'EN_ATTENTE'

    doublon = ecole['client'].post(url, {'etablissement_destination': 'Autre lycée'}, follow=True)
    assert TransfertEleve.objects.count() == 1
    assert 'déjà en cours' in doublon.content.decode()


def test_transfert_demander_refuse_un_eleve_part_ou_d_un_autre_etablissement(ecole):
    """Un élève en abandon ne demande pas de transfert ; un dossier d'une autre école est inaccessible."""
    ecole['inscription'].statut = 'ABANDON'
    ecole['inscription'].save(update_fields=['statut'])
    abandon = ecole['client'].get(reverse('inscriptions:transfert_inter_demander',
                                          kwargs={'inscription_id': ecole['inscription'].pk}), follow=True)
    assert abandon.redirect_chain[-1][0] == reverse('inscriptions:eleve_detail',
                                                   kwargs={'pk': ecole['eleve'].pk})
    assert 'déjà en statut Abandon' in abandon.content.decode()

    autre_etab = baker.make('etablissements.Etablissement', nom='AILLEURS')
    ailleurs = baker.make(Inscription, annee_scolaire=ecole['annee'], eleve__photo='',
                          classe=baker.make('parametres.Classe', etablissement=autre_etab, nom='6e A'))
    hors = ecole['client'].get(reverse('inscriptions:transfert_inter_demander',
                                       kwargs={'inscription_id': ailleurs.pk}), follow=True)
    assert hors.redirect_chain[-1][0] == reverse('inscriptions:eleve_list')
    assert 'Accès refusé' in hors.content.decode()


# ── Détail : situation financière et historique ─────────────────────────────

def test_transfert_detail_resume_le_dossier(ecole):
    """Le détail chiffre ce qui est payé, ce qui reste dû et rappelle le cursus de l'élève."""
    transfert = _transfert(ecole)
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=ecole['etab'], nom='Scolarité',
                          code='SCOL', actif=True)
    statut_eleve = baker.make('parametres.StatutEleve', etablissement=ecole['etab'], nom='Affecté')
    baker.make('finances.Paiement', inscription=ecole['inscription'], montant=Decimal('30000'),
               rubrique=rubrique, statut_eleve=statut_eleve, numero_recu='R-T1',
               date_paiement=date(2026, 10, 5), mode_paiement='ESPECES')
    baker.make('finances.Echeancier', inscription=ecole['inscription'], libelle='2e tranche',
               date_limite=date(2026, 12, 31), montant_du=Decimal('20000'))
    baker.make('finances.Echeancier', inscription=ecole['inscription'], libelle='1re tranche',
               date_limite=date(2026, 9, 30), montant_du=Decimal('25000'), paye=True)

    reponse = ecole['client'].get(reverse('inscriptions:transfert_inter_detail',
                                          kwargs={'pk': transfert.pk}))
    assert reponse.status_code == 200
    assert reponse.context['total_paye'] == Decimal('30000')
    assert reponse.context['total_du'] == Decimal('20000'), 'une échéance réglée n’est plus due'
    assert list(reponse.context['inscriptions_historique']) == [ecole['inscription']]
    assert reponse.context['can_approve'] is True


def test_transfert_hors_etablissement_est_renvoye(ecole):
    """Un transfert d'une autre école n'est ni consultable ni actionnable."""
    autre_etab = baker.make('etablissements.Etablissement', nom='AILLEURS')
    ailleurs = baker.make(Inscription, annee_scolaire=ecole['annee'], eleve__photo='',
                          classe=baker.make('parametres.Classe', etablissement=autre_etab, nom='6e A'))
    transfert = baker.make(TransfertEleve, inscription=ailleurs, etablissement_destination='Ici')

    detail = ecole['client'].get(reverse('inscriptions:transfert_inter_detail',
                                         kwargs={'pk': transfert.pk}), follow=True)
    assert detail.redirect_chain[-1][0] == reverse('inscriptions:transfert_inter_list')
    assert 'Accès refusé' in detail.content.decode()

    for nom in ('transfert_inter_approuver', 'transfert_inter_refuser'):
        refus = ecole['client'].post(reverse(f'inscriptions:{nom}', kwargs={'pk': transfert.pk}),
                                     follow=True)
        assert refus.redirect_chain[-1][0] == reverse('inscriptions:transfert_inter_list')
        assert 'Accès refusé' in refus.content.decode()
    dossier = ecole['client'].get(reverse('inscriptions:transfert_inter_dossier_pdf',
                                          kwargs={'pk': transfert.pk}), follow=True)
    assert dossier.redirect_chain[-1][0] == reverse('inscriptions:transfert_inter_list')
    transfert.refresh_from_db()
    assert transfert.statut == 'EN_ATTENTE'


# ── Approbation et refus ────────────────────────────────────────────────────

def test_transfert_approuve_cloture_le_dossier_et_trace_le_parcours(ecole):
    """Approuver marque l'inscription en abandon, met à jour l'élève et écrit l'événement de parcours."""
    transfert = _transfert(ecole)
    reponse = ecole['client'].post(reverse('inscriptions:transfert_inter_approuver',
                                           kwargs={'pk': transfert.pk}),
                                   {'notes_admin': 'Dossier complet, quitus remis.'})

    transfert.refresh_from_db()
    ecole['inscription'].refresh_from_db()
    ecole['eleve'].refresh_from_db()
    assert reponse.status_code == 302
    assert transfert.statut == 'APPROUVE' and transfert.traite_par == ecole['directeur']
    assert transfert.date_traitement == date.today()
    assert transfert.notes_admin.startswith('Dossier complet')
    assert ecole['inscription'].statut == 'ABANDON'

    evenement = EvenementParcours.objects.get(eleve=ecole['eleve'])
    assert evenement.type_evenement == EvenementParcours.TypeEvenement.TRANSFERT_SORTANT
    assert evenement.etablissement_transfert == 'Lycée Bogodogo'
    assert evenement.inscription == ecole['inscription']
    assert evenement.enregistre_par == ecole['directeur']
    assert ecole['eleve'].last_classe == '3e A' and ecole['eleve'].last_annee == '2026-2027'


def test_transfert_deja_traite_ne_se_rejoue_pas(ecole):
    """Un transfert approuvé ne peut plus être approuvé ni refusé : le dossier reste clos."""
    transfert = _transfert(ecole, statut='APPROUVE', date_traitement=date(2026, 10, 20))
    for nom in ('transfert_inter_approuver', 'transfert_inter_refuser'):
        reponse = ecole['client'].post(reverse(f'inscriptions:{nom}', kwargs={'pk': transfert.pk}),
                                       follow=True)
        assert 'déjà été traité' in reponse.content.decode()
    transfert.refresh_from_db()
    assert transfert.statut == 'APPROUVE'
    assert not EvenementParcours.objects.exists()


def test_transfert_refuse_laisse_l_eleve_inscrit(ecole):
    """Un refus documente le motif et ne touche ni au statut de l'élève ni à son parcours."""
    transfert = _transfert(ecole)
    rapport = ecole['client'].post(reverse('inscriptions:transfert_inter_refuser',
                                           kwargs={'pk': transfert.pk}),
                                   {'notes_admin': 'Place disponible en 4e à la rentrée.'})
    assert rapport.status_code == 302
    transfert.refresh_from_db()
    ecole['inscription'].refresh_from_db()
    assert transfert.statut == 'REFUSE' and transfert.traite_par == ecole['directeur']
    assert transfert.notes_admin.startswith('Place disponible')
    assert ecole['inscription'].statut == 'AFFECTE', "l'élève reste inscrit"
    assert not EvenementParcours.objects.exists()


def test_transfert_refuse_sans_droit_est_bloque(ecole, mocker):
    """Sans l'action « décider un transfert », approuver et refuser sont refusés avec un message."""
    mocker.patch.object(vues_transferts, 'autorise_url', return_value=False)
    transfert = _transfert(ecole)

    approbation = ecole['client'].post(reverse('inscriptions:transfert_inter_approuver',
                                               kwargs={'pk': transfert.pk}), follow=True)
    assert 'les droits pour approuver' in approbation.content.decode()
    refus = ecole['client'].post(reverse('inscriptions:transfert_inter_refuser',
                                         kwargs={'pk': transfert.pk}), follow=True)
    assert 'les droits pour refuser' in refus.content.decode()
    transfert.refresh_from_db()
    assert transfert.statut == 'EN_ATTENTE'


# ── Dossier PDF ─────────────────────────────────────────────────────────────

def test_dossier_transfert_pdf_reprend_l_eleve_et_ses_sommes(ecole, mocker):
    """Le dossier PDF part à l'établissement d'accueil : identité, cursus et montants y figurent."""
    transfert = _transfert(ecole, statut='APPROUVE', date_traitement=date(2026, 10, 20))
    statut_eleve = baker.make('parametres.StatutEleve', etablissement=ecole['etab'], nom='Affecté')
    baker.make('finances.Paiement', inscription=ecole['inscription'], montant=Decimal('45000'),
               statut_eleve=statut_eleve, numero_recu='R-PDF', date_paiement=date(2026, 10, 5),
               mode_paiement='ESPECES')
    moteur = mocker.patch.object(vues_transferts, '_WeasyHTML')
    moteur.return_value.write_pdf.return_value = b'%PDF-1.4 dossier'

    reponse = ecole['client'].get(reverse('inscriptions:transfert_inter_dossier_pdf',
                                          kwargs={'pk': transfert.pk}))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert reponse.content == b'%PDF-1.4 dossier'
    assert 'Dossier_Transfert_OUEDRAOGO_Awa.pdf' in reponse['Content-Disposition']
    html = moteur.call_args.kwargs['string']
    assert 'OUEDRAOGO' in html and 'Lycée Bogodogo' in html and '45' in html


def test_dossier_transfert_pdf_sans_moteur_previent(ecole, mocker):
    """Sans WeasyPrint, le dossier renvoie au transfert avec un message clair."""
    transfert = _transfert(ecole)
    mocker.patch.object(vues_transferts, '_WeasyHTML', None)
    reponse = ecole['client'].get(reverse('inscriptions:transfert_inter_dossier_pdf',
                                          kwargs={'pk': transfert.pk}), follow=True)
    assert reponse.redirect_chain[-1][0] == reverse('inscriptions:transfert_inter_detail',
                                                   kwargs={'pk': transfert.pk})
    assert 'WeasyPrint' in reponse.content.decode()


def test_transfert_list_sans_etablissement_est_vide(ecole):
    """Un compte sans établissement ne voit aucun transfert : la liste n'est pas une fuite globale."""
    _transfert(ecole)
    ecole['directeur'].etablissement = None
    ecole['directeur'].save(update_fields=['etablissement'])
    reponse = ecole['client'].get(reverse('inscriptions:transfert_inter_list'))
    assert reponse.status_code == 200
    assert list(reponse.context['page_obj']) == []
