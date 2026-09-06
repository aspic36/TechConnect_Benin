from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class InscriptionForm(UserCreationForm):
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
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class ProfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'phone', 'ville', 'company_name', 'bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class ConnexionForm(AuthenticationForm):
    username = forms.CharField(label="Nom d'utilisateur")