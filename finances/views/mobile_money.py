"""Demandes de paiement Mobile Money.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q, Sum
from decimal import Decimal, InvalidOperation
from ..models import (
    Paiement, ModePaiement, DemandePaiementMobile, LigneReleve, OperateurMobileMoney, ReleveMobileMoney,
)
from ..releves import (
    FichierInvalide, STATUTS_A_TRAITER, affecter_ligne, ignorer_ligne, importer_releve, valider_lignes,
)
from ..paiements_mobiles import (
    ErreurPasserelle, cinetpay_configure, confirmer_demande, creer_lien, verifier_en_attente, verifier_paiement,
)
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
        'cinetpay_actif': cinetpay_configure(),
        'nb_liens_en_attente': counts.filter(statut='EN_ATTENTE').exclude(lien_paiement='').count(),
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

                        lien = ''
                        if cinetpay_configure():
                            try:
                                lien = creer_lien(demande)
                            except ErreurPasserelle as exc:
                                messages.warning(
                                    request,
                                    f"Lien de paiement en ligne indisponible ({exc}) : SMS d'instructions *144# envoyé à la place.",
                                )
                        _envoyer_sms_mobile_money(demande, request)

                        messages.success(
                            request,
                            f"Demande {demande.reference} créée. SMS envoyé au {telephone}."
                            + (" Lien de paiement en ligne inclus." if lien else "")
                        )
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

        confirmer_demande(demande, request.user, reference_transaction,
                          "Confirmation manuelle d'une réception Mobile Money")

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


@login_required
@require_POST
def mobile_money_verifier(request, pk=None):
    """Vérification active auprès de CinetPay : une demande, ou toutes celles en attente munies d'un lien."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    if not cinetpay_configure():
        messages.error(request, "Paiement en ligne non configuré (CINETPAY_API_KEY, CINETPAY_SITE_ID, CINETPAY_URL_PUBLIQUE).")
        return redirect('finances:mobile_money_list')
    if pk is None:
        bilan = verifier_en_attente(getattr(request.user, 'etablissement', None), request.user)
        messages.info(request, (
            f"Vérification terminée : {bilan.get('CONFIRME', 0)} confirmé(s), {bilan.get('EN_ATTENTE', 0)} en attente, "
            f"{bilan.get('REFUSE', 0)} refusé(s), {bilan.get('ERREUR', 0)} erreur(s)."
        ))
        return redirect('finances:mobile_money_list')
    demande = get_object_or_404(DemandePaiementMobile.objects.select_related('inscription__classe'), pk=pk)
    _require_same_establishment(request, demande.inscription)
    if not demande.lien_paiement:
        messages.error(request, "Cette demande n'a pas de lien de paiement en ligne.")
        return redirect('finances:mobile_money_list')
    etat, message = verifier_paiement(demande, request.user)
    {'CONFIRME': messages.success, 'EN_ATTENTE': messages.info, 'REFUSE': messages.warning}.get(etat, messages.error)(request, message)
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
        if demande.lien_paiement:
            message = (
                f"YELEN SCHOOL - Paiement {demande.reference}\n"
                f"Eleve: {eleve.nom} {eleve.prenom}\n"
                f"Montant: {int(demande.montant)} FCFA\n"
                f"Payer par Orange Money ou Moov Money: {demande.lien_paiement}"
            )
            ok, _ = envoyer_sms(demande.telephone, message, limite=320)
        else:
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


# ── Relevés Mobile Money : import et rapprochement (circuit hors ligne) ─────

def _verifier_etablissement(request, etablissement_id):
    """Même règle que _require_same_establishment, pour un relevé."""
    from core.models import RoleChoices
    if getattr(request.user, 'role', None) == RoleChoices.SUPER_ADMIN:
        return
    if request.user.etablissement_id is None or etablissement_id != request.user.etablissement_id:
        raise PermissionDenied("Cette opération concerne un autre établissement.")


