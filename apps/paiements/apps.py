"""Configuration de l'app paiements (intégration Mobile Money)."""

from django.apps import AppConfig


class PaiementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.paiements'
    verbose_name = 'Paiements (Mobile Money)'