from django import forms
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from .models import User
from core.models import RoleChoices
from etablissements.models import Etablissement


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'new-password'}),
        help_text="Au moins 8 caractères.",
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'email', 'telephone', 'role', 'etablissement']
        widgets = {
            'last_name':    forms.TextInput(attrs={'class': 'input'}),
            'first_name':   forms.TextInput(attrs={'class': 'input'}),
            'email':        forms.EmailInput(attrs={'class': 'input', 'autocomplete': 'email'}),
            'telephone':    forms.TextInput(attrs={'class': 'input'}),
            'role':         forms.Select(attrs={'class': 'input select'}),
            'etablissement': forms.Select(attrs={'class': 'input select'}),
        }

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self._configure_for_user(current_user)

    def _configure_for_user(self, current_user):
        if current_user and current_user.role != RoleChoices.SUPER_ADMIN:
            self.fields['role'].choices = [
                c for c in RoleChoices.choices if c[0] != RoleChoices.SUPER_ADMIN
            ]
            self.fields['etablissement'].queryset = Etablissement.objects.filter(
                pk=current_user.etablissement_id
            )
            self.fields['etablissement'].initial = current_user.etablissement
        else:
            self.fields['etablissement'].queryset = Etablissement.objects.all().order_by('nom')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1', '')
        p2 = cleaned_data.get('password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'email', 'telephone', 'role', 'etablissement', 'is_active']
        widgets = {
            'last_name':    forms.TextInput(attrs={'class': 'input'}),
            'first_name':   forms.TextInput(attrs={'class': 'input'}),
            'email':        forms.EmailInput(attrs={'class': 'input'}),
            'telephone':    forms.TextInput(attrs={'class': 'input'}),
            'role':         forms.Select(attrs={'class': 'input select'}),
            'etablissement': forms.Select(attrs={'class': 'input select'}),
        }

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        if current_user and current_user.role != RoleChoices.SUPER_ADMIN:
            self.fields['role'].choices = [
                c for c in RoleChoices.choices if c[0] != RoleChoices.SUPER_ADMIN
            ]
            self.fields['etablissement'].queryset = Etablissement.objects.filter(
                pk=current_user.etablissement_id
            )
        else:
            self.fields['etablissement'].queryset = Etablissement.objects.all().order_by('nom')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Formulaire d'auto-modification du profil par l'utilisateur connecté."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telephone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input'}),
            'last_name':  forms.TextInput(attrs={'class': 'input'}),
            'email':      forms.EmailInput(attrs={'class': 'input', 'autocomplete': 'email'}),
            'telephone':  forms.TextInput(attrs={'class': 'input', 'placeholder': 'ex: +226 70 00 00 00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save(update_fields=['first_name', 'last_name', 'email', 'telephone', 'username'])
        return user


class ChangeOwnPasswordForm(forms.Form):
    """Changement de mot de passe par l'utilisateur lui-même (vérifie l'ancien)."""
    old_password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'current-password'}),
    )
    password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'new-password'}),
        help_text="Au moins 8 caractères.",
    )
    password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password', '')
        p1 = cleaned_data.get('password1', '')
        p2 = cleaned_data.get('password2', '')
        if self.user and old_password and not self.user.check_password(old_password):
            self.add_error('old_password', "Le mot de passe actuel est incorrect.")
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return cleaned_data


class PasswordResetRateLimitedForm(DjangoPasswordResetForm):
    """PasswordResetForm avec limitation de débit (3 requêtes/heure/session).

    Protège contre les abus de demande de réinitialisation par email.
    """

    RATE_LIMIT_MAX = 3
    RATE_LIMIT_WINDOW_MINUTES = 60

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        request = self.request
        if request:
            reset_attempts = request.session.get('password_reset_attempts', [])
            now_ts = timezone.now().timestamp()
            cutoff = now_ts - (self.RATE_LIMIT_WINDOW_MINUTES * 60)
            reset_attempts = [t for t in reset_attempts if isinstance(t, (int, float)) and t > cutoff]
            if len(reset_attempts) >= self.RATE_LIMIT_MAX:
                oldest = reset_attempts[0]
                remaining_seconds = int(oldest + (self.RATE_LIMIT_WINDOW_MINUTES * 60) - now_ts)
                raise forms.ValidationError(
                    f"Trop de tentatives. Réessayez dans {max(1, remaining_seconds // 60)} minute(s)."
                )
            reset_attempts.append(now_ts)
            request.session['password_reset_attempts'] = reset_attempts
            request.session.modified = True

        return email


class ParentCreateForm(forms.ModelForm):
    """Formulaire de création d'un compte parent avec liaison aux élèves."""
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'new-password'}),
        help_text="Au moins 8 caractères.",
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'new-password'}),
    )
    eleves = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox'}),
        label="Élèves liés (ses enfants)",
    )

    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'email', 'telephone', 'eleves']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'input'}),
            'first_name': forms.TextInput(attrs={'class': 'input'}),
            'email': forms.EmailInput(attrs={'class': 'input', 'autocomplete': 'email'}),
            'telephone': forms.TextInput(attrs={'class': 'input'}),
        }

    def __init__(self, *args, etablissement=None, **kwargs):
        super().__init__(*args, **kwargs)
        from inscriptions.models import Eleve, Inscription
        from parametres.models import AnneeScolaire
        
        annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
        
        if etablissement and annee_courante:
            eleves_qs = Eleve.objects.filter(
                inscriptions__classe__etablissement=etablissement,
                inscriptions__annee_scolaire=annee_courante,
                is_active=True
            ).distinct().order_by('nom', 'prenom')
        else:
            eleves_qs = Eleve.objects.filter(is_active=True).order_by('nom', 'prenom')
        
        self.fields['eleves'].queryset = eleves_qs
        self.etablissement = etablissement

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1', '')
        p2 = cleaned_data.get('password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email'].lower()
        user.role = 'PARENT'
        user.etablissement = self.etablissement
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            user.eleves_lies.set(self.cleaned_data.get('eleves', []))
        return user


class SetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'new-password'}),
        help_text="Au moins 8 caractères.",
    )
    password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'input'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1', '')
        p2 = cleaned_data.get('password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return cleaned_data
