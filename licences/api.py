"""
licences/api.py
===============
API REST pour vérification licence — P2 IsLicenseActive + AuditLog centralisation.

Endpoints :
- GET /licences/api/status/ → statut licence établissement courant (auth requise)
- GET /api/licences/status/ → même chose via api/urls (DRF token)
- GET /licences/api/audit/ → audit logs centralisés (staff éditeur)
"""

from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from api.authentication import ExpiringTokenAuthentication
from api.permissions import EleveScopeAccess
from core.models import RoleChoices
from .models import Licence, LicenceAuditLog, StatutLicence


def _get_licence_for_user(user):
    etab = getattr(user, 'etablissement', None)
    if not etab:
        return None, None
    try:
        return etab, etab.licence
    except Licence.DoesNotExist:
        return etab, None


def _licence_to_dict(licence, etab=None):
    if not licence:
        return {
            'active': False,
            'statut': 'ABSENTE',
            'message': 'Aucune licence trouvée pour cet établissement',
        }
    return {
        'active': licence.est_active(),
        'cle_licence': licence.cle_licence,
        'type_licence': licence.type_licence,
        'type_display': licence.get_type_licence_display(),
        'statut': licence.statut,
        'statut_display': licence.get_statut_display(),
        'date_activation': licence.date_activation.isoformat() if licence.date_activation else None,
        'date_expiration': licence.date_expiration.isoformat() if licence.date_expiration else None,
        'jours_restants': licence.jours_restants(),
        'signature_valide': licence.verifier_signature(),
        'etablissement': {
            'id': str(etab.id) if etab else str(licence.etablissement_id),
            'nom': etab.nom if etab else '',
        } if etab or licence.etablissement_id else None,
        # P1 — heartbeat / bail
        'dernier_heartbeat': licence.dernier_heartbeat.isoformat() if licence.dernier_heartbeat else None,
        'bail_offline_expire_le': licence.bail_offline_expire_le.isoformat() if licence.bail_offline_expire_le else None,
        'bail_jours_restants': licence.get_bail_jours_restants(),
        'bail_expired': licence.is_bail_offline_expired(),
        'heartbeat_failures': licence.heartbeat_failures,
        'features': licence.get_features_disponibles() if licence.est_active() else [],
    }


# ── IsLicenseActive API (P2) ────────────────────────────────────────────────

class IsLicenseActiveView(APIView):
    """
    GET /api/licences/active/ — Vérifie si la licence de l'établissement courant est active.

    Auth : Token DRF (ExpiringTokenAuthentication) ou session.
    Réponse 200 : {active: bool, ...}
    404 si pas de licence.

    Utilisé par :
    - PWA / clients externes pour vérifier validité avant opérations offline
    - Monitoring / healthchecks
    - Filigrane PDF (pour afficher statut)
    """
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        etab, licence = _get_licence_for_user(request.user)
        if not licence:
            return Response({
                'active': False,
                'statut': 'ABSENTE',
                'message': 'Aucune licence trouvée',
                'etablissement': {'id': str(etab.id), 'nom': etab.nom} if etab else None,
            }, status=status.HTTP_404_NOT_FOUND)

        data = _licence_to_dict(licence, etab)
        # Si licence inactive, on retourne 200 avec active=False (pas 403) pour que le client puisse afficher message
        # Mais si révoquée/expirée/bail expiré, on peut retourner 403 selon query param ?strict
        strict = request.query_params.get('strict', 'false').lower() == 'true'
        if strict and not data['active']:
            return Response(data, status=status.HTTP_403_FORBIDDEN)
        return Response(data, status=status.HTTP_200_OK)


class LicenceStatusView(APIView):
    """
    GET /licences/api/status/ — Même chose mais via session (pour UI web).
    """
    # Pas de DRF auth, utilise session Django (login_required via permission)
    permission_classes = [IsAuthenticated]

    def get(self, request):
        etab, licence = _get_licence_for_user(request.user)
        if not licence:
            return Response({
                'active': False,
                'statut': 'ABSENTE',
                'message': 'Aucune licence trouvée',
            }, status=status.HTTP_404_NOT_FOUND)
        return Response(_licence_to_dict(licence, etab))


# ── LicenceAuditLog centralisation (P2) ─────────────────────────────────────

