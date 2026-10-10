import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestPersonnelViews:
    def test_personnel_list_redirect_anon(self, client):
        url = reverse('personnel:personnel_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_personnel_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('personnel:personnel_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_salaire_list_redirect_anon(self, client):
        url = reverse('personnel:salaire_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_salaire_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('personnel:salaire_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_conge_list_redirect_anon(self, client):
        url = reverse('personnel:conge_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_conge_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('personnel:conge_list')
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestSalairePersonnelModel:
    def _make_membre(self, **kw):
        etab = baker.make('etablissements.Etablissement', code='BK')
        defaults = dict(etablissement=etab, matricule='')
        defaults.update(kw)
        return baker.make('personnel.MembrePersonnel', **defaults)

    def test_prime_anciennete_moins_2_ans(self):
        from personnel.models import SalairePersonnel
        membre = self._make_membre(date_embauche=date.today() - timedelta(days=365))
        prime = SalairePersonnel.calculer_prime_anciennete(membre, Decimal('100000'))
        assert prime == Decimal('0')

    def test_prime_anciennete_entre_2_et_5_ans(self):
        from personnel.models import SalairePersonnel
        membre = self._make_membre(date_embauche=date.today() - timedelta(days=365 * 3))
        prime = SalairePersonnel.calculer_prime_anciennete(membre, Decimal('100000'))
        assert prime == Decimal('5000')

    def test_prime_anciennete_plus_20_ans(self):
        from personnel.models import SalairePersonnel
        membre = self._make_membre(date_embauche=date.today() - timedelta(days=365 * 25))
        prime = SalairePersonnel.calculer_prime_anciennete(membre, Decimal('100000'))
        assert prime == Decimal('25000')




@pytest.mark.django_db
class TestCongePersonnelModel:
    def test_calcul_jours_ouvrables_semaine_complete(self):
        from personnel.models import CongePersonnel
        # Lundi au samedi = 6 jours ouvrables
        etab = baker.make('etablissements.Etablissement', code='BK')
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab, matricule='')
        conge = baker.prepare(
            'personnel.CongePersonnel',
            personnel=membre,
            date_debut=date(2026, 4, 6),   # lundi
            date_fin=date(2026, 4, 11),    # samedi
        )
        assert conge._calcul_jours_ouvrables() == 6

    def test_calcul_jours_ouvrables_exclut_dimanche(self):
        from personnel.models import CongePersonnel
        # Samedi + dimanche + lundi = 2 jours ouvrables (sam + lun)
        etab = baker.make('etablissements.Etablissement', code='BK')
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab, matricule='')
        conge = baker.prepare(
            'personnel.CongePersonnel',
            personnel=membre,
            date_debut=date(2026, 4, 11),  # samedi
            date_fin=date(2026, 4, 13),    # lundi
        )
        assert conge._calcul_jours_ouvrables() == 2

    def test_jours_restants_initial(self):
        from personnel.models import CongePersonnel
        etab = baker.make('etablissements.Etablissement', code='BK')
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab, matricule='')
        restants = CongePersonnel.jours_restants(membre, 2026)
        assert restants == CongePersonnel.DROITS_ANNUELS


@pytest.mark.django_db
class TestPersonnelFiltre:
    """Sélecteur partagé par la liste et ses exports CSV / Excel / PDF."""

    @pytest.fixture
    def donnees(self):
        from personnel.selectors import personnel_filtre
        etab = baker.make('etablissements.Etablissement')
        actif = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Zongo', prenom='Ali',
                           matricule='01-P-2026-01', is_active=True)
        inactif = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Kabore', prenom='Awa',
                             matricule='01-P-2026-02', is_active=False)
        autre = baker.make('personnel.MembrePersonnel', nom='Zongo', prenom='Issa', is_active=True)
        return personnel_filtre, etab, actif, inactif, autre

    def test_actifs_de_l_etablissement_par_defaut(self, donnees):
        filtre, etab, actif, inactif, autre = donnees
        assert list(filtre(etab)) == [actif]

    def test_inactifs_inclus_sur_demande(self, donnees):
        filtre, etab, actif, inactif, autre = donnees
        assert list(filtre(etab, inclure_inactifs=True)) == [inactif, actif]  # tri nom, prénom

    def test_recherche_nom_prenom_matricule(self, donnees):
        filtre, etab, actif, inactif, autre = donnees
        assert list(filtre(etab, query='2026-02', inclure_inactifs=True)) == [inactif]
        assert list(filtre(etab, query='ali')) == [actif]
        assert list(filtre(etab, query='introuvable')) == []

    def test_selection_par_identifiants(self, donnees):
        filtre, etab, actif, inactif, autre = donnees
        ids = f'{inactif.pk}, pas-un-uuid,,{autre.pk}'
        # la sélection ignore le filtre « actifs », les identifiants invalides et les autres établissements
        assert list(filtre(etab, ids=ids)) == [inactif]
        # une sélection sans identifiant valide retombe sur les filtres standard
        assert list(filtre(etab, ids='pas-un-uuid')) == [actif]


