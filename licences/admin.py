"""
Module Licences - Admin
========================
YELEN SCHOOL v3.4 - Interface d'administration Django pour les licences

Interface complète pour :
- Générer des clés de licence
- Activer/Révoquer/Renouveler des licences
- Consulter l'audit trail
- Gérer les alertes d'expiration
- Actions bulk sur plusieurs licences

Auteur: YELEN SCHOOL Team
Date: Mars 2026
"""

from datetime import timedelta
from typing import List

from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.db.models import Q, Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Licence,
    LicenceActivation,
    LicenceAuditLog,
    LicenceAlert,
    TypeLicence,
    StatutLicence,
    FEATURE_FLAGS,
    LIMITES_LICENCES,
)


# ═══════════════════════════════════════════════════════════════════
# FILTRES PERSONNALISÉS
# ═══════════════════════════════════════════════════════════════════

class StatutLicenceFilter(SimpleListFilter):
    """Filtre par statut de licence avec compteurs."""
    
    title = _('Statut')
    parameter_name = 'statut_custom'
    
    def lookups(self, request, model_admin):
        return [
            ('actives', _('✅ Actives')),
            ('expirees', _('⏰ Expirées')),
            ('revoquees', _('🚫 Révoquées')),
            ('en_attente', _('⏳ En attente')),
            ('expirant_30j', _('⚠️ Expirant sous 30j')),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'actives':
            return queryset.filter(
                statut=StatutLicence.ACTIVE,
                date_expiration__gte=timezone.now().date()
            )
        elif self.value() == 'expirees':
            return queryset.filter(statut=StatutLicence.EXPIREE)
        elif self.value() == 'revoquees':
            return queryset.filter(statut=StatutLicence.REVOQUEE)
        elif self.value() == 'en_attente':
            return queryset.filter(statut=StatutLicence.EN_ATTENTE)
        elif self.value() == 'expirant_30j':
            date_limite = timezone.now().date() + timedelta(days=30)
            return queryset.filter(
                statut=StatutLicence.ACTIVE,
                date_expiration__lte=date_limite,
                date_expiration__gt=timezone.now().date()
            )
        return queryset


class TypeLicenceFilter(SimpleListFilter):
    """Filtre par type de licence."""
    
    title = _('Type de licence')
    parameter_name = 'type_licence'
    
    def lookups(self, request, model_admin):
        return TypeLicence.choices
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(type_licence=self.value())
        return queryset


# ═══════════════════════════════════════════════════════════════════
# ADMIN : LICENCE (Principal)
# ═══════════════════════════════════════════════════════════════════

@admin.register(Licence)
class LicenceAdmin(admin.ModelAdmin):
    """
    Interface d'administration principale pour les licences.
    
    Fonctionnalités :
    - Génération automatique de clés
    - Actions bulk (renouveler, révoquer, activer)
    - Dashboard statistiques
    - Export CSV
    """
    
    # ─── Configuration de la liste ───
    list_display = [
        'cle_licence_display',
        'etablissement_display',
        'type_licence_badge',
        'statut_badge',
        'date_expiration_display',
        'jours_restants_display',
        'signature_valide_display',
        'actions_rapides',
    ]
    
    list_filter = [
        StatutLicenceFilter,
        TypeLicenceFilter,
        'date_activation',
        'date_expiration',
    ]
    
    search_fields = [
        'cle_licence',
        'etablissement__nom',
        'notes_interne',
    ]
    
    readonly_fields = [
        'cle_licence',
        'signature_hmac',
        'date_activation',
        'created_at',
        'updated_at',
        'derniere_verification',
        'features_disponibles_display',
        'limites_display',
        'historique_audit_display',
    ]
    
    fieldsets = (
        (_('🔑 Informations de licence'), {
            'fields': (
                'etablissement',
                'cle_licence',
                'type_licence',
                'statut',
            )
        }),
        (_('📅 Dates'), {
            'fields': (
                'date_activation',
                'date_expiration',
                'derniere_verification',
            )
        }),
        (_('🔒 Sécurité'), {
            'fields': (
                'signature_hmac',
            ),
            'classes': ('collapse',),
        }),
        (_('📋 Fonctionnalités disponibles'), {
            'fields': (
                'features_disponibles_display',
                'limites_display',
            ),
            'classes': ('collapse',),
        }),
        (_('📝 Notes internes'), {
            'fields': (
                'notes_interne',
            ),
            'classes': ('collapse',),
        }),
        (_('📊 Historique'), {
            'fields': (
                'created_at',
                'updated_at',
                'historique_audit_display',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # ─── Actions bulk ───
    actions = [
        'activer_licences',
        'renouveler_1_an',
        'renouveler_6_mois',
        'revoquer_licences',
        'verifier_signatures',
        'export_csv',
    ]
    
    # ─── Configuration générale ───
    list_per_page = 50
    date_hierarchy = 'date_expiration'
    ordering = ['-date_activation']
    
    # ─── Permissions ───
    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression des licences avec historique."""
        if obj and obj.audit_logs.exists():
            return False
        return super().has_delete_permission(request, obj)
    
    # ═══════════════════════════════════════════════════════════════
    # AFFICHAGE PERSONNALISÉ DES COLONNES
    # ═══════════════════════════════════════════════════════════════
    
    @admin.display(description=_('Clé de licence'))
    def cle_licence_display(self, obj):
        """Affiche la clé avec style."""
        return format_html(
            '<code style="background:#1a2a42;padding:4px 8px;border-radius:4px;'
            'color:#00a86b;font-weight:bold;">{}</code>',
            obj.cle_licence
        )
    
    @admin.display(description=_('Établissement'))
    def etablissement_display(self, obj):
        """Affiche l'établissement avec lien."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:etablissements_etablissement_change', args=[obj.etablissement.pk]),
            obj.etablissement.nom
        )
    
    @admin.display(description=_('Type'))
    def type_licence_badge(self, obj):
        """Badge coloré pour le type de licence."""
        colors = {
            'STARTER': '#f5a623',
            'STANDARD': '#00a86b',
            'PREMIUM': '#dc3545',
            'RESEAU': '#17a2b8',
        }
        
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;'
            'border-radius:12px;font-size:11px;font-weight:bold;">{}</span>',
            colors.get(obj.type_licence, '#666'),
            obj.get_type_licence_display()
        )
    
    @admin.display(description=_('Statut'))
    def statut_badge(self, obj):
        """Badge coloré pour le statut."""
        colors = {
            'ACTIVE': '#00a86b',
            'EXPIREE': '#dc3545',
            'REVOQUEE': '#666',
            'EN_ATTENTE': '#f5a623',
        }
        
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;'
            'border-radius:12px;font-size:11px;font-weight:bold;">{}</span>',
            colors.get(obj.statut, '#666'),
            obj.get_statut_display()
        )
    
    @admin.display(description=_('Expiration'), ordering='date_expiration')
    def date_expiration_display(self, obj):
        """Affiche la date d'expiration avec couleur."""
        jours = obj.jours_restants()
        
        if jours < 0:
            color = '#dc3545'  # Rouge
        elif jours <= 7:
            color = '#dc3545'  # Rouge
        elif jours <= 30:
            color = '#f5a623'  # Orange
        else:
            color = '#00a86b'  # Vert
        
        return format_html(
            '<span style="color:{};">{}</span>',
            color,
            obj.date_expiration.strftime('%d/%m/%Y')
        )
    
    @admin.display(description=_('Jours restants'))
    def jours_restants_display(self, obj):
        """Affiche les jours restants avec icône."""
        jours = obj.jours_restants()
        
        if jours < 0:
            icon = '🔴'
            text = f'Expirée ({abs(jours)}j)'
        elif jours == 0:
            icon = '🚨'
            text = 'Expire aujourd\'hui'
        elif jours <= 7:
            icon = '🚨'
            text = f'{jours}j'
        elif jours <= 30:
            icon = '⚠️'
            text = f'{jours}j'
        else:
            icon = '✅'
            text = f'{jours}j'
        
        return format_html('{} {}', icon, text)
    
    @admin.display(description=_('Signature'), boolean=True)
    def signature_valide_display(self, obj):
        """Vérifie la signature HMAC."""
        return obj.verifier_signature()
    
    @admin.display(description=_('Actions'))
    def actions_rapides(self, obj):
        """Boutons d'actions rapides."""
        buttons = []
        
        if obj.statut == StatutLicence.EN_ATTENTE:
            buttons.append(
                f'<a href="{reverse("admin:licences_licence_activer", args=[obj.pk])}" '
                f'style="background:#00a86b;color:white;padding:4px 8px;'
                f'border-radius:4px;text-decoration:none;font-size:11px;">✅ Activer</a>'
            )
        
        if obj.est_active():
            buttons.append(
                f'<a href="{reverse("admin:licences_licence_renouveler", args=[obj.pk])}" '
                f'style="background:#17a2b8;color:white;padding:4px 8px;'
                f'border-radius:4px;text-decoration:none;font-size:11px;">🔄 Renouveler</a>'
            )
        
        if obj.statut != StatutLicence.REVOQUEE:
            buttons.append(
                f'<a href="{reverse("admin:licences_licence_revoquer", args=[obj.pk])}" '
                f'style="background:#dc3545;color:white;padding:4px 8px;'
                f'border-radius:4px;text-decoration:none;font-size:11px;">🚫 Révoquer</a>'
            )
        
        return format_html(' '.join(buttons))
    
    # ═══════════════════════════════════════════════════════════════
    # CHAMPS READONLY PERSONNALISÉS
    # ═══════════════════════════════════════════════════════════════
    
    @admin.display(description=_('Features disponibles'))
    def features_disponibles_display(self, obj):
        """Liste les features disponibles."""
        if not obj.est_active():
            return format_html('<p style="color:#dc3545;">Licence inactive</p>')
        
        features = obj.get_features_disponibles()
        
        html = '<ul style="margin:0;padding-left:20px;">'
        for feature in features:
            html += f'<li>✅ {feature}</li>'
        html += '</ul>'
        
        return format_html(html)
    
    @admin.display(description=_('Limites'))
    def limites_display(self, obj):
        """Affiche les limites de la licence."""
        limites = LIMITES_LICENCES[obj.type_licence]
        
        return format_html(
            '<ul style="margin:0;padding-left:20px;">'
            '<li>👥 Élèves max : <strong>{}</strong></li>'
            '<li>👨‍🏫 Enseignants max : <strong>{}</strong></li>'
            '<li>🏫 Classes max : <strong>{}</strong></li>'
            '<li>💰 Prix annuel : <strong>{} FCFA</strong></li>'
            '</ul>',
            limites['max_eleves'],
            limites['max_enseignants'],
            limites['max_classes'],
            f"{limites['prix_annuel_fcfa']:,}".replace(',', ' ')
        )
    
    @admin.display(description=_('Historique audit'))
    def historique_audit_display(self, obj):
        """Affiche les 5 dernières entrées d'audit."""
        logs = obj.audit_logs.all()[:5]
        
        if not logs:
            return format_html('<p>Aucune entrée</p>')
        
        html = '<table style="width:100%;border-collapse:collapse;">'
        html += '<tr style="background:#1a2a42;color:white;">'
        html += '<th style="padding:4px;text-align:left;">Date</th>'
        html += '<th style="padding:4px;text-align:left;">Action</th>'
        html += '<th style="padding:4px;text-align:left;">Description</th>'
        html += '</tr>'
        
        for log in logs:
            html += '<tr style="border-bottom:1px solid #ddd;">'
            html += f'<td style="padding:4px;">{log.created_at.strftime("%d/%m/%Y %H:%M")}</td>'
            html += f'<td style="padding:4px;">{log.get_action_display()}</td>'
            html += f'<td style="padding:4px;">{log.description[:50]}...</td>'
            html += '</tr>'
        
        html += '</table>'
        
        return format_html(html)
    
    # ═══════════════════════════════════════════════════════════════
    # ACTIONS BULK
    # ═══════════════════════════════════════════════════════════════
    
    @admin.action(description=_('✅ Activer les licences sélectionnées'))
    def activer_licences(self, request, queryset):
        """Active les licences en attente."""
        count = 0
        for licence in queryset.filter(statut=StatutLicence.EN_ATTENTE):
            licence.activer()
            count += 1
        
        self.message_user(
            request,
            _(f'{count} licence(s) activée(s) avec succès.'),
            messages.SUCCESS
        )
    
    @admin.action(description=_('🔄 Renouveler pour 1 an'))
    def renouveler_1_an(self, request, queryset):
        """Renouvelle les licences pour 1 an."""
        count = 0
        for licence in queryset:
            licence.renouveler(duree_jours=365)
            count += 1
        
        self.message_user(
            request,
            _(f'{count} licence(s) renouvelée(s) pour 1 an.'),
            messages.SUCCESS
        )
    
    @admin.action(description=_('🔄 Renouveler pour 6 mois'))
    def renouveler_6_mois(self, request, queryset):
        """Renouvelle les licences pour 6 mois."""
        count = 0
        for licence in queryset:
            licence.renouveler(duree_jours=180)
            count += 1
        
        self.message_user(
            request,
            _(f'{count} licence(s) renouvelée(s) pour 6 mois.'),
            messages.SUCCESS
        )
    
    @admin.action(description=_('🚫 Révoquer les licences sélectionnées'))
    def revoquer_licences(self, request, queryset):
        """Révoque les licences sélectionnées."""
        count = 0
        for licence in queryset.exclude(statut=StatutLicence.REVOQUEE):
            licence.revoquer(raison="Révocation bulk admin")
            count += 1
        
        self.message_user(
            request,
            _(f'{count} licence(s) révoquée(s).'),
            messages.WARNING
        )
    
    @admin.action(description=_('🔍 Vérifier les signatures HMAC'))
    def verifier_signatures(self, request, queryset):
        """Vérifie l'intégrité des signatures."""
        invalides = []
        
        for licence in queryset:
            if not licence.verifier_signature():
                invalides.append(licence.cle_licence)
        
        if invalides:
            self.message_user(
                request,
                _(f'⚠️ {len(invalides)} signature(s) invalide(s) : {", ".join(invalides)}'),
                messages.ERROR
            )
        else:
            self.message_user(
                request,
                _('✅ Toutes les signatures sont valides.'),
                messages.SUCCESS
            )
    
    @admin.action(description=_('📥 Exporter en CSV'))
    def export_csv(self, request, queryset):
        """Exporte les licences en CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="licences_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Clé', 'Établissement', 'Type', 'Statut',
            'Date activation', 'Date expiration', 'Jours restants'
        ])
        
        for licence in queryset:
            writer.writerow([
                licence.cle_licence,
                licence.etablissement.nom,
                licence.get_type_licence_display(),
                licence.get_statut_display(),
                licence.date_activation,
                licence.date_expiration,
                licence.jours_restants(),
            ])
        
        return response
    
    # ═══════════════════════════════════════════════════════════════
    # URLS PERSONNALISÉES
    # ═══════════════════════════════════════════════════════════════
    
    def get_urls(self):
        """Ajoute des URLs personnalisées."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/activer/',
                self.admin_site.admin_view(self.activer_view),
                name='licences_licence_activer',
            ),
            path(
                '<path:object_id>/renouveler/',
                self.admin_site.admin_view(self.renouveler_view),
                name='licences_licence_renouveler',
            ),
            path(
                '<path:object_id>/revoquer/',
                self.admin_site.admin_view(self.revoquer_view),
                name='licences_licence_revoquer',
            ),
        ]
        return custom_urls + urls
    
    def activer_view(self, request, object_id):
        """Vue pour activer une licence."""
        licence = self.get_object(request, object_id)
        
        if licence.statut == StatutLicence.EN_ATTENTE:
            licence.activer()
            self.message_user(
                request,
                _(f'Licence {licence.cle_licence} activée avec succès.'),
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                _(f'La licence est déjà au statut : {licence.get_statut_display()}'),
                messages.WARNING
            )
        
        return redirect('admin:licences_licence_changelist')
    
    def renouveler_view(self, request, object_id):
        """Vue pour renouveler une licence."""
        licence = self.get_object(request, object_id)
        licence.renouveler(duree_jours=365)
        
        self.message_user(
            request,
            _(f'Licence {licence.cle_licence} renouvelée jusqu\'au {licence.date_expiration}.'),
            messages.SUCCESS
        )
        
        return redirect('admin:licences_licence_changelist')
    
    def revoquer_view(self, request, object_id):
        """Vue pour révoquer une licence."""
        licence = self.get_object(request, object_id)
        licence.revoquer(raison="Révocation manuelle admin")
        
        self.message_user(
            request,
            _(f'Licence {licence.cle_licence} révoquée.'),
            messages.WARNING
        )
        
        return redirect('admin:licences_licence_changelist')


