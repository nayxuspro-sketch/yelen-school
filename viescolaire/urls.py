from django.urls import path
from . import views

app_name = 'viescolaire'

urlpatterns = [
    # Conseils de classe
    path('conseils/', views.conseil_list, name='conseil_list'),
    path('conseils/creer/', views.conseil_create, name='conseil_create'),
    path('conseils/<uuid:conseil_id>/', views.conseil_detail, name='conseil_detail'),
    path('conseils/<uuid:conseil_id>/pv-pdf/', views.conseil_pv_pdf, name='conseil_pv_pdf'),

    # Sanctions disciplinaires
    path('sanctions/', views.sanction_list, name='sanction_list'),
    path('sanctions/creer/', views.sanction_create, name='sanction_create'),
    path('sanctions/<uuid:sanction_id>/supprimer/', views.sanction_delete, name='sanction_delete'),

    # Activités parascolaires
    path('activites/', views.activite_list, name='activite_list'),
    path('activites/creer/', views.activite_create, name='activite_create'),
    path('activites/<uuid:activite_id>/', views.activite_detail, name='activite_detail'),
    path('activites/<uuid:activite_id>/modifier/', views.activite_edit, name='activite_edit'),
    path('activites/<uuid:activite_id>/supprimer/', views.activite_delete, name='activite_delete'),

    # Fiches de suivi
    path('fiches-suivi/', views.fiches_suivi_list, name='fiches_suivi_list'),
    path('eleve/<uuid:inscription_id>/fiche-suivi/', views.fiche_suivi_eleve, name='fiche_suivi_eleve'),

    # Discipline — capital points
    path('discipline/config/', views.config_discipline, name='config_discipline'),
    path('discipline/capital/', views.capital_points_list, name='capital_points_list'),

    # Appels de décision
    path('appels-decision/', views.appel_decision_list, name='appel_decision_list'),
    path('decision/<uuid:decision_id>/contester/', views.appel_decision_create, name='appel_decision_create'),
    path('appels-decision/<uuid:appel_id>/traiter/', views.appel_decision_traiter, name='appel_decision_traiter'),

    # Emploi du temps
    path('emploi-du-temps/', views.emploi_du_temps_index, name='emploi_du_temps_index'),
    path('classe/<uuid:classe_id>/emploi-du-temps/', views.emploi_du_temps, name='emploi_du_temps'),
    path('classe/<uuid:classe_id>/emploi-du-temps/pdf/', views.emploi_du_temps_pdf, name='emploi_du_temps_pdf'),
    path('classe/<uuid:classe_id>/seance/ajouter/', views.seance_create, name='seance_create'),
    path('seance/<uuid:seance_id>/supprimer/', views.seance_delete, name='seance_delete'),
]
