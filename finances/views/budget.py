"""Budget prévisionnel, catégories et dépenses, tableau de bord budgétaire.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse
from decimal import Decimal, InvalidOperation
import io
from ..models import Paiement, ModePaiement, CategorieDepense, BudgetAnnuel, Depense, StatutDepense
from parametres.models import AnneeScolaire
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES, FINANCE_APPROVER_ROLES
from .commun import _require_finance_role


def _etab_and_annee(request):
    """Retourne (etablissement, annee_courante) pour l'utilisateur connecté."""
    etab = getattr(request.user, 'etablissement', None)
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None
    return etab, annee


def _get_annees(etab):
    qs = AnneeScolaire.objects.order_by('-libelle')
    if etab:
        qs = qs.filter(etablissement=etab)
    return qs


@login_required
def categorie_depense_list(request):
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab, _ = _etab_and_annee(request)
    categories = CategorieDepense.objects.filter(etablissement=etab).order_by('type_depense', 'nom')
    return render(request, 'finances/categorie_depense_list.html', {
        'categories': categories,
    })


@login_required
def categorie_depense_form(request, pk=None):
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    from ..models import TypeDepense
    etab, _ = _etab_and_annee(request)
    instance = get_object_or_404(CategorieDepense, pk=pk, etablissement=etab) if pk else None
    error = None

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        code = request.POST.get('code', '').strip().upper()
        type_depense = request.POST.get('type_depense', TypeDepense.AUTRE)
        actif = request.POST.get('actif') == 'on'

        if not nom or not code:
            error = "Le nom et le code sont obligatoires."
        elif CategorieDepense.objects.filter(
            etablissement=etab, code=code
        ).exclude(pk=pk).exists():
            error = f"Le code « {code} » est déjà utilisé."
        else:
            if instance:
                instance.nom = nom
                instance.code = code
                instance.type_depense = type_depense
                instance.actif = actif
                instance.updated_by = request.user
                instance._audit_reason = 'Modification d’une catégorie de dépense'
                instance.save()
                messages.success(request, f"Catégorie « {nom} » mise à jour.")
            else:
                CategorieDepense.objects.create(
                    etablissement=etab, nom=nom, code=code,
                    type_depense=type_depense, actif=actif,
                    created_by=request.user, updated_by=request.user,
                )
                messages.success(request, f"Catégorie « {nom} » créée.")
            return redirect('finances:categorie_depense_list')

    return render(request, 'finances/categorie_depense_form.html', {
        'instance': instance,
        'types': TypeDepense.choices,
        'error': error,
    })


@login_required
@require_POST
def categorie_depense_delete(request, pk):
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab, _ = _etab_and_annee(request)
    cat = get_object_or_404(CategorieDepense, pk=pk, etablissement=etab)
    if cat.depenses.exists():
        messages.error(request, "Impossible de supprimer : des dépenses utilisent cette catégorie.")
    else:
        reason = request.POST.get('motif', '').strip()
        if not reason:
            messages.error(request, "Le motif de désactivation est obligatoire.")
        else:
            cat._audit_reason = reason
            cat.actif = False
            cat.is_active = False
            cat.updated_by = request.user
            cat.save(update_fields=['actif', 'is_active', 'updated_by', 'updated_at'])
            messages.success(request, "Catégorie désactivée et conservée dans l'historique.")
    return redirect('finances:categorie_depense_list')


@login_required
def depense_list(request):
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab, annee_courante = _etab_and_annee(request)
    annees = _get_annees(etab)

    annee_id = request.GET.get('annee')
    cat_id = request.GET.get('categorie')
    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '').strip()

    annee_sel = None
    if annee_id:
        annee_sel = annees.filter(pk=annee_id).first()
    if not annee_sel:
        annee_sel = annee_courante

    qs = Depense.objects.select_related(
        'categorie', 'annee_scolaire', 'saisi_par', 'valide_par'
    ).filter(annee_scolaire__etablissement=etab)

    if annee_sel:
        qs = qs.filter(annee_scolaire=annee_sel)
    if cat_id:
        qs = qs.filter(categorie_id=cat_id)
    if statut:
        qs = qs.filter(statut=statut)
    if q:
        qs = qs.filter(
            Q(libelle__icontains=q) | Q(beneficiaire__icontains=q) |
            Q(numero_depense__icontains=q) | Q(reference__icontains=q)
        )

    total = qs.filter(statut=StatutDepense.VALIDEE).aggregate(s=Sum('montant'))['s'] or Decimal('0')
    categories = CategorieDepense.objects.filter(etablissement=etab, actif=True)

    return render(request, 'finances/depense_list.html', {
        'depenses': qs.order_by('-date_depense'),
        'annees': annees,
        'annee_sel': annee_sel,
        'categories': categories,
        'cat_id': cat_id or '',
        'statut': statut,
        'q': q,
        'total_valide': total,
        'statuts': StatutDepense.choices,
    })