@pytest.mark.django_db
class TestPersonnelListPdf:
    @pytest.fixture
    def contexte(self):
        etab = baker.make('etablissements.Etablissement', nom='Lycée Yelen', code='LY')
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False)
        actif = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Zongo', prenom='Ali',
                           genre='M', fonction='Professeur de SVT', is_active=True)
        inactif = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Kabore', prenom='Awa',
                             genre='F', is_active=False)
        return etab, user, actif, inactif

    def test_redirection_anonyme(self, client):
        response = client.get(reverse('personnel:personnel_list_pdf'))
        assert response.status_code == 302
        assert reverse('accounts:login') in response['Location']

    def test_pdf_genere_avec_le_nom_de_l_etablissement(self, client, contexte):
        pytest.importorskip('weasyprint')
        etab, user, actif, inactif = contexte
        client.force_login(user)
        response = client.get(reverse('personnel:personnel_list_pdf'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response['Content-Disposition'] == 'inline; filename="personnel_LY.pdf"'
        assert response.content.startswith(b'%PDF')

    def test_filtres_identiques_a_la_liste(self, client, contexte, mocker):
        """Le HTML transmis à WeasyPrint reflète les filtres actifs / tous / recherche / sélection."""
        etab, user, actif, inactif = contexte
        client.force_login(user)
        html_cls = mocker.patch('core.pdf.HTML')
        html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'
        url = reverse('personnel:personnel_list_pdf')

        def html_pour(params=''):
            assert client.get(url + params).status_code == 200
            return html_cls.call_args.kwargs['string']

        html = html_pour()
        assert 'ZONGO' in html and 'KABORE' not in html
        assert '1 membre — Actifs' in html and 'Professeur de SVT' in html

        html = html_pour('?tous=1')
        assert 'ZONGO' in html and 'KABORE' in html
        assert '2 membres — Actifs et inactifs' in html and 'Inactifs : <strong>1</strong>' in html

        html = html_pour('?tous=1&q=awa')
        assert 'KABORE' in html and 'ZONGO' not in html and 'Recherche : « awa »' in html

        html = html_pour(f'?ids={inactif.pk}')
        assert 'KABORE' in html and 'ZONGO' not in html and '1 membre — Sélection' in html

    def test_pdf_avec_licence_active(self, client, contexte, mocker):
        """Régression : avec une licence active, le filigrane (filigrane_licence.html) lit
        « etablissement » dans le contexte — son absence provoquait un 500 en production."""
        from licences.models import Licence, StatutLicence, TypeLicence
        etab, user, _, _ = contexte
        licence = Licence(etablissement=etab, type_licence=TypeLicence.PREMIUM,
                          statut=StatutLicence.ACTIVE, date_expiration=date.today() + timedelta(days=300))
        licence.save()
        client.force_login(user)
        html_cls = mocker.patch('core.pdf.HTML')
        html_cls.return_value.write_pdf.return_value = b'%PDF-1.7'

        response = client.get(reverse('personnel:personnel_list_pdf'))

        assert response.status_code == 200
        html = html_cls.call_args.kwargs['string']
        assert f'Licence PREMIUM — {licence.cle_licence} — Lycée Yelen' in html

    def test_bouton_pdf_sur_la_liste(self, client, contexte):
        etab, user, actif, inactif = contexte
        client.force_login(user)
        response = client.get(reverse('personnel:personnel_list') + '?tous=1')
        assert response.status_code == 200
        assert (reverse('personnel:personnel_list_pdf') + '?tous=1').encode() in response.content
