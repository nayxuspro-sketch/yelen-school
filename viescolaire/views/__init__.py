"""Vues de l'application viescolaire.

Paquet découpé par domaine (octobre 2026) ; les URLs et les tests continuent
d'utiliser ``viescolaire.views.<nom>`` grâce aux ré-exports ci-dessous.
"""
from .conseils import (  # noqa: F401
    conseil_list,
    conseil_detail,
    conseil_create,
    conseil_pv_pdf,
    appel_decision_list,
    appel_decision_create,
    appel_decision_traiter,
)
from .sanctions import (  # noqa: F401
    sanction_list,
    sanction_create,
    sanction_delete,
)
from .activites import (  # noqa: F401
    activite_list,
    activite_detail,
    activite_create,
    activite_edit,
    activite_delete,
)
from .commun import (  # noqa: F401
    _get_etab,
)
from .edt import (  # noqa: F401
    _jours_grille,
    edt_config,
    emploi_du_temps_index,
    emploi_du_temps,
    seance_create,
    seance_delete,
    edt_generer,
    emploi_du_temps_pdf,
    emploi_du_temps_prof_index,
    emploi_du_temps_prof,
    emploi_du_temps_prof_pdf,
    occupation_salles,
)
from .suivi import (  # noqa: F401
    fiche_suivi_eleve,
    fiches_suivi_list,
    _calcul_capital_points,
    config_discipline,
    capital_points_list,
)
from .commun import WeasyHTML  # noqa: F401
