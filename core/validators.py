"""
core/validators.py — Validateurs de fichiers partagés
=======================================================
Fournit une validation robuste des uploads d'images :
  1. Taille maximale
  2. Extension autorisée
  3. Vérification du contenu réel via Pillow (protection contre le spoofing MIME)
"""

import os

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Formats Pillow acceptés (format interne Pillow, pas MIME)
_ALLOWED_PILLOW_FORMATS = {'JPEG', 'PNG', 'GIF', 'WEBP'}
_ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

# Tailles par défaut
DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024    # 5 Mo (signatures et cachets compris : allégés ensuite par core.images)


def validate_image_upload(file, max_size_bytes=DEFAULT_MAX_IMAGE_BYTES):
    """
    Valide qu'un fichier uploadé est une vraie image.

    Vérifie :
    - La taille ne dépasse pas max_size_bytes
    - L'extension est parmi .jpg/.jpeg/.png/.gif/.webp
    - Le contenu est un fichier image réel (via Pillow — résiste au spoofing
      du champ content_type envoyé par le navigateur)

    À utiliser dans les méthodes clean_<field>() des ModelForms.
    """
    if not file:
        return

    # 1. Vérification de la taille
    if file.size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(
            _("L'image est trop volumineuse. Taille maximale : %(max)s Mo."),
            params={'max': f'{max_mb:.1f}'},
        )

    # 2. Vérification de l'extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValidationError(
            _("Format non autorisé (%(ext)s). Utilisez : %(allowed)s."),
            params={
                'ext': ext or _('aucune extension'),
                'allowed': ', '.join(sorted(_ALLOWED_EXTENSIONS)),
            },
        )

    # 3. Vérification du contenu réel via Pillow
    try:
        from PIL import Image
        file.seek(0)
        img = Image.open(file)
        img_format = img.format  # lit uniquement l'en-tête (lazy)
        file.seek(0)             # reset pour les lectures suivantes
        if img_format not in _ALLOWED_PILLOW_FORMATS:
            raise ValidationError(
                _("Contenu d'image non reconnu (%(fmt)s). "
                  "Utilisez JPEG, PNG, GIF ou WebP."),
                params={'fmt': img_format or _('inconnu')},
            )
    except ValidationError:
        raise
    except Exception:
        raise ValidationError(
            _("Fichier image invalide ou corrompu. "
              "Assurez-vous que le fichier est une image JPEG, PNG, GIF ou WebP.")
        )


_EXTENSIONS_PIECE_JOINTE = {'.pdf', '.jpg', '.jpeg', '.png'}


def validate_piece_jointe(file, max_size_bytes=DEFAULT_MAX_IMAGE_BYTES):
    """Pièce jointe déposée par un tiers (justificatif d'absence) : PDF ou image JPEG / PNG, 5 Mo au plus, dont le
    contenu réel correspond à l'extension annoncée."""
    if not file:
        return
    if file.size > max_size_bytes:
        raise ValidationError(_("Le fichier est trop volumineux. Taille maximale : %(max)s Mo."),
                              params={'max': f'{max_size_bytes / (1024 * 1024):.0f}'})
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in _EXTENSIONS_PIECE_JOINTE:
        raise ValidationError(_("Format non autorisé (%(ext)s). Utilisez : PDF, JPG ou PNG."),
                              params={'ext': ext or _('aucune extension')})
    if ext == '.pdf':
        file.seek(0)
        entete = file.read(5)
        file.seek(0)
        if entete != b'%PDF-':
            raise ValidationError(_("Le fichier n'est pas un PDF valide."))
        return
    validate_image_upload(file, max_size_bytes)
