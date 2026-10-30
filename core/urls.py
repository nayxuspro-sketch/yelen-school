from django.urls import path
from . import aide, views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('recherche/', views.recherche_globale, name='recherche'),
    path('pilotage/', views.pilotage, name='pilotage'),
    path('pilotage/enseignants/', views.pilotage_enseignants, name='pilotage_enseignants'),
    path('audit/', views.audit_log_list, name='audit_log_list'),
    path('audit/pdf/', views.audit_log_pdf, name='audit_log_pdf'),
    path('audit/<int:pk>/', views.audit_log_detail, name='audit_log_detail'),
    path('portail/parent/', views.portail_parent, name='portail_parent'),
    path('portail/parent/bulletins/', views.portail_parent_bulletins, name='portail_parent_bulletins'),
    path('portail/parent/notifications/', views.portail_parent_notifications, name='portail_parent_notifications'),
    path('portail/parent/vie-scolaire/', views.portail_parent_vie_scolaire, name='portail_parent_vie_scolaire'),
    path('portail/parent/vie-scolaire/justifier/', views.portail_parent_justifier, name='portail_parent_justifier'),
    path('portail/eleve/', views.portail_eleve, name='portail_eleve'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/tout-lu/', views.notifications_marquer_tout_lu, name='notifications_tout_lu'),
    path('notifications/<int:pk>/lu/', views.notification_marquer_lu, name='notification_marquer_lu'),
    path('notifications/badge/', views.notifications_badge, name='notifications_badge'),
    path('sms/configuration/', views.sms_configuration, name='sms_configuration'),
    path('exploitation/', views.exploitation, name='exploitation'),
    path('exploitation/sauvegardes/<str:nom>', views.sauvegarde_telecharger, name='sauvegarde_telecharger'),
    path('reunion-parents/', views.reunion_parents, name='reunion_parents'),
    path('risques/recalculer/', views.risque_recalculer, name='risque_recalculer'),

    # PWA — portail parent
    path('manifest.json', views.pwa_manifest, name='pwa_manifest'),
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
    path('aide/screenshots/<str:nom>', aide.aide_capture, name='aide_capture'),
]
