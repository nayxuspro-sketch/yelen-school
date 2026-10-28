from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from .models import Eleve, Inscription
from .services import message_annee_cloturee, message_classe_complete
from parametres.models import AnneeScolaire, Classe, StatutEleve
from core.validators import validate_image_upload

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
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

    #: Champs de chaque section du gabarit eleve_form.html, dans l'ordre d'affichage.
    SECTIONS = {
        'identite': ('nom', 'prenom', 'genre', 'date_naissance', 'lieu_naissance', 'nationalite', 'photo'),
        'localisation': ('lieu_residence', 'etablissement_origine', 'last_classe', 'last_annee'),
        'famille': ('telephone_urgence', 'nom_pere', 'profession_pere', 'nom_mere', 'profession_mere',
                    'telephone_parent', 'tuteur_nom', 'tuteur_telephone', 'tuteur_adresse'),
        'sante': ('groupe_sanguin', 'allergies', 'medecin_traitant', 'informations_medicales', 'personnes_autorisees'),
    }

    @property
    def sections(self):
        """Champs liés de chaque section (« nom » n'est plus confondu avec « nom_pere » par un test de sous-chaîne)."""
        return {nom: [self[champ] for champ in champs] for nom, champs in self.SECTIONS.items()}

    class Meta:
        model = Eleve
        fields = [
            'nom', 'prenom', 'genre', 'date_naissance', 'lieu_naissance',
            'nationalite', 'lieu_residence',
            'telephone_urgence', 'photo', 'nom_pere', 'profession_pere',
            'nom_mere', 'profession_mere', 'telephone_parent', 'tuteur_nom',
            'tuteur_telephone', 'tuteur_adresse', 'etablissement_origine',
            'last_classe', 'last_annee',
            'groupe_sanguin', 'allergies', 'medecin_traitant', 'informations_medicales', 'personnes_autorisees',
        ]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'tuteur_adresse': forms.Textarea(attrs={'rows': 2}),
            'informations_medicales': forms.Textarea(attrs={'rows': 2}),
            'personnes_autorisees': forms.Textarea(attrs={'rows': 3, 'placeholder': 'OUEDRAOGO Salif — oncle — 70 00 00 00'}),
            'photo': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/png,image/gif,image/webp',
                'class': 'input',
            }),
        }

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._etablissement = etablissement
        self.homonymes = []
        photo_field = self.fields['photo']
        photo_field.validators.append(
            FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
        )
        _apply_yelen_classes(self.fields)

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'size'):
            validate_image_upload(photo, max_size_bytes=MAX_IMAGE_SIZE_MB * 1024 * 1024)
        return photo

    def clean(self):
        """À la création, signale les élèves de l'établissement (ou jamais inscrits) portant les mêmes nom, prénom
        et date de naissance ; la création n'aboutit qu'après confirmation explicite."""
        cleaned_data = super().clean()
        # « confirmer_homonyme=1 » est posé par le gabarit après un premier signalement : le second envoi confirme.
        if not self.instance._state.adding or self.data.get('confirmer_homonyme') == '1':
            return cleaned_data
        nom, prenom, naissance = cleaned_data.get('nom'), cleaned_data.get('prenom'), cleaned_data.get('date_naissance')
        if nom and prenom and naissance:
            homonymes = Eleve.objects.filter(nom__iexact=nom.strip(), prenom__iexact=prenom.strip(),
                                             date_naissance=naissance, is_active=True)
            if self._etablissement:
                homonymes = homonymes.filter(Q(inscriptions__classe__etablissement=self._etablissement)
                                             | Q(inscriptions__isnull=True)).distinct()
            self.homonymes = list(homonymes.order_by('matricule')[:5])
            if self.homonymes:
                raise forms.ValidationError(
                    "Un élève portant les mêmes nom, prénom et date de naissance existe déjà. Vérifiez qu'il ne "
                    "s'agit pas du même élève (réinscription) avant de confirmer la création.")
        return cleaned_data


