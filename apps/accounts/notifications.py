"""
Fonctions utilitaires du système de notifications internes.

Centralise la création de notifications pour un ou plusieurs destinataires,
ainsi que la notification d'alerte envoyée à toute l'équipe staff (pour les
éléments à confirmer : abonnements, commissions, évaluations…).
"""

from .models import Notification, User


def creer_notification(destinataires, message, type, lien=''):
    """Crée une notification pour chaque destinataire du tableau ``destinataires``."""
    for destinataire in destinataires:
        if destinataire is not None:
            Notification.objects.create(
                destinataire=destinataire,
                message=message,
                type=type,
                lien=lien,
            )


def notifier_staff(message, type, lien=''):
    """Alerte toute l'équipe administrative (is_staff) via une notification."""
    creer_notification(
        User.objects.filter(is_staff=True),
        message,
        type,
        lien,
    )