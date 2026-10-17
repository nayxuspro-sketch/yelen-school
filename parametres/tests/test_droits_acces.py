"""Droits d'accès par rôle (modules, fonctionnalités, actions) : valeurs par défaut, application, administration."""
import pytest
from django.urls import reverse
from model_bakery import baker

from etablissements.models import Etablissement
from parametres import droits


@pytest.fixture(autouse=True)
def cache_vide():
    droits.invalider_cache()
    yield
    droits.invalider_cache()


@pytest.fixture
def etab():
    return baker.make(Etablissement)


def _client_role(client, etab, role):
    client.force_login(baker.make('accounts.User', etablissement=etab, role=role, must_change_password=False))
    return client


NB_FONCTIONNALITES = sum(len(m.fonctionnalites) for m in droits.MODULES)
NB_CASES = NB_FONCTIONNALITES + len(droits.TOUTES_ACTIONS)


@pytest.mark.django_db
class TestValeursParDefaut:
    def test_comportement_historique(self):
        matrice = {role: d['fonctionnalites'] for role, d in droits.matrice_effective().items()}

        assert matrice['ENSEIGNANT']['inscriptions'] == {'/inscriptions/', '/inscriptions/reinscription/'}
        assert matrice['AVS']['viescolaire'] and not matrice['AVS']['finances']
        assert not matrice['ENSEIGNANT']['finances'] and matrice['SECRETAIRE']['finances'] and matrice['COMPTABLE']['finances']
        assert matrice['DIRECTEUR']['parametres'] and not matrice['SECRETAIRE']['parametres']
        assert 'parametres' not in droits.modules_autorises(baker.prepare('accounts.User', role='SECRETAIRE'))

    def test_actions_heritent_par_defaut_de_leur_module(self):
        """Au déploiement, chaque action suit l'accès historique du module : rien ne change pour les utilisateurs."""
        actions = {role: d['actions'] for role, d in droits.matrice_effective().items()}

        assert ('pedagogie', '/pedagogie/evaluations/', 'saisir_notes') in actions['ENSEIGNANT']
        assert not {a for a in actions['ENSEIGNANT'] if a[0] == 'finances'}
        assert ('finances', '/finances/paiements/', 'encaisser') in actions['COMPTABLE']
        assert droits.actions_autorisees(baker.prepare('accounts.User', role='SUPER_ADMIN')) == droits.TOUTES_ACTIONS

    def test_actes_restreints_gardent_leurs_roles_historiques(self):
        """Saisie / approbation financières, exports, transferts, sanctions : mêmes rôles qu'avant la matrice."""
        effectif = droits.matrice_effective()
        actions = {role: d['actions'] for role, d in effectif.items()}

        assert ('finances', '/finances/paiements/', 'encaisser') not in actions['SECRETAIRE']
        assert ('finances', '/finances/paiements/', 'rembourser') not in actions['COMPTABLE']
        assert ('finances', '/finances/paiements/', 'rembourser') in actions['DIRECTEUR_RESEAU']
        assert ('finances', '/finances/depenses/', 'valider') not in actions['COMPTABLE']
        assert '/finances/budget/' not in effectif['SECRETAIRE']['fonctionnalites']['finances']
        assert '/finances/budget/' in effectif['COMPTABLE']['fonctionnalites']['finances']
        assert ('inscriptions', '/inscriptions/', 'exporter') not in actions['ENSEIGNANT']
        assert ('inscriptions', '/inscriptions/', 'transferts_decider') not in actions['CENSEUR']
        assert ('inscriptions', '/inscriptions/', 'transferts_decider') in actions['DIRECTEUR']
        assert ('viescolaire', '/viescolaire/sanctions/', 'prononcer') not in actions['ENSEIGNANT']
        assert ('viescolaire', '/viescolaire/sanctions/', 'prononcer') in actions['AVS']

    def test_acte_restreint_ne_s_ouvre_que_par_sa_propre_case(self):
        """Cocher la fonctionnalité (ou le module) n'ouvre pas un acte restreint ; seule sa case le fait."""
        from parametres.models import DroitAcces
        DroitAcces.objects.create(role='SECRETAIRE', module='finances', autorise=True)
        DroitAcces.objects.create(role='SECRETAIRE', module='finances', fonctionnalite='/finances/paiements/', autorise=True)
        assert ('finances', '/finances/paiements/', 'encaisser') not in droits.matrice_effective()['SECRETAIRE']['actions']

        droits.invalider_cache()
        DroitAcces.objects.create(role='SECRETAIRE', module='finances', fonctionnalite='/finances/paiements/',
                                  action='encaisser', autorise=True)
        assert ('finances', '/finances/paiements/', 'encaisser') in droits.matrice_effective()['SECRETAIRE']['actions']

    def test_cible_d_une_action_par_nom_d_url(self):
        """Une action est reconnue par son nom d'URL, même hors du préfixe de sa fonctionnalité."""
        assert droits.cible('finances', '/finances/remboursements/x/annuler/', 'remboursement_delete') == ('/finances/paiements/', 'rembourser')
        assert droits.cible('pedagogie', '/pedagogie/evaluations/x/saisie/', 'evaluation_saisie') == ('/pedagogie/evaluations/', 'saisir_notes')
        assert droits.cible('pedagogie', '/pedagogie/evaluations/', 'evaluation_list') == ('/pedagogie/evaluations/', None)
        assert droits.libelle_cible('pedagogie', '/x/', 'evaluation_saisie') == '« Saisir les notes » (Pédagogie › Évaluations)'

    def test_super_admin_tout(self):
        super_admin = baker.prepare('accounts.User', role='SUPER_ADMIN')
        assert droits.modules_autorises(super_admin) == droits.CODES_MODULES
        assert len(droits.fonctionnalites_autorisees(super_admin)) == NB_FONCTIONNALITES

    def test_fonctionnalite_du_chemin_prefixe_le_plus_long(self):
        assert droits.fonctionnalite_du_chemin('finances', '/finances/relances/historique/?page=2') == '/finances/relances/historique/'
        assert droits.fonctionnalite_du_chemin('finances', '/finances/relances/') == '/finances/relances/'
        assert droits.fonctionnalite_du_chemin('finances', '/finances/situation/eleve/x/') == '/finances/paiements/'
        assert droits.fonctionnalite_du_chemin('inscriptions', '/inscriptions/abc/modifier/') == '/inscriptions/'
        assert droits.fonctionnalite_du_chemin('pedagogie', '/pedagogie/hors-menu/') is None

    def test_droit_sur_le_module_entier_herite_aux_fonctionnalites(self):
        """Un enregistrement historique (fonctionnalite='') vaut pour toutes les fonctionnalités du module."""
        from parametres.models import DroitAcces
        DroitAcces.objects.create(role='ENSEIGNANT', module='finances', autorise=True)
        DroitAcces.objects.create(role='ENSEIGNANT', module='finances', fonctionnalite='/finances/depenses/', autorise=False)
        DroitAcces.objects.create(role='ENSEIGNANT', module='pedagogie', autorise=False)
        DroitAcces.objects.create(role='ENSEIGNANT', module='pedagogie', fonctionnalite='/pedagogie/matieres/', autorise=True)

        effectif = droits.matrice_effective()['ENSEIGNANT']
        finances = effectif['fonctionnalites']['finances']

        assert '/finances/paiements/' in finances and '/finances/depenses/' not in finances
        assert ('finances', '/finances/paiements/', 'encaisser') not in effectif['actions']   # acte restreint : règle propre
        assert ('pedagogie', '/pedagogie/evaluations/', 'saisir_notes') not in effectif['actions']  # hérité du module
        assert ('pedagogie', '/pedagogie/matieres/', 'gerer') in effectif['actions']          # hérité de la fonctionnalité


