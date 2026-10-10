"""Vues de l'application pedagogie.

Paquet découpé par domaine (octobre 2026) ; les URLs et les autres applications
continuent d'utiliser ``pedagogie.views.<nom>`` grâce aux ré-exports ci-dessous.
"""
from .commun import (  # noqa: F401
    HTML,
    _pdf_licence_info,
    get_licence_info_for_pdf,
    inject_licence_filigrane_context,
)
from .resultats import (  # noqa: F401
    classe_result_list,
    bilan_periodes,
    generer_commentaires_bilan,
    bilan_pdf,
    releve_moyenne_classe_pdf,
    resultat_classe,
    calculer_moyennes_classe,
    moyennes_disciplines,
    moyennes_disciplines_pdf,
    releve_notes,
    _build_releve_context,
    releve_notes_pdf,
    fiche_discipline_pdf,
    logger,
)
from .matieres import (  # noqa: F401
    matiere_list,
    _build_cycles_config,
    matiere_create,
    matiere_update,
    matiere_cycle_save,
    enseignement_list,
    enseignement_create,
    enseignement_update,
)
from .evaluations import (  # noqa: F401
    _trimestre_en_cours,
    evaluation_list,
    _resolve_trimestre,
    evaluation_create,
    evaluation_update,
    evaluation_saisie,
    saisie_rapide_classe,
    saisie_classe_select,
    EVALUATIONS_CLASSES_PAR_PAGE,
)
from .bulletins import (  # noqa: F401
    _get_appreciation_generale,
    _load_appreciations,
    _match_appreciation,
    _annotate_resultats,
    _build_bulletin_context,
    bulletin_apercu,
    bulletin_pdf,
    bulletin_classe_batch_pdf,
    _build_bulletin_annuel_context,
    _get_mention,
    bulletin_duplicata_pdf,
    bulletin_annuel_apercu,
    bulletin_annuel_pdf,
    bulletin_annuel_classe_batch_pdf,
    _compute_palmares_annuel,
    palmares_annuel,
    palmares_annuel_pdf,
)
from .predictions import (  # noqa: F401
    risque_decrochage,
    risque_decrochage_pdf,
    prediction_index,
    prediction_classe,
    prediction_calculer,
    prediction_classe_pdf,
)
from .cahier_textes import (  # noqa: F401
    cahier_textes_index,
    cahier_textes_classe,
    cahier_textes_create,
    cahier_textes_update,
    cahier_textes_delete,
)
from .competences import (  # noqa: F401
    competences_index,
    competences_referentiel,
    competence_supprimer,
    competences_saisie,
    competence_sauvegarder,
    competences_bulletin_pdf,
)
