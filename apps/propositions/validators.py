"""
Module de validateurs pour l'application propositions.

Fournit les validateurs appliqués aux pièces jointes des litiges
(extensions autorisées + taille maximale de 5 Mo).
"""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Taille maximale d'une pièce jointe : 5 Mo (en octets)
TAILLE_MAX_PIECE_OCTETS = 5 * 1024 * 1024

# Pièces justificatives acceptées : documents PDF et images courantes
EXTENSIONS_PIECE = FileExtensionValidator(
    allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp']
)


def valider_taille_piece(pièce):
    """Vérifie que le fichier joint ne dépasse pas la taille maximale (5 Mo)."""
    if pièce and getattr(pièce, 'size', 0) > TAILLE_MAX_PIECE_OCTETS:
        raise ValidationError('La pièce jointe ne doit pas dépasser 5 Mo.')