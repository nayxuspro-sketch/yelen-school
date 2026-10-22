import re

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
    salles, enseignants, récapitulatif de douze enseignements et signataire."""

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

        mocker.patch('viescolaire.views.WeasyHTML', HTMLEspion)
        return documents

    @pytest.fixture
    def contexte(self, client):
        from datetime import time
        from parametres.models import TypeDocument
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
        return len(pages)

    def test_classe_une_page(self, client, espion, contexte):
        classe, _ = contexte
        nb = self._une_page(espion, client.get(reverse('viescolaire:emploi_du_temps_pdf', args=[classe.pk])))
        assert nb == 1, f'{nb} pages'

    def test_professeur_une_page(self, client, espion, contexte):
        _, prof = contexte
        nb = self._une_page(espion, client.get(reverse('viescolaire:emploi_du_temps_prof_pdf', args=[prof.pk])))
        assert nb == 1, f'{nb} pages'
