from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from core.models import CycleChoices, RoleChoices
from accounts.models import User

from .forms import EtablissementForm
from .models import Etablissement

# Imports optionnels pour les stats
try:
    from inscriptions.models import Eleve
except ImportError:
    Eleve = None

try:
    from parametres.models import Classe
except ImportError:
    Classe = None


@login_required
def etablissement_detail(request):
    etab = getattr(request.user, 'etablissement', None)

    # Si l'utilisateur est super-admin et n'a pas d'établissement lié,
    # on essaie de prendre le premier établissement en base.
    if not etab and request.user.is_superuser:
        etab = Etablissement.objects.first()

    if request.method == 'POST':
        instance = etab or Etablissement()
        form = EtablissementForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            saved = form.save()
            # Lier le super-admin au nouvel établissement si nécessaire
            if request.user.is_superuser and not request.user.etablissement:
                request.user.etablissement = saved
                request.user.save()
            return _render_etab_detail(request, saved, form=form,
                                       success="Configuration enregistrée avec succès.")
        return _render_etab_detail(request, instance, form=form)

    if not etab and not request.user.is_superuser:
        return render(request, 'etablissements/detail.html', {
            'etablissement': None,
            'error': "Votre compte n'est pas associé à un établissement.",
        })

    form = EtablissementForm(instance=etab) if etab else EtablissementForm()
    return _render_etab_detail(request, etab, form=form)


def _render_etab_detail(request, etab, form=None, success=None, error=None):
    """Helper pour rendre le template avec toutes les données nécessaires (stats, cycles)."""
    stats = {
        'eleves': Eleve.objects.count() if Eleve else 0,
        'personnel': User.objects.exclude(
            role__in=[RoleChoices.PARENT, RoleChoices.ELEVE, RoleChoices.SUPER_ADMIN]
        ).count(),
        'classes': Classe.objects.count() if Classe else 0,
    }
    return render(request, 'etablissements/detail.html', {
        'etablissement': etab,
        'form': form,
        # Maintenu pour compatibilité avec le template existant
        'cycles_all': CycleChoices.choices,
        'cycles_selected': etab.cycles if etab else [],
        'stats': stats,
        'success': success,
        'error': error,
    })


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD RÉSEAU MULTI-ÉTABLISSEMENTS
# ═══════════════════════════════════════════════════════════════════

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import GroupeEtablissements


def _is_reseau_user(user):
    return hasattr(user, 'role') and user.role in ('SUPER_ADMIN', 'DIRECTEUR_RESEAU')


def _get_groupe(user):
    """Retourne le groupe accessible par l'utilisateur."""
    if user.role == 'SUPER_ADMIN':
        return None  # voit tous les groupes
    return getattr(user, 'groupe', None)


@login_required
def reseau_dashboard(request):
    """Dashboard consolidé réseau — statistiques agrégées par établissement."""
    if not _is_reseau_user(request.user):
        messages.error(request, "Accès réservé au Directeur Réseau.")
        return redirect('core:home')

    groupe_filtre = _get_groupe(request.user)

    if groupe_filtre:
        groupes = [groupe_filtre]
        etablissements_qs = Etablissement.objects.filter(groupe=groupe_filtre)
    else:
        groupes = list(GroupeEtablissements.objects.prefetch_related('etablissements').order_by('nom'))
        etablissements_qs = Etablissement.objects.filter(groupe__isnull=False)

    # Aucun groupe ? Afficher quand même tous les établissements (SUPER_ADMIN)
    if not groupes and request.user.role == 'SUPER_ADMIN':
        etablissements_qs = Etablissement.objects.all()

    # Statistiques par établissement
    from inscriptions.models import Inscription
    from finances.models import Paiement
    from parametres.models import AnneeScolaire

    stats_par_etab = []
    for etab in etablissements_qs.order_by('nom'):
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
        nb_eleves = Inscription.objects.filter(
            classe__etablissement=etab,
            annee_scolaire=annee,
        ).exclude(statut='ABANDON').count() if annee else 0

        total_paye = sum(
            p.montant for p in Paiement.objects.filter(
                inscription__classe__etablissement=etab,
                inscription__annee_scolaire=annee,
            )
        ) if annee else 0

        stats_par_etab.append({
            'etablissement': etab,
            'annee': annee,
            'nb_eleves': nb_eleves,
            'total_paye': total_paye,
        })

    total_eleves = sum(s['nb_eleves'] for s in stats_par_etab)
    total_encaisse = sum(s['total_paye'] for s in stats_par_etab)

    return render(request, 'etablissements/reseau_dashboard.html', {
        'groupes': groupes,
        'stats_par_etab': stats_par_etab,
        'total_eleves': total_eleves,
        'total_encaisse': total_encaisse,
        'groupe_filtre': groupe_filtre,
    })


@login_required
def groupe_list(request):
    """Liste des groupes d'établissements (SUPER_ADMIN seulement)."""
    if request.user.role != 'SUPER_ADMIN':
        return redirect('etablissements:reseau_dashboard')
    groupes = GroupeEtablissements.objects.prefetch_related('etablissements').order_by('nom')
    etablissements_sans_groupe = Etablissement.objects.filter(groupe__isnull=True).order_by('nom')
    return render(request, 'etablissements/groupe_list.html', {
        'groupes': groupes,
        'etablissements_sans_groupe': etablissements_sans_groupe,
    })


@login_required
def groupe_form(request, pk=None):
    """Création / modification d'un groupe."""
    if request.user.role != 'SUPER_ADMIN':
        return redirect('etablissements:reseau_dashboard')

    groupe = get_object_or_404(GroupeEtablissements, pk=pk) if pk else None

    if request.method == 'POST':
        nom  = request.POST.get('nom', '').strip()
        code = request.POST.get('code', '').strip()
        desc = request.POST.get('description', '').strip()
        if not nom or not code:
            messages.error(request, "Nom et code sont obligatoires.")
        else:
            if groupe:
                groupe.nom = nom
                groupe.code = code
                groupe.description = desc
                groupe.save()
                messages.success(request, f"Groupe «{nom}» mis à jour.")
            else:
                groupe = GroupeEtablissements.objects.create(nom=nom, code=code, description=desc)
                messages.success(request, f"Groupe «{nom}» créé.")
            return redirect('etablissements:groupe_list')

    return render(request, 'etablissements/groupe_form.html', {'groupe': groupe})


@login_required
@require_POST
def groupe_affecter_etab(request, groupe_pk):
    """Affecte un établissement à un groupe."""
    if request.user.role != 'SUPER_ADMIN':
        return redirect('etablissements:reseau_dashboard')
    groupe = get_object_or_404(GroupeEtablissements, pk=groupe_pk)
    etab_pk = request.POST.get('etablissement_pk')
    if etab_pk:
        etab = get_object_or_404(Etablissement, pk=etab_pk)
        etab.groupe = groupe
        etab.save(update_fields=['groupe'])
        messages.success(request, f"{etab.nom} rattaché au groupe {groupe.nom}.")
    return redirect('etablissements:groupe_list')
