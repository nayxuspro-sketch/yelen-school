from django.urls import path
from . import views

app_name = 'personnel'

urlpatterns = [
    path('', views.personnel_list, name='personnel_list'),
    path('nouveau/', views.personnel_create, name='create'),
    path('<uuid:pk>/', views.personnel_detail, name='detail'),
    path('<uuid:pk>/modifier/', views.personnel_update, name='update'),
    path('<uuid:pk>/inscription/', views.inscription_create, name='inscription_create'),
    path('<uuid:pk>/toggle-active/', views.toggle_active, name='toggle_active'),
    path('<uuid:pk>/badge/', views.badge_personnel, name='badge'),
    path('<uuid:pk>/contrat/', views.contrat_travail, name='contrat'),
]
