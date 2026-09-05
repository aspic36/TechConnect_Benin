from django.conf import settings
from django.db import models


class Message(models.Model):
    mission = models.ForeignKey('propositions.Mission', on_delete=models.CASCADE, related_name='messages')
    expediteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages_envoyes')
    contenu = models.TextField()
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message'
        ordering = ['date_creation']

    def __str__(self):
        return f"{self.expediteur.username}: {self.contenu[:50]}"