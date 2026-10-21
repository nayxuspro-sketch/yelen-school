"""
Droits d'accès par rôle : modules et fonctionnalités.

Le Super Admin coche, pour chaque rôle du personnel, les fonctionnalités
(entrées de menu) accessibles dans chaque module. Un module est accessible dès
qu'une de ses fonctionnalités l'est ; ses pages hors menu suivent cet accès.

Une fonctionnalité est identifiée par le préfixe d'URL de son entrée de menu
(``data-url`` du menu latéral) ; des préfixes secondaires y rattachent les
pages liées. Un module correspond à l'espace de noms d'URL d'une application.
Une fonctionnalité peut comporter des actions (sous-fonctionnalités : saisie,
validation, suppression…), identifiées par les noms d'URL de leurs vues ; une
action n'est accessible que si sa fonctionnalité l'est.

Résolution d'un droit (rôle, module, fonctionnalité[, action]) :
  1. enregistrement ``DroitAcces`` de l'action ;
  2. sinon enregistrement de la fonctionnalité (``action=''``) ;
  3. sinon enregistrement du module (``fonctionnalite=''``, historique) ;
  4. sinon valeur par défaut (``DEFAUTS``), qui reproduit le comportement
     antérieur de l'application.
Une action ou une fonctionnalité dont l'accès historique était plus restreint
que celui de son module porte ses propres rôles par défaut (``roles=``) : ils
remplacent les étapes 2 à 4, de sorte que le déploiement ne change rien.

Rôles personnalisés (``parametres.models.RolePersonnalise``) : créés par le
Super Admin sur un rôle intégré de référence (``base``). Tant qu'un droit n'est
pas enregistré pour le rôle personnalisé, il vaut celui de sa référence ; un
utilisateur de ce rôle porte ``role = base`` (comportement métier inchangé) et
la matrice le reconnaît par ``User.role_effectif`` (le code du rôle personnalisé).

Le Super Admin dispose de tous les accès ; PARENT et ÉLÈVE restent confinés à
leurs portails par ``RoleAccessMiddleware``.
"""
from collections import namedtuple

from django.core.cache import cache

from core.models import RoleChoices
from finances.permissions import FINANCE_APPROVER_ROLES, FINANCE_WRITE_ROLES

Action = namedtuple('Action', 'code libelle url_names roles')
Fonctionnalite = namedtuple('Fonctionnalite', 'prefixe libelle prefixes actions roles')
Module = namedtuple('Module', 'code libelle section fonctionnalites')

# Rôles historiques des actes restreints (cf. finances.permissions et anciens contrôles codés en dur)
_DIRECTION = frozenset({RoleChoices.DIRECTEUR, RoleChoices.CENSEUR})
_SECRETARIAT = _DIRECTION | {RoleChoices.SECRETAIRE, RoleChoices.COMPTABLE}
_FINANCE_SAISIE = frozenset(FINANCE_WRITE_ROLES)
_FINANCE_APPROBATION = frozenset(FINANCE_APPROVER_ROLES)


def _a(code, libelle, *url_names, roles=None):
    return Action(code, libelle, url_names, roles)


def _f(prefixe, libelle, *autres, actions=(), roles=None):
    return Fonctionnalite(prefixe, libelle, (prefixe, *autres), tuple(actions), roles)


SECTION_SCOLARITE = 'Scolarité'
SECTION_ADMINISTRATION = 'Administration'
SECTION_CONFIGURATION = 'Configuration'

