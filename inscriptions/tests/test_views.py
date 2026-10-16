import pytest
from django.urls import reverse
from model_bakery import baker

@pytest.mark.django_db
class TestInscriptionsViews:
    @pytest.fixture
    def logged_in_client(self, client):
        user = baker.make('accounts.User', is_superuser=True)
        client.force_login(user)
        return client

    def test_eleve_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des élèves."""
        baker.make('inscriptions.Eleve', _quantity=3)
        url = reverse('inscriptions:eleve_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'eleve_list' in response.context
        assert len(response.context['eleve_list']) >= 3

    def test_eleve_list_htmx(self, logged_in_client):
        """Vérifie la recherche HTMX dans la liste des élèves."""
        baker.make('inscriptions.Eleve', nom="ZONGO", prenom="Jean")
        url = reverse('inscriptions:eleve_list')
        response = logged_in_client.get(url, {'q': 'ZONGO'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert 'ZONGO' in response.content.decode().upper()

    def test_eleve_detail_view(self, logged_in_client):
        """Vérifie l'accès aux détails d'un élève."""
        eleve = baker.make('inscriptions.Eleve')
        url = reverse('inscriptions:eleve_detail', kwargs={'pk': eleve.pk})
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert response.context['eleve'] == eleve

    def test_eleve_create_view_get(self, logged_in_client):
        """Vérifie l'affichage du formulaire de création."""
        url = reverse('inscriptions:eleve_create')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context


@pytest.mark.django_db
def test_formulaire_inscription_sans_onchange_genere(client):
    """Le remplissage niveau / cycle / code de paiement repose sur des écouteurs, plus sur des onchange (CSP)."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True))
    eleve = baker.make('inscriptions.Eleve')

    html = client.get(reverse('inscriptions:inscription_create', kwargs={'pk': eleve.pk})).content.decode()

    assert 'onchange=' not in html and 'window.update' not in html
    assert "classeSelect.addEventListener('change'" in html
    assert "statutSelect.addEventListener('change', updateCodePaiementFromFields)" in html


@pytest.mark.django_db
class TestEleveListStatistiques:
    """Sous la liste des élèves : effectif par genre et répartition des âges, calculés sur
    l'ensemble filtré (toutes pages), aussi dans la réponse HTMX."""

    @staticmethod
    def _lignes(html, titre):
        import re
        bloc = html.split(titre)[1].split('</table>')[0]
        return [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', ligne)).strip()
                for ligne in re.findall(r'<tr[^>]*>(.*?)</tr>', bloc, re.S)][1:]

    def test_tableaux_sous_la_liste(self, client, mocker):
        import datetime
        aujourd_hui = datetime.date.today()
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', is_superuser=True, etablissement=etab))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
        autre = baker.make('parametres.Classe', etablissement=etab, cycle=classe.cycle)
        for genre, age, cl in (('M', 7, classe), ('M', 10, classe), ('F', 10, classe), ('F', 16, classe), ('M', 16, autre)):
            eleve = baker.make('inscriptions.Eleve', genre=genre, date_naissance=datetime.date(aujourd_hui.year - age, 1, 1))
            baker.make('inscriptions.Inscription', eleve=eleve, classe=cl, annee_scolaire=annee)

        html = client.get(reverse('inscriptions:eleve_list')).content.decode()
        assert self._lignes(html, 'Effectif par genre') == ['Garçons 3', 'Filles 2', 'EFFECTIF TOTAL 5']
        assert self._lignes(html, 'Répartition des âges par genre') == [
            '6 – 8 ans 1 0 1', '9 – 11 ans 1 1 2', '15 – 17 ans 1 1 2', 'TOTAL 3 2 5']

        partiel = client.get(reverse('inscriptions:eleve_list'), {'classe': classe.pk}, HTTP_HX_REQUEST='true').content.decode()
        assert self._lignes(partiel, 'Effectif par genre') == ['Garçons 2', 'Filles 2', 'EFFECTIF TOTAL 4']

        rendu = mocker.patch('inscriptions.views._WeasyHTML')
        rendu.return_value.write_pdf.return_value = b'%PDF-1.7 test'
        assert client.get(reverse('inscriptions:eleve_list_pdf'), {'classe': classe.pk}).status_code == 200
        html_pdf = rendu.call_args.kwargs['string']
        assert self._lignes(html_pdf, 'Effectif par genre') == ['Garçons 2', 'Filles 2', 'EFFECTIF TOTAL 4']
        assert self._lignes(html_pdf, 'Répartition des âges par genre') == [
            '6 – 8 ans 1 0 1', '9 – 11 ans 1 1 2', '15 – 17 ans 0 1 1', 'TOTAL 2 2 4']
