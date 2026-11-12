"""Isolation des parcours Vie scolaire selon les cycles autorisés du compte."""
from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker

from viescolaire.models import AppelDecision, DecisionConseil, SanctionDisciplinaire


@pytest.fixture
def perimetre_cycles(client):
    etab = baker.make('etablissements.Etablissement')
    primaire = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire')
    secondaire = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    annee = baker.make(
        'parametres.AnneeScolaire', etablissement=etab, est_courante=True,
        libelle='2026-2027', date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30),
    )
    trimestre = baker.make(
        'pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='Trimestre 1',
        date_debut=date(2026, 10, 1), date_fin=date(2026, 12, 31),
    )
    classe_primaire = baker.make(
        'parametres.Classe', etablissement=etab, cycle=primaire,
        nom='CP1', niveau='CP1', actif=True,
    )
    classe_secondaire = baker.make(
        'parametres.Classe', etablissement=etab, cycle=secondaire,
        nom='6e A', niveau='6e', actif=True,
    )
    eleve_primaire = baker.make(
        'inscriptions.Eleve', nom='ELEVEPRIMAIRE', prenom='Awa', photo='',
        date_naissance=date(2017, 1, 1),
    )
    eleve_secondaire = baker.make(
        'inscriptions.Eleve', nom='ELEVSECONDAIRE', prenom='Boureima', photo='',
        date_naissance=date(2012, 1, 1),
    )
    inscription_primaire = baker.make(
        'inscriptions.Inscription', eleve=eleve_primaire, classe=classe_primaire,
        annee_scolaire=annee, statut='ACTIF', is_active=True,
    )
    inscription_secondaire = baker.make(
        'inscriptions.Inscription', eleve=eleve_secondaire, classe=classe_secondaire,
        annee_scolaire=annee, statut='ACTIF', is_active=True,
    )
    conseil_primaire = baker.make(
        'viescolaire.ConseilClasse', classe=classe_primaire, trimestre=trimestre,
        date_conseil=date(2026, 12, 15),
    )
    conseil_secondaire = baker.make(
        'viescolaire.ConseilClasse', classe=classe_secondaire, trimestre=trimestre,
        date_conseil=date(2026, 12, 16),
    )
    decision_primaire = baker.make(
        DecisionConseil, conseil=conseil_primaire, inscription=inscription_primaire,
        decision=DecisionConseil.DecisionChoices.REDOUBLEMENT,
    )
    decision_secondaire = baker.make(
        DecisionConseil, conseil=conseil_secondaire, inscription=inscription_secondaire,
        decision=DecisionConseil.DecisionChoices.REDOUBLEMENT,
    )
    appel_primaire = baker.make(
        AppelDecision, decision_conseil=decision_primaire, motif='Demande primaire',
    )
    appel_secondaire = baker.make(
        AppelDecision, decision_conseil=decision_secondaire, motif='Demande secondaire',
    )
    type_sanction = baker.make(
        'parametres.TypeSanction', code='AVERT', libelle='Avertissement', actif=True,
    )
    sanction_primaire = baker.make(
        SanctionDisciplinaire, inscription=inscription_primaire,
        type_sanction=type_sanction, date_sanction=date(2026, 11, 1), motif='Motif primaire',
    )
    sanction_secondaire = baker.make(
        SanctionDisciplinaire, inscription=inscription_secondaire,
        type_sanction=type_sanction, date_sanction=date(2026, 11, 2), motif='Motif secondaire',
    )
    activite_primaire = baker.make(
        'viescolaire.ActiviteParascolaire', annee_scolaire=annee, nom='Club primaire',
    )
    activite_secondaire = baker.make(
        'viescolaire.ActiviteParascolaire', annee_scolaire=annee, nom='Club secondaire',
    )
    activite_mixte = baker.make(
        'viescolaire.ActiviteParascolaire', annee_scolaire=annee, nom='Club mixte',
    )
    participation_secondaire = baker.make(
        'viescolaire.ParticipationActivite', activite=activite_secondaire,
        inscription=inscription_secondaire, is_active=True,
    )
    baker.make(
        'viescolaire.ParticipationActivite', activite=activite_primaire,
        inscription=inscription_primaire, is_active=True,
    )
    baker.make(
        'viescolaire.ParticipationActivite', activite=activite_mixte,
        inscription=inscription_primaire, is_active=True,
    )
    baker.make(
        'viescolaire.ParticipationActivite', activite=activite_mixte,
        inscription=inscription_secondaire, is_active=True,
    )

    user = baker.make(
        'accounts.User', etablissement=etab, role='DIRECTEUR',
        est_tous_cycles=False, must_change_password=False,
    )
    user.cycles.add(primaire)
    client.force_login(user)
    return {
        'client': client,
        'etab': etab,
        'annee': annee,
        'trimestre': trimestre,
        'classe_primaire': classe_primaire,
        'classe_secondaire': classe_secondaire,
        'inscription_primaire': inscription_primaire,
        'inscription_secondaire': inscription_secondaire,
        'conseil_primaire': conseil_primaire,
        'conseil_secondaire': conseil_secondaire,
        'decision_secondaire': decision_secondaire,
        'appel_primaire': appel_primaire,
        'appel_secondaire': appel_secondaire,
        'sanction_primaire': sanction_primaire,
        'sanction_secondaire': sanction_secondaire,
        'activite_primaire': activite_primaire,
        'activite_secondaire': activite_secondaire,
        'activite_mixte': activite_mixte,
        'participation_secondaire': participation_secondaire,
    }


