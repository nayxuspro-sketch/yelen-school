import re
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker
from pedagogie.models import Matiere, Note

@pytest.mark.django_db
class TestPedagogieViews:
    @pytest.fixture
    def logged_in_client(self, client):
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN')
        client.force_login(user)
        return client

    def test_matiere_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des matières."""
        url = reverse('pedagogie:matiere_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'matiere_list' in response.context

    def test_enseignement_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des enseignements."""
        baker.make('parametres.AnneeScolaire', est_courante=True)
        url = reverse('pedagogie:enseignement_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'classes_groupes' in response.context

    def test_enseignements_dans_le_menu_pedagogie(self, logged_in_client):
        """L'entrée « Enseignements » de la barre latérale (retirée par erreur dans d402ea0) suit « Matières »."""
        html = logged_in_client.get(reverse('pedagogie:matiere_list')).content.decode()
        menu = html.split('id="pedagogie-submenu"')[1].split('</div>')[0]
        lien = f'href="{reverse("pedagogie:enseignement_list")}" class="sb-item-submodern" data-url="/pedagogie/enseignements/"'
        assert lien in menu
        assert menu.index('>Matières<') < menu.index('>Enseignements<') < menu.index('>Évaluations<')

    def test_evaluation_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des évaluations."""
        baker.make('parametres.AnneeScolaire', est_courante=True)
        url = reverse('pedagogie:evaluation_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'evaluation_list' in response.context

    def test_matiere_create_post(self, logged_in_client):
        """Vérifie la création d'une matière via POST."""
        url = reverse('pedagogie:matiere_create')
        data = {
            'code': 'MAT-FINAL', 
            'nom': 'Mathematiques Final', 
            'categorie': 'SCIENTIFIQUE',
            'coefficient': '2.00',
            'moy_max': '20.00',
            'moy_min': '0.00',
            'heures_hebdomadaires': '4.0',
            'est_discipline': False,
            'est_obligatoire': True
        }
        response = logged_in_client.post(url, data)
        # Si redirection (302), c'est un succès. Sinon, c'est que le form est invalide.
        assert response.status_code == 302
        assert Matiere.objects.filter(code='MAT-FINAL').exists()

    def test_evaluation_saisie_post(self, logged_in_client):
        """Vérifie la saisie groupée des notes."""
        annee = baker.make('parametres.AnneeScolaire', est_courante=True)
        classe = baker.make('parametres.Classe')
        ins = baker.make('inscriptions.Inscription', annee_scolaire=annee, classe=classe)
        ens = baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe)
        evaluation = baker.make('pedagogie.Evaluation', enseignement=ens)
        url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})
        data = {f'note_{ins.id}': '18.5', f'obs_{ins.id}': 'Excellent'}
        response = logged_in_client.post(url, data)
        assert response.status_code == 302
        assert Note.objects.filter(inscription=ins, evaluation=evaluation, valeur=Decimal('18.5')).exists()

    def test_calculer_moyennes_classe_post(self, logged_in_client):
        """Vérifie le déclenchement du calcul des moyennes via POST."""
        classe = baker.make('parametres.Classe')
        trimestre = baker.make('pedagogie.Trimestre')
        url = reverse('pedagogie:calculer_moyennes_classe', kwargs={'class_id': classe.pk})
        response = logged_in_client.post(url, {'trimestre_id': trimestre.pk})
        assert response.status_code == 302


@pytest.mark.django_db
def test_competences_saisie_affiche_la_grille(client):
    """La page de saisie des compétences doit se rendre (le filtre dict_get vient de pedagogie_tags)."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    baker.make('pedagogie.Trimestre', annee_scolaire=annee)
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee)
    competence = baker.make('pedagogie.Competence', cycle=cycle, actif=True)

    response = client.get(reverse('pedagogie:competences_saisie', kwargs={'classe_id': classe.pk}))

    assert response.status_code == 200
    assert f'"inscription": "{inscription.pk}", "competence": "{competence.pk}"' in response.content.decode()


@pytest.mark.django_db
def test_evaluation_saisie_affiche_les_notes_existantes_non_localisees(client):
    """Les notes (Decimal) étaient rendues « 12,50 » dans des <input type="number"> : le navigateur
    rejetait la valeur et toute note déjà saisie apparaissait vide à la réouverture."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, role='SUPER_ADMIN'))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
    ens = baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe)
    evaluation = baker.make('pedagogie.Evaluation', enseignement=ens, bareme=Decimal('20.00'))
    notee, zero, absent = baker.make('inscriptions.Inscription', annee_scolaire=annee, classe=classe, _quantity=3)
    baker.make('pedagogie.Note', inscription=notee, evaluation=evaluation, valeur=Decimal('12.50'))
    baker.make('pedagogie.Note', inscription=zero, evaluation=evaluation, valeur=Decimal('0.00'))
    baker.make('pedagogie.Note', inscription=absent, evaluation=evaluation, valeur=Decimal('0.00'), observation='ABS')

    html = client.get(reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})).content.decode()

    def valeur(prefixe, inscription):
        return re.search(rf'id="{prefixe}-{inscription.pk}"[^>]*\bvalue="([^"]*)"', html).group(1)

    for prefixe in ('note', 'mnote'):
        assert valeur(prefixe, notee) == '12.50'
        assert valeur(prefixe, zero) == '0'
        assert valeur(prefixe, absent) == ''
    assert set(re.findall(r'\bmax="([^"]*)"', html)) == {'20'}
    assert 'parseFloat("20")' in html


@pytest.mark.django_db
class TestCahierTextesCreate:
    """Création d'une entrée du cahier de textes avec le journal d'audit actif (production) :
    les champs date/heure doivent être des objets typés, car l'audit appelle str(entrée)."""

    @pytest.fixture
    def contexte(self, client):
        from core.signals import disable_audit, enable_audit
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', etablissement=etab, role='SUPER_ADMIN'))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
        enseignement = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, est_actif=True)
        enable_audit()
        yield classe, enseignement
        disable_audit()

    def test_creation_journalisee(self, contexte, client):
        import datetime
        from core.models import AuditLog
        from pedagogie.models import CahierTextes
        classe, enseignement = contexte
        url = reverse('pedagogie:cahier_textes_create') + f'?classe={classe.pk}'
        reponse = client.post(url, {
            'enseignement': str(enseignement.pk), 'date': '2026-10-16', 'heure_debut': '08:00',
            'heure_fin': '10:00', 'contenu': 'Les fractions', 'devoirs': 'Exercices 1 à 5',
            'date_remise_devoirs': '2026-10-20',
        })
        assert reponse.status_code == 302
        entree = CahierTextes.objects.get()
        assert (entree.date, entree.heure_debut, entree.date_remise_devoirs) == (
            datetime.date(2026, 10, 16), datetime.time(8, 0), datetime.date(2026, 10, 20))
        assert AuditLog.objects.filter(model_name='cahiertextes', action='CREATE').exists()

    def test_date_invalide_refusee_sans_erreur_serveur(self, contexte, client):
        from pedagogie.models import CahierTextes
        classe, enseignement = contexte
        url = reverse('pedagogie:cahier_textes_create') + f'?classe={classe.pk}'
        reponse = client.post(url, {'enseignement': str(enseignement.pk), 'date': '16/10/2026', 'contenu': 'Cours'})
        assert reponse.status_code == 200
        assert CahierTextes.objects.count() == 0
