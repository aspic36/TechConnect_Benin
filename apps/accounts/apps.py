"""
Configuration de l'application accounts.

Declare le ``AppConfig`` utilise par Django pour detecter et charger
l'application (nom, champ cle automatique par defaut).
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration de l'application ``accounts``."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
