"""Configuration de l'administration Django pour le modèle Message."""

from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Administration des messages avec filtrage par état de lecture."""

    list_display = ('mission', 'expediteur', 'lu', 'date_creation')
    list_filter = ('lu',)
    # Jointure optimisée sur mission et expéditeur
    list_select_related = ('mission', 'expediteur')