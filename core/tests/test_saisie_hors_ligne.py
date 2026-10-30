"""Saisie hors réseau (notes, appels) : un formulaire conservé par le navigateur est rejoué avec l'en-tête
X-Saisie-Differee et la vue répond en JSON (core/hors_ligne.py) ; Service Worker, pastille et page
« Saisies hors réseau » (static/js/sw_saisies.js, static/js/saisies_hors_ligne.js)."""
import datetime
import re
import uuid
from decimal import Decimal

import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Note

pytestmark = pytest.mark.django_db

DIFFEREE = {'HTTP_X_SAISIE_DIFFEREE': '2026-10-30T18:05:00.000Z'}


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def direction(client, etab, settings):
    settings.TWO_FACTOR_REQUIRED = False
    user = baker.make('accounts.User', role='SUPER_ADMIN', etablissement=etab, is_superuser=True, must_change_password=False)
    client.force_login(user)
    return user


@pytest.fixture
def evaluation(etab):
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A')
    ens = baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe,
                     matiere=baker.make('pedagogie.Matiere', nom='Mathématiques'))
    evaluation = baker.make('pedagogie.Evaluation', enseignement=ens, titre='Devoir 1', bareme=Decimal('20.00'))
    evaluation.inscription = baker.make('inscriptions.Inscription', annee_scolaire=annee, classe=classe, statut='INSCRIT')
    return evaluation


@pytest.fixture
def appel(etab):
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, nom='5e B')
    appel = baker.make('presences.Appel', classe=classe, annee_scolaire=annee, date=datetime.date(2026, 10, 30),
                       matiere=baker.make('pedagogie.Matiere', nom='Physique'), est_clos=False)
    appel.presence = baker.make('presences.Presence', appel=appel, statut='PRESENT',
                                inscription=baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee))
    return appel


# ── Rejeu côté serveur ────────────────────────────────────────────────────────────────────────────

def test_notes_rejouees_acceptees_en_json_et_messages_consommes(client, direction, evaluation):
    url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})

    reponse = client.post(url, {f'note_{evaluation.inscription.id}': '15,5'}, **DIFFEREE)

    assert reponse.status_code == 200 and reponse['Content-Type'].startswith('application/json')
    retour = reponse.json()
    assert retour['ok'] is True
    assert [m['texte'] for m in retour['messages']] == ['1 note(s) enregistrée(s).']
    assert Note.objects.get(inscription=evaluation.inscription, evaluation=evaluation).valeur == Decimal('15.5')
    assert '1 note(s) enregistrée(s)' not in client.get(url).content.decode()    # rien ne « ressort » plus tard


def test_sans_en_tete_le_comportement_reste_une_redirection(client, direction, evaluation):
    url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})

    reponse = client.post(url, {f'note_{evaluation.inscription.id}': '12'})

    assert reponse.status_code == 302 and reponse.url == url
    assert '1 note(s) enregistrée(s)' in client.get(url).content.decode()


def test_session_expiree_signalee_401(client, evaluation):
    url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})

    reponse = client.post(url, {f'note_{evaluation.inscription.id}': '12'}, **DIFFEREE)

    assert reponse.status_code == 401 and reponse.json() == {'ok': False, 'code': 'connexion'}
    assert not Note.objects.exists()


def test_saisie_d_un_autre_compte_refusee_403(client, direction, evaluation):
    url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})

    reponse = client.post(url, {f'note_{evaluation.inscription.id}': '12'},
                          HTTP_X_SAISIE_UTILISATEUR=str(uuid.uuid4()), **DIFFEREE)

    assert reponse.status_code == 403 and reponse.json() == {'ok': False, 'code': 'utilisateur'}
    assert not Note.objects.exists()
    assert client.post(url, {f'note_{evaluation.inscription.id}': '12'},
                       HTTP_X_SAISIE_UTILISATEUR=str(direction.pk), **DIFFEREE).json()['ok'] is True


def test_trimestre_verrouille_refus_explicite(client, direction, evaluation):
    evaluation.trimestre.notes_saisies = True       # période clôturée
    evaluation.trimestre.save()
    url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})

    retour = client.post(url, {f'note_{evaluation.inscription.id}': '12'}, **DIFFEREE).json()

    assert retour['ok'] is False
    assert retour['messages'][0]['niveau'] == 'error' and 'Saisie des notes refusée' in retour['messages'][0]['texte']


