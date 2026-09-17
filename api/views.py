"""
api/views.py — Vues DRF pour l'API sécurisée YELEN SCHOOL
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from .authentication import ExpiringTokenAuthentication
from .permissions import EleveScopeAccess, role_utilisateur
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.db.models import Q

from inscriptions.models import Eleve, Inscription
from parametres.models import AnneeScolaire, PeriodeEvaluation
from pedagogie.models import MoyenneGenerale, Resultat
from finances.models import Paiement
from presences.models import Presence
from bulletins.models import Bulletin
from core.models import RoleChoices

from .serializers import (
    EleveSerializer, InscriptionSerializer, AnneeScolaireSerializer,
    PeriodeSerializer, MoyenneGeneraleSerializer, PaiementSerializer,
    PresenceSerializer, BulletinSerializer,
)


def _get_user_etablissement(user):
    """Récupère l'établissement de l'utilisateur ou None si Super Admin."""
    if role_utilisateur(user) == RoleChoices.SUPER_ADMIN:
        return None
    return getattr(user, 'etablissement', None)


def eleves_visibles(user):
    """QuerySet des élèves VISIBLES pour l'utilisateur (cloisonnement RBAC).

    - SUPER_ADMIN / DIRECTEUR_RESEAU : tous les établissements
    - PARENT / ELEVE                : uniquement eleves_lies (enfants / soi)
    - staff                          : leur établissement uniquement
    """
    role = role_utilisateur(user)
    if role in (RoleChoices.SUPER_ADMIN, RoleChoices.DIRECTEUR_RESEAU):
        return Eleve.objects.all().order_by('nom', 'prenom')
    if role in (RoleChoices.PARENT, RoleChoices.ELEVE):
        return Eleve.objects.filter(
            pk__in=user.eleves_lies.values('pk'),
        ).order_by('nom', 'prenom')
    etab = _get_user_etablissement(user)
    if etab is None:
        return Eleve.objects.none()
    return Eleve.objects.filter(
        inscriptions__classe__etablissement=etab,
    ).distinct().order_by('nom', 'prenom')


def get_eleve_scope(user, pk):
    """Élève si dans le périmètre RBAC de l'utilisateur, sinon None
    (les vues répondent 404 : aucune fuite d'existence)."""
    return eleves_visibles(user).filter(pk=pk).first()


# ── Throttling pour éviter les abus ─────────────────────────────────────────────

class LoginRateThrottle(UserRateThrottle):
    """Limite les tentatives de login à 5/minute pour éviter brute force."""
    scope = 'login'
    rate = '5/minute'


# ── Authentification ──────────────────────────────────────────────────────────

class ObtenirTokenView(APIView):
    """POST /api/auth/token/ — Obtenir un token à partir de username/password."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response(
                {'erreur': 'Champs username et password requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Ne pas révéler si l'email existe ou non
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {'erreur': 'Identifiants invalides.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Vérifier si le compte est verrouillé
        if hasattr(user, 'locked_until') and user.locked_until:
            from django.utils import timezone
            if user.locked_until > timezone.now():
                return Response(
                    {'erreur': 'Compte temporairement verrouillé. Réessayez plus tard.'},
                    status=status.HTTP_423_LOCKED,
                )
        
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'role': getattr(user, 'role', ''),
        })


class RevoquerTokenView(APIView):
    """DELETE /api/auth/token/ — Révoquer le token courant."""
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RenouvelerTokenView(APIView):
    """POST /api/auth/token/refresh/ — Renouveler (faire tourner) le token courant.

    À appeler par le client (PWA) avant l'expiration du token
    (TOKEN_EXPIRY_HOURS, défaut 24 h) pour ne pas être déconnecté :

        POST /api/auth/token/refresh/
        Authorization: Token <token courant>

    Réponse 200 : {'token': '<nouveau token>', 'user_id', 'username', 'role'}.
    Le token précédent est IMMÉDIATEMENT invalidé (rotation) : un token
    intercepté ne reste utile que jusqu'à sa prochaine rotation.

    Si le token est déjà expiré (supprimé par ExpiringTokenAuthentication),
    la réponse est 401 : le client doit repasser par l'authentification
    complète /api/auth/token/ avec username/password.
    """
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        # Rotation : supprimer tous les tokens de l'utilisateur,
        # puis en émettre un seul nouveau.
        Token.objects.filter(user=request.user).delete()
        nouveau = Token.objects.create(user=request.user)
        return Response({
            'token': nouveau.key,
            'user_id': request.user.pk,
            'username': request.user.username,
            'role': getattr(request.user, 'role', ''),
        })


# ── Années scolaires ──────────────────────────────────────────────────────────

class AnneesListView(APIView):
    """GET /api/annees/ — Liste des années scolaires."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request):
        etab = _get_user_etablissement(request.user)
        if etab:
            annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
        else:
            annees = AnneeScolaire.objects.all().order_by('-date_debut')
        serializer = AnneeScolaireSerializer(annees, many=True)
        return Response(serializer.data)


class AnneePeriodesView(APIView):
    """GET /api/annees/<annee_id>/periodes/ — Périodes d'une année scolaire."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, annee_id):
        etab = _get_user_etablissement(request.user)
        if etab:
            annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
        else:
            annee = get_object_or_404(AnneeScolaire, pk=annee_id)
        periodes = PeriodeEvaluation.objects.filter(annee_scolaire=annee).order_by('numero')
        serializer = PeriodeSerializer(periodes, many=True)
        return Response(serializer.data)


# ── Élèves ────────────────────────────────────────────────────────────────────

class ElevesListView(APIView):
    """GET /api/eleves/ — Liste des élèves VISIBLES par le rôle demandeur.

    Cloisonnement : staff → son établissement ; parent → ses enfants ;
    élève → lui-même ; super admin / directeur réseau → tous.
    """
    permission_classes = [EleveScopeAccess]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request):
        qs = eleves_visibles(request.user)

        matricule = request.query_params.get('matricule')
        nom = request.query_params.get('nom')
        if matricule:
            qs = qs.filter(matricule__icontains=matricule)
        if nom:
            qs = qs.filter(nom__icontains=nom)
        
        serializer = EleveSerializer(qs, many=True)
        return Response(serializer.data)


class EleveDetailView(APIView):
    """GET /api/eleves/<pk>/ — Détail d'un élève."""
    permission_classes = [EleveScopeAccess]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, pk):
        eleve = get_eleve_scope(request.user, pk)
        if eleve is None:
            return Response(
                {'erreur': 'Élève introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(EleveSerializer(eleve).data)


class EleveInscriptionsView(APIView):
    """GET /api/eleves/<pk>/inscriptions/ — Inscriptions d'un élève."""
    permission_classes = [EleveScopeAccess]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, pk):
        eleve = get_eleve_scope(request.user, pk)
        if eleve is None:
            return Response(
                {'erreur': 'Élève introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        inscriptions = Inscription.objects.filter(eleve=eleve).select_related(
            'classe', 'annee_scolaire'
        ).order_by('-annee_scolaire__date_debut')
        serializer = InscriptionSerializer(inscriptions, many=True)
        return Response(serializer.data)


class EleveBulletinsView(APIView):
    """GET /api/eleves/<pk>/bulletins/ — Bulletins publiés d'un élève."""
    permission_classes = [EleveScopeAccess]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, pk):
        eleve = get_eleve_scope(request.user, pk)
        if eleve is None:
            return Response(
                {'erreur': 'Élève introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        bulletins = Bulletin.objects.filter(
            inscription__eleve=eleve,
            est_publie=True,
        ).select_related('inscription__classe', 'trimestre').order_by('-date_publication')
        serializer = BulletinSerializer(bulletins, many=True)
        return Response(serializer.data)


class EleveMoyennesView(APIView):
    """GET /api/eleves/<pk>/moyennes/ — Moyennes générales d'un élève."""
    permission_classes = [EleveScopeAccess]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, pk):
        eleve = get_eleve_scope(request.user, pk)
        if eleve is None:
            return Response(
                {'erreur': 'Élève introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        annee_id = request.query_params.get('annee')
        qs = MoyenneGenerale.objects.filter(
            inscription__eleve=eleve,
        ).select_related('trimestre', 'inscription')
        if annee_id:
            qs = qs.filter(inscription__annee_scolaire_id=annee_id)
        serializer = MoyenneGeneraleSerializer(qs.order_by('trimestre__numero'), many=True)
        return Response(serializer.data)


class ElevePaiementsView(APIView):
    """GET /api/eleves/<pk>/paiements/ — Paiements d'un élève."""
    permission_classes = [EleveScopeAccess]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, pk):
        eleve = get_eleve_scope(request.user, pk)
        if eleve is None:
            return Response(
                {'erreur': 'Élève introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        annee_id = request.query_params.get('annee')
        qs = Paiement.objects.filter(
            inscription__eleve=eleve,
        ).select_related('rubrique').order_by('-date_paiement')
        if annee_id:
            qs = qs.filter(inscription__annee_scolaire_id=annee_id)
        serializer = PaiementSerializer(qs, many=True)
        return Response(serializer.data)


class ElevePresencesView(APIView):
    """GET /api/eleves/<pk>/presences/ — Présences/absences d'un élève."""
    permission_classes = [EleveScopeAccess]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, pk):
        eleve = get_eleve_scope(request.user, pk)
        if eleve is None:
            return Response(
                {'erreur': 'Élève introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        annee_id = request.query_params.get('annee')
        qs = Presence.objects.filter(
            inscription__eleve=eleve,
        ).select_related('appel').order_by('-appel__date')
        if annee_id:
            qs = qs.filter(inscription__annee_scolaire_id=annee_id)
        serializer = PresenceSerializer(qs, many=True)
        return Response(serializer.data)
