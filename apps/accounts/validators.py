from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

TAILLE_MAX_AVATAR_OCTETS = 5 * 1024 * 1024

EXTENSIONS_AVATAR = FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])


def valider_taille_avatar(avatar):
    if avatar and getattr(avatar, 'size', 0) > TAILLE_MAX_AVATAR_OCTETS:
        raise ValidationError('L\'image ne doit pas dépasser 5 Mo.')