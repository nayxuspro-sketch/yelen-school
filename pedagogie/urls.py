from django.urls import path
from . import views

app_name = 'pedagogie'

urlpatterns = [
    # Matières
    path('matieres/', views.matiere_list, name='matiere_list'),
    path('matieres/nouvelle/', views.matiere_create, name='matiere_create'),
    path('matieres/<uuid:pk>/modifier/', views.matiere_update, name='matiere_update'),
    path(
        'matieres/<uuid:matiere_pk>/cycle/<uuid:cycle_pk>/config/',
        views.matiere_cycle_save, name='matiere_cycle_save',
    ),

    # Enseignements (Affectations)
    path('enseignements/', views.enseignement_list, name='enseignement_list'),
    path('enseignements/nouveau/', views.enseignement_create, name='enseignement_create'),
    path('enseignements/<uuid:pk>/modifier/', views.enseignement_update, name='enseignement_update'),

    # Évaluations & Notes
    path('evaluations/', views.evaluation_list, name='evaluation_list'),
    path('evaluations/nouvelle/', views.evaluation_create, name='evaluation_create'),
    path('evaluations/<uuid:pk>/modifier/', views.evaluation_update, name='evaluation_update'),
    path('evaluations/<uuid:pk>/saisie/', views.evaluation_saisie, name='evaluation_saisie'),

    # Saisie rapide par classe
    path('classes/', views.saisie_classe_select, name='saisie_classe_select'),
    path('classes/<uuid:class_id>/saisie/', views.saisie_rapide_classe, name='saisie_rapide_classe'),

    # Résultats & Moyennes
    path('resultats/', views.classe_result_list, name='classe_result_list'),
    path('resultats/bilan-periodes/', views.bilan_periodes, name='bilan_periodes'),
    path('resultats/bilan-periodes/pdf/', views.bilan_pdf, name='bilan_pdf'),
    path('resultats/bilan-periodes/analyse-ia/', views.generer_commentaires_bilan, name='generer_commentaires_bilan'),
    path('resultats/bilan-periodes/releve-pdf/', views.releve_moyenne_classe_pdf, name='releve_moyenne_classe_pdf'),
    path('resultats/classe/<uuid:class_id>/', views.resultat_classe, name='resultat_classe'),
    path('resultats/classe/<uuid:class_id>/calculer/', views.calculer_moyennes_classe, name='calculer_moyennes_classe'),

    # Exports PDF bulletins
    path(
        'resultats/inscription/<uuid:inscription_id>/trimestre/<uuid:trimestre_id>/bulletin/pdf/',
        views.bulletin_pdf, name='bulletin_pdf',
    ),
    path(
        'resultats/classe/<uuid:class_id>/trimestre/<uuid:trimestre_id>/bulletins/batch/pdf/',
        views.bulletin_classe_batch_pdf, name='bulletin_classe_batch_pdf',
    ),

    # Relevé de notes
    path('releve-notes/', views.releve_notes, name='releve_notes'),
    path('releve-notes/pdf/', views.releve_notes_pdf, name='releve_notes_pdf'),

    # Moyennes par discipline
    path('resultats/moyennes-disciplines/', views.moyennes_disciplines, name='moyennes_disciplines'),
    path('resultats/moyennes-disciplines/pdf/', views.moyennes_disciplines_pdf, name='moyennes_disciplines_pdf'),
]
