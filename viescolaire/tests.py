import re
from html import unescape

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestViescolaireViews:
    def test_conseil_list_redirect_anon(self, client):
        url = reverse('viescolaire:conseil_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_conseil_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('viescolaire:conseil_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_activite_list_redirect_anon(self, client):
        url = reverse('viescolaire:activite_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_activite_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('viescolaire:activite_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_sanction_list_redirect_anon(self, client):
        url = reverse('viescolaire:sanction_list')
        response = client.get(url)
        assert response.status_code == 302


class TestApercuEdtJours:
    """L'aperçu de génération d'EDT affiche le nom du jour côté serveur (plus de script inline,
    bloqué par la CSP) et seulement quand le jour change."""

    def test_jour_nom(self):
        from viescolaire.services import SeancePrevue
        seance = SeancePrevue(enseignement_id='x', jour=1, heure_debut='07:30', heure_fin='08:20',
                              matiere_nom='Maths', prof_nom='Zongo')
        assert seance.jour_nom == 'Lundi'
        seance.jour = 9
        assert seance.jour_nom == '9'

    @pytest.mark.django_db
    def test_apercu_sans_script_et_jour_affiche_une_fois(self):
        from django.template.loader import render_to_string
        from viescolaire.services import ResultatGeneration, SeancePrevue
        classe = baker.make('parametres.Classe')
        annee = baker.make('parametres.AnneeScolaire', etablissement=classe.etablissement)
        seances = [
            SeancePrevue('e1', 1, '07:30', '08:20', 'Maths', 'Zongo'),
            SeancePrevue('e2', 1, '08:20', '09:10', 'SVT', 'Kabore'),
            SeancePrevue('e3', 2, '07:30', '08:20', 'Anglais', 'Traore'),
        ]
        resultat = ResultatGeneration(seances=seances, nb_placees=3, nb_total=3)

        html = render_to_string('viescolaire/partials/edt_apercu.html',
                                {'classe': classe, 'annee': annee, 'mode': 'remplacer', 'resultat': resultat})

        assert '<script' not in html
        assert html.count('Lundi') == 1 and html.count('Mardi') == 1
        assert html.count('class="edt-gen-day-cell"') == 3


@pytest.mark.django_db
class TestPagesSansGestionnaireInline:
    """Sanction et appel de décision : aucun attribut on*, scripts et styles de page noncés (CSP)."""

    @staticmethod
    def _verifier_csp(html):
        assert not re.search(r'\son[a-z]+="', html)
        balises = re.findall(r'<(?:script(?![^>]*\ssrc=)|style)\b[^>]*>', html)
        assert balises and all('nonce="' in b for b in balises)

    def test_sanction_create_selecteur_classe(self, client):
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', etablissement=etab, role='DIRECTEUR'))
        classe = baker.make('parametres.Classe', etablissement=etab, actif=True)

        response = client.get(reverse('viescolaire:sanction_create') + f'?classe={classe.pk}')

        assert response.status_code == 200
        html = response.content.decode()
        self._verifier_csp(html)
        assert '<form method="get"' in html and 'name="classe"' in html and 'data-csp-submit-on-change' in html

    def test_appel_decision_traiter_bascule_nouvelle_decision(self, client):
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', etablissement=etab))
        classe = baker.make('parametres.Classe', etablissement=etab)
        appel = baker.make('viescolaire.AppelDecision', decision_conseil__conseil__classe=classe)

        response = client.get(reverse('viescolaire:appel_decision_traiter', kwargs={'appel_id': appel.pk}))

        assert response.status_code == 200
        html = response.content.decode()
        self._verifier_csp(html)
        assert "addEventListener('change', toggleNouvelleDecision)" in html


@pytest.mark.django_db
class TestEmploiDuTempsPdfUnePage:
    """Les emplois du temps (classe et professeur) tiennent sur une seule page A4
    paysage, même chargés : douze séances par jour sur six jours, intitulés longs,
    salles, enseignants, récapitulatif de douze enseignements et signataire (signature scannée embarquée)."""

    MATIERES = [
        ('MATH', 'Mathématiques'), ('SVT', 'Sciences de la Vie et de la Terre'),
        ('HG', 'Histoire-Géographie'), ('PC', 'Physique-Chimie'),
        ('EPS', 'Éducation Physique et Sportive'), ('FR', 'Français'),
        ('ANG', 'Anglais'), ('PHILO', 'Philosophie'), ('ECM', 'Éducation Civique et Morale'),
        ('ALL', 'Allemand'), ('INFO', 'Informatique et Sciences du Numérique'), ('ESP', 'Espagnol Langue Vivante 2'),
    ]

    @pytest.fixture
    def espion(self, mocker):
        pytest.importorskip('weasyprint')
        import core.pdf

        documents = []

        class HTMLEspion(core.pdf.HTML):
            def write_pdf(self, target=None, **kwargs):
                document = self.render()
                documents.append(document)
                return document.write_pdf(target, **kwargs)

        mocker.patch('viescolaire.views.edt.WeasyHTML', HTMLEspion)
        return documents

    @pytest.fixture
    def contexte(self, client, settings, tmp_path):
        import io
        from datetime import time
        from django.core.files.base import ContentFile
        from PIL import Image
        from parametres.models import TypeDocument
        settings.MEDIA_ROOT = tmp_path
        etab = baker.make('etablissements.Etablissement', nom='COMPLEXE SCOLAIRE LE SAVOIR')
        baker.make('parametres.IdentiteEtablissement', etablissement=etab, ville='Ouagadougou')
        client.force_login(baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True, libelle='2026-2027')
        cycle = baker.make('parametres.Cycle', etablissement=etab)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='TLE', nom='Terminale D2')
        prof = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='OUEDRAOGO',
                          prenom='Abdoul Rasmané', fonction='Professeur certifié', matricule='PC-2019-0456')
        type_doc, _ = TypeDocument.objects.get_or_create(code='EMPLOI_DU_TEMPS', defaults={'libelle': 'Emploi du temps', 'categorie': 'SCOLARITE', 'actif': True})
        baker.make('parametres.SignataireDocument', cycle=cycle, type_document=type_doc, annee_scolaire=annee,
                   membre_personnel_id=prof.id, fonction='Le Censeur', actif=True)
        tampon = io.BytesIO()
        Image.new('RGBA', (600, 220), (0, 0, 0, 0)).save(tampon, 'PNG')
        prof.signature.save('censeur.png', ContentFile(tampon.getvalue()), save=True)
        creneaux = [(time(7 + i, 0), time(8 + i, 0)) for i in range(6)] + \
                   [(time(14 + i, 0), time(15 + i, 0)) for i in range(6)]
        for code, nom in self.MATIERES:
            matiere = baker.make('pedagogie.Matiere', code=code, nom=nom)
            enseignement = baker.make('pedagogie.Enseignement', matiere=matiere, classe=classe,
                                      annee_scolaire=annee, personnel=prof, heures_hebdomadaires=6)
            for jour in range(1, 7):
                debut, fin = creneaux[self.MATIERES.index((code, nom))]
                baker.make('viescolaire.SeanceCours', enseignement=enseignement, jour=jour,
                           heure_debut=debut, heure_fin=fin, salle=f'B{jour}')
        return classe, prof

    def _une_page(self, espion, reponse):
        assert reponse.status_code == 200 and reponse.content.startswith(b'%PDF')
        assert len(espion) == 1
        pages = espion[0].pages
        # A4 paysage : 297 × 210 mm
        assert round(pages[0].width) == 1123 and round(pages[0].height) == 794
        from core.tests.test_media_pdf import images_rendues
        assert 'msig-img' in images_rendues(pages[0]), 'signature scannée du signataire embarquée'
        return len(pages)

    def test_classe_une_page(self, client, espion, contexte):
        classe, _ = contexte
        nb = self._une_page(espion, client.get(reverse('viescolaire:emploi_du_temps_pdf', args=[classe.pk])))
        assert nb == 1, f'{nb} pages'

    def test_professeur_une_page(self, client, espion, contexte):
        _, prof = contexte
        nb = self._une_page(espion, client.get(reverse('viescolaire:emploi_du_temps_prof_pdf', args=[prof.pk])))
        assert nb == 1, f'{nb} pages'

    def test_signataire_configure_pour_l_emploi_du_temps(self, client, mocker, contexte):
        """Les deux emplois du temps portent le signataire configuré pour « Emploi du Temps » (fonction, signature,
        NOM Prénom) et non le dernier signataire enregistré sur le cycle (ici le directeur, pour les bulletins)."""
        from parametres.models import AnneeScolaire, TypeDocument
        classe, prof = contexte
        directeur = baker.make('personnel.MembrePersonnel', etablissement=classe.etablissement, nom='SAWADOGO', prenom='Boureima')
        baker.make('parametres.SignataireDocument', cycle=classe.cycle, type_document=TypeDocument.objects.get(code='BULLETIN'),
                   annee_scolaire=AnneeScolaire.objects.get(etablissement=classe.etablissement),
                   membre_personnel_id=directeur.id, fonction='Le Directeur', actif=True)
        weasy = mocker.patch('viescolaire.views.edt.WeasyHTML')
        for nom_url, pk in (('viescolaire:emploi_du_temps_pdf', classe.pk), ('viescolaire:emploi_du_temps_prof_pdf', prof.pk)):
            assert client.get(reverse(nom_url, args=[pk])).status_code == 200, nom_url
            html = weasy.call_args.kwargs['string']
            assert 'Le Censeur' in html and '<div class="sig-name">OUEDRAOGO Abdoul Rasmané</div>' in html, nom_url
            assert '<div class="sig-sign"><img class="msig-img" src="/media/personnel/signatures/' in html, nom_url
            assert 'SAWADOGO' not in html, nom_url


