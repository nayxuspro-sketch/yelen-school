from django import forms
from .models import MembrePersonnel, InscriptionPersonnel, SalairePersonnel, CongePersonnel
from parametres.models import Cycle, TitreFonction, TitreHonorifiquePersonnel

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
            'fonction', 'titre_honorifique', 'date_embauche', 'est_contractuel',
            'est_vacataire', 'est_directeur', 'est_censeur',
            'situation_matrimoniale', 'nombre_enfants', 'photo',
            'etablissement', 'poste_principal_code', 'cycles'
        ]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_embauche': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'adresse': forms.Textarea(attrs={'rows': 3}),
            'cycles': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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


class InscriptionPersonnelForm(forms.ModelForm):
    """Formulaire pour l'inscription annuelle du personnel scolaire."""

    class Meta:
        model = InscriptionPersonnel
        fields = [
            'personnel', 'annee_scolaire', 'poste', 'cycle',
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
