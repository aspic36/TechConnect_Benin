from django import forms

from .models import Evaluation, Paiement, Proposition


class PropositionForm(forms.ModelForm):
    class Meta:
        model = Proposition
        fields = ('prix', 'delais_jours', 'message')
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }


class EvaluationForm(forms.ModelForm):
    note = forms.IntegerField(min_value=1, max_value=5, label='Note')

    class Meta:
        model = Evaluation
        fields = ('note', 'commentaire')
        widgets = {
            'note': forms.NumberInput(attrs={'min': 1, 'max': 5, 'type': 'range'}),
            'commentaire': forms.Textarea(attrs={'rows': 4}),
        }


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ('montant', 'methode')