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
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False, est_tous_cycles=True)
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

    def test_titre_porte_l_annee_scolaire_courante(self, client, contexte, mocker):
        etab, user, actif, inactif = contexte
        client.force_login(user)
        html_cls = mocker.patch('core.pdf.HTML')
        html_cls.return_value.write_pdf.return_value = b'%PDF-1.7 test'

        assert client.get(reverse('personnel:personnel_list_pdf')).status_code == 200
        assert '<div class="doc-title">Liste du personnel</div>' in html_cls.call_args.kwargs['string']

        baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)
        assert client.get(reverse('personnel:personnel_list_pdf')).status_code == 200
        assert 'Liste du personnel – Année scolaire 2026-2027' in html_cls.call_args.kwargs['string']

    @pytest.fixture
    def html_du_pdf(self, client, monkeypatch):
        """Rend la liste du personnel et retourne le HTML remis à WeasyPrint (sans dépendre de libpango)."""
        import sys
        import types
        rendus = []

        class FauxHTML:
            def __init__(self, **kwargs):
                rendus.append(kwargs['string'])

            def write_pdf(self):
                return b'%PDF-1.7 test'

        faux = types.ModuleType('core.pdf')
        faux.HTML = FauxHTML
        monkeypatch.setitem(sys.modules, 'core.pdf', faux)

        def rendre(utilisateur):
            client.force_login(utilisateur)
            assert client.get(reverse('personnel:personnel_list_pdf')).status_code == 200
            return rendus[-1]

        return rendre

    def test_signature_du_directeur_general_sur_la_liste_du_personnel(self, contexte, html_du_pdf,
                                                                      settings, tmp_path):
        """La liste du personnel couvre tous les cycles : elle est signée par le directeur général
        (fonction, signature scannée, NOM Prénom), jamais par un signataire de cycle plus récent."""
        import io
        from django.core.files.base import ContentFile
        from PIL import Image
        from parametres.models import TypeDocument
        settings.MEDIA_ROOT = tmp_path
        etab, user, actif, inactif = contexte
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        cycle = baker.make('parametres.Cycle', etablissement=etab)
        # Un directeur de cycle, configuré plus récemment : il ne signe pas la liste générale.
        baker.make('parametres.SignataireDocument', cycle=cycle, annee_scolaire=annee, actif=True,
                   type_document=TypeDocument.objects.get(code='LISTE_PERSONNEL'), membre_personnel_id=actif.id,
                   fonction='Le Censeur')
        dg = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='OUÉDRAOGO', prenom='Issa',
                        fonction='Directeur général', est_directeur=True, is_active=True,
                        date_embauche=date(2015, 10, 1))
        tampon = io.BytesIO()
        Image.new('RGBA', (300, 110), (0, 0, 0, 0)).save(tampon, 'PNG')
        dg.signature.save('directeur.png', ContentFile(tampon.getvalue()), save=True)

        html = html_du_pdf(user)

        assert '<div class="msig-fonction">Directeur général</div>' in html
        assert '<div class="msig-sign"><img class="msig-img" src="/media/personnel/signatures/' in html
        assert '<div class="msig-name">OUÉDRAOGO Issa</div>' in html
        assert 'ZONGO Ali' not in html and 'Le Censeur' not in html

    def test_sans_directeur_general_le_type_liste_personnel_signe(self, contexte, html_du_pdf):
        """Aucun directeur général désigné : le titulaire configuré pour « Liste du Personnel » signe."""
        etab, user, actif, inactif = contexte
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        cycle = baker.make('parametres.Cycle', etablissement=etab)
        from parametres.models import TypeDocument
        baker.make('parametres.SignataireDocument', cycle=cycle, annee_scolaire=annee, actif=True,
                   type_document=TypeDocument.objects.get(code='LISTE_PERSONNEL'), membre_personnel_id=actif.id,
                   fonction='Le Proviseur')

        html = html_du_pdf(user)

        assert '<div class="msig-fonction">Le Proviseur</div>' in html
        assert '<div class="msig-name">ZONGO Ali</div>' in html

    def test_sans_signataire_le_nom_de_la_fiche_est_imprime(self, contexte, html_du_pdf):
        """Ni directeur général ni signataire configuré : le nom de la fiche établissement, sans image."""
        etab, user, actif, inactif = contexte
        baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_directeur='Issa OUÉDRAOGO')

        html = html_du_pdf(user)

        assert '<div class="msig-name">Issa OUÉDRAOGO</div>' in html
        assert 'class="msig-img"' not in html

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
        assert 'PREMIUM - Lycée Yelen' in html
        assert licence.cle_licence not in html

    def test_bouton_pdf_sur_la_liste(self, client, contexte):
        etab, user, actif, inactif = contexte
        client.force_login(user)
        response = client.get(reverse('personnel:personnel_list') + '?tous=1')
        assert response.status_code == 200
        assert (reverse('personnel:personnel_list_pdf') + '?tous=1').encode() in response.content


