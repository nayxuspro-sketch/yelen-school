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