@login_required
def releve_list(request):
    """Relevés importés et paiements Mobile Money saisis au guichet non encore confirmés par un relevé."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = getattr(request.user, 'etablissement', None)
    releves = ReleveMobileMoney.objects.select_related('importe_par', 'rubrique').annotate(
        nb_lignes=Count('lignes'),
        total=Sum('lignes__montant'),
        nb_a_traiter=Count('lignes', filter=Q(lignes__statut__in=STATUTS_A_TRAITER)),
    )
    a_rapprocher = Paiement.objects.filter(
        mode_paiement=ModePaiement.MOBILE_MONEY, ligne_releve__isnull=True,
    ).select_related('inscription__eleve', 'inscription__classe').order_by('-date_paiement', '-created_at')
    if etab is not None:
        releves = releves.filter(etablissement=etab)
        a_rapprocher = a_rapprocher.filter(inscription__classe__etablissement=etab)
    return render(request, 'finances/releve_list.html', {
        'releves': releves,
        'a_rapprocher': a_rapprocher[:50],
        'nb_a_rapprocher': a_rapprocher.count(),
    })


@login_required
def releve_import(request):
    """Import d'un relevé marchand Orange Money / Moov Money (CSV ou Excel)."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = getattr(request.user, 'etablissement', None)
    if etab is None:
        messages.error(request, "L'import d'un relevé nécessite un compte rattaché à un établissement.")
        return redirect('finances:releve_list')
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')
    if request.method == 'POST':
        operateur = request.POST.get('operateur', '')
        fichier = request.FILES.get('fichier')
        try:
            rubrique = rubriques.filter(pk=request.POST.get('rubrique')).first() if request.POST.get('rubrique') else None
        except (ValueError, ValidationError):
            rubrique = None
        if operateur not in OperateurMobileMoney.values or fichier is None:
            messages.error(request, "Choisir l'opérateur et le fichier du relevé.")
        else:
            try:
                releve = importer_releve(etab, operateur, fichier, request.user, rubrique)
            except FichierInvalide as exc:
                messages.error(request, str(exc))
            else:
                nb = releve.lignes.count()
                messages.success(
                    request,
                    f"Relevé importé : {nb} transaction(s) nouvelle(s), {releve.nb_doublons} déjà connue(s), "
                    f"{releve.nb_rejets} ligne(s) ignorée(s) (débits, totaux, lignes illisibles)."
                )
                return redirect('finances:releve_detail', pk=releve.pk)
    return render(request, 'finances/releve_import.html', {
        'rubriques': rubriques,
        'operateurs': OperateurMobileMoney.choices,
    })


@login_required
def releve_detail(request, pk):
    """Écran de rapprochement d'un relevé : totaux, lignes à traiter, validation."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    releve = get_object_or_404(ReleveMobileMoney.objects.select_related('rubrique', 'importe_par'), pk=pk)
    _verifier_etablissement(request, releve.etablissement_id)
    Statut = LigneReleve.Statut
    lignes = releve.lignes.select_related('inscription__eleve', 'inscription__classe', 'paiement')
    totaux = lignes.aggregate(
        total=Sum('montant'), frais=Sum('frais'),
        rapproche=Sum('montant', filter=Q(statut=Statut.RAPPROCHE)),
        a_traiter=Sum('montant', filter=Q(statut__in=STATUTS_A_TRAITER)),
        ignore=Sum('montant', filter=Q(statut=Statut.IGNORE)),
        nb_rapproche=Count('pk', filter=Q(statut=Statut.RAPPROCHE)),
        nb_a_traiter=Count('pk', filter=Q(statut__in=STATUTS_A_TRAITER)),
        nb_ignore=Count('pk', filter=Q(statut=Statut.IGNORE)),
    )
    ordre = {Statut.PROPOSE: 0, Statut.A_CONFIRMER: 1, Statut.NON_IDENTIFIE: 2, Statut.RAPPROCHE: 3, Statut.IGNORE: 4}
    return render(request, 'finances/releve_detail.html', {
        'releve': releve,
        'lignes': sorted(lignes, key=lambda l: (ordre[l.statut], l.date_operation)),
        'totaux': totaux,
        'nb_lignes': len(lignes),
    })


@login_required
@require_POST
def releve_valider(request, pk):
    """Crée les paiements des lignes cochées (proposées / à confirmer)."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    releve = get_object_or_404(ReleveMobileMoney.objects.select_related('rubrique'), pk=pk)
    _verifier_etablissement(request, releve.etablissement_id)
    crees, erreurs = valider_lignes(releve, request.POST.getlist('lignes'), request.user)
    if crees:
        messages.success(request, f"{crees} paiement(s) Mobile Money enregistré(s) avec reçu.")
    elif not erreurs:
        messages.info(request, "Aucune ligne cochée à valider.")
    for erreur in erreurs:
        messages.error(request, erreur)
    return redirect('finances:releve_detail', pk=releve.pk)


@login_required
@require_POST
def releve_ligne_affecter(request, pk):
    """Affecte manuellement une transaction à un élève (matricule)."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    ligne = get_object_or_404(LigneReleve.objects.select_related('releve'), pk=pk)
    _verifier_etablissement(request, ligne.releve.etablissement_id)
    ok, message = affecter_ligne(ligne, request.POST.get('matricule', ''), request.user)
    (messages.success if ok else messages.error)(request, message)
    return redirect('finances:releve_detail', pk=ligne.releve_id)


@login_required
@require_POST
def releve_ligne_ignorer(request, pk):
    """Exclut une transaction du rapprochement (motif obligatoire)."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    ligne = get_object_or_404(LigneReleve.objects.select_related('releve'), pk=pk)
    _verifier_etablissement(request, ligne.releve.etablissement_id)
    ok, message = ignorer_ligne(ligne, request.POST.get('motif', ''), request.user)
    (messages.success if ok else messages.error)(request, message)
    return redirect('finances:releve_detail', pk=ligne.releve_id)
