import datetime
import re

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestDocumentsViews:
    def test_document_list_redirect_anon(self, client):
        url = reverse('documents:document_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_document_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('documents:document_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_liste_classes_selector_redirect_anon(self, client):
        url = reverse('documents:liste_classes_selector')
        response = client.get(url)
        assert response.status_code == 302

    def test_liste_classes_selector_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('documents:liste_classes_selector')
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_convocation_form_selecteur_classe_sans_inline(client):
    """Le filtre de classe est un formulaire GET (CSP) et la liste des élèves s'affiche pour la classe choisie."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, actif=True)
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee)

    response = client.get(reverse('documents:convocation_form') + f'?classe={classe.pk}')

    assert response.status_code == 200
    html = response.content.decode()
    assert not re.search(r'\son[a-z]+="', html) and 'toggleAll' not in html
    assert '<form method="get"' in html and 'name="classe"' in html and 'data-csp-submit-on-change' in html
    assert f'<option value="{classe.pk}" selected>' in html
    assert f'value="{inscription.pk}" class="eleve-cb"' in html and 'class="convocation-eleve"' in html
    assert all('nonce="' in b for b in re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html))


@pytest.mark.django_db
class TestCertificatScolariteFiliation:
    """Le certificat mentionne la filiation : « né(e) le … à …, de PÈRE et de MÈRE, de nationalité … »."""

    @pytest.fixture
    def inscription(self, client):
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR'))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
        eleve = baker.make('inscriptions.Eleve', nom_pere='Ouedraogo Jean', nom_mere='Sawadogo Marie')
        return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)

    @staticmethod
    def _filiation(html):
        corps = re.search(r'à <strong[^>]*>[^<]*</strong>,(.*?)de nationalité', html, re.S).group(1)
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', corps)).strip()

    def test_apercu_et_pdf_mentionnent_les_deux_parents(self, client, inscription, mocker):
        url = reverse('documents:certificat_scolarite', kwargs={'inscription_id': inscription.pk})
        html_cls = mocker.patch('core.pdf.HTML')
        html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'

        apercu = client.get(url)
        assert apercu.status_code == 200
        assert self._filiation(apercu.content.decode()) == 'de OUEDRAOGO JEAN et de SAWADOGO MARIE,'

        assert client.get(url + '?format=pdf').status_code == 200
        assert self._filiation(html_cls.call_args.kwargs['string']) == 'de OUEDRAOGO JEAN et de SAWADOGO MARIE,'

    def test_un_seul_parent_ou_aucun(self, client, inscription):
        url = reverse('documents:certificat_scolarite', kwargs={'inscription_id': inscription.pk})
        eleve = inscription.eleve

        eleve.nom_pere = ''
        eleve.save()
        assert self._filiation(client.get(url).content.decode()) == 'de SAWADOGO MARIE,'

        eleve.nom_mere = ''
        eleve.save()
        assert self._filiation(client.get(url).content.decode()) == ''


@pytest.mark.django_db
def test_certificat_pdf_format_a5_portrait(client, mocker):
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR'))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee)
    html_cls = mocker.patch('core.pdf.HTML')
    html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'

    url = reverse('documents:certificat_scolarite', kwargs={'inscription_id': inscription.pk})
    assert client.get(url + '?format=pdf').status_code == 200

    css = html_cls.call_args.kwargs['string']
    assert re.search(r'@page\s*\{\s*size:\s*A5 portrait;', css)
    assert 'width: 14.8cm;' in css and 'height: 21cm;' in css
    assert 'Format A5 portrait' in client.get(url).content.decode()


@pytest.mark.django_db
def test_document_numero_et_version_generes_a_la_creation(client, mocker):
    """La clé primaire UUID est pré-remplie : le test `not self.pk` ne déclenchait jamais la numérotation
    (« N° — » sur chaque certificat)."""
    from documents.models import Document

    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee)
    from parametres.models import TypeDocument
    type_doc, _ = TypeDocument.objects.get_or_create(code='CERT_SCOL', defaults={'libelle': 'Certificat', 'categorie': 'SCOLARITE'})
    annee_civile = datetime.date.today().year

    premier = Document.objects.create(type_document=type_doc, annee_scolaire=annee, inscription=inscription)
    second = Document.objects.create(type_document=type_doc, annee_scolaire=annee, inscription=inscription)
    assert (premier.numero_document, premier.version) == (f'CERT_SCOL-{annee_civile}-00001', 1)
    assert (second.numero_document, second.version) == (f'CERT_SCOL-{annee_civile}-00002', 2)

    client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR'))
    html_cls = mocker.patch('core.pdf.HTML')
    html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'
    client.get(reverse('documents:certificat_scolarite', kwargs={'inscription_id': inscription.pk}) + '?format=pdf')
    assert f'N° CERT_SCOL-{annee_civile}-00003' in html_cls.call_args.kwargs['string']


@pytest.mark.django_db
def test_liste_classe_effectif_par_genre(client, mocker):
    """Sous la liste alphabétique, un tableau donne le nombre d'élèves par genre et l'effectif total
    (prévisualisation HTML et PDF)."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR'))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
    for genre in ('M', 'M', 'F', 'M', 'F'):
        eleve = baker.make('inscriptions.Eleve', genre=genre, date_naissance=datetime.date(datetime.date.today().year - 16, 1, 1))
        baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
    url = reverse('documents:liste_classe_pdf', kwargs={'classe_id': classe.pk})

    def lignes(html, titre):
        html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
        bloc = html.split(titre)[1].split('</table>')[0]
        return [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', ligne)).strip()
                for ligne in re.findall(r'<tr[^>]*>(.*?)</tr>', bloc, re.S)][1:]

    genre_attendu = ['Garçons 3', 'Filles 2', 'EFFECTIF TOTAL 5']
    ages_attendu = ['15 – 17 ans 3 2 5', 'TOTAL 3 2 5']
    apercu = client.get(url)
    assert apercu.status_code == 200
    assert lignes(apercu.content.decode(), 'Effectif par genre') == genre_attendu
    assert lignes(apercu.content.decode(), 'Répartition des âges par genre') == ages_attendu

    html_cls = mocker.patch('core.pdf.HTML')
    html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'
    assert client.get(url + '?format=pdf').status_code == 200
    assert lignes(html_cls.call_args.kwargs['string'], 'Effectif par genre') == genre_attendu
    assert lignes(html_cls.call_args.kwargs['string'], 'Répartition des âges par genre') == ages_attendu
