"""Routes URL de l'app paiements (callback FedaPay, webhook)."""

from django.urls import path

from . import views

app_name = 'paiements'

urlpatterns = [
    path('retour/', views.retour_paiement, name='retour'),
    path('webhook/', views.webhook_fedapay, name='webhook'),
]