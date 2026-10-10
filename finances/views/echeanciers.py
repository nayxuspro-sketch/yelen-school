"""Échéanciers individuels et échéancier global.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from ..models import Echeancier
from ..forms import EcheancierForm
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from .commun import _require_finance_role, _require_same_establishment


@login_required
def echeancier_create(request, inscription_id):
    """Créer un échéancier pour un élève."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    _require_same_establishment(request, inscription)
    
    if request.method == 'POST':
        form = EcheancierForm(request.POST)
        if form.is_valid():
            echeancier = form.save(commit=False)
            echeancier.inscription = inscription
            echeancier.created_by = request.user
            echeancier.updated_by = request.user
            echeancier._audit_reason = 'Création d’une échéance financière'
            echeancier.save()
            messages.success(request, f"Échéance '{echeancier.libelle}' créée avec succès.")
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)
    else:
        form = EcheancierForm()
    
    return render(request, 'finances/echeancier_form.html', {
        'form': form,
        'inscription': inscription,
        'title': "Créer une échéance",
    })


@login_required
def echeancier_edit(request, echeancier_id):
    """Modifier une échéance existante."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    echeancier = get_object_or_404(Echeancier, pk=echeancier_id, is_active=True)
    inscription = echeancier.inscription
    _require_same_establishment(request, inscription)
    
    if request.method == 'POST':
        form = EcheancierForm(request.POST, instance=echeancier)
        if form.is_valid():
            echeancier = form.save(commit=False)
            echeancier.updated_by = request.user
            echeancier._audit_reason = 'Modification d’une échéance financière'
            echeancier.save()
            messages.success(request, f"Échéance '{echeancier.libelle}' mise à jour.")
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)
    else:
        form = EcheancierForm(instance=echeancier)
    
    return render(request, 'finances/echeancier_form.html', {
        'form': form,
        'inscription': inscription,
        'echeancier': echeancier,
        'title': "Modifier l'échéance",
    })


@login_required
def echeancier_delete(request, echeancier_id):
    """Désactiver une échéance sans supprimer la trace financière."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    echeancier = get_object_or_404(Echeancier, pk=echeancier_id, is_active=True)
    inscription = echeancier.inscription
    _require_same_establishment(request, inscription)
    
    if request.method == 'POST':
        reason = request.POST.get('motif', '').strip()
        if not reason:
            messages.error(request, "Le motif de désactivation est obligatoire.")
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)
        echeancier_name = echeancier.libelle
        echeancier._audit_reason = reason
        echeancier.is_active = False
        echeancier.updated_by = request.user
        echeancier.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        messages.success(request, f"Échéance '{echeancier_name}' désactivée et conservée.")
        return redirect('finances:situation_eleve', inscription_id=inscription.pk)
    
    return render(request, 'finances/echeancier_confirm_delete.html', {
        'echeancier': echeancier,
        'inscription': inscription,
    })


