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
    path('portail/eleve/', views.portail_eleve, name='portail_eleve'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/tout-lu/', views.notifications_marquer_tout_lu, name='notifications_tout_lu'),
    path('notifications/<int:pk>/lu/', views.notification_marquer_lu, name='notification_marquer_lu'),
    path('notifications/badge/', views.notifications_badge, name='notifications_badge'),
    path('sms/configuration/', views.sms_configuration, name='sms_configuration'),
    path('reunion-parents/', views.reunion_parents, name='reunion_parents'),
]
