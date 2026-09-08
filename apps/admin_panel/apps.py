"""
Configuration de l'app Django admin_panel.

Déclare la classe de configuration qui permet à Django d'enregistrer cette app.
"""

from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    """Configuration de l'app admin_panel (back-office, réservée au staff)."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.admin_panel'
