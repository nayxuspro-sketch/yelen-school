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

        effectif = droits.matrice_effective()['ENSEIGNANT']
        finances = effectif['fonctionnalites']['finances']

        assert '/finances/paiements/' in finances and '/finances/depenses/' not in finances
        assert ('finances', '/finances/paiements/', 'encaisser') in effectif['actions']       # hérité du module
        assert ('finances', '/finances/depenses/', 'saisir') not in effectif['actions']       # hérité de la fonctionnalité


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
