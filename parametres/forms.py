from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import slugify

from core.models import RoleChoices
from pedagogie.models import TypeEvaluation
from personnel.models import MembrePersonnel

from .models import (
    TypeDocument, Cycle, AnneeScolaire, Classe, Poste, LocalisationPoste,
    StatutEleve, RubriquePaiement, AppreciationMoyenneSecondaire,
    AppreciationMoyennePrimaire, CategorieDiscipline, Discipline,
    PeriodeEvaluation, TypeSanction, Distinction, TitreFonction, Salle, TitreHonorifiquePersonnel,
    EvenementCalendrier, IdentiteEtablissement, RolePersonnalise,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            # « Tout Cycle » est conservé pour les anciennes données, mais n'est pas un cycle réel
            # à créer : la référence doit rester un cycle distinct de l'établissement.
            self.fields['code'].choices = [
                (code, label) for code, label in self.fields['code'].choices if code != 'TOUT'
            ]
            # Le formulaire de création n'affiche pas de case « actif » : garder le défaut du modèle.
            self.fields.pop('actif', None)


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
        fields = ['nom', 'code', 'description', 'montant', 'obligatoire', 'soumise_plafond', 'ordre', 'actif']
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


class DistinctionForm(forms.ModelForm):
    class Meta:
        model = Distinction
        fields = ['code', 'libelle', 'description', 'ordre', 'actif']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class TitreFonctionForm(forms.ModelForm):
    class Meta:
        model = TitreFonction
        fields = ['nom', 'actif']


class SalleForm(forms.ModelForm):
    class Meta:
        model = Salle
        fields = ['nom', 'capacite', 'actif']

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._etablissement = etablissement

    def clean_nom(self):
        nom = ' '.join(self.cleaned_data['nom'].split())
        doublons = Salle.objects.filter(etablissement=self._etablissement, nom__iexact=nom)
        if self.instance.pk:
            doublons = doublons.exclude(pk=self.instance.pk)
        if doublons.exists():
            raise forms.ValidationError("Une salle porte déjà ce nom.")
        return nom

    def save(self, commit=True):
        self.instance.etablissement = self._etablissement
        return super().save(commit)


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
            'numero_agrement_mena', 'date_agrement', 'categorie_reglementaire', 'zone_implantation',
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
        return _image_document(self.cleaned_data.get('signature_directeur'))

    def clean_cachet_etablissement(self):
        return _image_document(self.cleaned_data.get('cachet_etablissement'))


def _validate_image(image, max_size):
    """Valide la taille et le contenu réel d'une image via Pillow."""
    from core.validators import validate_image_upload
    validate_image_upload(image, max_size_bytes=max_size)


def _image_document(image):
    """Signature ou cachet : un nouvel envoi est validé (image réelle, 5 Mo max.) puis allégé pour l'impression ;
    une image déjà enregistrée est rendue telle quelle."""
    if isinstance(image, UploadedFile):
        from core.images import optimiser_image_document
        from core.validators import validate_image_upload
        validate_image_upload(image)
        return optimiser_image_document(image)
    return image


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
    signature = forms.ImageField(
        required=False,
        label="Signature scannée",
        help_text="Facultatif — PNG à fond transparent recommandé ; l'image est allégée automatiquement pour "
                  "l'impression. Enregistrée sur la fiche du membre du personnel et apposée sur tous les "
                  "documents qu'il signe.",
    )
    retirer_signature = forms.BooleanField(required=False, label="Retirer la signature enregistrée")

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['membre_personnel'].queryset = (
                MembrePersonnel.objects
                .filter(etablissement=etablissement, is_active=True)
                .order_by('nom', 'prenom')
            )

    def clean_signature(self):
        return _image_document(self.cleaned_data.get('signature'))

    def appliquer_signature(self, membre):
        """Enregistre (ou retire) la signature scannée sur la fiche du membre du personnel signataire."""
        image = self.cleaned_data.get('signature')
        if image:
            if membre.signature:
                membre.signature.delete(save=False)
            membre.signature = image
            membre.save(update_fields=['signature', 'updated_at'])
        elif self.cleaned_data.get('retirer_signature') and membre.signature:
            membre.signature.delete(save=False)
            membre.save(update_fields=['signature', 'updated_at'])


class RolePersonnaliseForm(forms.ModelForm):
    """Nouveau rôle : libellé et rôle de référence ; le code est dérivé du libellé."""

    class Meta:
        model = RolePersonnalise
        fields = ['libelle', 'base']
        widgets = {
            'libelle': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ex. Surveillant général', 'maxlength': 60}),
            'base': forms.Select(attrs={'class': 'input select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .droits import ROLES_CONFIGURABLES
        self.fields['base'].widget.choices = [(r.value, r.label) for r in ROLES_CONFIGURABLES]
        self.fields['base'].help_text = ("Comportement métier (tableau de bord, périmètre d'un enseignant…) "
                                         "et droits de départ du nouveau rôle.")

    def clean_base(self):
        from .droits import ROLES_CONFIGURABLES
        base = self.cleaned_data['base']
        if base not in {r.value for r in ROLES_CONFIGURABLES}:
            raise forms.ValidationError("Rôle de référence inconnu.")
        return base

    def clean_libelle(self):
        libelle = ' '.join(self.cleaned_data['libelle'].split())
        code = slugify(libelle).replace('-', '_').upper()[:30].strip('_')
        if not code:
            raise forms.ValidationError("Le libellé doit contenir des lettres ou des chiffres.")
        if code in RoleChoices.values or RolePersonnalise.objects.filter(code=code).exists():
            raise forms.ValidationError(f"Un rôle de code « {code} » existe déjà.")
        self.instance.code = code
        return libelle


class PolitiqueDonneesForm(forms.ModelForm):
    class Meta:
        from .models import PolitiqueDonnees
        model = PolitiqueDonnees
        fields = ['duree_conservation_annees', 'responsable_traitement', 'contact_responsable']

    def clean_duree_conservation_annees(self):
        duree = self.cleaned_data['duree_conservation_annees']
        if not 2 <= duree <= 50:
            raise forms.ValidationError("La durée de conservation doit être comprise entre 2 et 50 ans.")
        return duree
