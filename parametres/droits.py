"""
Droits d'accès aux modules par rôle.

Le Super Admin attribue, module par module, l'accès de chaque rôle du personnel.
La matrice est enregistrée dans ``DroitAcces`` ; en l'absence d'enregistrement,
les valeurs par défaut ci-dessous reproduisent le comportement historique de
l'application. Le Super Admin dispose de tous les accès ; les rôles PARENT et
ÉLÈVE restent confinés à leurs portails par ``RoleAccessMiddleware``.

Un module correspond à l'espace de noms d'URL d'une application (``app_name``).
"""
from collections import namedtuple

from django.core.cache import cache

from core.models import RoleChoices

Module = namedtuple('Module', 'code libelle section')

SECTION_SCOLARITE = 'Scolarité'
SECTION_ADMINISTRATION = 'Administration'
SECTION_CONFIGURATION = 'Configuration'

MODULES = (
    Module('inscriptions',  'Inscriptions',        SECTION_SCOLARITE),
    Module('pedagogie',     'Pédagogie',           SECTION_SCOLARITE),
    Module('bulletins',     'Bulletins',           SECTION_SCOLARITE),
    Module('presences',     'Présences',           SECTION_SCOLARITE),
    Module('examens',       'Examens',             SECTION_SCOLARITE),
    Module('viescolaire',   'Vie scolaire',        SECTION_SCOLARITE),
    Module('personnel',     'Personnel',           SECTION_ADMINISTRATION),
    Module('finances',      'Finances',            SECTION_ADMINISTRATION),
    Module('vacations',     'Vacations',           SECTION_ADMINISTRATION),
    Module('communication', 'Communication',       SECTION_ADMINISTRATION),
    Module('manuels',       'Manuels scolaires',   SECTION_ADMINISTRATION),
    Module('documents',     'Documents',           SECTION_ADMINISTRATION),
    Module('parametres',    'Paramètres',          SECTION_CONFIGURATION),
)
CODES_MODULES = frozenset(m.code for m in MODULES)

ROLES_CONFIGURABLES = (
    RoleChoices.DIRECTEUR_RESEAU,
    RoleChoices.DIRECTEUR,
    RoleChoices.CENSEUR,
    RoleChoices.SECRETAIRE,
    RoleChoices.COMPTABLE,
    RoleChoices.ENSEIGNANT,
    RoleChoices.AVS,
)

_TOUS = frozenset(ROLES_CONFIGURABLES)
# Comportement historique : tous les modules ouverts au personnel, sauf les
# finances (fermées aux enseignants et AVS) et les paramètres (direction).
DEFAUTS = {
    'finances': _TOUS - {RoleChoices.ENSEIGNANT, RoleChoices.AVS},
    'parametres': frozenset({RoleChoices.DIRECTEUR, RoleChoices.CENSEUR}),
}

CLE_CACHE = 'droits_acces:matrice'
DUREE_CACHE = 60  # secondes — borne la latence d'un cache local par processus


def matrice_effective():
    """{rôle: frozenset(codes de modules autorisés)} pour les rôles configurables."""
    matrice = cache.get(CLE_CACHE)
    if matrice is None:
        from .models import DroitAcces
        explicites = {
            (role, module): autorise
            for role, module, autorise in DroitAcces.objects.values_list('role', 'module', 'autorise')
        }
        matrice = {
            role.value: frozenset(
                m.code for m in MODULES
                if explicites.get((role.value, m.code), role in DEFAUTS.get(m.code, _TOUS))
            )
            for role in ROLES_CONFIGURABLES
        }
        cache.set(CLE_CACHE, matrice, DUREE_CACHE)
    return matrice


def invalider_cache():
    cache.delete(CLE_CACHE)


def modules_autorises(user):
    """Codes des modules accessibles à ``user`` (tous pour le Super Admin / superutilisateur)."""
    role = getattr(user, 'role', None)
    if role == RoleChoices.SUPER_ADMIN or getattr(user, 'is_superuser', False):
        return CODES_MODULES
    return matrice_effective().get(role, frozenset())


def modules_autorises_requete(request):
    """Comme ``modules_autorises`` mais mémorisé sur la requête (middleware + gabarit)."""
    modules = getattr(request, '_droits_modules', None)
    if modules is None:
        modules = request._droits_modules = modules_autorises(request.user)
    return modules


def peut_acceder(user, module):
    return module in modules_autorises(user)


def libelle_module(code):
    return next((m.libelle for m in MODULES if m.code == code), code)


def enregistrer_matrice(coches, utilisateur):
    """Enregistre la matrice complète ; ``coches`` = {"ROLE:module", …} autorisés."""
    from .models import DroitAcces

    existants = {(d.role, d.module): d for d in DroitAcces.objects.all()}
    nouveaux = []
    for role in (r.value for r in ROLES_CONFIGURABLES):
        for module in MODULES:
            autorise = f'{role}:{module.code}' in coches
            droit = existants.get((role, module.code))
            if droit is None:
                nouveaux.append(DroitAcces(role=role, module=module.code, autorise=autorise,
                                           created_by=utilisateur, updated_by=utilisateur))
            elif droit.autorise != autorise:
                droit.autorise = autorise
                droit.updated_by = utilisateur
                droit.save(update_fields=['autorise', 'updated_by', 'updated_at'])
    if nouveaux:
        DroitAcces.objects.bulk_create(nouveaux)
    invalider_cache()
