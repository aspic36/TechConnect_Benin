"""
Module d'administration pour l'application accounts.

Enregistre le modele ``User`` personnalise dans l'admin Django en
etendant la configuration par defaut (UserAdmin) avec les champs
supplementaires de TechConnect Benin.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Configuration admin du modele ``User`` personnalise.

    Ajoute les colonnes de liste (role, telephone, ville, verification) et
    etend les fieldsets par defaut avec la section « Profil TechConnect ».
    """
    list_display = ('username', 'email', 'role', 'phone', 'ville', 'is_verified')
    list_filter = ('role', 'is_verified', 'is_staff')
    # Extension du fieldset existant avec les champs de profil TechConnect
    fieldsets = UserAdmin.fieldsets + (
        ('Profil TechConnect', {'fields': ('role', 'phone', 'company_name', 'ville', 'bio', 'avatar', 'is_verified')}),
    )
    # Champs proposes lors de la creation d'un utilisateur via l'admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profil TechConnect', {'fields': ('role', 'phone', 'company_name', 'ville')}),
    )
