from django.urls import path
from . import views

app_name = 'examens'

urlpatterns = [
    # Sessions
    path('', views.session_list, name='session_list'),
    path('nouvelle/', views.session_create, name='session_create'),
    path('<uuid:session_id>/', views.session_detail, name='session_detail'),
    path('<uuid:session_id>/modifier/', views.session_edit, name='session_edit'),

    # Inscription d'une classe
    path('<uuid:session_id>/inscrire/<uuid:classe_id>/', views.inscrire_classe, name='inscrire_classe'),

    # Saisie des résultats
    path('<uuid:session_id>/resultats/', views.saisie_resultats, name='saisie_resultats'),

    # Centres
    path('<uuid:session_id>/centres/nouveau/', views.centre_create, name='centre_create'),
    path('centres/<uuid:centre_id>/modifier/', views.centre_edit, name='centre_edit'),
    path('centres/<uuid:centre_id>/supprimer/', views.centre_delete, name='centre_delete'),

    # Salles
    path('centres/<uuid:centre_id>/salles/nouvelle/', views.salle_create, name='salle_create'),
    path('salles/<uuid:salle_id>/modifier/', views.salle_edit, name='salle_edit'),
    path('salles/<uuid:salle_id>/supprimer/', views.salle_delete, name='salle_delete'),
]
