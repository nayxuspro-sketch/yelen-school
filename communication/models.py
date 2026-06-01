import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


class MessageParent(BaseModel):

    TYPE_CONVOCATION   = 'CONVOCATION'
    TYPE_AVERTISSEMENT = 'AVERTISSEMENT'
    TYPE_JUSTIFICATIF  = 'JUSTIFICATIF'
    TYPE_RELANCE       = 'RELANCE'

    TYPE_CHOICES = [
        ('CONVOCATION',   'Convocation à un entretien'),
        ('AVERTISSEMENT', 'Avertissement de comportement'),
        ('JUSTIFICATIF',  "Demande de justificatif d'absence"),
        ('RELANCE',       'Relance de paiement'),
    ]

    STATUT_ENVOYE  = 'ENVOYE'
    STATUT_LU      = 'LU'
    STATUT_REPONDU = 'REPONDU'

    STATUT_CHOICES = [
        ('ENVOYE',   'Envoyé'),
        ('LU',       'Lu'),
        ('REPONDU',  'Répondu'),
    ]

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='messages_parents',
        verbose_name=_("Établissement"),
    )
    eleve = models.ForeignKey(
        'inscriptions.Eleve',
        on_delete=models.CASCADE,
        related_name='messages_parents',
        verbose_name=_("Élève"),
    )
    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Année scolaire"),
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_("Type"),
    )
    objet = models.CharField(
        max_length=200,
        verbose_name=_("Objet"),
    )
    contenu = models.TextField(
        verbose_name=_("Contenu"),
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Token de réponse"),
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='ENVOYE',
        verbose_name=_("Statut"),
    )
    telephone_utilise = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Téléphone"),
    )
    # Liste de créneaux (seulement pour CONVOCATION) : ["Lundi 12 mai à 10h00", ...]
    creneaux_proposes = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Créneaux proposés"),
    )
    envoye_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='messages_envoyes',
        verbose_name=_("Envoyé par"),
    )
    sms_envoye = models.BooleanField(default=False, verbose_name=_("SMS envoyé"))
    date_envoi_sms = models.DateTimeField(null=True, blank=True, verbose_name=_("Date envoi SMS"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Message parent")
        verbose_name_plural = _("Messages parents")

    def __str__(self):
        return f"{self.get_type_display()} — {self.eleve} ({self.get_statut_display()})"

    def get_lien_reponse(self, request=None):
        from django.urls import reverse
        path = reverse('communication:repondre', kwargs={'token': self.token})
        if request:
            return request.build_absolute_uri(path)
        return path


class ReponseParent(BaseModel):

    message = models.OneToOneField(
        MessageParent,
        on_delete=models.CASCADE,
        related_name='reponse',
        verbose_name=_("Message"),
    )
    # CONVOCATION
    creneau_choisi = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("Créneau choisi"),
    )
    # AVERTISSEMENT
    accuse_reception = models.BooleanField(
        default=False,
        verbose_name=_("Accusé de réception"),
    )
    # RELANCE
    date_reglement_prevue = models.DateField(
        null=True, blank=True,
        verbose_name=_("Date de règlement prévisionnelle"),
    )
    # JUSTIFICATIF
    justificatif = models.FileField(
        upload_to='communication/justificatifs/',
        null=True, blank=True,
        verbose_name=_("Justificatif"),
    )
    # Tous types
    commentaire = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Commentaire"),
    )

    class Meta:
        verbose_name = _("Réponse parent")
        verbose_name_plural = _("Réponses parents")

    def __str__(self):
        return f"Réponse à : {self.message}"


class IncomingSMSLog(BaseModel):
    """Journal d'audit pour les messages SMS reçus et traités."""

    COMMAND_CHOICES = [
        ('NOTE', 'Demande de note/moyenne'),
        ('SOLDE', 'Demande de solde financier'),
        ('ABS', 'Demande de relevé d\'absences'),
        ('HELP', 'Aide / Instructions'),
        ('INVALID', 'Commande invalide ou inconnue'),
    ]

    sender_number = models.CharField(
        max_length=20,
        verbose_name=_("Numéro émetteur"),
    )
    message_text = models.TextField(
        verbose_name=_("Texte du SMS"),
    )
    command_type = models.CharField(
        max_length=10,
        choices=COMMAND_CHOICES,
        default='INVALID',
        verbose_name=_("Type de commande"),
    )
    eleve = models.ForeignKey(
        'inscriptions.Eleve',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_sms',
        verbose_name=_("Élève concerné"),
    )
    response_text = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Réponse envoyée"),
    )
    is_authorized = models.BooleanField(
        default=False,
        verbose_name=_("Autorisé"),
    )
    processed_successfully = models.BooleanField(
        default=False,
        verbose_name=_("Traité avec succès"),
    )
    error_message = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Message d'erreur"),
    )

    class Meta:
        verbose_name = _("SMS Entrant")
        verbose_name_plural = _("SMS Entrants")
        ordering = ['-created_at']

    def __str__(self):
        return f"SMS de {self.sender_number} ({self.command_type}) — {self.created_at}"
