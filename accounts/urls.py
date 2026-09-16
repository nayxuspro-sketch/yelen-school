"""URL configuration for accounts app."""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/',      views.login_view,  name='login'),
    path('login/2fa/',  views.login_2fa,   name='login_2fa'),
    path('login/2fa/setup/', views.login_2fa_setup, name='login_2fa_setup'),
    path('logout/',     views.logout_view, name='logout'),

    # Mot de passe oublié — réinitialisation par email avec limitation de débit
    path('mot-de-passe-oublie/',
        views.PasswordResetRateLimitedView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.txt',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='/accounts/mot-de-passe-oublie/envoye/',
        ),
        name='password_reset'),
    path('mot-de-passe-oublie/envoye/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done'),
    path('reinitialiser/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/reinitialiser/termine/',
        ),
        name='password_reset_confirm'),
    path('reinitialiser/termine/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete'),

    # Profil
    path('profile/',    views.profile_view, name='profile'),
    path('profile/mot-de-passe/', views.profile_change_password, name='profile_change_password'),
    path('profile/2fa/activer/',   views.totp_setup,   name='totp_setup'),
    path('profile/2fa/desactiver/', views.totp_disable, name='totp_disable'),

    # Gestion des utilisateurs
    path('utilisateurs/',                   views.user_list,          name='user_list'),
    path('utilisateurs/csv/',               views.user_list_csv,     name='user_list_csv'),
    path('utilisateurs/creer/',             views.user_create,        name='user_create'),
    path('utilisateurs/parent/creer/',      views.parent_create,     name='parent_create'),
    path('utilisateurs/<uuid:pk>/modifier/', views.user_update,       name='user_update'),
    path('utilisateurs/<uuid:pk>/mot-de-passe/', views.user_set_password, name='user_set_password'),
    path('utilisateurs/<uuid:pk>/activer/', views.user_toggle_active, name='user_toggle_active'),
]
