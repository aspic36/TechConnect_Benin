"""Configuration de l'application demandes."""

from django.apps import AppConfig


class DemandesConfig(AppConfig):
    """Config de l'app demandes : gestion des catégories et demandes de services."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.demandes'
