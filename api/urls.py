"""
api/urls.py — Routes de l'API publique YELEN SCHOOL
"""

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # ── Authentification ──────────────────────────────────────────
    path('auth/token/',          views.ObtenirTokenView.as_view(),   name='obtenir_token'),
    path('auth/token/revoke/',   views.RevoquerTokenView.as_view(),  name='revoquer_token'),

    # ── Années scolaires ──────────────────────────────────────────
    path('annees/',                          views.AnneesListView.as_view(),     name='annees_list'),
    path('annees/<int:annee_id>/periodes/',  views.AnneePeriodesView.as_view(),  name='annee_periodes'),

    # ── Élèves ────────────────────────────────────────────────────
    path('eleves/',                           views.ElevesListView.as_view(),      name='eleves_list'),
    path('eleves/<uuid:pk>/',                  views.EleveDetailView.as_view(),     name='eleve_detail'),
    path('eleves/<uuid:pk>/inscriptions/',     views.EleveInscriptionsView.as_view(), name='eleve_inscriptions'),
    path('eleves/<uuid:pk>/bulletins/',        views.EleveBulletinsView.as_view(),  name='eleve_bulletins'),
    path('eleves/<uuid:pk>/moyennes/',         views.EleveMoyennesView.as_view(),   name='eleve_moyennes'),
    path('eleves/<uuid:pk>/paiements/',        views.ElevePaiementsView.as_view(),  name='eleve_paiements'),
    path('eleves/<uuid:pk>/presences/',        views.ElevePresencesView.as_view(),  name='eleve_presences'),
]