@pytest.mark.django_db
class TestInscriptionPersonnel:
    """Régression : le formulaire d'inscription (sans champ « personnel ») provoquait un 500
    dans InscriptionPersonnel.clean() → aucune inscription possible, cartes de
    /documents/personnel/ toujours « Inactif »."""

    @pytest.fixture
    def contexte(self, client):
        etab = baker.make('etablissements.Etablissement', nom='Lycée Yelen', code='LY')
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False, est_tous_cycles=True)
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Kabore', prenom='Gilbert')
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        poste = baker.make('parametres.Poste', etablissement=etab, code='ENS', titre='Enseignant')
        cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
        client.force_login(user)
        donnees = {'annee_scolaire': annee.pk, 'poste': poste.pk, 'cycle': cycle.pk,
                   'est_actif': 'on', 'heures_hebdomadaires': '0', 'observations': ''}
        return membre, annee, cycle, donnees

    def test_agent_limite_au_cycle_autorise(self, client, contexte):
        from personnel.models import InscriptionPersonnel
        membre, annee, cycle, _ = contexte
        autre = baker.make('parametres.Cycle', etablissement=membre.etablissement, code='PRI', nom='Primaire')
        classe_autorisee = baker.make('parametres.Classe', etablissement=membre.etablissement,
                                      cycle=autre, nom='CP2', niveau='CP2', actif=True)
        classe_interdite = baker.make('parametres.Classe', etablissement=membre.etablissement,
                                      cycle=cycle, nom='6e A', niveau='6e', actif=True)
        membre.cycles.add(cycle, autre)
        membre.classe_affectation = classe_interdite
        membre.save()
        baker.make('personnel.InscriptionPersonnel', personnel=membre, annee_scolaire=annee,
                   cycle=autre, est_actif=True)
        baker.make('personnel.InscriptionPersonnel', personnel=membre, annee_scolaire=annee,
                   cycle=cycle, est_actif=True)
        hors_perimetre = baker.make('personnel.MembrePersonnel', etablissement=membre.etablissement,
                                    nom='YAMEOGO', prenom='Paul', cycles=[cycle])
        baker.make('personnel.InscriptionPersonnel', personnel=hors_perimetre, annee_scolaire=annee,
                   cycle=cycle, est_actif=True)
        baker.make('personnel.AbsencePersonnel', personnel=membre, classe=classe_autorisee,
                   date_debut=date(2026, 9, 1), date_fin=date(2026, 9, 1), observation='ABSENCE AUTORISEE')
        baker.make('personnel.AbsencePersonnel', personnel=membre, classe=classe_interdite,
                   date_debut=date(2026, 9, 2), date_fin=date(2026, 9, 2), observation='ABSENCE INTERDITE')
        agent = baker.make('accounts.User', etablissement=membre.etablissement, role='ENSEIGNANT',
                           must_change_password=False)
        agent.cycles.add(autre)
        client.force_login(agent)

        liste = client.get(reverse('personnel:personnel_list'))
        assert liste.status_code == 200
        assert f'value="{membre.pk}"' in liste.content.decode()
        assert 'YAMEOGO' not in liste.content.decode()
        assert autre.nom in liste.content.decode()
        assert cycle.nom not in liste.content.decode()
        assert client.get(reverse('personnel:detail', args=[hors_perimetre.pk])).status_code == 404

        fiche = client.get(reverse('personnel:detail', args=[membre.pk]))
        assert fiche.status_code == 200
        html = fiche.content.decode()
        assert 'Primaire' in html and 'Secondaire' not in html
        assert 'ABSENCE AUTORISEE' in html and 'ABSENCE INTERDITE' not in html
        assert InscriptionPersonnel.objects.filter(personnel=membre).count() == 2

    def test_inscription_enregistree_et_carte_active(self, client, contexte):
        from personnel.models import InscriptionPersonnel
        membre, annee, cycle, donnees = contexte

        response = client.post(reverse('personnel:inscription_create', args=[membre.pk]), donnees)

        assert response.status_code == 302
        assert response['Location'] == reverse('personnel:detail', args=[membre.pk])
        inscription = InscriptionPersonnel.objects.get()
        assert (inscription.personnel, inscription.annee_scolaire, inscription.cycle) == (membre, annee, cycle)

        page = client.get(reverse('documents:liste_personnel_selector')).content.decode()
        assert 'badge-success">Actif' in page and 'Inactif' not in page

    def test_champ_obligatoire_manquant_affiche_l_erreur(self, client, contexte):
        from personnel.models import InscriptionPersonnel
        membre, _, _, donnees = contexte
        donnees['cycle'] = ''

        response = client.post(reverse('personnel:inscription_create', args=[membre.pk]), donnees)

        assert response.status_code == 200
        assert 'Ce champ est obligatoire' in response.content.decode()
        assert InscriptionPersonnel.objects.count() == 0

    def test_doublon_refuse_avec_message(self, client, contexte):
        from personnel.models import InscriptionPersonnel
        membre, _, _, donnees = contexte
        url = reverse('personnel:inscription_create', args=[membre.pk])
        assert client.post(url, donnees).status_code == 302

        response = client.post(url, donnees)

        assert response.status_code == 200
        assert 'déjà une inscription active pour Secondaire' in response.content.decode()
        assert InscriptionPersonnel.objects.count() == 1

    def test_modification_conserve_le_membre(self, client, contexte):
        from personnel.models import InscriptionPersonnel
        membre, _, _, donnees = contexte
        client.post(reverse('personnel:inscription_create', args=[membre.pk]), donnees)
        inscription = InscriptionPersonnel.objects.get()
        donnees['heures_hebdomadaires'] = '12'

        response = client.post(reverse('personnel:inscription_edit', args=[inscription.pk]), donnees)

        assert response.status_code == 302
        inscription.refresh_from_db()
        assert inscription.personnel == membre and inscription.heures_hebdomadaires == 12