@pytest.mark.django_db
class TestConfigEDT:
    """Horaires de cours et jours de classe configurables : page, grilles, PDF, saisie manuelle, générateur."""

    DONNEES = {
        'heure_debut_matin': '07:00', 'heure_fin_matin': '12:00',
        'heure_debut_aprem': '15:00', 'heure_fin_aprem': '17:00',
        'duree_seance': 55, 'jours_actifs': [1, 2, 3, 4, 5],
    }

    @pytest.fixture
    def ecole(self, client):
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
        prof = baker.make('personnel.MembrePersonnel', etablissement=etab)
        enseignement = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, personnel=prof,
                                  heures_hebdomadaires=2, est_actif=True)
        return {'etab': etab, 'annee': annee, 'classe': classe, 'prof': prof, 'enseignement': enseignement}

    @pytest.fixture
    def pdf_html(self, mocker):
        """Remplace WeasyPrint et capture le HTML rendu."""
        rendus = []

        class FauxHTML:
            def __init__(self, string=None, **kwargs):
                rendus.append(string)

            def write_pdf(self, target=None, **kwargs):
                target.write(b'%PDF-1.4')

        mocker.patch('viescolaire.views.edt.WeasyHTML', FauxHTML)
        return rendus

    def _colonnes(self, html):
        """En-têtes de la grille (premier tableau de la page)."""
        return re.findall(r'<th[^>]*>\s*([^<]*?)\s*</th>', html.split('</thead>')[0])

    def test_defauts_sans_configuration(self, client, ecole):
        from viescolaire.models import ConfigEDT
        config = ConfigEDT.pour(ecole['etab'])
        assert config._state.adding and config.get_jours_actifs() == [1, 2, 3, 4, 5, 6]
        assert config.plages_libelle() == '07:30–12:00 et 14:00–17:20' and len(config.creneaux()) == 9
        html = client.get(reverse('viescolaire:emploi_du_temps_index')).content.decode()
        assert 'Horaires et jours de classe' in html and reverse('viescolaire:edt_config') in html

    def test_page_configuration(self, client, ecole):
        from viescolaire.models import ConfigEDT
        url = reverse('viescolaire:edt_config')
        html = client.get(url).content.decode()
        assert 'value="07:30"' in html and '07:30–08:20' in html and '9 séances de 50 min' in html
        reponse = client.post(url, self.DONNEES)
        assert reponse.status_code == 302 and reponse.url == reverse('viescolaire:emploi_du_temps_index')
        config = ConfigEDT.objects.get(etablissement=ecole['etab'])
        assert config.get_jours_actifs() == [1, 2, 3, 4, 5] and config.duree_seance == 55
        assert config.plages_libelle() == '07:00–12:00 et 15:00–17:00' and len(config.creneaux()) == 7
        # Journée continue : après-midi vide
        client.post(url, {**self.DONNEES, 'heure_debut_aprem': '', 'heure_fin_aprem': ''})
        config.refresh_from_db()
        assert config.heure_debut_aprem is None and config.plages_libelle() == '07:00–12:00'

    @pytest.mark.parametrize('donnees, champ', [
        ({'heure_fin_matin': '07:00'}, 'heure_fin_matin'),
        ({'heure_fin_aprem': ''}, 'heure_fin_aprem'),
        ({'heure_debut_aprem': '11:00'}, 'heure_debut_aprem'),
        ({'heure_fin_aprem': '15:00'}, 'heure_fin_aprem'),
        ({'duree_seance': 10}, 'duree_seance'),
        ({'jours_actifs': []}, 'jours_actifs'),
    ])
    def test_validation(self, client, ecole, donnees, champ):
        from viescolaire.models import ConfigEDT
        reponse = client.post(reverse('viescolaire:edt_config'), {**self.DONNEES, **donnees})
        assert reponse.status_code == 200 and reponse.context['form'].errors.keys() == {champ}
        assert not ConfigEDT.objects.exists()

    def test_reserve_a_la_direction(self, client, ecole):
        client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=ecole['etab'], must_change_password=False))
        assert client.get(reverse('viescolaire:edt_config')).status_code in (302, 403)
        html = client.get(reverse('viescolaire:emploi_du_temps_index')).content.decode()
        assert reverse('viescolaire:edt_config') not in html

    def test_grilles_et_pdf_suivent_les_jours_de_classe(self, client, ecole, pdf_html):
        from datetime import time
        baker.make('viescolaire.ConfigEDT', etablissement=ecole['etab'], jours_actifs=[1, 2, 3, 4, 5],
                   heure_debut_matin=time(7, 0), heure_fin_matin=time(12, 0),
                   heure_debut_aprem=None, heure_fin_aprem=None, duree_seance=60)
        baker.make('viescolaire.SeanceCours', enseignement=ecole['enseignement'], jour=1,
                   heure_debut=time(8, 0), heure_fin=time(9, 0))
        classe, prof = ecole['classe'], ecole['prof']
        attendu = ['Horaire', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        html = client.get(reverse('viescolaire:emploi_du_temps', args=[classe.pk])).content.decode()
        assert self._colonnes(html) == attendu and 'Samedi' not in html
        assert 'Heures de cours : 07:00–12:00 · séances de 60 min' in html and 'max="12:00"' in html
        assert self._colonnes(client.get(reverse('viescolaire:emploi_du_temps_prof', args=[prof.pk])).content.decode()) == attendu
        client.get(reverse('viescolaire:emploi_du_temps_pdf', args=[classe.pk]))
        client.get(reverse('viescolaire:emploi_du_temps_prof_pdf', args=[prof.pk]))
        assert len(pdf_html) == 2
        for rendu in pdf_html:
            assert self._colonnes(rendu)[:5] == attendu[1:] and 'Samedi' not in rendu and 'width: 20%' in rendu
        # Une séance existante hors jours de classe reste visible
        baker.make('viescolaire.SeanceCours', enseignement=ecole['enseignement'], jour=6,
                   heure_debut=time(8, 0), heure_fin=time(9, 0))
        html = client.get(reverse('viescolaire:emploi_du_temps', args=[classe.pk])).content.decode()
        assert self._colonnes(html) == attendu + ['Samedi']

    def test_seance_manuelle_respecte_la_configuration(self, client, ecole):
        from viescolaire.models import SeanceCours
        baker.make('viescolaire.ConfigEDT', etablissement=ecole['etab'], jours_actifs=[1, 2, 3, 4, 5])
        url = reverse('viescolaire:seance_create', args=[ecole['classe'].pk])
        base = {'annee': ecole['annee'].pk, 'enseignement': ecole['enseignement'].pk, 'heure_debut': '08:00', 'heure_fin': '08:50'}
        for donnees, message in [
            ({'jour': 6}, "Samedi n'est pas un jour de classe configuré."),
            ({'jour': 2, 'heure_debut': '12:30', 'heure_fin': '13:20'},
             'Horaire hors des heures de cours configurées (07:30–12:00 et 14:00–17:20).'),
            ({'jour': 2, 'heure_debut': '11:30', 'heure_fin': '14:20'},
             'Horaire hors des heures de cours configurées (07:30–12:00 et 14:00–17:20).'),
        ]:
            reponse = client.post(url, {**base, **donnees}, follow=True)
            assert message in unescape(reponse.content.decode())
        assert not SeanceCours.objects.exists()
        assert client.post(url, {**base, 'jour': 2}).status_code == 302
        assert SeanceCours.objects.filter(jour=2, heure_debut='08:00').exists()
        assert client.post(url, {**base, 'jour': 'x'}).status_code == 400

    def test_generateur_utilise_la_configuration(self, ecole):
        from datetime import time
        from viescolaire.models import ConfigEDT
        from viescolaire.services import GenerateurEDT, _build_slots
        config = baker.make('viescolaire.ConfigEDT', etablissement=ecole['etab'], jours_actifs=[1, 3],
                            heure_debut_matin=time(8, 0), heure_fin_matin=time(10, 0),
                            heure_debut_aprem=None, heure_fin_aprem=None, duree_seance=60)
        assert _build_slots(config) == [(1, time(8), time(9)), (1, time(9), time(10)),
                                        (3, time(8), time(9)), (3, time(9), time(10))]
        gen = GenerateurEDT(ecole['classe'], ecole['annee'], config)
        assert gen.duree == 60 and len(gen.slots) == 4
        assert len(GenerateurEDT(ecole['classe'], ecole['annee'], None).slots) == 54
        assert ConfigEDT.pour(None)._state.adding


@pytest.mark.django_db
class TestRetraitSeance:
    """Retrait d'une séance depuis la grille d'un professeur ou d'une classe."""

    @pytest.fixture
    def ecole(self, client):
        from datetime import time
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab), nom='6ème A')
        prof = baker.make('personnel.MembrePersonnel', etablissement=etab)
        enseignement = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, personnel=prof,
                                  matiere=baker.make('pedagogie.Matiere', nom='Mathématiques'), est_actif=True)
        seances = [baker.make('viescolaire.SeanceCours', enseignement=enseignement, jour=jour,
                              heure_debut=time(8, 0), heure_fin=time(8, 50)) for jour in (1, 2)]
        return {'etab': etab, 'annee': annee, 'classe': classe, 'prof': prof, 'seances': seances}

    def _formulaire(self, html, seance):
        """Formulaire de retrait de la séance dans la grille, avec sa cible de retour."""
        motif = re.compile(r'<form method="post" action="%s"[^>]*data-csp-confirm-submit="Retirer cette séance de Mathématiques \?">'
                           r'.*?name="retour" value="(\w+)"' % reverse('viescolaire:seance_delete', args=[seance.pk]), re.S)
        return motif.search(html)

    def test_retrait_depuis_la_grille_du_professeur(self, client, ecole):
        from viescolaire.models import SeanceCours
        lundi, mardi = ecole['seances']
        url_prof = reverse('viescolaire:emploi_du_temps_prof', args=[ecole['prof'].pk])
        html = client.get(url_prof).content.decode()
        assert self._formulaire(html, lundi).group(1) == 'prof' and self._formulaire(html, mardi)
        reponse = client.post(reverse('viescolaire:seance_delete', args=[lundi.pk]), {'retour': 'prof'})
        assert reponse.status_code == 302 and reponse.url == f"{url_prof}?annee={ecole['annee'].pk}"
        assert list(SeanceCours.objects.values_list('jour', flat=True)) == [2]
        html = unescape(client.get(reponse.url).content.decode())
        assert 'Séance retirée : Mathématiques — Lundi 08:00–08:50 (6ème A).' in html
        assert not self._formulaire(html, lundi) and self._formulaire(html, mardi)

    def test_retrait_depuis_la_grille_de_la_classe(self, client, ecole):
        from viescolaire.models import SeanceCours
        lundi, _ = ecole['seances']
        url_classe = reverse('viescolaire:emploi_du_temps', args=[ecole['classe'].pk])
        assert self._formulaire(client.get(url_classe).content.decode(), lundi).group(1) == 'classe'
        reponse = client.post(reverse('viescolaire:seance_delete', args=[lundi.pk]), {'retour': 'classe'})
        assert reponse.status_code == 302 and reponse.url == f"{url_classe}?annee={ecole['annee'].pk}"
        assert SeanceCours.objects.count() == 1

    def test_isolation_etablissement_et_droit(self, client, ecole):
        from parametres import droits
        from parametres.models import DroitAcces
        from viescolaire.models import SeanceCours
        autre = baker.make('viescolaire.SeanceCours', enseignement=baker.make('pedagogie.Enseignement', personnel=None))
        assert client.post(reverse('viescolaire:seance_delete', args=[autre.pk])).status_code == 404
        # Action « modifier » retirée aux enseignants : ni bouton, ni suppression
        DroitAcces.objects.create(role='ENSEIGNANT', module='viescolaire', fonctionnalite='/viescolaire/emploi-du-temps/',
                                  action='modifier', autorise=False)
        droits.invalider_cache()
        client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=ecole['etab'], must_change_password=False))
        html = client.get(reverse('viescolaire:emploi_du_temps_prof', args=[ecole['prof'].pk])).content.decode()
        assert 'Mathématiques' in html and 'edt-course-remove' not in html
        lundi, _ = ecole['seances']
        assert client.post(reverse('viescolaire:seance_delete', args=[lundi.pk]), {'retour': 'prof'}).status_code in (302, 403)
        assert SeanceCours.objects.count() == 3
        droits.invalider_cache()


