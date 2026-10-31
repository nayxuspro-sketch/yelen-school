"""Vues du module Inscriptions : élèves, inscriptions, documents, rentrée, parcours, transferts, préinscriptions."""

from .eleves import (  # noqa: F401 — réexporté tel quel
    eleve_list,
    eleve_list_csv,
    eleve_list_xlsx,
    eleve_list_pdf,
    eleve_dossier,
    piece_dossier_telecharger,
    piece_dossier_supprimer,
    eleve_export_donnees,
    eleve_detail,
    eleve_create,
    eleve_update,
    eleve_delete,
)

from .inscriptions import (  # noqa: F401 — réexporté tel quel
    inscription_create,
    inscription_update,
    get_classe_niveau,
    get_classe_cycle,
    get_statut_code,
    _get_inscription_courante,
    marquer_abandon,
    transfert_classe,
)

from .documents import (  # noqa: F401 — réexporté tel quel
    _signataire_carte,
    eleve_fiche_pdf,
    eleve_carte,
    classe_cartes_pdf,
)

from .rentree import (  # noqa: F401 — réexporté tel quel
    _contexte_rentree,
    _classes_par_niveau,
    _uuids,
    reinscription_list,
    passage_classe,
    reinscrire_eleve,
)

from .parcours import (  # noqa: F401 — réexporté tel quel
    _TRANSITION_META,
    _calculer_transition,
    eleve_parcours,
    evenement_parcours_supprimer,
)

from .transferts import (  # noqa: F401 — réexporté tel quel
    transfert_inter_list,
    transfert_inter_demander,
    transfert_inter_detail,
    transfert_inter_approuver,
    transfert_inter_refuser,
    transfert_inter_dossier_pdf,
)

from .preinscriptions import (  # noqa: F401 — réexporté tel quel
    _annee_preinscription,
    preinscription_list,
    preinscription_form,
    preinscription_decider,
    preinscription_inscrire,
)

# `__all__` : couverture et `import *` voient exactement les mêmes noms.
__all__ = [
    'eleve_list',
    'eleve_list_csv',
    'eleve_list_xlsx',
    'eleve_list_pdf',
    'eleve_dossier',
    'piece_dossier_telecharger',
    'piece_dossier_supprimer',
    'eleve_export_donnees',
    'eleve_detail',
    'eleve_create',
    'eleve_update',
    'eleve_delete',
    'inscription_create',
    'inscription_update',
    'get_classe_niveau',
    'get_classe_cycle',
    'get_statut_code',
    '_get_inscription_courante',
    'marquer_abandon',
    'transfert_classe',
    '_signataire_carte',
    'eleve_fiche_pdf',
    'eleve_carte',
    'classe_cartes_pdf',
    '_contexte_rentree',
    '_classes_par_niveau',
    '_uuids',
    'reinscription_list',
    'passage_classe',
    'reinscrire_eleve',
    '_TRANSITION_META',
    '_calculer_transition',
    'eleve_parcours',
    'evenement_parcours_supprimer',
    'transfert_inter_list',
    'transfert_inter_demander',
    'transfert_inter_detail',
    'transfert_inter_approuver',
    'transfert_inter_refuser',
    'transfert_inter_dossier_pdf',
    '_annee_preinscription',
    'preinscription_list',
    'preinscription_form',
    'preinscription_decider',
    'preinscription_inscrire',
]
