"""Vues de l'app paiements (callback retours navigateur + webhook FedaPay)."""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import services
from .providers import get_provider
from .providers.fedapay import WebhookInvalide

logger = logging.getLogger(__name__)


@login_required
def retour_paiement(request):
    """Page de retour après le paiement FedaPay (redirection du navigateur).

    Indique à l'utilisateur que le paiement est en cours de vérification et
    l'invite à consulter la page de la mission. Le statut réel du paiement
    est confirmé par le webhook FedaPay ou la vérification manuelle.
    """
    return render(request, 'paiements/retour.html')


@csrf_exempt
@require_POST
def webhook_fedapay(request):
    """Endpoint webhook FedaPay (aucun login : appelé par l'agrégateur).

    Vérifie la signature ``X-FEDAPAY-SIGNATURE``, traite l'événement de façon
    idempotente et répond 200 à FedaPay (même si l'événement est inconnu,
    pour éviter les renvois inutiles).
    """
    signature = request.headers.get('X-FEDAPAY-SIGNATURE', '')
    try:
        evenement = get_provider().verifier_webhook(request.body, signature)
    except WebhookInvalide:
        return JsonResponse({'erreur': 'signature invalide'}, status=400)
    except NotImplementedError:
        return JsonResponse({'erreur': 'webhook non configuré'}, status=503)
    try:
        statut = services.traiter_webhook(evenement)
    except Exception as exc:  # pragma: no cover - erreur inattendue
        logger.exception('Échec du traitement du webhook FedaPay : %s', exc)
        return JsonResponse({'erreur': 'traitement échoué'}, status=500)
    return JsonResponse({'statut': statut})