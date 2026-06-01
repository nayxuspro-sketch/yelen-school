from django.contrib import admin
from .models import ManuelScolaire, ExemplaireManuel, AttributionManuel


@admin.register(ManuelScolaire)
class ManuelScolaireAdmin(admin.ModelAdmin):
    list_display = ['titre', 'cycle', 'matiere', 'classe', 'prix_remplacement', 'actif']
    list_filter = ['cycle', 'actif', 'etablissement']
    search_fields = ['titre', 'auteur', 'isbn']


@admin.register(ExemplaireManuel)
class ExemplaireAdmin(admin.ModelAdmin):
    list_display = ['code_exemplaire', 'manuel', 'etat', 'actif']
    list_filter = ['etat', 'actif']
    search_fields = ['code_exemplaire', 'manuel__titre']
    readonly_fields = ['code_exemplaire']


@admin.register(AttributionManuel)
class AttributionAdmin(admin.ModelAdmin):
    list_display = ['exemplaire', 'inscription', 'date_attribution', 'date_retour', 'facture_genere']
    list_filter = ['facture_genere']
    search_fields = ['exemplaire__code_exemplaire', 'inscription__eleve__nom']
    raw_id_fields = ['exemplaire', 'inscription']
