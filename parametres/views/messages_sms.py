"""Modèles de messages et SMS automatiques."""
import logging

from django.core.management import call_command
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from io import StringIO

from ..models import (
    ModeleMessage, DeclencheurSMS,
)

logger = logging.getLogger(__name__)
from .commun import _get_etab


# ─── MODÈLES DE MESSAGES ──────────────────────────────────────────────────────

@login_required
def modeles_messages_list(request):
    """Liste et édition des modèles de messages SMS personnalisables."""
    etab = _get_etab(request)
    types = ModeleMessage.TypeChoices.choices
    modeles = {m.type: m for m in ModeleMessage.objects.filter(etablissement=etab)}
    items = []
    for code, label in types:
        modele = modeles.get(code)
        items.append({
            'code': code,
            'label': label,
            'modele': modele,
            'defaut': ModeleMessage.DEFAUTS.get(code, ''),
            'variables': _variables_par_type(code),
        })
    return render(request, 'parametres/modeles_messages.html', {
        'items': items,
        'etab': etab,
    })


@login_required
def modele_message_form(request, type_msg):
    """Sauvegarde (création ou mise à jour) d'un modèle de message."""
    etab = _get_etab(request)
    if type_msg not in dict(ModeleMessage.TypeChoices.choices):
        return HttpResponse('Type invalide', status=400)

    modele, _ = ModeleMessage.objects.get_or_create(
        etablissement=etab,
        type=type_msg,
        defaults={'contenu_sms': ModeleMessage.DEFAUTS.get(type_msg, '')},
    )

    if request.method == 'POST':
        contenu = request.POST.get('contenu_sms', '').strip()
        actif = 'actif' in request.POST
        if contenu:
            modele.contenu_sms = contenu
            modele.actif = actif
            modele.save(update_fields=['contenu_sms', 'actif', 'updated_at'])
            messages.success(request, f"Modèle « {modele.get_type_display()} » enregistré.")
        return redirect('parametres:modeles_messages')

    return render(request, 'parametres/partials/modele_message_form.html', {
        'modele': modele,
        'type_msg': type_msg,
        'label': dict(ModeleMessage.TypeChoices.choices).get(type_msg, ''),
        'defaut': ModeleMessage.DEFAUTS.get(type_msg, ''),
        'variables': _variables_par_type(type_msg),
    })


@login_required
@require_POST
def modele_message_reset(request, type_msg):
    """Réinitialise un modèle au contenu par défaut."""
    etab = _get_etab(request)
    defaut = ModeleMessage.DEFAUTS.get(type_msg, '')
    ModeleMessage.objects.filter(etablissement=etab, type=type_msg).update(
        contenu_sms=defaut
    )
    messages.success(request, "Modèle réinitialisé au contenu par défaut.")
    return redirect('parametres:modeles_messages')


def _variables_par_type(type_msg):
    """Retourne la liste des variables disponibles pour un type de message."""
    return {
        'BULLETIN': ['{nom_eleve}', '{classe}', '{trimestre}', '{etablissement}'],
        'ABSENCE':  ['{nom_eleve}', '{date}', '{matiere}', '{etablissement}'],
        'RETARD':   ['{nom_eleve}', '{date}', '{matiere}', '{etablissement}'],
        'PAIEMENT': ['{nom_eleve}', '{montant}', '{rubrique}', '{etablissement}'],
        'REUNION':  ['{date}', '{heure}', '{lieu}', '{objet}', '{etablissement}'],
        'SEUIL_ABSENCES': ['{nom_eleve}', '{classe}', '{nb}', '{periode}', '{etablissement}'],
        'SANCTION': ['{nom_eleve}', '{classe}', '{date}', '{sanction}', '{motif}', '{etablissement}'],
    }.get(type_msg, [])


# ─── SMS AUTOMATIQUES ─────────────────────────────────────────────────────────

_SMS_CONFIGURATION_ROLES = {'SUPER_ADMIN', 'DIRECTEUR'}


def _check_sms_configuration_access(request):
    """Retourne l'établissement autorisé pour la configuration SMS."""
    if getattr(request.user, 'role', None) not in _SMS_CONFIGURATION_ROLES:
        return None
    return _get_etab(request)


