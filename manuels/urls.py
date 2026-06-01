from django.urls import path
from . import views

app_name = 'manuels'

urlpatterns = [
    # Catalogue
    path('', views.catalogue, name='catalogue'),
    path('nouveau/', views.manuel_form, name='manuel_create'),
    path('<uuid:pk>/', views.manuel_detail, name='manuel_detail'),
    path('<uuid:pk>/modifier/', views.manuel_form, name='manuel_edit'),
    path('<uuid:pk>/supprimer/', views.manuel_delete, name='manuel_delete'),

    # Exemplaires
    path('<uuid:manuel_pk>/exemplaires/nouveau/', views.exemplaire_form, name='exemplaire_create'),
    path('<uuid:manuel_pk>/exemplaires/<uuid:pk>/modifier/', views.exemplaire_form, name='exemplaire_edit'),
    path('<uuid:manuel_pk>/exemplaires/<uuid:pk>/supprimer/', views.exemplaire_delete, name='exemplaire_delete'),

    # Attributions
    path('attributions/', views.attributions_list, name='attributions_list'),
    path('attributions/nouvelle/', views.attribution_form, name='attribution_create'),
    path('attributions/depuis/<uuid:exemplaire_pk>/', views.attribution_form, name='attribution_depuis_exemplaire'),
    path('attributions/<uuid:pk>/retour/', views.attribution_retour, name='attribution_retour'),

    # Manuels non rendus
    path('non-rendus/', views.non_rendus, name='non_rendus'),
    path('non-rendus/<uuid:pk>/facturer/', views.facturer_non_rendu, name='facturer_non_rendu'),

    # Export PDF
    path('inventaire/classe/<uuid:classe_pk>/pdf/', views.inventaire_classe_pdf, name='inventaire_classe_pdf'),
    path('attributions/pdf/', views.attributions_annee_pdf, name='attributions_annee_pdf'),
    path('non-rendus/pdf/', views.non_rendus_pdf, name='non_rendus_pdf'),

    # HTMX partials
    path('htmx/eleves/', views.inscription_par_classe, name='htmx_eleves'),
    path('htmx/exemplaires/', views.exemplaires_par_manuel, name='htmx_exemplaires'),
]
