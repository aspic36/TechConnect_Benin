"""
Modèles de l'app propositions.

Définit les entités métier liées au cycle de vie d'une mission :
Proposition (offre d'un prestataire), Mission (travail lancé),
Évaluation (note 1-5) et Paiement (accord direct MVP).
"""

from django.conf import settings
from django.db import models


class Proposition(models.Model):
    """Offre soumise par un prestataire en réponse à une demande d'un client."""

    class Statut(models.TextChoices):
        """Statuts possibles du cycle de vie d'une proposition."""
        ENVOYEE = 'envoyee', 'Envoyée'
        ACCEPTEE = 'acceptee', 'Acceptée'
        REFUSEE = 'refusee', 'Refusée'

    demande = models.ForeignKey('demandes.Demande', on_delete=models.CASCADE, related_name='propositions')
    prestataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='propositions')
    prix = models.DecimalField(max_digits=12, decimal_places=0)
    delais_jours = models.PositiveIntegerField(verbose_name='Délais (jours)')
    message = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ENVOYEE)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Proposition'
        ordering = ['-date_creation']

    def __str__(self):
        """Représentation lisible de la proposition (prestataire → demande)."""
        return f"Proposition {self.prestataire.username} → {self.demande.titre}"


class Mission(models.Model):
    """Travail lancé sur une demande après l'acceptation d'une proposition."""

    class Statut(models.TextChoices):
        """Statuts du cycle de vie d'une mission (de l'en cours au litige)."""
        EN_COURS = 'en_cours', 'En cours'
        TERMINEE = 'terminee', 'Terminée'
        CLOTUREE = 'cloturee', 'Clôturée'
        LITIGE = 'litige', 'Litige'

    demande = models.OneToOneField('demandes.Demande', on_delete=models.CASCADE, related_name='mission')
    proposition = models.OneToOneField(Proposition, on_delete=models.SET_NULL, null=True, related_name='mission')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='missions_client')
    prestataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='missions_prestataire')
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mission'
        ordering = ['-date_creation']

    def __str__(self):
        """Représentation lisible de la mission via le titre de la demande."""
        return f"Mission: {self.demande.titre}"


class Evaluation(models.Model):
    """Avis (note 1-5 et commentaire) laissé par une partie de la mission sur l'autre."""

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='evaluations')
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='evaluations_donnees')
    cible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='evaluations_recues')
    note = models.PositiveSmallIntegerField()
    commentaire = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Évaluation'
        ordering = ['-date_creation']
        # Contrainte métier : la note doit toujours être comprise entre 1 et 5.
        constraints = [
            models.CheckConstraint(check=models.Q(note__gte=1, note__lte=5), name='note_1_5')
        ]

    def __str__(self):
        """Représentation lisible : auteur → cible avec la note sur 5."""
        return f"{self.auteur.username} → {self.cible.username}: {self.note}/5"


class Paiement(models.Model):
    """Enregistrement d'un paiement par le client (accord direct MVP)."""

    class Methode(models.TextChoices):
        """Moyens de paiement acceptés dans le modèle MVP."""
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'
        VIREMENT = 'virement', 'Virement bancaire'
        ESPECES = 'especes', 'Espèces'

    class Statut(models.TextChoices):
        """État du paiement : en attente ou payé."""
        EN_ATTENTE = 'en_attente', 'En attente'
        PAYE = 'paye', 'Payé'

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(max_digits=12, decimal_places=0)
    methode = models.CharField(max_length=20, choices=Methode.choices, default=Methode.ESPECES)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Paiement'
        ordering = ['-date_creation']

    def __str__(self):
        """Représentation lisible : montant en FCFA et titre de la mission."""
        return f"Paiement {self.montant} FCFA — {self.mission.demande.titre}"