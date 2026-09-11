"""
Enregistrement des modèles de l'app propositions dans l'interface d'administration Django.

Expose Proposition, Mission, Évaluation et Paiement dans le back-office.
"""

from django.contrib import admin

from .models import Commission, Evaluation, Mission, Paiement, Proposition


@admin.register(Proposition)
class PropositionAdmin(admin.ModelAdmin):
    """Administration des propositions : liste, filtres par statut et jointures."""
    list_display = ('demande', 'prestataire', 'prix', 'delais_jours', 'statut', 'date_creation')
    list_filter = ('statut',)
    list_select_related = ('demande', 'prestataire')


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    """Administration des missions : liste, filtres par statut et jointures."""
    list_display = ('demande', 'client', 'prestataire', 'statut', 'date_debut', 'date_fin')
    list_filter = ('statut',)
    list_select_related = ('demande', 'client', 'prestataire')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    """Administration des évaluations : liste des avis avec jointures."""
    list_display = ('mission', 'auteur', 'cible', 'note', 'date_creation')
    list_select_related = ('mission', 'auteur', 'cible')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    """Administration des paiements : liste, filtres par méthode et statut."""
    list_display = ('mission', 'montant', 'methode', 'statut', 'date_creation')
    list_filter = ('methode', 'statut')


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    """Administration des commissions de la plateforme (part de chaque mission)."""
    list_display = ('mission', 'montant', 'statut', 'date_limite', 'date_declaration', 'date_paiement')
    list_filter = ('statut',)
    list_select_related = ('mission__demande',)