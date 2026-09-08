"""URLs de l'app messagerie : route vers le fil de messages d'une mission."""

from django.urls import path

from . import views

# Namespace pour les reverse() et {% url %}
app_name = 'messagerie'

urlpatterns = [
    # Fil de messages pour une mission donnée (accès restreint aux 2 parties)
    path('mission/<int:pk>/', views.fil_mission, name='fil'),
]