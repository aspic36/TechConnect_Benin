"""
Context processors globaux du projet TechConnect Bénin.

Le compteur de notifications non lues est injecté dans tous les templates
afin d'afficher la cloche de notification avec sa pastille dans le header.
"""

from .models import Notification


def notifications_globales(request):
    """Renvoie le nombre de notifications non lues de l'utilisateur connecté."""
    if request.user.is_authenticated:
        return {
            'nb_notifications': Notification.objects.filter(
                destinataire=request.user, est_lue=False
            ).count(),
        }
    return {'nb_notifications': 0}