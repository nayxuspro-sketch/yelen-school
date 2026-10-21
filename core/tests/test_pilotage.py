"""Tableau de bord direction : recouvrement, impayés par classe, effectifs, absences, élèves à risque."""
import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from core.pilotage import tableau_de_bord

AUJOURDHUI = datetime.date(2026, 10, 21)


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement', nom='LE SAVOIR')


@pytest.fixture
def annee(etab):
    return baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                      date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2027, 7, 15))


def _connecter(client, etab, role):
    user = baker.make('accounts.User', role=role, etablissement=etab, must_change_password=False)
    client.force_login(user)
    return user


@pytest.fixture
def donnees(etab, annee):
    """Deux classes tarifées : 6e A (3 élèves, 50 000) et 3e C (2 élèves, 80 000)."""
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Externe')
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité')
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Post-primaire', code='PP', ordre=1, actif=True)
    classes, inscriptions = {}, {}
    for nom, tarif, eleves in (('6e A', 50000, (('Ouedraogo', 'M'), ('Kabore', 'F'), ('Sawadogo', 'F'))),
                               ('3e C', 80000, (('Traore', 'M'), ('Zongo', 'M')))):
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau=nom[:2], nom=nom, capacite_max=40)
        baker.make('parametres.TarifScolarite', etablissement=etab, annee_scolaire=annee, cycle=cycle, classe=classe,
                   statut_eleve=statut, rubrique=rubrique, montant=Decimal(tarif), actif=True)
        classes[nom] = classe
        for n, genre in eleves:
            inscriptions[n] = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut='AFFECTE',
                                         statut_eleve=statut, est_redoublant=(n == 'Zongo'),
                                         eleve=baker.make('inscriptions.Eleve', nom=n, prenom='Awa', genre=genre))
    # Abandon (hors effectif, hors attendu) et élève d'un autre établissement (invisible)
    baker.make('inscriptions.Inscription', classe=classes['6e A'], annee_scolaire=annee, statut='ABANDON', statut_eleve=statut)
    autre = baker.make('inscriptions.Inscription', annee_scolaire=annee, classe__etablissement=baker.make('etablissements.Etablissement'))
    # Paiements : 6e A → 50 000 + 20 000 + 0 ; 3e C → 80 000 + 0
    for n, montant in (('Ouedraogo', 50000), ('Kabore', 20000), ('Traore', 80000)):
        baker.make('finances.Paiement', inscription=inscriptions[n], montant=Decimal(montant), rubrique=rubrique)
    # Absences : Sawadogo aujourd'hui + il y a 10 j ; Zongo il y a 3 j ; Traore il y a 60 j (hors 30 j) ; autre étab aujourd'hui
    for n, delta in (('Sawadogo', 0), ('Sawadogo', 10), ('Zongo', 3), ('Traore', 60)):
        ins = inscriptions[n]
        appel = baker.make('presences.Appel', classe=ins.classe, annee_scolaire=annee, date=AUJOURDHUI - datetime.timedelta(days=delta))
        baker.make('presences.Presence', appel=appel, inscription=ins, statut='ABSENT')
        baker.make('presences.Presence', appel=appel, inscription=inscriptions['Ouedraogo' if n != 'Ouedraogo' else 'Kabore'], statut='PRESENT')
    appel_autre = baker.make('presences.Appel', classe=autre.classe, annee_scolaire=annee, date=AUJOURDHUI)
    baker.make('presences.Presence', appel=appel_autre, inscription=autre, statut='ABSENT')
    baker.make('presences.Justification', inscription=inscriptions['Sawadogo'], statut='EN_ATTENTE',
               date_debut=AUJOURDHUI, date_fin=AUJOURDHUI, motif='Maladie')
    # Risques : un critique, un élevé, un faible ; un critique dans l'autre établissement
    for n, score in (('Sawadogo', 90), ('Zongo', 60), ('Ouedraogo', 10)):
        baker.make('pedagogie.RisqueDecrochage', inscription=inscriptions[n], score=score,
                   niveau=__import__('pedagogie.models', fromlist=['RisqueDecrochage']).RisqueDecrochage.niveau_pour_score(score),
                   facteurs=[{'libelle': 'Absences répétées', 'points': 30}])
    baker.make('pedagogie.RisqueDecrochage', inscription=autre, score=95, niveau='CRITIQUE', facteurs=[])
    return classes, inscriptions


