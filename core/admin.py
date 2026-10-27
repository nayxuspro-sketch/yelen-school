from django.contrib import admin

from .models import AuditLog, SmsSortant


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Consultation uniquement : aucune mutation depuis l'interface."""

    list_display = ('timestamp', 'action', 'user', 'etablissement', 'model_name', 'object_id', 'source', 'entry_hash')
    list_filter = ('action', 'source', 'app_label', 'model_name')
    search_fields = ('object_repr', 'object_id', 'user__email', 'entry_hash')
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SmsSortant)
class SmsSortantAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'numero', 'statut', 'tentatives', 'prochaine_tentative', 'date_envoi', 'derniere_erreur')
    list_filter = ('statut',)
    search_fields = ('numero', 'message', 'derniere_erreur')
    readonly_fields = ('created_at', 'date_envoi')
    ordering = ('-created_at',)
