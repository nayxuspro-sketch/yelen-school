from django.urls import path

from . import views

app_name = 'bulletins'

urlpatterns = [
    # Index — sélecteur classe / trimestre
    path('', views.bulletins_index, name='index'),

    # Bulletins d'une classe pour un trimestre
    path(
        'classe/<uuid:class_id>/trimestre/<uuid:trimestre_id>/',
        views.bulletins_classe,
        name='bulletins_classe',
    ),

    # Saisie absences + appréciation conseil (HTMX)
    path(
        'inscription/<uuid:inscription_id>/trimestre/<uuid:trimestre_id>/saisir/',
        views.bulletin_saisir,
        name='bulletin_saisir',
    ),

    # Toggle publication individuel (HTMX POST)
    path(
        'inscription/<uuid:inscription_id>/trimestre/<uuid:trimestre_id>/publier/',
        views.bulletin_publier,
        name='bulletin_publier',
    ),

    # Publication en masse pour toute une classe (POST)
    path(
        'classe/<uuid:class_id>/trimestre/<uuid:trimestre_id>/publier-tous/',
        views.bulletins_classe_publier,
        name='bulletins_classe_publier',
    ),
]
