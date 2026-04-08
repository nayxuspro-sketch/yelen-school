from django.contrib import admin

from .models import Bulletin


@admin.register(Bulletin)
class BulletinAdmin(admin.ModelAdmin):
    list_display = [
        'get_eleve', 'get_classe', 'trimestre', 'est_publie',
        'absences_justifiees', 'absences_non_justifiees', 'retards',
        'date_publication',
    ]
    list_filter = ['est_publie', 'trimestre__annee_scolaire', 'trimestre', 'inscription__classe']
    search_fields = [
        'inscription__eleve__nom', 'inscription__eleve__prenom',
        'inscription__eleve__matricule',
    ]
    readonly_fields = ['date_publication', 'publie_par', 'created_at', 'updated_at']
    list_per_page = 50

    @admin.display(description="Élève", ordering='inscription__eleve__nom')
    def get_eleve(self, obj):
        return str(obj.inscription.eleve)

    @admin.display(description="Classe", ordering='inscription__classe__nom')
    def get_classe(self, obj):
        return obj.inscription.classe.nom
