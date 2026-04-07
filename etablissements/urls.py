from django.urls import path
from . import views

app_name = 'etablissements'

urlpatterns = [
    path('', views.etablissement_detail, name='detail'),
]