@pytest.mark.django_db
class TestColonneInscriptionAnnuelle:
    """Colonne « Inscription <année courante> » de la liste /personnel/."""

    @pytest.fixture
    def contexte(self, client):
        etab = baker.make('etablissements.Etablissement', nom='Lycée Yelen', code='LY')
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False, est_tous_cycles=True)
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)
        ancienne = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2025-2026', est_courante=False)
        cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire')
        poste = baker.make('parametres.Poste', etablissement=etab, code='ENS', titre='Enseignant')
        inscrit = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Zongo', prenom='Ali',
                             is_active=True, cycles=[cycle])
        non_inscrit = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Kabore', prenom='Awa',
                                 is_active=True, cycles=[cycle])
        baker.make('personnel.InscriptionPersonnel', personnel=inscrit, annee_scolaire=annee,
                   cycle=cycle, poste=poste, est_actif=True)
        # Ne comptent pas : inscription d'une année passée, inscription inactive de l'année courante
        baker.make('personnel.InscriptionPersonnel', personnel=non_inscrit, annee_scolaire=ancienne,
                   cycle=cycle, poste=poste, est_actif=True)
        baker.make('personnel.InscriptionPersonnel', personnel=non_inscrit, annee_scolaire=annee,
                   cycle=cycle, poste=poste, est_actif=False)
        client.force_login(user)
        return etab, annee, cycle, poste, inscrit, non_inscrit

    @staticmethod
    def ligne(html, membre):
        """Fragment HTML de la ligne du tableau correspondant au membre (repéré par sa case à cocher)."""
        lignes = [l for l in html.split('<tr>') if f'value="{membre.pk}"' in l]
        assert len(lignes) == 1
        return lignes[0]

    def test_etat_par_membre(self, client, contexte):
        _, _, _, _, inscrit, non_inscrit = contexte

        html = client.get(reverse('personnel:personnel_list')).content.decode()

        assert '<th style="width:170px;">Inscription 2026-2027</th>' in html
        ligne_inscrit = self.ligne(html, inscrit)
        assert 'badge-success">Inscrit' in ligne_inscrit and 'Secondaire · Enseignant' in ligne_inscrit
        ligne_non_inscrit = self.ligne(html, non_inscrit)
        assert 'badge-warning">Non inscrit' in ligne_non_inscrit
        assert reverse('personnel:inscription_create', args=[non_inscrit.pk]) in ligne_non_inscrit

    def test_sans_annee_courante(self, client, contexte):
        _, annee, _, _, inscrit, _ = contexte
        annee.est_courante = False
        annee.save()

        html = client.get(reverse('personnel:personnel_list')).content.decode()

        assert 'Inscription annuelle</th>' in html
        assert 'Non inscrit' not in html and 'badge-success">Inscrit' not in html
        assert 'title="Aucune année scolaire courante"' in self.ligne(html, inscrit)

    def test_recherche_htmx_conserve_la_colonne(self, client, contexte):
        _, _, _, _, inscrit, _ = contexte

        response = client.get(reverse('personnel:personnel_list') + '?q=zon', HTTP_HX_REQUEST='true')

        html = response.content.decode()
        assert response.status_code == 200 and '<html' not in html
        assert 'Secondaire · Enseignant' in self.ligne(html, inscrit)

    def test_aucune_requete_supplementaire_par_membre(self, client, contexte):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        etab, annee, cycle, poste, _, _ = contexte
        url = reverse('personnel:personnel_list')
        client.get(url)  # amorce les caches (droits d'accès) indépendants du nombre de membres

        with CaptureQueriesContext(connection) as avant:
            client.get(url)
        for i in range(5):
            membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom=f'Ouedraogo{i}',
                                is_active=True, cycles=[cycle])
            baker.make('personnel.InscriptionPersonnel', personnel=membre, annee_scolaire=annee,
                       cycle=cycle, poste=poste, est_actif=True)
        with CaptureQueriesContext(connection) as apres:
            client.get(url)

        assert len(apres) == len(avant)