# ═══════════════════════════════════════════════════════════════════
# ADMIN : ACTIVATION DE LICENCE
# ═══════════════════════════════════════════════════════════════════

@admin.register(LicenceActivation)
class LicenceActivationAdmin(admin.ModelAdmin):
    """Administration des activations de licence."""
    
    list_display = [
        'licence_display',
        'hostname',
        'mac_address',
        'ip_address',
        'mode_activation',
        'est_active_badge',
        'created_at',
    ]
    
    list_filter = [
        'mode_activation',
        'est_active',
        'created_at',
    ]
    
    search_fields = [
        'licence__cle_licence',
        'hostname',
        'mac_address',
        'ip_address',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'empreinte_serveur_display',
    ]
    
    fieldsets = (
        (_('Licence'), {
            'fields': ('licence',)
        }),
        (_('Serveur'), {
            'fields': (
                'hostname',
                'mac_address',
                'ip_address',
                'empreinte_serveur_display',
            )
        }),
        (_('Activation'), {
            'fields': (
                'mode_activation',
                'est_active',
                'date_revocation',
            )
        }),
        (_('Métadonnées'), {
            'fields': (
                'user_agent',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    @admin.display(description=_('Licence'))
    def licence_display(self, obj):
        return format_html(
            '<code>{}</code>',
            obj.licence.cle_licence
        )
    
    @admin.display(description=_('Active'), boolean=True)
    def est_active_badge(self, obj):
        return obj.est_active
    
    @admin.display(description=_('Empreinte serveur'))
    def empreinte_serveur_display(self, obj):
        return format_html(
            '<code style="font-size:10px;">{}</code>',
            obj.get_empreinte_serveur()
        )


# ═══════════════════════════════════════════════════════════════════
# ADMIN : AUDIT LOG (Lecture seule)
# ═══════════════════════════════════════════════════════════════════

@admin.register(LicenceAuditLog)
class LicenceAuditLogAdmin(admin.ModelAdmin):
    """
    Journal d'audit en lecture seule.
    
    Aucune modification ni suppression possible.
    """
    
    list_display = [
        'created_at',
        'licence_display',
        'action_display',
        'description_short',
        'acteur_display',
        'chaine_valide_badge',
    ]
    
    list_filter = [
        'action',
        'acteur_systeme',
        'created_at',
    ]
    
    search_fields = [
        'licence__cle_licence',
        'description',
        'acteur_user__email',
    ]
    
    readonly_fields = [
        'licence',
        'action',
        'description',
        'acteur_user',
        'acteur_systeme',
        'ip_address',
        'user_agent',
        'hash_precedent',
        'hash_actuel',
        'created_at',
        'verifier_chaine_display',
    ]
    
    fieldsets = (
        (_('Action'), {
            'fields': (
                'licence',
                'action',
                'description',
                'created_at',
            )
        }),
        (_('Acteur'), {
            'fields': (
                'acteur_user',
                'acteur_systeme',
                'ip_address',
                'user_agent',
            )
        }),
        (_('Chaînage cryptographique'), {
            'fields': (
                'hash_precedent',
                'hash_actuel',
                'verifier_chaine_display',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        """Empêcher l'ajout manuel."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Empêcher toute modification."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Empêcher toute suppression."""
        return False
    
    @admin.display(description=_('Licence'))
    def licence_display(self, obj):
        return format_html('<code>{}</code>', obj.licence.cle_licence)
    
    @admin.display(description=_('Action'))
    def action_display(self, obj):
        return obj.get_action_display()
    
    @admin.display(description=_('Description'))
    def description_short(self, obj):
        return obj.description[:80] + '...' if len(obj.description) > 80 else obj.description
    
    @admin.display(description=_('Acteur'))
    def acteur_display(self, obj):
        if obj.acteur_systeme:
            return '🤖 Système'
        elif obj.acteur_user:
            return obj.acteur_user.email
        return '—'
    
    @admin.display(description=_('Chaîne valide'), boolean=True)
    def chaine_valide_badge(self, obj):
        return obj.verifier_chaine()
    
    @admin.display(description=_('Vérification chaîne'))
    def verifier_chaine_display(self, obj):
        valide = obj.verifier_chaine()
        
        if valide:
            return format_html(
                '<span style="color:#00a86b;font-weight:bold;">✅ Chaîne intacte</span>'
            )
        else:
            return format_html(
                '<span style="color:#dc3545;font-weight:bold;">⚠️ ALTÉRATION DÉTECTÉE</span>'
            )


# ═══════════════════════════════════════════════════════════════════
# ADMIN : ALERTES D'EXPIRATION
# ═══════════════════════════════════════════════════════════════════

@admin.register(LicenceAlert)
class LicenceAlertAdmin(admin.ModelAdmin):
    """Administration des alertes d'expiration."""
    
    list_display = [
        'date_alerte',
        'licence_display',
        'type_alerte_display',
        'envoyee_badge',
        'date_envoi',
        'destinataires_count',
    ]
    
    list_filter = [
        'type_alerte',
        'envoyee',
        'date_alerte',
    ]
    
    search_fields = [
        'licence__cle_licence',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (_('Alerte'), {
            'fields': (
                'licence',
                'type_alerte',
                'date_alerte',
            )
        }),
        (_('Envoi'), {
            'fields': (
                'envoyee',
                'date_envoi',
                'destinataires',
            )
        }),
        (_('Métadonnées'), {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    @admin.display(description=_('Licence'))
    def licence_display(self, obj):
        return format_html('<code>{}</code>', obj.licence.cle_licence)
    
    @admin.display(description=_('Type'))
    def type_alerte_display(self, obj):
        return obj.get_type_alerte_display()
    
    @admin.display(description=_('Envoyée'), boolean=True)
    def envoyee_badge(self, obj):
        return obj.envoyee
    
    @admin.display(description=_('Destinataires'))
    def destinataires_count(self, obj):
        return len(obj.destinataires) if obj.destinataires else 0
