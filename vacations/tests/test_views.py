"""
Tests — vacations.views
"""

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestContratListView:
    def test_redirige_si_anonyme(self, client):
        url = reverse('vacations:contrat_list')
        assert client.get(url).status_code == 302

    def test_accessible_connecte(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(reverse('vacations:contrat_list')).status_code == 200

    def test_affiche_contrats_annee_courante(self, client, admin_user, contrat):
        client.force_login(admin_user)
        response = client.get(reverse('vacations:contrat_list'))
        assert response.status_code == 200
        assert contrat in response.context['contrats']


@pytest.mark.django_db
class TestSaisieHeuresView:
    def test_redirige_si_anonyme(self, client, contrat):
        url = reverse('vacations:saisie_heures', kwargs={'contrat_id': contrat.pk})
        assert client.get(url).status_code == 302

    def test_accessible_connecte(self, client, admin_user, contrat):
        client.force_login(admin_user)
        url = reverse('vacations:saisie_heures', kwargs={'contrat_id': contrat.pk})
        assert client.get(url).status_code == 200

    def test_post_enregistre_heures(self, client, admin_user, contrat):
        client.force_login(admin_user)
        url = reverse('vacations:saisie_heures', kwargs={'contrat_id': contrat.pk})
        response = client.post(url, {
            'mois': 3,
            'annee': 2026,
            'heures_effectuees': '8',
            'heures_annulees': '0',
            'observations': '',
        })
        assert response.status_code == 302
        from vacations.models import HeureVacation
        assert HeureVacation.objects.filter(contrat=contrat, mois=3, annee=2026).exists()


@pytest.mark.django_db
class TestBulletinListView:
    def test_redirige_si_anonyme(self, client):
        assert client.get(reverse('vacations:bulletin_list')).status_code == 302

    def test_accessible_connecte(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(reverse('vacations:bulletin_list')).status_code == 200

    def test_filtre_par_statut(self, client, admin_user, annee, personnel):
        baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            mois=3, annee=2026,
            statut='PAYE',
        )
        autre_personnel = baker.make(
            'personnel.MembrePersonnel',
            nom='SOME', prenom='One', matricule='PERS-T-2026-0002',
            genre='F', nationalite='BF', lieu_naissance='OUA',
            telephone='1', numero_cni='B1', fonction='Ens.',
            titre_honorifique='Mme', situation_matrimoniale='C',
            poste_principal_code='ENS',
        )
        baker.make(
            'vacations.BulletinVacation',
            personnel=autre_personnel,
            annee_scolaire=annee,
            mois=4, annee=2026,
            statut='BROUILLON',
        )
        client.force_login(admin_user)
        response = client.get(reverse('vacations:bulletin_list'), {'statut': 'PAYE'})
        assert response.status_code == 200
        assert all(b.statut == 'PAYE' for b in response.context['bulletins'])


@pytest.mark.django_db
class TestValiderHeure:
    def test_valider_heure(self, client, admin_user, contrat):
        heure = baker.make('vacations.HeureVacation', contrat=contrat, est_valide=False)
        client.force_login(admin_user)
        url = reverse('vacations:valider_heure', kwargs={'heure_id': heure.pk})
        assert client.get(url).status_code == 302
        heure.refresh_from_db()
        assert heure.est_valide is True

    def test_invalider_heure(self, client, admin_user, contrat):
        heure = baker.make('vacations.HeureVacation', contrat=contrat, est_valide=True)
        client.force_login(admin_user)
        url = reverse('vacations:invalider_heure', kwargs={'heure_id': heure.pk})
        assert client.get(url).status_code == 302
        heure.refresh_from_db()
        assert heure.est_valide is False


@pytest.mark.django_db
class TestValiderBulletin:
    """Valider / payer un bulletin par un utilisateur rattaché à un établissement (cas réel) : le contrôle
    d'établissement lisait ``bulletin.contrat`` — attribut inexistant sur BulletinVacation — d'où une erreur 500."""

    def test_valider_bulletin(self, client, annee, personnel):
        bulletin = baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            statut='BROUILLON',
        )
        client.force_login(baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN',
                                      etablissement=annee.etablissement))
        url = reverse('vacations:valider_bulletin', kwargs={'bulletin_id': bulletin.pk})
        assert client.get(url).status_code == 302
        bulletin.refresh_from_db()
        assert bulletin.statut == 'VALIDE'

    def test_payer_bulletin(self, client, annee, personnel):
        bulletin = baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            statut='VALIDE',
        )
        client.force_login(baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN',
                                      etablissement=annee.etablissement))
        url = reverse('vacations:payer_bulletin', kwargs={'bulletin_id': bulletin.pk})
        assert client.get(url).status_code == 302
        bulletin.refresh_from_db()
        assert bulletin.statut == 'PAYE'
        assert bulletin.date_paiement is not None

    @pytest.mark.parametrize('nom_url', ['vacations:valider_bulletin', 'vacations:payer_bulletin'])
    def test_autre_etablissement_refuse(self, client, annee, personnel, nom_url):
        bulletin = baker.make('vacations.BulletinVacation', personnel=personnel, annee_scolaire=annee, statut='BROUILLON')
        client.force_login(baker.make('accounts.User', is_superuser=True, etablissement=baker.make('etablissements.Etablissement')))
        reponse = client.get(reverse(nom_url, kwargs={'bulletin_id': bulletin.pk}))
        assert reponse.status_code == 302 and reponse['Location'] == reverse('vacations:bulletin_list')
        bulletin.refresh_from_db()
        assert bulletin.statut == 'BROUILLON'


