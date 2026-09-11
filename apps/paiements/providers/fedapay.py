"""Implémentation FedaPay (agrégateur Mobile Money Bénin).

Contrats API vérifiés en sandbox le 11/09/2026 (clés de test) :
- ``POST /transactions``        → ``{"v1/transaction": {id, reference, status,
                                  payment_url, payment_token, custom_metadata…}}``
- ``POST /transactions/{id}/token`` → ``{"token": …, "url": …}``
- ``GET  /transactions/{id}``    → ``{"v1/transaction": {…, status…}}``
- ``POST /payouts``              → ``{"v1/payout": {…}}`` (permission requise)
- ``POST /payouts/start``        → envoie les reversements listés

Comportements constatés sur ce compte sandbox : le paiement « sans redirection »
(``POST /mtn_open``…) et les reversements répondent « Opération non autorisée »
tant que la capacité n'est pas activée sur le compte marchand. On utilise donc
la REDIRECTION (``payment_url``) pour la collecte, sans permission spéciale.

Authentification : ``Authorization: Bearer <clé secrète>``.
"""

import hashlib
import hmac
import time

import requests

from django.conf import settings

from .base import PaiementProvider, ResultatCollecte, ResultatReversement


class ErreurFedaPay(Exception):
    """Erreur d'appel à l'API FedaPay."""


class PaiementNonAutorise(ErreurFedaPay):
    """Capacité non activée sur le compte marchand (ex. reversement)."""


class WebhookInvalide(ValueError):
    """Signature ou donnée de webhook FedaPay invalide."""


class FedaPayProvider(PaiementProvider):
    """Client REST minimal de l'API FedaPay (v1)."""

    def __init__(self):
        self.secret_key = settings.FEDAPAY_SECRET_KEY
        self.base_url = settings.FEDAPAY_BASE_URL
        self.webhook_secret = settings.FEDAPAY_WEBHOOK_SECRET
        self.timeout = 20

    # ------------------------------------------------------------------
    # Requêtes de base
    # ------------------------------------------------------------------
    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _post(self, chemin: str, payload: dict) -> dict:
        try:
            reponse = requests.post(
                self.base_url + chemin, json=payload,
                headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise ErreurFedaPay(f'FedaPay injoignable ({chemin}) : {exc}') from exc
        return self._traiter(reponse, chemin)

    def _get(self, chemin: str) -> dict:
        try:
            reponse = requests.get(
                self.base_url + chemin,
                headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise ErreurFedaPay(f'FedaPay injoignable ({chemin}) : {exc}') from exc
        return self._traiter(reponse, chemin)

    def _traiter(self, reponse, chemin: str) -> dict:
        try:
            data = reponse.json()
        except ValueError as exc:
            raise ErreurFedaPay(
                f'Réponse FedaPay illisible ({chemin}, HTTP {reponse.status_code}).') from exc
        # Le compte marchand n'a pas la permission demandée.
        if isinstance(data, dict) and data.get('message') == 'Opération non autorisée':
            raise PaiementNonAutorise(data.get('message', ''))
        if reponse.status_code >= 400:
            raise ErreurFedaPay(
                f'FedaPay HTTP {reponse.status_code} ({chemin}) : {data}')
        return data

    @staticmethod
    def _ressource(data: dict, nom: str) -> dict:
        """Extrait la ressource nourricière ``v1/<nom>``, sinon la donnée brute."""
        return data.get(f'v1/{nom}', data)

    # ------------------------------------------------------------------
    # Interface PaiementProvider
    # ------------------------------------------------------------------
    def initier_collecte(self, *, montant: int, description: str,
                         email: str, telephone: str, callback_url: str,
                         reference: str, mode: str | None = None) -> ResultatCollecte:
        payload = {
            'description': description,
            'amount': int(montant),
            'currency': {'iso': 'XOF'},
            'callback_url': callback_url,
            'customer': {
                'email': email,
                'phone_number': {'number': telephone, 'country': 'bj'},
            },
            'custom_metadata': {'reference_plateforme': reference},
        }
        if mode:
            payload['mode'] = mode
        data = self._traiter(
            requests.post(self.base_url + '/transactions', json=payload,
                          headers=self._headers(), timeout=self.timeout),
            '/transactions')
        txn = self._ressource(data, 'transaction')
        return ResultatCollecte(
            transaction_id=str(txn['id']),
            reference=txn.get('reference', ''),
            url=txn.get('payment_url', ''),   # page de paiement FedaPay
            statut=txn.get('status', 'pending'),
        )

    def verifier_transaction(self, transaction_id: str) -> str:
        data = self._get(f'/transactions/{transaction_id}')
        return self._ressource(data, 'transaction').get('status', '')

    def initier_reversement(self, *, montant: int, prenom: str, nom: str,
                            email: str, telephone: str,
                            reference: str, mode: str = 'mtn_open') -> ResultatReversement:
        payload = {
            'amount': int(montant),
            'currency': {'iso': 'XOF'},
            'mode': mode,
            'description': f'Reversement mission {reference}',
            'merchant_reference': reference,
            'customer': {
                'firstname': prenom,
                'lastname': nom,
                'email': email,
                'phone_number': {'number': telephone, 'country': 'bj'},
            },
            'custom_metadata': {'reference_plateforme': reference},
        }
        data = self._post('/payouts', payload)
        payout = self._ressource(data, 'payout')
        return ResultatReversement(
            payout_id=str(payout['id']),
            reference=payout.get('reference', ''),
            statut=payout.get('status', 'pending'),
        )

    def envoyer_reversement(self, payout_id: str,
                            telephone: str | None = None) -> str:
        item = {'id': int(payout_id)}
        if telephone:
            item['phone_number'] = {'number': telephone, 'country': 'bj'}
        data = self._post('/payouts/start', {'payouts': [item]})
        # Réponse documentée : liste des reversements ; on renvoie le statut
        # du premier élément du tableau retourné.
        envois = data.get('payouts') or data.get('v1/payouts') or []
        if envois:
            return envois[0].get('status') or envois[0].get('statut', '')
        return 'pending'

    def verifier_webhook(self, corps: bytes, signature: str) -> dict:
        if not self.webhook_secret:
            raise WebhookInvalide('FEDAPAY_WEBHOOK_SECRET non configuré.')
        # Signature au format ``t=<timestamp>,v1=<hmac sha256 hex>``
        # (même schéma que le SDK officiel FedaPay).
        champs = dict(item.split('=', 1) for item in signature.split(',') if '=' in item)
        horodatage, empreinte = champs.get('t'), champs.get('v1')
        if not horodatage or not empreinte:
            raise WebhookInvalide('Signature mal formée.')
        if abs(time.time() - float(horodatage)) > 300:
            raise WebhookInvalide('Webhook trop ancien.')
        attendu = hmac.new(
            self.webhook_secret.encode(),
            f'{horodatage}.{corps.decode("utf-8")}'.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(attendu, empreinte):
            raise WebhookInvalide('Signature FedaPay invalide.')
        import json
        return json.loads(corps.decode('utf-8'))