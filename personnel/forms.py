from django import forms
from .models import MembrePersonnel, InscriptionPersonnel, SalairePersonnel, CongePersonnel, AbsencePersonnel
from parametres.models import TitreFonction, TitreHonorifiquePersonnel
from core.validators import validate_image_upload

# Import pour le chiffrement
try:
    from core.encryption import mask_cni
except ImportError:
    def mask_cni(x): return x


def _apply_yelen_classes(fields):
    """Apply yelen.css input/select classes to all form fields."""
    for name, field in fields.items():
        w = field.widget
        if isinstance(w, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
            pass  # checkboxes keep their default rendering
        elif isinstance(w, (forms.Select, forms.SelectMultiple)):
            w.attrs['class'] = 'input select'
        elif isinstance(w, forms.Textarea):
            w.attrs['class'] = 'input'
        else:
            existing = w.attrs.get('class', '')
            w.attrs['class'] = ('input ' + existing).strip()


class MembrePersonnelForm(forms.ModelForm):
    """Formulaire pour la création et modification d'un membre du personnel."""
    
    numero_cni = forms.CharField(
        label="Numéro CNI / Passport / N° Extrait",
        required=False,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Numéro CNI'}),
        help_text="Ce champ sera chiffré pour protection"
    )

    class Meta:
        model = MembrePersonnel
        fields = [
            'nom', 'prenom', 'genre', 'date_naissance', 'lieu_naissance',
            'nationalite', 'telephone', 'email', 'adresse', 'numero_cni',
            'fonction', 'titre_honorifique', 'titre_capacite', 'date_embauche', 'est_contractuel',
            'profil_pointage', 'heure_arrivee_limite', 'heure_depart_normale',
            'est_vacataire', 'est_directeur', 'est_censeur',
            'situation_matrimoniale', 'nombre_enfants', 'photo',
            'etablissement', 'poste_principal_code', 'cycles', 'classe_affectation', 'qualite_affectation'
        ]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_embauche': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'adresse': forms.Textarea(attrs={'rows': 3}),
            'cycles': forms.CheckboxSelectMultiple(),
            'classe_affectation': forms.Select(),
            'qualite_affectation': forms.Select(),
            'heure_arrivee_limite': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'heure_depart_normale': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        # Établissement du membre : limite la liste des classes proposées à celles de son établissement.
        etablissement = kwargs.pop('etablissement', None)
        super().__init__(*args, **kwargs)
        self._filtrer_classes(etablissement)
        self.fields['qualite_affectation'].required = False      # titulaire par défaut

        # Pré-remplir le champ numero_cni avec la valeur déchiffrée (masquée)
        if self.instance and self.instance.pk:
            cni = self.instance.numero_cni
            if cni:
                self.initial['numero_cni'] = mask_cni(cni)
        # Alimenter fonction depuis TitreFonction (paramètres)
        fonctions = list(TitreFonction.objects.filter(actif=True).values_list('nom', flat=True))
        if fonctions:
            self.fields['fonction'].widget = forms.Select(
                choices=[('', '---------')] + [(f, f) for f in fonctions]
            )
        # Alimenter titre_honorifique depuis TitreHonorifiquePersonnel (paramètres)
        titres_h = list(TitreHonorifiquePersonnel.objects.filter(actif=True).values_list('nom', flat=True))
        if titres_h:
            self.fields['titre_honorifique'].widget = forms.Select(
                choices=[('', '---------')] + [(t, t) for t in titres_h]
            )
        _apply_yelen_classes(self.fields)

    def _filtrer_classes(self, etablissement=None):
        """Classe d'affectation : uniquement les classes de l'établissement du membre (fondé sur la valeur saisie
        lors d'une création, sur l'instance lors d'une modification, ou sur l'établissement de l'utilisateur)."""
        from parametres.models import Classe

        etablissement = etablissement or (self.instance.etablissement if self.instance.pk else None)
        if etablissement is None:
            saisie = self.data.get('etablissement') if self.data else None
            etablissement = Classe._meta.get_field('etablissement').related_model.objects.filter(pk=saisie).first() \
                if saisie else None
        classes = Classe.objects.all()
        if etablissement is not None:
            classes = classes.filter(etablissement=etablissement)
        self.fields['classe_affectation'].queryset = classes.select_related('cycle').order_by('cycle__ordre', 'nom')

    def clean(self):
        """La classe d'affectation doit appartenir à l'établissement du membre."""
        donnees = super().clean()
        if not donnees.get('qualite_affectation'):
            donnees['qualite_affectation'] = MembrePersonnel.QualiteAffectation.TITULAIRE
        classe, etablissement = donnees.get('classe_affectation'), donnees.get('etablissement')
        if classe and etablissement and classe.etablissement_id != etablissement.pk:
            self.add_error('classe_affectation',
                           "Cette classe n'appartient pas à l'établissement choisi pour le membre.")
        return donnees

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'size'):
            validate_image_upload(photo)
        return photo