class LicenceAuditLogCentralView(APIView):
    """
    GET /licences/api/audit/ — Audit logs centralisés (staff éditeur uniquement).

    Query params :
    - licence_id (UUID) : filtrer par licence
    - action : filtrer par action (CREATION, ACTIVATION, etc.)
    - etablissement_id : filtrer par établissement
    - limit : nombre max (défaut 100, max 500)
    - offset : pagination

    P2 centralisation : tous les logs au même endroit, avec chaînage vérifiable.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Staff éditeur uniquement (P1 ENSURE_ADMIN→staff)
        if not request.user.is_staff:
            return Response(
                {'erreur': 'Accès réservé au staff éditeur'},
                status=status.HTTP_403_FORBIDDEN
            )

        qs = LicenceAuditLog.objects.select_related('licence', 'licence__etablissement', 'acteur_user').order_by('-created_at')

        licence_id = request.query_params.get('licence_id')
        if licence_id:
            qs = qs.filter(licence_id=licence_id)

        etab_id = request.query_params.get('etablissement_id')
        if etab_id:
            qs = qs.filter(licence__etablissement_id=etab_id)

        action = request.query_params.get('action')
        if action:
            qs = qs.filter(action=action.upper())

        # Pagination simple
        try:
            limit = min(int(request.query_params.get('limit', 100)), 500)
        except ValueError:
            limit = 100
        try:
            offset = int(request.query_params.get('offset', 0))
        except ValueError:
            offset = 0

        total = qs.count()
        logs = qs[offset:offset+limit]

        # Vérifier intégrité chaîne pour les logs retournés
        data = []
        for log in logs:
            data.append({
                'id': str(log.id),
                'licence': {
                    'id': str(log.licence.id),
                    'cle_licence': log.licence.cle_licence,
                    'type_licence': log.licence.type_licence,
                    'etablissement': {
                        'id': str(log.licence.etablissement_id),
                        'nom': getattr(log.licence.etablissement, 'nom', '') if hasattr(log.licence, 'etablissement') else '',
                    }
                },
                'action': log.action,
                'action_display': log.get_action_display(),
                'description': log.description,
                'acteur_user': {
                    'id': str(log.acteur_user.id),
                    'username': log.acteur_user.username,
                } if log.acteur_user else None,
                'acteur_systeme': log.acteur_systeme,
                'ip_address': str(log.ip_address) if log.ip_address else None,
                'created_at': log.created_at.isoformat() if log.created_at else None,
                'hash_precedent': log.hash_precedent,
                'hash_actuel': log.hash_actuel,
                'chaine_valide': log.verifier_chaine(),
            })

        # Statistiques centralisées
        from django.db.models import Count
        stats = {
            'total': total,
            'par_action': list(
                LicenceAuditLog.objects.values('action').annotate(count=Count('id')).order_by('-count')
            ),
            'par_licence': list(
                LicenceAuditLog.objects.values('licence__cle_licence').annotate(count=Count('id')).order_by('-count')[:10]
            ),
        }

        return Response({
            'logs': data,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total,
            },
            'stats': stats,
        })


class LicenceAuditLogVerifyView(APIView):
    """
    POST /licences/api/audit/verify/ — Vérifie l'intégrité de la chaîne d'audit pour une licence.

    Body : {licence_id: UUID}
    Retourne : {ok: bool, total: int, invalides: [], chaine_intacte: bool}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {'erreur': 'Accès réservé au staff éditeur'},
                status=status.HTTP_403_FORBIDDEN
            )

        licence_id = request.data.get('licence_id')
        if not licence_id:
            return Response(
                {'erreur': 'licence_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            licence = Licence.objects.get(pk=licence_id)
        except Licence.DoesNotExist:
            return Response(
                {'erreur': 'Licence introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

        logs = LicenceAuditLog.objects.filter(licence=licence).order_by('created_at')
        total = logs.count()
        invalides = []
        chaine_intacte = True
        precedent_hash = ''

        for log in logs:
            # Vérifier hash précédent
            if log.hash_precedent != precedent_hash:
                invalides.append({
                    'id': str(log.id),
                    'raison': f"hash_precedent attendu {precedent_hash[:8]}... mais trouvé {log.hash_precedent[:8]}...",
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                })
                chaine_intacte = False
            # Vérifier hash actuel
            if not log.verifier_chaine():
                invalides.append({
                    'id': str(log.id),
                    'raison': "hash_actuel invalide (contenu modifié)",
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                })
                chaine_intacte = False
            precedent_hash = log.hash_actuel

        return Response({
            'licence': {
                'id': str(licence.id),
                'cle_licence': licence.cle_licence,
            },
            'ok': chaine_intacte and len(invalides) == 0,
            'total': total,
            'invalides': invalides,
            'chaine_intacte': chaine_intacte,
        })