MODULES = (
    Module('inscriptions', 'Inscriptions', SECTION_SCOLARITE, (
        _f('/inscriptions/', 'Élèves', actions=(
            _a('gerer', 'Créer / modifier un élève et ses inscriptions',
               'eleve_create', 'eleve_update', 'inscription_create', 'inscription_update',
               'transfert_classe', 'marquer_abandon', 'eleve_import', 'eleve_import_template'),
            _a('supprimer', 'Supprimer un élève', 'eleve_delete', 'evenement_supprimer'),
            _a('exporter', 'Exporter la liste des élèves (CSV / Excel)', 'eleve_list_csv', 'eleve_list_xlsx', roles=_SECRETARIAT),
            _a('transferts', 'Demander un transfert inter-établissements', 'transfert_inter_demander'),
            _a('transferts_decider', 'Approuver / refuser un transfert', 'transfert_inter_approuver', 'transfert_inter_refuser',
               roles=frozenset({RoleChoices.DIRECTEUR})),
        )),
        _f('/inscriptions/reinscription/', 'Réinscription', actions=(
            _a('reinscrire', 'Réinscrire un élève', 'reinscrire_eleve'),
        )),
    )),
    Module('pedagogie', 'Pédagogie', SECTION_SCOLARITE, (
        _f('/pedagogie/cahier-textes/', 'Cahier de textes', actions=(
            _a('saisir', 'Saisir / modifier une entrée', 'cahier_textes_create', 'cahier_textes_update'),
            _a('supprimer', 'Supprimer une entrée', 'cahier_textes_delete'),
        )),
        _f('/pedagogie/matieres/', 'Matières', actions=(
            _a('gerer', 'Créer / modifier une matière', 'matiere_create', 'matiere_update'),
        )),
        _f('/pedagogie/enseignements/', 'Enseignements', actions=(
            _a('gerer', 'Créer / modifier un enseignement', 'enseignement_create', 'enseignement_update'),
        )),
        _f('/pedagogie/evaluations/', 'Évaluations', '/pedagogie/classes/', actions=(
            _a('gerer', 'Créer / modifier une évaluation', 'evaluation_create', 'evaluation_update'),
            _a('saisir_notes', 'Saisir les notes', 'evaluation_saisie', 'saisie_classe_select', 'saisie_rapide_classe'),
        )),
        _f('/pedagogie/releve-notes/', 'Relevé de notes'),
        _f('/pedagogie/resultats/', 'Résultats', actions=(
            _a('calculer', 'Calculer les moyennes', 'calculer_moyennes_classe'),
            _a('analyse_ia', "Générer l'analyse IA du bilan", 'generer_commentaires_bilan'),
        )),
        _f('/pedagogie/resultats/moyennes-disciplines/', 'Moyennes par discipline'),
        _f('/pedagogie/risque-decrochage/', 'Risque de décrochage'),
        _f('/pedagogie/predictions/', 'Prédictions examens', actions=(
            _a('calculer', 'Calculer les prédictions', 'prediction_calculer'),
        )),
        _f('/pedagogie/competences/', 'Bulletins compétences', actions=(
            _a('saisir', 'Saisir les compétences', 'competences_saisie', 'competence_sauvegarder'),
            _a('referentiel', 'Gérer le référentiel', 'competences_referentiel', 'competence_supprimer'),
        )),
    )),
    Module('bulletins', 'Bulletins', SECTION_SCOLARITE, (
        _f('/bulletins/', 'Bulletins trimestriels'),
        _f('/bulletins/annuel/', 'Bulletin annuel'),
    )),
    Module('presences', 'Présences', SECTION_SCOLARITE, (
        _f('/presences/', 'Appels', actions=(
            _a('faire_appel', "Faire l'appel", 'classe_select', 'appel_create', 'appel_saisie', 'qr_scanner', 'api_qr_pointer'),
        )),
        _f('/presences/justifications/', 'Justifications', actions=(
            _a('enregistrer', 'Enregistrer une justification', 'justification_create'),
            _a('traiter', 'Traiter (accepter / refuser)', 'justification_process'),
        )),
    )),
    Module('examens', 'Examens', SECTION_SCOLARITE, (
        _f('/examens/', "Sessions d'examens", actions=(
            _a('gerer', 'Créer / modifier une session', 'session_create', 'session_edit'),
            _a('inscrire', 'Inscrire les candidats', 'inscrire_classe'),
            _a('resultats', 'Saisir les résultats', 'saisie_resultats'),
            _a('centres', 'Centres, salles et placements',
               'centre_create', 'centre_edit', 'centre_delete', 'salle_create', 'salle_edit', 'salle_delete',
               'placement_salle', 'placement_delete'),
        )),
    )),
    Module('viescolaire', 'Vie scolaire', SECTION_SCOLARITE, (
        _f('/viescolaire/fiches-suivi/', 'Fiches de suivi', '/viescolaire/eleve/'),
        _f('/viescolaire/emploi-du-temps/', 'Emploi du temps', '/viescolaire/classe/', '/viescolaire/seance/', actions=(
            _a('modifier', "Modifier l'emploi du temps (séances, génération)", 'seance_create', 'seance_delete', 'edt_generer'),
        )),
        _f('/viescolaire/emploi-du-temps/professeur/', 'Emploi du temps par professeur'),
        _f('/viescolaire/conseils/', 'Conseils de classe', actions=(
            _a('creer', 'Créer un conseil de classe', 'conseil_create'),
        )),
        _f('/viescolaire/appels-decision/', 'Appels de décision', '/viescolaire/decision/', actions=(
            _a('contester', 'Contester une décision', 'appel_decision_create'),
            _a('traiter', 'Traiter un appel', 'appel_decision_traiter'),
        )),
        _f('/viescolaire/sanctions/', 'Sanctions disciplinaires', actions=(
            _a('prononcer', 'Prononcer une sanction', 'sanction_create', roles=_SECRETARIAT - {RoleChoices.COMPTABLE} | {RoleChoices.AVS}),
            _a('supprimer', 'Supprimer une sanction', 'sanction_delete'),
        )),
        _f('/viescolaire/activites/', 'Activités parascolaires', actions=(
            _a('gerer', 'Créer / modifier une activité', 'activite_create', 'activite_edit'),
            _a('supprimer', 'Supprimer une activité', 'activite_delete'),
        )),
        _f('/viescolaire/discipline/capital/', 'Capital points discipline', '/viescolaire/discipline/', actions=(
            _a('configurer', 'Configurer le système de points', 'config_discipline'),
        )),
    )),
    Module('personnel', 'Personnel', SECTION_ADMINISTRATION, (
        _f('/personnel/', 'Liste du personnel', actions=(
            _a('gerer', 'Créer / modifier un agent et ses inscriptions',
               'create', 'update', 'inscription_create', 'inscription_edit', 'toggle_active'),
            _a('supprimer', 'Supprimer une inscription annuelle', 'inscription_delete'),
        )),
        _f('/personnel/salaires/', 'Salaires', actions=(
            _a('gerer', 'Créer / modifier un salaire', 'salaire_create', 'salaire_create_pour', 'salaire_update'),
            _a('valider', 'Valider un salaire', 'salaire_valider'),
            _a('payer', 'Payer un salaire', 'salaire_payer'),
            _a('supprimer', 'Supprimer un salaire', 'salaire_delete'),
        )),
        _f('/personnel/conges/', 'Congés', actions=(
            _a('creer', 'Enregistrer une demande de congé', 'conge_create', 'conge_create_pour'),
            _a('decider', 'Approuver / refuser un congé', 'conge_approuver', 'conge_refuser'),
        )),
    )),
    Module('finances', 'Finances', SECTION_ADMINISTRATION, (
        _f('/finances/paiements/', 'Paiements', '/finances/situation/', '/finances/echeancier/', '/finances/echeanciers/', actions=(
            _a('encaisser', 'Encaisser un paiement', 'paiement_create', 'paiement_recherche_eleve', 'paiement_confirmation',
               'api_rubriques', roles=_FINANCE_SAISIE),
            _a('rembourser', 'Rembourser / annuler un remboursement', 'remboursement_create', 'remboursement_delete',
               roles=_FINANCE_APPROBATION),
            _a('echeanciers', 'Créer / modifier / supprimer un échéancier', 'echeancier_create', 'echeancier_edit', 'echeancier_delete',
               roles=_FINANCE_SAISIE),
        )),
        _f('/finances/redevables/', 'Redevables'),
        _f('/finances/exoneres/', 'Exonérés'),
        _f('/finances/bourses/', 'Bourses & Aides', '/finances/types-bourses/', actions=(
            _a('attribuer', 'Attribuer / modifier une bourse', 'bourse_create', 'bourse_edit', 'api_calculer_bourse', roles=_FINANCE_SAISIE),
            _a('supprimer', 'Supprimer une bourse', 'bourse_delete', roles=_FINANCE_SAISIE),
            _a('types', 'Gérer les types de bourses', 'type_bourse_create', 'type_bourse_edit', 'type_bourse_delete', roles=_FINANCE_SAISIE),
        )),
        _f('/finances/relances/', 'Relances', actions=(
            _a('sms', 'Envoyer les relances par SMS', 'relance_sms', roles=_FINANCE_SAISIE),
        )),
        _f('/finances/relances/historique/', 'Historique relances'),
        _f('/finances/bilan/encaissements/', 'Bilan encaissements'),
        _f('/finances/mobile-money/', 'Mobile Money', actions=(
            _a('initier', 'Initier une demande de paiement', 'mobile_money_create', roles=_FINANCE_SAISIE),
            _a('traiter', 'Confirmer / annuler / vérifier / relancer une transaction', 'mobile_money_confirmer', 'mobile_money_annuler', 'mobile_money_verifier', 'mobile_money_relancer', roles=_FINANCE_SAISIE),
            _a('importer', 'Importer un relevé Orange Money / Moov Money', 'releve_import', roles=_FINANCE_SAISIE),
            _a('rapprocher', 'Rapprocher un relevé (valider, affecter, exclure)', 'releve_valider', 'releve_ligne_affecter', 'releve_ligne_ignorer', roles=_FINANCE_SAISIE),
        )),
        _f('/finances/depenses/', 'Dépenses', '/finances/categories-depenses/', actions=(
            _a('saisir', 'Saisir / modifier / supprimer une dépense', 'depense_create', 'depense_edit', 'depense_delete',
               roles=_FINANCE_SAISIE),
            _a('valider', 'Valider / annuler une dépense', 'depense_valider', 'depense_annuler', roles=_FINANCE_APPROBATION),
            _a('categories', 'Gérer les catégories de dépenses',
               'categorie_depense_create', 'categorie_depense_edit', 'categorie_depense_delete', roles=_FINANCE_SAISIE),
        )),
        _f('/finances/budget/tresorerie/', 'Trésorerie'),
        _f('/finances/budget/', 'Budget prévisionnel', roles=_FINANCE_SAISIE),
    )),
    Module('vacations', 'Vacations', SECTION_ADMINISTRATION, (
        _f('/vacations/', 'Contrats', actions=(
            _a('creer', 'Créer un contrat', 'contrat_create'),
            _a('saisir_heures', 'Saisir les heures', 'saisie_heures'),
            _a('valider_heures', 'Valider / invalider les heures', 'valider_heure', 'invalider_heure'),
        )),
        _f('/vacations/bulletins/', 'Bulletins de vacation', actions=(
            _a('generer', 'Générer les bulletins', 'generer_tous_bulletins', 'generer_bulletin'),
            _a('valider', 'Valider un bulletin', 'valider_bulletin'),
            _a('payer', 'Payer un bulletin', 'payer_bulletin'),
        )),
    )),
    Module('communication', 'Communication', SECTION_ADMINISTRATION, (
        _f('/communication/', 'Messages parents', actions=(
            _a('envoyer', 'Envoyer un message', 'message_create'),
        )),
        _f('/communication/sms-direct/', 'SMS Direct', actions=(
            _a('envoyer', 'Envoyer un SMS', 'sms_direct_envoyer'),
        )),
    )),
    Module('manuels', 'Manuels scolaires', SECTION_ADMINISTRATION, (
        _f('/manuels/', 'Catalogue', actions=(
            _a('gerer', 'Créer / modifier manuels et exemplaires',
               'manuel_create', 'manuel_edit', 'exemplaire_create', 'exemplaire_edit'),
            _a('supprimer', 'Supprimer manuels et exemplaires', 'manuel_delete', 'exemplaire_delete'),
        )),
        _f('/manuels/attributions/', 'Attributions', actions=(
            _a('attribuer', 'Attribuer un manuel', 'attribution_create', 'attribution_depuis_exemplaire'),
            _a('retour', 'Enregistrer un retour', 'attribution_retour'),
        )),
        _f('/manuels/non-rendus/', 'Non rendus', actions=(
            _a('facturer', 'Facturer un manuel non rendu', 'facturer_non_rendu'),
        )),
    )),
    Module('documents', 'Documents', SECTION_ADMINISTRATION, (
        _f('/documents/listes/', 'Listes de classes'),
        _f('/documents/personnel/', 'Liste du personnel'),
        _f('/documents/convocations/', 'Convocations'),
        _f('/documents/circulaires/', 'Circulaires'),
        _f('/documents/statistiques-officielles/', 'Statistiques officielles'),
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
# (module, nom d'URL) → (préfixe de la fonctionnalité, code de l'action)
ACTIONS_PAR_URL = {
    (m.code, nom): (f.prefixe, a.code)
    for m in MODULES for f in m.fonctionnalites for a in f.actions for nom in a.url_names
}
TOUTES_ACTIONS = frozenset((m.code, f.prefixe, a.code) for m in MODULES for f in m.fonctionnalites for a in f.actions)

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

RoleConfigurable = namedtuple('RoleConfigurable', 'code libelle base')  # base : None pour un rôle intégré


def roles_configurables():
    """Colonnes de la matrice : rôles intégrés du personnel puis rôles personnalisés."""
    from .models import RolePersonnalise
    integres = [RoleConfigurable(r.value, r.label, None) for r in ROLES_CONFIGURABLES]
    return integres + [RoleConfigurable(r.code, r.libelle, r.base) for r in RolePersonnalise.objects.order_by('libelle')]


def choix_roles(exclure_super_admin=False):
    """Choix (code, libellé) d'un rôle d'utilisateur : rôles intégrés puis rôles personnalisés."""
    from .models import RolePersonnalise
    integres = [c for c in RoleChoices.choices if not (exclure_super_admin and c[0] == RoleChoices.SUPER_ADMIN)]
    return integres + [(r.code, r.libelle) for r in RolePersonnalise.objects.order_by('libelle')]


def affecter_role(user, code):
    """Applique un code de rôle (intégré ou personnalisé) à ``user`` ; ``role`` reste le rôle de référence."""
    from .models import RolePersonnalise
    if code in RoleChoices.values:
        user.role, user.role_personnalise = code, None
    else:
        role = RolePersonnalise.objects.get(code=code)
        user.role, user.role_personnalise = role.base, role
# Comportement historique : tous les modules ouverts au personnel, sauf les
# finances (fermées aux enseignants et AVS) et les paramètres (direction).
DEFAUTS = {
    'finances': _TOUS - {RoleChoices.ENSEIGNANT, RoleChoices.AVS},
    'parametres': frozenset({RoleChoices.DIRECTEUR, RoleChoices.CENSEUR}),
}

CLE_CACHE = 'droits_acces:matrice:v3'
DUREE_CACHE = 60  # secondes — borne la latence d'un cache local par processus


def matrice_effective():
    """{rôle: {'fonctionnalites': {module: frozenset(préfixes)}, 'actions': frozenset((module, préfixe, action))}}."""
    matrice = cache.get(CLE_CACHE)
    if matrice is None:
        from .models import DroitAcces
        explicites = {
            (role, module, fonctionnalite, action): autorise
            for role, module, fonctionnalite, action, autorise
            in DroitAcces.objects.values_list('role', 'module', 'fonctionnalite', 'action', 'autorise')
        }

        roles = roles_configurables()
        bases = {r.code: r.base for r in roles if r.base}

        def autorise(role, module, f, a=None):
            base = bases.get(role)  # rôle personnalisé : à défaut d'enregistrement propre, valeur de sa référence
            if a is not None:
                cle = (role, module.code, f.prefixe, a.code)
                if cle in explicites:
                    return explicites[cle]
                if a.roles is not None:
                    return autorise(base, module, f, a) if base else role in a.roles
            cle = (role, module.code, f.prefixe, '')
            if cle in explicites:
                return explicites[cle]
            if f.roles is not None:
                return autorise(base, module, f) if base else role in f.roles
            cle = (role, module.code, '', '')
            if cle in explicites:
                return explicites[cle]
            if base:
                return autorise(base, module, f, a)
            return role in DEFAUTS.get(module.code, _TOUS)

        matrice = {}
        for role in roles:
            fonctionnalites = {
                module.code: frozenset(f.prefixe for f in module.fonctionnalites if autorise(role.code, module, f))
                for module in MODULES
            }
            actions = frozenset(
                (module.code, f.prefixe, a.code)
                for module in MODULES for f in module.fonctionnalites for a in f.actions
                if autorise(role.code, module, f, a)
            )
            matrice[role.code] = {'fonctionnalites': fonctionnalites, 'actions': actions}
        cache.set(CLE_CACHE, matrice, DUREE_CACHE)
    return matrice


def invalider_cache():
    cache.delete(CLE_CACHE)


def _est_super(user):
    return getattr(user, 'est_super_admin', False)


def _droits_role(user):
    code = getattr(user, 'role_effectif', None) or getattr(user, 'role', None)
    return matrice_effective().get(code, {'fonctionnalites': {}, 'actions': frozenset()})


def fonctionnalites_autorisees(user):
    """Préfixes des fonctionnalités accessibles à ``user`` (toutes pour le Super Admin)."""
    if _est_super(user):
        return PREFIXES_FONCTIONNALITES
    return frozenset(p for prefixes in _droits_role(user)['fonctionnalites'].values() for p in prefixes)


def actions_autorisees(user):
    """Triplets (module, préfixe, action) accessibles à ``user`` (tous pour le Super Admin)."""
    if _est_super(user):
        return TOUTES_ACTIONS
    return _droits_role(user)['actions']


def modules_autorises(user):
    """Codes des modules dont au moins une fonctionnalité est accessible à ``user``."""
    if _est_super(user):
        return CODES_MODULES
    return frozenset(module for module, prefixes in _droits_role(user)['fonctionnalites'].items() if prefixes)


def fonctionnalite_du_chemin(module, path):
    """Clé de la fonctionnalité du module couvrant ``path`` (préfixe le plus long), sinon None."""
    for prefixe, cle in _PREFIXES_PAR_MODULE.get(module, ()):
        if path.startswith(prefixe):
            return cle
    return None


def droits_requete(request):
    """(modules, fonctionnalités, actions) autorisés pour la requête, mémorisés sur celle-ci."""
    droits = getattr(request, '_droits', None)
    if droits is None:
        user = request.user
        droits = request._droits = (modules_autorises(user), fonctionnalites_autorisees(user), actions_autorisees(user))
    return droits


def cible(module, path, url_name):
    """(préfixe de fonctionnalité, code d'action) visés par une requête ; chacun peut être None."""
    action = ACTIONS_PAR_URL.get((module, url_name))
    if action:
        return action
    return fonctionnalite_du_chemin(module, path), None


def acces_autorise(request, module, path, url_name=None):
    """Accès de l'utilisateur de la requête à ``path`` / ``url_name`` du ``module``."""
    modules, fonctionnalites, actions = droits_requete(request)
    prefixe, action = cible(module, path, url_name)
    if action:
        return prefixe in fonctionnalites and (module, prefixe, action) in actions
    return prefixe in fonctionnalites if prefixe else module in modules


def autorise_url(request, nom_complet):
    """Droit d'afficher un lien vers ``'module:nom_url'`` (actions cataloguées ; sinon vrai)."""
    module, _, url_name = nom_complet.partition(':')
    action = ACTIONS_PAR_URL.get((module, url_name))
    if not action:
        return True
    _, fonctionnalites, actions = droits_requete(request)
    prefixe, code = action
    return prefixe in fonctionnalites and (module, prefixe, code) in actions


def libelle_cible(module, path, url_name=None):
    """Libellé humain de la cible refusée : « Saisir les notes » (Pédagogie › Évaluations)."""
    prefixe, action = cible(module, path, url_name)
    m = MODULES_PAR_CODE[module]
    f = next((f for f in m.fonctionnalites if f.prefixe == prefixe), None)
    if f is None:
        return f"« {m.libelle} »"
    if action:
        a = next(a for a in f.actions if a.code == action)
        return f"« {a.libelle} » ({m.libelle} › {f.libelle})"
    return f"« {f.libelle} » ({m.libelle})"


def peut_acceder(user, module):
    return module in modules_autorises(user)


def libelle_module(code):
    return MODULES_PAR_CODE[code].libelle if code in MODULES_PAR_CODE else code


def cles_matrice():
    """Toutes les clés (module, préfixe, action) de la matrice, action '' pour la fonctionnalité elle-même."""
    for module in MODULES:
        for f in module.fonctionnalites:
            yield module.code, f.prefixe, ''
            for a in f.actions:
                yield module.code, f.prefixe, a.code


def enregistrer_matrice(coches, utilisateur):
    """Enregistre la matrice complète ; ``coches`` = {"ROLE:module:préfixe:action", …} autorisés (action vide = fonctionnalité)."""
    from .models import DroitAcces

    existants = {(d.role, d.module, d.fonctionnalite, d.action): d for d in DroitAcces.objects.exclude(fonctionnalite='')}
    nouveaux = []
    for role in (r.code for r in roles_configurables()):
        for module, prefixe, action in cles_matrice():
            autorise = f'{role}:{module}:{prefixe}:{action}' in coches
            droit = existants.get((role, module, prefixe, action))
            if droit is None:
                nouveaux.append(DroitAcces(role=role, module=module, fonctionnalite=prefixe, action=action,
                                           autorise=autorise, created_by=utilisateur, updated_by=utilisateur))
            elif droit.autorise != autorise:
                droit.autorise = autorise
                droit.updated_by = utilisateur
                droit.save(update_fields=['autorise', 'updated_by', 'updated_at'])
    if nouveaux:
        DroitAcces.objects.bulk_create(nouveaux)
    invalider_cache()
