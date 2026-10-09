"""
Rôles autorisés sur le module Finances.

Ces ensembles sont consommés par ``finances.views._require_finance_role`` :

- ``FINANCE_VIEW_ROLES``     : consultation (situations, listes, reçus, états) ;
- ``FINANCE_WRITE_ROLES``    : saisie (paiements, échéanciers, bourses, dépenses) ;
- ``FINANCE_APPROVER_ROLES`` : actes engageant l'établissement (remboursements,
  validation / annulation de dépenses) — réservés à la direction afin de
  séparer la saisie (comptable) de l'approbation.

Les rôles PARENT et ELEVE sont déjà confinés à leurs portails par
``yelen_school.role_middleware`` ; ENSEIGNANT et AVS n'ont aucun accès financier.
"""
from core.models import RoleChoices

FINANCE_VIEW_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR_RESEAU,
    RoleChoices.DIRECTEUR,
    RoleChoices.CENSEUR,
    RoleChoices.COMPTABLE,
    RoleChoices.SECRETAIRE,
})

FINANCE_WRITE_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR,
    RoleChoices.CENSEUR,
    RoleChoices.COMPTABLE,
})

FINANCE_APPROVER_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR_RESEAU,
    RoleChoices.DIRECTEUR,
    RoleChoices.CENSEUR,
})
