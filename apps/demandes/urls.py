"""URLs de l'app demandes : routes vers les vues de gestion des demandes."""

from django.urls import path

from . import views

# Namespace pour les reverse() et {% url %}
app_name = 'demandes'

urlpatterns = [
    # Création d'une demande (client uniquement)
    path('publier/', views.creation_demande, name='creation_demande'),
    # Liste des demandes du client connecté
    path('mes-demandes/', views.mes_demandes, name='mes_demandes'),
    # Catalogue public des demandes validées (prestataires)
    path('catalogue/', views.catalogue, name='catalogue'),
    # Détail d'une demande (contrôle d'accès propriétaire / prestataire)
    path('demande/<int:pk>/', views.detail_demande, name='detail_demande'),
]