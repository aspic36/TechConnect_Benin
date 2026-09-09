"""
Module de modèles pour l'application accounts.

Definit le modele Utilisateur personnalise (User) etabli sur AbstractUser,
avec les champs supplementaires propres a TechConnect Benin (role, telephone,
societe, ville, biographie, avatar, statut de verification) ainsi que les
abonnements prestataires (Abonnement) et la logique de quotas de propositions.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .validators import EXTENSIONS_AVATAR, valider_taille_avatar


class User(AbstractUser):
    """Modele Utilisateur personnalise pour TechConnect Benin.

    Etend AbstractUser avec un champ ``role`` (client / prestataire) et des
    informations de profil (telephone, societe, ville, bio, avatar, plan).
    """

    class Role(models.TextChoices):
        """Choices possibles pour le champ ``role``."""
        CLIENT = 'client', 'Client'
        PRESTATAIRE = 'prestataire', 'Prestataire'

    class Plan(models.TextChoices):
        """Plans d'abonnement des prestataires (freemium)."""
        GRATUIT = 'gratuit', 'Gratuit'
        STANDARD = 'standard', 'Standard'
        PRO = 'pro', 'Pro'

    # --- Champs de profil TechConnect ---
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    # Avatar avec validation d'extension et de taille (max 5 Mo)
    avatar = models.ImageField(
        upload_to='avatars/', blank=True, null=True,
        validators=[EXTENSIONS_AVATAR, valider_taille_avatar],
    )
    is_verified = models.BooleanField(default=False)
    # Sanctions économiques : un prestataire suspendu ne peut plus utiliser la
    # plateforme tant qu'il n'a pas réglé sa commission. Le bannissement (= is_active
    # à False) bloque définitivement la connexion.
    suspendu = models.BooleanField(default=False)
    date_suspension = models.DateTimeField(null=True, blank=True)
    # Abonnement prestataire : plan en cours + période couverte par le paiement.
    # Le plan effectivement appliqué dépend de la validité de date_fin_plan.
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.GRATUIT)
    date_debut_plan = models.DateTimeField(null=True, blank=True)
    date_fin_plan = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Representation lisible : ``username (Role)``."""
        return f"{self.username} ({self.get_role_display()})"

    # --- Logique d'abonnement / quotas ---

    def plan_effectif(self):
        """Renvoie le plan réellement applicable au prestataire.

        Un plan payant (Standard/Pro) n'est actif que pendant la période
        couverte (date_fin_plan dans le futur) ; sinon on retombe sur Gratuit.
        """
        if self.plan != self.Plan.GRATUIT and self.date_fin_plan and self.date_fin_plan > timezone.now():
            return self.plan
        return self.Plan.GRATUIT

    def quota_mensuel(self):
        """Nombre de propositions autorisées sur le mois en cours (None = illimité)."""
        from django.conf import settings
        quotas = {
            self.Plan.GRATUIT: settings.PLAN_GRAUIT_PROPOSITIONS,
            self.Plan.STANDARD: settings.PLAN_STANDARD_PROPOSITIONS,
            self.Plan.PRO: None,
        }
        return quotas[self.plan_effectif()]

    def propositions_du_mois(self):
        """Compte les propositions soumises par ce prestataire depuis le 1er du mois."""
        from apps.propositions.models import Proposition
        debut_du_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return Proposition.objects.filter(
            prestataire=self, date_creation__gte=debut_du_mois
        ).count()

    def peut_proposer(self):
        """Tuple (autorise, utilisees, quota) pour l'affichage et le contrôle."""
        quota = self.quota_mensuel()
        utilisees = self.propositions_du_mois()
        if quota is None:
            return True, utilisees, None
        return utilisees < quota, utilisees, quota

    def prochaine_recharge(self):
        """Date du prochain 1er du mois, où le quota se recharge automatiquement."""
        maintenant = timezone.now()
        if maintenant.month == 12:
            return maintenant.replace(year=maintenant.year + 1, month=1, day=1, hour=12)
        return maintenant.replace(month=maintenant.month + 1, day=1, hour=12)


class Abonnement(models.Model):
    """Demande d'abonnement payant d'un prestataire, confirmée par un admin.

    Reproduit le modèle de la commission : le prestataire choisit un plan
    (Standard/Pro) et déclare son paiement, l'administrateur confirme, ce qui
    active la période d'abonnement sur le compte (``User.plan`` + ``date_fin``).
    """

    class Statut(models.TextChoices):
        """État d'une demande d'abonnement : en attente, active ou refusée."""
        EN_ATTENTE = 'en_attente', 'En attente'
        ACTIF = 'actif', 'Actif'
        REFUSE = 'refuse', 'Refusé'

    class Methode(models.TextChoices):
        """Moyen de paiement déclaré par le prestataire (accord direct, à distance)."""
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'
        VIREMENT = 'virement', 'Virement bancaire'

    prestataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='abonnements')
    plan = models.CharField(max_length=20, choices=User.Plan.choices)
    montant = models.DecimalField(max_digits=12, decimal_places=0)
    methode = models.CharField(max_length=20, choices=Methode.choices, blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_demande = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)
    # Date de fin de la période d'abonnement définie à la confirmation.
    date_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Abonnement'
        ordering = ['-date_demande']

    def __str__(self):
        """Représentation lisible : prestataire, plan et montant."""
        return f"{self.prestataire.username} — {self.get_plan_display()} ({self.montant} FCFA)"


class Notification(models.Model):
    """Notification interne affichée via la cloche du site.

    Notifie un utilisateur connecté d'un événement le concernant (abonnement
    confirmé, commission réglée, proposition acceptée…) ou l'équipe staff des
    éléments à traiter (demandes d'abonnement, commissions à confirmer…).
    """

    class Type(models.TextChoices):
        """Domaine métier de la notification (pour l'icône et le regroupement)."""
        ABONNEMENT = 'abonnement', 'Abonnement'
        COMMISSION = 'commission', 'Commission'
        MISSION = 'mission', 'Mission'
        DEMANDE = 'demande', 'Demande'
        SYSTEME = 'systeme', 'Système'

    destinataire = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEME)
    message = models.CharField(max_length=255)
    # Chemin cible (nom de vue ou URL) où l'utilisateur peut réagir.
    lien = models.CharField(max_length=255, blank=True)
    est_lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        ordering = ['-date_creation']

    def __str__(self):
        """Représentation lisible : destinataire et message."""
        return f"{self.destinataire.username}: {self.message}"
