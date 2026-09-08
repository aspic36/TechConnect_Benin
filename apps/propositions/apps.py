"""
Configuration de l'app Django propositions.

Déclare la classe de configuration qui permet à Django d'enregistrer cette app.
"""

from django.apps import AppConfig


class PropositionsConfig(AppConfig):
    """Configuration de l'app propositions (cycle de vie des missions)."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.propositions'
