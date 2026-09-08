"""Modèles de l'app demandes : catégories de services et demandes de clients."""

from django.conf import settings
from django.db import models


class Categorie(models.Model):
    """Catégorie de service informatique (ex. : Développement web, Maintenance)."""

    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'

    def __str__(self):
        return self.nom


class Demande(models.Model):
    """Demande d'un client cherchant un prestataire pour un besoin informatique."""

    class Statut(models.TextChoices):
        """Choix de statut définissant le cycle de vie d'une demande."""
        EN_ATTENTE = 'en_attente', 'En attente de validation'
        EN_COURS = 'en_cours', 'En cours (propositions)'
        MISSION_ACTIVE = 'mission_active', 'Mission en cours'
        CLOTUREE = 'cloturee', 'Clôturée'

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='demandes')
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, related_name='demandes')
    titre = models.CharField(max_length=200)
    description = models.TextField()
    budget_min = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    lieu = models.CharField(max_length=100, blank=True)
    a_distance = models.BooleanField(default=False)
    urgence = models.BooleanField(default=False)
    # Statut par défaut : en_attente (modéré par l'admin avant publication)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Demande'
        # Les demandes les plus récentes apparaissent en premier
        ordering = ['-date_creation']

    def __str__(self):
        return self.titre