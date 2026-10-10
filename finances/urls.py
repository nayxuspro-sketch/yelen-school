from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('paiements/', views.paiement_list, name='paiement_list'),
    path('paiements/nouveau/', views.paiement_create, name='paiement_create'),
    path('paiements/recherche-eleve/', views.paiement_recherche_eleve, name='paiement_recherche_eleve'),
    path('paiements/confirmation/', views.paiement_confirmation, name='paiement_confirmation'),
    path('paiements/<uuid:paiement_id>/recu/pdf/', views.recu_pdf, name='recu_pdf'),
    path('paiements/<uuid:paiement_id>/rembourser/', views.remboursement_create, name='remboursement_create'),
    path('remboursements/<uuid:remboursement_id>/annuler/', views.remboursement_delete, name='remboursement_delete'),
    path('redevables/', views.liste_redevables, name='liste_redevables'),
    path('redevables/pdf/', views.liste_redevables_pdf, name='liste_redevables_pdf'),
    path('bilan/encaissements/', views.bilan_encaissements, name='bilan_encaissements'),
    path('bilan/encaissements/pdf/', views.bilan_encaissements_pdf, name='bilan_encaissements_pdf'),
    path('bilan/encaissements/csv/', views.bilan_encaissements_csv, name='bilan_encaissements_csv'),
    path('bilan/encaissements/xlsx/', views.bilan_encaissements_xlsx, name='bilan_encaissements_xlsx'),
    path('situation/eleve/<uuid:inscription_id>/', views.situation_eleve, name='situation_eleve'),
    path('situation/eleve/<uuid:inscription_id>/historique/pdf/', views.historique_pdf, name='historique_pdf'),
    path('api/rubriques/<uuid:inscription_id>/', views.api_rubriques_inscription, name='api_rubriques'),

    # Relances de paiement
    path('relances/', views.relance_paiement, name='relance_paiement'),
    path('relances/pdf/', views.relance_paiement_pdf, name='relance_paiement_pdf'),
    path('relances/count/', views.relance_count, name='relance_count'),
    path('relances/sms/', views.relance_sms, name='relance_sms'),
    path('relances/historique/', views.historique_relances, name='historique_relances'),

    # Tableau global des échéanciers
    path('echeanciers/', views.echeancier_global, name='echeancier_global'),
    path('echeanciers/xlsx/', views.echeancier_global_xlsx, name='echeancier_global_xlsx'),

    # Échéancier par élève
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

    # Bourses et aides scolaires — attribution par élève
    path('bourses/eleve/<uuid:inscription_id>/attribuer/', views.bourse_create, name='bourse_create'),
    path('bourses/<uuid:bourse_id>/modifier/', views.bourse_edit, name='bourse_edit'),
    path('bourses/<uuid:bourse_id>/supprimer/', views.bourse_delete, name='bourse_delete'),

    # Bourses — tableau de bord global
    path('bourses/', views.boursiers_list, name='boursiers_list'),
    path('bourses/pdf/', views.boursiers_pdf, name='boursiers_pdf'),

    # Types de bourses (paramétrage)
    path('types-bourses/', views.type_bourse_list, name='type_bourse_list'),
    path('types-bourses/nouveau/', views.type_bourse_form, name='type_bourse_create'),
    path('types-bourses/<uuid:type_id>/modifier/', views.type_bourse_form, name='type_bourse_edit'),
    path('types-bourses/<uuid:type_id>/supprimer/', views.type_bourse_delete, name='type_bourse_delete'),

    # API AJAX
    path('api/bourse/calculer/', views.api_calculer_bourse, name='api_calculer_bourse'),

    # Mobile Money
    path('mobile-money/', views.mobile_money_list, name='mobile_money_list'),
    path('mobile-money/nouveau/', views.mobile_money_create, name='mobile_money_create'),
    path('mobile-money/<uuid:pk>/confirmer/', views.mobile_money_confirmer, name='mobile_money_confirmer'),
    path('mobile-money/<uuid:pk>/annuler/', views.mobile_money_annuler, name='mobile_money_annuler'),
    path('payer/<str:token>/', views.mobile_money_confirmation_parent, name='mobile_money_confirmation_parent'),

    # ── Budget & Dépenses ──────────────────────────────────────────────────
    path('depenses/', views.depense_list, name='depense_list'),
    path('depenses/nouvelle/', views.depense_form, name='depense_create'),
    path('depenses/<uuid:pk>/modifier/', views.depense_form, name='depense_edit'),
    path('depenses/<uuid:pk>/supprimer/', views.depense_delete, name='depense_delete'),
    path('depenses/<uuid:pk>/valider/', views.depense_valider, name='depense_valider'),
    path('depenses/<uuid:pk>/annuler/', views.depense_annuler, name='depense_annuler'),

    path('budget/', views.budget_previsionnel, name='budget_previsionnel'),
    path('budget/tresorerie/', views.tableau_bord_budget, name='tableau_bord_budget'),
    path('budget/tresorerie/xlsx/', views.tableau_bord_budget_xlsx, name='tableau_bord_budget_xlsx'),

    path('categories-depenses/', views.categorie_depense_list, name='categorie_depense_list'),
    path('categories-depenses/nouvelle/', views.categorie_depense_form, name='categorie_depense_create'),
    path('categories-depenses/<uuid:pk>/modifier/', views.categorie_depense_form, name='categorie_depense_edit'),
    path('categories-depenses/<uuid:pk>/supprimer/', views.categorie_depense_delete, name='categorie_depense_delete'),
]
