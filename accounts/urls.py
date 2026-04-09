"""URL configuration for accounts app."""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/',      views.login_view,  name='login'),
    path('login/2fa/',  views.login_2fa,   name='login_2fa'),
    path('logout/',     views.logout_view, name='logout'),
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
