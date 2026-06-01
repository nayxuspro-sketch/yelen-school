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
        'resultats/inscription/<uuid:inscription_id>/trimestre/<uuid:trimestre_id>/bulletin/apercu/',
        views.bulletin_apercu, name='bulletin_apercu',
    ),
    path(
        'resultats/inscription/<uuid:inscription_id>/trimestre/<uuid:trimestre_id>/bulletin/pdf/',
        views.bulletin_pdf, name='bulletin_pdf',
    ),
    path(
        'resultats/inscription/<uuid:inscription_id>/trimestre/<uuid:trimestre_id>/bulletin/duplicata/',
        views.bulletin_duplicata_pdf, name='bulletin_duplicata_pdf',
    ),
    path(
        'resultats/classe/<uuid:class_id>/trimestre/<uuid:trimestre_id>/bulletins/batch/pdf/',
        views.bulletin_classe_batch_pdf, name='bulletin_classe_batch_pdf',
    ),
    path(
        'resultats/classe/<uuid:class_id>/trimestre/<uuid:trimestre_id>/bulletins/batch/zip/',
        views.bulletin_classe_batch_pdf, name='bulletin_classe_zip',
    ),
    # path(
    #     'resultats/trimestre/<uuid:trimestre_id>/bulletins/etab/zip/',
    #     views.bulletins_etab_zip, name='bulletins_etab_zip',
    # ),

    # Relevé de notes
    path('releve-notes/', views.releve_notes, name='releve_notes'),
    path('releve-notes/pdf/', views.releve_notes_pdf, name='releve_notes_pdf'),
    path('releve-notes/fiche-discipline/pdf/', views.fiche_discipline_pdf, name='fiche_discipline_pdf'),

    # Moyennes par discipline
    path('resultats/moyennes-disciplines/', views.moyennes_disciplines, name='moyennes_disciplines'),
    path('resultats/moyennes-disciplines/pdf/', views.moyennes_disciplines_pdf, name='moyennes_disciplines_pdf'),

    # Risque de décrochage
    path('risque-decrochage/', views.risque_decrochage, name='risque_decrochage'),
    path('risque-decrochage/pdf/', views.risque_decrochage_pdf, name='risque_decrochage_pdf'),

    # Bulletins annuels
    path(
        'resultats/inscription/<uuid:inscription_id>/bulletin/annuel/apercu/',
        views.bulletin_annuel_apercu, name='bulletin_annuel_apercu',
    ),
    path(
        'resultats/inscription/<uuid:inscription_id>/bulletin/annuel/pdf/',
        views.bulletin_annuel_pdf, name='bulletin_annuel_pdf',
    ),
    path(
        'resultats/classe/<uuid:class_id>/bulletin/annuel/batch/pdf/',
        views.bulletin_annuel_classe_batch_pdf, name='bulletin_annuel_classe_batch_pdf',
    ),

    # Palmarès annuel
    path(
        'resultats/classe/<uuid:class_id>/palmares/annuel/',
        views.palmares_annuel, name='palmares_annuel',
    ),
    path(
        'resultats/classe/<uuid:class_id>/palmares/annuel/pdf/',
        views.palmares_annuel_pdf, name='palmares_annuel_pdf',
    ),

    # Prédiction réussite examens
    path('predictions/', views.prediction_index, name='prediction_index'),
    path('predictions/classe/<uuid:class_id>/', views.prediction_classe, name='prediction_classe'),
    path('predictions/classe/<uuid:class_id>/calculer/', views.prediction_calculer, name='prediction_calculer'),
    path('predictions/classe/<uuid:class_id>/pdf/', views.prediction_classe_pdf, name='prediction_classe_pdf'),

    # Bulletins de compétences
    path('competences/', views.competences_index, name='competences_index'),
    path('competences/cycle/<uuid:cycle_id>/referentiel/', views.competences_referentiel, name='competences_referentiel'),
    path('competences/competence/<uuid:pk>/supprimer/', views.competence_supprimer, name='competence_supprimer'),
    path('competences/classe/<uuid:classe_id>/saisie/', views.competences_saisie, name='competences_saisie'),
    path('competences/sauvegarder/', views.competence_sauvegarder, name='competence_sauvegarder'),
    path('competences/bulletin/<uuid:inscription_id>/trimestre/<uuid:trimestre_id>/pdf/', views.competences_bulletin_pdf, name='competences_bulletin_pdf'),

    # Cahier de textes
    path('cahier-textes/', views.cahier_textes_index, name='cahier_textes_index'),
    path('cahier-textes/classe/<uuid:classe_id>/', views.cahier_textes_classe, name='cahier_textes_classe'),
    path('cahier-textes/ajouter/', views.cahier_textes_create, name='cahier_textes_create'),
    path('cahier-textes/<uuid:pk>/modifier/', views.cahier_textes_update, name='cahier_textes_update'),
    path('cahier-textes/<uuid:pk>/supprimer/', views.cahier_textes_delete, name='cahier_textes_delete'),
]
