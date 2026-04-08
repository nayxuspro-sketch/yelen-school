"""
URL configuration for yelen_school project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('parametres/', include('parametres.urls')),
    path('accounts/', include('accounts.urls')),
    path('licences/', include('licences.urls')),
    path('personnel/', include('personnel.urls')),
    path('inscriptions/', include('inscriptions.urls')),
    path('pedagogie/', include('pedagogie.urls')),
    path('finances/', include('finances.urls')),
    path('presences/', include('presences.urls')),
    path('documents/', include('documents.urls')),
    path('examens/', include('examens.urls')),
    path('vacations/', include('vacations.urls')),
    path('etablissements/', include('etablissements.urls')),
    path('viescolaire/', include('viescolaire.urls')),
    path('bulletins/', include('bulletins.urls')),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
