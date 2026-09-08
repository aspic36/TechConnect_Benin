"""
Module de validateurs pour l'application accounts.

Fournit les fonctions et objets de validation appliques aux fichiers
télécharges (avatar) : restriction des extensions autorisees et controle
de la taille maximale du fichier.
"""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Taille maximale d'un avatar : 5 Mo (en octets)
TAILLE_MAX_AVATAR_OCTETS = 5 * 1024 * 1024

# Validateur d'extension : n'autorise que les formats image courants
EXTENSIONS_AVATAR = FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])


def valider_taille_avatar(avatar):
    """Verifie que le fichier avatar ne depasse pas la taille maximale.

    Levalidateur est appele automatiquement par le champ ``ImageField``
    du modele ``User``.

    :raises ValidationError: si la taille du fichier depasse 5 Mo.
    """
    if avatar and getattr(avatar, 'size', 0) > TAILLE_MAX_AVATAR_OCTETS:
        raise ValidationError('L\'image ne doit pas dépasser 5 Mo.')
