from django.contrib import admin

from .models import Evaluation, Mission, Paiement, Proposition


@admin.register(Proposition)
class PropositionAdmin(admin.ModelAdmin):
    list_display = ('demande', 'prestataire', 'prix', 'delais_jours', 'statut', 'date_creation')
    list_filter = ('statut',)
    list_select_related = ('demande', 'prestataire')


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('demande', 'client', 'prestataire', 'statut', 'date_debut', 'date_fin')
    list_filter = ('statut',)
    list_select_related = ('demande', 'client', 'prestataire')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('mission', 'auteur', 'cible', 'note', 'date_creation')
    list_select_related = ('mission', 'auteur', 'cible')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('mission', 'montant', 'methode', 'statut', 'date_creation')
    list_filter = ('methode', 'statut')