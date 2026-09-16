from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from django.conf import settings

from .forms import LicenceForm, RenouvelerForm, RevoquerForm
from .models import Licence, StatutLicence, LIMITES_LICENCES, TypeLicence, FEATURE_FLAGS


# ── Garde superuser ───────────────────────────────────────────────────────────

def _superuser_required(view_func):
    """Réserve l'émission/révocation web au build fournisseur.

    En production cliente, les licences sont importées hors ligne par fichier
    signé ; un superutilisateur local ne doit pas pouvoir modifier les données
    commerciales depuis l'interface.
    """
    def can_manage(user):
        return bool(
            user.is_superuser
            and (
                not getattr(settings, 'LICENSE_ENFORCEMENT_ENABLED', True)
                or getattr(settings, 'LICENSE_ALLOW_SUPERUSER_BYPASS', False)
            )
        )

    return user_passes_test(can_manage, login_url='/')(view_func)


def _get_licence(user):
    etab = getattr(user, 'etablissement', None)
    if not etab:
        return None, None
    try:
        return etab, etab.licence
    except Licence.DoesNotExist:
        return etab, None


def _enrich(lic):
    jours = lic.jours_restants()
    return {
        'obj': lic,
        'jours_restants': jours,
        'jours_pct': max(0, min(100, round(jours / 365 * 100))) if jours is not None and jours >= 0 else 0,
        'signature_valide': lic.verifier_signature(),
        'limites': LIMITES_LICENCES.get(lic.type_licence, {}),
    }


# ── Liste / tableau de bord ───────────────────────────────────────────────────

@login_required
def gestion_licences(request):
    """Tableau de bord licences. Superusers : toutes. Autres : la leur."""
    if request.user.is_superuser:
        qs = Licence.objects.select_related('etablissement').order_by('statut', 'date_expiration')
        licences_enrichies = [_enrich(lic) for lic in qs]
    else:
        etab, licence = _get_licence(request.user)
        licences_enrichies = [_enrich(licence)] if licence else []

    context = {
        'licences': licences_enrichies,
        'is_superuser': request.user.is_superuser,
        'StatutLicence': StatutLicence,
    }
    return render(request, 'licences/gestion.html', context)


# ── Création ─────────────────────────────────────────────────────────────────

@login_required
@_superuser_required
def licence_create(request):
    """Créer une nouvelle licence pour un établissement."""
    form = LicenceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        licence = form.save()
        messages.success(request, f"Licence {licence.cle_licence} créée pour {licence.etablissement.nom}.")
        return redirect('licences:gestion')
    return render(request, 'licences/licence_form.html', {
        'form': form,
        'titre': 'Nouvelle licence',
        'submit_label': 'Créer la licence',
    })


# ── Modification ──────────────────────────────────────────────────────────────

@login_required
@_superuser_required
def licence_edit(request, pk):
    """Modifier le type et la date d'expiration d'une licence."""
    licence = get_object_or_404(Licence, pk=pk)
    form = LicenceForm(request.POST or None, instance=licence)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Licence {licence.cle_licence} mise à jour.")
        return redirect('licences:gestion')
    return render(request, 'licences/licence_form.html', {
        'form': form,
        'licence': licence,
        'titre': f'Modifier — {licence.cle_licence}',
        'submit_label': 'Enregistrer les modifications',
    })


# ── Activation ────────────────────────────────────────────────────────────────

@login_required
@_superuser_required
def licence_activer(request, pk):
    """Activer une licence en attente."""
    licence = get_object_or_404(Licence, pk=pk)
    if request.method == 'POST':
        if licence.statut == StatutLicence.EN_ATTENTE:
            licence.activer()
            messages.success(
                request,
                f"Licence {licence.cle_licence} activée — accès accordé à {licence.etablissement.nom}.",
            )
        else:
            messages.warning(request, f"Statut actuel : {licence.get_statut_display()}. Activation impossible.")
        return redirect('licences:gestion')
    return render(request, 'licences/licence_confirm.html', {
        'licence': licence,
        'action': 'activer',
        'titre': 'Activer la licence',
        'message': (
            f"Activer la licence <strong>{licence.cle_licence}</strong> pour"
            f" <strong>{licence.etablissement.nom}</strong> ?<br>"
            "L'établissement pourra accéder à l'application immédiatement."
        ),
        'btn_label': 'Activer',
        'btn_class': 'btn-primary',
    })


# ── Renouvellement ────────────────────────────────────────────────────────────

@login_required
@_superuser_required
def licence_renouveler(request, pk):
    """Renouveler une licence (choisir la durée)."""
    licence = get_object_or_404(Licence, pk=pk)
    form = RenouvelerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        duree = form.cleaned_data['duree_jours']
        licence.renouveler(duree_jours=duree)
        messages.success(
            request,
            f"Licence {licence.cle_licence} renouvelée — nouvelle expiration : {licence.date_expiration:%d/%m/%Y}."
        )
        return redirect('licences:gestion')
    return render(request, 'licences/licence_renouveler.html', {
        'form': form,
        'licence': licence,
    })


# ── Révocation ────────────────────────────────────────────────────────────────

