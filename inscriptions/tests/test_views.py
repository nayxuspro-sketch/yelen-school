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
def test_liste_des_eleves_pdf_entete_avec_logo(client, settings, tmp_path, mocker):
    """L'en-tête du PDF « Liste des élèves » porte le logo et l'identité de l'établissement : la vue ne passait
    que ``identite`` au socle PDF, jamais ``logo_url`` — la cellule du logo restait vide."""
    import io
    import core.pdf
    from django.core.files.base import ContentFile
    from PIL import Image
    pytest.importorskip('weasyprint')
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, must_change_password=False))
    identite = baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='COMPLEXE SCOLAIRE LE SAVOIR',
                          numero_agrement_mena='2019-0456/MENAPLN')
    tampon = io.BytesIO()
    Image.new('RGB', (120, 120), (0, 90, 160)).save(tampon, 'PNG')
    identite.logo.save('logo.png', ContentFile(tampon.getvalue()), save=True)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
    baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee)
    sources, documents = [], []

    class HTMLEspion(core.pdf.HTML):
        def __init__(self, *args, **kwargs):
            sources.append(kwargs['string'])
            super().__init__(*args, **kwargs)

        def write_pdf(self, target=None, **kwargs):
            document = self.render()
            documents.append(document)
            return document.write_pdf(target, **kwargs)
    mocker.patch('inscriptions.views._WeasyHTML', HTMLEspion)

    def images(box):
        propres = [box.element.get('alt')] if getattr(box, 'element_tag', None) == 'img' else []
        return propres + [alt for enfant in getattr(box, 'children', ()) for alt in images(enfant)]

    assert client.get(reverse('inscriptions:eleve_list_pdf')).status_code == 200
    html = sources[0]
    assert f'<td class="pdf-entete-logo"><img src="http://testserver{identite.logo.url}" alt="Logo"></td>' in html
    assert 'COMPLEXE SCOLAIRE LE SAVOIR' in html and 'N° Agrément : 2019-0456/MENAPLN' in html
    assert 'Logo' in images(documents[0].pages[0]._page_box), "logo réellement rendu dans l'en-tête"


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
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, telephone='25 36 47 58')
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

    attendu.append(f"VALABLE POUR L'ANNÉE SCOLAIRE : {annee.libelle}")   # mention en gras au bas de la carte
    attendu.append('Tél : 25 36 47 58')   # téléphone de l'établissement dans l'en-tête

    assert client.get(reverse('inscriptions:eleve_carte', kwargs={'pk': eleve.pk}) + '?format=pdf').status_code == 200
    carte = unescape(weasy.call_args.kwargs['string'])
    assert all(texte in carte for texte in attendu) and carte.count('class="carte"') == 1   # une seule face
    assert 'Verso' not in carte and 'Recto' not in carte and 'Cachet et signature' not in carte

    assert client.get(reverse('inscriptions:classe_cartes_pdf', kwargs={'pk': classe.pk})).status_code == 200
    cartes = unescape(weasy.call_args.kwargs['string'])
    assert all(texte in cartes for texte in attendu)
    for html in (carte, cartes):   # en-tête clair, « CARTE SCOLAIRE » en gras lisible, mention en gras
        assert re.search(r'\.carte-header \{[^}]*background: #f5f5f5;', html) and '.carte-header {\n    background: #111' not in html
        assert re.search(r'\.label-carte \{ font-size: 6pt; font-weight: 700; color: #111;', html)
        assert re.search(r'\.validite \{ font-size: 4\.5pt; font-weight: 700;', html)
        assert re.search(r'\.etab-tel \{ font-size: 4pt;', html)
        # lignes Résidence / Père / Mère / N° d'urgence en 5 pt, la dernière en gras
        assert re.search(r'\.contacts \{[^}]*font-size: 5pt;', html) and '.contacts .urgence { font-weight: 700;' in html
        assert '<span class="lbl urgence">N° d\'urgence :</span><span class="val urgence">' in html

    apercu = unescape(client.get(reverse('inscriptions:eleve_carte', kwargs={'pk': eleve.pk})).content.decode())
    assert all(texte in apercu for texte in attendu) and 'Verso' not in apercu and 'Recto' not in apercu
    assert 'font-size:0.6rem; line-height:1.2;' in apercu and '<span style="color:#0A1628; font-weight:700;">N° d\'urgence :</span>' in apercu


