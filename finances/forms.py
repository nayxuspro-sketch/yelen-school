from django import forms
from .models import FraisScolarite, Paiement, ModePaiement, Echeancier, ModePenalite, ParametresFinances, TypeBourse
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


class ParametresFinancesForm(forms.ModelForm):
    """Pénalités de retard, blocage des bulletins, remise fratrie — listes limitées à l'établissement."""

    class Meta:
        model = ParametresFinances
        fields = ['penalite_mode', 'penalite_valeur', 'penalite_delai_jours', 'penalite_rubrique',
                  'bloquer_bulletins_impayes', 'seuil_blocage_pct', 'remise_fratrie', 'remise_fratrie_a_partir']
        widgets = {
            'penalite_mode': forms.Select(attrs={'class': 'input select'}),
            'penalite_valeur': forms.NumberInput(attrs={'class': 'input', 'step': '1', 'min': '0'}),
            'penalite_delai_jours': forms.NumberInput(attrs={'class': 'input', 'min': '0', 'max': '365'}),
            'penalite_rubrique': forms.Select(attrs={'class': 'input select'}),
            'bloquer_bulletins_impayes': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            'seuil_blocage_pct': forms.NumberInput(attrs={'class': 'input', 'min': '1', 'max': '100'}),
            'remise_fratrie': forms.Select(attrs={'class': 'input select'}),
            'remise_fratrie_a_partir': forms.NumberInput(attrs={'class': 'input', 'min': '2', 'max': '10'}),
        }

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['penalite_rubrique'].queryset = RubriquePaiement.objects.filter(
            etablissement=etablissement, actif=True).order_by('nom')
        self.fields['remise_fratrie'].queryset = TypeBourse.objects.filter(
            etablissement=etablissement, actif=True, is_active=True).order_by('nom')

    def clean(self):
        cleaned = super().clean()
        mode, valeur = cleaned.get('penalite_mode'), cleaned.get('penalite_valeur')
        if mode and mode != ModePenalite.AUCUNE:
            if not valeur or valeur <= 0:
                self.add_error('penalite_valeur', "Indiquez la valeur de la pénalité.")
            if mode == ModePenalite.POURCENT and valeur and valeur > 100:
                self.add_error('penalite_valeur', "Un pourcentage ne peut pas dépasser 100.")
            if not cleaned.get('penalite_rubrique'):
                self.add_error('penalite_rubrique', "Choisissez la rubrique sur laquelle les pénalités s'encaissent.")
        seuil = cleaned.get('seuil_blocage_pct')
        if cleaned.get('bloquer_bulletins_impayes') and (seuil is None or not 1 <= seuil <= 100):
            self.add_error('seuil_blocage_pct', "Le seuil doit être compris entre 1 et 100 %.")
        if (cleaned.get('remise_fratrie_a_partir') or 0) < 2:
            self.add_error('remise_fratrie_a_partir', "La remise fratrie commence au plus tôt au 2e enfant.")
        return cleaned
