"""
Module d'URLs pour l'application accounts.

Definit les routes associees aux vues d'authentification, de gestion
de profil et de la page d'accueil.  Le namespace ``accounts`` est
declare via ``app_name``.
"""

from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('inscription/', views.inscription, name='inscription'),
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('profil/portfolio/', views.gestion_portfolio, name='portfolio'),
    path('profil/portfolio/<int:pk>/supprimer/', views.supprimer_projet, name='supprimer_projet'),
    path('prestataires/<int:pk>/', views.profil_prestataire, name='profil_prestataire'),
    path('abonnement/', views.abonnement, name='abonnement'),
    path('notifications/', views.mes_notifications, name='notifications'),
    path('notifications/marquer-lues/', views.marquer_lues, name='marquer_lues'),
    path('cgu/', views.cgu, name='cgu'),
]
