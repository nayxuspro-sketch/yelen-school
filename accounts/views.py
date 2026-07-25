"""
Module Accounts - Views
=======================
YELEN SCHOOL v3.4 - Authentification utilisateur
"""

from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST

from core.models import RoleChoices
from .forms import UserCreateForm, UserUpdateForm, SetPasswordForm, ProfileUpdateForm, ChangeOwnPasswordForm, PasswordResetRateLimitedForm
from .models import User
from licences.models import Licence


# ── Mot de passe oublié — vue avec limitation de débit ────────────────────────

class PasswordResetRateLimitedView(PasswordResetView):
    """PasswordResetView avec limitation de débit (3 req./h) anti-brute force.

    Utilise PasswordResetRateLimitedForm qui vérifie la session
    et bloque après RATE_LIMIT_MAX tentatives par fenêtre.
    """
    form_class = PasswordResetRateLimitedForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.request = self.request
        return form


# ── Helpers ───────────────────────────────────────────────────────────────────

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
_LICENCE_ALERT_DAYS = 30


def _check_licence_post_login(request, user, on_expired_redirect='accounts:login'):
    """
    Vérifie la licence de l'établissement après connexion.
    Déconnecte et retourne une réponse si la licence est expirée.
    Ajoute un warning si elle expire bientôt.
    Retourne None si tout est OK.
    """
    if not user.etablissement_id:
        return None
    try:
        licence = Licence.objects.get(etablissement_id=user.etablissement_id)
        today = timezone.now().date()
        date_alerte = licence.date_expiration - timedelta(days=_LICENCE_ALERT_DAYS)
        if licence.date_expiration < today:
            logout(request)
            messages.error(
                request,
                f"La licence de votre établissement a expiré le "
                f"{licence.date_expiration.strftime('%d/%m/%Y')}. "
                f"Veuillez contacter l'administrateur pour le renouvellement."
            )
            return redirect(on_expired_redirect)
        if date_alerte <= today <= licence.date_expiration:
            jours_restants = (licence.date_expiration - today).days
            messages.warning(
                request,
                f"Attention : la licence de votre établissement expire le "
                f"{licence.date_expiration.strftime('%d/%m/%Y')} "
                f"(dans {jours_restants} jour(s)). Veuillez procéder au renouvellement."
            )
    except Licence.DoesNotExist:
        messages.warning(
            request,
            "Aucune licence n'est associée à votre établissement. "
            "Contactez l'administrateur."
        )
    return None


def _admin_required(view_func):
    """Décorateur : réservé aux SUPER_ADMIN et DIRECTEUR."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role not in (RoleChoices.SUPER_ADMIN, RoleChoices.DIRECTEUR):
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def _can_manage(current_user, target_user):
    """Vérifie qu'un utilisateur peut gérer un autre (même établissement ou super admin)."""
    if current_user.role == RoleChoices.SUPER_ADMIN:
        return True
    return target_user.etablissement_id == current_user.etablissement_id


# ── Authentification ──────────────────────────────────────────────────────────

def _redirect_after_login(request, user, next_url=''):
    """Redirige l'utilisateur vers la bonne page après connexion réussie."""
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    if user.role == 'PARENT':
        return redirect('core:portail_parent')
    if user.role == 'ELEVE':
        return redirect('core:portail_eleve')
    return redirect('core:home')


def login_view(request):
    """Connexion utilisateur — étape 1 : email + mot de passe."""
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '').strip()

        if not email or not password:
            messages.error(request, "Veuillez fournir votre identifiant et mot de passe.")
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.locked_until and user.locked_until > timezone.now():
                remaining_seconds = (user.locked_until - timezone.now()).seconds
                remaining_minutes = remaining_seconds // 60 + 1
                messages.error(
                    request,
                    f"Compte temporairement verrouillé. Réessayez dans {remaining_minutes} minute(s)."
                )
                return render(request, 'accounts/login.html')

            if user.failed_login_attempts > 0 or user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save(update_fields=['failed_login_attempts', 'locked_until'])

            if user.totp_enabled and user.totp_secret:
                request.session['_2fa_user_pk'] = str(user.pk)
                request.session['_2fa_next'] = request.GET.get('next', '')
                return redirect('accounts:login_2fa')

            login(request, user)
            blocked = _check_licence_post_login(request, user, on_expired_redirect='accounts:login')
            if blocked:
                return blocked
            return _redirect_after_login(request, user, request.GET.get('next', ''))
        else:
            messages.error(request, "Identifiant ou mot de passe incorrect.")

            try:
                user = User.objects.get(email__iexact=email)
                user.failed_login_attempts += 1

                if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                    user.locked_until = timezone.now() + timezone.timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                    user.save(update_fields=['failed_login_attempts', 'locked_until'])
                    messages.error(
                        request,
                        f"Compte verrouillé après {MAX_LOGIN_ATTEMPTS} tentatives échouées. "
                        f"Réessayez dans {LOCKOUT_DURATION_MINUTES} minutes."
                    )
                else:
                    remaining = MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
                    messages.error(
                        request,
                        f"Identifiant ou mot de passe incorrect. Il vous reste {remaining} tentative(s)."
                    )
            except User.DoesNotExist:
                pass

    return render(request, 'accounts/login.html')


