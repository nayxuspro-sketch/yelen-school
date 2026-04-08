from django.contrib import admin
from .models import Appel, Presence, Justification


@admin.register(Appel)
class AppelAdmin(admin.ModelAdmin):
    list_display = ['classe', 'date', 'matiere', 'effectue_par', 'nb_presents', 'nb_absents', 'est_clos']
    list_filter = ['date', 'classe', 'annee_scolaire', 'est_clos']
    search_fields = ['classe__nom', 'effectue_par__nom', 'effectue_par__prenom']
    date_hierarchy = 'date'
    ordering = ['-date']


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'appel', 'statut', 'minutes_retard']
    list_filter = ['statut', 'appel__date', 'appel__classe']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom']
    ordering = ['-appel__date']


@admin.register(Justification)
class JustificationAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'date_debut', 'date_fin', 'statut', 'traitee_par']
    list_filter = ['statut', 'date_debut']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom']
    date_hierarchy = 'date_debut'
