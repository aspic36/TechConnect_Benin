"""Modèles de l'app paiements : journal des webhooks FedaPay.

Le journal ``EvenementWebhook`` garantit l'**idempotence** : un même événement
FedaPay (livré plusieurs fois en cas de retry) n'est traité qu'une seule fois.
Les modèles métier de paiement restent dans ``apps.propositions``.
"""

from django.db import models


class EvenementWebhook(models.Model):
    """Trace d'un événement webhook FedaPay reçu et traité.

    ``reference`` est une clé stable (type d'événement + id de l'entité
    concernée, sinon empreinte du corps) qui empêche le double traitement.
    """

    reference = models.CharField(max_length=128, unique=True)
    type = models.CharField(max_length=64, blank=True)
    donnees = models.JSONField(default=dict, blank=True)
    recu_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Événement webhook'
        verbose_name_plural = 'Événements webhook'
        ordering = ['-recu_le']

    def __str__(self):
        """Représentation lisible : type d'événement et date de réception."""
        return f'{self.type or "événement"} ({self.reference})'