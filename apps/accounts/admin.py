from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone', 'ville', 'is_verified')
    list_filter = ('role', 'is_verified', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Profil TechConnect', {'fields': ('role', 'phone', 'company_name', 'ville', 'bio', 'avatar', 'is_verified')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profil TechConnect', {'fields': ('role', 'phone', 'company_name', 'ville')}),
    )