@login_required
def depense_form(request, pk=None):
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab, annee_courante = _etab_and_annee(request)
    instance = get_object_or_404(Depense, pk=pk, annee_scolaire__etablissement=etab) if pk else None

    if instance and instance.statut == StatutDepense.VALIDEE:
        messages.error(request, "Une dépense validée ne peut pas être modifiée.")
        return redirect('finances:depense_list')

    categories = CategorieDepense.objects.filter(etablissement=etab, actif=True)
    annees = _get_annees(etab)
    error = None

    if request.method == 'POST':
        libelle     = request.POST.get('libelle', '').strip()
        montant_str = request.POST.get('montant', '').strip()
        cat_id      = request.POST.get('categorie')
        annee_id    = request.POST.get('annee_scolaire')
        date_dep    = request.POST.get('date_depense')
        mode        = request.POST.get('mode_paiement', ModePaiement.ESPECES)
        beneficiaire = request.POST.get('beneficiaire', '').strip()
        reference   = request.POST.get('reference', '').strip()
        observation = request.POST.get('observation', '').strip()

        try:
            montant = Decimal(montant_str.replace(' ', '').replace(',', '.'))
            if not montant.is_finite() or montant <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            error = "Montant invalide."

        if not libelle:
            error = "Le libellé est obligatoire."

        if not error:
            categorie = get_object_or_404(CategorieDepense, pk=cat_id, etablissement=etab)
            annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
            if instance:
                instance.libelle = libelle
                instance.montant = montant
                instance.categorie = categorie
                instance.annee_scolaire = annee
                instance.date_depense = date_dep
                instance.mode_paiement = mode
                instance.beneficiaire = beneficiaire
                instance.reference = reference
                instance.observation = observation
                instance.updated_by = request.user
                instance._audit_reason = 'Modification d’une dépense en brouillon'
                instance.save()
                messages.success(request, f"Dépense {instance.numero_depense} mise à jour.")
            else:
                dep = Depense.objects.create(
                    annee_scolaire=annee, categorie=categorie,
                    libelle=libelle, montant=montant, date_depense=date_dep,
                    mode_paiement=mode, beneficiaire=beneficiaire,
                    reference=reference, observation=observation,
                    statut=StatutDepense.BROUILLON,
                    saisi_par=request.user, created_by=request.user, updated_by=request.user,
                )
                messages.success(request, f"Dépense {dep.numero_depense} créée.")
            return redirect('finances:depense_list')

    from datetime import date as _date
    return render(request, 'finances/depense_form.html', {
        'instance': instance,
        'categories': categories,
        'annees': annees,
        'annee_courante': annee_courante,
        'modes': ModePaiement.choices,
        'error': error,
        'today': _date.today().isoformat(),
    })


@login_required
@require_POST
def depense_delete(request, pk):
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab, _ = _etab_and_annee(request)
    reason = request.POST.get('motif', '').strip()
    with transaction.atomic():
        dep = get_object_or_404(
            Depense.objects.select_for_update(),
            pk=pk,
            annee_scolaire__etablissement=etab,
        )
        if dep.statut == StatutDepense.VALIDEE:
            messages.error(request, "Une dépense validée doit être annulée par un approbateur, pas supprimée.")
        elif not reason:
            messages.error(request, "Le motif d'annulation est obligatoire.")
        else:
            num = dep.numero_depense
            dep._audit_reason = reason
            dep.motif_annulation = reason
            dep.statut = StatutDepense.ANNULEE
            dep.updated_by = request.user
            dep.save(update_fields=['statut', 'motif_annulation', 'updated_by', 'updated_at'])
            messages.success(request, f"Dépense {num} annulée et conservée dans l'historique.")
    return redirect('finances:depense_list')


