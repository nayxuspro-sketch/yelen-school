from django.contrib import admin
from .models import ContratVacation, HeureVacation, BulletinVacation


@admin.register(ContratVacation)
class ContratVacationAdmin(admin.ModelAdmin):
    list_display = ['personnel', 'annee_scolaire', 'enseignement', 'taux_horaire', 'heures_hebdo_prevues', 'actif']
    list_filter = ['annee_scolaire', 'actif']
    search_fields = ['personnel__nom', 'personnel__prenom', 'personnel__matricule']
    ordering = ['-annee_scolaire', 'personnel__nom']


@admin.register(HeureVacation)
class HeureVacationAdmin(admin.ModelAdmin):
    list_display = ['contrat', 'mois', 'annee', 'heures_effectuees', 'heures_nettes', 'montant_du', 'est_valide']
    list_filter = ['annee', 'mois', 'est_valide', 'contrat__annee_scolaire']
    search_fields = ['contrat__personnel__nom', 'contrat__personnel__prenom']
    ordering = ['-annee', '-mois']

    def heures_nettes(self, obj):
        return obj.heures_nettes
    heures_nettes.short_description = "Heures nettes"

    def montant_du(self, obj):
        return f"{obj.montant_du:,.0f} FCFA"
    montant_du.short_description = "Montant dû"


@admin.register(BulletinVacation)
class BulletinVacationAdmin(admin.ModelAdmin):
    list_display = ['personnel', 'mois', 'annee', 'total_heures', 'montant_total', 'statut', 'date_paiement']
    list_filter = ['statut', 'annee', 'mois', 'annee_scolaire']
    search_fields = ['personnel__nom', 'personnel__prenom']
    ordering = ['-annee', '-mois']
    actions = ['marquer_paye']

    def marquer_paye(self, request, queryset):
        from datetime import date
        queryset.update(statut=BulletinVacation.StatutChoices.PAYE, date_paiement=date.today())
        self.message_user(request, f"{queryset.count()} bulletin(s) marqué(s) comme payé(s).")
    marquer_paye.short_description = "Marquer comme payé"