@pytest.mark.django_db
class TestFicheSuivi:
    """Accès à la fiche de suivi depuis les listes (ligne cliquable et bouton) et isolation par établissement."""

    @pytest.fixture
    def ecole(self, client):
        from datetime import date
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab), actif=True)
        eleve = baker.make('inscriptions.Eleve', nom='SAWADOGO', prenom='Aïcha', date_naissance=date(2012, 5, 3))
        inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
        return {'etab': etab, 'annee': annee, 'inscription': inscription}

    def test_listes_pointent_vers_la_fiche(self, client, ecole):
        url = reverse('viescolaire:fiche_suivi_eleve', args=[ecole['inscription'].pk])
        html = client.get(reverse('viescolaire:fiches_suivi_list')).content.decode()
        assert f'data-csp-href="{url}"' in html and f'<a href="{url}"' in html
        html = client.get(reverse('viescolaire:capital_points_list')).content.decode()
        assert f'data-csp-href="{url}#sanctions"' in html and f'<a href="{url}#sanctions"' in html
        reponse = client.get(url)
        assert reponse.status_code == 200 and 'SAWADOGO' in reponse.content.decode()

    def test_aucune_url_de_fiche_codee_en_dur(self):
        """L'ancienne navigation JS forgeait /viescolaire/fiche-suivi/<id>/ (route inexistante → 404)."""
        from pathlib import Path
        racine = Path(__file__).resolve().parents[1]
        assert 'fiche-suivi' not in (racine / 'static/js/csp_handlers.js').read_text(encoding='utf-8')
        assert not [f for f in racine.rglob('*.html') if 'staticfiles' not in f.parts
                    and 'data-csp-href-template' in f.read_text(encoding='utf-8')]

    def test_isolation_etablissement(self, client, ecole):
        from datetime import date
        autre = baker.make('inscriptions.Inscription', eleve=baker.make('inscriptions.Eleve', date_naissance=date(2012, 1, 1)))
        assert client.get(reverse('viescolaire:fiche_suivi_eleve', args=[autre.pk])).status_code == 404


