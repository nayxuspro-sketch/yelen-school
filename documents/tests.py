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
    assert 'width: 14.8cm;' in css and '.bas { position: absolute; left: 1.2cm; right: 1.2cm; bottom: 0.65cm; }' in css
    assert 'Format A5 portrait' in client.get(url).content.decode()


@pytest.mark.django_db
def test_certificat_signature_scannee_du_signataire(client, mocker, settings, tmp_path):
    """La signature scannée du signataire configuré est apposée dans l'espace de signature du certificat ;
    sans signature enregistrée, l'espace reste vierge."""
    from django.core.files.base import ContentFile
    from parametres.models import TypeDocument
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR'))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    inscription = baker.make('inscriptions.Inscription', annee_scolaire=annee,
                             classe=baker.make('parametres.Classe', etablissement=etab, cycle=cycle))
    type_doc, _ = TypeDocument.objects.get_or_create(code='CERT_SCOL', defaults={'libelle': 'Certificat', 'categorie': 'SCOLARITE'})
    membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salimata')
    baker.make('parametres.SignataireDocument', cycle=cycle, type_document=type_doc, annee_scolaire=annee,
               membre_personnel_id=membre.id, fonction='Le Directeur des Études', actif=True)
    html_cls = mocker.patch('core.pdf.HTML')
    html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'
    url = reverse('documents:certificat_scolarite', kwargs={'inscription_id': inscription.pk}) + '?format=pdf'

    assert client.get(url).status_code == 200
    assert '<div class="sig-espace"></div>' in html_cls.call_args.kwargs['string']

    membre.signature.save('kabore.png', ContentFile(b'\x89PNG\r\n\x1a\n'), save=True)
    assert client.get(url).status_code == 200
    html = html_cls.call_args.kwargs['string']
    assert f'<div class="sig-espace"><img class="msig-img" src="{membre.signature.url}" alt=""></div>' in html
    assert membre.signature.url.startswith('/media/personnel/signatures/kabore')


@pytest.mark.django_db
def test_certificat_charge_tient_sur_une_page(client, mocker, settings, tmp_path):
    """Pire cas réaliste rendu par WeasyPrint : identité complète (nom long, agrément, sigle, adresse, contacts,
    logo et cachet), filiation et lieu de naissance longs, fonction du signataire longue, signature scannée
    → une seule page A5, bloc QR + signature ancré au bas de la page."""
    import io
    import core.pdf
    from django.core.files.base import ContentFile
    from PIL import Image
    from parametres.models import TypeDocument
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR'))
    identite = baker.make('parametres.IdentiteEtablissement', etablissement=etab, type_etablissement='PRIVE',
                          nom_etablissement='COMPLEXE SCOLAIRE PRIVÉ LE SAVOIR DE OUAGADOUGOU', sigle='CSPLS',
                          numero_agrement_mena='N°2024-0147/MENAPLN/SG/DGEPFIC', ville='Ouagadougou',
                          adresse_complete='Secteur 15, Ouaga 2000, 01 BP 1234 Ouagadougou 01',
                          telephone='+226 25 36 47 58 / 70 12 34 56', email='contact@lesavoir.bf')
    tampon = io.BytesIO()
    Image.new('RGB', (900, 900), (20, 60, 120)).save(tampon, 'PNG')
    identite.logo.save('logo.png', ContentFile(tampon.getvalue()), save=False)
    identite.cachet_etablissement.save('cachet.png', ContentFile(tampon.getvalue()), save=True)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True, libelle='2026-2027')
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Secondaire général second cycle')
    eleve = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Awa Wendpanga Christelle', nationalite='Burkinabè',
                       date_naissance=datetime.date(2010, 3, 14), lieu_naissance='Koudougou (province du Boulkiemdé), Burkina Faso',
                       nom_pere='OUEDRAOGO Wendpanga Abdoul Rasmané', nom_mere='SAWADOGO Kiswendsida Mariam Rasmata')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee,
                             classe=baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='Terminale D 2'))
    type_doc, _ = TypeDocument.objects.get_or_create(code='CERT_SCOL', defaults={'libelle': 'Certificat', 'categorie': 'SCOLARITE'})
    membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salimata Wendkouni')
    baker.make('parametres.SignataireDocument', cycle=cycle, type_document=type_doc, annee_scolaire=annee,
               membre_personnel_id=membre.id, fonction='Le Directeur Général du Complexe Scolaire', actif=True)
    tampon = io.BytesIO()
    Image.new('RGBA', (1654, 600), (0, 0, 0, 0)).save(tampon, 'PNG')
    membre.signature.save('kabore.png', ContentFile(tampon.getvalue()), save=True)

    documents, sources = [], []

    class HTMLEspion(core.pdf.HTML):
        def __init__(self, *args, **kwargs):
            sources.append(kwargs.get('string', ''))
            super().__init__(*args, **kwargs)

        def render(self, *args, **kwargs):
            document = super().render(*args, **kwargs)
            documents.append(document)
            return document

    mocker.patch('core.pdf.HTML', HTMLEspion)
    url = reverse('documents:certificat_scolarite', kwargs={'inscription_id': inscription.pk}) + '?format=pdf'
    assert client.get(url).status_code == 200 and len(documents) == 1
    assert len(documents[0].pages) == 1, 'le certificat de scolarité tient sur une seule page A5'
    assert '<div class="bas">' in sources[0] and f'src="{membre.signature.url}"' in sources[0]


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


