"""
Module Pédagogie - Admin
========================
YELEN SCHOOL v3.4 - Configuration Django Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Matiere,
    Enseignement,
    TypeEvaluation,
    Trimestre,
    Evaluation,
    Note,
    Resultat,
)


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'categorie', 'coefficient', 'est_obligatoire']
    list_filter = ['categorie', 'est_obligatoire']
    search_fields = ['code', 'nom']


@admin.register(Enseignement)
class EnseignementAdmin(admin.ModelAdmin):
    list_display = ['matiere', 'classe', 'annee_scolaire', 'personnel', 'est_actif']
    list_filter = ['annee_scolaire', 'est_actif']
    search_fields = ['matiere__nom', 'classe__nom']


@admin.register(TypeEvaluation)
class TypeEvaluationAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'coefficient', 'ponderation', 'ordre']
    ordering = ['ordre', 'code']


@admin.register(Trimestre)
class TrimestreAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_periode', 'annee_scolaire', 'numero', 'date_debut', 'date_fin']
    list_filter = ['type_periode', 'annee_scolaire']
    ordering = ['annee_scolaire', 'numero']


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_evaluation', 'trimestre', 'date_planifiee', 'bareme', 'statut']
    list_filter = ['statut', 'type_evaluation', 'trimestre']
    search_fields = ['titre', 'type_evaluation__nom']
    ordering = ['-date_planifiee']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['inscription_eleve', 'evaluation', 'valeur', 'statut']
    list_filter = ['statut', 'evaluation__trimestre']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom']
    ordering = ['-evaluation__date_planifiee']
    
    def inscription_eleve(self, obj):
        return f"{obj.inscription.eleve.prenom} {obj.inscription.eleve.nom}"
    inscription_eleve.short_description = _('Élève')


@admin.register(Resultat)
class ResultatAdmin(admin.ModelAdmin):
    list_display = ['inscription_eleve', 'trimestre', 'moyenne_sur_20', 'rang']
    list_filter = ['trimestre']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom']
    ordering = ['trimestre', 'rang']
    
    def inscription_eleve(self, obj):
        return f"{obj.inscription.eleve.prenom} {obj.inscription.eleve.nom}"
    inscription_eleve.short_description = _('Élève')
