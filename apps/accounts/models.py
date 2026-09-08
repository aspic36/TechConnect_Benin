"""
Module de modèles pour l'application accounts.

Definit le modele Utilisateur personnalise (User) etabli sur AbstractUser,
avec les champs supplementaires propres a TechConnect Benin (role, telephone,
societe, ville, biographie, avatar, statut de verification).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .validators import EXTENSIONS_AVATAR, valider_taille_avatar


class User(AbstractUser):
    """Modele Utilisateur personnalise pour TechConnect Benin.

    Etend AbstractUser avec un champ ``role`` (client / prestataire) et des
    informations de profil (telephone, societe, ville, bio, avatar).
    """

    class Role(models.TextChoices):
        """Choices possibles pour le champ ``role``."""
        CLIENT = 'client', 'Client'
        PRESTATAIRE = 'prestataire', 'Prestataire'

    # --- Champs de profil TechConnect ---
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    # Avatar avec validation d'extension et de taille (max 5 Mo)
    avatar = models.ImageField(
        upload_to='avatars/', blank=True, null=True,
        validators=[EXTENSIONS_AVATAR, valider_taille_avatar],
    )
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        """Representation lisible : ``username (Role)``."""
        return f"{self.username} ({self.get_role_display()})"
