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


from licences.decorators import requires_licence_feature
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
from django.core.exceptions import ValidationError
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


def etablissement_pilotable(user, etab_id):
    """Établissement qu'un Super Admin ou un Directeur Réseau peut piloter à distance (même groupe), sinon None."""
    if not etab_id or not _is_reseau_user(user):
        return None
    try:
        etab = Etablissement.objects.select_related('groupe').filter(pk=etab_id).first()
    except (ValueError, ValidationError):
        return None
    if etab is None or user.role == 'SUPER_ADMIN':
        return etab
    return etab if user.groupe_id and etab.groupe_id == user.groupe_id else None


def _export_reseau_xlsx(groupe, lignes, totaux):
    from core.excel import ExcelExport

    wb = ExcelExport("Réseau")
    wb.add_title("Vue consolidée du réseau", groupe.nom if groupe else "Tous les établissements")
    wb.add_header(['Établissement', 'Année', 'Élèves', 'Garçons', 'Filles', 'Classes', 'Remplissage %',
                   'Attendu (FCFA)', 'Encaissé (FCFA)', 'Reste (FCFA)', 'Recouvrement %', 'Redevables',
                   'Absences 30 j', 'Absentéisme 30 j %', 'Justificatifs en attente', 'Élèves à risque'])

    def valeurs(ligne):
        e, r, a, q = ligne['effectifs'], ligne['recouvrement'], ligne['absences'], ligne['risque']
        return [e['total'], e['garcons'], e['filles'], e['classes'], e['taux_remplissage'],
                int(r['attendu']), int(r['encaisse']), int(r['reste']), r['taux'], r['redevables'],
                a['trente_jours'], a['taux_30j'], a['justifications_attente'], q['prioritaires_nb']]

    for ligne in lignes:
        if ligne['annee'] is None:
            wb.add_row([ligne['etablissement'].nom, 'Aucune année courante'] + [''] * 14)
        else:
            wb.add_row([ligne['etablissement'].nom, ligne['annee'].libelle] + valeurs(ligne))
    wb.add_row(['Total réseau', f"{totaux['sites']} site(s)"] + valeurs(totaux), highlight_color='E5E7EB')
    return wb.response('reseau_consolide.xlsx')


@login_required
@requires_licence_feature('multi_etablissements')
def reseau_dashboard(request):
    """Vue consolidée multi-sites : indicateurs de pilotage de chaque établissement du groupe et totaux pondérés."""
    from core.pilotage import tableau_reseau

    if not _is_reseau_user(request.user):
        messages.error(request, "Accès réservé au Directeur Réseau.")
        return redirect('core:home')

    groupe = _get_groupe(request.user)
    groupes = []
    if request.user.role == 'SUPER_ADMIN':
        groupes = list(GroupeEtablissements.objects.order_by('nom'))
        if request.GET.get('groupe'):
            try:
                groupe = GroupeEtablissements.objects.filter(pk=request.GET['groupe']).first()
            except (ValueError, ValidationError):
                groupe = None
        etablissements = Etablissement.objects.filter(groupe=groupe) if groupe else Etablissement.objects.all()
    elif groupe is not None:
        etablissements = Etablissement.objects.filter(groupe=groupe)
    else:
        messages.warning(request, "Votre compte n'est rattaché à aucun groupe d'établissements.")
        etablissements = Etablissement.objects.none()

    consolide = tableau_reseau(etablissements.select_related('groupe').order_by('nom'))
    if request.GET.get('format') == 'xlsx':
        return _export_reseau_xlsx(groupe, **consolide)

    return render(request, 'etablissements/reseau_dashboard.html', {
        'groupes': groupes, 'groupe_filtre': groupe, 'lignes': consolide['lignes'], 'totaux': consolide['totaux'],
    })


@login_required
@requires_licence_feature('multi_etablissements')
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
@requires_licence_feature('multi_etablissements')
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
@requires_licence_feature('multi_etablissements')
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