@pytest.mark.django_db
def test_vacations_limitees_aux_cycles_autorises(client):
    """Listes, choix de formulaire et accès direct n'exposent pas les contrats du cycle secondaire."""
    from datetime import date
    from django.urls import reverse
    from vacations.models import ContratVacation

    etab = baker.make('etablissements.Etablissement')
    primaire = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire')
    secondaire = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    annee = baker.make(
        'parametres.AnneeScolaire', etablissement=etab, est_courante=True,
        date_debut=date(2026, 9, 1), date_fin=date(2027, 6, 30),
    )
    classe_primaire = baker.make('parametres.Classe', etablissement=etab, cycle=primaire, nom='CP1')
    classe_secondaire = baker.make('parametres.Classe', etablissement=etab, cycle=secondaire, nom='6e A')
    matiere_primaire = baker.make('pedagogie.Matiere', code='VACPRIM', nom='Lecture')
    matiere_secondaire = baker.make('pedagogie.Matiere', code='VACSEC', nom='Physique')
    prof_primaire = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Ali')
    prof_secondaire = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZONGO', prenom='Awa')
    prof_primaire.cycles.add(primaire)
    prof_secondaire.cycles.add(secondaire)
    enseignement_primaire = baker.make(
        'pedagogie.Enseignement', classe=classe_primaire, annee_scolaire=annee,
        personnel=prof_primaire, matiere=matiere_primaire,
    )
    enseignement_secondaire = baker.make(
        'pedagogie.Enseignement', classe=classe_secondaire, annee_scolaire=annee,
        personnel=prof_secondaire, matiere=matiere_secondaire,
    )
    contrat_primaire = baker.make(
        'vacations.ContratVacation', personnel=prof_primaire, annee_scolaire=annee,
        enseignement=enseignement_primaire, actif=True,
    )
    contrat_secondaire = baker.make(
        'vacations.ContratVacation', personnel=prof_secondaire, annee_scolaire=annee,
        enseignement=enseignement_secondaire, actif=True,
    )
    bulletin_primaire = baker.make(
        'vacations.BulletinVacation', personnel=prof_primaire, annee_scolaire=annee,
        mois=3, annee=2027,
    )
    bulletin_secondaire = baker.make(
        'vacations.BulletinVacation', personnel=prof_secondaire, annee_scolaire=annee,
        mois=3, annee=2027,
    )
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    user.cycles.add(primaire)
    client.force_login(user)

    contrats = client.get(reverse('vacations:contrat_list'))
    assert contrats.status_code == 200
    assert contrat_primaire in contrats.context['contrats']
    assert contrat_secondaire not in contrats.context['contrats']

    formulaire = client.get(reverse('vacations:contrat_create'))
    assert formulaire.status_code == 200
    choix = formulaire.context['form'].fields
    assert prof_primaire in choix['personnel'].queryset
    assert prof_secondaire not in choix['personnel'].queryset
    assert enseignement_primaire in choix['enseignement'].queryset
    assert enseignement_secondaire not in choix['enseignement'].queryset

    invalide = client.post(reverse('vacations:contrat_create'), {
        'personnel': str(prof_secondaire.pk), 'annee_scolaire': str(annee.pk),
        'enseignement': str(enseignement_secondaire.pk), 'taux_horaire': '2500',
        'heures_hebdo_prevues': '2', 'date_debut': '2026-09-01', 'actif': 'on',
    })
    assert invalide.status_code == 200 and invalide.context['form'].errors
    assert not ContratVacation.objects.filter(personnel=prof_secondaire, annee_scolaire=annee).exclude(
        pk=contrat_secondaire.pk
    ).exists()

    assert client.get(reverse('vacations:saisie_heures', args=[contrat_secondaire.pk])).status_code == 404
    bulletins = client.get(reverse('vacations:bulletin_list'))
    assert bulletin_primaire in bulletins.context['bulletins']
    assert bulletin_secondaire not in bulletins.context['bulletins']
    reponse = client.get(reverse('vacations:valider_bulletin', args=[bulletin_secondaire.pk]))
    assert reponse.status_code == 302
    bulletin_secondaire.refresh_from_db()
    assert bulletin_secondaire.statut == 'BROUILLON'


