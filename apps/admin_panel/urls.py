"""
Routes URL du back-office (admin_panel).

Mappe chaque URL aux vues de gestion du tableau de bord, des prestataires,
de la modération des demandes et de la clôture des litiges.
"""

from django.urls import path

from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('prestataires/', views.liste_prestataires, name='prestataires'),
    path('prestataires/<int:pk>/verifier/', views.verifier_prestataire, name='verifier'),
    path('demandes/', views.liste_demandes, name='demandes'),
    path('demandes/<int:pk>/valider/', views.valider_demande, name='valider_demande'),
    path('demandes/<int:pk>/supprimer/', views.refuser_demande, name='refuser_demande'),
    path('litiges/', views.liste_litiges, name='litiges'),
    path('litiges/<int:pk>/clore/', views.clore_litige, name='clore_litige'),
    path('commissions/', views.liste_commissions, name='commissions'),
    path('commissions/<int:pk>/confirmer/', views.confirmer_commission, name='confirmer_commission'),
    path('commissions/<int:pk>/prolonger/', views.prolonger_commission, name='prolonger_commission'),
    path('prestataires/<int:pk>/suspendre/', views.suspendre_prestataire, name='suspendre'),
    path('prestataires/<int:pk>/bannir/', views.bannir_prestataire, name='bannir'),
    path('prestataires/<int:pk>/reactiver/', views.reactiver_prestataire, name='reactiver'),
]