import base64
import io

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _build_qr_data_uri(text: str, box_size: int) -> str:
    """Génère un QR code PNG encodé en base64 data URI."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{b64}'


@register.simple_tag
def qr_etablissement(etab_nom, adresse='', ville='', telephone='', taille='grand'):
    """QR code unique représentant l'établissement."""
    lines = [f"ETB: {etab_nom}"]
    if ville:
        lines.append(f"VIL: {ville}")
    if telephone:
        lines.append(f"TEL: {telephone}")
    if adresse:
        lines.append(f"ADR: {adresse}")
    text = "\n".join(lines)
    box_size = 4 if taille == 'grand' else 2
    px = 80 if taille == 'grand' else 40
    uri = _build_qr_data_uri(text, box_size)
    return mark_safe(
        f'<img src="{uri}" width="{px}" height="{px}" alt="QR {etab_nom}" '
        f'style="display:block; image-rendering:pixelated;">'
    )


def _build_qr_text(matricule, nom, prenom, etab_nom, adresse='', ville='', telephone=''):
    lines = [
        f"MAT: {matricule}",
        f"NOM: {str(nom).upper()} {prenom}",
        f"ETB: {etab_nom}",
    ]
    if adresse:
        lines.append(f"ADR: {adresse}")
    if ville:
        lines.append(f"VIL: {ville}")
    if telephone:
        lines.append(f"TEL: {telephone}")
    return "\n".join(lines)


@register.simple_tag
def qr_eleve(matricule, nom, prenom, etab_nom, taille='petit', adresse='', ville='', telephone=''):
    """
    Génère un QR code embarqué pour un élève.
    taille : 'petit' (40px, pour listes) ou 'grand' (80px, pour certificat/reçu)
    """
    text = _build_qr_text(matricule, nom, prenom, etab_nom, adresse, ville, telephone)
    box_size = 2 if taille == 'petit' else 4
    px = 40 if taille == 'petit' else 80
    uri = _build_qr_data_uri(text, box_size)
    return mark_safe(
        f'<img src="{uri}" width="{px}" height="{px}" alt="QR {matricule}" '
        f'style="display:block; image-rendering:pixelated;">'
    )


@register.simple_tag
def qr_personnel(matricule, nom, prenom, etab_nom, taille='petit', adresse='', ville='', telephone=''):
    """
    Génère un QR code embarqué pour un membre du personnel.
    taille : 'petit' (40px, pour listes) ou 'grand' (80px, standalone)
    """
    text = _build_qr_text(matricule, nom, prenom, etab_nom, adresse, ville, telephone)
    box_size = 2 if taille == 'petit' else 4
    px = 40 if taille == 'petit' else 80
    uri = _build_qr_data_uri(text, box_size)
    return mark_safe(
        f'<img src="{uri}" width="{px}" height="{px}" alt="QR {matricule}" '
        f'style="display:block; image-rendering:pixelated;">'
    )