def test_appel_rejoue_puis_appel_clos_refuse(client, direction, appel):
    url = reverse('presences:appel_saisie', args=[appel.pk])
    donnees = {f'statut_{appel.presence.pk}': 'RETARD', f'retard_{appel.presence.pk}': '10'}

    retour = client.post(url, donnees, **DIFFEREE).json()
    appel.presence.refresh_from_db()
    assert retour == {'ok': True, 'messages': [{'niveau': 'success', 'texte': 'Présences enregistrées.'}]}
    assert (appel.presence.statut, appel.presence.minutes_retard) == ('RETARD', 10)

    appel.est_clos = True
    appel.save()
    retour = client.post(url, {f'statut_{appel.presence.pk}': 'ABSENT'}, **DIFFEREE).json()
    appel.presence.refresh_from_db()
    assert retour['ok'] is False and 'clôturé' in retour['messages'][0]['texte']
    assert appel.presence.statut == 'RETARD'


def test_droit_refuse_par_la_matrice_en_json(client, etab, evaluation, settings):
    """Un rôle sans accès au module reçoit un refus lisible (403 JSON) au lieu d'une redirection HTML."""
    from parametres import droits
    from parametres.models import DroitAcces
    settings.TWO_FACTOR_REQUIRED = False
    DroitAcces.objects.create(role='ENSEIGNANT', module='pedagogie', fonctionnalite='/pedagogie/evaluations/', autorise=False)
    droits.invalider_cache()
    client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, must_change_password=False))
    url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})

    reponse = client.post(url, {f'note_{evaluation.inscription.id}': '12'}, **DIFFEREE)

    assert reponse.status_code == 403
    assert reponse.json()['code'] == 'droit' and 'non autorisé' in reponse.json()['messages'][0]['texte']
    assert client.post(url, {f'note_{evaluation.inscription.id}': '12'}).status_code == 302   # sans en-tête : inchangé


# ── Navigateur : Service Worker, pastille, page de la file ───────────────────────────────────────

def test_service_worker_intercepte_les_saisies_et_precache_la_page_de_la_file(client):
    script = client.get('/app-sw.js').content.decode()

    assert "importScripts('/static/js/sw_saisies" in script
    assert "SAISIES.concerne(url.pathname)" in script and "SAISIES.intercepter(e.request)" in script
    assert "'/hors-ligne/saisies/'," in script
    assert not re.search(r'__[A-Z_]+__', script)                 # tous les marqueurs remplacés
    for nom in ('js/sw_saisies.js', 'js/saisies_hors_ligne.js'):
        assert finders.find(nom), nom


def test_page_de_la_file_accessible_hors_connexion(client):
    page = client.get(reverse('core:saisies_hors_ligne')).content.decode()

    assert 'id="saisies-liste"' in page and 'id="saisies-transmettre"' in page and 'id="saisies-pages"' in page
    assert 'js/saisies_hors_ligne' in page and "serviceWorker.register('/app-sw.js'" in page
    assert 'name="yelen-utilisateur"' not in page      # anonyme : aucune identité


def test_service_worker_memorise_les_pages_visitees(client):
    """Copie synchrone de la réponse + écriture garantie : sans cela, rien n'est jamais mis en cache."""
    sw = client.get('/app-sw.js').content.decode()
    assert 'const copie = r.clone();' in sw
    assert 'e.waitUntil(caches.open(APP_CACHE).then(c => c.put(e.request, copie))' in sw
    assert sw.count('if (r.ok && !r.redirected) memoriser(r);') == 2            # ressources statiques et pages


def test_contexte_frais_avant_transmission(client, direction):
    """Session, identité et jeton CSRF courants, demandés par le navigateur juste avant de rejouer."""
    contexte = client.get(reverse('core:saisies_contexte')).json()
    assert contexte['authentifie'] is True and contexte['utilisateur'] == str(direction.pk) and len(contexte['csrf']) == 64

    client.logout()
    contexte = client.get(reverse('core:saisies_contexte')).json()
    assert contexte['authentifie'] is False and contexte['utilisateur'] == '' and len(contexte['csrf']) == 64
    assert "'/hors-ligne/contexte/'" in client.get('/app-sw.js').content.decode()      # jamais servi depuis le cache


def test_pages_connectees_portent_identite_pastille_et_script(client, direction, evaluation):
    page = client.get(reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})).content.decode()

    assert f'name="yelen-utilisateur" content="{direction.pk}"' in page
    assert 'id="saisies-attente"' in page and 'js/saisies_hors_ligne' in page
    assert '<title>Notes — Devoir 1 — Mathématiques — 6e A — YELEN SCHOOL</title>' in page


def test_titre_de_la_page_d_appel_identifie_la_seance(client, direction, appel):
    page = client.get(reverse('presences:appel_saisie', args=[appel.pk])).content.decode()

    assert '<title>Appel — 5e B — Physique — 30/10/2026 — YELEN SCHOOL</title>' in page


def test_page_hors_ligne_mene_a_la_file_sans_boucle_de_rechargement(client):
    page = client.get(reverse('core:offline')).content.decode()

    assert reverse('core:saisies_hors_ligne') in page
    assert 'update(false);' in page and "function () { update(true); }" in page