def login_2fa(request):
    """Connexion utilisateur — étape 2 : code TOTP."""
    user_pk = request.session.get('_2fa_user_pk')
    if not user_pk:
        return redirect('accounts:login')

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return redirect('accounts:login')

    if request.method == 'POST':
        import pyotp
        code = request.POST.get('code', '').strip().replace(' ', '')
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(code, valid_window=1):
            del request.session['_2fa_user_pk']
            next_url = request.session.pop('_2fa_next', '')
            login(request, user)
            blocked = _check_licence_post_login(request, user)
            if blocked:
                return blocked
            return _redirect_after_login(request, user, next_url)
        messages.error(request, "Code incorrect ou expiré. Réessayez.")

    return render(request, 'accounts/login_2fa.html', {'email': user.email})


@require_POST
def logout_view(request):
    """Déconnexion utilisateur (POST uniquement — protection CSRF)."""
    logout(request)
    return redirect('accounts:login')


@login_required
def totp_setup(request):
    """Activation de la 2FA : affiche le QR code et valide le premier code."""
    import pyotp
    import qrcode
    import io
    import base64
    from django.core.signing import Signer

    user = request.user

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().replace(' ', '')
        signed_secret = request.POST.get('signed_secret', '').strip()
        if not signed_secret:
            messages.error(request, "Session expirée. Recommencez.")
            return redirect('accounts:totp_setup')

        try:
            signer = Signer()
            secret = signer.unsign(signed_secret)
        except Exception:
            messages.error(request, "Session expirée. Recommencez.")
            return redirect('accounts:totp_setup')

        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=1):
            user.totp_secret = secret
            user.totp_enabled = True
            user.save(update_fields=['totp_secret', 'totp_enabled'])
            messages.success(request, "Double authentification activée avec succès.")
            return redirect('accounts:profile')
        messages.error(request, "Code incorrect. Vérifiez votre application et réessayez.")

        new_secret = pyotp.random_base32()
    else:
        new_secret = pyotp.random_base32()

    uri = pyotp.TOTP(new_secret).provisioning_uri(name=user.email, issuer_name="YELEN SCHOOL")
    buf = io.BytesIO()
    qrcode.make(uri).save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    signer = Signer()
    signed_secret = signer.sign(new_secret)

    return render(request, 'accounts/totp_setup.html', {
        'signed_secret': signed_secret,
        'qr_b64': qr_b64,
    })


@login_required
def totp_disable(request):
    """Désactivation de la 2FA après vérification du code courant."""
    if request.method != 'POST':
        return redirect('accounts:profile')

    import pyotp
    user = request.user
    if not user.totp_enabled:
        return redirect('accounts:profile')

    code = request.POST.get('code', '').strip().replace(' ', '')
    if pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
        user.totp_secret = ''
        user.totp_enabled = False
        user.save(update_fields=['totp_secret', 'totp_enabled'])
        messages.success(request, "Double authentification désactivée.")
    else:
        messages.error(request, "Code incorrect. La 2FA n'a pas été désactivée.")

    return redirect('accounts:profile')


@login_required
def profile_view(request):
    """Profil de l'utilisateur connecté — modification des infos personnelles."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    pw_form = ChangeOwnPasswordForm(user=request.user)
    return render(request, 'accounts/profile.html', {'form': form, 'pw_form': pw_form})


@login_required
def profile_change_password(request):
    """Changement de mot de passe par l'utilisateur connecté."""
    if request.method != 'POST':
        return redirect('accounts:profile')

    pw_form = ChangeOwnPasswordForm(request.POST, user=request.user)
    if pw_form.is_valid():
        request.user.set_password(pw_form.cleaned_data['password1'])
        request.user.save(update_fields=['password'])
        # Reconnecter après changement de mot de passe pour éviter la déconnexion
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        messages.success(request, "Mot de passe modifié avec succès.")
        return redirect('accounts:profile')

    form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form, 'pw_form': pw_form})


# ── Gestion des utilisateurs ─────────────────────────────────────────────────

@_admin_required
def user_list(request):
    """Liste des utilisateurs avec recherche et filtre par rôle."""
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    page_number = request.GET.get('page', 1)

    users = User.objects.select_related('etablissement').order_by('last_name', 'first_name')

    if request.user.role != RoleChoices.SUPER_ADMIN:
        users = users.filter(etablissement=request.user.etablissement)

    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)

    paginator = Paginator(users, 25)
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/user_list.html', {
        'users': page_obj,
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'roles': RoleChoices.choices,
    })


