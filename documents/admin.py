from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'numero_document', 'type_document', 'annee_scolaire',
        'inscription', 'classe', 'genere_par', 'created_at'
    ]
    list_filter = ['type_document', 'annee_scolaire']
    search_fields = [
        'numero_document',
        'inscription__eleve__nom',
        'inscription__eleve__prenom',
        'classe__nom',
    ]
    ordering = ['-created_at']
    readonly_fields = ['numero_document', 'created_at', 'updated_at']