@login_required
@_superuser_required
def licence_revoquer(request, pk):
    """Révoquer une licence avec saisie du motif."""
    licence = get_object_or_404(Licence, pk=pk)
    if licence.statut == StatutLicence.REVOQUEE:
        messages.info(request, "Cette licence est déjà révoquée.")
        return redirect('licences:gestion')
    form = RevoquerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        licence.revoquer(raison=form.cleaned_data['raison'])
        messages.warning(
            request,
            f"Licence {licence.cle_licence} révoquée — {licence.etablissement.nom} n'a plus accès.",
        )
        return redirect('licences:gestion')
    return render(request, 'licences/licence_revoquer.html', {
        'form': form,
        'licence': licence,
    })


# ── Pages informatives (middleware redirect) ──────────────────────────────────

@login_required
def activer(request):
    etab, licence = _get_licence(request.user)
    return render(request, 'licences/activer.html', {
        'etab': etab,
        'licence': licence,
        'is_superuser': request.user.is_superuser,
        'limites': LIMITES_LICENCES,
    })


@login_required
def renouveler(request):
    etab, licence = _get_licence(request.user)
    jours_restants = licence.jours_restants() if licence else None
    est_expiree = (
        licence.statut == StatutLicence.EXPIREE or (jours_restants is not None and jours_restants < 0)
    ) if licence else False
    return render(request, 'licences/renouveler.html', {
        'etab': etab,
        'licence': licence,
        'jours_restants': jours_restants,
        'est_expiree': est_expiree,
        'limites': LIMITES_LICENCES.get(licence.type_licence, {}) if licence else {},
        'is_superuser': request.user.is_superuser,
    })


@login_required
def statut_licence(request):
    """Page de statut de licence accessible à tout utilisateur authentifié."""
    etab, licence = _get_licence(request.user)
    jours_restants = licence.jours_restants() if licence else None
    est_expiree = (
        licence is not None and (
            licence.statut == StatutLicence.EXPIREE
            or (jours_restants is not None and jours_restants < 0)
        )
    )
    expire_bientot = (
        not est_expiree
        and jours_restants is not None
        and jours_restants <= 30
    )
    LABELS = {
        'inscriptions': 'Inscriptions & élèves',
        'enregistrement_eleves': 'Enregistrement des élèves',
        'carte_identite_scolaire': 'Carte d\'identité scolaire',
        'notes_bulletins': 'Notes & bulletins',
        'presences': 'Gestion des présences',
        'finances_base': 'Finances de base',
        'certificats': 'Certificats & attestations',
        'attestations': 'Attestations de scolarité',
        'autorisations_absence': 'Autorisations d\'absence',
        'cursus_scolaire': 'Cursus scolaire',
        'examens_officiels': 'Examens officiels (CEP/BEPC/BAC)',
        'portail_parents': 'Portail parents',
        'gestion_personnel': 'Gestion du personnel',
        'vacations': 'Vacations enseignants',
        'statistiques_listes': 'Statistiques & listes',
        'ia_predictive': 'IA prédictive',
        'rapports_avances': 'Rapports avancés',
        'multi_etablissements': 'Multi-établissements',
    }
    type_licence = licence.type_licence if licence else ''
    features_rows = [
        {'label': LABELS.get(feat, feat), 'inclus': type_licence in niveaux}
        for feat, niveaux in FEATURE_FLAGS.items()
    ]
    jours_pct = 0
    if jours_restants is not None:
        jours_pct = max(0, min(100, round(jours_restants / 365 * 100)))
    return render(request, 'licences/statut.html', {
        'etab': etab,
        'licence': licence,
        'jours_restants': jours_restants,
        'jours_restants_pct': jours_pct,
        'date_debut': licence.date_activation if licence else None,
        'est_expiree': est_expiree,
        'expire_bientot': expire_bientot,
        'limites': LIMITES_LICENCES.get(licence.type_licence, {}) if licence else {},
        'is_superuser': request.user.is_superuser,
        'signature_valide': licence.verifier_signature() if licence else None,
        'features_rows': features_rows,
    })


@login_required
def support(request):
    etab, licence = _get_licence(request.user)
    return render(request, 'licences/support.html', {
        'etab': etab,
        'licence': licence,
        'statut_display': licence.get_statut_display() if licence else None,
        'is_superuser': request.user.is_superuser,
    })


@login_required
def guide(request):
    etab, licence = _get_licence(request.user)
    return render(request, 'licences/guide.html', {
        'etab': etab,
        'licence': licence,
    })


# ── Outils offline (superuser seulement) ─────────────────────────────────────

@login_required
@_superuser_required
def outils_licence(request):
    """Ancien écran HMAC désactivé.

    L'émission et la vérification de licences sont volontairement sorties de
    l'interface web : la clé privée fournisseur ne doit jamais être manipulée
    par une requête HTTP ou stockée dans l'installation cliente.
    """
    from django.http import HttpResponseGone

    return HttpResponseGone(
        "L'outil local de licence HMAC a été désactivé. "
        "Utilisez les commandes fournisseur Ed25519."
    )