@pytest.mark.django_db
def test_carte_scolaire_signature_du_signataire_sous_la_photo(client, settings, tmp_path, mocker):
    """Sous la photo de l'élève : la signature scannée du signataire de la Carte d'Identité Scolaire (le directeur),
    puis son NOM et son prénom — carte seule, cartes de classe et aperçu. Sans image, l'espace reste vierge."""
    import datetime
    import io
    import core.pdf
    from django.core.files.base import ContentFile
    from PIL import Image
    from core.tests.test_media_pdf import images_rendues
    from parametres.models import TypeDocument
    pytest.importorskip('weasyprint')
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, must_change_password=False))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='POST')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    eleve = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Abdoul', genre='M', date_naissance=datetime.date(2012, 5, 12), photo='')
    baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
    directeur = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Issa')
    type_doc, _ = TypeDocument.objects.get_or_create(code='CARTE_ID', defaults={'libelle': "Carte d'Identité Scolaire", 'categorie': 'SCOLARITE', 'actif': True})
    baker.make('parametres.SignataireDocument', cycle=cycle, type_document=type_doc, annee_scolaire=annee,
               membre_personnel_id=directeur.id, fonction='Le Directeur', actif=True)
    tampon = io.BytesIO()
    Image.new('RGBA', (600, 220), (0, 0, 0, 0)).save(tampon, 'PNG')
    directeur.signature.save('directeur.png', ContentFile(tampon.getvalue()), save=True)

    documents = []

    class HTMLEspion(core.pdf.HTML):
        def write_pdf(self, target=None, **kwargs):
            document = self.render()
            documents.append(document)
            return document.write_pdf(target, **kwargs)
    mocker.patch('inscriptions.views._WeasyHTML', HTMLEspion)

    def boite(box, classe_css):
        if classe_css in (box.element.get('class', '') if getattr(box, 'element', None) is not None else '').split():
            return box
        return next((b for enfant in getattr(box, 'children', ()) if (b := boite(enfant, classe_css))), None)

    def texte(box):
        return ''.join(getattr(b, 'text', '') for b in box.descendants())

    assert client.get(reverse('inscriptions:eleve_carte', kwargs={'pk': eleve.pk}) + '?format=pdf').status_code == 200
    page = documents[-1].pages[0]
    assert images_rendues(page) == ['msig-img'], 'signature scannée embarquée dans la carte'
    photo, signature, nom, prenom, corps, pied = (
        boite(page._page_box, c) for c in ('photo-box', 'msig-img', 'sign-nom', 'sign-prenom', 'carte-body', 'carte-footer'))
    assert photo.position_y + photo.height <= signature.position_y, 'la signature est sous la photo'
    assert (texte(nom), texte(prenom)) == ('KABORE', 'Issa')
    assert signature.position_y + signature.height <= nom.position_y <= prenom.position_y, 'NOM puis prénom sous la signature'
    assert prenom.position_y + prenom.height <= corps.content_box_y() + corps.height < pied.position_y, \
        'le bloc signataire tient dans le corps de la carte, au-dessus du pied'
    for b in (signature, nom, prenom):
        assert abs((b.position_x + b.border_width() / 2) - (photo.position_x + photo.border_width() / 2)) < 0.5, 'centré sous la photo'

    assert client.get(reverse('inscriptions:classe_cartes_pdf', kwargs={'pk': classe.pk})).status_code == 200
    page_lot = documents[-1].pages[0]
    assert images_rendues(page_lot) == ['msig-img'] and texte(boite(page_lot._page_box, 'sign-nom')) == 'KABORE'

    apercu = client.get(reverse('inscriptions:eleve_carte', kwargs={'pk': eleve.pk})).content.decode()
    assert f'<img src="{directeur.signature.url}" alt=""' in apercu and '>KABORE</div>' in apercu and '>Issa</div>' in apercu

    directeur.signature.delete(save=True)   # sans image : espace vierge de même hauteur, nom conservé
    assert client.get(reverse('inscriptions:eleve_carte', kwargs={'pk': eleve.pk}) + '?format=pdf').status_code == 200
    page = documents[-1].pages[0]
    zone, nom_sans = boite(page._page_box, 'photo-sign'), boite(page._page_box, 'sign-nom')
    assert images_rendues(page) == [] and texte(nom_sans) == 'KABORE' and nom_sans.position_y == nom.position_y
    assert round(zone.height * 25.4 / 96, 1) == 5.0
