from django.urls import path
from . import aide, views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('recherche/', views.recherche_globale, name='recherche'),
    path('demarrage/', views.demarrage, name='demarrage'),
    path('pilotage/', views.pilotage, name='pilotage'),
    path('pilotage/enseignants/', views.pilotage_enseignants, name='pilotage_enseignants'),
    path('audit/', views.audit_log_list, name='audit_log_list'),
    path('audit/pdf/', views.audit_log_pdf, name='audit_log_pdf'),
    path('audit/<int:pk>/', views.audit_log_detail, name='audit_log_detail'),
    path('portail/parent/', views.portail_parent, name='portail_parent'),
    path('portail/parent/bulletins/', views.portail_parent_bulletins, name='portail_parent_bulletins'),
    path('portail/parent/notifications/', views.portail_parent_notifications, name='portail_parent_notifications'),
    path('portail/parent/vie-scolaire/', views.portail_parent_vie_scolaire, name='portail_parent_vie_scolaire'),
    path('portail/parent/cahier/', views.portail_parent_cahier, name='portail_parent_cahier'),
    path('portail/parent/vie-scolaire/justifier/', views.portail_parent_justifier, name='portail_parent_justifier'),
    path('portail/parent/bulletins/<uuid:pk>/', views.portail_bulletin, name='portail_parent_bulletin'),
    path('portail/parent/documents/<uuid:pk>/', views.portail_document, name='portail_parent_document'),
    # Portail élève : mêmes vues, préfixe /portail/eleve/ (rôle ELEVE — yelen_school/role_middleware.py)
    path('portail/eleve/', views.portail_parent, name='portail_eleve'),
    path('portail/eleve/bulletins/', views.portail_parent_bulletins, name='portail_eleve_bulletins'),
    path('portail/eleve/bulletins/<uuid:pk>/', views.portail_bulletin, name='portail_eleve_bulletin'),
    path('portail/eleve/notifications/', views.portail_parent_notifications, name='portail_eleve_notifications'),
    path('portail/eleve/vie-scolaire/', views.portail_parent_vie_scolaire, name='portail_eleve_vie_scolaire'),
    path('portail/eleve/cahier/', views.portail_parent_cahier, name='portail_eleve_cahier'),
    path('portail/eleve/documents/<uuid:pk>/', views.portail_document, name='portail_eleve_document'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/tout-lu/', views.notifications_marquer_tout_lu, name='notifications_tout_lu'),
    path('notifications/<int:pk>/lu/', views.notification_marquer_lu, name='notification_marquer_lu'),
    path('notifications/badge/', views.notifications_badge, name='notifications_badge'),
    path('notifications/push/abonner/', views.push_abonner, name='push_abonner'),
    path('notifications/push/desabonner/', views.push_desabonner, name='push_desabonner'),
    path('notifications/push/test/', views.push_test, name='push_test'),
    path('sms/configuration/', views.sms_configuration, name='sms_configuration'),
    path('exploitation/', views.exploitation, name='exploitation'),
    path('exploitation/sauvegardes/<str:nom>', views.sauvegarde_telecharger, name='sauvegarde_telecharger'),
    path('reunion-parents/', views.reunion_parents, name='reunion_parents'),
    path('risques/recalculer/', views.risque_recalculer, name='risque_recalculer'),

    # PWA — portail parent
    path('favicon.ico', views.favicon, name='favicon'),
    path('manifest.json', views.pwa_manifest, name='pwa_manifest'),
    path('manifest-eleve.json', views.pwa_manifest, {'role': 'ELEVE'}, name='pwa_manifest_eleve'),
    path('pwa/icon/<int:size>/', views.pwa_icon, name='pwa_icon'),
    path('certificat-autorite/', views.certificat_autorite, name='certificat_autorite'),

    # PWA — application principale (staff)
    path('app-manifest.json', views.app_manifest, name='app_manifest'),
    path('offline/', views.offline_page, name='offline'),
    path('hors-ligne/saisies/', views.saisies_hors_ligne, name='saisies_hors_ligne'),
    path('hors-ligne/contexte/', views.saisies_contexte, name='saisies_contexte'),

    # Chatbot IA
    path('assistant/', views.chatbot, name='chatbot'),

    # Healthcheck pour load balancer / monitoring
    path('health/', views.health_check, name='health_check'),
    path('aide/', aide.aide, name='aide'),
    path('aide/demarrage/', aide.aide, {'rapide': True}, name='aide_demarrage'),
    path('aide/screenshots/<str:nom>', aide.aide_capture, name='aide_capture'),
]
