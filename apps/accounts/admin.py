"""
Module d'administration pour l'application accounts.

Enregistre le modele ``User`` personnalise dans l'admin Django en
etendant la configuration par defaut (UserAdmin) avec les champs
supplementaires de TechConnect Benin.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Abonnement, Notification, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Configuration admin du modele ``User`` personnalise.

    Ajoute les colonnes de liste (role, telephone, ville, verification, plan)
    et etend les fieldsets par defaut avec les sections « Profil TechConnect »
    et « Sanctions ».
    """
    list_display = ('username', 'email', 'role', 'phone', 'ville', 'is_verified', 'suspendu', 'plan')
    list_filter = ('role', 'is_verified', 'is_staff', 'suspendu', 'plan')
    # Extension du fieldset existant avec les champs de profil TechConnect
    fieldsets = UserAdmin.fieldsets + (
        ('Profil TechConnect', {'fields': ('role', 'phone', 'company_name', 'ville', 'bio', 'avatar', 'is_verified')}),
        ('Abonnement', {'fields': ('plan', 'date_debut_plan', 'date_fin_plan')}),
        ('Sanctions', {'fields': ('suspendu', 'date_suspension')}),
    )
    # Champs proposes lors de la creation d'un utilisateur via l'admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profil TechConnect', {'fields': ('role', 'phone', 'company_name', 'ville')}),
    )


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    """Administration des demandes d'abonnement des prestataires."""
    list_display = ('prestataire', 'plan', 'montant', 'statut', 'date_demande', 'date_fin')
    list_filter = ('statut', 'plan')
    list_select_related = ('prestataire',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Administration des notifications internes de la plateforme."""
    list_display = ('destinataire', 'type', 'message', 'est_lue', 'date_creation')
    list_filter = ('type', 'est_lue')
    list_select_related = ('destinataire',)
