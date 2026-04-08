"""
Module Inscriptions - Admin
===========================
YELEN SCHOOL v3.4 - Configuration Django Admin

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Eleve, Inscription


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    """
    Configuration admin pour le modèle Eleve.
    """
    list_display = [
        'matricule',
        'nom',
        'prenom',
        'genre',
        'date_naissance',
        'age_formatted',
        'telephone_parent',
        'is_active',
    ]
    
    list_filter = [
        'genre',
        'nationalite',
        'pays_residence',
        'is_active',
    ]
    
    search_fields = [
        'nom',
        'prenom',
        'matricule',
        'telephone_parent',
        'telephone_urgence',
    ]
    
    readonly_fields = [
        'matricule',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (_('Identification'), {
            'fields': ('matricule',)
        }),
        (_('Informations personnelles'), {
            'fields': (
                'nom', 'prenom', 'genre',
                'date_naissance', 'lieu_naissance',
                'nationalite', 'pays_residence',
            )
        }),
        (_('Localisation'), {
            'fields': (
                'province', 'commune', 'village',
            ),
            'classes': ('collapse',)
        }),
        (_('Contact'), {
            'fields': (
                'telephone_urgence', 'email',
            )
        }),
        (_('Photo'), {
            'fields': ('photo',),
            'classes': ('collapse',)
        }),
        (_('Famille - Père'), {
            'fields': (
                'nom_pere', 'profession_pere',
            ),
            'classes': ('collapse',)
        }),
        (_('Famille - Mère'), {
            'fields': (
                'nom_mere', 'profession_mere',
            ),
            'classes': ('collapse',)
        }),
        (_('Tuteur'), {
            'fields': (
                'tuteur_nom', 'tuteur_telephone', 'tuteur_adresse',
            ),
            'classes': ('collapse',)
        }),
        (_('Historique'), {
            'fields': (
                'etablissement_origine', 'last_classe', 'last_annee',
            ),
            'classes': ('collapse',)
        }),
        (_('Statut'), {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['nom', 'prenom']
    
    def age_formatted(self, obj):
        """Affiche l'âge avec coloration."""
        age = obj.age
        if age is None:
            return '-'
        # Colorer en fonction de l'âge
        if age < 18:
            color = 'green'
        elif age > 25:
            color = 'red'
        else:
            color = 'orange'
        return format_html('<span style="color: {};">{} ans</span>', color, age)
    age_formatted.short_description = _('Âge')


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    """
    Configuration admin pour le modèle Inscription.
    """
    list_display = [
        'eleve',
        'classe',
        'annee_scolaire',
        'statut',
        'est_redoublant',
        'date_inscription',
    ]
    
    list_filter = [
        'statut',
        'est_redoublant',
        'annee_scolaire',
    ]
    
    search_fields = [
        'eleve__nom',
        'eleve__prenom',
        'eleve__matricule',
        'numero_recu',
    ]
    
    readonly_fields = [
        'numero_recu',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (_('Élève et année'), {
            'fields': (
                'eleve', 'annee_scolaire', 'classe',
            )
        }),
        (_('Statut'), {
            'fields': (
                'statut', 'est_redoublant',
            )
        }),
(_('Observations'), {
            'fields': ('observations',),
            'classes': ('collapse',)
        }),
        (_('Statut système'), {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-annee_scolaire', 'eleve__nom', 'eleve__prenom']
    
    date_hierarchy = 'date_inscription'
