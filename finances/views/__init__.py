"""Vues de l'application finances.

Paquet découpé par domaine (octobre 2026) ; les URLs et les autres applications
continuent d'utiliser ``finances.views.<nom>`` grâce aux ré-exports ci-dessous.
"""
from .commun import (  # noqa: F401
    _numero_valide,
    _situations_financieres_en_lot,
    _require_finance_role,
    _require_same_establishment,
    _calcul_situation_financiere,
    _payment_overage_errors,
    WeasyHTML,
)
from .paiements import (  # noqa: F401
    paiement_list,
    paiement_recherche_eleve,
    paiement_create,
    situation_eleve,
    remboursement_create,
    remboursement_delete,
    api_rubriques_inscription,
    recu_pdf,
    historique_pdf,
    paiement_confirmation,
)
from .etats import (  # noqa: F401
    liste_redevables,
    _bilan_paiements_qs,
    bilan_encaissements,
    bilan_encaissements_pdf,
    bilan_encaissements_csv,
    bilan_encaissements_xlsx,
    liste_redevables_pdf,
    liste_exoneres,
    liste_exoneres_pdf,
    certificat_non_redevabilite,
)
from .relances import (  # noqa: F401
    relance_paiement,
    relance_count,
    relance_paiement_pdf,
    relance_sms,
    historique_relances,
)
from .echeanciers import (  # noqa: F401
    echeancier_create,
    echeancier_edit,
    echeancier_delete,
    echeancier_global,
    echeancier_global_xlsx,
)
from .bourses import (  # noqa: F401
    bourse_create,
    bourse_edit,
    bourse_delete,
    boursiers_list,
    boursiers_pdf,
    type_bourse_list,
    type_bourse_form,
    type_bourse_delete,
    api_calculer_bourse,
)
from .mobile_money import (  # noqa: F401
    mobile_money_list,
    mobile_money_create,
    mobile_money_confirmer,
    mobile_money_annuler,
    mobile_money_confirmation_parent,
    _envoyer_sms_mobile_money,
)
from .budget import (  # noqa: F401
    _etab_and_annee,
    _get_annees,
    categorie_depense_list,
    categorie_depense_form,
    categorie_depense_delete,
    depense_list,
    depense_form,
    depense_delete,
    depense_valider,
    depense_annuler,
    budget_previsionnel,
    tableau_bord_budget,
    tableau_bord_budget_xlsx,
)
