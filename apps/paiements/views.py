"""Vues de l'app paiements (callback FedaPay)."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def retour_paiement(request):
    """Page de retour après le paiement FedaPay (redirection du navigateur).

    Indique à l'utilisateur que le paiement est en cours de vérification et
    l'invite à consulter la page de la mission. Le statut réel du paiement
    sera confirmé par le webhook FedaPay (P3) ou la vérification manuelle.
    """
    return render(request, 'paiements/retour.html')