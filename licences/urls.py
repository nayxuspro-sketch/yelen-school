from django.urls import path
from . import views
from . import api as licence_api

app_name = 'licences'

urlpatterns = [
    path('', views.gestion_licences, name='gestion'),
    path('nouvelle/', views.licence_create, name='licence_create'),
    path('<uuid:pk>/modifier/', views.licence_edit, name='licence_edit'),
    path('<uuid:pk>/activer/', views.licence_activer, name='licence_activer'),
    path('<uuid:pk>/renouveler/', views.licence_renouveler, name='licence_renouveler'),
    path('<uuid:pk>/revoquer/', views.licence_revoquer, name='licence_revoquer'),
    # Pages informatives (redirections middleware)
    path('activer/', views.activer, name='activer'),
    path('support/', views.support, name='support'),
    path('guide/', views.guide, name='guide'),
    path('renouveler/', views.renouveler, name='renouveler'),
    path('mon-abonnement/', views.statut_licence, name='statut'),
    path('outils/', views.outils_licence, name='outils'),
    # P2 — API centralisation + IsLicenseActive
    path('api/status/', licence_api.LicenceStatusView.as_view(), name='api_status'),
    path('api/audit/', licence_api.LicenceAuditLogCentralView.as_view(), name='api_audit'),
    path('api/audit/verify/', licence_api.LicenceAuditLogVerifyView.as_view(), name='api_audit_verify'),
]
