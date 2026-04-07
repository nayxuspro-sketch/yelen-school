from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('paiements/', views.paiement_list, name='paiement_list'),
    path('paiements/nouveau/', views.paiement_create, name='paiement_create'),
    path('paiements/<uuid:paiement_id>/recu/pdf/', views.recu_pdf, name='recu_pdf'),
    path('redevables/', views.liste_redevables, name='liste_redevables'),
    path('redevables/pdf/', views.liste_redevables_pdf, name='liste_redevables_pdf'),
    path('bilan/encaissements/', views.bilan_encaissements, name='bilan_encaissements'),
    path('bilan/encaissements/pdf/', views.bilan_encaissements_pdf, name='bilan_encaissements_pdf'),
    path('situation/eleve/<uuid:inscription_id>/', views.situation_eleve, name='situation_eleve'),
    path('situation/eleve/<uuid:inscription_id>/historique/pdf/', views.historique_pdf, name='historique_pdf'),
    path('api/rubriques/<uuid:inscription_id>/', views.api_rubriques_inscription, name='api_rubriques'),

    # Relances de paiement
    path('relances/', views.relance_paiement, name='relance_paiement'),
    path('relances/pdf/', views.relance_paiement_pdf, name='relance_paiement_pdf'),
    path('relances/count/', views.relance_count, name='relance_count'),

    # Échéancier
    path('echeancier/<uuid:inscription_id>/creer/', views.echeancier_create, name='echeancier_create'),
    path('echeancier/<uuid:echeancier_id>/modifier/', views.echeancier_edit, name='echeancier_edit'),
    path('echeancier/<uuid:echeancier_id>/supprimer/', views.echeancier_delete, name='echeancier_delete'),

    # Certificat de non-redevabilité
    path(
        'situation/eleve/<uuid:inscription_id>/certificat/non-redevabilite/',
        views.certificat_non_redevabilite,
        name='certificat_non_redevabilite',
    ),

    # Élèves exonérés
    path('exoneres/', views.liste_exoneres, name='liste_exoneres'),
    path('exoneres/pdf/', views.liste_exoneres_pdf, name='liste_exoneres_pdf'),
]