@pytest.mark.django_db
def test_enregistrement_sanction_avec_journal_audit():
    """En production le journal d'audit appelle str(sanction) à chaque enregistrement : type_sanction est une relation."""
    from core.models import AuditLog
    from core.signals import disable_audit, enable_audit
    type_sanction = baker.make('parametres.TypeSanction', libelle='Avertissement', code='AVERT')
    enable_audit()
    try:
        sanction = baker.make('viescolaire.SanctionDisciplinaire', type_sanction=type_sanction)
    finally:
        disable_audit()
    assert 'Avertissement' in str(sanction)
    assert AuditLog.objects.filter(model_name='sanctiondisciplinaire', object_id=str(sanction.pk)).exists()


@pytest.mark.django_db
class TestConflitsEDT:
    """Une classe, un professeur ou une salle ne peuvent pas être occupés deux fois au même moment."""

    @pytest.fixture
    def ecole(self, client):
        from datetime import time
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        cycle = baker.make('parametres.Cycle', etablissement=etab)
        c6, c5 = (baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom=nom) for nom in ('6e A', '5e B'))
        p, q = (baker.make('personnel.MembrePersonnel', etablissement=etab, nom=nom, prenom='Ali') for nom in ('KABORE', 'ZONGO'))
        maths = baker.make('pedagogie.Enseignement', classe=c6, annee_scolaire=annee, personnel=p, est_actif=True,
                           matiere=baker.make('pedagogie.Matiere', nom='Mathématiques'), heures_hebdomadaires=1)
        physique = baker.make('pedagogie.Enseignement', classe=c6, annee_scolaire=annee, personnel=q, est_actif=True,
                              matiere=baker.make('pedagogie.Matiere', nom='Physique'), heures_hebdomadaires=1)
        francais = baker.make('pedagogie.Enseignement', classe=c5, annee_scolaire=annee, personnel=p, est_actif=True,
                              matiere=baker.make('pedagogie.Matiere', nom='Français'), heures_hebdomadaires=1)
        anglais = baker.make('pedagogie.Enseignement', classe=c5, annee_scolaire=annee, personnel=q, est_actif=True,
                             matiere=baker.make('pedagogie.Matiere', nom='Anglais'), heures_hebdomadaires=1)
        seance = baker.make('viescolaire.SeanceCours', enseignement=maths, jour=1, heure_debut=time(8, 0), heure_fin=time(8, 50), salle='S1')
        return {'etab': etab, 'annee': annee, 'c6': c6, 'c5': c5, 'p': p, 'maths': maths, 'physique': physique,
                'francais': francais, 'anglais': anglais, 'seance': seance}

    def _ajouter(self, client, ecole, classe, enseignement, **donnees):
        base = {'annee': ecole['annee'].pk, 'enseignement': enseignement.pk, 'jour': 1, 'heure_debut': '08:00', 'heure_fin': '08:50'}
        return client.post(reverse('viescolaire:seance_create', args=[classe.pk]), {**base, **donnees}, follow=True)

    def test_saisie_refusee_pour_la_classe_le_professeur_et_la_salle(self, client, ecole):
        from viescolaire.models import SeanceCours
        cas = [
            (ecole['c6'], ecole['physique'], {'heure_debut': '08:30', 'heure_fin': '09:20'},
             'la classe 6e A a déjà Mathématiques le lundi 08:00–08:50'),
            (ecole['c5'], ecole['francais'], {},
             'KABORE Ali enseigne déjà Mathématiques en 6e A le lundi 08:00–08:50'),
            (ecole['c5'], ecole['anglais'], {'salle': 's1'},
             'la salle s1 est déjà occupée par 6e A (Mathématiques) le lundi 08:00–08:50'),
        ]
        for classe, enseignement, donnees, motif in cas:
            html = unescape(self._ajouter(client, ecole, classe, enseignement, **donnees).content.decode())
            assert f'Séance non ajoutée : {motif}.' in html, motif
        assert SeanceCours.objects.count() == 1

        # Enchaînée (08:50) ou autre salle : acceptée
        self._ajouter(client, ecole, ecole['c6'], ecole['physique'], heure_debut='08:50', heure_fin='09:40')
        self._ajouter(client, ecole, ecole['c5'], ecole['anglais'], salle='S2')
        assert SeanceCours.objects.count() == 3

    def test_grille_signale_les_chevauchements_existants(self, client, ecole):
        from datetime import time
        from viescolaire.edt_conflits import conflits_classe
        baker.make('viescolaire.SeanceCours', enseignement=ecole['physique'], jour=1, heure_debut=time(8, 30), heure_fin=time(9, 20))
        baker.make('viescolaire.SeanceCours', enseignement=ecole['francais'], jour=1, heure_debut=time(8, 0), heure_fin=time(8, 50))
        baker.make('viescolaire.SeanceCours', enseignement=ecole['anglais'], jour=2, heure_debut=time(8, 0), heure_fin=time(8, 50))
        motifs = sorted(motif for _, motif in conflits_classe(ecole['c6'], ecole['annee']))
        assert motifs == ['KABORE Ali enseigne déjà Français en 5e B le lundi 08:00–08:50',
                          'la classe 6e A a déjà Physique le lundi 08:30–09:20']
        html = unescape(client.get(reverse('viescolaire:emploi_du_temps', args=[ecole['c6'].pk]), {'annee': ecole['annee'].pk}).content.decode())
        assert "2 conflits d'emploi du temps" in html and 'Lundi 08:00–08:50 · Mathématiques : la classe 6e A a déjà Physique' in html
        html = unescape(client.get(reverse('viescolaire:emploi_du_temps', args=[ecole['c5'].pk]), {'annee': ecole['annee'].pk}).content.decode())
        assert "1 conflit d'emploi du temps" in html

    def test_generateur_evite_un_professeur_occupe_dans_une_autre_classe(self, ecole):
        from datetime import time
        from viescolaire.services import GenerateurEDT
        config = baker.make('viescolaire.ConfigEDT', etablissement=ecole['etab'], jours_actifs=[1],
                            heure_debut_matin=time(8, 0), heure_fin_matin=time(10, 0),
                            heure_debut_aprem=time(14, 0), heure_fin_aprem=time(15, 0), duree_seance=60)
        ecole['seance'].delete()
        for hd, hf in ((time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))):   # KABORE enseigne en 5e B toute la matinée
            baker.make('viescolaire.SeanceCours', enseignement=ecole['francais'], jour=1, heure_debut=hd, heure_fin=hf)
        ecole['physique'].delete()
        for _ in range(5):
            resultat = GenerateurEDT(ecole['c6'], ecole['annee'], config).generer()
            assert [(s.jour, s.heure_debut) for s in resultat.seances] == [(1, '14:00')]

    def test_application_de_la_generation_ignore_les_conflits(self, client, ecole):
        import json
        from viescolaire.models import SeanceCours
        session = client.session
        session[f"edt_preview_{ecole['c6'].pk}"] = json.dumps([
            {'enseignement_id': str(ecole['physique'].pk), 'jour': 1, 'heure_debut': '08:00', 'heure_fin': '08:50'},
            {'enseignement_id': str(ecole['physique'].pk), 'jour': 2, 'heure_debut': '08:00', 'heure_fin': '08:50'},
        ])
        session.save()
        reponse = client.post(reverse('viescolaire:edt_generer', args=[ecole['c6'].pk]),
                              {'annee': ecole['annee'].pk, 'action': 'appliquer', 'mode': 'completer'})
        assert reponse.status_code == 200 and reponse.headers.get('HX-Refresh') == 'true'
        assert sorted(SeanceCours.objects.filter(enseignement=ecole['physique']).values_list('jour', flat=True)) == [2]
        html = unescape(client.get(reverse('viescolaire:emploi_du_temps', args=[ecole['c6'].pk]), {'annee': ecole['annee'].pk}).content.decode())
        assert '1 séance(s) non placée(s) pour éviter un conflit : Physique (la classe 6e A a déjà Mathématiques le lundi 08:00–08:50).' in html