def _sms_enabled():
    """Interprète correctement les booléens issus du cache runtime ou settings."""
    from core.sms import sms_actifs

    return sms_actifs()


def _get_or_create_sms_triggers(etab):
    """Garantit l'existence d'un déclencheur par type pour l'établissement."""
    for trigger_type, _label in DeclencheurSMS.TypeChoices.choices:
        DeclencheurSMS.objects.get_or_create(
            etablissement=etab,
            type_declencheur=trigger_type,
        )
    return DeclencheurSMS.objects.filter(etablissement=etab).order_by('type_declencheur')


def _render_sms_trigger_list(request, etab):
    return render(request, 'parametres/partials/sms_declencheurs_list.html', {
        'declencheurs': _get_or_create_sms_triggers(etab),
        'sms_enabled': _sms_enabled(),
    })


@login_required
def sms_auto_config(request):
    """Configure les déclencheurs SMS automatiques de l'établissement courant."""
    etab = _check_sms_configuration_access(request)
    if not etab:
        return HttpResponseForbidden("Accès réservé aux directeurs et super administrateurs associés à un établissement.")

    return render(request, 'parametres/sms_auto.html', {
        'declencheurs': _get_or_create_sms_triggers(etab),
        'sms_enabled': _sms_enabled(),
    })


@login_required
@require_POST
def sms_auto_toggle(request, pk):
    """Active ou désactive un déclencheur SMS sans franchir l'établissement."""
    etab = _check_sms_configuration_access(request)
    if not etab:
        return HttpResponseForbidden("Accès interdit.")

    declencheur = get_object_or_404(DeclencheurSMS, pk=pk, etablissement=etab)
    declencheur.actif = not declencheur.actif
    declencheur.updated_by = request.user
    declencheur.save(update_fields=['actif', 'updated_by', 'updated_at'])
    return _render_sms_trigger_list(request, etab)


@login_required
@require_POST
def sms_auto_save(request, pk):
    """Enregistre le nombre de jours avant échéance pour un déclencheur."""
    etab = _check_sms_configuration_access(request)
    if not etab:
        return HttpResponseForbidden("Accès interdit.")

    declencheur = get_object_or_404(DeclencheurSMS, pk=pk, etablissement=etab)
    try:
        jours_avant = int(request.POST.get('jours_avant', ''))
    except (TypeError, ValueError):
        jours_avant = 0

    if not 1 <= jours_avant <= 30:
        messages.error(request, "Le rappel doit être compris entre 1 et 30 jours avant l'échéance.")
    else:
        declencheur.jours_avant = jours_avant
        declencheur.updated_by = request.user
        declencheur.save(update_fields=['jours_avant', 'updated_by', 'updated_at'])
        messages.success(request, "Paramètre du rappel d'échéancier enregistré.")

    return redirect('parametres:sms_auto_config')


@login_required
@require_POST
def sms_auto_executer(request, pk):
    """Exécute manuellement un déclencheur actif pour l'établissement courant."""
    etab = _check_sms_configuration_access(request)
    if not etab:
        return HttpResponseForbidden("Accès interdit.")

    declencheur = get_object_or_404(DeclencheurSMS, pk=pk, etablissement=etab)
    if not _sms_enabled():
        messages.error(request, "Les SMS sont désactivés dans la configuration SMS.")
        return redirect('parametres:sms_auto_config')
    if not declencheur.actif:
        messages.error(request, "Activez ce déclencheur avant de l'exécuter.")
        return redirect('parametres:sms_auto_config')

    output = StringIO()
    try:
        call_command(
            'sms_auto',
            type=declencheur.type_declencheur,
            etablissement=str(etab.pk),
            stdout=output,
            stderr=output,
        )
    except Exception as exc:
        logger.exception("Exécution de la commande SMS impossible")
        messages.error(request, f"Exécution SMS échouée : {exc}")
    else:
        lines = [line.strip() for line in output.getvalue().splitlines() if line.strip()]
        summary = lines[-1] if lines else 'Aucun SMS à envoyer.'
        messages.success(request, f"Déclencheur exécuté : {summary}")

    return redirect('parametres:sms_auto_config')
