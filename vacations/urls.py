from django.urls import path
from . import views

app_name = 'vacations'

urlpatterns = [
    path('', views.contrat_list, name='contrat_list'),
    path('contrat/<uuid:contrat_id>/heures/', views.saisie_heures, name='saisie_heures'),
    path('bulletins/', views.bulletin_list, name='bulletin_list'),
    path('bulletin/<uuid:contrat_id>/<int:mois>/<int:annee>/', views.generer_bulletin, name='generer_bulletin'),
]
