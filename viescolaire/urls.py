from django.urls import path
from . import views

app_name = 'viescolaire'

urlpatterns = [
    # Conseils de classe
    path('conseils/', views.conseil_list, name='conseil_list'),
    path('conseils/creer/', views.conseil_create, name='conseil_create'),
    path('conseils/<uuid:conseil_id>/', views.conseil_detail, name='conseil_detail'),

    # Sanctions disciplinaires
    path('sanctions/', views.sanction_list, name='sanction_list'),
    path('sanctions/creer/', views.sanction_create, name='sanction_create'),
    path('sanctions/<uuid:sanction_id>/supprimer/', views.sanction_delete, name='sanction_delete'),

    # Activités parascolaires
    path('activites/', views.activite_list, name='activite_list'),
    path('activites/<uuid:activite_id>/', views.activite_detail, name='activite_detail'),
]