class InscriptionPersonnelForm(forms.ModelForm):
    """Formulaire pour l'inscription annuelle du personnel scolaire."""

    class Meta:
        model = InscriptionPersonnel
        # 'personnel' est fixé par la vue (instance), jamais saisi dans le formulaire
        fields = [
            'annee_scolaire', 'poste', 'cycle',
            'est_actif', 'date_debut', 'date_fin', 'observations',
            'heures_hebdomadaires'
        ]
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_fin': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observations': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_yelen_classes(self.fields)


class SalairePersonnelForm(forms.ModelForm):
    """Formulaire de saisie d'un bulletin de salaire mensuel."""

    class Meta:
        model = SalairePersonnel
        fields = [
            'personnel', 'annee_scolaire', 'mois', 'annee',
            'salaire_base', 'indemnite_transport', 'indemnite_logement',
            'prime_anciennete', 'autres_primes',
            'retenue_cnss', 'retenue_iuts', 'autres_retenues',
            'statut', 'date_paiement', 'reference_paiement', 'observations',
        ]
        widgets = {
            'date_paiement': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observations': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        etablissement = kwargs.pop('etablissement', None)
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['personnel'].queryset = MembrePersonnel.objects.filter(
                etablissement=etablissement, is_active=True
            ).order_by('nom', 'prenom')
        _apply_yelen_classes(self.fields)


class CongePersonnelForm(forms.ModelForm):
    """Formulaire de demande / saisie d'un congé."""

    class Meta:
        model = CongePersonnel
        fields = [
            'personnel', 'type_conge', 'date_debut', 'date_fin',
            'motif', 'observations',
        ]
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_fin': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'motif': forms.Textarea(attrs={'rows': 3}),
            'observations': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        etablissement = kwargs.pop('etablissement', None)
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['personnel'].queryset = MembrePersonnel.objects.filter(
                etablissement=etablissement, is_active=True
            ).order_by('nom', 'prenom')
        _apply_yelen_classes(self.fields)


class AbsencePersonnelForm(forms.ModelForm):
    """Saisie d'une absence d'un agent."""

    class Meta:
        model = AbsencePersonnel
        fields = ['personnel', 'date_debut', 'date_fin', 'motif', 'justifiee', 'retenue', 'observation']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_fin': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        etablissement = kwargs.pop('etablissement', None)
        super().__init__(*args, **kwargs)
        if etablissement:
            self.fields['personnel'].queryset = MembrePersonnel.objects.filter(
                etablissement=etablissement, is_active=True
            ).order_by('nom', 'prenom')
        _apply_yelen_classes(self.fields)

    def clean(self):
        cleaned = super().clean()
        debut, fin = cleaned.get('date_debut'), cleaned.get('date_fin')
        if debut and fin and fin < debut:
            self.add_error('date_fin', "La date de fin doit être postérieure ou égale à la date de début.")
        return cleaned
