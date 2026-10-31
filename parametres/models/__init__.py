"""Modèles du module Paramètres — configuration de l'établissement, du calendrier et des documents."""

from .etablissement import (  # noqa: F401 — réexporté tel quel
    IdentiteEtablissement,
    Cycle,
    Classe,
    Salle,
)

from .structure import (  # noqa: F401 — réexporté tel quel
    Poste,
    LocalisationPoste,
    StatutEleve,
    TitreFonction,
    TitreHonorifiquePersonnel,
)

from .tarifs import (  # noqa: F401 — réexporté tel quel
    RubriquePaiement,
    TarifScolarite,
)

from .evaluation import (  # noqa: F401 — réexporté tel quel
    AppreciationMoyenneSecondaire,
    AppreciationMoyennePrimaire,
    CategorieDiscipline,
    Discipline,
)

from .annee import (  # noqa: F401 — réexporté tel quel
    AnneeScolaireManager,
    AnneeScolaire,
    PeriodeEvaluation,
)

from .documents import (  # noqa: F401 — réexporté tel quel
    TypeDocument,
    SignataireDocumentManager,
    SignataireDocument,
    CoSignataire,
)

from .vie_scolaire import (  # noqa: F401 — réexporté tel quel
    TypeSanction,
    Distinction,
    EvenementCalendrier,
    ModeleMessage,
    DeclencheurSMS,
)

from .droits import (  # noqa: F401 — réexporté tel quel
    RolePersonnalise,
    DroitAcces,
    PolitiqueDonnees,
)

# `__all__` : couverture et `import *` voient exactement les mêmes noms.
__all__ = [
    'IdentiteEtablissement',
    'Cycle',
    'Classe',
    'Salle',
    'Poste',
    'LocalisationPoste',
    'StatutEleve',
    'TitreFonction',
    'TitreHonorifiquePersonnel',
    'RubriquePaiement',
    'TarifScolarite',
    'AppreciationMoyenneSecondaire',
    'AppreciationMoyennePrimaire',
    'CategorieDiscipline',
    'Discipline',
    'AnneeScolaireManager',
    'AnneeScolaire',
    'PeriodeEvaluation',
    'TypeDocument',
    'SignataireDocumentManager',
    'SignataireDocument',
    'CoSignataire',
    'TypeSanction',
    'Distinction',
    'EvenementCalendrier',
    'ModeleMessage',
    'DeclencheurSMS',
    'RolePersonnalise',
    'DroitAcces',
    'PolitiqueDonnees',
]
