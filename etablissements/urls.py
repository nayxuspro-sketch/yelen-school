from django.urls import path
from . import views

app_name = 'etablissements'

urlpatterns = [
    path('', views.etablissement_detail, name='detail'),
    # Dashboard réseau
    path('reseau/', views.reseau_dashboard, name='reseau_dashboard'),
    # Gestion des groupes
    path('groupes/', views.groupe_list, name='groupe_list'),
    path('groupes/nouveau/', views.groupe_form, name='groupe_create'),
    path('groupes/<uuid:pk>/modifier/', views.groupe_form, name='groupe_edit'),
    path('groupes/<uuid:groupe_pk>/affecter/', views.groupe_affecter_etab, name='groupe_affecter_etab'),
]
