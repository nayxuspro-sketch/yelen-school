from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('',                       views.message_list,   name='message_list'),
    path('nouveau/',               views.message_create, name='message_create'),
    path('<uuid:pk>/',             views.message_detail, name='message_detail'),
    path('repondre/<uuid:token>/', views.repondre,       name='repondre'),
    path('webhook/sms/',           views.webhook_incoming_sms, name='webhook_incoming_sms'),
]
