# licences/tests/test_limites.py
# ================================================================
# Tests du contrôle des plafonds de licence (élèves / enseignants / classes).
#
# Plafonds STARTER : 150 élèves · 15 enseignants · 10 classes.
# Les usages sont comptés sur l'ANNÉE SCOLAIRE COURANTE de l'établissement.
from datetime import date, timedelta

import pytest
from django.urls import reverse
from model_bakery import baker

from licences.services import (
    compter_classes,
    compter_eleves,
    compter_enseignants,
    get_usage_limites,
)


@pytest.fixture
def etab_annee():
    """Établissement + année scolaire courante."""
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make(
        'parametres.AnneeScolaire',
        etablissement=etab,
        libelle='2026-2027',
        date_debut=date(2026, 10, 1),
        date_fin=date(2027, 6, 30),
        est_courante=True,
    )
    return etab, annee


@pytest.fixture
def cycle(etab_annee):
    etab, annee = etab_annee
    return baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire', ordre=2)


@pytest.fixture
def licence_starter(etab_annee):
    etab, annee = etab_annee
    return baker.make(
        'licences.Licence',
        etablissement=etab,
        type_licence='STARTER',
        statut='ACTIVE',
        date_expiration=date.today() + timedelta(days=365),
    )


def _inscrire(etab, annee, cycle, nb):
    """Crée nb inscriptions actives (un élève distinct chacun)."""
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom=f'6A-{nb}', actif=True)
    inscriptions = baker.make(
        'inscriptions.Inscription',
        _quantity=nb,
        classe=classe,
        annee_scolaire=annee,
    )
    return inscriptions


@pytest.mark.django_db
class TestCompteurs:
    def test_eleves_comptes_annee_courante(self, etab_annee, cycle):
        etab, annee = etab_annee
        assert compter_eleves(etab) == 0
        _inscrire(etab, annee, cycle, 25)
        assert compter_eleves(etab) == 25

    def test_eleves_autre_annee_non_comptes(self, etab_annee, cycle):
        etab, annee = etab_annee
        _inscrire(etab, annee, cycle, 10)
        # Une autre année (non courante) ne compte pas
        autre_annee = baker.make(
            'parametres.AnneeScolaire',
            etablissement=etab,
            libelle='2025-2026',
            date_debut=date(2025, 10, 1),
            date_fin=date(2026, 6, 30),
            est_courante=False,
        )
        _inscrire(etab, autre_annee, cycle, 40)
        assert compter_eleves(etab) == 10

    def test_eleves_abandon_non_comptes(self, etab_annee, cycle):
        etab, annee = etab_annee
        _inscrire(etab, annee, cycle, 5)
        # Marquer 3 d'entre eux en abandon
        from inscriptions.models import Inscription
        pks_abandon = list(
            Inscription.objects
            .filter(annee_scolaire=annee, classe__etablissement=etab)
            .values_list('pk', flat=True)[:3]
        )
        Inscription.objects.filter(pk__in=pks_abandon).update(statut='ABANDON')
        assert compter_eleves(etab) == 2

    def test_enseignants_catégorie_enseignement(self, etab_annee, cycle):
        from personnel.models import InscriptionPersonnel, MembrePersonnel
        etab, annee = etab_annee
        poste_ens = baker.make('parametres.Poste', etablissement=etab, code='ENS', titre='Enseignant', categorie='ENSEIGNEMENT')
        poste_adm = baker.make('parametres.Poste', etablissement=etab, code='SECR', titre='Secrétaire', categorie='ADMINISTRATION')
        for i in range(4):
            membre = baker.make('personnel.MembrePersonnel', etablissement=etab, is_active=True)
            baker.make(
                'personnel.InscriptionPersonnel',
                personnel=membre,
                annee_scolaire=annee,
                cycle=cycle,
                poste=poste_ens,
                est_actif=True,
                is_active=True,
            )
        # 2 membres non-enseignants : ne doivent PAS être comptés
        for i in range(2):
            membre = baker.make('personnel.MembrePersonnel', etablissement=etab, is_active=True)
            baker.make(
                'personnel.InscriptionPersonnel',
                personnel=membre,
                annee_scolaire=annee,
                cycle=cycle,
                poste=poste_adm,
                est_actif=True,
                is_active=True,
            )
        assert compter_enseignants(etab) == 4

    def test_classes_actives(self, etab_annee, cycle):
        etab, annee = etab_annee
        assert compter_classes(etab) == 0
        baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6A', actif=True)
        baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6B', actif=True)
        baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6C', actif=False)
        assert compter_classes(etab) == 2

    def test_sans_annee_courante_usage_zero(self, etab_annee):
        etab, annee = etab_annee
        annee.est_courante = False
        annee.save()
        assert compter_eleves(etab) == 0
        assert compter_enseignants(etab) == 0


