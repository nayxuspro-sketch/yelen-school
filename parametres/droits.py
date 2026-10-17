"""
Droits d'accès par rôle : modules et fonctionnalités.

Le Super Admin coche, pour chaque rôle du personnel, les fonctionnalités
(entrées de menu) accessibles dans chaque module. Un module est accessible dès
qu'une de ses fonctionnalités l'est ; ses pages hors menu suivent cet accès.

Une fonctionnalité est identifiée par le préfixe d'URL de son entrée de menu
(``data-url`` du menu latéral) ; des préfixes secondaires y rattachent les
pages liées. Un module correspond à l'espace de noms d'URL d'une application.

Résolution d'un droit (rôle, module, fonctionnalité) :
  1. enregistrement ``DroitAcces`` de la fonctionnalité ;
  2. sinon enregistrement du module (``fonctionnalite=''``, historique) ;
  3. sinon valeur par défaut (``DEFAUTS``), qui reproduit le comportement
     antérieur de l'application.

Le Super Admin dispose de tous les accès ; PARENT et ÉLÈVE restent confinés à
leurs portails par ``RoleAccessMiddleware``.
"""
from collections import namedtuple

from django.core.cache import cache

from core.models import RoleChoices

Fonctionnalite = namedtuple('Fonctionnalite', 'prefixe libelle prefixes')
Module = namedtuple('Module', 'code libelle section fonctionnalites')


def _f(prefixe, libelle, *autres):
    return Fonctionnalite(prefixe, libelle, (prefixe, *autres))


SECTION_SCOLARITE = 'Scolarité'
SECTION_ADMINISTRATION = 'Administration'
SECTION_CONFIGURATION = 'Configuration'

