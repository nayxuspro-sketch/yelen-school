"""
api/views.py — Vues DRF pour l'API publique YELEN SCHOOL
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404

from inscriptions.models import Eleve, Inscription
from parametres.models import AnneeScolaire, PeriodeEvaluation
from pedagogie.models import MoyenneGenerale, Resultat
from finances.models import Paiement
from presences.models import Presence
from bulletins.models import Bulletin

from .serializers import (
    EleveSerializer, InscriptionSerializer, AnneeScolaireSerializer,
    PeriodeSerializer, MoyenneGeneraleSerializer, PaiementSerializer,
    PresenceSerializer, BulletinSerializer,
)


# ── Authentification ──────────────────────────────────────────────────────────

class ObtenirTokenView(APIView):
    """POST /api/auth/token/ — Obtenir un token à partir de username/password."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response(
                {'erreur': 'Champs username et password requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {'erreur': 'Identifiants invalides.'},
                status=status.HTTP_401_UNAUTHORIZED,
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
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Années scolaires ──────────────────────────────────────────────────────────

class AnneesListView(APIView):
    """GET /api/annees/ — Liste des années scolaires."""

    def get(self, request):
        annees = AnneeScolaire.objects.all().order_by('-date_debut')
        serializer = AnneeScolaireSerializer(annees, many=True)
        return Response(serializer.data)


class AnneePeriodesView(APIView):
    """GET /api/annees/<annee_id>/periodes/ — Périodes d'une année scolaire."""

    def get(self, request, annee_id):
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
        periodes = PeriodeEvaluation.objects.filter(annee_scolaire=annee).order_by('numero')
        serializer = PeriodeSerializer(periodes, many=True)
        return Response(serializer.data)


# ── Élèves ────────────────────────────────────────────────────────────────────

class ElevesListView(APIView):
    """GET /api/eleves/ — Liste des élèves (filtrables par matricule, nom)."""

    def get(self, request):
        qs = Eleve.objects.all().order_by('nom', 'prenom')
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

    def get(self, request, pk):
        eleve = get_object_or_404(Eleve, pk=pk)
        return Response(EleveSerializer(eleve).data)


class EleveInscriptionsView(APIView):
    """GET /api/eleves/<pk>/inscriptions/ — Inscriptions d'un élève."""

    def get(self, request, pk):
        eleve = get_object_or_404(Eleve, pk=pk)
        inscriptions = Inscription.objects.filter(eleve=eleve).select_related(
            'classe', 'annee_scolaire'
        ).order_by('-annee_scolaire__date_debut')
        serializer = InscriptionSerializer(inscriptions, many=True)
        return Response(serializer.data)


class EleveBulletinsView(APIView):
    """GET /api/eleves/<pk>/bulletins/ — Bulletins publiés d'un élève."""

    def get(self, request, pk):
        eleve = get_object_or_404(Eleve, pk=pk)
        bulletins = Bulletin.objects.filter(
            inscription__eleve=eleve,
            est_publie=True,
        ).select_related('inscription__classe', 'trimestre').order_by('-date_publication')
        serializer = BulletinSerializer(bulletins, many=True)
        return Response(serializer.data)


class EleveMoyennesView(APIView):
    """GET /api/eleves/<pk>/moyennes/ — Moyennes générales d'un élève."""

    def get(self, request, pk):
        eleve = get_object_or_404(Eleve, pk=pk)
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

    def get(self, request, pk):
        eleve = get_object_or_404(Eleve, pk=pk)
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

    def get(self, request, pk):
        eleve = get_object_or_404(Eleve, pk=pk)
        annee_id = request.query_params.get('annee')
        qs = Presence.objects.filter(
            inscription__eleve=eleve,
        ).select_related('appel').order_by('-appel__date')
        if annee_id:
            qs = qs.filter(inscription__annee_scolaire_id=annee_id)
        serializer = PresenceSerializer(qs, many=True)
        return Response(serializer.data)
