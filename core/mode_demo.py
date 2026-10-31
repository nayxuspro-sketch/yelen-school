"""Mode démonstration — instance d'essai publique (offre hébergée, chantier B8).

Une instance de démonstration peut être ouverte à des prospects : elle doit alors être **incapable de
communiquer avec l'extérieur**. Un seul commutateur (``DEMO_MODE=true``) suffit, et il est vérifié aux
endroits par lesquels passent toutes les sorties :

- ``core.sms.sms_actifs()``  → les SMS, mis en file ou non, ne partent plus (aucun appel à la passerelle) ;
- ``core.notifications``     → l'e-mail des notifications n'est plus envoyé ;
- ``core.push.notifier``     → aucune notification push ;
- ``finances.paiements_mobiles.cinetpay_configure()`` → la demande Mobile Money est réputée non configurée,
  donc aucun lien de paiement n'est créé et aucun appel sortant n'a lieu.

Le bandeau « DÉMONSTRATION » (``core.context_processors.demo`` / ``base.html``), le champ ``demo`` de
``/health/`` et la commande ``reinitialiser_demo`` complètent le dispositif.

Ce module ne contient aucune logique métier : il ne fait que lire le réglage, pour que les tests puissent
l'activer par ``override_settings(DEMO_MODE=True)``.
"""
from django.conf import settings


def actif() -> bool:
    """Vrai si l'instance est une démonstration publique."""
    return bool(getattr(settings, 'DEMO_MODE', False))


def refus(canal: str) -> str:
    """Motif consigné quand une sortie est retenue en mode démonstration."""
    return f"Mode démonstration : {canal} non envoyé."
