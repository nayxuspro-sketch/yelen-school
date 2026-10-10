"""Bourses, boursiers et types de bourse.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import io
from ..models import BourseEleve, TypeBourse, TypeReduction
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe, RubriquePaiement
from core.utils import get_etablissement_context
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from .commun import WeasyHTML, _require_finance_role, _require_same_establishment


@login_required
def bourse_create(request, inscription_id):
    """Attribuer une bourse ou aide scolaire à une inscription."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    _require_same_establishment(request, inscription)
    etab = inscription.classe.etablissement

    types_bourses = TypeBourse.objects.filter(etablissement=etab, actif=True).order_by('nom')
    from parametres.models import RubriquePaiement
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')

    if request.method == 'POST':
        type_bourse_id = request.POST.get('type_bourse')
        montant_raw = request.POST.get('montant_accorde', '').replace(',', '.').strip()
        rubrique_id = request.POST.get('rubrique') or None
        date_attr = request.POST.get('date_attribution') or str(timezone.now().date())
        date_exp = request.POST.get('date_expiration') or None
        reference = request.POST.get('reference_document', '').strip()
        observation = request.POST.get('observation', '').strip()

        errors = []
        type_bourse = None
        montant = None

        try:
            type_bourse = TypeBourse.objects.get(pk=type_bourse_id, etablissement=etab)
        except (TypeBourse.DoesNotExist, ValueError, ValidationError):
            errors.append("Type de bourse invalide.")

        try:
            montant = Decimal(montant_raw)
            if not montant.is_finite() or montant <= 0:
                errors.append("Le montant doit être positif.")
        except (InvalidOperation, ValueError):
            errors.append("Montant invalide.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            rubrique = None
            if rubrique_id:
                from parametres.models import RubriquePaiement as RP
                try:
                    rubrique = RP.objects.filter(
                        pk=rubrique_id, etablissement=etab
                    ).first()
                except (ValueError, ValidationError):
                    rubrique = None

            BourseEleve.objects.create(
                inscription=inscription,
                type_bourse=type_bourse,
                montant_accorde=montant,
                rubrique=rubrique,
                date_attribution=date_attr,
                date_expiration=date_exp or None,
                reference_document=reference,
                observation=observation,
                attribue_par=request.user,
                created_by=request.user,
                updated_by=request.user,
                actif=True,
            )
            messages.success(
                request,
                f"Bourse \u00ab\u00a0{type_bourse.nom}\u00a0\u00bb de {montant:,.0f} FCFA attribuee a "
                f"{inscription.eleve.get_nom_complet()}."
            )
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)

    return render(request, 'finances/bourse_form.html', {
        'inscription': inscription,
        'types_bourses': types_bourses,
        'rubriques': rubriques,
        'today': timezone.now().date().isoformat(),
    })


