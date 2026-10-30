"""Journal de caisse : opérations d'une journée par caissier, arrêté de caisse (espèces comptées, écart),
réouverture par la direction, PDF."""
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.utils import fcfa, get_etablissement_context
from .. import caisse as services
from ..models import ClotureCaisse
from ..permissions import FINANCE_APPROVER_ROLES, FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from .commun import WeasyHTML, _require_finance_role


def _jour(request):
    try:
        return date.fromisoformat(request.GET.get('date') or request.POST.get('date') or '')
    except ValueError:
        return timezone.localdate()


def _caissier(request, etab, jour):
    """Caissier filtré : paramètre ``caissier`` parmi ceux ayant opéré ce jour ; sans paramètre, l'utilisateur
    connecté s'il a opéré (sa propre caisse) ; ``caissier=`` vide → toutes les caisses."""
    caissiers = services.caissiers_du_jour(etab, jour)
    voulu = request.GET.get('caissier')
    if voulu is None:
        voulu = str(request.user.pk)
    return caissiers, next((c for c in caissiers if str(c.pk) == voulu), None)


def _contexte_journal(etab, jour, caissier):
    paiements = services.paiements_du_jour(etab, jour, caissier)
    remboursements = services.remboursements_du_jour(etab, jour, caissier)
    clotures = ClotureCaisse.objects.filter(etablissement=etab, date=jour).select_related('caissier', 'cloture_par')
    return {
        'jour': jour,
        'caissier': caissier,
        'paiements': paiements,
        'remboursements': remboursements,
        'totaux': services.totaux_journee(paiements, remboursements),
        'clotures': clotures,
        'cloture_caissier': clotures.filter(caissier=caissier).first() if caissier else None,
    }


@login_required
def journal_caisse(request):
    """Journal de caisse d'une journée : encaissements et remboursements, totaux par mode, arrêtés de caisse."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    jour = _jour(request)
    caissiers, caissier = _caissier(request, etab, jour)
    contexte = _contexte_journal(etab, jour, caissier)
    contexte.update({
        'caissiers': caissiers,
        'peut_arreter': caissier is not None and caissier.pk == request.user.pk and contexte['cloture_caissier'] is None,
        'historique': ClotureCaisse.objects.filter(etablissement=etab).select_related('caissier')[:15],
    })
    return render(request, 'finances/journal_caisse.html', contexte)


@login_required
@require_POST
def caisse_arreter(request):
    """Arrêté de la caisse du jour de l'utilisateur connecté : espèces comptées, écart calculé et figé."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = request.user.etablissement
    jour = _jour(request)
    retour = reverse('finances:journal_caisse') + f'?date={jour.isoformat()}&caissier={request.user.pk}'
    try:
        montant_compte = Decimal(str(request.POST.get('montant_compte', '')).replace(',', '.').replace(' ', ''))
        if not montant_compte.is_finite() or montant_compte < 0:
            raise InvalidOperation
    except InvalidOperation:
        messages.error(request, "Indiquez le montant des espèces comptées (nombre positif).")
        return redirect(retour)
    try:
        cloture = services.arreter_caisse(etab, jour, request.user, montant_compte,
                                          request.POST.get('observation', ''), request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(retour)
    ecart = f"écart {cloture.ecart:+,.0f} FCFA".replace(',', ' ') if cloture.ecart else "aucun écart"
    messages.success(request, f"Caisse du {jour:%d/%m/%Y} arrêtée : {fcfa(cloture.especes_theoriques)} d'espèces "
                              f"attendues, {fcfa(montant_compte)} comptées ({ecart}).".replace(',', ' '))
    return redirect(retour)


@login_required
@require_POST
def caisse_rouvrir(request, pk):
    """Annule un arrêté de caisse (direction) : le caissier peut de nouveau saisir sur cette journée."""
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    cloture = get_object_or_404(ClotureCaisse, pk=pk, etablissement=request.user.etablissement)
    jour, caissier = cloture.date, cloture.caissier
    cloture.delete()
    messages.success(request, f"Caisse de {caissier.get_full_name()} du {jour:%d/%m/%Y} rouverte.")
    return redirect(reverse('finances:journal_caisse') + f'?date={jour.isoformat()}')


@login_required
def journal_caisse_pdf(request):
    """Journal de caisse PDF (A4 portrait) : opérations, totaux par mode, arrêté de caisse s'il existe."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:journal_caisse')
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    jour = _jour(request)
    _, caissier = _caissier(request, etab, jour)
    contexte = _contexte_journal(etab, jour, caissier)
    etab_context = get_etablissement_context(etab, request)
    contexte.update({
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'now': timezone.now(),
    })
    html_string = render_to_string('finances/pdf/journal_caisse.html', contexte, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Journal_Caisse_{jour.isoformat()}.pdf"'
    return response
