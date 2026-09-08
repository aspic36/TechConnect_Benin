"""
Formulaires de l'app propositions.

Définit les formulaires pour la soumission d'une proposition par un prestataire,
l'évaluation d'une mission (note 1-5) et l'enregistrement d'un paiement par le client.
"""

from django import forms

from .models import Evaluation, Paiement, Proposition


class PropositionForm(forms.ModelForm):
    """Formulaire de soumission d'une offre : prix, délais et message au client."""

    class Meta:
        model = Proposition
        fields = ('prix', 'delais_jours', 'message')
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }


class EvaluationForm(forms.ModelForm):
    """Formulaire d'évaluation d'une mission : note de 1 à 5 et commentaire optionnel."""

    note = forms.IntegerField(min_value=1, max_value=5, label='Note')

    class Meta:
        model = Evaluation
        fields = ('note', 'commentaire')
        widgets = {
            # Curseur (range) limité à la plage 1-5 pour la note.
            'note': forms.NumberInput(attrs={'min': 1, 'max': 5, 'type': 'range'}),
            'commentaire': forms.Textarea(attrs={'rows': 4}),
        }


class PaiementForm(forms.ModelForm):
    """Formulaire d'enregistrement d'un paiement par le client (montant + méthode)."""

    class Meta:
        model = Paiement
        fields = ('montant', 'methode')