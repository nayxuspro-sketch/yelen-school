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

    def __init__(self, *args, request=None, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)

        from parametres.models import AnneeScolaire
        from personnel.models import MembrePersonnel
        from pedagogie.models import Enseignement

        if etablissement is None and request is not None:
            etablissement = getattr(request.user, 'etablissement', None)

        annees = AnneeScolaire.objects.filter(est_courante=True)
        personnel = MembrePersonnel.objects.filter(is_active=True)
        enseignements = Enseignement.objects.all()
        if etablissement is not None:
            annees = annees.filter(etablissement=etablissement)
            personnel = personnel.filter(etablissement=etablissement)
            enseignements = enseignements.filter(classe__etablissement=etablissement)

        if request is not None:
            from .selectors import classes_vacation_visibles, personnel_vacation_visible
            from personnel.selectors import cycles_accessibles
            from yelen_school.cycle_filter import get_cycle_ids

            if etablissement is None and get_cycle_ids(request) is not None:
                annees = annees.filter(
                    etablissement_id__in=cycles_accessibles(request).values('etablissement_id')
                )
            personnel = personnel_vacation_visible(request, etablissement)
            enseignements = enseignements.filter(
                classe__in=classes_vacation_visibles(request, etablissement)
            )

        self.fields['annee_scolaire'].queryset = annees.order_by('-date_debut')
        self.fields['personnel'].queryset = personnel.order_by('nom', 'prenom')

        self.fields['enseignement'].queryset = (
            enseignements
            .select_related('matiere', 'classe')
            .order_by('matiere__nom', 'classe__nom')
        )
        self.fields['enseignement'].required = False

        self.fields['taux_horaire'].initial = 2500
        self.fields['heures_hebdo_prevues'].initial = 2.0
