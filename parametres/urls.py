from django.urls import path
from . import views

app_name = 'parametres'

urlpatterns = [
    # Index
    path('', views.parametres_index, name='index'),

    # Années scolaires
    path('annees/', views.annee_list, name='annee_list'),
    path('annees/create/', views.annee_form, name='annee_create'),
    path('annees/<uuid:pk>/edit/', views.annee_form, name='annee_edit'),
    path('annees/<uuid:pk>/set-courante/', views.annee_set_courante, name='annee_set_courante'),
    path('annees/<uuid:pk>/delete/', views.annee_delete, name='annee_delete'),

    # Cycles
    path('cycles/', views.cycle_list, name='cycle_list'),
    path('cycles/create/', views.cycle_form, name='cycle_create'),
    path('cycles/<uuid:pk>/edit/', views.cycle_form, name='cycle_edit'),
    path('cycles/<uuid:pk>/delete/', views.cycle_delete, name='cycle_delete'),

    # Classes
    path('classes/', views.classe_list, name='classe_list'),
    path('classes/create/', views.classe_form, name='classe_create'),
    path('classes/<uuid:pk>/edit/', views.classe_form, name='classe_edit'),
    path('classes/<uuid:pk>/delete/', views.classe_delete, name='classe_delete'),

    # Postes
    path('postes/', views.poste_list, name='poste_list'),
    path('postes/create/', views.poste_form, name='poste_create'),
    path('postes/<uuid:pk>/edit/', views.poste_form, name='poste_edit'),
    path('postes/<uuid:pk>/delete/', views.poste_delete, name='poste_delete'),

    # Statuts élève
    path('statuts/', views.statut_list, name='statut_list'),
    path('statuts/create/', views.statut_form, name='statut_create'),
    path('statuts/<uuid:pk>/edit/', views.statut_form, name='statut_edit'),
    path('statuts/<uuid:pk>/delete/', views.statut_delete, name='statut_delete'),

    # Rubriques paiement
    path('rubriques/', views.rubrique_list, name='rubrique_list'),
    path('rubriques/create/', views.rubrique_form, name='rubrique_create'),
    path('rubriques/<uuid:pk>/edit/', views.rubrique_form, name='rubrique_edit'),
    path('rubriques/<uuid:pk>/toggle/', views.rubrique_toggle_actif, name='rubrique_toggle'),
    path('rubriques/<uuid:pk>/delete/', views.rubrique_delete, name='rubrique_delete'),

    # Tarifs de scolarité
    path('tarifs/', views.tarif_list, name='tarif_list'),
    path('tarifs/simulation/', views.tarif_simulation, name='tarif_simulation'),
    path('tarifs/simulation/resultat/', views.tarif_simulation_resultat, name='tarif_simulation_resultat'),
    path('tarifs/create/', views.tarif_form, name='tarif_create'),
    path('tarifs/<uuid:pk>/edit/', views.tarif_form, name='tarif_edit'),
    path('tarifs/<uuid:pk>/toggle/', views.tarif_toggle_actif, name='tarif_toggle'),
    path('tarifs/<uuid:pk>/delete/', views.tarif_delete, name='tarif_delete'),

    # Appréciations conduite
    path('appreciations/', views.appreciation_list, name='appreciation_list'),
    path('appreciations/create/', views.appreciation_form, name='appreciation_create'),
    path('appreciations/<uuid:pk>/edit/', views.appreciation_form, name='appreciation_edit'),
    path('appreciations/<uuid:pk>/delete/', views.appreciation_delete, name='appreciation_delete'),

    # Appréciations moyenne primaire
    path('appreciations-primaire/', views.appreciation_primaire_list, name='appreciation_primaire_list'),
    path('appreciations-primaire/create/', views.appreciation_primaire_form, name='appreciation_primaire_create'),
    path('appreciations-primaire/<uuid:pk>/edit/', views.appreciation_primaire_form, name='appreciation_primaire_edit'),
    path('appreciations-primaire/<uuid:pk>/delete/', views.appreciation_primaire_delete, name='appreciation_primaire_delete'),

    # Catégories de disciplines
    path('categories-disciplines/', views.categorie_discipline_list, name='categorie_discipline_list'),
    path('categories-disciplines/create/', views.categorie_discipline_form, name='categorie_discipline_create'),
    path('categories-disciplines/<uuid:pk>/edit/', views.categorie_discipline_form, name='categorie_discipline_edit'),
    path('categories-disciplines/<uuid:pk>/delete/', views.categorie_discipline_delete, name='categorie_discipline_delete'),

    # Disciplines
    path('disciplines/', views.discipline_list, name='discipline_list'),
    path('disciplines/create/', views.discipline_form, name='discipline_create'),
    path('disciplines/<uuid:pk>/edit/', views.discipline_form, name='discipline_edit'),
    path('disciplines/<uuid:pk>/delete/', views.discipline_delete, name='discipline_delete'),

    # Périodes d'évaluation
    path('periodes/', views.periode_list, name='periode_list'),
    path('periodes/create/', views.periode_form, name='periode_create'),
    path('periodes/<uuid:pk>/edit/', views.periode_form, name='periode_edit'),
    path('periodes/<uuid:pk>/delete/', views.periode_delete, name='periode_delete'),

    # Signataires
    path('signataires/', views.signataires_list, name='signataires_list'),
    path('signataires/cycle/<uuid:cycle_id>/', views.signataires_list_detail, name='signataires_list_detail'),
    path('signataires/edit/<uuid:cycle_id>/<uuid:document_type_id>/', views.signataire_edit, name='signataire_edit'),
    path('signataires/formulaire/', views.signataire_formulaire, name='signataire_formulaire'),
    path('signataires/configurer/', views.signataire_config, name='signataire_config'),

    # Types de documents
    path('types-documents/', views.type_document_list, name='type_document_list'),
    path('types-documents/create/', views.type_document_form, name='type_document_create'),
    path('types-documents/<uuid:pk>/edit/', views.type_document_form, name='type_document_edit'),
    path('types-documents/<uuid:pk>/delete/', views.type_document_delete, name='type_document_delete'),

    # Types de sanctions
    path('types-sanctions/', views.type_sanction_list, name='type_sanction_list'),
    path('types-sanctions/create/', views.type_sanction_form, name='type_sanction_create'),
    path('types-sanctions/<uuid:pk>/edit/', views.type_sanction_form, name='type_sanction_edit'),
    path('types-sanctions/<uuid:pk>/delete/', views.type_sanction_delete, name='type_sanction_delete'),

    # Titres fonctions
    path('titres-fonctions/', views.titre_fonction_list, name='titre_fonction_list'),
    path('titres-fonctions/create/', views.titre_fonction_form, name='titre_fonction_create'),
    path('titres-fonctions/<uuid:pk>/edit/', views.titre_fonction_form, name='titre_fonction_edit'),
    path('titres-fonctions/<uuid:pk>/delete/', views.titre_fonction_delete, name='titre_fonction_delete'),

    # Titres honorifiques
    path('titres-honorifiques/', views.titre_honorifique_list, name='titre_honorifique_list'),
    path('titres-honorifiques/create/', views.titre_honorifique_form, name='titre_honorifique_create'),
    path('titres-honorifiques/<uuid:pk>/edit/', views.titre_honorifique_form, name='titre_honorifique_edit'),
    path('titres-honorifiques/<uuid:pk>/delete/', views.titre_honorifique_delete, name='titre_honorifique_delete'),

    # Types d'évaluation
    path('types-evaluations/', views.type_evaluation_list, name='type_evaluation_list'),
    path('types-evaluations/create/', views.type_evaluation_form, name='type_evaluation_create'),
    path('types-evaluations/<uuid:pk>/edit/', views.type_evaluation_form, name='type_evaluation_edit'),
    path('types-evaluations/<uuid:pk>/delete/', views.type_evaluation_delete, name='type_evaluation_delete'),

    # Établissement
    path('etablissement/', views.etablissement_edit, name='etablissement'),
    path('identite-etablissement/', views.identite_etablissement, name='identite_etablissement'),

    # Calendrier scolaire
    path('calendrier/', views.calendrier, name='calendrier'),
    path('calendrier/evenements/create/', views.evenement_form, name='evenement_create'),
    path('calendrier/evenements/<uuid:pk>/edit/', views.evenement_form, name='evenement_edit'),
    path('calendrier/evenements/<uuid:pk>/delete/', views.evenement_delete, name='evenement_delete'),

    # Modèles de messages SMS
    path('modeles-messages/', views.modeles_messages_list, name='modeles_messages'),
    path('modeles-messages/<str:type_msg>/edit/', views.modele_message_form, name='modele_message_form'),
    path('modeles-messages/<str:type_msg>/reset/', views.modele_message_reset, name='modele_message_reset'),

    # Localisations de postes
    path('localisations/', views.localisation_list, name='localisation_list'),
    path('localisations/create/', views.localisation_form, name='localisation_create'),
    path('localisations/<uuid:pk>/edit/', views.localisation_form, name='localisation_edit'),
    path('localisations/<uuid:pk>/delete/', views.localisation_delete, name='localisation_delete'),

    # Co-signataires (à implémenter)
    # path('signataires/<uuid:signataire_pk>/cosignataires/', views.cosignataire_list, name='cosignataire_list'),
    # path('signataires/<uuid:signataire_pk>/cosignataires/create/', views.cosignataire_form, name='cosignataire_create'),
    # path('signataires/<uuid:signataire_pk>/cosignataires/<uuid:pk>/edit/', views.cosignataire_form, name='cosignataire_edit'),
    # path('cosignataires/<uuid:pk>/delete/', views.cosignataire_delete, name='cosignataire_delete'),

    # SMS automatiques
    path('sms-auto/', views.sms_auto_config, name='sms_auto_config'),
    path('sms-auto/<uuid:pk>/toggle/', views.sms_auto_toggle, name='sms_auto_toggle'),
    path('sms-auto/<uuid:pk>/save/', views.sms_auto_save, name='sms_auto_save'),
    path('sms-auto/<uuid:pk>/executer/', views.sms_auto_executer, name='sms_auto_executer'),
]
