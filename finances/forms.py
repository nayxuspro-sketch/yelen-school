from django import forms
from django.utils.translation import gettext_lazy as _
from .models import FraisScolarite, Paiement, ModePaiement, TypeFrais, Echeancier
from inscriptions.models import Inscription
from parametres.models import RubriquePaiement

class FraisScolariteForm(forms.ModelForm):
    class Meta:
        model = FraisScolarite
        fields = ['annee_scolaire', 'classe', 'cycle', 'type_frais', 'montant']
        widgets = {
            'annee_scolaire': forms.Select(attrs={'class': 'input select'}),
            'classe': forms.Select(attrs={'class': 'input select'}),
            'cycle': forms.Select(attrs={'class': 'input select'}),
            'type_frais': forms.Select(attrs={'class': 'input select'}),
            'montant': forms.NumberInput(attrs={'class': 'input', 'step': '0.01'}),
        }

class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['inscription', 'rubrique', 'montant', 'mode_paiement', 'reference', 'echeance', 'observation']
        widgets = {
            'inscription': forms.Select(attrs={'class': 'input select', 'id': 'id_inscription'}),
            'rubrique': forms.Select(attrs={'class': 'input select', 'id': 'id_rubrique'}),
            'montant': forms.NumberInput(attrs={
                'class': 'input',
                'id': 'id_montant',
                'step': '0.01',
                'placeholder': 'Montant versé',
            }),
            'mode_paiement': forms.Select(attrs={'class': 'input select'}),
            'reference': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Numéro de chèque, transaction mobile...'}),
            'echeance': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'observation': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # rubrique : toutes les rubriques actives (validation POST doit accepter la valeur choisie via JS)
        self.fields['rubrique'].queryset = RubriquePaiement.objects.filter(actif=True)
        self.fields['rubrique'].required = False
        self.fields['montant'].required = False

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode_paiement')
        reference = (cleaned_data.get('reference') or '').strip()
        if mode and mode != ModePaiement.ESPECES and not reference:
            self.add_error(
                'reference',
                "La référence de transaction est obligatoire pour ce mode de paiement."
            )
        return cleaned_data


class EcheancierForm(forms.ModelForm):
    class Meta:
        model = Echeancier
        fields = ['libelle', 'date_limite', 'montant_du', 'paye']
        widgets = {
            'libelle': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ex: 1ère tranche, Scolarité mois de...'}),
            'date_limite': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'montant_du': forms.NumberInput(attrs={'class': 'input', 'step': '0.01', 'placeholder': 'Montant attendu'}),
            'paye': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['libelle'].required = True
        self.fields['date_limite'].required = True
        self.fields['montant_du'].required = True
