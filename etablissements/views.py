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
