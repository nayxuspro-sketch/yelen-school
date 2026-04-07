from django.urls import path
from . import views

app_name = 'presences'

urlpatterns = [
    path('', views.appel_list, name='appel_list'),
    path('imprimer/', views.appel_print, name='appel_print'),
    path('classes/', views.classe_select, name='classe_select'),
    path('appel/classe/<uuid:classe_id>/', views.appel_create, name='appel_create'),
    path('appel/<uuid:appel_id>/saisie/', views.appel_saisie, name='appel_saisie'),
    path('eleve/<uuid:inscription_id>/bilan/', views.bilan_eleve, name='bilan_eleve'),
    path('eleve/<uuid:inscription_id>/justification/', views.justification_create, name='justification_create'),
    path('justifications/', views.justification_list, name='justification_list'),
    path('justifications/<uuid:justification_id>/traiter/', views.justification_process, name='justification_process'),
]
