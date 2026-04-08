from django.contrib import admin
from .models import (
    AnneeScolaire, Cycle, RubriquePaiement, StatutEleve, TypeDocument,
    LocalisationPoste, IdentiteEtablissement, Classe,
    AppreciationMoyenneSecondaire, AppreciationMoyennePrimaire,
    TarifScolarite, SignataireDocument, CoSignataire, Poste, PeriodeEvaluation,
    Discipline, TitreFonction, TitreHonorifiquePersonnel,
)

admin.site.register(AnneeScolaire)
admin.site.register(Cycle)
admin.site.register(RubriquePaiement)
admin.site.register(StatutEleve)
admin.site.register(TypeDocument)
admin.site.register(LocalisationPoste)
admin.site.register(IdentiteEtablissement)
admin.site.register(Classe)
admin.site.register(AppreciationMoyenneSecondaire)
admin.site.register(AppreciationMoyennePrimaire)
admin.site.register(TarifScolarite)
class CoSignataireInline(admin.TabularInline):
    model = CoSignataire
    extra = 1
    fields = ('ordre', 'membre_personnel_id', 'fonction', 'titres_honorifiques', 'actif')
    ordering = ('ordre',)


@admin.register(SignataireDocument)
class SignataireDocumentAdmin(admin.ModelAdmin):
    list_display = ('cycle', 'type_document', 'annee_scolaire', 'fonction',
                    'get_membre_nom', 'nb_co_signataires', 'actif')
    list_filter = ('cycle', 'type_document', 'annee_scolaire', 'actif')
    inlines = [CoSignataireInline]

    def get_membre_nom(self, obj):
        m = obj.get_membre_personnel()
        return str(m) if m else '—'
    get_membre_nom.short_description = 'Signataire principal'

    def nb_co_signataires(self, obj):
        n = obj.co_signataires.filter(actif=True).count()
        return n if n else '—'
    nb_co_signataires.short_description = 'Co-signataires'
admin.site.register(Poste)
admin.site.register(PeriodeEvaluation)
admin.site.register(Discipline)
admin.site.register(TitreFonction)
admin.site.register(TitreHonorifiquePersonnel)