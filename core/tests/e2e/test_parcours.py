"""Parcours navigateur (5.42.0) — les cinq gestes critiques vus depuis un vrai navigateur.

Un serveur de test et Chromium piloté par Playwright : connexion, encaissement avec reçu PDF, saisie de
notes, bulletin PDF, portail parent. Les régressions visuelles (commentaire de gabarit affiché, page
blanche, redirection d'un service worker) ne se voient que là.

Lancés par le job CI « parcours » (`pytest -m e2e`) ; ignorés du reste de la suite :
    pytest -m e2e              # avec Playwright et Chromium installés
    python -m playwright install chromium
"""
import os

import pytest
from django.core.management import call_command

# Playwright installe sa boucle d'événements dans le fil du test ; Django refuse alors toute requête ORM
# synchrone (« SynchronousOnlyOperation »). Le test et le navigateur restent séquentiels : l'échappatoire
# documentée de Django est utilisée ici, et nulle part dans l'application.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

playwright_api = pytest.importorskip('playwright.sync_api', reason='Playwright non installé (job CI « parcours »)')

from django.urls import reverse  # noqa: E402  (après importorskip : le module est ignoré sans Playwright)
from playwright.sync_api import expect  # noqa: E402

from core.management.commands.charger_demo import MOT_DE_PASSE  # noqa: E402
from finances.models import Paiement  # noqa: E402
from inscriptions.models import Inscription  # noqa: E402
from pedagogie.models import Evaluation, Note  # noqa: E402


@pytest.fixture(autouse=True)
def hachage_rapide(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@pytest.fixture(autouse=True)
def fichiers_statiques_haches(settings):
    """pytest-django sert /static/ par les *finders* (dossiers sources) ; les noms hachés produits par
    collectstatic n'existent que dans STATIC_ROOT. Sans cette ligne la page arrive sans feuille de style et
    les clics tombent à côté : le test ne prouverait plus rien."""
    settings.STATICFILES_DIRS = [settings.STATIC_ROOT, *settings.STATICFILES_DIRS]


@pytest.fixture
def navigateur(live_server):
    """Chromium démarré après la préparation de la base : Playwright installe sa boucle d'événements, et
    Django refuse toute opération synchrone sur la base une fois cette boucle en place."""
    with playwright_api.sync_playwright() as playwright:
        navigateur = playwright.chromium.launch()
        yield navigateur
        navigateur.close()


@pytest.fixture
def page(navigateur):
    contexte = navigateur.new_context(base_url='http://localhost', locale='fr-FR',
                                      viewport={'width': 1440, 'height': 900})
    page = contexte.new_page()
    yield page
    contexte.close()


@pytest.fixture
def demo():
    """Établissement de démonstration (chantier C4) : tout le parcours part de données réelles."""
    call_command('charger_demo', '--eleves', '8', verbosity=0)
    return Inscription.objects.filter(annee_scolaire__est_courante=True).order_by('eleve__nom').first()


def connecter(page, live_server, email):
    page.goto(f'{live_server.url}{reverse("accounts:login")}')
    page.fill('input[name="username"]', email)
    page.fill('input[name="password"]', MOT_DE_PASSE)
    page.click('button[type="submit"]')
    page.wait_for_url(lambda url: '/login/' not in url)


def test_connexion_directeur(page, live_server, demo):
    connecter(page, live_server, 'direction@demo.bf')
    expect(page).to_have_url(live_server.url + reverse('core:home'))
    expect(page.locator('body')).to_contain_text('YELEN SCHOOL')
    assert 'Tableau de bord' in page.content()


def test_encaissement_et_recu_pdf(page, live_server, demo):
    inscription = Inscription.objects.filter(annee_scolaire__est_courante=True).order_by('eleve__nom')[1]
    connecter(page, live_server, 'comptabilite@demo.bf')
    page.goto(f'{live_server.url}{reverse("finances:paiement_create")}?inscription={inscription.pk}')
    rubrique = page.locator('.pai-rub-card:not(.is-soldee)').first
    rubrique.wait_for()
    # Une seule rubrique en attente : la page la présélectionne. Sinon, clic sur son en-tête (le montant
    # proposé est le reste à payer).
    page.evaluate("""() => {
        const carte = document.querySelector('.pai-rub-card:not(.is-soldee)');
        if (carte && !carte.classList.contains('is-selected')) carte.querySelector('.pai-rub-hd').click();
    }""")
    expect(page.locator('#btn-submit')).to_be_enabled()
    page.click('#btn-submit')
    page.wait_for_url('**/paiements/confirmation/**')

    paiement = Paiement.objects.filter(inscription=inscription).latest('created_at')
    recu = page.request.get(f'{live_server.url}{reverse("finances:recu_pdf", args=[paiement.pk])}')
    assert recu.status == 200 and recu.headers['content-type'].startswith('application/pdf')
    assert recu.body()[:4] == b'%PDF'


def test_saisie_de_notes(page, live_server, demo):
    evaluation = Evaluation.objects.filter(
        trimestre__annee_scolaire__est_courante=True, enseignement__personnel__email='e.moussa@demo.bf').first()
    connecter(page, live_server, 'e.moussa@demo.bf')
    page.goto(f'{live_server.url}{reverse("pedagogie:evaluation_saisie", args=[evaluation.pk])}')
    expect(page.locator('body')).to_contain_text(evaluation.enseignement.classe.nom)
    champ = page.locator('input[name^="note_"]').first
    champ.fill('12')
    page.click('#form-saisie button[type="submit"]')
    expect(page.get_by_text('note(s) enregistrée(s)').first).to_be_visible()
    assert Note.objects.filter(evaluation=evaluation, valeur=12).exists()


def test_bulletin_pdf(page, live_server, demo):
    from pedagogie.models import Trimestre
    trimestre = Trimestre.objects.get(annee_scolaire__est_courante=True, numero=1)
    connecter(page, live_server, 'direction@demo.bf')
    apercu = f'{live_server.url}{reverse("pedagogie:bulletin_apercu", args=[demo.pk, trimestre.pk])}'
    page.goto(apercu)
    expect(page.locator('body')).to_contain_text(demo.eleve.nom)

    bulletin = page.request.get(f'{live_server.url}{reverse("pedagogie:bulletin_pdf", args=[demo.pk, trimestre.pk])}')
    assert bulletin.status == 200 and bulletin.headers['content-type'].startswith('application/pdf')
    assert bulletin.body()[:4] == b'%PDF'


def test_portail_parent(page, live_server, demo):
    from accounts.models import User
    parent = User.objects.get(username='parent@demo.bf')
    enfants = list(parent.eleves_lies.all())
    connecter(page, live_server, 'parent@demo.bf')
    expect(page).to_have_url(live_server.url + reverse('core:portail_parent'))
    for enfant in enfants:
        expect(page.locator('body')).to_contain_text(enfant.nom)

    page.goto(f'{live_server.url}{reverse("core:portail_parent_bulletins")}')
    expect(page.locator('.pp-topbar-logo')).to_have_text('Bulletins')
    assert any(enfant.nom in page.content() for enfant in enfants)
