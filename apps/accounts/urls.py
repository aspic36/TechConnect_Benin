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
    path('abonnement/', views.abonnement, name='abonnement'),
    path('cgu/', views.cgu, name='cgu'),
]
