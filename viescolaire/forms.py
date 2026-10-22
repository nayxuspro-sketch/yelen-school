"""Formulaires de la vie scolaire."""
from django import forms

from .models import ConfigEDT, JourSemaine


class ConfigEDTForm(forms.ModelForm):
    """Horaires de cours et jours de classe de l'établissement (emploi du temps)."""

    duree_seance = forms.IntegerField(
        min_value=20, max_value=180, label="Durée d'une séance (minutes)",
        widget=forms.NumberInput(attrs={'class': 'input input-sm', 'step': 5}),
        error_messages={'min_value': "La durée d'une séance doit être d'au moins 20 minutes.",
                        'max_value': "La durée d'une séance ne peut pas dépasser 180 minutes."},
    )
    jours_actifs = forms.TypedMultipleChoiceField(
        choices=JourSemaine.choices,
        coerce=int,
        widget=forms.CheckboxSelectMultiple,
        label="Jours de classe",
        error_messages={'required': "Cochez au moins un jour de classe."},
    )

    class Meta:
        model = ConfigEDT
        fields = (
            'heure_debut_matin', 'heure_fin_matin',
            'heure_debut_aprem', 'heure_fin_aprem',
            'duree_seance', 'jours_actifs',
        )
        widgets = {
            nom: forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'input input-sm'})
            for nom in ('heure_debut_matin', 'heure_fin_matin', 'heure_debut_aprem', 'heure_fin_aprem')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['jours_actifs'] = self.instance.get_jours_actifs()

    def clean_jours_actifs(self):
        return sorted(set(self.cleaned_data['jours_actifs']))

    def clean(self):
        donnees = super().clean()
        debut_m, fin_m = donnees.get('heure_debut_matin'), donnees.get('heure_fin_matin')
        debut_a, fin_a = donnees.get('heure_debut_aprem'), donnees.get('heure_fin_aprem')
        if debut_m and fin_m and fin_m <= debut_m:
            self.add_error('heure_fin_matin', "La fin de la matinée doit être postérieure à son début.")
        if bool(debut_a) != bool(fin_a):
            self.add_error('heure_fin_aprem' if debut_a else 'heure_debut_aprem',
                           "Renseignez le début et la fin de l'après-midi, ou aucun des deux.")
        elif debut_a and fin_a:
            if fin_a <= debut_a:
                self.add_error('heure_fin_aprem', "La fin de l'après-midi doit être postérieure à son début.")
            if fin_m and debut_a < fin_m:
                self.add_error('heure_debut_aprem', "L'après-midi doit commencer après la fin de la matinée.")
        return donnees
