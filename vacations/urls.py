from django.urls import path
from . import views

app_name = 'vacations'

urlpatterns = [
    path('', views.contrat_list, name='contrat_list'),
    path('nouveau/', views.contrat_create, name='contrat_create'),
    path('contrat/<uuid:contrat_id>/heures/', views.saisie_heures, name='saisie_heures'),
    path('heures/<uuid:heure_id>/valider/', views.valider_heure, name='valider_heure'),
    path('heures/<uuid:heure_id>/invalider/', views.invalider_heure, name='invalider_heure'),
    path('bulletins/', views.bulletin_list, name='bulletin_list'),
    path('bulletins/generer/', views.generer_tous_bulletins, name='generer_tous_bulletins'),
    path('bulletins/<uuid:bulletin_id>/valider/', views.valider_bulletin, name='valider_bulletin'),
    path('bulletins/<uuid:bulletin_id>/payer/', views.payer_bulletin, name='payer_bulletin'),
    path('bulletin/<uuid:contrat_id>/<int:mois>/<int:annee>/', views.generer_bulletin, name='generer_bulletin'),
    path('bulletin/<uuid:bulletin_id>/pdf/', views.bulletin_vacation_pdf, name='bulletin_vacation_pdf'),
]