class InscriptionForm(forms.ModelForm):
    """Formulaire pour l'inscription annuelle d'un élève."""
    
    niveau = forms.CharField(
        label=_("Niveau"),
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'input input-readonly',
            'placeholder': 'Calculé automatiquement',
        })
    )

    cycle = forms.CharField(
        label=_("Cycle"),
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'input input-readonly',
            'placeholder': 'Calculé automatiquement',
        })
    )

    code_paiement = forms.CharField(
        label=_("Code paiement"),
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'input input-readonly',
            'placeholder': 'Calculé automatiquement',
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
        # Filtrer années, classes et statuts par établissement
        if etablissement:
            self.fields['annee_scolaire'].queryset = AnneeScolaire.objects.filter(
                etablissement=etablissement
            ).order_by('-date_debut')
            self.fields['classe'].queryset = Classe.objects.filter(
                etablissement=etablissement, actif=True
            ).select_related('cycle').order_by('cycle__ordre', 'nom')
            self.fields['statut_eleve'].queryset = StatutEleve.objects.filter(
                etablissement=etablissement, actif=True
            ).order_by('ordre', 'nom')
        else:
            self.fields['annee_scolaire'].queryset = AnneeScolaire.objects.none()
            self.fields['classe'].queryset = Classe.objects.none()
            self.fields['statut_eleve'].queryset = StatutEleve.objects.none()

        self.fields['classe'].widget.attrs.update({'class': 'input select'})
        self.fields['statut_eleve'].widget.attrs.update({'class': 'input select'})

        if self.instance and self.instance.pk:
            try:
                if self.instance.classe:
                    self.initial['niveau'] = self.instance.classe.niveau
                    if self.instance.classe.cycle:
                        self.initial['cycle'] = self.instance.classe.cycle.nom
                    if self.instance.statut_eleve:
                        self.initial['code_paiement'] = (
                            f"{self.instance.classe.niveau}-{self.instance.statut_eleve.nom}"
                        )
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

        annee = cleaned_data.get('annee_scolaire')
        if annee and message_annee_cloturee(annee):
            self.add_error('annee_scolaire', message_annee_cloturee(annee))
        elif annee and classe and 'classe' not in self.errors:
            complet = message_classe_complete(classe, annee, exclure=self.instance)
            if complet:
                self.add_error('classe', complet)

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
        complet = self._inscription and message_classe_complete(nouvelle_classe, self._inscription.annee_scolaire)
        if complet:
            raise forms.ValidationError(complet)
        return nouvelle_classe


class PreInscriptionForm(forms.ModelForm):
    """Demande d'inscription d'un nouvel élève : années ouvertes et classes actives de l'établissement."""

    class Meta:
        from .models import PreInscription
        model = PreInscription
        fields = ['annee_scolaire', 'classe_demandee', 'nom', 'prenom', 'genre', 'date_naissance', 'lieu_naissance',
                  'etablissement_origine', 'last_classe', 'parent_nom', 'parent_telephone', 'observation']
        widgets = {'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, etablissement=None, annee_defaut=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._etablissement = etablissement
        self.fields['annee_scolaire'].queryset = (AnneeScolaire.objects.filter(etablissement=etablissement, cloturee=False)
                                                  .order_by('-date_debut'))
        self.fields['classe_demandee'].queryset = (Classe.objects.filter(etablissement=etablissement, actif=True)
                                                   .select_related('cycle').order_by('cycle__ordre', 'nom'))
        if annee_defaut is not None and not self.instance.pk:
            self.fields['annee_scolaire'].initial = annee_defaut.pk
        _apply_yelen_classes(self.fields)

    def clean_parent_telephone(self):
        telephone = ' '.join(self.cleaned_data['parent_telephone'].split())
        if sum(c.isdigit() for c in telephone) < 8:
            raise forms.ValidationError("Indiquez un numéro de téléphone joignable (8 chiffres au moins).")
        return telephone

    def clean(self):
        donnees = super().clean()
        annee = donnees.get('annee_scolaire')
        if annee is not None:
            message = message_annee_cloturee(annee)
            if message:
                self.add_error('annee_scolaire', message)
        return donnees

    def save(self, commit=True):
        self.instance.etablissement = self._etablissement
        self.instance.nom = ' '.join(self.instance.nom.split()).upper()
        self.instance.prenom = ' '.join(self.instance.prenom.split())
        return super().save(commit)