@login_required
def bourse_edit(request, bourse_id):
    """Modifier une bourse attribuee."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    bourse = get_object_or_404(BourseEleve, pk=bourse_id, is_active=True, actif=True)
    inscription = bourse.inscription
    _require_same_establishment(request, inscription)
    etab = inscription.classe.etablissement

    types_bourses = TypeBourse.objects.filter(etablissement=etab, actif=True).order_by('nom')
    from parametres.models import RubriquePaiement
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')

    if request.method == 'POST':
        type_bourse_id = request.POST.get('type_bourse')
        montant_raw = request.POST.get('montant_accorde', '').replace(',', '.').strip()
        rubrique_id = request.POST.get('rubrique') or None
        date_attr = request.POST.get('date_attribution') or str(timezone.now().date())
        date_exp = request.POST.get('date_expiration') or None
        reference = request.POST.get('reference_document', '').strip()
        observation = request.POST.get('observation', '').strip()
        actif = request.POST.get('actif') == 'on'

        errors = []
        type_bourse = None
        montant = None

        try:
            type_bourse = TypeBourse.objects.get(pk=type_bourse_id, etablissement=etab)
        except (TypeBourse.DoesNotExist, ValueError, ValidationError):
            errors.append("Type de bourse invalide.")

        try:
            montant = Decimal(montant_raw)
            if not montant.is_finite() or montant <= 0:
                errors.append("Le montant doit etre positif.")
        except (InvalidOperation, ValueError):
            errors.append("Montant invalide.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            rubrique = None
            if rubrique_id:
                from parametres.models import RubriquePaiement as RP
                try:
                    rubrique = RP.objects.filter(
                        pk=rubrique_id, etablissement=etab
                    ).first()
                except (ValueError, ValidationError):
                    rubrique = None

            bourse.type_bourse = type_bourse
            bourse.montant_accorde = montant
            bourse.rubrique = rubrique
            bourse.date_attribution = date_attr
            bourse.date_expiration = date_exp or None
            bourse.reference_document = reference
            bourse.observation = observation
            bourse.actif = actif
            bourse.updated_by = request.user
            bourse._audit_reason = 'Modification d’une attribution de bourse'
            bourse.save()
            messages.success(request, "Bourse mise a jour.")
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)

    return render(request, 'finances/bourse_form.html', {
        'inscription': inscription,
        'bourse': bourse,
        'types_bourses': types_bourses,
        'rubriques': rubriques,
        'today': timezone.now().date().isoformat(),
    })


@login_required
@require_POST
def bourse_delete(request, bourse_id):
    """Désactiver une bourse sans supprimer l'historique."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    bourse = get_object_or_404(BourseEleve, pk=bourse_id, is_active=True, actif=True)
    _require_same_establishment(request, bourse.inscription)
    inscription_id = bourse.inscription_id
    nom = bourse.type_bourse.nom
    reason = request.POST.get('motif', '').strip()
    if not reason:
        messages.error(request, "Le motif de désactivation est obligatoire.")
    else:
        bourse._audit_reason = reason
        bourse.actif = False
        bourse.is_active = False
        bourse.updated_by = request.user
        bourse.save(update_fields=['actif', 'is_active', 'updated_by', 'updated_at'])
        messages.success(request, f"Bourse {nom!r} désactivée et conservée.")
    return redirect('finances:situation_eleve', inscription_id=inscription_id)


@login_required
def boursiers_list(request):
    """Liste globale de tous les eleves beneficiant d'une bourse ou aide scolaire."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    source = request.GET.get('source', '')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('nom')

    qs = BourseEleve.objects.filter(
        inscription__annee_scolaire=annee_sel,
        inscription__classe__etablissement=etab,
        actif=True,
        is_active=True,
    ).select_related(
        'inscription__eleve', 'inscription__classe',
        'type_bourse', 'rubrique',
    ).order_by('inscription__classe__nom', 'inscription__eleve__nom')

    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if source:
        qs = qs.filter(type_bourse__source=source)

    total_reduction = qs.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')

    from ..models import SourceBourse
    return render(request, 'finances/boursiers_list.html', {
        'bourses': qs,
        'annees': annees,
        'annee_sel': annee_sel,
        'classes': classes,
        'classe_id': classe_id,
        'source_sel': source,
        'source_choices': SourceBourse.choices,
        'total_reduction': total_reduction,
    })


@login_required
def boursiers_pdf(request):
    """PDF - Liste des boursiers/beneficiaires d'aides."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur ce serveur.")
        return redirect('finances:boursiers_list')
    etab = request.user.etablissement
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    source = request.GET.get('source', '')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    qs = BourseEleve.objects.filter(
        inscription__annee_scolaire=annee_sel,
        inscription__classe__etablissement=etab,
        actif=True,
        is_active=True,
    ).select_related(
        'inscription__eleve', 'inscription__classe',
        'type_bourse', 'rubrique',
    ).order_by('inscription__classe__nom', 'inscription__eleve__nom')

    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if source:
        qs = qs.filter(type_bourse__source=source)

    total_reduction = qs.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')

    etab_context = get_etablissement_context(etab, request)
    html_string = render_to_string('finances/pdf/liste_boursiers.html', {
        'bourses': qs,
        'annee_sel': annee_sel,
        'total_reduction': total_reduction,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'now': timezone.now(),
    }, request=request)

    buffer = io.BytesIO()
    WeasyHTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="boursiers.pdf"'
    return response


