"""Bulletins de compétences : fonctionnalité réservée au Préscolaire et au Primaire.

L'évaluation par compétences (API au primaire, APC au préscolaire) ne concerne pas les enseignants du
secondaire : le post-primaire et le secondaire restent notés sur 20. L'entrée de menu et les quatre
écrans (sélecteur, référentiel, saisie, bulletin) suivent ce périmètre.
"""
import pytest
from django.urls import reverse
from model_bakery import baker

pytestmark = pytest.mark.django_db

MENU = 'Bulletins compétences'


def _etablissement(codes):
    """Établissement doté des cycles demandés (Préscolaire/Primaire/Post-primaire/Secondaire)."""
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classes = {}
    for ordre, code in enumerate(('PRES', 'PRIM', 'POST', 'SEC'), start=1):
        if code in codes:
            cycle = baker.make('parametres.Cycle', etablissement=etab, code=code, nom=code, ordre=ordre)
            classes[code] = baker.make('parametres.Classe', etablissement=etab, cycle=cycle,
                                       nom=f'Classe {code}', niveau=code)
    return etab, annee, classes


def _enseignant(client, etab, annee, classes_enseignees, email='prof@ecole.bf'):
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab, email=email)
    for classe in classes_enseignees:
        baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe, personnel=prof, est_actif=True)
    client.force_login(baker.make('accounts.User', etablissement=etab, role='ENSEIGNANT', email=email,
                                  must_change_password=False))
    return client


def _direction(client, etab):
    client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR',
                                  must_change_password=False, est_tous_cycles=True))
    return client


def _cycles_du_selecteur(client):
    reponse = client.get(reverse('pedagogie:competences_index'))
    assert reponse.status_code == 200
    return sorted(reponse.context['cycles'].values_list('code', flat=True))


def _menu_competences(client):
    return MENU in client.get(reverse('core:home')).content.decode()


# ── Enseignant ────────────────────────────────────────────────────────────────────────────────

def test_enseignant_du_secondaire_ne_voit_pas_la_fonctionnalite(client):
    """Un professeur du secondaire ne doit ni voir l'entrée de menu, ni atteindre les écrans."""
    etab, annee, classes = _etablissement({'PRIM', 'SEC'})
    c = _enseignant(client, etab, annee, [classes['SEC']])

    assert not _menu_competences(c)
    assert _cycles_du_selecteur(c) == []
    for code in ('SEC', 'PRIM'):      # ni sa classe, ni celle du primaire où il n'enseigne pas
        url = reverse('pedagogie:competences_saisie', kwargs={'classe_id': classes[code].pk})
        assert c.get(url).status_code == 404


def test_enseignant_du_primaire_conserve_la_fonctionnalite(client):
    etab, annee, classes = _etablissement({'PRIM', 'SEC'})
    c = _enseignant(client, etab, annee, [classes['PRIM']])

    assert _menu_competences(c)
    assert _cycles_du_selecteur(c) == ['PRIM']
    assert c.get(reverse('pedagogie:competences_saisie',
                         kwargs={'classe_id': classes['PRIM'].pk})).status_code == 200


def test_enseignant_primaire_ne_saisit_pas_les_competences_d_un_collegue(client):
    etab, annee, classes = _etablissement({'PRIM'})
    collegue = baker.make('personnel.MembrePersonnel', etablissement=etab, email='collegue@ecole.bf')
    baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classes['PRIM'], personnel=collegue,
               est_actif=True)
    c = _enseignant(client, etab, annee, [])       # aucune classe à lui

    assert _cycles_du_selecteur(c) == []
    assert c.get(reverse('pedagogie:competences_saisie',
                         kwargs={'classe_id': classes['PRIM'].pk})).status_code == 404


# ── Direction ────────────────────────────────────────────────────────────────────────────────

def test_direction_d_un_etablissement_du_secondaire_ne_voit_pas_la_fonctionnalite(client):
    etab, _annee, classes = _etablissement({'POST', 'SEC'})
    c = _direction(client, etab)

    assert not _menu_competences(c)
    assert _cycles_du_selecteur(c) == []
    assert c.get(reverse('pedagogie:competences_saisie',
                         kwargs={'classe_id': classes['SEC'].pk})).status_code == 404


def test_direction_d_un_etablissement_mixte_ne_voit_que_prescolaire_et_primaire(client):
    etab, _annee, _classes = _etablissement({'PRES', 'PRIM', 'SEC'})
    c = _direction(client, etab)

    assert _menu_competences(c)
    assert _cycles_du_selecteur(c) == ['PRES', 'PRIM']


# ── Référentiel et bulletin ──────────────────────────────────────────────────────────────────

def test_referentiel_d_un_cycle_du_secondaire_est_introuvable(client):
    etab, _annee, classes = _etablissement({'SEC'})
    c = _direction(client, etab)

    cycle_id = classes['SEC'].cycle_id
    assert c.get(reverse('pedagogie:competences_referentiel', kwargs={'cycle_id': cycle_id})).status_code == 404


def test_bulletin_de_competences_d_un_eleve_du_secondaire_est_introuvable(client, mocker):
    etab, annee, classes = _etablissement({'PRIM', 'SEC'})
    mocker.patch('pedagogie.views.competences.HTML')   # WeasyPrint absent du poste de test
    c = _direction(client, etab)
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1)
    inscription = baker.make('inscriptions.Inscription', classe=classes['SEC'], annee_scolaire=annee)

    url = reverse('pedagogie:competences_bulletin_pdf',
                  kwargs={'inscription_id': inscription.pk, 'trimestre_id': trimestre.pk})
    assert c.get(url).status_code == 404
