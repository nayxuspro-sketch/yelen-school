from django.urls import path

from . import views

app_name = 'bulletins'

urlpatterns = [
    # Index — sélecteur classe / trimestre
    path('', views.bulletins_index, name='index'),

    # Index bulletin annuel
    path(
        'annuel/',
        views.BulletinAnnuelIndexView.as_view(),
        name='bulletin_annuel_index',
    ),

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

    # ── Bulletin annuel ───────────────────────────────────────
    path(
        'inscription/<uuid:inscription_id>/annee/<uuid:annee_pk>/bulletin-annuel/',
        views.BulletinAnnuelView.as_view(),
        name='bulletin_annuel',
    ),
    path(
        'inscription/<uuid:inscription_id>/annee/<uuid:annee_pk>/bulletin-annuel/pdf/',
        views.BulletinAnnuelPDFView.as_view(),
        name='bulletin_annuel_pdf',
    ),
    path(
        'classe/<uuid:class_id>/annee/<uuid:annee_pk>/annuel/batch/pdf/',
        views.BulletinAnnuelBatchPDFView.as_view(),
        name='bulletin_annuel_batch_pdf',
    ),

    # Signature électronique parentale (accès public par token)
    path('parent/<str:token>/', views.bulletin_parent_consulter, name='bulletin_parent_consulter'),
    path('parent/<str:token>/signer/', views.bulletin_parent_signer, name='bulletin_parent_signer'),
]