@login_required
@require_POST
def depense_valider(request, pk):
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    etab, _ = _etab_and_annee(request)
    with transaction.atomic():
        dep = get_object_or_404(
            Depense.objects.select_for_update(),
            pk=pk,
            annee_scolaire__etablissement=etab,
        )
        if dep.statut != StatutDepense.BROUILLON:
            messages.error(request, "Seule une dépense en brouillon peut être validée.")
        elif dep.saisi_par_id == request.user.pk:
            messages.error(request, "Le saisisseur ne peut pas valider sa propre dépense.")
        else:
            import datetime as _dt
            dep._audit_reason = request.POST.get('motif', '').strip() or 'Validation de dépense par un approbateur'
            dep.statut = StatutDepense.VALIDEE
            dep.valide_par = request.user
            dep.date_validation = _dt.date.today()
            dep.updated_by = request.user
            dep.save(update_fields=['statut', 'valide_par', 'date_validation', 'updated_by', 'updated_at'])
            messages.success(request, f"Dépense {dep.numero_depense} validée.")
    return redirect('finances:depense_list')


@login_required
@require_POST
def depense_annuler(request, pk):
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    etab, _ = _etab_and_annee(request)
    reason = request.POST.get('motif', '').strip()
    with transaction.atomic():
        dep = get_object_or_404(
            Depense.objects.select_for_update(),
            pk=pk,
            annee_scolaire__etablissement=etab,
        )
        if dep.statut == StatutDepense.ANNULEE:
            messages.error(request, "Cette dépense est déjà annulée.")
        elif not reason:
            messages.error(request, "Le motif d'annulation est obligatoire.")
        else:
            dep._audit_reason = reason
            dep.motif_annulation = reason
            dep.statut = StatutDepense.ANNULEE
            dep.updated_by = request.user
            dep.save(update_fields=['statut', 'motif_annulation', 'updated_by', 'updated_at'])
            messages.success(request, f"Dépense {dep.numero_depense} annulée.")
    return redirect('finances:depense_list')


@login_required
def budget_previsionnel(request):
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab, annee_courante = _etab_and_annee(request)
    annees = _get_annees(etab)

    annee_id = request.GET.get('annee')
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    categories = CategorieDepense.objects.filter(etablissement=etab, actif=True)

    if request.method == 'POST' and annee_sel:
        budgets_a_ecrire = []
        budget_errors = []
        for cat in categories:
            val = request.POST.get(f'budget_{cat.pk}', '').strip()
            try:
                montant = Decimal(val.replace(' ', '').replace(',', '.'))
                if not montant.is_finite() or montant < 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                budget_errors.append(f"Montant invalide pour « {cat.nom} ».")
                continue
            budgets_a_ecrire.append((cat, montant))

        if budget_errors:
            for error in budget_errors:
                messages.error(request, error)
        else:
            with transaction.atomic():
                for cat, montant in budgets_a_ecrire:
                    budget, created = BudgetAnnuel.objects.get_or_create(
                        annee_scolaire=annee_sel,
                        categorie=cat,
                        defaults={
                            'montant_prevu': montant,
                            'created_by': request.user,
                            'updated_by': request.user,
                        },
                    )
                    if not created:
                        budget._audit_reason = 'Mise à jour du budget prévisionnel'
                        budget.montant_prevu = montant
                        budget.updated_by = request.user
                        budget.save(update_fields=['montant_prevu', 'updated_by', 'updated_at'])
            messages.success(request, "Budget prévisionnel enregistré.")
            return redirect(f"{request.path}?annee={annee_sel.pk}")

    budgets_map = {}
    if annee_sel:
        for b in BudgetAnnuel.objects.filter(annee_scolaire=annee_sel, categorie__etablissement=etab):
            budgets_map[b.categorie_id] = b.montant_prevu

    lignes_budget = [
        {'categorie': cat, 'montant': budgets_map.get(cat.pk, Decimal('0'))}
        for cat in categories
    ]
    total_prevu = sum(budgets_map.values(), Decimal('0'))

    return render(request, 'finances/budget_previsionnel.html', {
        'annees': annees,
        'annee_sel': annee_sel,
        'categories': categories,
        'lignes_budget': lignes_budget,
        'total_prevu': total_prevu,
    })


