"""
Examens officiels — parcours complet (session → centres → salles → inscription → placement → résultats → exports)
et cloisonnement par établissement (Lot J).
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.urls import reverse
from model_bakery import baker

from examens.models import CentreExamen, InscriptionExamen, PlacementExamen, SalleExamen, SessionExamen

pytestmark = pytest.mark.django_db


@pytest.fixture
def monde(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR', code='SAV')
    autre = baker.make('etablissements.Etablissement', nom='AUTRE', code='AUT')
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    annee_autre = baker.make('parametres.AnneeScolaire', etablissement=autre, libelle='2026-2027 bis', est_courante=True,
                             date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='3e A', actif=True)
    eleves = [
        baker.make('inscriptions.Eleve', nom='TRAORE', prenom='Awa', genre='F', photo='', date_naissance=date(2011, 3, 4)),
        baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Issa', genre='M', photo='', date_naissance=date(2011, 5, 6)),
        baker.make('inscriptions.Eleve', nom='ZONGO', prenom='Ali', genre='M', photo='', date_naissance=date(2010, 7, 8)),
    ]
    inscriptions = [baker.make('inscriptions.Inscription', eleve=e, classe=classe, annee_scolaire=annee, statut='ACTIF')
                    for e in eleves]
    baker.make('inscriptions.Inscription', eleve=baker.make('inscriptions.Eleve', nom='PARTI', prenom='Loin', photo='',
                                                             date_naissance=date(2011, 1, 1)),
               classe=classe, annee_scolaire=annee, statut='ABANDON')
    session = baker.make(SessionExamen, annee_scolaire=annee, type_examen='BEPC', libelle='BEPC 2027',
                         date_debut=date(2027, 6, 1), date_fin=date(2027, 6, 4), statut='PLANIFIEE')
    centre = baker.make(CentreExamen, session=session, nom='Centre Nord', code_centre='CN01', capacite=100)
    salle = baker.make(SalleExamen, centre=centre, nom='Salle 1', capacite=2)
    # Un autre établissement, avec sa propre session complète
    session_autre = baker.make(SessionExamen, annee_scolaire=annee_autre, type_examen='BEPC', libelle='BEPC ailleurs',
                               date_debut=date(2027, 6, 1), date_fin=date(2027, 6, 4))
    centre_autre = baker.make(CentreExamen, session=session_autre, nom='Centre Sud', code_centre='CS01', capacite=50)
    salle_autre = baker.make(SalleExamen, centre=centre_autre, nom='Salle X', capacite=10)
    classe_autre = baker.make('parametres.Classe', etablissement=autre, nom='3e Z', actif=True)
    insc_autre = baker.make('inscriptions.Inscription', classe=classe_autre, annee_scolaire=annee_autre, statut='ACTIF',
                            eleve=baker.make('inscriptions.Eleve', nom='AILLEURS', prenom='Moussa', photo='',
                                             date_naissance=date(2011, 1, 1)))
    candidat_autre = baker.make(InscriptionExamen, session=session_autre, inscription=insc_autre, centre=centre_autre)
    placement_autre = baker.make(PlacementExamen, salle=salle_autre, candidat=candidat_autre, numero_place=1)
    return SimpleNamespace(client=client, user=user, etab=etab, autre=autre, annee=annee, annee_autre=annee_autre,
                           classe=classe, inscriptions=inscriptions, session=session, centre=centre, salle=salle,
                           session_autre=session_autre, centre_autre=centre_autre, salle_autre=salle_autre,
                           classe_autre=classe_autre, placement_autre=placement_autre)


def _inscrire(m, centre=None):
    """Inscrit la classe à la session (via la vue) et renvoie les candidats triés par nom."""
    donnees = {'centre': str(centre.pk)} if centre else {}
    reponse = m.client.post(reverse('examens:inscrire_classe', args=[m.session.pk, m.classe.pk]), donnees)
    assert reponse.status_code == 302
    return list(InscriptionExamen.objects.filter(session=m.session).order_by('inscription__eleve__nom'))


def _texte_messages(reponse):
    return ' '.join(str(msg) for msg in reponse.context['messages'])


# ── Sessions ─────────────────────────────────────────────────────────────────

def test_le_formulaire_de_session_ne_propose_que_les_annees_de_l_etablissement(monde):
    reponse = monde.client.get(reverse('examens:session_create'))
    choix = list(reponse.context['form'].fields['annee_scolaire'].queryset)
    assert choix == [monde.annee]
    reponse = monde.client.post(reverse('examens:session_create'), {
        'annee_scolaire': str(monde.annee_autre.pk), 'type_examen': 'CEP', 'libelle': 'CEP ailleurs',
        'date_debut': '2027-06-10', 'date_fin': '2027-06-11', 'statut': 'PLANIFIEE',
    })
    assert reponse.status_code == 200 and 'annee_scolaire' in reponse.context['form'].errors
    assert not SessionExamen.objects.filter(libelle='CEP ailleurs').exists()


def test_creation_puis_modification_d_une_session(monde):
    reponse = monde.client.post(reverse('examens:session_create'), {
        'annee_scolaire': str(monde.annee.pk), 'type_examen': 'CEP', 'libelle': 'CEP 2027',
        'date_debut': '2027-06-10', 'date_fin': '2027-06-11', 'statut': 'PLANIFIEE',
    })
    session = SessionExamen.objects.get(libelle='CEP 2027')
    assert reponse.status_code == 302 and reponse.url == reverse('examens:session_detail', args=[session.pk])
    reponse = monde.client.post(reverse('examens:session_edit', args=[session.pk]), {
        'annee_scolaire': str(monde.annee.pk), 'type_examen': 'CEP', 'libelle': 'CEP 2027 — session unique',
        'date_debut': '2027-06-10', 'date_fin': '2027-06-12', 'statut': 'EN_COURS',
    })
    session.refresh_from_db()
    assert reponse.status_code == 302 and session.libelle == 'CEP 2027 — session unique' and session.statut == 'EN_COURS'


def test_une_date_de_fin_anterieure_au_debut_est_refusee(monde):
    reponse = monde.client.post(reverse('examens:session_create'), {
        'annee_scolaire': str(monde.annee.pk), 'type_examen': 'BAC', 'libelle': 'BAC 2027',
        'date_debut': '2027-06-10', 'date_fin': '2027-06-09', 'statut': 'PLANIFIEE',
    })
    assert reponse.status_code == 200
    assert 'postérieure à la date de début' in reponse.context['form'].errors['date_fin'][0]
    assert not SessionExamen.objects.filter(libelle='BAC 2027').exists()


def test_la_liste_des_sessions_est_limitee_a_l_etablissement(monde):
    html = monde.client.get(reverse('examens:session_list')).content.decode()
    assert 'BEPC 2027' in html and 'BEPC ailleurs' not in html


def test_detail_de_session_propose_les_classes_de_l_annee(monde):
    reponse = monde.client.get(reverse('examens:session_detail', args=[monde.session.pk]))
    assert reponse.status_code == 200
    assert list(reponse.context['classes']) == [monde.classe]


# ── Inscription des candidats ────────────────────────────────────────────────

def test_inscrire_une_classe_ignore_les_abandons_et_ne_duplique_pas(monde):
    candidats = _inscrire(monde, centre=monde.centre)
    assert [c.inscription.eleve.nom for c in candidats] == ['OUEDRAOGO', 'TRAORE', 'ZONGO']
    assert all(c.centre == monde.centre and c.statut == 'INSCRIT' for c in candidats)
    # Une seconde inscription de la même classe n'ajoute personne
    reponse = monde.client.post(reverse('examens:inscrire_classe', args=[monde.session.pk, monde.classe.pk]), follow=True)
    assert '0 élève(s) inscrit(s)' in _texte_messages(reponse)
    assert InscriptionExamen.objects.filter(session=monde.session).count() == 3


def test_inscrire_une_classe_affiche_les_deja_inscrits(monde):
    _inscrire(monde)
    reponse = monde.client.get(reverse('examens:inscrire_classe', args=[monde.session.pk, monde.classe.pk]))
    assert reponse.status_code == 200
    assert reponse.context['deja_inscrits'] == {i.pk for i in monde.inscriptions}


def test_inscrire_une_classe_d_un_autre_etablissement_est_impossible(monde):
    assert monde.client.post(reverse('examens:inscrire_classe', args=[monde.session.pk, monde.classe_autre.pk])).status_code == 404
    # Un centre d'une autre session ne peut pas être affecté
    reponse = monde.client.post(reverse('examens:inscrire_classe', args=[monde.session.pk, monde.classe.pk]),
                                {'centre': str(monde.centre_autre.pk)})
    assert reponse.status_code == 404 and not InscriptionExamen.objects.filter(session=monde.session).exists()


# ── Centres et salles ────────────────────────────────────────────────────────

def test_cycle_de_vie_d_un_centre_et_d_une_salle(monde):
    c = monde.client
    reponse = c.post(reverse('examens:centre_create', args=[monde.session.pk]),
                     {'nom': 'Lycée Municipal', 'code_centre': 'LM02', 'adresse': 'Secteur 12', 'capacite': '80'})
    centre = CentreExamen.objects.get(code_centre='LM02')
    assert reponse.status_code == 302 and centre.session == monde.session
    reponse = c.post(reverse('examens:centre_edit', args=[centre.pk]),
                     {'nom': 'Lycée Municipal de Ouaga', 'code_centre': 'LM02', 'adresse': '', 'capacite': '90'})
    centre.refresh_from_db()
    assert reponse.status_code == 302 and centre.nom == 'Lycée Municipal de Ouaga' and centre.capacite == 90

    reponse = c.post(reverse('examens:salle_create', args=[centre.pk]), {'nom': 'Salle A', 'capacite': '30'})
    salle = SalleExamen.objects.get(centre=centre, nom='Salle A')
    assert reponse.status_code == 302 and salle.capacite == 30
    reponse = c.post(reverse('examens:salle_edit', args=[salle.pk]), {'nom': 'Salle A1', 'capacite': '25'})
    salle.refresh_from_db()
    assert reponse.status_code == 302 and salle.nom == 'Salle A1' and salle.capacite == 25

    assert c.post(reverse('examens:salle_delete', args=[salle.pk])).status_code == 302
    assert not SalleExamen.objects.filter(pk=salle.pk).exists()
    assert c.post(reverse('examens:centre_delete', args=[centre.pk])).status_code == 302
    assert not CentreExamen.objects.filter(pk=centre.pk).exists()


# ── Placement en salle ───────────────────────────────────────────────────────

def test_le_placement_manuel_respecte_la_capacite_de_la_salle(monde):
    candidats = _inscrire(monde, centre=monde.centre)
    reponse = monde.client.post(reverse('examens:placement_salle', args=[monde.salle.pk]),
                                {'action': 'placer', 'candidat_ids': [str(c.pk) for c in candidats]}, follow=True)
    assert '2 candidat(s) placé(s)' in _texte_messages(reponse)
    assert PlacementExamen.objects.filter(salle=monde.salle).count() == 2
    assert reponse.context['places_restantes'] == 0 and len(reponse.context['non_places']) == 1


def test_le_placement_automatique_puis_le_retrait_d_un_candidat(monde):
    _inscrire(monde, centre=monde.centre)
    reponse = monde.client.post(reverse('examens:placement_salle', args=[monde.salle.pk]), {'action': 'auto'}, follow=True)
    assert '2 candidat(s) assigné(s) automatiquement' in _texte_messages(reponse)
    placement = PlacementExamen.objects.filter(salle=monde.salle).first()
    reponse = monde.client.post(reverse('examens:placement_delete', args=[placement.pk]))
    assert reponse.status_code == 302 and reponse.url == reverse('examens:placement_salle', args=[monde.salle.pk])
    assert PlacementExamen.objects.filter(salle=monde.salle).count() == 1
    # La place libérée est réattribuée au candidat restant
    monde.client.post(reverse('examens:placement_salle', args=[monde.salle.pk]), {'action': 'auto'})
    assert PlacementExamen.objects.filter(salle=monde.salle).count() == 2


def test_un_candidat_d_une_autre_session_ne_peut_pas_etre_place(monde):
    _inscrire(monde, centre=monde.centre)
    reponse = monde.client.post(reverse('examens:placement_salle', args=[monde.salle.pk]),
                                {'action': 'placer', 'candidat_ids': [str(monde.placement_autre.candidat.pk)]})
    assert reponse.status_code == 404 and not PlacementExamen.objects.filter(salle=monde.salle).exists()


# ── Résultats, exports et statistiques ───────────────────────────────────────

def _saisir_resultats(m):
    oued, traore, zongo = _inscrire(m, centre=m.centre)
    donnees = {
        f'statut_{oued.pk}': 'ADMIS', f'moyenne_{oued.pk}': '12,50', f'mention_{oued.pk}': 'Assez Bien',
        f'statut_{traore.pk}': 'ADMIS', f'moyenne_{traore.pk}': '15.00', f'mention_{traore.pk}': 'Bien',
        f'statut_{zongo.pk}': 'AJOURNE', f'moyenne_{zongo.pk}': 'abc',
    }
    reponse = m.client.post(reverse('examens:saisie_resultats', args=[m.session.pk]), donnees, follow=True)
    return reponse, (oued, traore, zongo)


def test_la_saisie_des_resultats_enregistre_statut_moyenne_et_mention(monde):
    reponse, (oued, traore, zongo) = _saisir_resultats(monde)
    oued.refresh_from_db(); traore.refresh_from_db(); zongo.refresh_from_db()
    assert (oued.statut, oued.moyenne_examen, oued.mention) == ('ADMIS', Decimal('12.50'), 'Assez Bien')
    assert (traore.statut, traore.moyenne_examen, traore.mention) == ('ADMIS', Decimal('15.00'), 'Bien')
    assert zongo.statut == 'AJOURNE' and zongo.moyenne_examen is None
    textes = _texte_messages(reponse)
    assert 'Résultats enregistrés.' in textes and 'Moyenne invalide ignorée pour : ZONGO ALI' in textes


def test_export_csv_des_resultats(monde):
    _saisir_resultats(monde)
    reponse = monde.client.get(reverse('examens:session_resultats_csv', args=[monde.session.pk]))
    assert reponse.status_code == 200 and reponse['Content-Type'].startswith('text/csv')
    contenu = reponse.content.decode('utf-8-sig')
    assert 'TRAORE' in contenu and 'Admis' in contenu and 'Ajourn' in contenu


def test_liste_des_candidats_filtree_par_centre_et_export_excel(monde):
    candidats = _inscrire(monde, centre=monde.centre)
    autre_centre = baker.make(CentreExamen, session=monde.session, nom='Centre Est', code_centre='CE02', capacite=20)
    InscriptionExamen.objects.filter(pk=candidats[0].pk).update(centre=autre_centre)
    reponse = monde.client.get(reverse('examens:candidats_session', args=[monde.session.pk]), {'centre': str(monde.centre.pk)})
    assert reponse.status_code == 200
    assert sorted(c.inscription.eleve.nom for c in reponse.context['candidats']) == ['TRAORE', 'ZONGO']
    reponse = monde.client.get(reverse('examens:candidats_session_xlsx', args=[monde.session.pk]), {'centre': str(autre_centre.pk)})
    assert reponse.status_code == 200
    assert reponse['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment' in reponse['Content-Disposition']


def test_pdf_de_la_liste_des_candidats(monde, mocker):
    weasy = mocker.patch('examens.views.WeasyHTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    _inscrire(monde, centre=monde.centre)
    reponse = monde.client.get(reverse('examens:candidats_session_pdf', args=[monde.session.pk]))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    html = weasy.call_args.kwargs['string']
    assert 'TRAORE' in html and 'Centre Nord' in html


def test_statistiques_de_session_a_l_ecran_et_en_pdf(monde, mocker):
    _saisir_resultats(monde)
    reponse = monde.client.get(reverse('examens:session_statistiques', args=[monde.session.pk]))
    assert reponse.status_code == 200
    globale = reponse.context['globale']
    assert (globale['inscrits'], globale['presents'], globale['admis'], globale['ajournes']) == (3, 3, 2, 1)
    assert globale['taux'] == pytest.approx(66.7) and globale['admis_f'] == 1 and globale['admis_g'] == 1
    assert [ligne['libelle'] for ligne in reponse.context['par_mention']] == ['Bien', 'Assez Bien']  # de la meilleure à la moindre
    weasy = mocker.patch('examens.views.WeasyHTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7'
    reponse = monde.client.get(reverse('examens:session_statistiques', args=[monde.session.pk]), {'format': 'pdf'})
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'


# ── Cloisonnement ────────────────────────────────────────────────────────────

@pytest.mark.parametrize('nom_url, cible, methode', [
    ('examens:session_edit', 'session_autre', 'get'),
    ('examens:session_resultats_csv', 'session_autre', 'get'),
    ('examens:candidats_session_pdf', 'session_autre', 'get'),
    ('examens:centre_create', 'session_autre', 'get'),
    ('examens:centre_edit', 'centre_autre', 'get'),
    ('examens:centre_delete', 'centre_autre', 'post'),
    ('examens:salle_create', 'centre_autre', 'get'),
    ('examens:salle_edit', 'salle_autre', 'get'),
    ('examens:salle_delete', 'salle_autre', 'post'),
    ('examens:placement_salle', 'salle_autre', 'get'),
    ('examens:placement_delete', 'placement_autre', 'post'),
])
def test_les_objets_d_un_autre_etablissement_sont_introuvables(monde, nom_url, cible, methode):
    url = reverse(nom_url, args=[getattr(monde, cible).pk])
    assert getattr(monde.client, methode)(url).status_code == 404


def test_inscrire_une_classe_a_la_session_d_un_autre_etablissement_est_introuvable(monde):
    url = reverse('examens:inscrire_classe', args=[monde.session_autre.pk, monde.classe_autre.pk])
    assert monde.client.post(url).status_code == 404
    assert InscriptionExamen.objects.filter(session=monde.session_autre).count() == 1


@pytest.mark.parametrize('nom_url', ['examens:session_detail', 'examens:saisie_resultats', 'examens:candidats_session',
                                     'examens:candidats_session_xlsx', 'examens:session_statistiques'])
def test_les_ecrans_d_une_session_etrangere_renvoient_a_la_liste(monde, nom_url):
    reponse = monde.client.get(reverse(nom_url, args=[monde.session_autre.pk]))
    assert reponse.status_code == 302 and reponse.url == reverse('examens:session_list')


def test_un_utilisateur_sans_etablissement_voit_tout(client, monde):
    client.force_login(baker.make('accounts.User', etablissement=None, is_superuser=True, must_change_password=False))
    assert client.get(reverse('examens:session_edit', args=[monde.session_autre.pk])).status_code == 200
