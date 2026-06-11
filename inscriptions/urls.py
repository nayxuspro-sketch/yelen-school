from django.urls import path
from . import views

app_name = 'inscriptions'

urlpatterns = [
    path('', views.eleve_list, name='eleve_list'),
    path('csv/', views.eleve_list_csv, name='eleve_list_csv'),
    path('xlsx/', views.eleve_list_xlsx, name='eleve_list_xlsx'),
    path('pdf/', views.eleve_list_pdf, name='eleve_list_pdf'),
    path('eleve/nouveau/', views.eleve_create, name='eleve_create'),
    path('eleve/<uuid:pk>/', views.eleve_detail, name='eleve_detail'),
    path('eleve/<uuid:pk>/modifier/', views.eleve_update, name='eleve_update'),
    path('eleve/<uuid:pk>/supprimer/', views.eleve_delete, name='eleve_delete'),
    path('eleve/<uuid:pk>/inscrire/', views.inscription_create, name='inscription_create'),
    path('inscription/<uuid:pk>/modifier/', views.inscription_update, name='inscription_update'),
    path('inscription/<uuid:pk>/abandon/', views.marquer_abandon, name='marquer_abandon'),
    path('inscription/<uuid:pk>/transfert/', views.transfert_classe, name='transfert_classe'),
    path('api/classes/<uuid:pk>/niveau/', views.get_classe_niveau, name='classe_niveau'),
    path('api/classes/<uuid:pk>/cycle/', views.get_classe_cycle, name='classe_cycle'),
    path('api/statut-eleve/<uuid:pk>/code/', views.get_statut_code, name='statut_code'),
    # Carte scolaire
    path('eleve/<uuid:pk>/carte/', views.eleve_carte, name='eleve_carte'),
    path('classe/<uuid:pk>/cartes-pdf/', views.classe_cartes_pdf, name='classe_cartes_pdf'),
    # Réinscription
    path('reinscription/', views.reinscription_list, name='reinscription_list'),
    path('reinscription/eleve/<uuid:pk>/', views.reinscrire_eleve, name='reinscrire_eleve'),
    # Parcours scolaire
    path('eleve/<uuid:pk>/parcours/', views.eleve_parcours, name='eleve_parcours'),
    path('evenement/<uuid:pk>/supprimer/', views.evenement_parcours_supprimer, name='evenement_supprimer'),
    # Transferts inter-établissements
    path('transferts/', views.transfert_inter_list, name='transfert_inter_list'),
    path('inscription/<uuid:inscription_id>/transfert-inter/', views.transfert_inter_demander, name='transfert_inter_demander'),
    path('transferts/<uuid:pk>/', views.transfert_inter_detail, name='transfert_inter_detail'),
    path('transferts/<uuid:pk>/approuver/', views.transfert_inter_approuver, name='transfert_inter_approuver'),
    path('transferts/<uuid:pk>/refuser/', views.transfert_inter_refuser, name='transfert_inter_refuser'),
    path('transferts/<uuid:pk>/dossier/pdf/', views.transfert_inter_dossier_pdf, name='transfert_inter_dossier_pdf'),
    # Import Excel
    path('import/template/', views.eleve_import_template, name='eleve_import_template'),
    path('import/', views.eleve_import, name='eleve_import'),
]