@pytest.mark.django_db
def test_bulletin_agrege_cache_si_le_membre_a_des_contrats_dans_plusieurs_cycles(client):
    """Un bulletin vacation agrège tous les contrats du membre : il ne peut exposer un autre cycle."""
    from datetime import date
    from django.urls import reverse

    etab = baker.make('etablissements.Etablissement')
    primaire = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire')
    secondaire = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
    annee = baker.make(
        'parametres.AnneeScolaire', etablissement=etab, est_courante=True,
        date_debut=date(2026, 9, 1), date_fin=date(2027, 6, 30),
    )
    classe_primaire = baker.make('parametres.Classe', etablissement=etab, cycle=primaire, nom='CP1')
    classe_secondaire = baker.make('parametres.Classe', etablissement=etab, cycle=secondaire, nom='6e A')
    membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Ali')
    membre.cycles.add(primaire)
    matiere = baker.make('pedagogie.Matiere', code='VAC-CYCLE', nom='Lecture')
    ens_primaire = baker.make(
        'pedagogie.Enseignement', classe=classe_primaire, annee_scolaire=annee,
        personnel=membre, matiere=matiere,
    )
    ens_secondaire = baker.make(
        'pedagogie.Enseignement', classe=classe_secondaire, annee_scolaire=annee,
        personnel=membre, matiere=matiere,
    )
    contrat_primaire = baker.make(
        'vacations.ContratVacation', personnel=membre, annee_scolaire=annee,
        enseignement=ens_primaire, taux_horaire=2500,
    )
    contrat_secondaire = baker.make(
        'vacations.ContratVacation', personnel=membre, annee_scolaire=annee,
        enseignement=ens_secondaire, taux_horaire=4000,
    )
    baker.make('vacations.HeureVacation', contrat=contrat_primaire, mois=3, annee=2027,
               heures_effectuees=4, est_valide=True)
    baker.make('vacations.HeureVacation', contrat=contrat_secondaire, mois=3, annee=2027,
               heures_effectuees=6, est_valide=True)
    bulletin = baker.make(
        'vacations.BulletinVacation', personnel=membre, annee_scolaire=annee,
        mois=3, annee=2027, statut='BROUILLON',
    )
    bulletin.calculer_totaux()
    assert bulletin.total_heures == 10  # la synthèse contient bien les deux contrats

    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    user.cycles.add(primaire)
    client.force_login(user)

    liste = client.get(reverse('vacations:bulletin_list'))
    assert liste.status_code == 200 and bulletin not in liste.context['bulletins']
    assert client.get(reverse('vacations:bulletin_vacation_pdf', args=[bulletin.pk])).status_code == 404
    assert client.get(reverse('vacations:valider_bulletin', args=[bulletin.pk])).status_code == 302
    assert client.get(reverse('vacations:payer_bulletin', args=[bulletin.pk])).status_code == 302
    assert client.get(reverse('vacations:generer_bulletin', args=[contrat_primaire.pk, 3, 2027])).status_code == 302

    bulletin.refresh_from_db()
    assert bulletin.statut == 'BROUILLON' and bulletin.total_heures == 10
    assert client.get(reverse('vacations:saisie_heures', args=[contrat_secondaire.pk])).status_code == 404
