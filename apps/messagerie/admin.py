from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('mission', 'expediteur', 'lu', 'date_creation')
    list_filter = ('lu',)
    list_select_related = ('mission', 'expediteur')