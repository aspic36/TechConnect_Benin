"""Modèle de messagerie : échange de messages entre client et prestataire autour d'une mission."""

from django.conf import settings
from django.db import models


class Message(models.Model):
    """Message échangé entre les deux parties (client / prestataire) d'une mission."""

    mission = models.ForeignKey('propositions.Mission', on_delete=models.CASCADE, related_name='messages')
    expediteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages_envoyes')
    contenu = models.TextField()
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message'
        # Les messages s'affichent dans l'ordre chronologique (plus ancien en premier)
        ordering = ['date_creation']

    def __str__(self):
        return f"{self.expediteur.username}: {self.contenu[:50]}"