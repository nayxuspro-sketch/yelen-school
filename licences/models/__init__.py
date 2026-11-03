"""Modèles du module Licences — façade rétrocompatible."""
from .activations_audit import LicenceActivation, LicenceAlert, LicenceAuditLog
from .licence import (
    FEATURE_FLAGS,
    LIMITES_LICENCES,
    Licence,
    LicenceManager,
    StatutLicence,
    TypeLicence,
    User,
)

__all__ = [
    'FEATURE_FLAGS',
    'LIMITES_LICENCES',
    'Licence',
    'LicenceActivation',
    'LicenceAlert',
    'LicenceAuditLog',
    'LicenceManager',
    'StatutLicence',
    'TypeLicence',
    'User',
]