@login_required
def tableau_bord_budget(request):
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    from django.db.models.functions import TruncMonth
    etab, annee_courante = _etab_and_annee(request)
    annees = _get_annees(etab)

    annee_id = request.GET.get('annee')
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    categories = CategorieDepense.objects.filter(etablissement=etab, actif=True)

    # Recettes (paiements validés de l'année)
    recettes_total = Decimal('0')
    if annee_sel:
        recettes_total = Paiement.objects.filter(
            inscription__annee_scolaire=annee_sel
        ).aggregate(s=Sum('montant'))['s'] or Decimal('0')

    # Dépenses validées par catégorie
    depenses_qs = Depense.objects.filter(
        annee_scolaire=annee_sel,
        statut=StatutDepense.VALIDEE,
    ) if annee_sel else Depense.objects.none()

    depenses_par_cat = {}
    for d in depenses_qs.values('categorie_id').annotate(total=Sum('montant')):
        depenses_par_cat[str(d['categorie_id'])] = d['total']

    budgets_par_cat = {}
    if annee_sel:
        for b in BudgetAnnuel.objects.filter(annee_scolaire=annee_sel, categorie__etablissement=etab):
            budgets_par_cat[str(b.categorie_id)] = b.montant_prevu

    lignes = []
    for cat in categories:
        prevu = budgets_par_cat.get(str(cat.pk), Decimal('0'))
        reel = depenses_par_cat.get(str(cat.pk), Decimal('0'))
        ecart = prevu - reel
        pct = int(reel / prevu * 100) if prevu else 0
        lignes.append({
            'categorie': cat,
            'prevu': prevu,
            'reel': reel,
            'ecart': ecart,
            'pct': min(pct, 100),
            'depasse': reel > prevu and prevu > 0,
        })

    total_depenses = depenses_qs.aggregate(s=Sum('montant'))['s'] or Decimal('0')
    total_prevu = sum(budgets_par_cat.values(), Decimal('0'))
    solde = recettes_total - total_depenses

    # Évolution mensuelle des dépenses
    evolution = list(
        depenses_qs.annotate(mois=TruncMonth('date_depense'))
        .values('mois')
        .annotate(total=Sum('montant'))
        .order_by('mois')
    )

    return render(request, 'finances/tableau_bord_budget.html', {
        'annees': annees,
        'annee_sel': annee_sel,
        'lignes': lignes,
        'recettes_total': recettes_total,
        'total_depenses': total_depenses,
        'total_prevu': total_prevu,
        'solde': solde,
        'evolution': evolution,
    })


@login_required
def tableau_bord_budget_xlsx(request):
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, numbers
    from openpyxl.utils import get_column_letter

    etab, annee_courante = _etab_and_annee(request)
    annees = _get_annees(etab)
    annee_id = request.GET.get('annee')
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    categories = CategorieDepense.objects.filter(etablissement=etab, actif=True)
    depenses_qs = Depense.objects.filter(
        annee_scolaire=annee_sel, statut=StatutDepense.VALIDEE
    ) if annee_sel else Depense.objects.none()

    depenses_par_cat = {
        str(d['categorie_id']): d['total']
        for d in depenses_qs.values('categorie_id').annotate(total=Sum('montant'))
    }
    budgets_par_cat = {}
    if annee_sel:
        for b in BudgetAnnuel.objects.filter(annee_scolaire=annee_sel, categorie__etablissement=etab):
            budgets_par_cat[str(b.categorie_id)] = b.montant_prevu

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Trésorerie"

    vert = '006B44'
    blanc = 'FFFFFF'
    gris = 'F5F5F5'

    # En-tête
    ws.merge_cells('A1:E1')
    ws['A1'] = f"TABLEAU DE BORD TRÉSORERIE — {annee_sel or 'Toutes années'}"
    ws['A1'].font = Font(bold=True, color=blanc, size=13)
    ws['A1'].fill = PatternFill('solid', fgColor=vert)
    ws['A1'].alignment = Alignment(horizontal='center')

    headers = ['Catégorie', 'Type', 'Budget prévu (FCFA)', 'Réel (FCFA)', 'Écart (FCFA)']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = Font(bold=True, color=blanc)
        cell.fill = PatternFill('solid', fgColor=vert)
        cell.alignment = Alignment(horizontal='center')

    fmt_num = '#,##0'
    for i, cat in enumerate(categories, 3):
        prevu = budgets_par_cat.get(str(cat.pk), Decimal('0'))
        reel = depenses_par_cat.get(str(cat.pk), Decimal('0'))
        fill = PatternFill('solid', fgColor=gris) if i % 2 == 0 else None
        row = [cat.nom, cat.get_type_depense_display(), float(prevu), float(reel), float(prevu - reel)]
        for col, val in enumerate(row, 1):
            cell = ws.cell(row=i, column=col, value=val)
            if fill:
                cell.fill = fill
            if col >= 3:
                cell.number_format = fmt_num

    # Largeurs colonnes
    for col, w in enumerate([30, 22, 20, 20, 20], 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    label = str(annee_sel).replace('/', '-') if annee_sel else 'bilan'
    resp = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resp['Content-Disposition'] = f'attachment; filename="tresorerie_{label}.xlsx"'
    return resp
