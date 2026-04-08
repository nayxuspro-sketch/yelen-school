from django import forms

from core.models import CycleChoices

from .models import Etablissement


class EtablissementForm(forms.ModelForm):
    cycles = forms.MultipleChoiceField(
        choices=CycleChoices.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Cycles proposés",
    )

    class Meta:
        model = Etablissement
        fields = ['nom', 'code', 'adresse', 'telephone', 'email', 'ville', 'pays', 'logo', 'cycles']
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ArrayField stores a list — initialise the MultipleChoiceField from it
        if self.instance and self.instance.pk:
            self.initial['cycles'] = self.instance.cycles or []
