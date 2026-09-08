"""Configuration de l'application messagerie."""

from django.apps import AppConfig


class MessagerieConfig(AppConfig):
    """Config de l'app messagerie : messagerie privée par mission entre client et prestataire."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.messagerie'