@login_required
def type_bourse_list(request):
    """Gerer les types de bourses de l'etablissement."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    types = TypeBourse.objects.filter(etablissement=etab).order_by('nom')
    return render(request, 'finances/type_bourse_list.html', {'types': types})


@login_required
def type_bourse_form(request, type_id=None):
    """Creer ou modifier un type de bourse."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = request.user.etablissement
    instance = get_object_or_404(TypeBourse, pk=type_id, etablissement=etab) if type_id else None

    from parametres.models import RubriquePaiement
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')
    from ..models import SourceBourse

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()
        source = request.POST.get('source', SourceBourse.ETABLISSEMENT)
        type_reduction = request.POST.get('type_reduction', TypeReduction.POURCENTAGE)
        valeur_raw = request.POST.get('valeur_reduction', '').replace(',', '.').strip()
        rubrique_id = request.POST.get('rubrique') or None
        actif = request.POST.get('actif') == 'on'

        errors = []
        valeur = None

        if not nom:
            errors.append("Le nom est obligatoire.")
        if not code:
            errors.append("Le code est obligatoire.")
        try:
            valeur = Decimal(valeur_raw)
            if not valeur.is_finite() or valeur <= 0:
                errors.append("La valeur de reduction doit etre positive.")
            if type_reduction == TypeReduction.POURCENTAGE and valeur > 100:
                errors.append("Un pourcentage ne peut pas depasser 100.")
        except (InvalidOperation, ValueError):
            errors.append("Valeur de reduction invalide.")

        if not errors:
            qs_code = TypeBourse.objects.filter(etablissement=etab, code=code)
            if instance:
                qs_code = qs_code.exclude(pk=instance.pk)
            if qs_code.exists():
                errors.append(f"Le code {code!r} est deja utilise.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            rubrique = None
            if rubrique_id:
                from parametres.models import RubriquePaiement as RP
                try:
                    rubrique = RP.objects.filter(
                        pk=rubrique_id, etablissement=etab
                    ).first()
                except (ValueError, ValidationError):
                    rubrique = None

            if instance:
                instance.nom = nom
                instance.code = code
                instance.description = description
                instance.source = source
                instance.type_reduction = type_reduction
                instance.valeur_reduction = valeur
                instance.rubrique = rubrique
                instance.actif = actif
                instance.updated_by = request.user
                instance._audit_reason = 'Modification d’un type de bourse'
                instance.save()
                messages.success(request, f"Type de bourse {nom!r} mis a jour.")
            else:
                TypeBourse.objects.create(
                    etablissement=etab, nom=nom, code=code, description=description,
                    source=source, type_reduction=type_reduction, valeur_reduction=valeur,
                    rubrique=rubrique, actif=actif,
                    created_by=request.user, updated_by=request.user,
                )
                messages.success(request, f"Type de bourse {nom!r} cree.")
            return redirect('finances:type_bourse_list')

    return render(request, 'finances/type_bourse_form.html', {
        'instance': instance,
        'rubriques': rubriques,
        'source_choices': SourceBourse.choices,
        'type_reduction_choices': TypeReduction.choices,
    })


@login_required
@require_POST
def type_bourse_delete(request, type_id):
    """Désactiver un type de bourse sans supprimer l'historique."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = request.user.etablissement
    tb = get_object_or_404(TypeBourse, pk=type_id, etablissement=etab)
    if tb.attributions.filter(actif=True, is_active=True).exists():
        messages.error(request, "Impossible de désactiver : des bourses actives utilisent ce type.")
    else:
        reason = request.POST.get('motif', '').strip()
        if not reason:
            messages.error(request, "Le motif de désactivation est obligatoire.")
        else:
            nom = tb.nom
            tb._audit_reason = reason
            tb.actif = False
            tb.is_active = False
            tb.updated_by = request.user
            tb.save(update_fields=['actif', 'is_active', 'updated_by', 'updated_at'])
            messages.success(request, f"Type {nom!r} désactivé et conservé.")
    return redirect('finances:type_bourse_list')


@login_required
def api_calculer_bourse(request):
    """AJAX - Calcule le montant d'une bourse a partir du type et du total du."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    type_id = request.GET.get('type_bourse')
    total_du_raw = request.GET.get('total_du', '0').replace(',', '.')
    try:
        total_du = Decimal(total_du_raw)
    except (InvalidOperation, ValueError):
        total_du = Decimal('0')

    try:
        tb_qs = TypeBourse.objects.filter(pk=type_id, actif=True, is_active=True)
        if request.user.etablissement_id is not None:
            tb_qs = tb_qs.filter(etablissement_id=request.user.etablissement_id)
        tb = tb_qs.get()
    except TypeBourse.DoesNotExist:
        return JsonResponse({'montant': '0'})

    if tb.type_reduction == TypeReduction.POURCENTAGE:
        montant = (total_du * tb.valeur_reduction / 100).quantize(Decimal('1'))
    else:
        montant = min(tb.valeur_reduction, total_du)

    return JsonResponse({
        'montant': str(montant),
        'type_reduction': tb.type_reduction,
        'valeur': str(tb.valeur_reduction),
        'description': tb.description,
    })
