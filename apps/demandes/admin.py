from django.contrib import admin

from .models import Categorie, Demande


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug')
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(Demande)
class DemandeAdmin(admin.ModelAdmin):
    list_display = ('titre', 'client', 'categorie', 'budget_min', 'budget_max', 'statut', 'lieu')
    list_filter = ('statut', 'categorie', 'a_distance', 'urgence')
    search_fields = ('titre', 'description')
    list_select_related = ('client', 'categorie')