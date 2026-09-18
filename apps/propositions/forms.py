"""
Formulaires de l'app propositions.

Définit les formulaires pour la soumission d'une proposition par un prestataire,
l'évaluation d'une mission (note 1-5) et le signalement d'un litige avec preuve.
"""

from django import forms

from .models import Evaluation, Litige, Proposition


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


class SignalerLitigeForm(forms.ModelForm):
    """Formulaire de signalement d'un litige : motif obligatoire + preuve optionnelle."""

    class Meta:
        model = Litige
        fields = ('motif', 'piece_jointe')
        widgets = {
            'motif': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': "Décris précisément le problème (travail non terminé, qualité…).",
            }),
            'piece_jointe': forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png,.gif,.webp'}),
        }
        labels = {
            'motif': 'Motif du litige',
            'piece_jointe': 'Pièce jointe (preuve, optionnelle)',
        }