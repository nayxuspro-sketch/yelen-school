from django.contrib import admin
from .models import MessageParent, ReponseParent, IncomingSMSLog

@admin.register(MessageParent)
class MessageParentAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'type', 'objet', 'statut', 'telephone_utilise', 'sms_envoye', 'created_at')
    list_filter = ('type', 'statut', 'sms_envoye', 'annee_scolaire')
    search_fields = ('eleve__nom', 'eleve__prenom', 'objet', 'telephone_utilise')
    ordering = ('-created_at',)

@admin.register(ReponseParent)
class ReponseParentAdmin(admin.ModelAdmin):
    list_display = ('message', 'creneau_choisi', 'accuse_reception', 'date_reglement_prevue', 'created_at')
    list_filter = ('accuse_reception', 'date_reglement_prevue')
    search_fields = ('message__eleve__nom', 'message__eleve__prenom', 'commentaire')
    ordering = ('-created_at',)

@admin.register(IncomingSMSLog)
class IncomingSMSLogAdmin(admin.ModelAdmin):
    list_display = ('sender_number', 'command_type', 'eleve', 'is_authorized', 'processed_successfully', 'created_at')
    list_filter = ('command_type', 'is_authorized', 'processed_successfully')
    search_fields = ('sender_number', 'message_text', 'response_text', 'eleve__nom', 'eleve__prenom', 'error_message')
    ordering = ('-created_at',)