@pytest.mark.django_db
def test_liste_personnel_pdf_qr_sous_le_recapitulatif(client, mocker):
    """Le code QR (réduit à 2,5 cm) suit immédiatement le tableau récapitulatif, calé à gauche, avant le signataire."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='POST')
    baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    html_cls = mocker.patch('core.pdf.HTML')
    html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'

    url = reverse('documents:liste_personnel_pdf', kwargs={'cycle_id': cycle.pk})
    assert client.get(url + '?format=pdf').status_code == 200

    html = html_cls.call_args.kwargs['string']
    assert re.search(r'\.qr-zone img \{ width: 2\.5cm; height: 2\.5cm; \}', html)
    assert 'border-top: 1px solid #aaa' not in html and 'justify-content: space-between' not in html
    corps = html[html.index('<body'):]
    assert corps.rfind('</table>') < corps.index('class="qr-zone"') < corps.index('<!-- Signataire -->')


def test_qr_bulletin_contenu_et_balise():
    """Le QR du bulletin trimestriel encode matricule, classe, trimestre et moyenne ; balise image auto-portée."""
    from documents.templatetags.qr_tags import _build_qr_bulletin_text, qr_bulletin

    assert _build_qr_bulletin_text('2024-0001', '6ème A', 'Trimestre 1', '2025-2026', '14,50') == (
        'MAT: 2024-0001\nCLA: 6ème A\nTRI: Trimestre 1 2025-2026\nMOY: 14,50/20')
    balise = qr_bulletin('2024-0001', '6ème A', 'Trimestre 1', '2025-2026', '14,50')
    assert balise.startswith('<img src="data:image/png;base64,') and 'alt="QR bulletin 2024-0001"' in balise


def test_qr_bulletin_annuel_contenu_et_balise():
    """Le QR du bulletin annuel encode matricule, classe, année scolaire et moyenne annuelle."""
    from documents.templatetags.qr_tags import _build_qr_bulletin_annuel_text, qr_bulletin_annuel

    assert _build_qr_bulletin_annuel_text('2024-0001', '6ème A', '2025-2026', '13,75') == (
        'MAT: 2024-0001\nCLA: 6ème A\nANN: 2025-2026\nMOY: 13,75/20')
    balise = qr_bulletin_annuel('2024-0001', '6ème A', '2025-2026', '13,75')
    assert balise.startswith('<img src="data:image/png;base64,') and 'alt="QR bulletin annuel 2024-0001"' in balise
