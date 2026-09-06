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
]