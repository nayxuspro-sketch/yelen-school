from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('certificat/<uuid:inscription_id>/', views.certificat_scolarite, name='certificat_scolarite'),
    path('listes/', views.liste_classes_selector, name='liste_classes_selector'),
    path('liste-classe/<uuid:classe_id>/', views.liste_classe_pdf, name='liste_classe_pdf'),
    path('personnel/', views.liste_personnel_selector, name='liste_personnel_selector'),
    path('personnel/<uuid:cycle_id>/', views.liste_personnel_pdf, name='liste_personnel_pdf'),
]
