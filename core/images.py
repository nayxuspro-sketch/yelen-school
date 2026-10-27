"""
core/images.py — Images apposées sur les documents (signatures scannées, cachets)
================================================================================
Quelle que soit la taille du fichier envoyé (photo de téléphone, scan à 600 dpi), l'image enregistrée est
ramenée à une définition suffisante pour l'impression et ré-encodée : les documents PDF restent légers et
l'utilisateur n'a aucune réduction à faire lui-même.
"""

import os
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

COTE_MAX = 800   # px — ≈ 68 mm à 300 dpi, au-delà des 45 mm d'une signature ou d'un cachet imprimés
QUALITE_JPEG = 85


def optimiser_image_document(fichier, cote_max=COTE_MAX):
    """Retourne un ContentFile prêt à être affecté à un ImageField : orientation EXIF appliquée, côté le plus
    long ramené à `cote_max` px (jamais agrandi), PNG si l'image a de la transparence, JPEG sinon."""
    fichier.seek(0)
    image = ImageOps.exif_transpose(Image.open(fichier))
    image.thumbnail((cote_max, cote_max), Image.LANCZOS)
    transparente = image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)
    tampon = BytesIO()
    if transparente:
        image.convert('RGBA').save(tampon, format='PNG', optimize=True)
        extension = '.png'
    else:
        image.convert('RGB').save(tampon, format='JPEG', quality=QUALITE_JPEG, optimize=True)
        extension = '.jpg'
    nom = os.path.splitext(os.path.basename(fichier.name))[0] + extension
    return ContentFile(tampon.getvalue(), name=nom)
