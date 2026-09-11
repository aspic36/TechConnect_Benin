"""Tests du fournisseur de paiement FedaPay (API mockée, pas de réseau)."""

import hashlib
import hmac
import json
import re
import time
from unittest.mock import patch

from django.test import TestCase, override_settings

from .providers import get_provider
from .providers.fedapay import (
    ErreurFedaPay,
    FedaPayProvider,
    PaiementNonAutorise,
    WebhookInvalide,
)

BASE = 'https://sandbox-api.fedapay.com/v1'


class _Reponse:
    """Objet de réponse HTTP minimal."""

    def __init__(self, donnee, status_code=200):
        self._donnee = donnee
        self.status_code = status_code

    def json(self):
        return self._donnee


@override_settings(FEDAPAY_SECRET_KEY='sk_sandbox_test',
                   FEDAPAY_BASE_URL=BASE, FEDAPAY_WEBHOOK_SECRET='wh_secret_test')
class FedaPayProviderTests(TestCase):

    def _provider(self):
        return FedaPayProvider()

    def test_initier_collecte_parse_la_transaction(self):
        reponse = _Reponse({'v1/transaction': {
            'id': 42, 'reference': 'trx_abc',
            'status': 'pending',
            'payment_url': 'https://sandbox-process.fedapay.com/xyz',
        }})
        with patch('requests.post', return_value=reponse) as mock_post:
            resultat = self._provider().initier_collecte(
                montant=2500, description='Mission', email='c@t.bj',
                telephone='+22966000001',
                callback_url='https://example.com/webhooks/fedapay/',
                reference='M-1',
            )
        self.assertEqual(resultat.transaction_id, '42')
        self.assertEqual(resultat.reference, 'trx_abc')
        self.assertEqual(resultat.url, 'https://sandbox-process.fedapay.com/xyz')
        self.assertEqual(resultat.statut, 'pending')
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['amount'], 2500)
        self.assertEqual(payload['currency'], {'iso': 'XOF'})
        self.assertEqual(payload['customer']['phone_number'],
                         {'number': '+22966000001', 'country': 'bj'})
        self.assertEqual(payload['custom_metadata'],
                         {'reference_plateforme': 'M-1'})

    def test_verifier_transaction_retourne_statut(self):
        reponse = _Reponse({'v1/transaction': {'id': 42, 'status': 'approved'}})
        with patch('requests.get', return_value=reponse):
            statut = self._provider().verifier_transaction('42')
        self.assertEqual(statut, 'approved')

    def test_initier_reversement_parse_le_payout(self):
        reponse = _Reponse({'v1/payout': {
            'id': 7, 'reference': 'pout_123', 'status': 'pending',
        }})
        with patch('requests.post', return_value=reponse) as mock_post:
            resultat = self._provider().initier_reversement(
                montant=2375, prenom='Yves', nom='Demo',
                email='y@t.bj', telephone='+22996000001', reference='M-1',
            )
        self.assertEqual(resultat.payout_id, '7')
        self.assertEqual(resultat.reference, 'pout_123')
        self.assertEqual(resultat.statut, 'pending')
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['merchant_reference'], 'M-1')

    def test_operation_non_autorisee_leve_exception_metier(self):
        reponse = _Reponse({'message': 'Opération non autorisée',
                            'errors': {}, 'model': None})
        with patch('requests.post', return_value=reponse):
            with self.assertRaises(PaiementNonAutorise):
                self._provider().initier_reversement(
                    montant=2375, prenom='Yves', nom='Demo',
                    email='y@t.bj', telephone='+22996000001', reference='M-1')

    def test_erreur_http_leve_erreurfedapay(self):
        reponse = _Reponse({'message': 'nope'}, status_code=400)
        with patch('requests.post', return_value=reponse):
            with self.assertRaises(ErreurFedaPay):
                self._provider().initier_collecte(
                    montant=1, description='m', email='e@t.bj',
                    telephone='+22966000001', callback_url='x', reference='r')

    # ---- Webhooks ----

    def _signer(self, corps_bytes, secret='wh_secret_test', horodatage=None):
        if horodatage is None:
            horodatage = str(int(time.time()))
        empreinte = hmac.new(
            secret.encode(), f'{horodatage}.{corps_bytes.decode()}'.encode(),
            hashlib.sha256).hexdigest()
        return f't={horodatage},v1={empreinte}'

    def test_webhook_signature_valide_retourne_evenement(self):
        evenement = {'name': 'transaction.approved',
                     'transaction': {'id': 42, 'reference': 'trx_abc'}}
        corps = json.dumps(evenement).encode()
        signature = self._signer(corps)
        with patch('requests.get'):
            resultat = self._provider().verifier_webhook(corps, signature)
        self.assertEqual(resultat['name'], 'transaction.approved')

    def test_webhook_signature_invalide_rejetee(self):
        corps = json.dumps({'name': 'transaction.approved'}).encode()
        signature = 't=1234567890,v1=invalide'
        with self.assertRaises(WebhookInvalide):
            self._provider().verifier_webhook(corps, signature)

    def test_webhook_trop_ancien_rejete(self):
        corps = json.dumps({'name': 'transaction.approved'}).encode()
        signature = self._signer(corps, horodatage='1500000000')
        with self.assertRaises(WebhookInvalide):
            self._provider().verifier_webhook(corps, signature)

    def test_webhook_sans_secret_config_rejete(self):
        # On surcharge en retirant le secret webhook.
        provider = FedaPayProvider()
        provider.webhook_secret = ''
        with self.assertRaises(WebhookInvalide):
            provider.verifier_webhook(b'{}', 't=1,v1=x')


class FactoryTests(TestCase):

    @override_settings(FEDAPAY_SECRET_KEY='sk_sandbox_test')
    def test_avec_secret_retourne_fedapay(self):
        self.assertIsInstance(get_provider(), FedaPayProvider)

    def test_provider_vide_leve_not_implemented(self):
        # sans FEDAPAY_SECRET_KEY, le provider de secours signale la config.
        with override_settings(FEDAPAY_SECRET_KEY=''):
            providers = get_provider()
            with self.assertRaisesRegex(NotImplementedError, re.escape('FEDAPAY_SECRET_KEY')):
                providers.initier_collecte(
                    montant=1, description='m', email='e', telephone='+2296',
                    callback_url='x', reference='r')