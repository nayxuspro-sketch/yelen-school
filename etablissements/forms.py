from django import forms

from core.models import CycleChoices
from core.validators import validate_image_upload

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
        # Le JSONField stocke une liste — initialise le MultipleChoiceField à partir d'elle
        if self.instance and self.instance.pk:
            self.initial['cycles'] = self.instance.cycles or []

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo and hasattr(logo, 'size'):
            validate_image_upload(logo)
        return logo
