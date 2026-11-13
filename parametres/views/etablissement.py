"""Fiche établissement, identité et droits d'accès par rôle."""
import logging

from django.db import DatabaseError
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST

from ..forms import (
    EtablissementBaseForm, IdentiteEtablissementForm, RolePersonnaliseForm,
)
from ..models import (
    DroitAcces, RolePersonnalise,
)
from etablissements.models import Etablissement

logger = logging.getLogger(__name__)
from .commun import _get_etab


# ─── FICHE UNIQUE DE L'ÉTABLISSEMENT ─────────────────────────────────

_CHAMPS_IDENTITE_PARTAGES = {
    'nom_etablissement': 'nom',
    'adresse_complete': 'adresse',
    'ville': 'ville',
    'telephone': 'telephone',
    'email': 'email',
}


def _initial_identite(etab, identite):
    """Pour les fiches historiques, complète l'identité officielle avec les anciennes données du site."""
    initial = {}
    for champ_identite, champ_site in _CHAMPS_IDENTITE_PARTAGES.items():
        valeur_identite = getattr(identite, champ_identite, '') if identite else ''
        valeur_site = getattr(etab, champ_site, '')
        if not valeur_identite and valeur_site:
            initial[champ_identite] = valeur_site
    return initial


def _fiche_etablissement(request):
    """Formulaire unique : chaque donnée commune est saisie une fois puis synchronisée pour l'application et les PDF."""
    from parametres.models import Cycle, IdentiteEtablissement

    etab = _get_etab(request)
    if not etab and request.user.is_superuser:
        etab = Etablissement.objects.first()
    if not etab and request.user.is_superuser:
        etab = Etablissement.objects.create(
            nom="Mon Établissement", code="ETAB001", pays="Burkina Faso",
        )
        request.user.etablissement = etab
        request.user.save(update_fields=['etablissement'])

    if not etab:
        return render(request, 'parametres/etablissement.html', {
            'etablissement': None,
            'error': "Votre compte n'est pas associé à un établissement.",
        })

    identite = IdentiteEtablissement.objects.filter(etablissement=etab).first()
    initial = _initial_identite(etab, identite)
    if request.method == 'POST':
        identite_form = IdentiteEtablissementForm(request.POST, request.FILES, instance=identite)
        etablissement_form = EtablissementBaseForm(request.POST, instance=etab)
        if identite_form.is_valid() and etablissement_form.is_valid():
            try:
                from parametres.services import enregistrer_fiche_etablissement
                etab, identite = enregistrer_fiche_etablissement(etab, identite_form, etablissement_form)
                messages.success(request, "Fiche de l'établissement mise à jour.")
                return redirect('parametres:etablissement')
            except (DatabaseError, ValidationError, ValueError, OSError) as exc:
                logger.exception("Mise à jour de la fiche établissement impossible")
                messages.error(request, f"La fiche n'a pas été enregistrée : {exc}")
        else:
            messages.error(request, "Corrigez les champs signalés avant d'enregistrer.")
    else:
        identite_form = IdentiteEtablissementForm(instance=identite, initial=initial)
        etablissement_form = EtablissementBaseForm(instance=etab)

    logo_actuel = (identite.logo if identite and identite.logo else etab.logo)
    cycles_configures = Cycle.objects.filter(etablissement=etab).order_by('ordre', 'nom')

    # Signature des documents : la direction générale désignée sur la fiche du personnel prime sur le
    # nom saisi ici (voir {% signataire_directeur_general %}), qui reste le repli.
    from personnel.models import MembrePersonnel
    directeur_general = (
        MembrePersonnel.objects.filter(etablissement=etab, est_directeur=True, is_active=True)
        .order_by('date_embauche').first()
    )

    return render(request, 'parametres/etablissement.html', {
        'etablissement': etab,
        'identite': identite,
        'cycles_configures': cycles_configures,
        'identite_form': identite_form,
        'etablissement_form': etablissement_form,
        'logo_actuel': logo_actuel,
        'directeur_general': directeur_general,
    })


@login_required
def etablissement_edit(request):
    return _fiche_etablissement(request)


@login_required
def identite_etablissement(request):
    """Ancienne URL conservée : elle ouvre désormais la fiche unique de l'établissement."""
    return _fiche_etablissement(request)


# ─── DROITS D'ACCÈS PAR RÔLE ──────────────────────────────────────