@pytest.mark.django_db
def test_indicateurs(etab, annee, donnees):
    tb = tableau_de_bord(etab, annee, aujourdhui=AUJOURDHUI)

    # Recouvrement : attendu 3×50 000 + 2×80 000 = 310 000 ; encaissé 150 000 ; reste 160 000 → 48,4 %
    assert tb['recouvrement'] == {
        'attendu': Decimal('310000'), 'encaisse': Decimal('150000'), 'reste': Decimal('160000'),
        'taux': 48.4, 'redevables': 3, 'sans_tarif': 0,
    }
    # Impayés par classe : 3e C (80 000, 1 redevable) avant 6e A (80 000, 2 redevables) → égalité → ordre alphabétique
    assert [(l['classe'].nom, l['effectif'], l['redevables'], l['reste'], l['taux']) for l in tb['impayes']] == [
        ('3e C', 2, 1, Decimal('80000'), 50.0), ('6e A', 3, 2, Decimal('80000'), 46.7),
    ]
    # Effectifs
    eff = tb['effectifs']
    assert (eff['total'], eff['garcons'], eff['filles'], eff['redoublants'], eff['abandons'], eff['classes']) == (5, 3, 2, 1, 1, 2)
    assert (eff['capacite'], eff['taux_remplissage']) == (80, 6.2)
    assert [(c['cycle'].nom, c['classes'], c['garcons'], c['filles'], c['total']) for c in eff['cycles']] == [('Post-primaire', 2, 3, 2, 5)]
    # Absences : aujourd'hui 1 ; 7 j 2 ; 30 j 3 sur 6 pointages → 50 % ; l'autre établissement est ignoré
    ab = tb['absences']
    assert (ab['aujourdhui'], ab['sept_jours'], ab['trente_jours'], ab['taux_30j'], ab['justifications_attente']) == (1, 2, 3, 50.0, 1)
    assert [(c['appel__classe__nom'], c['nb'], c['eleves']) for c in ab['classes']] == [('6e A', 2, 1), ('3e C', 1, 1)]
    assert [(e['inscription__eleve__nom'], e['nb']) for e in ab['eleves']] == [('Sawadogo', 2), ('Traore', 1), ('Zongo', 1)]
    # Risques : critique 1, élevé 1, modéré 0, faible 1 ; prioritaires triés par score
    ri = tb['risque']
    assert [(n['code'], n['libelle'], n['nb']) for n in ri['niveaux']] == [
        ('CRITIQUE', 'Critique', 1), ('ELEVE', 'Élevé', 1), ('MODERE', 'Modéré', 0), ('FAIBLE', 'Faible', 1)]
    assert ri['prioritaires_nb'] == 2
    assert [(r.inscription.eleve.nom, r.score) for r in ri['prioritaires']] == [('Sawadogo', 90), ('Zongo', 60)]
    assert ri['date_calcul'] is not None


@pytest.mark.django_db
def test_page_direction(client, etab, annee, donnees):
    _connecter(client, etab, 'DIRECTEUR')

    response = client.get(reverse('core:pilotage'))

    assert response.status_code == 200
    html = response.content.decode()
    for bloc in ('Impayés par classe', 'Effectifs par cycle', 'Absences', 'Élèves à risque de décrochage', 'Imprimer'):
        assert bloc in html
    assert '48 %' in html and '160\xa0000' in html and '310\xa0000' in html  # intcomma (fr) : séparateur insécable
    assert 'SAWADOGO Awa' in html and '90/100' in html and 'Absences répétées' in html
    assert response.context['annee_selectionnee'] == annee


@pytest.mark.django_db
def test_annee_choisie_et_annee_invalide(client, etab, annee):
    _connecter(client, etab, 'CENSEUR')
    ancienne = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026', est_courante=False,
                          date_debut=datetime.date(2025, 10, 1), date_fin=datetime.date(2026, 7, 15))

    assert client.get(reverse('core:pilotage'), {'annee_id': ancienne.pk}).context['annee_selectionnee'] == ancienne
    assert client.get(reverse('core:pilotage'), {'annee_id': 'xyz'}).context['annee_selectionnee'] == annee


@pytest.mark.django_db
def test_sans_annee_scolaire(client, etab):
    _connecter(client, etab, 'DIRECTEUR')

    response = client.get(reverse('core:pilotage'))

    assert response.status_code == 200 and 'Aucune année scolaire' in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['COMPTABLE', 'ENSEIGNANT', 'AVS'])
def test_acces_refuse_hors_direction(client, etab, annee, role):
    _connecter(client, etab, role)

    for url in (reverse('core:pilotage'), reverse('core:audit_log_list')):
        response = client.get(url)
        assert response.status_code == 200 and 'Accès refusé' in response.content.decode()
        assert 'Impayés par classe' not in response.content.decode()


@pytest.mark.django_db
def test_menu_pilotage_reserve_direction(client, etab, annee):
    _connecter(client, etab, 'DIRECTEUR')
    assert 'data-url="/pilotage/"' in client.get('/').content.decode()

    _connecter(client, etab, 'COMPTABLE')
    assert 'data-url="/pilotage/"' not in client.get('/').content.decode()


@pytest.mark.django_db
def test_accueil_direction_limite_a_l_etablissement(client, etab, annee):
    """Personnel et absences du jour du tableau de bord d'accueil ne comptent que l'établissement de l'utilisateur."""
    _connecter(client, etab, 'DIRECTEUR')
    baker.make('personnel.MembrePersonnel', etablissement=etab)
    autre = baker.make('etablissements.Etablissement')
    baker.make('personnel.MembrePersonnel', etablissement=autre)
    baker.make('presences.Presence', statut='ABSENT', appel__date=datetime.date.today(), appel__classe__etablissement=autre)

    context = client.get('/').context

    assert context['total_personnel'] == 1 and context['nb_absences_aujourd_hui'] == 0
