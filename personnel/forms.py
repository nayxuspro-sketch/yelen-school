from django import forms
from .models import (MembrePersonnel, InscriptionPersonnel, SalairePersonnel, CongePersonnel, AbsencePersonnel,
                    ObservationAbsence)
from parametres.models import AnneeScolaire, Classe, Cycle, Poste, TitreFonction, TitreHonorifiquePersonnel
from pedagogie.models import Matiere
from core.validators import validate_image_upload
from .selectors import filtrer_membres_par_cycle_ids, membres_dans_cycle

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
        cycles_autorises = kwargs.pop('cycles_autorises', None)
        super().__init__(*args, **kwargs)
        self._cycles_a_preserver = []
        self._classe_a_preserver = None
        etablissement_cible = etablissement
        if etablissement_cible is None and not self.instance._state.adding and self.instance.etablissement_id:
            etablissement_cible = self.instance.etablissement
        if etablissement is not None:
            self.fields['etablissement'].queryset = self.fields['etablissement'].queryset.filter(pk=etablissement.pk)
            self.initial.setdefault('etablissement', etablissement)
        elif cycles_autorises is not None:
            etablissements_autorises = Cycle.objects.filter(pk__in=cycles_autorises).values('etablissement_id')
            self.fields['etablissement'].queryset = self.fields['etablissement'].queryset.filter(
                pk__in=etablissements_autorises
            )
            if not etablissement_cible and self.data.get('etablissement'):
                etablissement_cible = self.fields['etablissement'].queryset.filter(
                    pk=self.data.get('etablissement')
                ).first()

        cycles = Cycle.objects.all()
        if etablissement_cible is not None:
            cycles = cycles.filter(etablissement=etablissement_cible)
        if cycles_autorises is not None:
            cycles = cycles.filter(pk__in=cycles_autorises)
            if not self.instance._state.adding:
                self._cycles_a_preserver = list(
                    self.instance.cycles.exclude(pk__in=cycles_autorises).values_list('pk', flat=True)
                )
                classe = self.instance.classe_affectation
                if classe and classe.cycle_id not in cycles_autorises:
                    self._classe_a_preserver = classe
        self.fields['cycles'].queryset = cycles.order_by('ordre', 'nom')
        self._filtrer_classes(etablissement, cycles_autorises)
        self.fields['qualite_affectation'].required = False      # titulaire par défaut

        # Pré-remplir le champ numero_cni avec la valeur déchiffrée (masquée)
        if not self.instance._state.adding:
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

    def _filtrer_classes(self, etablissement=None, cycles_autorises=None):
        """Classe d'affectation : uniquement celles de l'établissement et des cycles accessibles."""
        etablissement_cible = etablissement
        if etablissement_cible is None and not self.instance._state.adding and self.instance.etablissement_id:
            etablissement_cible = self.instance.etablissement
        etablissement = etablissement_cible
        if etablissement is None:
            saisie = self.data.get('etablissement') if self.data else None
            etablissement = Classe._meta.get_field('etablissement').related_model.objects.filter(pk=saisie).first() \
                if saisie else None
        classes = Classe.objects.all()
        if etablissement is not None:
            classes = classes.filter(etablissement=etablissement)
        if cycles_autorises is not None:
            classes = classes.filter(cycle_id__in=cycles_autorises)
        self.fields['classe_affectation'].queryset = classes.select_related('cycle').order_by('cycle__ordre', 'nom')

    def _save_m2m(self):
        """Un utilisateur limité ne peut modifier ses cycles visibles, ni effacer les autres affectations."""
        super()._save_m2m()
        if self._cycles_a_preserver and self.instance.pk:
            self.instance.cycles.add(*self._cycles_a_preserver)

    def clean(self):
        """La classe d'affectation doit appartenir à l'établissement du membre."""
        donnees = super().clean()
        if not donnees.get('qualite_affectation'):
            donnees['qualite_affectation'] = MembrePersonnel.QualiteAffectation.TITULAIRE
        classe, etablissement = donnees.get('classe_affectation'), donnees.get('etablissement')
        if self._classe_a_preserver and not classe:
            donnees['classe_affectation'] = classe = self._classe_a_preserver
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
        etablissement = kwargs.pop('etablissement', None)
        cycles_autorises = kwargs.pop('cycles_autorises', None)
        super().__init__(*args, **kwargs)
        if etablissement is not None:
            self.fields['annee_scolaire'].queryset = AnneeScolaire.objects.filter(etablissement=etablissement)
            self.fields['poste'].queryset = Poste.objects.filter(etablissement=etablissement)
        cycles = Cycle.objects.all()
        if etablissement is not None:
            cycles = cycles.filter(etablissement=etablissement)
        if cycles_autorises is not None:
            cycles = cycles.filter(pk__in=cycles_autorises)
        self.fields['cycle'].queryset = cycles
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
        cycles_autorises = kwargs.pop('cycles_autorises', None)
        super().__init__(*args, **kwargs)
        membres = MembrePersonnel.objects.filter(is_active=True)
        if etablissement is not None:
            membres = membres.filter(etablissement=etablissement)
        self.fields['personnel'].queryset = filtrer_membres_par_cycle_ids(
            membres, cycles_autorises
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
        cycles_autorises = kwargs.pop('cycles_autorises', None)
        super().__init__(*args, **kwargs)
        membres = MembrePersonnel.objects.filter(is_active=True)
        if etablissement is not None:
            membres = membres.filter(etablissement=etablissement)
        self.fields['personnel'].queryset = filtrer_membres_par_cycle_ids(
            membres, cycles_autorises
        ).order_by('nom', 'prenom')
        _apply_yelen_classes(self.fields)


class AbsencePersonnelForm(forms.ModelForm):
    """Saisie quotidienne des absences des professeurs (5.58.0).

    Reprend le formulaire de référence : année scolaire (rappel), date, professeur, classe, matière,
    heure de début et de fin (le nombre d'heures en découle), observation **obligatoire** choisie dans la
    liste déroulante. Le cycle reste proposé en filtre au-dessus du formulaire : il restreint les
    professeurs et les classes (primaire, post-primaire / secondaire).
    """

    date = forms.DateField(label="Date", widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                           input_formats=['%Y-%m-%d', '%d/%m/%Y'])
    date_fin = forms.DateField(label="Au", required=False,
                               widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                               input_formats=['%Y-%m-%d', '%d/%m/%Y'],
                               help_text="Laisser vide pour une absence d'une seule journée.")
    cycle = forms.ModelChoiceField(label="Cycle", queryset=Cycle.objects.none(), required=False,
                                   empty_label="Tous les cycles")
    classe = forms.ModelChoiceField(label="Classe", queryset=Classe.objects.none(), required=False,
                                   empty_label="— Choisir —")
    matiere = forms.ModelChoiceField(label="Matière", queryset=Matiere.objects.none(), required=False,
                                     empty_label="— Choisir —")
    toutes_matieres = forms.BooleanField(label="Toutes les matières", required=False)

    class Meta:
        model = AbsencePersonnel
        fields = ['personnel', 'classe', 'matiere', 'toutes_matieres', 'heure_debut', 'heure_fin', 'motif',
                  'observation', 'justifiee', 'retenue']
        labels = {'personnel': "Nom du professeur", 'heure_debut': "Heure de début",
                  'heure_fin': "Heure de fin"}
        widgets = {
            'heure_debut': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'heure_fin': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        etablissement = kwargs.pop('etablissement', None)
        cycle = kwargs.pop('cycle', None)
        cycles_autorises = kwargs.pop('cycles_autorises', None)
        self.annee_scolaire = kwargs.pop('annee_scolaire', None)
        super().__init__(*args, **kwargs)

        membres = MembrePersonnel.objects.filter(is_active=True)
        classes = Classe.objects.all()
        matieres = Matiere.objects.all()
        if etablissement:
            membres = membres.filter(etablissement=etablissement)
            classes = classes.filter(etablissement=etablissement)
            self.fields['matiere'].queryset = Matiere.objects.order_by('nom')
        cycles = Cycle.objects.all()
        if etablissement is not None:
            cycles = cycles.filter(etablissement=etablissement)
        if cycles_autorises is not None:
            cycles = cycles.filter(pk__in=cycles_autorises)
            membres = filtrer_membres_par_cycle_ids(membres, cycles_autorises)
            classes = classes.filter(cycle_id__in=cycles_autorises)
        self.fields['cycle'].queryset = cycles.order_by('ordre', 'nom')
        self.fields['cycle'].empty_label = (
            'Tous les cycles autorisés' if cycles_autorises is not None else 'Tous les cycles'
        )

        # Cycle choisi au rechargement du formulaire : toujours validé contre les choix autorisés.
        if cycle is None and self.is_bound and self.data.get('cycle'):
            cycle = self.fields['cycle'].queryset.filter(pk=self.data.get('cycle')).first()
            if cycle is None:
                membres = membres.none()
                classes = classes.none()
        if cycle is not None:
            membres = membres_dans_cycle(membres, cycle)
            classes = classes.filter(cycle=cycle)
            self.fields['cycle'].initial = cycle
        self.fields['motif'].required = False                  # déduit de l'observation si non précisé
        self.fields['personnel'].queryset = membres.distinct().order_by('nom', 'prenom')
        self.fields['classe'].queryset = classes.select_related('cycle').order_by('cycle__ordre', 'nom')
        self.fields['matiere'].queryset = matieres.order_by('nom')

        # La date saisie une seule fois vaut date de début ; « Au » vide = absence d'une journée.
        if self.instance.pk:
            self.fields['date'].initial = self.instance.date_debut
            if self.instance.toutes_matieres:
                self.fields['toutes_matieres'].initial = True
            self.fields['date_fin'].initial = (self.instance.date_fin
                                              if self.instance.date_fin != self.instance.date_debut else None)

        # « Sélectionnez obligatoirement une observation » : message explicite du formulaire (clean), le champ
        # porte aussi l'attribut HTML `required` pour le navigateur.
        self.fields['observation'].required = False
        self.fields['observation'].widget = forms.Select(attrs={'required': 'required'})
        self._alimenter_observations(etablissement)

        _apply_yelen_classes(self.fields)

    def _alimenter_observations(self, etablissement=None):
        """Choix du champ Observation ; une valeur déjà enregistrée hors liste y est ajoutée pour rester éditable."""
        choix = [('', '— Sélectionner une observation —')]
        choix += [(o.libelle, o.libelle) for o in ObservationAbsence.disponibles(etablissement)]
        valeur = (self.data.get('observation') if self.data else '') or self.initial.get('observation') or ''
        if valeur and valeur not in [v for v, _ in choix]:
            choix.append((valeur, valeur))
        self.fields['observation'].widget.choices = choix

    def clean(self):
        donnees = super().clean()
        jour, fin_jour = donnees.get('date'), donnees.get('date_fin')
        if jour and fin_jour and fin_jour < jour:
            self.add_error('date_fin', "La date de fin doit être postérieure ou égale à la date de début.")
        debut, fin = donnees.get('heure_debut'), donnees.get('heure_fin')
        if debut and fin and fin <= debut:
            self.add_error('heure_fin', "L'heure de fin doit être postérieure à l'heure de début.")
        if not donnees.get('observation'):
            self.add_error('observation', "Sélectionnez obligatoirement une observation.")
        return donnees

    def save(self, commit=True):
        absence = super().save(commit=False)
        jour = self.cleaned_data['date']
        absence.date_debut = jour
        absence.date_fin = self.cleaned_data.get('date_fin') or jour     # une séance : une journée
        absence.toutes_matieres = bool(self.cleaned_data.get('toutes_matieres'))
        if absence.toutes_matieres:                     # « Toutes les matières » : aucune matière retenue
            absence.matiere = None
        absence.motif = (self.cleaned_data.get('motif')
                         or _motif_depuis_observation(self.cleaned_data.get('observation')))
        if commit:
            absence.save()
            self.save_m2m()
        return absence


MOTIFS_PAR_OBSERVATION = (
    ('MALADIE', ('santé', 'maladie', 'malade', 'consultation', 'hospital')),
    ('PERMISSION', ('congé', 'permission', 'absence autorisée')),
    ('FORMATION', ('formation', 'mission', 'stage', 'séminaire')),
)


def _motif_depuis_observation(observation):
    """Motif d'absence déduit de l'observation choisie (le formulaire ne demande que l'observation)."""
    texte = (observation or '').lower()
    for motif, mots in MOTIFS_PAR_OBSERVATION:
        if any(mot in texte for mot in mots):
            return motif
    return AbsencePersonnel.MotifChoices.AUTRE


class ObservationAbsenceForm(forms.ModelForm):
    """Ajout d'une observation manquante dans la liste déroulante du formulaire d'absence (5.57.0)."""

    class Meta:
        model = ObservationAbsence
        fields = ['libelle']
        widgets = {'libelle': forms.TextInput(attrs={'placeholder': "Ex. Raison de santé, Congé, Permission…",
                                                     'maxlength': 80})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['libelle'].required = True
        _apply_yelen_classes(self.fields)

    def clean_libelle(self):
        libelle = (self.cleaned_data.get('libelle') or '').strip()
        if not libelle:
            raise forms.ValidationError("Indiquez l'observation à ajouter.")
        return libelle
