"""
Module Examens - Forms
=======================
YELEN SCHOOL v3.4
"""

from django import forms
from .models import SessionExamen, CentreExamen, SalleExamen


class SessionExamenForm(forms.ModelForm):
    class Meta:
        model = SessionExamen
        fields = [
            'annee_scolaire', 'type_examen', 'libelle',
            'date_debut', 'date_fin', 'date_deliberation',
            'statut', 'observations',
        ]
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_fin': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_deliberation': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observations': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'input')

    def clean(self):
        cleaned = super().clean()
        debut = cleaned.get('date_debut')
        fin = cleaned.get('date_fin')
        if debut and fin and fin < debut:
            self.add_error('date_fin', "La date de fin doit être postérieure à la date de début.")
        return cleaned


class CentreExamenForm(forms.ModelForm):
    class Meta:
        model = CentreExamen
        fields = ['nom', 'code_centre', 'etablissement', 'adresse', 'capacite']
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'input')
        self.fields['etablissement'].required = False


class SalleExamenForm(forms.ModelForm):
    class Meta:
        model = SalleExamen
        fields = ['nom', 'capacite', 'surveillant_principal']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'input')
        self.fields['surveillant_principal'].required = False
