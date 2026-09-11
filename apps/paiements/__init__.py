"""Application « paiements » : intégration Mobile Money (FedaPay).

Isolation technique du fournisseur de paiement derrière une interface commune
(``providers/base.py``) pour pouvoir changer d'agrégateur sans toucher au
métier : collecte (client → plateforme, escrow) et reversement (plateforme →
prestataire, commission 5 % retenue).
"""