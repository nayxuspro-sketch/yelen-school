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
  sauf pour un enseignant (role ENSEIGNANT) : le cycle de sa classe
  d'affectation est autorisé, afin qu'il voie au moins sa propre classe.
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

            # Cycles explicitement assignés via ManyToMany (au moins un cycle)
            elif user.cycles.exists():
                if etab:
                    request.cycles_autorises = user.cycles.filter(
                        etablissement=etab
                    )
                else:
                    request.cycles_autorises = user.cycles.all()
                request.est_tous_cycles = False

            # Aucun cycle assigné et pas "Tous les cycles"
            else:
                # Enseignant : autoriser au moins le cycle de sa classe d'affectation
                if user.role == 'ENSEIGNANT':
                    from core.utils import get_membre_personnel
                    membre = get_membre_personnel(user)
                    if membre and membre.classe_affectation_id:
                        cycle_id = membre.classe_affectation.cycle_id
                        if etab:
                            request.cycles_autorises = Cycle.objects.filter(
                                id=cycle_id, etablissement=etab
                            )
                        else:
                            request.cycles_autorises = Cycle.objects.filter(id=cycle_id)
                        request.est_tous_cycles = False
                    else:
                        request.cycles_autorises = Cycle.objects.none()
                        request.est_tous_cycles = False
                else:
                    request.cycles_autorises = Cycle.objects.none()
                    request.est_tous_cycles = False

        return self.get_response(request)