@login_required
def droits_acces(request):
    """Matrice rôles × fonctionnalités (et actions) de chaque module, réservée au Super Admin."""
    from core.models import RoleChoices
    from .. import droits

    if request.user.role != RoleChoices.SUPER_ADMIN:
        return HttpResponseForbidden("Accès réservé au Super Admin.")

    if request.method == 'POST':
        droits.enregistrer_matrice(set(request.POST.getlist('droit')), request.user)
        messages.success(request, "Droits d'accès enregistrés.")
        return redirect('parametres:droits_acces')

    role_a_modifier = None
    edit_role_pk = request.GET.get('edit_role')
    if edit_role_pk:
        try:
            role_a_modifier = RolePersonnalise.objects.get(pk=edit_role_pk)
        except (RolePersonnalise.DoesNotExist, ValueError):
            role_a_modifier = None

    matrice = droits.matrice_effective()
    libelles = {role.value: role.label for role in droits.ROLES_CONFIGURABLES}
    colonnes = [(r.code, r.libelle, libelles.get(r.base)) for r in droits.roles_configurables()]
    roles = [code for code, _, _ in colonnes]

    def ligne(module, f, action=None):
        if action is None:
            cases = [(role, f.prefixe in matrice[role]['fonctionnalites'][module.code]) for role in roles]
            return {'libelle': f.libelle, 'cle': f'{module.code}:{f.prefixe}:', 'niveau': 1, 'cases': cases}
        cases = [(role, (module.code, f.prefixe, action.code) in matrice[role]['actions']) for role in roles]
        return {'libelle': action.libelle, 'cle': f'{module.code}:{f.prefixe}:{action.code}', 'niveau': 2, 'cases': cases}

    blocs = [{
        'module': module,
        'roles': roles,
        'lignes': [ligne(module, f, a) for f in module.fonctionnalites for a in (None, *f.actions)],
    } for module in droits.MODULES]

    if role_a_modifier:
        form_role = RolePersonnaliseForm(instance=role_a_modifier)
    else:
        form_role = RolePersonnaliseForm()
    return render(request, 'parametres/droits_acces.html', {
        'roles': colonnes,
        'blocs': blocs,
        'roles_personnalises': RolePersonnalise.objects.annotate(nb_utilisateurs=Count('utilisateurs')).order_by('libelle'),
        'form_role': form_role,
        'role_a_modifier': role_a_modifier,
    })


@login_required
@require_POST
def role_personnalise_create(request):
    """Crée un rôle personnalisé (Super Admin) ; il hérite des droits de sa référence jusqu'au prochain enregistrement."""
    from core.models import RoleChoices
    from .. import droits

    if request.user.role != RoleChoices.SUPER_ADMIN:
        return HttpResponseForbidden("Accès réservé au Super Admin.")
    form = RolePersonnaliseForm(request.POST)
    if form.is_valid():
        role = form.save(commit=False)
        role.created_by = role.updated_by = request.user
        role.save()
        droits.invalider_cache()
        messages.success(request, f"Rôle « {role.libelle} » créé : il démarre avec les droits du rôle "
                                  f"« {role.base_libelle} » ; ajustez-les ci-dessous puis enregistrez.")
    else:
        messages.error(request, ' '.join(e for erreurs in form.errors.values() for e in erreurs))
    return redirect('parametres:droits_acces')


@login_required
@require_POST
def role_personnalise_delete(request, pk):
    """Supprime un rôle personnalisé sans utilisateur, et ses droits enregistrés."""
    from core.models import RoleChoices
    from .. import droits

    if request.user.role != RoleChoices.SUPER_ADMIN:
        return HttpResponseForbidden("Accès réservé au Super Admin.")
    role = get_object_or_404(RolePersonnalise, pk=pk)
    nb = role.utilisateurs.count()
    if nb:
        messages.error(request, f"Impossible de supprimer « {role.libelle} » : {nb} utilisateur(s) le portent encore ; "
                                "attribuez-leur d'abord un autre rôle.")
    else:
        DroitAcces.objects.filter(role=role.code).delete()
        role.delete()
        droits.invalider_cache()
        messages.success(request, f"Rôle « {role.libelle} » supprimé.")
    return redirect('parametres:droits_acces')


@login_required
@require_POST
def role_personnalise_update(request, pk):
    """Modifie le libellé et le rôle de référence d'un rôle personnalisé — Super Admin."""
    from core.models import RoleChoices
    from .. import droits

    if request.user.role != RoleChoices.SUPER_ADMIN:
        return HttpResponseForbidden("Accès réservé au Super Admin.")
    role = get_object_or_404(RolePersonnalise, pk=pk)
    form = RolePersonnaliseForm(request.POST, instance=role)
    if form.is_valid():
        form.save()
        droits.invalider_cache()
        messages.success(request, f"Rôle « {role.libelle} » modifié.")
    else:
        messages.error(request, ' '.join(e for erreurs in form.errors.values() for e in erreurs))
    return redirect('parametres:droits_acces')