MODULES = (
    Module('inscriptions', 'Inscriptions', SECTION_SCOLARITE, (
        _f('/inscriptions/', 'Élèves'),
        _f('/inscriptions/reinscription/', 'Réinscription'),
    )),
    Module('pedagogie', 'Pédagogie', SECTION_SCOLARITE, (
        _f('/pedagogie/cahier-textes/', 'Cahier de textes'),
        _f('/pedagogie/matieres/', 'Matières'),
        _f('/pedagogie/enseignements/', 'Enseignements'),
        _f('/pedagogie/evaluations/', 'Évaluations', '/pedagogie/classes/'),
        _f('/pedagogie/releve-notes/', 'Relevé de notes'),
        _f('/pedagogie/resultats/', 'Résultats'),
        _f('/pedagogie/resultats/moyennes-disciplines/', 'Moyennes par discipline'),
        _f('/pedagogie/risque-decrochage/', 'Risque de décrochage'),
        _f('/pedagogie/predictions/', 'Prédictions examens'),
        _f('/pedagogie/competences/', 'Bulletins compétences'),
    )),
    Module('bulletins', 'Bulletins', SECTION_SCOLARITE, (
        _f('/bulletins/', 'Bulletins trimestriels'),
        _f('/bulletins/annuel/', 'Bulletin annuel'),
    )),
    Module('presences', 'Présences', SECTION_SCOLARITE, (
        _f('/presences/', 'Appels'),
        _f('/presences/justifications/', 'Justifications'),
    )),
    Module('examens', 'Examens', SECTION_SCOLARITE, (
        _f('/examens/', "Sessions d'examens"),
    )),
    Module('viescolaire', 'Vie scolaire', SECTION_SCOLARITE, (
        _f('/viescolaire/fiches-suivi/', 'Fiches de suivi', '/viescolaire/eleve/'),
        _f('/viescolaire/emploi-du-temps/', 'Emploi du temps', '/viescolaire/classe/', '/viescolaire/seance/'),
        _f('/viescolaire/emploi-du-temps/professeur/', 'Emploi du temps par professeur'),
        _f('/viescolaire/conseils/', 'Conseils de classe'),
        _f('/viescolaire/appels-decision/', 'Appels de décision', '/viescolaire/decision/'),
        _f('/viescolaire/sanctions/', 'Sanctions disciplinaires'),
        _f('/viescolaire/activites/', 'Activités parascolaires'),
        _f('/viescolaire/discipline/capital/', 'Capital points discipline', '/viescolaire/discipline/'),
    )),
    Module('personnel', 'Personnel', SECTION_ADMINISTRATION, (
        _f('/personnel/', 'Liste du personnel'),
        _f('/personnel/salaires/', 'Salaires'),
        _f('/personnel/conges/', 'Congés'),
    )),
    Module('finances', 'Finances', SECTION_ADMINISTRATION, (
        _f('/finances/paiements/', 'Paiements', '/finances/situation/', '/finances/echeancier/', '/finances/echeanciers/'),
        _f('/finances/redevables/', 'Redevables'),
        _f('/finances/exoneres/', 'Exonérés'),
        _f('/finances/bourses/', 'Bourses & Aides', '/finances/types-bourses/'),
        _f('/finances/relances/', 'Relances'),
        _f('/finances/relances/historique/', 'Historique relances'),
        _f('/finances/bilan/encaissements/', 'Bilan encaissements'),
        _f('/finances/mobile-money/', 'Mobile Money'),
        _f('/finances/depenses/', 'Dépenses', '/finances/categories-depenses/'),
        _f('/finances/budget/tresorerie/', 'Trésorerie'),
        _f('/finances/budget/', 'Budget prévisionnel'),
    )),
    Module('vacations', 'Vacations', SECTION_ADMINISTRATION, (
        _f('/vacations/', 'Contrats'),
        _f('/vacations/bulletins/', 'Bulletins de vacation'),
    )),
    Module('communication', 'Communication', SECTION_ADMINISTRATION, (
        _f('/communication/', 'Messages parents'),
        _f('/communication/sms-direct/', 'SMS Direct'),
    )),
    Module('manuels', 'Manuels scolaires', SECTION_ADMINISTRATION, (
        _f('/manuels/', 'Catalogue'),
        _f('/manuels/attributions/', 'Attributions'),
        _f('/manuels/non-rendus/', 'Non rendus'),
    )),
    Module('documents', 'Documents', SECTION_ADMINISTRATION, (
        _f('/documents/listes/', 'Listes de classes'),
        _f('/documents/personnel/', 'Liste du personnel'),
        _f('/documents/convocations/', 'Convocations'),
        _f('/documents/circulaires/', 'Circulaires'),
    )),
    Module('parametres', 'Paramètres', SECTION_CONFIGURATION, (
        _f('/parametres/etablissement/', 'Établissement'),
        _f('/parametres/identite-etablissement/', 'Identité établissement'),
        _f('/parametres/annees/', 'Années scolaires'),
        _f('/parametres/calendrier/', 'Calendrier scolaire'),
        _f('/parametres/modeles-messages/', 'Modèles de messages'),
        _f('/parametres/sms-auto/', 'SMS automatiques'),
        _f('/parametres/cycles/', 'Cycles'),
        _f('/parametres/classes/', 'Classes'),
        _f('/parametres/postes/', 'Postes'),
        _f('/parametres/statuts/', 'Statuts élèves'),
        _f('/parametres/rubriques/', 'Rubriques paiement'),
        _f('/parametres/tarifs/', 'Tarifs de scolarité'),
        _f('/parametres/disciplines/', 'Disciplines'),
        _f('/parametres/categories-disciplines/', 'Catégories disciplines'),
        _f('/parametres/periodes/', 'Périodes'),
        _f('/parametres/appreciations/', 'Appréciation Secondaire'),
        _f('/parametres/appreciations-primaire/', 'Appréciation Primaire'),
        _f('/parametres/signataires/', 'Signataires'),
        _f('/parametres/signataires/configurer/', 'Configurer signataires'),
        _f('/parametres/signataires/formulaire/', 'Formulaire signataires (menu Documents)'),
        _f('/parametres/types-evaluations/', "Types d'évaluation"),
        _f('/parametres/types-documents/', 'Types Documents'),
        _f('/parametres/types-sanctions/', 'Types Sanctions'),
        _f('/parametres/titres-fonctions/', 'Titres Fonctions'),
        _f('/parametres/titres-honorifiques/', 'Titres Honorifiques'),
    )),
)
MODULES_PAR_CODE = {m.code: m for m in MODULES}
CODES_MODULES = frozenset(MODULES_PAR_CODE)
PREFIXES_FONCTIONNALITES = frozenset(f.prefixe for m in MODULES for f in m.fonctionnalites)

# (préfixe, clé de fonctionnalité) par module, du plus spécifique au plus général
_PREFIXES_PAR_MODULE = {
    m.code: sorted(((p, f.prefixe) for f in m.fonctionnalites for p in f.prefixes), key=lambda t: -len(t[0]))
    for m in MODULES
}

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

