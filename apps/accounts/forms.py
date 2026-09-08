"""
Module de formulaires pour l'application accounts.

Fournit les formulaires d'inscription, d'edition du profil et de
connexion, en etendant les classes Django natives (UserCreationForm,
AuthenticationForm, ModelForm) pour y integrer les champs propres
au modele ``User`` de TechConnect Benin.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription d'un nouveau compte.

    Ajoute le choix du role (client / prestataire), le telephone et la
    ville au formulaire de creation standard de Django.
    """
    role = forms.ChoiceField(
        choices=User.Role.choices,
        initial=User.Role.CLIENT,
        label='Vous êtes',
        widget=forms.RadioSelect,
    )
    phone = forms.CharField(max_length=20, required=False, label='Téléphone')
    ville = forms.CharField(max_length=100, required=False, label='Ville')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role', 'phone', 'ville', 'company_name')

    def save(self, commit=True):
        """Sauvegarde l'utilisateur en injectant le champ ``role``.

        Le role n'etant pas gere nativement par UserCreationForm, il est
        affecte manuellement ici avant la persistance en base.
        """
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class ProfilForm(forms.ModelForm):
    """Formulaire d'edition du profil utilisateur (email, telephone, ville, ...)."""

    class Meta:
        model = User
        fields = ('email', 'phone', 'ville', 'company_name', 'bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion avec libelle personnalise pour le champ login."""
    username = forms.CharField(label="Nom d'utilisateur")