@pytest.mark.django_db
def test_listes_vie_scolaire_ne_montrent_que_le_cycle_autorise(perimetre_cycles):
    client = perimetre_cycles['client']

    conseils = client.get(reverse('viescolaire:conseil_list'))
    assert list(conseils.context['conseils']) == [perimetre_cycles['conseil_primaire']]

    sanctions = client.get(reverse('viescolaire:sanction_list')).content.decode()
    assert 'ELEVEPRIMAIRE' in sanctions and 'ELEVSECONDAIRE' not in sanctions

    appels = client.get(reverse('viescolaire:appel_decision_list'))
    assert list(appels.context['appels']) == [perimetre_cycles['appel_primaire']]

    fiches = client.get(reverse('viescolaire:fiches_suivi_list')).content.decode()
    assert 'ELEVEPRIMAIRE' in fiches and 'ELEVSECONDAIRE' not in fiches

    capital = client.get(reverse('viescolaire:capital_points_list')).content.decode()
    assert 'ELEVEPRIMAIRE' in capital and 'ELEVSECONDAIRE' not in capital

    activites = client.get(reverse('viescolaire:activite_list')).content.decode()
    assert 'Club primaire' in activites
    assert 'Club secondaire' not in activites and 'Club mixte' not in activites


@pytest.mark.django_db
def test_acces_direct_par_identifiant_refuse_un_autre_cycle(perimetre_cycles):
    client = perimetre_cycles['client']
    assert client.get(reverse(
        'viescolaire:conseil_detail', args=[perimetre_cycles['conseil_secondaire'].pk],
    )).status_code == 404
    assert client.get(reverse(
        'viescolaire:fiche_suivi_eleve', args=[perimetre_cycles['inscription_secondaire'].pk],
    )).status_code == 404
    for nom_url in ('activite_detail', 'activite_edit', 'activite_delete'):
        assert client.get(reverse(
            f'viescolaire:{nom_url}', args=[perimetre_cycles['activite_secondaire'].pk],
        )).status_code == 404
    assert client.get(reverse(
        'viescolaire:activite_detail', args=[perimetre_cycles['activite_mixte'].pk],
    )).status_code == 404
    assert client.get(reverse(
        'viescolaire:conseil_pv_pdf', args=[perimetre_cycles['conseil_secondaire'].pk],
    )).status_code == 404
    assert client.get(reverse(
        'viescolaire:sanction_delete', args=[perimetre_cycles['sanction_secondaire'].pk],
    )).status_code == 404
    assert client.get(reverse(
        'viescolaire:appel_decision_create', args=[perimetre_cycles['decision_secondaire'].pk],
    )).status_code == 404
    assert client.get(reverse(
        'viescolaire:appel_decision_traiter', args=[perimetre_cycles['appel_secondaire'].pk],
    )).status_code == 404


