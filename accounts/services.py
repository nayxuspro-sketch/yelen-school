"""
Services d'authentification partagés entre l'interface web et l'API.

Objectif : appliquer le verrouillage temporaire des comptes sans jamais
révéler à un attaquant si un identifiant existe, s'il est verrouillé ou si le
mot de passe était bon. Toutes les issues négatives sont indistinguables :
même message, même code de réponse, même ordre de grandeur de temps de calcul.
"""
from django.contrib.auth import authenticate
from django.utils import timezone

from core.audit import record_audit

from .models import User

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Message unique pour tous les échecs (compte inconnu, mot de passe faux,
# compte verrouillé) : informe l'utilisateur légitime de la règle sans donner
# d'indice sur la cause réelle.
LOGIN_FAILURE_MESSAGE = (
    "Identifiant ou mot de passe incorrect. "
    f"Après {MAX_LOGIN_ATTEMPTS} échecs consécutifs, le compte est verrouillé "
    f"{LOCKOUT_DURATION_MINUTES} minutes."
)


def _is_locked(user, now):
    return bool(user.locked_until and user.locked_until > now)


def register_failed_attempt(user, request=None):
    """Incrémente le compteur d'échecs et verrouille le compte au seuil."""
    user.failed_login_attempts += 1
    update_fields = ['failed_login_attempts']
    if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
        user.locked_until = timezone.now() + timezone.timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update_fields.append('locked_until')
    user.save(update_fields=update_fields)
    if user.locked_until and 'locked_until' in update_fields:
        record_audit(
            instance=user,
            action='SECURITY',
            changes={'event': 'account_locked', 'failed_attempts': user.failed_login_attempts},
            request=request,
            reason=f"Verrouillage temporaire après {user.failed_login_attempts} échecs de connexion",
        )


def clear_failed_attempts(user):
    """Remet à zéro le compteur et le verrou après une connexion réussie."""
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_attempts', 'locked_until'])


def authenticate_with_lockout(request, email, password):
    """
    Vérifie les identifiants en appliquant le verrouillage temporaire.

    Retourne l'utilisateur authentifié, ou ``None`` dans tous les autres cas :
    - compte inconnu : ``authenticate()`` exécute un hachage factice (temps
      comparable à un vrai compte) et rien n'est enregistré ;
    - mot de passe faux : le compteur d'échecs est incrémenté, le compte est
      verrouillé au seuil ;
    - compte verrouillé : le résultat est ignoré, même si le mot de passe est
      bon (aucun oracle pendant le verrouillage) et le compteur n'évolue pas.
    """
    email = (email or '').strip()
    password = password or ''
    now = timezone.now()
    known_user = User.objects.filter(email__iexact=email).first() if email else None

    # Toujours évaluer le mot de passe : le temps de réponse ne doit pas
    # dépendre de l'existence ou de l'état du compte. L'identifiant est
    # insensible à la casse : on authentifie avec l'adresse telle qu'enregistrée.
    username = known_user.email if known_user is not None else email
    authenticated = authenticate(request, username=username, password=password)

    if known_user is not None and _is_locked(known_user, now):
        return None

    if authenticated is None:
        if known_user is not None:
            register_failed_attempt(known_user, request=request)
        return None

    clear_failed_attempts(authenticated)
    return authenticated
