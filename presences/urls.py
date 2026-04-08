from django.urls import path
from . import views

app_name = 'presences'

urlpatterns = [
    path('', views.appel_list, name='appel_list'),
    path('imprimer/', views.appel_print, name='appel_print'),
    path('csv/', views.appel_csv, name='appel_csv'),
    path('classes/', views.classe_select, name='classe_select'),
    path('appel/classe/<uuid:classe_id>/', views.appel_create, name='appel_create'),
    path('appel/<uuid:appel_id>/saisie/', views.appel_saisie, name='appel_saisie'),
    path('eleve/<uuid:inscription_id>/bilan/', views.bilan_eleve, name='bilan_eleve'),
    path('eleve/<uuid:inscription_id>/justification/', views.justification_create, name='justification_create'),
    path('justifications/', views.justification_list, name='justification_list'),
    path('justifications/<uuid:justification_id>/traiter/', views.justification_process, name='justification_process'),
    path('bilan/', views.bilan_annuel, name='bilan_annuel'),
    path('bilan/csv/', views.bilan_csv, name='bilan_csv'),

    # QR-code / Pointage
    path('eleve/<uuid:inscription_id>/qr.png', views.qr_eleve_image, name='qr_eleve_image'),
    path('classe/<uuid:classe_id>/cartes-qr/', views.cartes_qr_classe, name='cartes_qr_classe'),
    path('appel/<uuid:appel_id>/scanner/', views.qr_scanner, name='qr_scanner'),
    path('appel/<uuid:appel_id>/qr/pointer/', views.api_qr_pointer, name='api_qr_pointer'),
]
