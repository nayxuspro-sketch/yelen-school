from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('',                       views.message_list,   name='message_list'),
    path('nouveau/',               views.message_create, name='message_create'),
    path('sms-direct/',            views.sms_direct_simulateur, name='sms_direct'),
    path('sms-direct/envoyer/',    views.sms_direct_envoyer, name='sms_direct_envoyer'),
    path('campagnes/',             views.campagne_list, name='campagne_list'),
    path('campagnes/nouvelle/',    views.campagne_nouvelle, name='campagne_nouvelle'),
    path('campagnes/<uuid:pk>/',   views.campagne_detail, name='campagne_detail'),
    path('campagnes/<uuid:pk>/renvoyer/', views.campagne_renvoyer, name='campagne_renvoyer'),
    path('<uuid:pk>/',             views.message_detail, name='message_detail'),
    path('repondre/<uuid:token>/', views.repondre,       name='repondre'),
    path('justificatif/<uuid:pk>/', views.justificatif_download, name='justificatif_download'),
    path('webhook/sms/',           views.webhook_incoming_sms, name='webhook_incoming_sms'),
]
