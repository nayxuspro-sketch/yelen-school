from django.contrib import admin
from .models import (
    SeanceCours, ConseilClasse, DecisionConseil,
    SanctionDisciplinaire, ActiviteParascolaire, ParticipationActivite
)


@admin.register(SeanceCours)
class SeanceCoursAdmin(admin.ModelAdmin):
    list_display = ['enseignement', 'get_jour_display', 'heure_debut', 'heure_fin', 'salle']
    list_filter = ['jour', 'enseignement__classe']


class DecisionConseilInline(admin.TabularInline):
    model = DecisionConseil
    extra = 0
    fields = ['inscription', 'decision', 'appreciation', 'felicitations', 'encouragements']


@admin.register(ConseilClasse)
class ConseilClasseAdmin(admin.ModelAdmin):
    list_display = ['classe', 'trimestre', 'date_conseil', 'tenu', 'president']
    list_filter = ['tenu', 'trimestre__annee_scolaire', 'classe']
    inlines = [DecisionConseilInline]


@admin.register(SanctionDisciplinaire)
class SanctionDisciplinaireAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'type_sanction', 'date_sanction', 'statut', 'prononcee_par']
    list_filter = ['type_sanction', 'statut', 'inscription__annee_scolaire']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom']


class ParticipationActiviteInline(admin.TabularInline):
    model = ParticipationActivite
    extra = 0


@admin.register(ActiviteParascolaire)
class ActiviteParascolaireAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_activite', 'annee_scolaire', 'responsable', 'nb_participants']
    list_filter = ['type_activite', 'annee_scolaire']
    inlines = [ParticipationActiviteInline]
