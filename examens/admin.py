from django.contrib import admin
from .models import SessionExamen, CentreExamen, InscriptionExamen, SalleExamen


@admin.register(SessionExamen)
class SessionExamenAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'type_examen', 'annee_scolaire', 'date_debut', 'date_fin', 'statut']
    list_filter = ['type_examen', 'statut', 'annee_scolaire']
    search_fields = ['libelle']
    ordering = ['-date_debut']


@admin.register(CentreExamen)
class CentreExamenAdmin(admin.ModelAdmin):
    list_display = ['code_centre', 'nom', 'session', 'etablissement', 'capacite']
    list_filter = ['session']
    search_fields = ['code_centre', 'nom']


@admin.register(InscriptionExamen)
class InscriptionExamenAdmin(admin.ModelAdmin):
    list_display = ['inscription_eleve', 'session', 'centre', 'numero_table', 'statut', 'moyenne_examen']
    list_filter = ['session', 'statut', 'centre']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom', 'numero_table']
    ordering = ['session', 'numero_table']

    def inscription_eleve(self, obj):
        return obj.inscription.eleve.get_nom_complet()
    inscription_eleve.short_description = "Élève"


@admin.register(SalleExamen)
class SalleExamenAdmin(admin.ModelAdmin):
    list_display = ['nom', 'centre', 'capacite', 'surveillant_principal']
    list_filter = ['centre__session', 'centre']
    search_fields = ['nom', 'centre__nom']
