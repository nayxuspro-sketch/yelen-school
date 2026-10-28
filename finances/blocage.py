"""Blocage des bulletins des élèves non à jour de leurs frais (portail parent, lien public, API), selon les
paramètres financiers de l'établissement."""
from decimal import Decimal

from .models import ParametresFinances


def motif_blocage_bulletin(inscription):
    """Message expliquant pourquoi le bulletin n'est pas consultable, ou None si l'élève est à jour (ou si le
    blocage n'est pas activé)."""
    from .views.commun import _situations_financieres_en_lot
    params = ParametresFinances.objects.filter(etablissement=inscription.classe.etablissement_id).first()
    if params is None or not params.bloquer_bulletins_impayes:
        return None
    situation = _situations_financieres_en_lot([inscription])[inscription.pk]
    total_du, total_paye = situation['total_du'], situation['total_paye']
    if total_du <= 0:
        return None
    requis = (total_du * Decimal(params.seuil_blocage_pct) / 100).quantize(Decimal('1'))
    if total_paye >= requis:
        return None
    return (f"Bulletin consultable après régularisation des frais de scolarité : reste à payer "
            f"{situation['reste_a_payer']:,.0f} FCFA ({params.seuil_blocage_pct} % du montant dû requis, "
            f"{total_paye:,.0f} FCFA réglés sur {total_du:,.0f}).").replace(',', ' ')
