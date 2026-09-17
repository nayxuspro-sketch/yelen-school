"""
licences/pdf_utils.py
=====================
Utilitaires pour filigrane PDF avec info licence (P2).

Injecte licence_info dans le contexte des PDFs pour traçabilité anti-fraude.
Réutilise _get_licence_for_user / _licence_to_dict de api.py pour éviter doublon.
"""

from typing import Optional, Dict


def get_licence_info_for_pdf(user, etablissement=None) -> Optional[Dict]:
    """
    Récupère les infos de licence pour filigrane PDF.

    Args:
        user: User Django (pour récupérer etablissement si etab non fourni)
        etablissement: Etablissement optionnel (prioritaire)

    Returns:
        dict avec type, cle_licence, etablissement_nom, jours_restants, etc. ou None
        Format léger pour filigrane (pas tout _licence_to_dict).
    """
    try:
        # P2 — factorisation : réutilise helper central api.py si dispo
        try:
            from .api import _get_licence_for_user as _get_lic
            if etablissement:
                # etablissement fourni → on bypass _get_lic mais on garde cohérence
                from .models import Licence
                try:
                    licence = etablissement.licence
                    etab = etablissement
                except Licence.DoesNotExist:
                    return None
            else:
                etab, licence = _get_lic(user)
                if not licence:
                    return None
        except ImportError:
            # Fallback si api pas importable (circular)
            from .models import Licence
            etab = etablissement or getattr(user, 'etablissement', None)
            if not etab:
                return None
            try:
                licence = etab.licence
            except Licence.DoesNotExist:
                return None

        # Même si expirée, on affiche l'info pour traçabilité
        return {
            'type': licence.type_licence,
            'type_display': licence.get_type_licence_display(),
            'cle_licence': licence.cle_licence,
            'statut': licence.statut,
            'jours_restants': licence.jours_restants(),
            'etablissement_nom': etab.nom,
            'etablissement_code': getattr(etab, 'code', ''),
            'date_expiration': licence.date_expiration.isoformat() if licence.date_expiration else '',
            'signature_valide': licence.verifier_signature(),
            'est_active': licence.est_active(),
        }
    except Exception:
        return None


def inject_licence_filigrane_context(context: Dict, user, etablissement=None) -> Dict:
    """
    Injecte licence_info dans un contexte de template PDF.

    Usage dans une vue :
        context = {...}
        context = inject_licence_filigrane_context(context, request.user, etab)
    """
    licence_info = get_licence_info_for_pdf(user, etablissement)
    if licence_info:
        context['licence_info'] = licence_info
    return context