@pytest.mark.django_db
class TestGetUsageLimites:
    def test_dans_limites_pas_de_depassement(self, etab_annee, cycle, licence_starter):
        etab, annee = etab_annee
        _inscrire(etab, annee, cycle, 100)  # < 150
        resultat = get_usage_limites(licence_starter)
        assert resultat['usage']['eleves'] == 100
        assert resultat['depassements'] == []

    def test_depassement_eleves_detecte(self, etab_annee, cycle, licence_starter):
        etab, annee = etab_annee
        _inscrire(etab, annee, cycle, 151)  # > 150
        resultat = get_usage_limites(licence_starter)
        assert len(resultat['depassements']) == 1
        dep = resultat['depassements'][0]
        assert dep['champ'] == 'eleves'
        assert dep['usage'] == 151
        assert dep['max'] == 150
        assert '151' in dep['message']

    def test_depassement_classes_detecte(self, etab_annee, cycle, licence_starter):
        etab, annee = etab_annee
        for i in range(11):  # > 10
            baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom=f'C{i}', actif=True)
        resultat = get_usage_limites(licence_starter)
        champs = {d['champ'] for d in resultat['depassements']}
        assert 'classes' in champs

    def test_licence_reseau_sans_depassement(self, etab_annee, cycle):
        etab, annee = etab_annee
        licence = baker.make(
            'licences.Licence',
            etablissement=etab,
            type_licence='RESEAU',
            statut='ACTIVE',
            date_expiration=date(2030, 1, 1),
        )
        _inscrire(etab, annee, cycle, 5000)
        resultat = get_usage_limites(licence)
        assert resultat['depassements'] == []


LICENCE_MIDDLEWARES = [
    'licences.middleware.LicenceCheckMiddleware',
    'licences.middleware.LicenceLimitsMiddleware',
    'licences.middleware.LicenceContextMiddleware',
]


@pytest.mark.django_db
class TestMiddlewareLimites:
    def test_avertissement_affiche_quand_plafond_depassed(self, client, etab_annee,
                                                           cycle, licence_starter,
                                                           settings):
        """Enforcement ON : plafond dépassé → avertissement sur la page."""
        settings.LICENSE_ENFORCEMENT = True
        middleware = list(settings.MIDDLEWARE)
        for mw in LICENCE_MIDDLEWARES:
            if mw not in middleware:
                middleware.append(mw)
        settings.MIDDLEWARE = middleware

        etab, annee = etab_annee
        _inscrire(etab, annee, cycle, 151)

        user = baker.make('accounts.User', is_superuser=False, etablissement=etab)
        client.force_login(user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 200
        messages_text = ' '.join(
            str(m) for m in response.context['messages']
        )
        assert '151' in messages_text
        assert '150' in messages_text

    def test_pas_d_avertissement_dans_limites(self, client, etab_annee, cycle,
                                              licence_starter, settings):
        settings.LICENSE_ENFORCEMENT = True
        middleware = list(settings.MIDDLEWARE)
        for mw in LICENCE_MIDDLEWARES:
            if mw not in middleware:
                middleware.append(mw)
        settings.MIDDLEWARE = middleware

        etab, annee = etab_annee
        _inscrire(etab, annee, cycle, 10)

        user = baker.make('accounts.User', is_superuser=False, etablissement=etab)
        client.force_login(user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 200
        messages_text = ' '.join(str(m) for m in response.context['messages'])
        assert 'Limite de licence dépassée' not in messages_text
