"""Vues de traitement des alertes de seuil d'absences."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import AlerteAbsences, SeuilAbsences


def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


# ═══════════════════════════════════════════════════════════════════
# ALERTES D'ABSENCES (seuil)
# ═══════════════════════════════════════════════════════════════════

_ROLES_SEUIL = ('SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR')


@login_required
def alertes_absences(request):
    """Élèves ayant atteint le seuil d'absences non justifiées : alertes à traiter, historique, réglage du seuil."""
    etab = _get_etab(request)
    reglage = SeuilAbsences.pour(etab) if etab else None
    toutes = request.GET.get('toutes') == '1'
    alertes = (AlerteAbsences.objects.filter(inscription__classe__etablissement=etab)
               .select_related('inscription__eleve', 'inscription__classe', 'traitee_par')) if etab else AlerteAbsences.objects.none()
    if not toutes:
        alertes = alertes.filter(traitee=False)
    return render(request, 'presences/alertes_absences.html', {
        'reglage': reglage, 'alertes': alertes[:300], 'toutes': toutes,
        'nb_a_traiter': AlerteAbsences.objects.filter(inscription__classe__etablissement=etab, traitee=False).count() if etab else 0,
        'peut_regler': request.user.role in _ROLES_SEUIL or request.user.is_superuser,
    })


@login_required
def alertes_absences_config(request):
    """Réglage du seuil (direction) : actif, seuil, période, SMS parent."""
    etab = _get_etab(request)
    if request.method != 'POST' or etab is None:
        return redirect('presences:alertes_absences')
    reglage = SeuilAbsences.pour(etab)
    try:
        seuil = int(request.POST.get('seuil', reglage.seuil))
    except (TypeError, ValueError):
        seuil = 0
    if not 1 <= seuil <= 60:
        messages.error(request, "Le seuil doit être compris entre 1 et 60 absences.")
        return redirect('presences:alertes_absences')
    reglage.seuil = seuil
    reglage.actif = request.POST.get('actif') == 'on'
    reglage.par_periode = request.POST.get('par_periode') == 'on'
    reglage.sms_parent = request.POST.get('sms_parent') == 'on'
    reglage.save(update_fields=['seuil', 'actif', 'par_periode', 'sms_parent', 'updated_at'])
    messages.success(request, f"Seuil enregistré : {seuil} absences non justifiées par "
                              f"{'période' if reglage.par_periode else 'année'}"
                              f"{'' if reglage.actif else ' (alertes désactivées)'}.")
    return redirect('presences:alertes_absences')


@login_required
def alerte_absences_traiter(request, alerte_id):
    """Marque l'alerte traitée (convocation, entretien) avec la suite donnée."""
    from django.utils import timezone
    if request.method != 'POST':
        return redirect('presences:alertes_absences')
    alerte = get_object_or_404(AlerteAbsences, pk=alerte_id, inscription__classe__etablissement=_get_etab(request))
    alerte.traitee = True
    alerte.traitee_par = request.user
    alerte.traitee_le = timezone.now()
    alerte.observation = request.POST.get('observation', '').strip()[:200]
    alerte.save(update_fields=['traitee', 'traitee_par', 'traitee_le', 'observation', 'updated_at'])
    messages.success(request, f"Alerte de {alerte.inscription.eleve.get_nom_complet()} marquée traitée.")
    return redirect('presences:alertes_absences')
