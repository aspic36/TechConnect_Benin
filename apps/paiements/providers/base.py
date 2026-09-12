"""Interface commune aux fournisseurs de paiement Mobile Money.

L'application métier ne connaît que cette abstraction : chaque agrégateur
(FedaPay aujourd'hui, un autre demain) implémente ces méthodes. Les montants
sont exprimés en FCFA (entiers) et les numéros de téléphone au format
international ``+229XXXXXXXX``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ResultatCollecte:
    """Résultat d'une initiation de collecte côté agrégateur."""
    transaction_id: str
    reference: str
    url: str          # page de paiement sécurisée de l'agrégateur
    statut: str       # 'pending', 'approved', ...


@dataclass
class ResultatReversement:
    """Résultat d'une création de reversement (payout)."""
    payout_id: str
    reference: str
    statut: str       # 'pending', 'started', 'sent', 'failed', ...


class PaiementProvider(ABC):

    @abstractmethod
    def initier_collecte(self, *, montant: int, description: str,
                         email: str, telephone: str, callback_url: str,
                         reference: str, mode: str | None = None,
                         prenom: str = '', nom: str = '') -> ResultatCollecte:
        """Crée une transaction de collecte et retourne le lien de paiement."""

    @abstractmethod
    def verifier_transaction(self, transaction_id: str) -> str:
        """Retourne le statut FedaPay d'une transaction ('pending', 'approved'…)."""

    @abstractmethod
    def initier_reversement(self, *, montant: int, prenom: str, nom: str,
                            email: str, telephone: str,
                            reference: str, mode: str = 'mtn_open') -> ResultatReversement:
        """Crée un reversement (payout) vers le prestataire, sans l'envoyer."""

    @abstractmethod
    def envoyer_reversement(self, payout_id: str,
                            telephone: str | None = None) -> str:
        """Déclenche l'envoi d'un reversement créé ; retourne son statut."""

    @abstractmethod
    def verifier_webhook(self, corps: bytes, signature: str) -> dict:
        """Vérifie l'authenticité d'un webhook et retourne l'événement parsé."""