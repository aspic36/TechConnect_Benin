from django.urls import path

from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('prestataires/', views.liste_prestataires, name='prestataires'),
    path('prestataires/<int:pk>/verifier/', views.verifier_prestataire, name='verifier'),
]