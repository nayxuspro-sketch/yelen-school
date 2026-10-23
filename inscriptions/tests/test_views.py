import re

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

    def test_chaque_champ_affiche_une_seule_fois(self, logged_in_client):
        """« Nom de famille * » n'est plus répété dans « Informations Familiales & Tuteur » (« nom » ⊂ « nom_pere »)."""
        from itertools import chain
        from inscriptions.forms import EleveForm
        assert set(chain.from_iterable(EleveForm.SECTIONS.values())) == set(EleveForm.base_fields)
        html = logged_in_client.get(reverse('inscriptions:eleve_create')).content.decode()
        assert {nom: html.count(f'name="{nom}"') for nom in EleveForm.base_fields} == dict.fromkeys(EleveForm.base_fields, 1)
        assert html.index('Nom de famille') < html.index('Informations Familiales') < html.index('Nom du père')
        assert 'Nom de famille' not in html[html.index('Informations Familiales'):]

    def test_telephone_urgence_35_caracteres(self, logged_in_client):
        """Le téléphone d'urgence accepte 35 caractères (deux numéros, ex. « 70 00 00 00 / 76 00 00 00 »)."""
        from inscriptions.models import Eleve
        numeros = '+226 70 00 00 00 / +226 76 00 00 00'
        assert len(numeros) == 35
        html = logged_in_client.get(reverse('inscriptions:eleve_create')).content.decode()
        assert 'maxlength="35"' in re.search(r'<input[^>]*name="telephone_urgence"[^>]*>', html).group(0)
        reponse = logged_in_client.post(reverse('inscriptions:eleve_create'), {
            'nom': 'TRAORE', 'prenom': 'Moussa', 'genre': 'M', 'date_naissance': '2013-01-01', 'lieu_naissance': 'Bobo-Dioulasso',
            'nationalite': 'Burkinabè', 'lieu_residence': 'Dafra', 'telephone_urgence': numeros,
        })
        assert reponse.status_code == 302 and Eleve.objects.get(nom='TRAORE').telephone_urgence == numeros

    def test_lieu_de_residence(self, logged_in_client):
        """« Localisation & Origine Scolaire » : lieu de résidence (village / quartier / secteur) au lieu du pays."""
        from html import unescape
        from inscriptions.models import Eleve
        html = unescape(logged_in_client.get(reverse('inscriptions:eleve_create')).content.decode())
        assert 'Lieu de résidence (Village/Quartier/Secteur)' in html and 'Pays de résidence' not in html
        assert 'name="lieu_residence"' in html and 'name="pays_residence"' not in html
        assert not any(f'name="{nom}"' in html for nom in ('province', 'commune', 'village'))
        assert 'Province' not in html and 'Commune' not in html and 'Village/Ville' not in html
        assert 'required' in re.search(r'<input[^>]*name="lieu_residence"[^>]*>', html).group(0)   # champ obligatoire
        assert re.search(r'Lieu de résidence \(Village/Quartier/Secteur\)\s*<span[^>]*>\*</span>', html)
        donnees = {'nom': 'KABORE', 'prenom': 'Awa', 'genre': 'F', 'date_naissance': '2014-03-05',
                   'lieu_naissance': 'Ouagadougou', 'nationalite': 'Burkinabè'}
        sans_residence = logged_in_client.post(reverse('inscriptions:eleve_create'), donnees)
        assert sans_residence.status_code == 200 and not Eleve.objects.filter(nom='KABORE').exists()
        assert 'Ce champ est obligatoire.' in unescape(sans_residence.content.decode())
        reponse = logged_in_client.post(reverse('inscriptions:eleve_create'), {**donnees, 'lieu_residence': 'Secteur 30 (Karpala)'})
        eleve = Eleve.objects.get(nom='KABORE')
        assert reponse.status_code == 302 and eleve.lieu_residence == 'Secteur 30 (Karpala)'
        assert 'Secteur 30 (Karpala)' in logged_in_client.get(reverse('inscriptions:eleve_detail', kwargs={'pk': eleve.pk})).content.decode()


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


@pytest.mark.django_db
def test_carte_scolaire_face_unique_avec_residence_et_parents(client, mocker):
    """La carte n'a plus de verso ; la face unique porte Résidence, Père, Mère et N° d'urgence (carte seule, cartes de classe, aperçu)."""
    import datetime
    from html import unescape
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True))
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab, code='POST'))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    eleve = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Abdoul', genre='M', date_naissance=datetime.date(2012, 5, 12),
                       lieu_residence='Secteur 30 (Karpala)', nom_pere='OUEDRAOGO Boukary', nom_mere='SAWADOGO Mariam',
                       telephone_urgence='', telephone_parent='70 11 22 33', photo='')
    baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
    weasy = mocker.patch('inscriptions.views._WeasyHTML')
    weasy.return_value.write_pdf.return_value = b'%PDF-1.7 test'
    attendu = ['Résidence :', 'Secteur 30 (Karpala)', 'Père :', 'OUEDRAOGO Boukary', 'Mère :', 'SAWADOGO Mariam',
               "N° d'urgence :", '70 11 22 33']   # sans numéro d'urgence dédié, le téléphone des parents est utilisé

    assert client.get(reverse('inscriptions:eleve_carte', kwargs={'pk': eleve.pk}) + '?format=pdf').status_code == 200
    carte = unescape(weasy.call_args.kwargs['string'])
    assert all(texte in carte for texte in attendu) and carte.count('class="carte"') == 1   # une seule face
    assert 'Verso' not in carte and 'Recto' not in carte and 'Cachet et signature' not in carte

    assert client.get(reverse('inscriptions:classe_cartes_pdf', kwargs={'pk': classe.pk})).status_code == 200
    cartes = unescape(weasy.call_args.kwargs['string'])
    assert all(texte in cartes for texte in attendu)

    apercu = unescape(client.get(reverse('inscriptions:eleve_carte', kwargs={'pk': eleve.pk})).content.decode())
    assert all(texte in apercu for texte in attendu) and 'Verso' not in apercu and 'Recto' not in apercu
