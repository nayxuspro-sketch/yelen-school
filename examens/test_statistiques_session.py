"""Lot H — statistiques d'une session d'examen ventilées par classe d'origine, sexe, centre, mention et tranche de
moyenne ; taux de réussite = admis / présents ; écran et PDF ; cloisonnement par établissement."""
import html as html_module
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from examens.statistiques import statistiques_session

pytestmark = pytest.mark.django_db


@pytest.fixture
def session(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    s = baker.make('examens.SessionExamen', annee_scolaire=annee, type_examen='BEPC', libelle='BEPC 2027')
    centre_a = baker.make('examens.CentreExamen', session=s, nom='Lycée Zinda', code_centre='ZIN')
    centre_b = baker.make('examens.CentreExamen', session=s, nom='Lycée Bogodogo', code_centre='BOG')
    c3a = baker.make('parametres.Classe', etablissement=etab, nom='3e A', actif=True)
    c3b = baker.make('parametres.Classe', etablissement=etab, nom='3e B', actif=True)

    def candidat(nom, genre, classe, centre, statut, moyenne=None, mention=''):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='X', genre=genre, date_naissance=date(2011, 1, 1), photo='')
        ins = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
        return baker.make('examens.InscriptionExamen', session=s, inscription=ins, centre=centre, statut=statut,
                          moyenne_examen=moyenne, mention=mention)

    candidat('A', 'M', c3a, centre_a, 'ADMIS', Decimal('14.50'), 'Bien')
    candidat('B', 'F', c3a, centre_a, 'ADMIS', Decimal('12.00'), 'Assez bien')
    candidat('C', 'F', c3a, centre_a, 'AJOURNE', Decimal('8.75'))
    candidat('D', 'M', c3a, centre_b, 'ABSENT')
    candidat('E', 'M', c3b, centre_b, 'ADMIS', Decimal('16.25'), 'Très bien')
    candidat('F', 'F', c3b, centre_b, 'EXCLU')
    candidat('G', 'F', c3b, None, 'INSCRIT')
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'annee': annee, 'session': s, 'user': user}


def _cle(ligne, *cles):
    return tuple(ligne[c] for c in cles)


def test_ventilations_et_taux(session):
    st = statistiques_session(session['session'])
    g = st['globale']
    assert _cle(g, 'inscrits', 'presents', 'admis', 'ajournes', 'absents', 'exclus') == (7, 5, 3, 1, 1, 1)
    assert _cle(g, 'inscrits_g', 'presents_g', 'admis_g', 'inscrits_f', 'presents_f', 'admis_f') == (3, 2, 2, 4, 3, 1)
    assert (g['taux'], g['taux_g'], g['taux_f']) == (60.0, 100.0, 33.3), 'admis / présents (absents hors dénominateur)'
    assert g['moyenne'] == Decimal('12.88') and st['non_notes'] == 1

    classes = {l['libelle']: l for l in st['par_classe']}
    assert list(classes) == ['3e A', '3e B']
    assert _cle(classes['3e A'], 'inscrits', 'presents', 'admis', 'taux', 'moyenne') == (4, 3, 2, 66.7, Decimal('11.75'))
    assert _cle(classes['3e B'], 'inscrits', 'presents', 'admis', 'taux', 'moyenne') == (3, 2, 1, 50.0, Decimal('16.25'))

    centres = [(l['libelle'], l['inscrits'], l['admis']) for l in st['par_centre']]
    assert centres == [('Lycée Bogodogo', 3, 1), ('Lycée Zinda', 3, 2), ('Sans centre', 1, 0)]

    assert [(l['libelle'], l['admis']) for l in st['par_mention']] == [('Très bien', 1), ('Bien', 1), ('Assez bien', 1)]
    assert [(t['libelle'], t['nb'], t['taux']) for t in st['tranches']] == [
        ('Moins de 8', 0, 0.0), ('8 à 9,99', 1, 25.0), ('10 à 11,99', 0, 0.0), ('12 à 13,99', 1, 25.0),
        ('14 à 15,99', 1, 25.0), ('16 et plus', 1, 25.0)]
    assert [c.inscription.eleve.nom for c in st['meilleurs']] == ['E', 'A', 'B']
    assert [t for t, _ in st['tableaux']] == ["Par classe d'origine", 'Par centre']


def test_session_vide(session):
    vide = baker.make('examens.SessionExamen', annee_scolaire=session['annee'], type_examen='BAC')
    st = statistiques_session(vide)
    assert (st['globale']['inscrits'], st['globale']['taux'], st['globale']['moyenne']) == (0, 0.0, None)
    assert st['par_classe'] == [] and st['meilleurs'] == [] and all(t['nb'] == 0 for t in st['tranches'])


def test_ecran_et_pdf(client, session, mocker):
    url = reverse('examens:session_statistiques', args=[session['session'].pk])
    page = client.get(url)
    assert page.status_code == 200
    html = page.content.decode()
    assert 'Statistiques' in html and '3e A' in html and 'Lycée Zinda' in html and '60,0' in html and '12,88' in html

    weasy = mocker.patch('examens.views.WeasyHTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-stats'
    pdf = client.get(url + '?format=pdf')
    assert pdf.status_code == 200 and pdf.content == b'%PDF-stats'
    assert pdf['Content-Disposition'] == 'inline; filename="statistiques_BEPC_2027.pdf"'
    source = html_module.unescape(weasy.call_args.kwargs['string'])
    assert 'BEPC 2027' in source and "Par classe d'origine" in source and 'Très bien' in source and '16 et plus' in source


def test_cloisonnement_par_etablissement(client, session):
    autre = baker.make('accounts.User', etablissement=baker.make('etablissements.Etablissement'), role='DIRECTEUR',
                       must_change_password=False)
    client.force_login(autre)
    reponse = client.get(reverse('examens:session_statistiques', args=[session['session'].pk]))
    assert reponse.status_code == 302 and reponse.url == reverse('examens:session_list')
