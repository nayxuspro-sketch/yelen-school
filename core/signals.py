"""
Signaux pour l'Audit Trail automatique.
"""
import json
from django.db.models import signals
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from yelen_school.audit_middleware import get_request, get_user_from_request, get_client_ip


def log_audit(sender, instance, action=None, **kwargs):
    """Enregistre une action dans l'audit trail."""
    from core.models import AuditLog
    
    # Déterminer l'action basée sur le type de signal
    signal = kwargs.get('signal')
    if signal == 'pre_delete':
        action = 'DELETE'
    elif action is None:
        action = 'UPDATE'
    
    # Ne pas journaliser le modèle AuditLog lui-même
    if sender == AuditLog:
        return
    
    # Ne pas journaliser si instance n'a pas encore d'ID (CREATE)
    if not instance.pk and action != 'CREATE':
        return
    
    try:
        # Récupérer l'utilisateur depuis l'instance ou la requête
        user = None
        if hasattr(instance, '_current_user'):
            user = instance._current_user
        if not user:
            user = get_user_from_request()
        
        # Récupérer l'IP cliente
        request = get_request()
        ip_address = get_client_ip(request) if request else None
        
        # Obtenir les valeurs avant modification pour UPDATE/DELETE
        changes = {}
        old_instance = None
        
        if action in ('UPDATE', 'DELETE'):
            try:
                old_instance = sender.objects.get(pk=instance.pk)
                if action == 'UPDATE':
                    # Comparer les champs modifiés
                    for field in instance._meta.fields:
                        if field.name in ('created_at', 'updated_at', 'created_by', 'updated_by', '_current_user'):
                            continue
                        old_val = getattr(old_instance, field.name, None)
                        new_val = getattr(instance, field.name, None)
                        if old_val != new_val:
                            changes[field.name] = {
                                'old': str(old_val) if old_val is not None else None,
                                'new': str(new_val) if new_val is not None else None,
                            }
            except sender.DoesNotExist:
                pass
        
        # Créer l'entrée d'audit
        AuditLog.objects.create(
            user=user,
            action=action,
            app_label=instance._meta.app_label,
            model_name=instance._meta.model_name,
            object_id=instance.pk,
            object_repr=str(instance)[:200],
            changes=changes,
            ip_address=ip_address,
        )
    except Exception as e:
        # Ne pas bloquer les opérations si l'audit échoue
        import logging
        logging.error(f"Audit log failed: {e}")


def _log_post_save(sender, instance, created, **kwargs):
    """Wrapper post_save qui distingue CREATE et UPDATE."""
    action = 'CREATE' if created else 'UPDATE'
    log_audit(sender=sender, instance=instance, action=action, **kwargs)


def _log_pre_delete(sender, instance, **kwargs):
    """Wrapper pre_delete pour DELETE."""
    log_audit(sender=sender, instance=instance, action='DELETE', **kwargs)


def setup_audit_signals():
    """Configure les signaux pour tous les modèles."""
    from django.apps import apps

    for model in apps.get_models():
        # Vérifier si le modèle hérite de BaseModel
        if hasattr(model, '_meta') and model._meta.proxy:
            continue
        try:
            if hasattr(model, 'created_at'):
                post_save.connect(_log_post_save, sender=model, dispatch_uid=f'audit_save_{model._meta.label}')
                pre_delete.connect(_log_pre_delete, sender=model, dispatch_uid=f'audit_delete_{model._meta.label}')
        except Exception:
            pass


# Configuration automatique à l'import
setup_audit_signals()