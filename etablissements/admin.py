from django.contrib import admin
from .models import Etablissement, GroupeEtablissements


@admin.register(GroupeEtablissements)
class GroupeEtablissementsAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'nb_etablissements']
    search_fields = ['nom', 'code']


@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'ville', 'groupe']
    list_filter = ['groupe']
    search_fields = ['nom', 'code', 'ville']
