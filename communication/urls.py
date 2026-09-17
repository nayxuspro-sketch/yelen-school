from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('',                       views.message_list,   name='message_list'),
    path('nouveau/',               views.message_create, name='message_create'),
    path('sms-direct/',            views.sms_direct_simulateur, name='sms_direct'),
    path('sms-direct/envoyer/',    views.sms_direct_envoyer, name='sms_direct_envoyer'),
    path('<uuid:pk>/',             views.message_detail, name='message_detail'),
    path('repondre/<uuid:token>/', views.repondre,       name='repondre'),
    path('justificatif/<uuid:pk>/', views.justificatif_download, name='justificatif_download'),
    path('webhook/sms/',           views.webhook_incoming_sms, name='webhook_incoming_sms'),
]
