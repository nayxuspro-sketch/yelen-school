from django import forms
from .models import Matiere, MatiereCycle, Enseignement, Evaluation, TypeEvaluation, Trimestre, Note
from parametres.models import Classe, AnneeScolaire, PeriodeEvaluation
from personnel.models import MembrePersonnel

def _apply_yelen_classes(fields):
    """Apply yelen.css dash-input class to all form fields."""
    for name, field in fields.items():
        w = field.widget
        if isinstance(w, forms.CheckboxInput):
            pass
        else:
            existing = w.attrs.get('class', '').replace('input', '').replace('select', '').strip()
            w.attrs['class'] = ('dash-input ' + existing).strip()

class MatiereCycleForm(forms.ModelForm):
    """Formulaire inline pour configurer une matière dans un cycle."""

    class Meta:
        model = MatiereCycle
        fields = ['coefficient', 'moy_min', 'moy_max', 'heures_hebdomadaires', 'est_obligatoire']
        widgets = {
            'coefficient': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'moy_min': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'moy_max': forms.NumberInput(attrs={'step': '0.01', 'min': '1'}),
            'heures_hebdomadaires': forms.NumberInput(attrs={'step': '0.5', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_yelen_classes(self.fields)


class MatiereForm(forms.ModelForm):
    """Formulaire pour la gestion des matières."""

    class Meta:
        model = Matiere
        fields = [
            'code', 'nom', 'nom_complet', 'categorie',
            'coefficient', 'moy_min', 'moy_max',
            'heures_hebdomadaires', 'est_discipline', 'est_obligatoire'
        ]
        widgets = {
            'nom_complet': forms.TextInput(attrs={'placeholder': 'Ex: Français - Lecture et Expression'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_yelen_classes(self.fields)


class EnseignementForm(forms.ModelForm):
    """Formulaire pour assigner une matière à une classe."""

    class Meta:
        model = Enseignement
        fields = [
            'matiere', 'classe', 'annee_scolaire',
            'personnel', 'coefficient', 'heures_hebdomadaires', 'est_actif'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_yelen_classes(self.fields)


class EvaluationForm(forms.ModelForm):
    """Formulaire pour planifier une évaluation."""

    # Remplace le FK trimestre (pedagogie.Trimestre) par une sélection
    # sur parametres.PeriodeEvaluation, plus riche et mieux configurée.
    periode = forms.ModelChoiceField(
        queryset=PeriodeEvaluation.objects.none(),
        label="Trimestre / Période",
        required=True,
        empty_label="-- Choisir une période --",
    )

    class Meta:
        model = Evaluation
        # 'trimestre' est géré manuellement via le champ 'periode' ci-dessus
        exclude = ['trimestre']
        widgets = {
            'date_planifiee': forms.DateInput(attrs={'type': 'date'}),
            'date_effectuee': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'observations': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pré-remplir le champ période depuis l'instance existante
        if self.instance and self.instance.pk and self.instance.trimestre_id:
            t = self.instance.trimestre
            # Trouver la PeriodeEvaluation correspondante (même annee + même numero)
            try:
                periode_initiale = PeriodeEvaluation.objects.get(
                    annee_scolaire=t.annee_scolaire,
                    numero=t.numero,
                )
                self.initial['periode'] = periode_initiale.pk
            except PeriodeEvaluation.DoesNotExist:
                pass

        # Peupler le queryset periode selon l'enseignement sélectionné
        enseignement_id = (
            self.data.get('enseignement')          # POST en cours
            or (self.instance.enseignement_id if self.instance and self.instance.pk else None)
        )
        if enseignement_id:
            try:
                ens = Enseignement.objects.select_related('annee_scolaire').get(pk=enseignement_id)
                self.fields['periode'].queryset = PeriodeEvaluation.objects.filter(
                    annee_scolaire=ens.annee_scolaire
                ).order_by('numero')
            except Enseignement.DoesNotExist:
                self.fields['periode'].queryset = PeriodeEvaluation.objects.all().order_by('numero')
        else:
            # Aucun enseignement sélectionné : toutes les périodes
            self.fields['periode'].queryset = PeriodeEvaluation.objects.all().order_by(
                'annee_scolaire__libelle', 'numero'
            )

        # Ordre d'affichage des champs
        self.order_fields([
            'enseignement', 'type_evaluation', 'periode',
            'titre', 'description', 'date_planifiee',
            'bareme', 'duree_minutes', 'coefficient', 'statut',
            'observations',
        ])

        _apply_yelen_classes(self.fields)


class NoteForm(forms.ModelForm):
    """Formulaire pour la saisie individuelle d'une note."""

    class Meta:
        model = Note
        fields = ['valeur', 'observation', 'statut']
        widgets = {
            'observation': forms.TextInput(attrs={'placeholder': 'Observation facultative'}),
        }

    def __init__(self, *args, evaluation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._evaluation = evaluation
        self.fields['valeur'].widget.attrs.update({'class': 'input input-note-val'})
        self.fields['observation'].widget.attrs.update({'class': 'input input-note-obs'})
        self.fields['statut'].widget.attrs.update({'class': 'input select input-note-statut'})
        if evaluation:
            self.fields['valeur'].widget.attrs['max'] = float(evaluation.bareme)
            self.fields['valeur'].widget.attrs['placeholder'] = f"/ {evaluation.bareme}"

    def clean_valeur(self):
        valeur = self.cleaned_data.get('valeur')
        if valeur is None:
            return valeur
        if valeur < 0:
            raise forms.ValidationError("La note ne peut pas être négative.")
        evaluation = self._evaluation or (self.instance.evaluation if self.instance and self.instance.pk else None)
        if evaluation and valeur > evaluation.bareme:
            raise forms.ValidationError(
                f"La note {valeur} dépasse le barème maximum de {evaluation.bareme}."
            )
        return valeur
