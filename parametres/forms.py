from django import forms

from pedagogie.models import TypeEvaluation
from personnel.models import MembrePersonnel

from .models import (
    TypeDocument, Cycle, AnneeScolaire, Classe, Poste, LocalisationPoste,
    StatutEleve, RubriquePaiement, AppreciationMoyenneSecondaire,
    AppreciationMoyennePrimaire, CategorieDiscipline, Discipline,
    PeriodeEvaluation, TypeSanction, TitreFonction, TitreHonorifiquePersonnel,
    EvenementCalendrier, IdentiteEtablissement,
)


class AnneeScolaireForm(forms.ModelForm):
    class Meta:
        model = AnneeScolaire
        fields = ['libelle', 'date_debut', 'date_fin', 'est_courante']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }


class CycleForm(forms.ModelForm):
    class Meta:
        model = Cycle
        fields = ['nom', 'code', 'description', 'ordre', 'actif']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields = ['nom', 'niveau', 'cycle', 'capacite_max', 'est_classe_examen',
                  'type_examen', 'serie_bac', 'actif']

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['cycle'].queryset = Cycle.objects.filter(
                etablissement=etablissement, actif=True
            )


class PosteForm(forms.ModelForm):
    class Meta:
        model = Poste
        fields = ['titre', 'code', 'categorie', 'description', 'actif']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class LocalisationPosteForm(forms.ModelForm):
    class Meta:
        model = LocalisationPoste
        fields = ['nom', 'type_localisation', 'batiment', 'etage', 'numero', 'actif']


class StatutEleveForm(forms.ModelForm):
    class Meta:
        model = StatutEleve
        fields = ['nom', 'code', 'description', 'couleur', 'ordre', 'actif']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class RubriquePaiementForm(forms.ModelForm):
    class Meta:
        model = RubriquePaiement
        fields = ['nom', 'code', 'description', 'montant', 'obligatoire', 'ordre', 'actif']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class AppreciationMoyenneSecondaireForm(forms.ModelForm):
    class Meta:
        model = AppreciationMoyenneSecondaire
        fields = ['libelle', 'moy_min', 'moy_max', 'couleur', 'ordre', 'actif']


class AppreciationMoyennePrimaireForm(forms.ModelForm):
    class Meta:
        model = AppreciationMoyennePrimaire
        fields = ['libelle', 'moy_min', 'moy_max', 'couleur', 'ordre', 'actif']


class CategorieDisciplineForm(forms.ModelForm):
    class Meta:
        model = CategorieDiscipline
        fields = ['nom', 'code', 'couleur', 'ordre', 'actif']


class DisciplineForm(forms.ModelForm):
    class Meta:
        model = Discipline
        fields = ['nom', 'code', 'cycle', 'categorie', 'couleur', 'ordre', 'est_evaluee', 'actif']

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['cycle'].queryset = Cycle.objects.filter(
                etablissement=etablissement, actif=True
            )
            self.fields['categorie'].queryset = CategorieDiscipline.objects.filter(
                etablissement=etablissement, actif=True
            )


class PeriodeEvaluationForm(forms.ModelForm):
    class Meta:
        model = PeriodeEvaluation
        fields = ['nom', 'type_periode', 'numero', 'annee_scolaire',
                  'date_debut', 'date_fin', 'est_en_cours']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['annee_scolaire'].queryset = AnneeScolaire.objects.filter(
                etablissement=etablissement
            )


class TypeSanctionForm(forms.ModelForm):
    class Meta:
        model = TypeSanction
        fields = ['code', 'libelle', 'description', 'actif', 'points_defaut']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class TitreFonctionForm(forms.ModelForm):
    class Meta:
        model = TitreFonction
        fields = ['nom', 'actif']


class TitreHonorifiquePersonnelForm(forms.ModelForm):
    class Meta:
        model = TitreHonorifiquePersonnel
        fields = ['nom', 'actif']


class EvenementCalendrierForm(forms.ModelForm):
    class Meta:
        model = EvenementCalendrier
        fields = ['titre', 'type', 'date_debut', 'date_fin',
                  'description', 'journee_complete', 'annee_scolaire']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['annee_scolaire'].queryset = AnneeScolaire.objects.filter(
                etablissement=etablissement
            )


class IdentiteEtablissementForm(forms.ModelForm):
    class Meta:
        model = IdentiteEtablissement
        fields = [
            'nom_etablissement', 'sigle', 'type_etablissement',
            'numero_agrement_mena', 'date_agrement',
            'adresse_complete', 'ville', 'province', 'region',
            'telephone', 'email', 'site_web',
            'nom_directeur', 'devise',
            'logo', 'signature_directeur', 'cachet_etablissement',
        ]
        widgets = {
            'date_agrement': forms.DateInput(attrs={'type': 'date'}),
            'adresse_complete': forms.Textarea(attrs={'rows': 2}),
            'devise': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_logo(self):
        image = self.cleaned_data.get('logo')
        if image and hasattr(image, 'size'):
            _validate_image(image, max_size=2 * 1024 * 1024)
        return image

    def clean_signature_directeur(self):
        image = self.cleaned_data.get('signature_directeur')
        if image and hasattr(image, 'size'):
            _validate_image(image, max_size=512 * 1024)
        return image

    def clean_cachet_etablissement(self):
        image = self.cleaned_data.get('cachet_etablissement')
        if image and hasattr(image, 'size'):
            _validate_image(image, max_size=512 * 1024)
        return image


def _validate_image(image, max_size):
    """Valide la taille et le contenu réel d'une image via Pillow."""
    from core.validators import validate_image_upload
    validate_image_upload(image, max_size_bytes=max_size)


class TypeEvaluationForm(forms.ModelForm):
    class Meta:
        model = TypeEvaluation
        fields = ['code', 'nom', 'description', 'coefficient', 'ponderation',
                  'nb_meilleures_notes', 'est_visible', 'ordre']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class TypeDocumentForm(forms.ModelForm):
    class Meta:
        model = TypeDocument
        fields = ['code', 'libelle', 'categorie', 'cycle', 'description', 'actif']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }


class SignataireForm(forms.Form):
    """Formulaire partagé entre signataire_config, signataire_edit et signataire_formulaire."""
    membre_personnel = forms.ModelChoiceField(
        queryset=MembrePersonnel.objects.none(),
        label="Membre du personnel",
    )
    fonction = forms.CharField(
        max_length=150,
        required=False,
        initial='Le Directeur',
        label="Fonction",
    )
    titre_honorifique = forms.CharField(
        max_length=50,
        required=False,
        label="Titre honorifique",
    )

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['membre_personnel'].queryset = (
                MembrePersonnel.objects
                .filter(etablissement=etablissement, is_active=True)
                .order_by('nom', 'prenom')
            )
