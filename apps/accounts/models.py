from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'client', 'Client'
        PRESTATAIRE = 'prestataire', 'Prestataire'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"