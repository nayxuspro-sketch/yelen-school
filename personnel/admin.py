"""
Module Personnel - Admin
========================
Configuration Django Admin pour le personnel scolaire.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import MembrePersonnel, InscriptionPersonnel, SalairePersonnel, CongePersonnel


@admin.register(MembrePersonnel)
class MembrePersonnelAdmin(admin.ModelAdmin):
    """Configuration admin pour les membres du personnel."""
    
    list_display = (
        'matricule',
        'nom',
        'prenom',
        'genre',
        'fonction',
        'etablissement',
        'est_directeur',
        'is_active'
    )
    
    list_filter = (
        'genre',
        'est_directeur',
        'est_contractuel',
        'est_vacataire',
        'etablissement',
        'is_active'
    )
    
    search_fields = (
        'nom',
        'prenom',
        'matricule',
        'telephone',
        'email'
    )
    
    readonly_fields = (
        'id',
        'matricule',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        (_('Identification'), {
            'fields': (
                'id',
                'matricule',
                'etablissement'
            )
        }),
        (_('Informations personnelles'), {
            'fields': (
                'nom',
                'prenom',
                'genre',
                'date_naissance',
                'lieu_naissance',
                'nationalite',
                'photo'
            )
        }),
        (_('Contact'), {
            'fields': (
                'telephone',
                'email',
                'adresse'
            )
        }),
        (_('Pièce d\'identité'), {
            'fields': (
                'numero_cni',
            )
        }),
        (_('Informations professionnelles'), {
            'fields': (
                'fonction',
                'poste_principal_code',
                'cycles',
                'date_embauche',
                'est_contractuel',
                'est_vacataire'
            )
        }),
        (_('Direction'), {
            'fields': (
                'est_directeur',
                'est_censeur'
            )
        }),
        (_('Famille'), {
            'fields': (
                'situation_matrimoniale',
                'nombre_enfants'
            )
        }),
        (_('Statut'), {
            'fields': (
                'is_active',
                'created_at',
                'updated_at'
            )
        })
    )
    
    filter_horizontal = ('cycles',)


@admin.register(InscriptionPersonnel)
class InscriptionPersonnelAdmin(admin.ModelAdmin):
    """Configuration admin pour les inscriptions annuelles du personnel."""
    
    list_display = (
        'personnel',
        'cycle',
        'annee_scolaire',
        'poste',
        'est_actif',
        'date_inscription'
    )
    
    list_filter = (
        'annee_scolaire',
        'cycle',
        'poste',
        'est_actif'
    )
    
    search_fields = (
        'personnel__nom',
        'personnel__prenom',
        'personnel__matricule'
    )
    
    readonly_fields = (
        'id',
        'date_inscription',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        (_('Identification'), {
            'fields': (
                'id',
                'personnel',
                'annee_scolaire'
            )
        }),
        (_('Affectation'), {
            'fields': (
                'poste',
                'cycle',
                'est_actif'
            )
        }),
        (_('Dates'), {
            'fields': (
                'date_inscription',
                'date_debut',
                'date_fin'
            )
        }),
        (_('Vacations'), {
            'fields': (
                'heures_hebdomadaires',
            )
        }),
        (_('Observations'), {
            'fields': (
                'observations',
            )
        }),
        (_('Statut'), {
            'fields': (
                'is_active',
                'created_at',
                'updated_at'
            )
        })
    )


@admin.register(SalairePersonnel)
class SalairePersonnelAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'mois', 'annee', 'salaire_base', 'statut', 'date_paiement')
    list_filter = ('statut', 'mois', 'annee')
    search_fields = ('personnel__nom', 'personnel__prenom', 'personnel__matricule')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(CongePersonnel)
class CongePersonnelAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'type_conge', 'date_debut', 'date_fin', 'nombre_jours', 'statut')
    list_filter = ('type_conge', 'statut')
    search_fields = ('personnel__nom', 'personnel__prenom', 'personnel__matricule')
    readonly_fields = ('id', 'nombre_jours', 'created_at', 'updated_at')
