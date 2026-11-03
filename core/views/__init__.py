"""Vues transverses du cœur : accueil, audit, notifications, portails, exploitation, PWA et système."""

from .accueil import (  # noqa: F401 — réexporté tel quel
    home,
    recherche_globale,
    indicateurs_evolution,
    demarrage,
    pilotage,
    pilotage_enseignants,
)

from .audit import (  # noqa: F401 — réexporté tel quel
    audit_log_list,
    audit_log_pdf,
    audit_log_detail,
)

from .notifications import (  # noqa: F401 — réexporté tel quel
    notifications_list,
    notification_marquer_lu,
    notifications_marquer_tout_lu,
    notifications_badge,
)

from .portail import (  # noqa: F401 — réexporté tel quel
    PORTAILS,
    _REFUS_PORTAIL,
    _portail,
    portail_parent,
    portail_parent_bulletins,
    portail_bulletin,
    portail_document,
    portail_carte_scolaire,
    portail_parent_notifications,
    _reponse_push,
    _requete_push,
    push_abonner,
    push_desabonner,
    push_test,
    portail_parent_vie_scolaire,
    portail_parent_cahier,
    portail_parent_justifier,
)

from .sms import (  # noqa: F401 — réexporté tel quel
    _ADRESSES_LOCALES,
    _url_webhook_sms,
    sms_configuration,
    _etat_reception_sms,
)

from .exploitation import (  # noqa: F401 — réexporté tel quel
    exploitation,
    sauvegarde_telecharger,
    mise_a_jour,
    mise_a_jour_en_ligne,
    mise_a_jour_etat,
    reunion_parents,
    risque_recalculer,
)

from .pwa import (  # noqa: F401 — réexporté tel quel
    app_manifest,
    app_service_worker,
    offline_page,
    saisies_hors_ligne,
    saisies_contexte,
    pwa_manifest,
    certificat_autorite,
    favicon,
    pwa_icon,
    pwa_service_worker,
)

from .systeme import (  # noqa: F401 — réexporté tel quel
    chatbot,
    health_check,
)

# `__all__` : couverture et `import *` voient exactement les mêmes noms.
__all__ = [
    'home',
    'recherche_globale',
    'indicateurs_evolution',
    'demarrage',
    'pilotage',
    'pilotage_enseignants',
    'audit_log_list',
    'audit_log_pdf',
    'audit_log_detail',
    'notifications_list',
    'notification_marquer_lu',
    'notifications_marquer_tout_lu',
    'notifications_badge',
    'PORTAILS',
    '_REFUS_PORTAIL',
    '_portail',
    'portail_parent',
    'portail_parent_bulletins',
    'portail_bulletin',
    'portail_document',
    'portail_carte_scolaire',
    'portail_parent_notifications',
    '_reponse_push',
    '_requete_push',
    'push_abonner',
    'push_desabonner',
    'push_test',
    'portail_parent_vie_scolaire',
    'portail_parent_cahier',
    'portail_parent_justifier',
    '_ADRESSES_LOCALES',
    '_url_webhook_sms',
    'sms_configuration',
    '_etat_reception_sms',
    'exploitation',
    'sauvegarde_telecharger',
    'mise_a_jour',
    'mise_a_jour_en_ligne',
    'mise_a_jour_etat',
    'reunion_parents',
    'risque_recalculer',
    'app_manifest',
    'app_service_worker',
    'offline_page',
    'saisies_hors_ligne',
    'saisies_contexte',
    'pwa_manifest',
    'certificat_autorite',
    'favicon',
    'pwa_icon',
    'pwa_service_worker',
    'chatbot',
    'health_check',
]
