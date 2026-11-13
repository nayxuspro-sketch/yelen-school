"""
yelen_school/cycle_middleware.py — Filtrage des données par cycle

Détermine, pour chaque utilisateur connecté, quels cycles il est autorisé à
voir et stocke le résultat sur l'objet request :

- request.cycles_autorises : QuerySet des cycles autorisés
- request.est_tous_cycles  : booléen — True si l'utilisateur voit tous les cycles

Règles :
- Superutilisateur / SUPER_ADMIN / DIRECTEUR_RESEAU : tous les cycles de l'établissement
- Utilisateur avec est_tous_cycles=True : tous les cycles de l'établissement
- Utilisateur avec cycles assignés (ManyToMany) : seulement ces cycles
- Sans droit explicite : aucun cycle ; une affectation professionnelle ne donne pas, à elle seule,
  un droit de consultation sur le compte utilisateur.
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

            # Superutilisateur et rôles réseau : tous les cycles de l'établissement
            if user.is_superuser or user.role in ('SUPER_ADMIN', 'DIRECTEUR_RESEAU'):
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

            # Aucun droit de consultation explicite : l'affectation professionnelle ne le remplace.
            else:
                request.cycles_autorises = Cycle.objects.none()
                request.est_tous_cycles = False

        return self.get_response(request)
