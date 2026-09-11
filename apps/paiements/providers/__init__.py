"""Fournisseur de paiement actif (factory)."""

from django.conf import settings


def get_provider():
    """Retourne une instance du fournisseur de paiement configuré.

    Seul FedaPay est implémenté pour l'instant ; un autre agrégateur
    implémenterait ``PaiementProvider`` (``providers/base.py``).
    """
    if settings.FEDAPAY_SECRET_KEY:
        from .fedapay import FedaPayProvider
        return FedaPayProvider()
    from .base import PaiementProvider

    class _Vide(PaiementProvider):  # pragma: no cover - mode hors config
        def initier_collecte(self, **kw):
            raise NotImplementedError('FEDAPAY_SECRET_KEY non configuré.')
        def verifier_transaction(self, transaction_id):
            raise NotImplementedError('FEDAPAY_SECRET_KEY non configuré.')
        def initier_reversement(self, **kw):
            raise NotImplementedError('FEDAPAY_SECRET_KEY non configuré.')
        def envoyer_reversement(self, payout_id, telephone=None):
            raise NotImplementedError('FEDAPAY_SECRET_KEY non configuré.')
        def verifier_webhook(self, corps, signature):
            raise NotImplementedError('FEDAPAY_SECRET_KEY non configuré.')

    return _Vide()