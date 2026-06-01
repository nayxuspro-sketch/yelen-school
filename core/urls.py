from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('recherche/', views.recherche_globale, name='recherche'),
    path('audit/', views.audit_log_list, name='audit_log_list'),
    path('audit/pdf/', views.audit_log_pdf, name='audit_log_pdf'),
    path('audit/<int:pk>/', views.audit_log_detail, name='audit_log_detail'),
    path('portail/parent/', views.portail_parent, name='portail_parent'),
    path('portail/parent/bulletins/', views.portail_parent_bulletins, name='portail_parent_bulletins'),
    path('portail/parent/notifications/', views.portail_parent_notifications, name='portail_parent_notifications'),
    path('portail/eleve/', views.portail_eleve, name='portail_eleve'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/tout-lu/', views.notifications_marquer_tout_lu, name='notifications_tout_lu'),
    path('notifications/<int:pk>/lu/', views.notification_marquer_lu, name='notification_marquer_lu'),
    path('notifications/badge/', views.notifications_badge, name='notifications_badge'),
    path('sms/configuration/', views.sms_configuration, name='sms_configuration'),
    path('reunion-parents/', views.reunion_parents, name='reunion_parents'),
    path('risques/recalculer/', views.risque_recalculer, name='risque_recalculer'),

    # PWA — portail parent
    path('manifest.json', views.pwa_manifest, name='pwa_manifest'),
    path('pwa/icon/<int:size>/', views.pwa_icon, name='pwa_icon'),

    # PWA — application principale (staff)
    path('app-manifest.json', views.app_manifest, name='app_manifest'),
    path('offline/', views.offline_page, name='offline'),

    # Chatbot IA
    path('assistant/', views.chatbot, name='chatbot'),
]
