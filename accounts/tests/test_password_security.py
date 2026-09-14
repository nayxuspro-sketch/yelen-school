"""Tests du parcours de remplacement obligatoire du mot de passe initial."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from model_bakery import baker

from accounts.models import User


@pytest.mark.django_db
def test_user_requires_password_change_field_defaults_to_false():
    user = baker.make(User)

    assert user.must_change_password is False


@pytest.mark.django_db
def test_forced_password_change_redirects_other_pages_but_allows_profile(client):
    user = User.objects.create_user(
        username='forced@example.com',
        email='forced@example.com',
        password='Temporary-password-123!',
    )
    user.must_change_password = True
    user.save(update_fields=['must_change_password'])
    client.force_login(user)

    response = client.get(reverse('core:home'))
    assert response.status_code == 302
    assert response.url == reverse('accounts:profile')

    profile_response = client.get(reverse('accounts:profile'))
    assert profile_response.status_code == 200


@pytest.mark.django_db
def test_password_change_clears_forced_flag_and_requires_current_password(client):
    user = User.objects.create_user(
        username='change@example.com',
        email='change@example.com',
        password='Temporary-password-123!',
    )
    user.must_change_password = True
    user.save(update_fields=['must_change_password'])
    client.force_login(user)

    wrong_old_response = client.post(
        reverse('accounts:profile_change_password'),
        {
            'old_password': 'not-the-current-password',
            'password1': 'New-strong-password-123!',
            'password2': 'New-strong-password-123!',
        },
    )
    assert wrong_old_response.status_code == 200
    user.refresh_from_db()
    assert user.must_change_password is True
    assert user.check_password('Temporary-password-123!')

    response = client.post(
        reverse('accounts:profile_change_password'),
        {
            'old_password': 'Temporary-password-123!',
            'password1': 'New-strong-password-123!',
            'password2': 'New-strong-password-123!',
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.must_change_password is False
    assert user.check_password('New-strong-password-123!')


@pytest.mark.django_db
def test_ensure_admin_requires_secret_for_new_installation(monkeypatch):
    monkeypatch.delenv('INITIAL_ADMIN_PASSWORD', raising=False)

    with pytest.raises(CommandError, match='INITIAL_ADMIN_PASSWORD'):
        call_command('ensure_admin')

    assert not User.objects.filter(email='admin@yelen.edu').exists()


@pytest.mark.django_db
def test_ensure_admin_creates_once_and_does_not_reset_on_restart(monkeypatch):
    monkeypatch.setenv('INITIAL_ADMIN_PASSWORD', 'First-initial-secret-123!')

    call_command('ensure_admin')
    admin = User.objects.get(email='admin@yelen.edu')
    assert admin.check_password('First-initial-secret-123!')
    assert admin.must_change_password is True

    monkeypatch.setenv('INITIAL_ADMIN_PASSWORD', 'Different-secret-456!')
    call_command('ensure_admin')
    admin.refresh_from_db()
    assert admin.check_password('First-initial-secret-123!')
    assert not admin.check_password('Different-secret-456!')


@pytest.mark.django_db
def test_ensure_admin_reset_is_explicit(monkeypatch):
    monkeypatch.setenv('INITIAL_ADMIN_PASSWORD', 'First-initial-secret-123!')
    call_command('ensure_admin')

    monkeypatch.setenv('INITIAL_ADMIN_PASSWORD', 'Reset-secret-789!')
    call_command('ensure_admin', '--reset')

    admin = User.objects.get(email='admin@yelen.edu')
    assert admin.check_password('Reset-secret-789!')
    assert admin.must_change_password is True


@pytest.mark.django_db
def test_legacy_admin_password_is_marked_for_change_without_reset(monkeypatch):
    admin = User.objects.create_superuser(
        username='admin@yelen.edu',
        email='admin@yelen.edu',
        password='admin123',
    )
    assert admin.must_change_password is False
    monkeypatch.delenv('INITIAL_ADMIN_PASSWORD', raising=False)

    call_command('ensure_admin')

    admin.refresh_from_db()
    assert admin.check_password('admin123')
    assert admin.must_change_password is True
