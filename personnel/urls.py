from django.urls import path
from . import views  # noqa: F401

app_name = 'personnel'

urlpatterns = [
    path('', views.personnel_list, name='personnel_list'),
    path('csv/', views.personnel_list_csv, name='personnel_list_csv'),
    path('xlsx/', views.personnel_list_xlsx, name='personnel_list_xlsx'),
    path('pdf/', views.personnel_list_pdf, name='personnel_list_pdf'),
    path('nouveau/', views.personnel_create, name='create'),
    path('<uuid:pk>/', views.personnel_detail, name='detail'),
    path('<uuid:pk>/modifier/', views.personnel_update, name='update'),
    path('<uuid:pk>/inscription/', views.inscription_create, name='inscription_create'),
    path('inscriptions/<uuid:inscription_id>/modifier/', views.inscription_edit, name='inscription_edit'),
    path('inscriptions/<uuid:inscription_id>/supprimer/', views.inscription_delete, name='inscription_delete'),
    path('<uuid:pk>/toggle-active/', views.toggle_active, name='toggle_active'),
    path('<uuid:pk>/badge/', views.badge_personnel, name='badge'),
    path('<uuid:pk>/contrat/', views.contrat_travail, name='contrat'),
    path('<uuid:pk>/attestation-travail/', views.attestation_travail, name='attestation_travail'),

    # Salaires
    path('salaires/', views.salaire_list, name='salaire_list'),
    path('salaires/paie/', views.paie_mois, name='paie_mois'),
    path('salaires/paie/preparer/', views.paie_preparer, name='paie_preparer'),
    path('salaires/paie/valider/', views.paie_valider, name='paie_valider'),
    path('salaires/paie/livre.pdf', views.livre_paie_pdf, name='livre_paie_pdf'),
    path('salaires/paie/bulletins.pdf', views.bulletins_paie_lot_pdf, name='bulletins_paie_lot_pdf'),
    path('salaires/nouveau/', views.salaire_create, name='salaire_create'),
    path('<uuid:pk>/salaire/nouveau/', views.salaire_create, name='salaire_create_pour'),
    path('salaires/<uuid:pk>/', views.salaire_detail, name='salaire_detail'),
    path('salaires/<uuid:pk>/modifier/', views.salaire_update, name='salaire_update'),
    path('salaires/<uuid:pk>/valider/', views.salaire_valider, name='salaire_valider'),
    path('salaires/<uuid:pk>/payer/', views.salaire_payer, name='salaire_payer'),
    path('salaires/<uuid:pk>/supprimer/', views.salaire_delete, name='salaire_delete'),

    # Pointage et évaluation annuelle
    path('pointage/', views.pointage_jour, name='pointage_jour'),
    path('pointage/mois/', views.pointage_mois, name='pointage_mois'),
    path('pointage/mois.pdf', views.pointage_mois_pdf, name='pointage_mois_pdf'),
    path('evaluations/', views.evaluation_list, name='evaluation_list'),
    path('evaluations/nouvelle/', views.evaluation_form, name='evaluation_create'),
    path('evaluations/<uuid:pk>/', views.evaluation_form, name='evaluation_update'),
    path('evaluations/<uuid:pk>/pdf/', views.evaluation_pdf, name='evaluation_pdf'),
    path('evaluations/<uuid:pk>/supprimer/', views.evaluation_delete, name='evaluation_delete'),

    # Congés
    path('absences/', views.absence_list, name='absence_list'),
    path('absences/imprimer/', views.absence_pdf, name='absence_pdf'),
    path('absences/nouvelle/', views.absence_create, name='absence_create'),
    path('<uuid:pk>/absence/nouvelle/', views.absence_create, name='absence_create_pour'),
    path('absences/<uuid:pk>/supprimer/', views.absence_delete, name='absence_delete'),
    path('absences/observations/nouvelle/', views.observation_absence_create, name='observation_absence_create'),
    path('conges/', views.conge_list, name='conge_list'),
    path('conges/nouveau/', views.conge_create, name='conge_create'),
    path('<uuid:pk>/conge/nouveau/', views.conge_create, name='conge_create_pour'),
    path('conges/<uuid:pk>/approuver/', views.conge_approuver, name='conge_approuver'),
    path('conges/<uuid:pk>/refuser/', views.conge_refuser, name='conge_refuser'),
    path('conges/<uuid:pk>/autorisation/', views.conge_autorisation_pdf, name='conge_autorisation'),
]
