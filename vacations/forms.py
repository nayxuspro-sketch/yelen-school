from django import forms
from .models import ContratVacation


class ContratVacationForm(forms.ModelForm):
    """Formulaire pour créer/modifier un contrat de vacation."""

    class Meta:
        model = ContratVacation
        fields = [
            'personnel',
            'annee_scolaire',
            'enseignement',
            'taux_horaire',
            'heures_hebdo_prevues',
            'date_debut',
            'date_fin',
            'actif',
        ]
        widgets = {
            'personnel': forms.Select(attrs={'class': 'input select'}),
            'annee_scolaire': forms.Select(attrs={'class': 'input select'}),
            'enseignement': forms.Select(attrs={'class': 'input select'}),
            'taux_horaire': forms.NumberInput(attrs={'class': 'input', 'min': '0', 'step': '100'}),
            'heures_hebdo_prevues': forms.NumberInput(attrs={'class': 'input', 'min': '0.5', 'step': '0.5'}),
            'date_debut': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'actif': forms.CheckboxInput(attrs={'class': 'input-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from parametres.models import AnneeScolaire
        from personnel.models import MembrePersonnel
        from pedagogie.models import Enseignement

        self.fields['annee_scolaire'].queryset = AnneeScolaire.objects.filter(
            est_courante=True
        ).order_by('-date_debut')

        self.fields['personnel'].queryset = MembrePersonnel.objects.filter(
            is_active=True
        ).order_by('nom', 'prenom')

        self.fields['enseignement'].queryset = (
            Enseignement.objects
            .select_related('matiere', 'classe')
            .order_by('matiere__nom', 'classe__nom')
        )
        self.fields['enseignement'].required = False

        self.fields['taux_horaire'].initial = 2500
        self.fields['heures_hebdo_prevues'].initial = 2.0
