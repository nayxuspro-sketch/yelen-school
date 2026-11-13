from django import forms

from core.validators import validate_image_upload

from .models import Etablissement


class EtablissementForm(forms.ModelForm):
    class Meta:
        model = Etablissement
        fields = ['nom', 'code', 'adresse', 'telephone', 'email', 'ville', 'pays', 'logo']
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nom'].label = "Nom de l'établissement"
        self.fields['nom'].help_text = "Nom de ce site scolaire, et non celui d'un éventuel réseau."

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo and hasattr(logo, 'size'):
            validate_image_upload(logo)
        return logo
