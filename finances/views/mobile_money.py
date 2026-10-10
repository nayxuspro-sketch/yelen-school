"""Demandes de paiement Mobile Money.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from ..models import Paiement, ModePaiement, DemandePaiementMobile
from inscriptions.models import Inscription
from parametres.models import RubriquePaiement
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from .commun import _numero_valide, _require_finance_role, _require_same_establishment


@login_required
def mobile_money_list(request):
    """Tableau de bord des demandes Mobile Money."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    ctx = {}
    qs = DemandePaiementMobile.objects.select_related(
        'inscription__eleve', 'inscription__classe', 'rubrique', 'cree_par', 'confirme_par'
    )
    etab = getattr(request.user, 'etablissement', None)
    if etab is not None:
        qs = qs.filter(inscription__classe__etablissement=etab)
    statut = request.GET.get('statut', '')
    if statut:
        qs = qs.filter(statut=statut)

    counts = DemandePaiementMobile.objects.all()
    if etab is not None:
        counts = counts.filter(inscription__classe__etablissement=etab)
    en_attente = counts.filter(statut='EN_ATTENTE').count()
    confirme   = counts.filter(statut='CONFIRME').count()
    annule     = counts.filter(statut='ANNULE').count()

    ctx.update({
        'demandes': qs,
        'statut_filtre': statut,
        'en_attente': en_attente,
        'confirme': confirme,
        'annule': annule,
        'StatutChoices': DemandePaiementMobile.StatutChoices,
    })
    return render(request, 'finances/mobile_money_list.html', ctx)


@login_required
def mobile_money_create(request):
    """Créer une demande de paiement Mobile Money pour un élève."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    ctx = {}
    inscription_id = request.GET.get('inscription') or request.POST.get('inscription')
    try:
        inscription = get_object_or_404(Inscription, pk=inscription_id) if inscription_id else None
    except (ValueError, ValidationError):
        messages.error(request, "Inscription invalide.")
        inscription = None
    if inscription:
        _require_same_establishment(request, inscription)

    rubriques = []
    if inscription:
        rubriques = RubriquePaiement.objects.filter(
            actif=True, etablissement=inscription.classe.etablissement
        ).order_by('ordre', 'nom')

    if request.method == 'POST':
        inscription_id = request.POST.get('inscription')
        rubrique_id    = request.POST.get('rubrique') or None
        montant_raw    = request.POST.get('montant', '').strip()
        telephone      = request.POST.get('telephone', '').strip()

        if not inscription_id or not montant_raw or not telephone:
            messages.error(request, "Tous les champs obligatoires doivent être renseignés.")
        elif not _numero_valide(telephone):
            messages.error(request, "Numéro de téléphone Mobile Money invalide.")
        else:
            try:
                montant = Decimal(montant_raw)
                if not montant.is_finite() or montant <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                messages.error(request, "Montant invalide.")
                montant = None

            if montant:
                try:
                    insc = get_object_or_404(Inscription, pk=inscription_id)
                except (ValueError, ValidationError):
                    messages.error(request, "Inscription invalide.")
                    insc = None
                if insc is not None:
                    _require_same_establishment(request, insc)
                    rubrique = None
                    if rubrique_id:
                        try:
                            rubrique = RubriquePaiement.objects.filter(
                                pk=rubrique_id,
                                etablissement=insc.classe.etablissement,
                                actif=True,
                            ).first()
                        except (ValueError, ValidationError):
                            rubrique = None
                        if rubrique is None:
                            messages.error(request, "Rubrique de paiement invalide.")
                            montant = None

                    if montant:
                        demande = DemandePaiementMobile.objects.create(
                            inscription=insc,
                            rubrique=rubrique,
                            montant=montant,
                            telephone=telephone,
                            cree_par=request.user,
                        )

                        _envoyer_sms_mobile_money(demande, request)

                        messages.success(request, f"Demande {demande.reference} créée. SMS envoyé au {telephone}.")
                        return redirect('finances:situation_eleve', inscription_id=insc.pk)

    ctx.update({
        'inscription': inscription,
        'rubriques': rubriques,
    })
    return render(request, 'finances/mobile_money_form.html', ctx)


@login_required
@require_POST
def mobile_money_confirmer(request, pk):
    """Le comptable confirme manuellement la réception du paiement."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    reference_transaction = request.POST.get('reference_transaction', '').strip()

    with transaction.atomic():
        demande = get_object_or_404(
            DemandePaiementMobile.objects.select_for_update(of=('self',)).select_related(
                'inscription__classe', 'inscription__eleve', 'rubrique'
            ),
            pk=pk,
        )
        _require_same_establishment(request, demande.inscription)
        if demande.statut != DemandePaiementMobile.StatutChoices.EN_ATTENTE:
            messages.warning(request, "Cette demande ne peut plus être confirmée.")
            return redirect('finances:mobile_money_list')

        paiement = Paiement(
            inscription=demande.inscription,
            rubrique=demande.rubrique,
            montant=demande.montant,
            mode_paiement=ModePaiement.MOBILE_MONEY,
            reference=reference_transaction or demande.reference,
            encaisse_par=request.user,
            statut_eleve=demande.inscription.statut_eleve,
        )
        paiement._audit_reason = "Confirmation manuelle d'une réception Mobile Money"
        paiement.save()
        demande._audit_reason = "Confirmation manuelle d'une réception Mobile Money"
        demande.statut = DemandePaiementMobile.StatutChoices.CONFIRME
        demande.confirme_le = timezone.now()
        demande.confirme_par = request.user
        demande.paiement = paiement
        demande.updated_by = request.user
        demande.save(update_fields=[
            'statut', 'confirme_le', 'confirme_par', 'paiement', 'updated_by', 'updated_at'
        ])

    messages.success(request, f"Paiement {demande.reference} confirmé. Reçu généré.")
    return redirect('finances:situation_eleve', inscription_id=demande.inscription.pk)


