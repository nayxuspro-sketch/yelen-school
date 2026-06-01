from django.urls import path
from . import views  # noqa: F401

app_name = 'personnel'

urlpatterns = [
    path('', views.personnel_list, name='personnel_list'),
    path('csv/', views.personnel_list_csv, name='personnel_list_csv'),
    path('xlsx/', views.personnel_list_xlsx, name='personnel_list_xlsx'),
    path('nouveau/', views.personnel_create, name='create'),
    path('<uuid:pk>/', views.personnel_detail, name='detail'),
    path('<uuid:pk>/modifier/', views.personnel_update, name='update'),
    path('<uuid:pk>/inscription/', views.inscription_create, name='inscription_create'),
    path('inscriptions/<uuid:inscription_id>/modifier/', views.inscription_edit, name='inscription_edit'),
    path('inscriptions/<uuid:inscription_id>/supprimer/', views.inscription_delete, name='inscription_delete'),
    path('<uuid:pk>/toggle-active/', views.toggle_active, name='toggle_active'),
    path('<uuid:pk>/badge/', views.badge_personnel, name='badge'),
    path('<uuid:pk>/contrat/', views.contrat_travail, name='contrat'),

    # Salaires
    path('salaires/', views.salaire_list, name='salaire_list'),
    path('salaires/nouveau/', views.salaire_create, name='salaire_create'),
    path('<uuid:pk>/salaire/nouveau/', views.salaire_create, name='salaire_create_pour'),
    path('salaires/<uuid:pk>/', views.salaire_detail, name='salaire_detail'),
    path('salaires/<uuid:pk>/modifier/', views.salaire_update, name='salaire_update'),
    path('salaires/<uuid:pk>/valider/', views.salaire_valider, name='salaire_valider'),
    path('salaires/<uuid:pk>/payer/', views.salaire_payer, name='salaire_payer'),
    path('salaires/<uuid:pk>/supprimer/', views.salaire_delete, name='salaire_delete'),

    # Congés
    path('conges/', views.conge_list, name='conge_list'),
    path('conges/nouveau/', views.conge_create, name='conge_create'),
    path('<uuid:pk>/conge/nouveau/', views.conge_create, name='conge_create_pour'),
    path('conges/<uuid:pk>/approuver/', views.conge_approuver, name='conge_approuver'),
    path('conges/<uuid:pk>/refuser/', views.conge_refuser, name='conge_refuser'),
    path('conges/<uuid:pk>/autorisation/', views.conge_autorisation_pdf, name='conge_autorisation'),
]
