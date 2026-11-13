"""Affectations du personnel par cycle et direction générale de l'établissement."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from model_bakery import baker

from personnel.models import InscriptionPersonnel
from personnel.selectors import membres_dans_cycle

pytestmark = pytest.mark.django_db


def test_personnel_transversal_peut_etre_affecte_a_plusieurs_cycles():
    etab = baker.make('etablissements.Etablissement')
    primaire = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire')
    secondaire = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    membre = baker.make(
        'personnel.MembrePersonnel', etablissement=etab, nom='SOME', prenom='Awa',
        cycles=[primaire, secondaire],
    )
    compte = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR')
    compte.cycles.add(primaire)  # droit de consultation, indépendant de l'affectation professionnelle

    assert set(membres_dans_cycle(type(membre).objects.all(), primaire)) == {membre}
    assert set(membres_dans_cycle(type(membre).objects.all(), secondaire)) == {membre}
    assert set(membre.cycles.all()) == {primaire, secondaire}
    assert set(compte.cycles.all()) == {primaire}


def test_directeur_general_et_directeurs_de_cycle_sont_distincts_et_uniques(client):
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)
    primaire = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire')
    secondaire = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    poste_direction = baker.make(
        'parametres.Poste', etablissement=etab, code='DIR-CYCLE', titre='Directeur de cycle', categorie='DIRECTION',
    )
    directeur_general = baker.make(
        'personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Issouf', est_directeur=True,
    )
    directeur_primaire = baker.make(
        'personnel.MembrePersonnel', etablissement=etab, nom='TRAORE', prenom='Awa',
    )
    directeur_secondaire = baker.make(
        'personnel.MembrePersonnel', etablissement=etab, nom='SAWADOGO', prenom='Moussa',
    )

    inscription_primaire = InscriptionPersonnel(
        personnel=directeur_primaire, annee_scolaire=annee, cycle=primaire,
        poste=poste_direction, est_actif=True, est_directeur_cycle=True,
    )
    inscription_primaire.full_clean()
    inscription_primaire.save()

    directeur_primaire_second = baker.make(
        'personnel.MembrePersonnel', etablissement=etab, nom='OUEDRAOGO', prenom='Ali',
    )
    doublon = InscriptionPersonnel(
        personnel=directeur_primaire_second, annee_scolaire=annee, cycle=primaire,
        poste=poste_direction, est_actif=True, est_directeur_cycle=True,
    )
    with pytest.raises(ValidationError, match='Un directeur de cycle actif est déjà désigné'):
        doublon.full_clean()
    # La contrainte SQL protège aussi les écritures qui contournent les formulaires.
    with pytest.raises(IntegrityError), transaction.atomic():
        InscriptionPersonnel.objects.create(
            personnel=directeur_primaire_second, annee_scolaire=annee, cycle=primaire,
            poste=poste_direction, est_actif=True, est_directeur_cycle=True,
        )

    inscription_secondaire = InscriptionPersonnel(
        personnel=directeur_secondaire, annee_scolaire=annee, cycle=secondaire,
        poste=poste_direction, est_actif=True, est_directeur_cycle=True,
    )
    inscription_secondaire.full_clean()
    inscription_secondaire.save()

    second_directeur_general = baker.make(
        'personnel.MembrePersonnel', etablissement=etab, nom='ZONGO', prenom='Paul',
    )
    second_directeur_general.est_directeur = True
    with pytest.raises(ValidationError, match='Un directeur général est déjà désigné'):
        second_directeur_general.full_clean()

    utilisateur = baker.make(
        'accounts.User', etablissement=etab, role='DIRECTEUR', est_tous_cycles=True,
        must_change_password=False,
    )
    client.force_login(utilisateur)
    reponse = client.get(reverse('parametres:cycle_list'))
    assert reponse.status_code == 200
    contenu = reponse.content.decode()
    assert directeur_general.get_nom_complet() not in contenu  # la fiche du cycle montre sa direction propre
    assert directeur_primaire.get_nom_complet() in contenu
    assert directeur_secondaire.get_nom_complet() in contenu
    assert 'Directeur · 2026-2027' in contenu
