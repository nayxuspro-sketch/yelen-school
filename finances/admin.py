from django.contrib import admin
from .models import Paiement, TypeBourse, BourseEleve, CategorieDepense, BudgetAnnuel, Depense


@admin.register(TypeBourse)
class TypeBourseAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'source', 'type_reduction', 'valeur_reduction', 'rubrique', 'actif']
    list_filter = ['source', 'type_reduction', 'actif']
    search_fields = ['nom', 'code']


@admin.register(BourseEleve)
class BourseEleveAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'type_bourse', 'montant_accorde', 'date_attribution', 'actif']
    list_filter = ['type_bourse__source', 'actif']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom', 'reference_document']
    raw_id_fields = ['inscription', 'type_bourse']


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'rubrique', 'montant', 'date_paiement', 'mode_paiement', 'numero_recu']
    list_filter = ['mode_paiement', 'date_paiement']
    search_fields = ['inscription__eleve__nom', 'numero_recu']
    readonly_fields = tuple(field.name for field in Paiement._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CategorieDepense)
class CategorieDepenseAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'type_depense', 'etablissement', 'actif']
    list_filter = ['type_depense', 'actif', 'etablissement']
    search_fields = ['nom', 'code']


@admin.register(BudgetAnnuel)
class BudgetAnnuelAdmin(admin.ModelAdmin):
    list_display = ['annee_scolaire', 'categorie', 'montant_prevu']
    list_filter = ['annee_scolaire', 'categorie__type_depense']
    search_fields = ['categorie__nom']


@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ['numero_depense', 'libelle', 'categorie', 'montant', 'date_depense', 'statut', 'saisi_par']
    list_filter = ['statut', 'categorie__type_depense', 'mode_paiement', 'annee_scolaire']
    search_fields = ['libelle', 'numero_depense', 'beneficiaire', 'reference']
    readonly_fields = ['numero_depense', 'saisi_par', 'valide_par', 'date_validation']
