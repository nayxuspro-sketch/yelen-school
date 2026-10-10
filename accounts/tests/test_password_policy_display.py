"""
La politique de mot de passe affichée doit être celle réellement appliquée
(AUTH_PASSWORD_VALIDATORS : 12 caractères minimum), et chaque refus doit
être visible — correction du « je n'arrive pas à changer le mot de passe ».
"""
import pytest
from django.conf import settings
from django.urls import reverse
from model_bakery import baker

from accounts.forms import ChangeOwnPasswordForm, password_help_text, password_min_length

MDP_ACTUEL = 'Temporaire-2026-ok!'


@pytest.fixture
def utilisateur(db):
    user = baker.make('accounts.User', role='SUPER_ADMIN', is_superuser=True, email='admin@yelen.test',
                      must_change_password=True)
    user.set_password(MDP_ACTUEL)
    user.save()
    return user


def test_longueur_minimale_lue_dans_les_reglages():
    attendu = next(v['OPTIONS']['min_length'] for v in settings.AUTH_PASSWORD_VALIDATORS
                   if v['NAME'].endswith('MinimumLengthValidator'))
    assert password_min_length() == attendu == 12
    assert '12' in password_help_text()


def test_aide_et_minlength_du_formulaire_suivent_la_politique():
    champ = ChangeOwnPasswordForm().fields['password1']
    assert '12' in str(champ.help_text)
    assert champ.widget.attrs['minlength'] == 12
    assert '8 caractères' not in str(champ.help_text)


@pytest.mark.django_db
def test_page_profil_affiche_la_vraie_regle(client, utilisateur):
    client.force_login(utilisateur)
    html = client.get(reverse('accounts:profile')).content.decode()
    assert 'Au moins 8 caractères' not in html
    assert 'minimum 12 caractères' in html
    assert 'Changement obligatoire' in html


@pytest.mark.django_db
def test_mot_de_passe_trop_court_refuse_avec_message_visible(client, utilisateur):
    client.force_login(utilisateur)
    response = client.post(reverse('accounts:profile_change_password'), {
        'old_password': MDP_ACTUEL, 'password1': 'Yelen2026', 'password2': 'Yelen2026',
    })
    html = response.content.decode()
    assert response.status_code == 200
    assert '<p class="form-error">' in html
    assert 'minimum 12 caractères' in html
    utilisateur.refresh_from_db()
    assert utilisateur.check_password(MDP_ACTUEL) and utilisateur.must_change_password is True


@pytest.mark.django_db
def test_toutes_les_erreurs_sont_listees(client, utilisateur):
    client.force_login(utilisateur)
    # court ET uniquement numérique → deux règles violées, deux messages
    response = client.post(reverse('accounts:profile_change_password'), {
        'old_password': MDP_ACTUEL, 'password1': '12345678', 'password2': '12345678',
    })
    html = response.content.decode()
    assert html.count('<p class="form-error">') >= 2


@pytest.mark.django_db
def test_mot_de_passe_conforme_accepte_et_leve_l_obligation(client, utilisateur):
    client.force_login(utilisateur)
    response = client.post(reverse('accounts:profile_change_password'), {
        'old_password': MDP_ACTUEL, 'password1': 'Ecole-Yelen-2026!', 'password2': 'Ecole-Yelen-2026!',
    })
    assert response.status_code == 302
    utilisateur.refresh_from_db()
    assert utilisateur.check_password('Ecole-Yelen-2026!') and utilisateur.must_change_password is False
    # la session reste valide après le changement
    assert client.get(reverse('accounts:profile')).status_code == 200
