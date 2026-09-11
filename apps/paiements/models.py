"""Modèles de l'app paiements (vides en P0).

Les modèles métier de paiement restent dans ``apps.propositions``
(``Paiement``, ``Commission``) ; ils seront enrichis pour l'escrow en P1
(référence FedaPay, statuts en_cours/paye/echec, log webhooks).
"""