CLE_CACHE = 'droits_acces:matrice:v2'
DUREE_CACHE = 60  # secondes — borne la latence d'un cache local par processus


def matrice_effective():
    """{rôle: {module: frozenset(préfixes des fonctionnalités autorisées)}}."""
    matrice = cache.get(CLE_CACHE)
    if matrice is None:
        from .models import DroitAcces
        explicites = {
            (role, module, fonctionnalite): autorise
            for role, module, fonctionnalite, autorise
            in DroitAcces.objects.values_list('role', 'module', 'fonctionnalite', 'autorise')
        }

        def autorise(role, module, fonctionnalite):
            cle = (role.value, module.code, fonctionnalite.prefixe)
            if cle in explicites:
                return explicites[cle]
            return explicites.get((role.value, module.code, ''), role in DEFAUTS.get(module.code, _TOUS))

        matrice = {
            role.value: {
                module.code: frozenset(f.prefixe for f in module.fonctionnalites if autorise(role, module, f))
                for module in MODULES
            }
            for role in ROLES_CONFIGURABLES
        }
        cache.set(CLE_CACHE, matrice, DUREE_CACHE)
    return matrice


def invalider_cache():
    cache.delete(CLE_CACHE)


def _est_super(user):
    return getattr(user, 'role', None) == RoleChoices.SUPER_ADMIN or getattr(user, 'is_superuser', False)


def fonctionnalites_autorisees(user):
    """Préfixes des fonctionnalités accessibles à ``user`` (toutes pour le Super Admin)."""
    if _est_super(user):
        return PREFIXES_FONCTIONNALITES
    par_module = matrice_effective().get(getattr(user, 'role', None), {})
    return frozenset(p for prefixes in par_module.values() for p in prefixes)


def modules_autorises(user):
    """Codes des modules dont au moins une fonctionnalité est accessible à ``user``."""
    if _est_super(user):
        return CODES_MODULES
    par_module = matrice_effective().get(getattr(user, 'role', None), {})
    return frozenset(module for module, prefixes in par_module.items() if prefixes)


def fonctionnalite_du_chemin(module, path):
    """Clé de la fonctionnalité du module couvrant ``path`` (préfixe le plus long), sinon None."""
    for prefixe, cle in _PREFIXES_PAR_MODULE.get(module, ()):
        if path.startswith(prefixe):
            return cle
    return None


def droits_requete(request):
    """(modules, fonctionnalités) autorisés pour la requête, mémorisés sur celle-ci."""
    droits = getattr(request, '_droits', None)
    if droits is None:
        droits = request._droits = (modules_autorises(request.user), fonctionnalites_autorisees(request.user))
    return droits


def acces_autorise(request, module, path):
    """Accès de l'utilisateur de la requête à ``path`` du ``module``."""
    modules, fonctionnalites = droits_requete(request)
    cle = fonctionnalite_du_chemin(module, path)
    return cle in fonctionnalites if cle else module in modules


def peut_acceder(user, module):
    return module in modules_autorises(user)


def libelle_module(code):
    return MODULES_PAR_CODE[code].libelle if code in MODULES_PAR_CODE else code


def enregistrer_matrice(coches, utilisateur):
    """Enregistre la matrice complète ; ``coches`` = {"ROLE:module:préfixe", …} autorisés."""
    from .models import DroitAcces

    existants = {(d.role, d.module, d.fonctionnalite): d for d in DroitAcces.objects.exclude(fonctionnalite='')}
    nouveaux = []
    for role in (r.value for r in ROLES_CONFIGURABLES):
        for module in MODULES:
            for f in module.fonctionnalites:
                autorise = f'{role}:{module.code}:{f.prefixe}' in coches
                droit = existants.get((role, module.code, f.prefixe))
                if droit is None:
                    nouveaux.append(DroitAcces(role=role, module=module.code, fonctionnalite=f.prefixe,
                                               autorise=autorise, created_by=utilisateur, updated_by=utilisateur))
                elif droit.autorise != autorise:
                    droit.autorise = autorise
                    droit.updated_by = utilisateur
                    droit.save(update_fields=['autorise', 'updated_by', 'updated_at'])
    if nouveaux:
        DroitAcces.objects.bulk_create(nouveaux)
    invalider_cache()
