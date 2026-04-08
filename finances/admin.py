from django.contrib import admin
from .models import Paiement, TypeBourse, BourseEleve


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
