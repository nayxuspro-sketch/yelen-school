from datetime import date, timedelta

from django import forms
from django.utils import timezone

from .models import Licence, TypeLicence, StatutLicence


class LicenceForm(forms.ModelForm):
    """Formulaire de création / modification d'une licence."""

    date_expiration = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date d'expiration",
        initial=lambda: (date.today() + timedelta(days=365)).isoformat(),
    )

    class Meta:
        model = Licence
        fields = ['etablissement', 'type_licence', 'date_expiration', 'notes_interne']
        widgets = {
            'etablissement': forms.Select(attrs={'class': 'form-control'}),
            'type_licence': forms.Select(attrs={'class': 'form-control'}),
            'notes_interne': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'etablissement': 'Établissement',
            'type_licence': 'Type de licence',
            'notes_interne': 'Notes internes',
        }

    def clean_etablissement(self):
        etab = self.cleaned_data.get('etablissement')
        if etab and not self.instance.pk:
            if Licence.objects.filter(etablissement=etab).exists():
                raise forms.ValidationError(
                    "Cet établissement possède déjà une licence."
                )
        return etab

    def clean_date_expiration(self):
        d = self.cleaned_data.get('date_expiration')
        if d and d <= date.today():
            raise forms.ValidationError(
                "La date d'expiration doit être dans le futur."
            )
        return d


class RenouvelerForm(forms.Form):
    """Formulaire de renouvellement de licence."""

    DUREE_CHOICES = [
        (180, '6 mois'),
        (365, '1 an'),
        (730, '2 ans'),
    ]

    duree_jours = forms.ChoiceField(
        choices=DUREE_CHOICES,
        label='Durée du renouvellement',
        initial=365,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
    )

    def clean_duree_jours(self):
        return int(self.cleaned_data['duree_jours'])


class RevoquerForm(forms.Form):
    """Formulaire de révocation de licence."""

    raison = forms.CharField(
        label='Motif de révocation',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex : non-paiement, fraude détectée…',
        }),
    )

    confirmation = forms.BooleanField(
        label="Je confirme la révocation de cette licence. L'établissement perdra immédiatement l'accès à l'application.",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