@_admin_required
def user_create(request):
    """Création d'un nouvel utilisateur."""
    if request.method == 'POST':
        form = UserCreateForm(request.POST, current_user=request.user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Utilisateur {user.get_full_name()} créé avec succès.")
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm(current_user=request.user)

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': "Créer un utilisateur",
    })


@_admin_required
def parent_create(request):
    """Création d'un compte parent avec liaison aux élèves."""
    from .forms import ParentCreateForm
    from inscriptions.models import Inscription
    from parametres.models import AnneeScolaire

    etab = request.user.etablissement

    if request.method == 'POST':
        form = ParentCreateForm(request.POST, etablissement=etab)
        if form.is_valid():
            parent = form.save()
            nb_lies = parent.eleves_lies.count()
            messages.success(request, f"Compte parent créé pour {parent.get_full_name()}. Élèves liés : {nb_lies}")
            return redirect('accounts:user_list')
    else:
        form = ParentCreateForm(etablissement=etab)

    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    eleves_inscrits = []
    if annee_courante:
        seen = set()
        for insc in (
            Inscription.objects
            .filter(
                classe__etablissement=etab,
                annee_scolaire=annee_courante,
                eleve__is_active=True,
            )
            .select_related('eleve', 'classe')
            .order_by('eleve__nom', 'eleve__prenom')
        ):
            pk = str(insc.eleve.pk)
            if pk not in seen:
                seen.add(pk)
                eleves_inscrits.append({
                    'pk': pk,
                    'label': f"{insc.eleve.prenom} {insc.eleve.nom}",
                    'matricule': insc.eleve.matricule or '',
                    'classe': insc.classe.nom,
                })

    selected_eleves = set(form.data.getlist('eleves')) if form.is_bound else set()

    return render(request, 'accounts/parent_form.html', {
        'form': form,
        'title': "Créer un compte parent",
        'eleves_inscrits': eleves_inscrits,
        'selected_eleves': selected_eleves,
    })


@_admin_required
def user_update(request, pk):
    """Modification d'un utilisateur existant."""
    edited_user = get_object_or_404(User, pk=pk)

    if not _can_manage(request.user, edited_user):
        messages.error(request, "Vous ne pouvez pas modifier cet utilisateur.")
        return redirect('accounts:user_list')

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=edited_user, current_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Utilisateur {edited_user.get_full_name()} mis à jour.")
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=edited_user, current_user=request.user)

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': f"Modifier {edited_user.get_full_name()}",
        'edited_user': edited_user,
    })


@_admin_required
def user_set_password(request, pk):
    """Réinitialisation du mot de passe d'un utilisateur."""
    edited_user = get_object_or_404(User, pk=pk)

    if not _can_manage(request.user, edited_user):
        messages.error(request, "Accès non autorisé.")
        return redirect('accounts:user_list')

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            edited_user.set_password(form.cleaned_data['password1'])
            edited_user.save(update_fields=['password'])
            messages.success(request, f"Mot de passe de {edited_user.get_full_name()} modifié.")
            return redirect('accounts:user_list')
    else:
        form = SetPasswordForm()

    return render(request, 'accounts/user_set_password.html', {
        'form': form,
        'edited_user': edited_user,
    })


@_admin_required
def user_toggle_active(request, pk):
    """Activer / désactiver un compte utilisateur."""
    if request.method != 'POST':
        return redirect('accounts:user_list')

    edited_user = get_object_or_404(User, pk=pk)

    if edited_user == request.user:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        return redirect('accounts:user_list')

    if not _can_manage(request.user, edited_user):
        messages.error(request, "Accès non autorisé.")
        return redirect('accounts:user_list')

    edited_user.is_active = not edited_user.is_active
    edited_user.save(update_fields=['is_active'])
    action = "activé" if edited_user.is_active else "désactivé"
    messages.success(request, f"Compte de {edited_user.get_full_name()} {action}.")
    return redirect('accounts:user_list')


@_admin_required
def user_list_csv(request):
    """Export CSV de la liste des utilisateurs."""
    import csv
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    ids = request.GET.get('ids', '')

    users = User.objects.select_related('etablissement').order_by('last_name', 'first_name')

    if request.user.role != RoleChoices.SUPER_ADMIN:
        users = users.filter(etablissement=request.user.etablissement)

    if ids:
        id_list = [id.strip() for id in ids.split(',') if id.strip()]
        if id_list:
            users = users.filter(pk__in=id_list)
    else:
        if query:
            users = users.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            )
        if role_filter:
            users = users.filter(role=role_filter)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="utilisateurs.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nom', 'Prenom', 'Email', 'Role', 'Etablissement', 'Actif'])

    for u in users:
        writer.writerow([
            u.last_name or '',
            u.first_name or '',
            u.email,
            u.get_role_display() if hasattr(u, 'get_role_display') else str(u.role),
            str(u.etablissement) if u.etablissement else '',
            'Oui' if u.is_active else 'Non',
        ])

    return response