@pytest.mark.django_db
class TestApplicationDesDroits:
    def test_module_refuse_redirige_avec_message(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')

        reponse = client.get(reverse('finances:paiement_list'))

        assert reponse.status_code == 302 and reponse.url == '/'
        suite = client.get('/')
        assert 'Accès à « Paiements » (Finances) non autorisé' in suite.content.decode()

    def test_module_refuse_en_htmx(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')
        assert client.get(reverse('finances:paiement_list'), HTTP_HX_REQUEST='true').status_code == 403

    def test_module_autorise(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')
        assert client.get(reverse('inscriptions:eleve_list')).status_code == 200

    def test_menu_suit_les_droits(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')

        html = client.get('/').content.decode()

        assert 'id="inscriptions-toggle"' in html and 'data-url="/pedagogie/matieres/"' in html
        assert 'id="finances-toggle"' not in html and 'id="params-toggle"' not in html
        assert 'droits-acces' not in html and 'data-url="/parametres/signataires/formulaire/"' not in html

    def test_page_hors_menu_suit_le_module(self, client, etab):
        """Une page du module sans entrée de menu suit l'accès au module (une fonctionnalité au moins)."""
        from parametres.models import DroitAcces
        for f in droits.MODULES_PAR_CODE['finances'].fonctionnalites:
            DroitAcces.objects.create(role='COMPTABLE', module='finances', fonctionnalite=f.prefixe,
                                      autorise=f.prefixe == '/finances/redevables/')
        baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        _client_role(client, etab, 'COMPTABLE')

        assert client.get('/finances/paiements/').url == '/'                        # refusée
        assert client.get('/finances/redevables/').status_code == 200
        assert client.get('/finances/types-bourses/').status_code == 302          # rattachée aux bourses
        reponse = client.get('/finances/hors-menu-inexistant/')
        assert reponse.status_code == 404                                           # pas de refus : module ouvert

    def test_action_refusee_dans_une_fonctionnalite_ouverte(self, client, etab):
        """« Saisir les notes » retiré : la liste des évaluations reste accessible, la saisie est refusée et ses boutons masqués."""
        from parametres.models import DroitAcces
        DroitAcces.objects.create(role='ENSEIGNANT', module='pedagogie', fonctionnalite='/pedagogie/evaluations/',
                                  action='saisir_notes', autorise=False)
        _client_role(client, etab, 'ENSEIGNANT')

        liste = client.get(reverse('pedagogie:evaluation_list'))
        assert liste.status_code == 200
        assert 'Saisie par classe' not in liste.content.decode()
        refus = client.get(reverse('pedagogie:saisie_classe_select'))
        assert refus.status_code == 302 and refus.url == '/'
        assert 'Accès à « Saisir les notes » (Pédagogie › Évaluations) non autorisé' in client.get('/').content.decode()
        assert client.get(reverse('pedagogie:saisie_classe_select'), HTTP_HX_REQUEST='true').status_code == 403
        assert client.get(reverse('pedagogie:evaluation_create')).status_code == 200           # action voisine conservée

    def test_acte_restreint_suit_la_matrice_et_non_plus_le_code(self, client, etab):
        """Les anciens contrôles de rôle codés en dur s'effacent devant la matrice (défauts identiques)."""
        from parametres.models import DroitAcces
        baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        secretaire = _client_role(client, etab, 'SECRETAIRE')
        refus = secretaire.get(reverse('finances:paiement_recherche_eleve'), {'q': 'x'})
        assert refus.status_code == 302 and refus.url == '/'
        assert 'Accès à « Encaisser un paiement » (Finances › Paiements) non autorisé' in secretaire.get('/').content.decode()
        assert secretaire.get(reverse('inscriptions:eleve_list_csv')).status_code == 200
        assert secretaire.post(reverse('inscriptions:transfert_inter_approuver', kwargs={'pk': etab.pk})).url == '/'

        DroitAcces.objects.create(role='SECRETAIRE', module='finances', fonctionnalite='/finances/paiements/',
                                  action='encaisser', autorise=True)
        droits.invalider_cache()
        assert secretaire.get(reverse('finances:paiement_recherche_eleve'), {'q': 'x'}).status_code == 200

        enseignant = _client_role(client.__class__(), etab, 'ENSEIGNANT')
        assert enseignant.get(reverse('inscriptions:eleve_list_csv')).url == '/'
        assert enseignant.get(reverse('viescolaire:sanction_create')).url == '/'
        super_admin = _client_role(client.__class__(), etab, 'SUPER_ADMIN')
        assert super_admin.get(reverse('viescolaire:sanction_create')).status_code == 200      # n'était plus accepté

    def test_action_exige_sa_fonctionnalite(self, client, etab):
        """Une action cochée reste refusée tant que sa fonctionnalité ne l'est pas."""
        from parametres.models import DroitAcces
        DroitAcces.objects.create(role='ENSEIGNANT', module='pedagogie', fonctionnalite='/pedagogie/evaluations/', autorise=False)
        DroitAcces.objects.create(role='ENSEIGNANT', module='pedagogie', fonctionnalite='/pedagogie/evaluations/',
                                  action='saisir_notes', autorise=True)
        _client_role(client, etab, 'ENSEIGNANT')

        assert client.get(reverse('pedagogie:saisie_classe_select')).url == '/'
        assert client.get(reverse('pedagogie:matiere_list')).status_code == 200


@pytest.mark.django_db
class TestAdministrationParLeSuperAdmin:
    def test_reservee_au_super_admin(self, client, etab):
        _client_role(client, etab, 'DIRECTEUR')
        assert client.get(reverse('parametres:droits_acces')).status_code == 403

    def test_matrice_affichee(self, client, etab):
        _client_role(client, etab, 'SUPER_ADMIN')

        html = client.get(reverse('parametres:droits_acces')).content.decode()

        assert 'name="droit" value="SECRETAIRE:finances:/finances/depenses/:"' in html
        assert 'name="droit" value="SECRETAIRE:finances:/finances/depenses/:valider"' in html
        assert '↳ Saisir les notes' in html
        assert html.count('name="droit"') == len(droits.ROLES_CONFIGURABLES) * NB_CASES
        assert html.count('data-groupe-maitre="') == len(droits.ROLES_CONFIGURABLES) * len(droits.MODULES)
        assert 'id="matrice-droits"' in html and 'data-url="/parametres/droits-acces/"' in html

    def test_enregistrement_applique_immediatement(self, client, etab):
        from parametres.models import DroitAcces
        _client_role(client, etab, 'SUPER_ADMIN')
        coches = [f'{role}:{module}:{prefixe}:{action}'
                  for role in droits.ROLES_CONFIGURABLES for module, prefixe, action in droits.cles_matrice()]
        coches.remove('ENSEIGNANT:inscriptions:/inscriptions/:')             # retrait d'une fonctionnalité
        coches.remove('ENSEIGNANT:pedagogie:/pedagogie/evaluations/:saisir_notes')   # retrait d'une action
        for f in droits.MODULES_PAR_CODE['bulletins'].fonctionnalites:
            coches.remove(f'ENSEIGNANT:bulletins:{f.prefixe}:')             # retrait d'un module entier

        reponse = client.post(reverse('parametres:droits_acces'), {'droit': coches})

        assert reponse.status_code == 302
        assert DroitAcces.objects.count() == len(droits.ROLES_CONFIGURABLES) * NB_CASES
        enseignant = _client_role(client.__class__(), etab, 'ENSEIGNANT')
        assert enseignant.get(reverse('finances:paiement_list')).status_code == 200            # accès ajouté
        assert enseignant.get(reverse('inscriptions:eleve_list')).status_code == 302           # fonctionnalité retirée
        assert enseignant.get(reverse('inscriptions:reinscription_list')).status_code == 200   # voisine conservée
        assert enseignant.get(reverse('bulletins:index')).status_code == 302                   # module retiré
        assert enseignant.get(reverse('pedagogie:saisie_classe_select')).status_code == 302    # action retirée
        assert enseignant.get(reverse('pedagogie:evaluation_list')).status_code == 200         # sa fonctionnalité conservée
        html = enseignant.get('/').content.decode()
        assert 'id="finances-toggle"' in html and 'id="inscriptions-toggle"' in html
        assert 'data-url="/inscriptions/reinscription/"' in html and 'data-url="/inscriptions/"' not in html
        assert 'id="bulletins-toggle"' not in html


@pytest.mark.django_db
class TestRolesPersonnalises:
    """Rôles créés par le Super Admin : colonne de la matrice, héritage de la référence, affectation aux utilisateurs."""

    def _creer(self, client, etab, libelle='Surveillant général', base='AVS'):
        _client_role(client, etab, 'SUPER_ADMIN')
        return client.post(reverse('parametres:role_personnalise_create'), {'libelle': libelle, 'base': base})

    def test_creation_code_derive_et_colonne_dans_la_matrice(self, client, etab):
        from parametres.models import RolePersonnalise

        assert self._creer(client, etab).status_code == 302
        role = RolePersonnalise.objects.get()
        assert (role.code, role.base, role.libelle) == ('SURVEILLANT_GENERAL', 'AVS', 'Surveillant général')
        html = client.get(reverse('parametres:droits_acces')).content.decode()
        assert 'Surveillant général' in html and 'réf. Agent de Vie Scolaire' in html
        assert 'value="SURVEILLANT_GENERAL:viescolaire:/viescolaire/sanctions/:prononcer"' in html
        assert html.count('name="droit"') == (len(droits.ROLES_CONFIGURABLES) + 1) * NB_CASES

    def test_code_en_conflit_refuse(self, client, etab):
        from parametres.models import RolePersonnalise
        self._creer(client, etab, libelle='Enseignant', base='ENSEIGNANT')           # code intégré
        self._creer(client, etab, libelle='Caisse', base='COMPTABLE')
        self._creer(client, etab, libelle='CAISSE', base='SECRETAIRE')               # même code
        assert list(RolePersonnalise.objects.values_list('code', flat=True)) == ['CAISSE']
        assert 'existe déjà' in client.get(reverse('parametres:droits_acces')).content.decode()

    def test_reserve_au_super_admin(self, client, etab):
        _client_role(client, etab, 'DIRECTEUR')
        assert client.post(reverse('parametres:role_personnalise_create'), {'libelle': 'X', 'base': 'AVS'}).status_code == 403

    def test_herite_de_sa_reference_puis_s_en_detache(self, client, etab):
        from parametres.models import DroitAcces, RolePersonnalise
        self._creer(client, etab, libelle='Caissier', base='SECRETAIRE')
        role = RolePersonnalise.objects.get()
        baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
        caissier = baker.make('accounts.User', etablissement=etab, role='SECRETAIRE', role_personnalise=role,
                              must_change_password=False)
        assert caissier.role_effectif == 'CAISSIER' and caissier.role_libelle == 'Caissier'
        client.force_login(caissier)

        # Comme une secrétaire : consultation des paiements oui, encaissement non
        assert client.get(reverse('finances:paiement_list')).status_code == 200
        assert client.get(reverse('finances:paiement_recherche_eleve'), {'q': 'x'}).url == '/'

        # Droits propres : encaissement ouvert, Pédagogie fermée — la secrétaire n'en est pas affectée
        DroitAcces.objects.create(role='CAISSIER', module='finances', fonctionnalite='/finances/paiements/',
                                  action='encaisser', autorise=True)
        DroitAcces.objects.create(role='CAISSIER', module='pedagogie', autorise=False)
        droits.invalider_cache()
        assert client.get(reverse('finances:paiement_recherche_eleve'), {'q': 'x'}).status_code == 200
        assert client.get(reverse('pedagogie:matiere_list')).url == '/'
        assert 'id="pedagogie-toggle"' not in client.get('/').content.decode()
        secretaire = _client_role(client.__class__(), etab, 'SECRETAIRE')
        assert secretaire.get(reverse('pedagogie:matiere_list')).status_code == 200
        assert secretaire.get(reverse('finances:paiement_recherche_eleve'), {'q': 'x'}).url == '/'

    def test_enregistrement_de_la_matrice_couvre_le_nouveau_role(self, client, etab):
        from parametres.models import DroitAcces
        self._creer(client, etab)
        coches = [f'{role.code}:{module}:{prefixe}:{action}'
                  for role in droits.roles_configurables() for module, prefixe, action in droits.cles_matrice()]
        coches.remove('SURVEILLANT_GENERAL:viescolaire:/viescolaire/sanctions/:')

        client.post(reverse('parametres:droits_acces'), {'droit': coches})

        assert DroitAcces.objects.filter(role='SURVEILLANT_GENERAL').count() == NB_CASES
        effectif = droits.matrice_effective()
        assert '/viescolaire/sanctions/' not in effectif['SURVEILLANT_GENERAL']['fonctionnalites']['viescolaire']
        assert '/viescolaire/sanctions/' in effectif['AVS']['fonctionnalites']['viescolaire']

    def test_suppression_protegee_puis_possible(self, client, etab):
        from parametres.models import DroitAcces, RolePersonnalise
        self._creer(client, etab)
        role = RolePersonnalise.objects.get()
        DroitAcces.objects.create(role=role.code, module='finances', autorise=True)
        porteur = baker.make('accounts.User', etablissement=etab, role='AVS', role_personnalise=role)

        client.post(reverse('parametres:role_personnalise_delete', kwargs={'pk': role.pk}))
        assert RolePersonnalise.objects.filter(pk=role.pk).exists()
        assert 'le portent encore' in client.get(reverse('parametres:droits_acces')).content.decode()

        porteur.role_personnalise = None
        porteur.save(update_fields=['role_personnalise'])
        client.post(reverse('parametres:role_personnalise_delete', kwargs={'pk': role.pk}))
        assert not RolePersonnalise.objects.exists() and not DroitAcces.objects.filter(role=role.code).exists()

    def test_formulaire_utilisateur_propose_et_applique_le_role(self, client, etab):
        from accounts.models import User
        from parametres.models import RolePersonnalise
        self._creer(client, etab, libelle='Caissier', base='COMPTABLE')
        role = RolePersonnalise.objects.get()

        html = client.get(reverse('accounts:user_create')).content.decode()
        assert '<optgroup label="Rôles personnalisés">' in html and '<option value="CAISSIER">Caissier</option>' in html
        donnees = {'last_name': 'Zongo', 'first_name': 'Awa', 'email': 'awa@ecole.bf', 'telephone': '',
                   'role': 'CAISSIER', 'etablissement': etab.pk,
                   'password1': 'MotDePasse!2026xyz', 'password2': 'MotDePasse!2026xyz'}
        assert client.post(reverse('accounts:user_create'), donnees).status_code == 302
        awa = User.objects.get(email='awa@ecole.bf')
        assert awa.role == 'COMPTABLE' and awa.role_personnalise == role

        html = client.get(reverse('accounts:user_update', kwargs={'pk': awa.pk})).content.decode()
        assert '<option value="CAISSIER" selected>Caissier</option>' in html
        donnees = {'last_name': 'Zongo', 'first_name': 'Awa', 'email': 'awa@ecole.bf', 'telephone': '',
                   'role': 'SECRETAIRE', 'etablissement': etab.pk, 'is_active': 'on'}
        assert client.post(reverse('accounts:user_update', kwargs={'pk': awa.pk}), donnees).status_code == 302
        awa.refresh_from_db()
        assert awa.role == 'SECRETAIRE' and awa.role_personnalise is None
        liste = client.get(reverse('accounts:user_list'), {'role': 'CAISSIER'}).content.decode()
        assert 'awa@ecole.bf' not in liste