@login_required
def echeancier_global(request):
    """Vue globale de tous les échéanciers : en retard, à venir, payés."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    today = timezone.now().date()
    seuil_alerte = today + timezone.timedelta(days=7)

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_id = request.GET.get('annee', '')
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classe_id = request.GET.get('classe', '')
    statut = request.GET.get('statut', '')  # 'retard', 'alerte', 'avenir', 'paye'
    q = request.GET.get('q', '').strip()

    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('cycle__ordre', 'nom')

    qs = (
        Echeancier.objects
        .filter(
            inscription__annee_scolaire=annee_sel,
            inscription__classe__etablissement=etab,
            is_active=True,
        )
        .select_related('inscription__eleve', 'inscription__classe__cycle')
        .order_by('date_limite', 'inscription__eleve__nom')
    ) if annee_sel else Echeancier.objects.none()

    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if q:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=q) |
            Q(inscription__eleve__prenom__icontains=q) |
            Q(inscription__eleve__matricule__icontains=q) |
            Q(libelle__icontains=q)
        )

    # Compteurs globaux (avant filtre statut)
    nb_retard  = qs.filter(paye=False, date_limite__lt=today).count()
    nb_alerte  = qs.filter(paye=False, date_limite__gte=today, date_limite__lte=seuil_alerte).count()
    nb_avenir  = qs.filter(paye=False, date_limite__gt=seuil_alerte).count()
    nb_paye    = qs.filter(paye=True).count()
    total_du   = qs.filter(paye=False).aggregate(s=Sum('montant_du'))['s'] or Decimal('0')
    total_paye = qs.filter(paye=True).aggregate(s=Sum('montant_du'))['s'] or Decimal('0')

    if statut == 'retard':
        qs = qs.filter(paye=False, date_limite__lt=today)
    elif statut == 'alerte':
        qs = qs.filter(paye=False, date_limite__gte=today, date_limite__lte=seuil_alerte)
    elif statut == 'avenir':
        qs = qs.filter(paye=False, date_limite__gt=seuil_alerte)
    elif statut == 'paye':
        qs = qs.filter(paye=True)

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'finances/echeancier_global.html', {
        'annees': annees,
        'annee_sel': annee_sel,
        'classes': classes,
        'page_obj': page_obj,
        'today': today,
        'seuil_alerte': seuil_alerte,
        'nb_retard': nb_retard,
        'nb_alerte': nb_alerte,
        'nb_avenir': nb_avenir,
        'nb_paye': nb_paye,
        'total_du': total_du,
        'total_paye': total_paye,
        'statut': statut,
        'classe_id': classe_id,
        'q': q,
        'annee_id': annee_id,
    })


@login_required
def echeancier_global_xlsx(request):
    """Export Excel du tableau global des échéanciers."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    from core.excel import ExcelExport

    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    today = timezone.now().date()
    seuil_alerte = today + timezone.timedelta(days=7)

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_id = request.GET.get('annee', '')
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classe_id = request.GET.get('classe', '')
    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '').strip()

    qs = (
        Echeancier.objects
        .filter(
            inscription__annee_scolaire=annee_sel,
            inscription__classe__etablissement=etab,
            is_active=True,
        )
        .select_related('inscription__eleve', 'inscription__classe__cycle')
        .order_by('date_limite', 'inscription__eleve__nom')
    ) if annee_sel else Echeancier.objects.none()

    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if q:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=q) |
            Q(inscription__eleve__prenom__icontains=q) |
            Q(inscription__eleve__matricule__icontains=q) |
            Q(libelle__icontains=q)
        )
    if statut == 'retard':
        qs = qs.filter(paye=False, date_limite__lt=today)
    elif statut == 'alerte':
        qs = qs.filter(paye=False, date_limite__gte=today, date_limite__lte=seuil_alerte)
    elif statut == 'avenir':
        qs = qs.filter(paye=False, date_limite__gt=seuil_alerte)
    elif statut == 'paye':
        qs = qs.filter(paye=True)

    titre = f"Échéanciers{' — ' + annee_sel.libelle if annee_sel else ''}"
    nom_fichier = f"echeanciers{'_' + annee_sel.libelle if annee_sel else ''}.xlsx".replace(' ', '_')

    wb = ExcelExport("Échéanciers")
    wb.add_title(titre, subtitle=etab.nom)
    wb.add_header(['Élève', 'Matricule', 'Classe', 'Cycle', 'Échéance', 'Date limite', 'Montant dû (FCFA)', 'Statut'])

    ROUGE  = "FECACA"
    ORANGE = "FED7AA"
    VERT   = "BBF7D0"

    for ech in qs:
        eleve  = ech.inscription.eleve
        classe = ech.inscription.classe
        if ech.paye:
            couleur, statut_label = VERT, 'Payé'
        elif ech.date_limite < today:
            couleur, statut_label = ROUGE, 'En retard'
        elif ech.date_limite <= seuil_alerte:
            couleur, statut_label = ORANGE, 'Échéance proche'
        else:
            couleur, statut_label = None, 'À venir'

        wb.add_row([
            f"{eleve.nom} {eleve.prenom}",
            eleve.matricule or '',
            classe.nom if classe else '',
            classe.cycle.nom if classe and classe.cycle else '',
            ech.libelle,
            ech.date_limite.strftime('%d/%m/%Y'),
            float(ech.montant_du),
            statut_label,
        ], highlight_color=couleur)

    return wb.response(nom_fichier)
