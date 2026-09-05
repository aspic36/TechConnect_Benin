from django import forms

from .models import Demande


class DemandeForm(forms.ModelForm):
    class Meta:
        model = Demande
        fields = (
            'titre', 'description', 'categorie', 'budget_min', 'budget_max',
            'lieu', 'a_distance', 'urgence',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'urgence': forms.CheckboxInput(),
        }