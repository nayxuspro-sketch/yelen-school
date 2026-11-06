"""
yelen_school/cycle_middleware.py — Filtrage des données par cycle

Détermine, pour chaque utilisateur connecté, quels cycles il est autorisé à
voir et stocke le résultat sur l'objet request :

- request.cycles_autorises : QuerySet des cycles autorisés
- request.est_tous_cycles  : booléen — True si l'utilisateur voit tous les cycles

Règles :
- SUPER_ADMIN / DIRECTEUR_RESEAU : tous les cycles de l'établissement
- Utilisateur avec est_tous_cycles=True : tous les cycles de l'établissement
- Utilisateur avec cycles assignés (ManyToMany) : seulement ces cycles
- Utilisateur sans cycles et sans est_tous_cycles : aucun cycle (données vides)

Ce middleware ne filtre pas par classe (enseignants) car il n'existe pas de
lien direct User → MembrePersonnel dans le modèle actuel. Ce filtrage pourra
être ajouté dans les vues spécifiques lorsque le lien sera disponible.
"""

from __future__ import annotations

from parametres.models import Cycle


class CycleAccessMiddleware:
    """
    Middleware de filtrage des données par cycle.
    Doit être placé après AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.cycles_autorises = Cycle.objects.none()
        request.est_tous_cycles = False

        if request.user.is_authenticated:
            user = request.user
            etab = getattr(user, 'etablissement', None)

            # Rôles réseau : tous les cycles de l'établissement
            if user.role in ('SUPER_ADMIN', 'DIRECTEUR_RESEAU'):
                if etab:
                    request.cycles_autorises = Cycle.objects.filter(
                        etablissement=etab
                    )
                else:
                    request.cycles_autorises = Cycle.objects.all()
                request.est_tous_cycles = True

            # Option « Tous les cycles » cochée
            elif getattr(user, 'est_tous_cycles', False):
                if etab:
                    request.cycles_autorises = Cycle.objects.filter(
                        etablissement=etab
                    )
                else:
                    request.cycles_autorises = Cycle.objects.all()
                request.est_tous_cycles = True

            # Cycles explicitement assignés via ManyToMany
            elif hasattr(user, 'cycles'):
                if etab:
                    request.cycles_autorises = user.cycles.filter(
                        etablissement=etab
                    )
                else:
                    request.cycles_autorises = user.cycles.all()
                request.est_tous_cycles = False

            # Aucun cycle assigné et pas "Tous les cycles" → données vides
            else:
                request.cycles_autorises = Cycle.objects.none()
                request.est_tous_cycles = False

        return self.get_response(request)
