from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('',                       views.message_list,   name='message_list'),
    path('nouveau/',               views.message_create, name='message_create'),
    path('sms-direct/',            views.sms_direct_simulateur, name='sms_direct'),
    path('sms-direct/envoyer/',    views.sms_direct_envoyer, name='sms_direct_envoyer'),
    path('messages-recus/',        views.messages_recus, name='messages_recus'),
    path('messages-recus/compteur/', views.messages_recus_compteur, name='messages_recus_compteur'),
    path('messages-recus/tout-lu/', views.messages_recus_tout_lu, name='messages_recus_tout_lu'),
    path('messages-recus/supprimer/', views.messages_recus_supprimer_selection, name='messages_recus_supprimer_selection'),
    path('messages-recus/<uuid:pk>/supprimer/', views.messages_recus_supprimer, name='messages_recus_supprimer'),
    path('messages-recus/<uuid:pk>/marquer/', views.messages_recus_marquer, name='messages_recus_marquer'),
    path('messages-recus/<uuid:pk>/repondre/', views.messages_recus_repondre, name='messages_recus_repondre'),
    path('commandes-sms/',         views.commandes_sms, name='commandes_sms'),
    path('commandes-sms/nouvelle/', views.commande_sms_nouvelle, name='commande_sms_nouvelle'),
    path('commandes-sms/<uuid:pk>/modifier/', views.commande_sms_modifier, name='commande_sms_modifier'),
    path('commandes-sms/<uuid:pk>/basculer/', views.commande_sms_basculer, name='commande_sms_basculer'),
    path('commandes-sms/<uuid:pk>/supprimer/', views.commande_sms_supprimer, name='commande_sms_supprimer'),
    path('campagnes/',             views.campagne_list, name='campagne_list'),
    path('campagnes/nouvelle/',    views.campagne_nouvelle, name='campagne_nouvelle'),
    path('campagnes/<uuid:pk>/',   views.campagne_detail, name='campagne_detail'),
    path('campagnes/<uuid:pk>/renvoyer/', views.campagne_renvoyer, name='campagne_renvoyer'),
    path('<uuid:pk>/',             views.message_detail, name='message_detail'),
    path('<uuid:pk>/renvoyer-sms/', views.message_renvoyer_sms, name='message_renvoyer_sms'),
    path('repondre/<uuid:token>/', views.repondre,       name='repondre'),
    path('justificatif/<uuid:pk>/', views.justificatif_download, name='justificatif_download'),
    path('webhook/sms/',           views.webhook_incoming_sms, name='webhook_incoming_sms'),
]
