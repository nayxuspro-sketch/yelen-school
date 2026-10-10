"""
Connexion : verrouillage temporaire sans fuite d'information.

Un attaquant ne doit pas pouvoir distinguer, depuis les réponses, un compte
inexistant d'un compte existant, ni savoir si un compte est verrouillé, ni
tester un mot de passe pendant le verrouillage.
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from accounts.services import (
    LOCKOUT_DURATION_MINUTES,
    LOGIN_FAILURE_MESSAGE,
    MAX_LOGIN_ATTEMPTS,
    authenticate_with_lockout,
)
from core.models import AuditLog

PASSWORD = 'Mot2PasseTresSolide!'

pytestmark = pytest.mark.django_db


@pytest.fixture
def utilisateur():
    user = baker.make(
        'accounts.User',
        email='prof@yelen.bf',
        is_active=True,
        totp_enabled=False,
        must_change_password=False,
    )
    user.set_password(PASSWORD)
    user.save()
    return user


def _messages(response):
    return [str(m) for m in response.context['messages']]


def test_meme_message_pour_compte_inconnu_et_mot_de_passe_faux(client, utilisateur):
    url = reverse('accounts:login')
    inconnu = client.post(url, {'username': 'personne@yelen.bf', 'password': 'x' * 12})
    faux = client.post(url, {'username': utilisateur.email, 'password': 'x' * 12})

    assert inconnu.status_code == faux.status_code == 200
    assert _messages(inconnu) == _messages(faux) == [LOGIN_FAILURE_MESSAGE]
    # Le message ne contient ni compteur de tentatives ni état de verrouillage.
    assert 'reste' not in LOGIN_FAILURE_MESSAGE
    assert 'verrouillé.' not in LOGIN_FAILURE_MESSAGE.split('Après')[0]


def test_verrouillage_apres_le_seuil_et_message_inchange(client, utilisateur):
    url = reverse('accounts:login')
    for _ in range(MAX_LOGIN_ATTEMPTS):
        response = client.post(url, {'username': utilisateur.email, 'password': 'mauvais-mdp'})
        assert _messages(response) == [LOGIN_FAILURE_MESSAGE]

    utilisateur.refresh_from_db()
    assert utilisateur.failed_login_attempts == MAX_LOGIN_ATTEMPTS
    assert utilisateur.locked_until is not None
    assert utilisateur.locked_until > timezone.now()
    assert utilisateur.locked_until <= timezone.now() + timezone.timedelta(minutes=LOCKOUT_DURATION_MINUTES)



def test_bon_mot_de_passe_refuse_pendant_le_verrouillage_sans_indice(client, utilisateur):
    utilisateur.failed_login_attempts = MAX_LOGIN_ATTEMPTS
    utilisateur.locked_until = timezone.now() + timezone.timedelta(minutes=5)
    utilisateur.save(update_fields=['failed_login_attempts', 'locked_until'])

    url = reverse('accounts:login')
    response = client.post(url, {'username': utilisateur.email, 'password': PASSWORD})

    assert response.status_code == 200          # pas de redirection : refusé
    assert _messages(response) == [LOGIN_FAILURE_MESSAGE]
    assert '_auth_user_id' not in client.session
    utilisateur.refresh_from_db()
    # Un échec pendant le verrouillage ne prolonge pas le verrou.
    assert utilisateur.failed_login_attempts == MAX_LOGIN_ATTEMPTS


def test_connexion_reussie_remet_le_compteur_a_zero(client, utilisateur):
    utilisateur.failed_login_attempts = 3
    utilisateur.save(update_fields=['failed_login_attempts'])

    response = client.post(reverse('accounts:login'), {'username': utilisateur.email, 'password': PASSWORD})

    assert response.status_code == 302
    utilisateur.refresh_from_db()
    assert utilisateur.failed_login_attempts == 0
    assert utilisateur.locked_until is None


def test_verrou_expire_autorise_la_connexion(client, utilisateur):
    utilisateur.failed_login_attempts = MAX_LOGIN_ATTEMPTS
    utilisateur.locked_until = timezone.now() - timezone.timedelta(seconds=1)
    utilisateur.save(update_fields=['failed_login_attempts', 'locked_until'])

    response = client.post(reverse('accounts:login'), {'username': utilisateur.email, 'password': PASSWORD})

    assert response.status_code == 302
    utilisateur.refresh_from_db()
    assert utilisateur.failed_login_attempts == 0 and utilisateur.locked_until is None


def test_service_journalise_le_verrouillage(rf, utilisateur):
    from core.signals import disable_audit, enable_audit
    enable_audit()
    try:
        request = rf.post('/accounts/login/')
        for _ in range(MAX_LOGIN_ATTEMPTS):
            assert authenticate_with_lockout(request, utilisateur.email, 'mauvais') is None
    finally:
        disable_audit()

    entree = AuditLog.objects.filter(action='SECURITY', object_id=str(utilisateur.pk)).order_by('-timestamp').first()
    assert entree is not None
    assert entree.changes.get('event') == 'account_locked'


def test_api_token_applique_le_meme_verrouillage(client, utilisateur):
    """L'API compte les échecs et répond à l'identique pendant le verrouillage (ni 423, ni indice)."""
    url = reverse('api:obtenir_token')
    for _ in range(2):  # sous la limite de débit de l'API (5/min)
        response = client.post(url, {'username': utilisateur.email, 'password': 'mauvais'})
        assert response.status_code == 401
        assert response.json() == {'erreur': 'Identifiants invalides.'}
    utilisateur.refresh_from_db()
    assert utilisateur.failed_login_attempts == 2

    utilisateur.failed_login_attempts = MAX_LOGIN_ATTEMPTS
    utilisateur.locked_until = timezone.now() + timezone.timedelta(minutes=5)
    utilisateur.save(update_fields=['failed_login_attempts', 'locked_until'])
    response = client.post(url, {'username': utilisateur.email, 'password': PASSWORD})
    assert response.status_code == 401
    assert response.json() == {'erreur': 'Identifiants invalides.'}


def test_identifiant_insensible_a_la_casse(client, utilisateur):
    response = client.post(reverse('accounts:login'), {'username': 'PROF@Yelen.bf', 'password': PASSWORD})
    assert response.status_code == 302