@pytest.mark.django_db
def test_post_vie_scolaire_ne_peut_pas_cibler_un_autre_cycle(perimetre_cycles):
    client = perimetre_cycles['client']
    data = {
        'classe': str(perimetre_cycles['classe_secondaire'].pk),
        'trimestre': str(perimetre_cycles['trimestre'].pk),
        'date_conseil': '2026-12-20',
    }
    assert client.post(reverse('viescolaire:conseil_create'), data).status_code == 404

    n_sanctions = SanctionDisciplinaire.objects.count()
    reponse = client.post(reverse('viescolaire:sanction_create'), {
        'inscription': str(perimetre_cycles['inscription_secondaire'].pk),
        'type_sanction': str(SanctionDisciplinaire.objects.first().type_sanction_id),
        'date_sanction': '2026-11-10',
        'motif': 'Tentative hors cycle',
        'points': '-1',
        'statut': SanctionDisciplinaire.StatutChoices.CONFIRME,
    })
    assert reponse.status_code == 200
    assert SanctionDisciplinaire.objects.count() == n_sanctions

    decision = perimetre_cycles['decision_secondaire']
    client.post(
        reverse('viescolaire:conseil_detail', args=[perimetre_cycles['conseil_primaire'].pk]),
        {'action': 'save_decisions', f'decision_{decision.pk}': DecisionConseil.DecisionChoices.PASSAGE},
    )
    decision.refresh_from_db()
    assert decision.decision == DecisionConseil.DecisionChoices.REDOUBLEMENT

    n_participations = perimetre_cycles['activite_primaire'].participations.count()
    assert client.post(
        reverse('viescolaire:activite_detail', args=[perimetre_cycles['activite_primaire'].pk]),
        {'action': 'inscrire', 'inscription': str(perimetre_cycles['inscription_secondaire'].pk)},
    ).status_code == 404
    assert perimetre_cycles['activite_primaire'].participations.count() == n_participations

    assert client.post(
        reverse('viescolaire:sanction_delete', args=[perimetre_cycles['sanction_secondaire'].pk]),
    ).status_code == 404
    perimetre_cycles['sanction_secondaire'].refresh_from_db()


@pytest.mark.django_db
def test_annees_et_activites_d_autres_etablissements_ne_sont_pas_exposees_sans_etablissement(perimetre_cycles):
    autre_etab = baker.make('etablissements.Etablissement')
    baker.make('parametres.Cycle', etablissement=autre_etab, code='SEC', nom='Autre secondaire')
    autre_annee = baker.make(
        'parametres.AnneeScolaire', etablissement=autre_etab, est_courante=True,
        libelle='2027-2028', date_debut=date(2027, 10, 1), date_fin=date(2028, 6, 30),
    )
    activite_autre = baker.make(
        'viescolaire.ActiviteParascolaire', annee_scolaire=autre_annee, nom='Activité autre école',
    )
    user = baker.make(
        'accounts.User', role='DIRECTEUR', est_tous_cycles=False, must_change_password=False,
    )
    user.cycles.add(perimetre_cycles['classe_primaire'].cycle)
    perimetre_cycles['client'].force_login(user)

    for route in ('viescolaire:conseil_list', 'viescolaire:conseil_create', 'viescolaire:sanction_create'):
        response = perimetre_cycles['client'].get(reverse(route))
        assert response.status_code == 200
        assert list(response.context['trimestres']) == [perimetre_cycles['trimestre']]

    for route in ('viescolaire:fiches_suivi_list', 'viescolaire:capital_points_list'):
        response = perimetre_cycles['client'].get(reverse(route))
        assert response.status_code == 200
        assert list(response.context['annees']) == [perimetre_cycles['annee']]

    activites = perimetre_cycles['client'].get(reverse('viescolaire:activite_list'))
    assert activites.status_code == 200
    assert activite_autre not in activites.context['activites']
    creation = perimetre_cycles['client'].get(reverse('viescolaire:activite_create'))
    assert creation.status_code == 200
    assert creation.context['annee_courante'] == perimetre_cycles['annee']


@pytest.mark.django_db
def test_activite_avec_participation_inactive_hors_cycle_ne_peut_pas_etre_supprimee(perimetre_cycles):
    baker.make(
        'viescolaire.ParticipationActivite',
        activite=perimetre_cycles['activite_primaire'],
        inscription=perimetre_cycles['inscription_secondaire'],
        is_active=False,
    )
    response = perimetre_cycles['client'].get(reverse(
        'viescolaire:activite_detail', args=[perimetre_cycles['activite_primaire'].pk],
    ))
    assert response.status_code == 404
    response = perimetre_cycles['client'].post(reverse(
        'viescolaire:activite_delete', args=[perimetre_cycles['activite_primaire'].pk],
    ))
    assert response.status_code == 404
    assert perimetre_cycles['activite_primaire'].__class__.objects.filter(
        pk=perimetre_cycles['activite_primaire'].pk,
    ).exists()