@pytest.mark.django_db
class TestMatriculePersonnel:
    """Régression : la séquence du matricule était déduite d'un tri alphabétique
    (« -1 » > « -02 », « -99 » > « -100 ») → doublon → IntegrityError (500) sur /personnel/nouveau/."""

    @staticmethod
    def prefixe(etab):
        return f"{etab.code}-P-{date.today().year}-"

    def test_sequence_numerique_malgre_un_suffixe_non_complete(self):
        etab = baker.make('etablissements.Etablissement', code='ETAB001')
        baker.make('personnel.MembrePersonnel', etablissement=etab, matricule=self.prefixe(etab) + '1')
        baker.make('personnel.MembrePersonnel', etablissement=etab, matricule=self.prefixe(etab) + '02')

        nouveau = baker.make('personnel.MembrePersonnel', etablissement=etab, matricule='')

        assert nouveau.matricule == self.prefixe(etab) + '03'

    def test_sequence_au_dela_de_cent(self):
        etab = baker.make('etablissements.Etablissement', code='LY')
        baker.make('personnel.MembrePersonnel', etablissement=etab, matricule=self.prefixe(etab) + '99')
        baker.make('personnel.MembrePersonnel', etablissement=etab, matricule=self.prefixe(etab) + '100')

        nouveau = baker.make('personnel.MembrePersonnel', etablissement=etab, matricule='')

        assert nouveau.matricule == self.prefixe(etab) + '101'

    def test_suffixe_manuel_non_numerique_ignore(self):
        etab = baker.make('etablissements.Etablissement', code='LY')
        baker.make('personnel.MembrePersonnel', etablissement=etab, matricule=self.prefixe(etab) + 'DIR')

        nouveau = baker.make('personnel.MembrePersonnel', etablissement=etab, matricule='')

        assert nouveau.matricule == self.prefixe(etab) + '01'

    def test_creation_via_le_formulaire(self, client):
        """Scénario de production : deux membres « -1 » et « -02 », puis ajout d'un troisième."""
        from personnel.models import MembrePersonnel
        etab = baker.make('etablissements.Etablissement', code='ETAB001')
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False, est_tous_cycles=True)
        baker.make('personnel.MembrePersonnel', etablissement=etab, matricule=self.prefixe(etab) + '1')
        baker.make('personnel.MembrePersonnel', etablissement=etab, matricule=self.prefixe(etab) + '02')
        client.force_login(user)
        donnees = {'nom': 'Ouedraogo', 'prenom': 'Issa', 'genre': 'M', 'date_naissance': '1990-01-01',
                   'lieu_naissance': 'Ouagadougou', 'nationalite': 'Burkinabè', 'fonction': 'Enseignant',
                   'date_embauche': '2026-09-01', 'situation_matrimoniale': 'CELIBATAIRE',
                   'nombre_enfants': 0, 'etablissement': etab.pk}

        response = client.post(reverse('personnel:create'), donnees)

        nouveau = MembrePersonnel.objects.get(nom='Ouedraogo')
        assert response.status_code == 302
        assert response['Location'] == reverse('personnel:detail', args=[nouveau.pk])
        assert nouveau.matricule == self.prefixe(etab) + '03'


