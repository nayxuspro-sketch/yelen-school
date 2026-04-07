from django.urls import path
from . import views

app_name = 'inscriptions'

urlpatterns = [
    path('', views.eleve_list, name='eleve_list'),
    path('eleve/nouveau/', views.eleve_create, name='eleve_create'),
    path('eleve/<uuid:pk>/', views.eleve_detail, name='eleve_detail'),
    path('eleve/<uuid:pk>/modifier/', views.eleve_update, name='eleve_update'),
    path('eleve/<uuid:pk>/inscrire/', views.inscription_create, name='inscription_create'),
    path('inscription/<uuid:pk>/modifier/', views.inscription_update, name='inscription_update'),
    path('inscription/<uuid:pk>/abandon/', views.marquer_abandon, name='marquer_abandon'),
    path('api/classes/<uuid:pk>/niveau/', views.get_classe_niveau, name='classe_niveau'),
    path('api/classes/<uuid:pk>/cycle/', views.get_classe_cycle, name='classe_cycle'),
    path('api/statut-eleve/<uuid:pk>/code/', views.get_statut_code, name='statut_code'),
    # Carte scolaire
    path('eleve/<uuid:pk>/carte/', views.eleve_carte, name='eleve_carte'),
    path('classe/<uuid:pk>/cartes-pdf/', views.classe_cartes_pdf, name='classe_cartes_pdf'),
]
