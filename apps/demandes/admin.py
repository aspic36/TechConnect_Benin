"""Configuration de l'administration Django pour les modèles demandes."""

from django.contrib import admin

from .models import Categorie, Demande


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    """Administration des catégories de services (slug auto-généré depuis le nom)."""

    list_display = ('nom', 'slug')
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(Demande)
class DemandeAdmin(admin.ModelAdmin):
    """Administration des demandes avec filtrage par statut, catégorie et recherche par titre."""

    list_display = ('titre', 'client', 'categorie', 'budget_min', 'budget_max', 'statut', 'lieu')
    list_filter = ('statut', 'categorie', 'a_distance', 'urgence')
    search_fields = ('titre', 'description')
    # Requête optimisée : jointure sur client et catégorie en une seule requête
    list_select_related = ('client', 'categorie')