@login_required
@require_POST
def mobile_money_annuler(request, pk):
    """Annuler une demande Mobile Money en attente."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    reason = request.POST.get('raison', '').strip()
    if not reason:
        messages.error(request, "Le motif d'annulation est obligatoire.")
        return redirect('finances:mobile_money_list')

    with transaction.atomic():
        demande = get_object_or_404(
            DemandePaiementMobile.objects.select_for_update(),
            pk=pk,
        )
        _require_same_establishment(request, demande.inscription)
        if demande.statut != DemandePaiementMobile.StatutChoices.EN_ATTENTE:
            messages.warning(request, "Seules les demandes en attente peuvent être annulées.")
            return redirect('finances:mobile_money_list')
        demande._audit_reason = reason
        demande.statut = DemandePaiementMobile.StatutChoices.ANNULE
        demande.observations = reason
        demande.updated_by = request.user
        demande.save(update_fields=['statut', 'observations', 'updated_by', 'updated_at'])

    messages.info(request, f"Demande {demande.reference} annulée.")
    return redirect('finances:mobile_money_list')


def mobile_money_confirmation_parent(request, token):
    """Page publique accessible par le parent via le lien SMS (sans connexion requise)."""
    demande = get_object_or_404(DemandePaiementMobile, token=token)
    ctx = {
        'demande': demande,
        'eleve': demande.inscription.eleve,
        'classe': demande.inscription.classe,
    }
    return render(request, 'finances/mobile_money_confirmation_parent.html', ctx)


def _envoyer_sms_mobile_money(demande, request):
    """Compose et envoie le SMS d'instruction Orange Money au parent."""
    try:
        from core.sms import envoyer_sms
        lien = request.build_absolute_uri(f"/finances/payer/{demande.token}/")
        eleve = demande.inscription.eleve
        message = (
            f"YELEN SCHOOL - Paiement {demande.reference}\n"
            f"Eleve: {eleve.nom} {eleve.prenom}\n"
            f"Montant: {int(demande.montant)} FCFA\n"
            f"Composez *144# > Paiement marchand > "
            f"confirmez ref: {demande.reference}\n"
            f"Details: {lien}"
        )
        ok, _ = envoyer_sms(demande.telephone, message)
        if ok:
            demande.sms_envoye = True
            demande.save(update_fields=['sms_envoye'])
    except Exception:
        pass