@pytest.mark.django_db
def test_titre_de_capacite_dans_le_volet_carriere(client):
    """Champ « Titre de capacité » (texte, 35 caractères) : formulaire, enregistrement, fiche."""
    import re
    from personnel.models import MembrePersonnel
    etab = baker.make('etablissements.Etablissement', code='ETAB001')
    client.force_login(baker.make('accounts.User', etablissement=etab, must_change_password=False, est_tous_cycles=True))
    html = client.get(reverse('personnel:create')).content.decode()
    champ = re.search(r'<input[^>]*name="titre_capacite"[^>]*>', html).group(0)
    assert 'maxlength="35"' in champ and 'type="text"' in champ
    assert html.index('Carrière &amp; Affectation') < html.index('name="titre_capacite"') < html.index('Contact &amp; Adresse')
    titre = 'CAPES Mathématiques — session 2019'
    assert len(titre) <= 35
    reponse = client.post(reverse('personnel:create'), {
        'nom': 'Ouedraogo', 'prenom': 'Issa', 'genre': 'M', 'date_naissance': '1990-01-01', 'lieu_naissance': 'Ouagadougou',
        'nationalite': 'Burkinabè', 'fonction': 'Enseignant', 'titre_capacite': titre, 'date_embauche': '2026-09-01',
        'situation_matrimoniale': 'CELIBATAIRE', 'nombre_enfants': 0, 'etablissement': etab.pk,
    })
    membre = MembrePersonnel.objects.get(nom='Ouedraogo')
    assert reponse.status_code == 302 and membre.titre_capacite == titre
    assert titre in client.get(reverse('personnel:detail', args=[membre.pk])).content.decode()
