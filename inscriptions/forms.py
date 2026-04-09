from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from .models import Eleve, Inscription, StatutInscriptionChoices
from parametres.models import Classe, AnneeScolaire, StatutEleve

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
MAX_IMAGE_SIZE_MB = 5


def _apply_yelen_classes(fields):
    """Apply yelen.css input/select classes to all form fields."""
    for name, field in fields.items():
        w = field.widget
        if isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault('class', '')
        elif isinstance(w, (forms.Select, forms.SelectMultiple)):
            w.attrs['class'] = 'input select'
        elif isinstance(w, forms.Textarea):
            w.attrs['class'] = 'input'
        else:
            existing = w.attrs.get('class', '')
            w.attrs['class'] = ('input ' + existing).strip()


class EleveForm(forms.ModelForm):
    """Formulaire pour la création et la modification d'un élève."""

    class Meta:
        model = Eleve
        fields = [
            'nom', 'prenom', 'genre', 'date_naissance', 'lieu_naissance',
            'nationalite', 'pays_residence', 'province', 'commune', 'village',
            'telephone_urgence', 'email', 'photo', 'nom_pere', 'profession_pere',
            'nom_mere', 'profession_mere', 'telephone_parent', 'tuteur_nom',
            'tuteur_telephone', 'tuteur_adresse', 'etablissement_origine',
            'last_classe', 'last_annee'
        ]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'tuteur_adresse': forms.Textarea(attrs={'rows': 2}),
            'photo': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/png,image/gif,image/webp',
                'class': 'input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        photo_field = self.fields['photo']
        photo_field.validators.append(
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
        )
        _apply_yelen_classes(self.fields)

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError(
                    f"La photo ne doit pas dépasser {MAX_IMAGE_SIZE_MB} Mo."
                )
            if hasattr(photo, 'content_type') and photo.content_type not in ALLOWED_MIME_TYPES:
                raise forms.ValidationError(
                    "Format d'image non autorisé. Utilisez JPG, PNG, GIF ou WebP."
                )
        return photo


class InscriptionForm(forms.ModelForm):
    """Formulaire pour l'inscription annuelle d'un élève."""
    
    niveau = forms.CharField(
        label=_("Niveau"),
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'input input-readonly',
            'style': 'background:var(--color-bg-input); border-style:dashed; cursor:not-allowed;',
            'placeholder': 'Sélectionnez une classe'
        })
    )
    
    cycle = forms.CharField(
        label=_("Cycle"),
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'input input-readonly',
            'style': 'background:var(--color-bg-input); border-style:dashed; cursor:not-allowed;',
            'placeholder': 'Cycle'
        })
    )
    
    code_paiement = forms.CharField(
        label=_("Code Paiement"),
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'input input-readonly',
            'style': 'background:var(--color-bg-input); border-style:dashed; cursor:not-allowed;',
            'placeholder': 'Niveau-Statut'
        })
    )

    class Meta:
        model = Inscription
        fields = [
            'eleve', 'annee_scolaire', 'date_inscription', 'classe', 'niveau', 'cycle',
            'statut_eleve', 'code_paiement', 'est_exonere', 'raison_exoneration',
            'est_redoublant', 'classe_redoublee',
            'observations'
        ]
        widgets = {
            'date_inscription': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observations': forms.Textarea(attrs={'rows': 2}),
            'raison_exoneration': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        etablissement = kwargs.pop('etablissement', None)
        super().__init__(*args, **kwargs)
        self._etablissement = etablissement
        # Champs conditionnels
        self.fields['raison_exoneration'].required = False
        self.fields['classe_redoublee'].required = False
        self.fields['statut_eleve'].required = False
        # Filtrer classes et statuts par établissement
        if etablissement:
            self.fields['classe'].queryset = Classe.objects.filter(
                etablissement=etablissement, actif=True
            ).select_related('cycle').order_by('cycle__ordre', 'nom')
            self.fields['statut_eleve'].queryset = StatutEleve.objects.filter(
                etablissement=etablissement, actif=True
            ).order_by('ordre', 'nom')
        else:
            self.fields['classe'].queryset = Classe.objects.none()
            self.fields['statut_eleve'].queryset = StatutEleve.objects.none()
        
        self.fields['classe'].widget.attrs.update({'class': 'input select', 'onchange': 'updateNiveauAndCycle(this)'})
        self.fields['statut_eleve'].widget.attrs.update({'class': 'input select', 'onchange': 'updateCodePaiement(this)'})
        
        # Pre-fill niveau, cycle and code_paiement from existing inscription
        if self.instance and self.instance.pk:
            try:
                if self.instance.classe:
                    self.initial['niveau'] = self.instance.classe.niveau
                    if self.instance.classe.cycle:
                        self.initial['cycle'] = self.instance.classe.cycle.nom
                    if self.instance.statut_eleve:
                        self.initial['code_paiement'] = f"{self.instance.classe.niveau}-{self.instance.statut_eleve.nom}"
            except AttributeError:
                pass
        
        _apply_yelen_classes(self.fields)

    def clean(self):
        cleaned_data = super().clean()
        est_exonere = cleaned_data.get('est_exonere')
        raison = cleaned_data.get('raison_exoneration', '')
        est_redoublant = cleaned_data.get('est_redoublant')
        classe_redoublee = cleaned_data.get('classe_redoublee')
        classe = cleaned_data.get('classe')

        if est_exonere and not raison.strip():
            self.add_error('raison_exoneration', "La raison d'exonération est obligatoire si l'élève est exonéré.")

        if est_redoublant and not classe_redoublee:
            self.add_error('classe_redoublee', "La classe redoublée est obligatoire si l'élève est redoublant.")

        if classe and self._etablissement and classe.etablissement_id != self._etablissement.pk:
            self.add_error('classe', "Cette classe n'appartient pas à votre établissement.")

        return cleaned_data


class TransfertClasseForm(forms.Form):
    """Formulaire de transfert d'un élève vers une autre classe (même année scolaire)."""
    classe = forms.ModelChoiceField(
        queryset=Classe.objects.none(),
        label="Nouvelle classe",
        widget=forms.Select(attrs={'class': 'input select'}),
    )
    motif = forms.CharField(
        label="Motif du transfert",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'ex: Sureffectif, demande parentale…'}),
    )

    def __init__(self, *args, inscription=None, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._inscription = inscription
        if etablissement:
            qs = Classe.objects.filter(etablissement=etablissement, actif=True).order_by('cycle__ordre', 'nom')
            if inscription:
                qs = qs.exclude(pk=inscription.classe_id)
            self.fields['classe'].queryset = qs

    def clean_classe(self):
        nouvelle_classe = self.cleaned_data['classe']
        if self._inscription and nouvelle_classe.pk == self._inscription.classe_id:
            raise forms.ValidationError("L'élève est déjà dans cette classe.")
        return nouvelle_classe
