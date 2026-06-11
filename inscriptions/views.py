from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from .models import Eleve, Inscription, EvenementParcours, TransfertEleve
from .forms import EleveForm, InscriptionForm, TransfertClasseForm
from parametres.models import AnneeScolaire, Classe
from core.utils import get_etablissement_context

try:
    from weasyprint import HTML as _WeasyHTML
except ImportError:
    _WeasyHTML = None

@login_required
def eleve_list(request):
    """Liste des élèves avec recherche, filtres HTMX et pagination."""
    query = request.GET.get('q', '')
    classe_id = request.GET.get('classe', '')
    statut_filter = request.GET.get('statut', '')
    page_number = request.GET.get('page', 1)
    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    # Inclure les élèves sans inscription (nouveaux) + ceux inscrits dans l'établissement
    eleves = Eleve.objects.order_by('nom', 'prenom')
    if etab:
        eleves = eleves.filter(
            Q(inscriptions__classe__etablissement=etab) |
            Q(inscriptions__isnull=True)
        ).distinct()

    if query:
        eleves = eleves.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(matricule__icontains=query)
        )

    if annee_courante:
        if classe_id:
            eleves = eleves.filter(
                inscriptions__classe_id=classe_id,
                inscriptions__annee_scolaire=annee_courante,
            ).distinct()
        if statut_filter == 'inscrit':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
            ).exclude(inscriptions__statut='ABANDON').distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut='ABANDON',
            ).distinct()
        elif statut_filter == 'non_inscrit':
            eleves = eleves.exclude(
                inscriptions__annee_scolaire=annee_courante,
            )
        elif statut_filter == 'inactif':
            eleves = eleves.filter(is_active=False)

    paginator = Paginator(eleves, 50)
    page_obj = paginator.get_page(page_number)

    # Inscription de l'année courante pour chaque élève de la page (incluant les ABANDON)
    inscriptions_courantes = {}
    if annee_courante:
        qs = Inscription.objects.filter(
            annee_scolaire=annee_courante,
            eleve__in=page_obj.object_list,
        ).select_related('eleve', 'classe', 'annee_scolaire', 'statut_eleve')
        for insc in qs:
            inscriptions_courantes[str(insc.eleve_id)] = insc

    classes = (
        Classe.objects.filter(etablissement=etab, actif=True)
        .select_related('cycle').order_by('cycle__ordre', 'nom')
        if etab else Classe.objects.none()
    )

    context = {
        'eleve_list': page_obj,
        'page_obj': page_obj,
        'query': query,
        'classe_id': classe_id,
        'statut_filter': statut_filter,
        'classes': classes,
        'inscriptions_courantes': inscriptions_courantes,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'inscriptions/partials/eleve_table.html', context)

    return render(request, 'inscriptions/eleve_list.html', context)


@login_required
def eleve_list_csv(request):
    """Export CSV de la liste des eleves (memes filtres qu'eleve_list)."""
    import csv
    from core.models import AuditLog
    from django.utils import timezone
    
    # Vérification de rôle - seuls certains rôles peuvent exporter
    from core.models import RoleChoices
    if request.user.role not in (
        RoleChoices.SUPER_ADMIN, RoleChoices.DIRECTEUR, RoleChoices.CENSEUR,
        RoleChoices.SECRETAIRE, RoleChoices.COMPTABLE
    ):
        messages.error(request, "Vous n'êtes pas autorisé à exporter la liste des élèves.")
        return redirect('inscriptions:eleve_list')
    
    query = request.GET.get('q', '')
    classe_id = request.GET.get('classe', '')
    statut_filter = request.GET.get('statut', '')
    ids = request.GET.get('ids', '')  # Pour export de selection
    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    eleves = Eleve.objects.order_by('nom', 'prenom')
    if etab:
        eleves = eleves.filter(
            Q(inscriptions__classe__etablissement=etab) |
            Q(inscriptions__isnull=True)
        ).distinct()

    # Filtre par IDs si selection
    if ids:
        id_list = [id.strip() for id in ids.split(',') if id.strip()]
        if id_list:
            eleves = eleves.filter(pk__in=id_list)
    elif query:
        eleves = eleves.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(matricule__icontains=query)
        )
    
    # Journaliser l'export CSV
    try:
        AuditLog.objects.create(
            user=request.user,
            action='EXPORT',
            app_label='inscriptions',
            model_name='eleve',
            object_id=None,
            object_repr=f"Export CSV - {eleves.count()} élèves",
            changes={'type': 'csv', 'filtres': query or 'aucun'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    except Exception:
        pass  # Ne pas bloquer l'export si l'audit échoue

    if annee_courante:
        if classe_id:
            eleves = eleves.filter(
                inscriptions__classe_id=classe_id,
                inscriptions__annee_scolaire=annee_courante,
            ).distinct()
        if statut_filter == 'inscrit':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
            ).exclude(inscriptions__statut='ABANDON').distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut='ABANDON',
            ).distinct()
        elif statut_filter == 'non_inscrit':
            eleves = eleves.exclude(
                inscriptions__annee_scolaire=annee_courante,
            )
        elif statut_filter == 'inactif':
            eleves = eleves.filter(is_active=False)

    # Inscriptions de l'année courante indexées par eleve_id
    inscriptions_index = {}
    if annee_courante:
        for insc in Inscription.objects.filter(
            annee_scolaire=annee_courante, eleve__in=eleves
        ).select_related('classe', 'statut_eleve'):
            inscriptions_index[str(insc.eleve_id)] = insc

    nom_fichier = 'eleves'
    if annee_courante:
        nom_fichier += f'_{annee_courante.libelle}'.replace(' ', '_')
    nom_fichier += '.csv'

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Matricule', 'Nom', 'Prenom', 'Date de naissance', 'Genre',
        'Classe', 'Statut eleve', 'Statut inscription',
    ])

    for eleve in eleves:
        insc = inscriptions_index.get(str(eleve.pk))
        writer.writerow([
            eleve.matricule or '',
            eleve.nom,
            eleve.prenom,
            eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
            eleve.get_genre_display() if hasattr(eleve, 'get_genre_display') else (eleve.genre or ''),
            insc.classe.nom if insc and insc.classe else '',
            insc.statut_eleve.nom if insc and insc.statut_eleve else '',
            insc.statut if insc else '',
        ])

    return response


@login_required
def eleve_list_xlsx(request):
    """Export Excel de la liste des élèves (mêmes filtres qu'eleve_list)."""
    from core.excel import ExcelExport
    from core.models import RoleChoices

    if request.user.role not in (
        RoleChoices.SUPER_ADMIN, RoleChoices.DIRECTEUR, RoleChoices.CENSEUR,
        RoleChoices.SECRETAIRE, RoleChoices.COMPTABLE,
    ):
        messages.error(request, "Vous n'êtes pas autorisé à exporter la liste des élèves.")
        return redirect('inscriptions:eleve_list')

    query = request.GET.get('q', '')
    classe_id = request.GET.get('classe', '')
    statut_filter = request.GET.get('statut', '')
    ids = request.GET.get('ids', '')
    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    eleves = Eleve.objects.order_by('nom', 'prenom')
    if etab:
        eleves = eleves.filter(
            Q(inscriptions__classe__etablissement=etab) |
            Q(inscriptions__isnull=True)
        ).distinct()
    if ids:
        id_list = [i.strip() for i in ids.split(',') if i.strip()]
        if id_list:
            eleves = eleves.filter(pk__in=id_list)
    elif query:
        eleves = eleves.filter(
            Q(nom__icontains=query) | Q(prenom__icontains=query) | Q(matricule__icontains=query)
        )
    if annee_courante:
        if classe_id:
            eleves = eleves.filter(
                inscriptions__classe_id=classe_id,
                inscriptions__annee_scolaire=annee_courante,
            ).distinct()
        if statut_filter == 'inscrit':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
            ).exclude(inscriptions__statut='ABANDON').distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut='ABANDON',
            ).distinct()
        elif statut_filter == 'non_inscrit':
            eleves = eleves.exclude(inscriptions__annee_scolaire=annee_courante)
        elif statut_filter == 'inactif':
            eleves = eleves.filter(is_active=False)

    inscriptions_index = {}
    if annee_courante:
        for insc in Inscription.objects.filter(
            annee_scolaire=annee_courante, eleve__in=eleves
        ).select_related('classe', 'statut_eleve'):
            inscriptions_index[str(insc.eleve_id)] = insc

    titre = f"Liste des élèves{' — ' + annee_courante.libelle if annee_courante else ''}"
    nom_fichier = f"eleves{'_' + annee_courante.libelle if annee_courante else ''}.xlsx".replace(' ', '_')

    wb = ExcelExport("Élèves")
    wb.add_title(titre, subtitle=etab.nom if etab else '')
    wb.add_header(['Matricule', 'Nom', 'Prénom', 'Date de naissance', 'Genre', 'Classe', 'Statut élève', 'Statut inscription'])

    for eleve in eleves:
        insc = inscriptions_index.get(str(eleve.pk))
        wb.add_row([
            eleve.matricule or '',
            eleve.nom,
            eleve.prenom,
            eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
            eleve.get_genre_display() if hasattr(eleve, 'get_genre_display') else (eleve.genre or ''),
            insc.classe.nom if insc and insc.classe else '',
            insc.statut_eleve.nom if insc and insc.statut_eleve else '',
            insc.get_statut_display() if insc and hasattr(insc, 'get_statut_display') else (insc.statut if insc else ''),
        ])

    return wb.response(nom_fichier)


@login_required
def eleve_list_pdf(request):
    """Export PDF de la liste des élèves (mêmes filtres qu'eleve_list)."""
    if _WeasyHTML is None:
        messages.error(request, "La génération PDF n'est pas disponible sur ce serveur (WeasyPrint manquant).")
        return redirect('inscriptions:eleve_list')

    from datetime import date as _date
    query = request.GET.get('q', '')
    classe_id = request.GET.get('classe', '')
    statut_filter = request.GET.get('statut', '')
    ids = request.GET.get('ids', '')  # Pour export de selection
    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    eleves = Eleve.objects.order_by('nom', 'prenom')
    if etab:
        eleves = eleves.filter(
            Q(inscriptions__classe__etablissement=etab) |
            Q(inscriptions__isnull=True)
        ).distinct()

    # Filtre par IDs si selection
    if ids:
        id_list = [id.strip() for id in ids.split(',') if id.strip()]
        if id_list:
            eleves = eleves.filter(pk__in=id_list)
    elif query:
        eleves = eleves.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(matricule__icontains=query)
        )

    if annee_courante:
        if classe_id:
            eleves = eleves.filter(
                inscriptions__classe_id=classe_id,
                inscriptions__annee_scolaire=annee_courante,
            ).distinct()
        if statut_filter == 'inscrit':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
            ).exclude(inscriptions__statut='ABANDON').distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut='ABANDON',
            ).distinct()
        elif statut_filter == 'non_inscrit':
            eleves = eleves.exclude(
                inscriptions__annee_scolaire=annee_courante,
            )
        elif statut_filter == 'inactif':
            eleves = eleves.filter(is_active=False)

    # Inscriptions de l'année courante indexées par eleve_id
    inscriptions_index = {}
    if annee_courante:
        for insc in Inscription.objects.filter(
            annee_scolaire=annee_courante, eleve__in=eleves
        ).select_related('classe'):
            inscriptions_index[str(insc.eleve_id)] = insc

    # Libellés des filtres actifs
    filtre_classe = ''
    if classe_id:
        try:
            filtre_classe = Classe.objects.get(pk=classe_id).nom
        except Classe.DoesNotExist:
            pass
    filtre_statut_labels = {
        'inscrit': 'Inscrits', 'abandon': 'Abandon', 'non_inscrit': 'Non inscrits'
    }
    filtre_statut = filtre_statut_labels.get(statut_filter, '')

    rows = []
    for eleve in eleves:
        insc = inscriptions_index.get(str(eleve.pk))
        rows.append({
            'matricule': eleve.matricule or '',
            'nom': eleve.nom.upper(),
            'prenom': eleve.prenom,
            'date_naissance': eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
            'genre': eleve.get_genre_display() if hasattr(eleve, 'get_genre_display') else (eleve.genre or ''),
            'classe': insc.classe.nom if insc and insc.classe else '',
            'statut_inscription': insc.statut if insc else '',
        })

    ctx_etab = get_etablissement_context(etab, request) if etab else {}
    html_str = render_to_string('inscriptions/pdf/eleve_list.html', {
        'rows': rows,
        'nb_eleves': len(rows),
        'etab_nom': etab.nom if etab else 'YELEN SCHOOL',
        'annee_libelle': annee_courante.libelle if annee_courante else '',
        'filtre_classe': filtre_classe,
        'filtre_statut': filtre_statut,
        'date_edition': _date.today().strftime('%d/%m/%Y'),
        'identite': ctx_etab.get('identite'),
    })

    pdf = _WeasyHTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()
    nom_fichier = 'eleves'
    if annee_courante:
        nom_fichier += f'_{annee_courante.libelle}'.replace(' ', '_')
    nom_fichier += '.pdf'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    return response


@login_required
def eleve_detail(request, pk):
    """Détails d'un élève."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    
    inscriptions = eleve.inscriptions.all().order_by('-annee_scolaire__date_debut')
    
    last_inscription = eleve.inscriptions.exclude(
        statut='ABANDON'
    ).order_by('-annee_scolaire__date_debut').first()
    
    context = {
        'eleve': eleve,
        'inscriptions': inscriptions,
        'last_inscription': last_inscription,
    }
    return render(request, 'inscriptions/eleve_detail.html', context)

@login_required
def eleve_create(request):
    """Création d'un nouvel élève."""
    if request.method == 'POST':
        form = EleveForm(request.POST, request.FILES)
        if form.is_valid():
            eleve = form.save()
            messages.success(request, f"Élève {eleve.get_nom_complet()} créé avec succès.")
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        form = EleveForm()
    
    return render(request, 'inscriptions/eleve_form.html', {
        'form': form, 
        'title': "Inscrire un nouvel élève"
    })

@login_required
def eleve_update(request, pk):
    """Modification d'un élève."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    
    if request.method == 'POST':
        form = EleveForm(request.POST, request.FILES, instance=eleve)
        if form.is_valid():
            eleve = form.save()
            messages.success(request, f"Profil de {eleve.get_nom_complet()} mis à jour.")
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        form = EleveForm(instance=eleve)
    
    return render(request, 'inscriptions/eleve_form.html', {
        'form': form, 
        'title': "Modifier le profil", 
        'eleve': eleve
    })

@login_required
def inscription_create(request, pk):
    """Réinscription ou nouvelle inscription annuelle d'un élève."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST, etablissement=etab)
        if form.is_valid():
            inscription = form.save(commit=False)
            inscription.eleve = eleve
            inscription.save()
            eleve.last_classe = inscription.classe.nom
            eleve.last_annee = inscription.annee_scolaire.libelle
            eleve.save(update_fields=['last_classe', 'last_annee'])
            messages.success(request, f"Inscription confirmée pour {eleve.get_nom_complet()}.")
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
        form = InscriptionForm(
            initial={'eleve': eleve, 'annee_scolaire': annee_courante, 'statut_eleve': 'AFFECTE'},
            etablissement=etab,
        )

    return render(request, 'inscriptions/inscription_form.html', {
        'form': form,
        'eleve': eleve
    })

@login_required
def inscription_update(request, pk):
    """Modifier une inscription existante."""
    inscription = get_object_or_404(Inscription, pk=pk)
    eleve = inscription.eleve
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST, instance=inscription, etablissement=etab)
        if form.is_valid():
            form.save()
            eleve.last_classe = inscription.classe.nom
            eleve.last_annee = inscription.annee_scolaire.libelle
            eleve.save(update_fields=['last_classe', 'last_annee'])
            messages.success(request, f"Inscription de {eleve.get_nom_complet()} mise à jour.")
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        form = InscriptionForm(instance=inscription, etablissement=etab)

    return render(request, 'inscriptions/inscription_form.html', {
        'form': form,
        'eleve': eleve,
        'inscription': inscription,
        'is_update': True
    })


def get_classe_niveau(request, pk):
    """API endpoint to get the niveau of a class."""
    from django.http import JsonResponse
    from parametres.models import Classe
    
    try:
        classe = Classe.objects.get(pk=pk)
        return JsonResponse({'niveau': classe.niveau})
    except Classe.DoesNotExist:
        return JsonResponse({'niveau': ''})


def get_classe_cycle(request, pk):
    """API endpoint to get the cycle of a class."""
    from django.http import JsonResponse
    from parametres.models import Classe
    
    try:
        classe = Classe.objects.select_related('cycle').get(pk=pk)
        return JsonResponse({
            'cycle': classe.cycle.nom if classe.cycle else '',
            'cycle_id': str(classe.cycle.pk) if classe.cycle else ''
        })
    except Classe.DoesNotExist:
        return JsonResponse({'cycle': '', 'cycle_id': ''})


def get_statut_code(request, pk):
    """API endpoint to get the code and nom of a statut eleve."""
    from django.http import JsonResponse
    from parametres.models import StatutEleve
    
    try:
        statut = StatutEleve.objects.get(pk=pk)
        return JsonResponse({'code': statut.code, 'nom': statut.nom})
    except StatutEleve.DoesNotExist:
        return JsonResponse({'code': '', 'nom': ''})


# ═══════════════════════════════════════════════════════════════════
# CARTE SCOLAIRE
# ═══════════════════════════════════════════════════════════════════

def _get_inscription_courante(eleve):
    """Retourne l'inscription de l'année courante, sinon la plus récente."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    if annee_courante:
        ins = Inscription.objects.filter(
            eleve=eleve, annee_scolaire=annee_courante
        ).select_related('classe__cycle', 'classe__etablissement', 'annee_scolaire', 'statut_eleve').first()
        if ins:
            return ins
    return Inscription.objects.filter(eleve=eleve).select_related(
        'classe__cycle', 'classe__etablissement', 'annee_scolaire', 'statut_eleve'
    ).order_by('-annee_scolaire__date_debut').first()


@login_required
def marquer_abandon(request, pk):
    """Marque une inscription comme Abandon (ou annule l'abandon)."""
    inscription = get_object_or_404(Inscription, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    
    if request.method == 'POST':
        if inscription.statut == 'ABANDON':
            inscription.statut = 'AFFECTE'
            messages.success(request, f"{inscription.eleve.get_nom_complet()} — Abandon annulé, statut remis à Affecté.")
        else:
            inscription.statut = 'ABANDON'
            messages.warning(request, f"{inscription.eleve.get_nom_complet()} — Marqué(e) Abandon pour {inscription.annee_scolaire.libelle}.")
        inscription.save(update_fields=['statut'])
    return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)


@login_required
def transfert_classe(request, pk):
    """Transfert d'un élève vers une autre classe pour la même année scolaire."""
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe', 'annee_scolaire'),
        pk=pk,
    )
    etab = getattr(request.user, 'etablissement', None)
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    
    if inscription.statut == 'ABANDON':
        messages.error(request, "Impossible de transférer une inscription marquée Abandon.")
        return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)

    if request.method == 'POST':
        form = TransfertClasseForm(request.POST, inscription=inscription, etablissement=etab)
        if form.is_valid():
            ancienne_classe = inscription.classe
            inscription.classe = form.cleaned_data['classe']
            inscription.save(update_fields=['classe'])
            eleve = inscription.eleve
            eleve.last_classe = inscription.classe.nom
            eleve.last_annee = inscription.annee_scolaire.libelle
            eleve.save(update_fields=['last_classe', 'last_annee'])
            messages.success(
                request,
                f"{eleve.get_nom_complet()} transféré(e) de "
                f"{ancienne_classe.nom} vers {inscription.classe.nom}."
            )
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        form = TransfertClasseForm(inscription=inscription, etablissement=etab)

    return render(request, 'inscriptions/transfert_classe.html', {
        'form': form,
        'inscription': inscription,
        'eleve': inscription.eleve,
    })


@login_required
@require_POST
def eleve_delete(request, pk):
    """Soft-delete d'un élève (is_active=False)."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)

    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')

    if not eleve.is_active:
        messages.warning(request, f"L'élève {eleve.get_nom_complet()} est déjà désactivé.")
        return redirect('inscriptions:eleve_detail', pk=eleve.pk)

    eleve.is_active = False
    eleve.save(update_fields=['is_active'])
    messages.success(request, f"L'élève {eleve.get_nom_complet()} a été désactivé.")
    return redirect('inscriptions:eleve_list')


@login_required
def eleve_carte(request, pk):
    """Aperçu et génération PDF de la carte scolaire d'un élève."""
    eleve = get_object_or_404(Eleve, pk=pk)
    inscription = _get_inscription_courante(eleve)

    etab = inscription.classe.etablissement if inscription else None
    etab_context = get_etablissement_context(etab, request) if etab else {}

    context = {
        'eleve': eleve,
        'inscription': inscription,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
    }

    if request.GET.get('format') == 'pdf':
        if _WeasyHTML is None:
            messages.error(request, "WeasyPrint n'est pas installé.")
            return redirect('inscriptions:eleve_detail', pk=pk)
        html_str = render_to_string('inscriptions/pdf/carte_scolaire.html', context, request=request)
        pdf = _WeasyHTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
        filename = f"Carte_{eleve.nom}_{eleve.prenom}.pdf".replace(" ", "_")
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    return render(request, 'inscriptions/carte_preview.html', context)


@login_required
def classe_cartes_pdf(request, pk):
    """Génère un PDF avec les cartes scolaires de tous les élèves d'une classe."""
    from parametres.models import Classe as _Classe
    if _WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('inscriptions:eleve_list')

    classe = get_object_or_404(_Classe, pk=pk)
    annee_id = request.GET.get('annee')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee = AnneeScolaire.objects.filter(est_courante=True).first()
    if not annee:
        messages.error(request, "Aucune année scolaire disponible.")
        return redirect('inscriptions:eleve_list')

    inscriptions = Inscription.objects.filter(
        classe=classe, annee_scolaire=annee
    ).select_related('eleve', 'classe__cycle', 'classe__etablissement', 'annee_scolaire', 'statut_eleve'
    ).order_by('eleve__nom', 'eleve__prenom')

    etab = classe.etablissement
    etab_context = get_etablissement_context(etab, request)

    html_str = render_to_string('inscriptions/pdf/cartes_classe.html', {
        'inscriptions': inscriptions,
        'classe': classe,
        'annee': annee,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
    }, request=request)

    pdf = _WeasyHTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
    filename = f"Cartes_{classe.nom}_{annee.libelle}.pdf".replace(" ", "_")
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def reinscription_list(request):
    """Page de réinscription - liste des élèves à réinscrire."""
    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    annee_suivante = None
    
    if annee_courante and annee_courante.date_fin:
        annee_suivante = AnneeScolaire.objects.filter(
            etablissement=annee_courante.etablissement,
            date_debut__year=annee_courante.date_fin.year,
        ).first()
    
    if not annee_suivante:
        messages.warning(request, "Aucune année scolaire suivante trouvée pour la réinscription.")
    
    eleves_a_reinscrire = []
    
    if annee_courante and etab:
        inscriptions = Inscription.objects.filter(
            annee_scolaire=annee_courante,
            classe__etablissement=etab,
            statut__in=['AFFECTE', 'BOURSIER']
        ).select_related('eleve', 'classe').order_by('eleve__nom')
        
        eleves_deja_inscrits = set(
            Inscription.objects.filter(
                annee_scolaire=annee_suivante,
                eleve__in=[i.eleve for i in inscriptions]
            ).values_list('eleve_id', flat=True)
        )
        
        for inscr in inscriptions:
            if inscr.eleve_id not in eleves_deja_inscrits:
                eleves_a_reinscrire.append({
                    'eleve': inscr.eleve,
                    'classe_actuelle': inscr.classe,
                })
    
    return render(request, 'inscriptions/reinscription_list.html', {
        'eleves': eleves_a_reinscrire,
        'annee_courante': annee_courante,
        'annee_suivante': annee_suivante,
    })


@login_required
def reinscrire_eleve(request, pk):
    """Réinscrire un élève dans une nouvelle classe."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    
    if not annee_courante:
        messages.error(request, "Aucune année scolaire active.")
        return redirect('inscriptions:reinscription_list')
    
    if request.method == 'POST':
        classe_id = request.POST.get('classe')
        if not classe_id:
            messages.error(request, "Veuillez sélectionner une classe.")
            return redirect('inscriptions:reinscrire_eleve', pk=pk)
        
        classe = get_object_or_404(Classe, pk=classe_id)
        
        Inscription.objects.create(
            eleve=eleve,
            annee_scolaire=annee_courante,
            classe=classe,
            statut='AFFECTE'
        )
        eleve.last_classe = classe.nom
        eleve.last_annee = annee_courante.libelle
        eleve.save(update_fields=['last_classe', 'last_annee'])
        messages.success(request, f"{eleve.get_nom_complet()} réinscrit en {classe.nom}.")
        return redirect('inscriptions:reinscription_list')
    
    classes = []
    if etab:
        classes = Classe.objects.filter(etablissement=etab).order_by('cycle__nom', 'niveau', 'nom')
    
    return render(request, 'inscriptions/reinscrire_eleve.html', {
        'eleve': eleve,
        'classes': classes,
        'annee': annee_courante,
    })


# ─── Parcours scolaire ────────────────────────────────────────────────────────

# Couleurs et icônes par type de transition (utilisées dans le template)
_TRANSITION_META = {
    'PASSAGE':           {'label': 'Passage',            'color': '#16a34a', 'icon': '↑', 'badge_class': 'badge-success'},
    'REDOUBLEMENT':      {'label': 'Redoublement',        'color': '#d97706', 'icon': '↺', 'badge_class': 'badge-warning'},
    'TRANSFERT_ENTRANT': {'label': 'Transfert entrant',   'color': '#2563eb', 'icon': '→', 'badge_class': 'badge-info'},
    'TRANSFERT_SORTANT': {'label': 'Transfert sortant',   'color': '#7c3aed', 'icon': '→', 'badge_class': 'badge-purple'},
    'ABANDON':           {'label': 'Abandon',             'color': '#dc2626', 'icon': '✕', 'badge_class': 'badge-danger'},
    'DIPLOME':           {'label': 'Diplôme',             'color': '#0891b2', 'icon': '✓', 'badge_class': 'badge-info'},
    'AUTRE':             {'label': 'Événement',           'color': '#6b7280', 'icon': '•', 'badge_class': 'badge-neutral'},
}


def _calculer_transition(insc_courante, insc_suivante):
    """
    Déduit automatiquement le type de transition entre deux inscriptions.
    insc_courante = fin d'une année, insc_suivante = début de l'année d'après.
    """
    if insc_courante.statut == 'ABANDON':
        return 'ABANDON'
    if insc_suivante is None:
        return None  # Dernière inscription connue — pas encore de suite
    if insc_suivante.est_redoublant:
        return 'REDOUBLEMENT'
    # Même classe → redoublement (même si flag non coché)
    if insc_courante.classe_id == insc_suivante.classe_id:
        return 'REDOUBLEMENT'
    return 'PASSAGE'


@login_required
def eleve_parcours(request, pk):
    """
    Timeline chronologique du parcours scolaire d'un élève.

    Reconstruit les transitions depuis les Inscription existantes et
    les enrichit avec les EvenementParcours manuels.
    """
    eleve = get_object_or_404(Eleve, pk=pk)

    # Toutes les inscriptions par ordre chronologique
    inscriptions = list(
        eleve.inscriptions
        .select_related('annee_scolaire', 'classe__cycle', 'statut_eleve')
        .order_by('annee_scolaire__date_debut')
    )

    # Événements manuels indexés par annee_scolaire_id
    evenements_qs = (
        EvenementParcours.objects
        .filter(eleve=eleve)
        .select_related('annee_scolaire', 'enregistre_par')
        .order_by('annee_scolaire__date_debut', 'date_evenement')
    )
    evenements_par_annee = {}
    for ev in evenements_qs:
        evenements_par_annee.setdefault(ev.annee_scolaire_id, []).append(ev)

    # Construction de la timeline
    timeline = []
    for i, insc in enumerate(inscriptions):
        insc_suivante = inscriptions[i + 1] if i + 1 < len(inscriptions) else None

        # Transition calculée automatiquement
        type_auto = _calculer_transition(insc, insc_suivante)

        # Événements manuels pour cette année
        ev_annee = evenements_par_annee.get(insc.annee_scolaire_id, [])

        # Événement manuel qui surcharge la transition auto (transfert_sortant, diplome…)
        ev_transition = next(
            (e for e in ev_annee if e.type_evenement in (
                'TRANSFERT_SORTANT', 'DIPLOME', 'ABANDON', 'AUTRE'
            )),
            None
        )

        transition = ev_transition.type_evenement if ev_transition else type_auto
        meta = _TRANSITION_META.get(transition, _TRANSITION_META['AUTRE']) if transition else None

        # Badges de statut de l'inscription
        badges = []
        if insc.est_redoublant:
            badges.append({'label': 'Redoublant', 'badge_class': 'badge-redoublant'})
        if insc.statut == 'ABANDON':
            badges.append({'label': 'Abandon', 'badge_class': 'badge-danger'})
        if insc.statut == 'BOURSIER':
            badges.append({'label': 'Boursier', 'badge_class': 'badge-boursier'})
        if insc.est_exonere:
            badges.append({'label': 'Exonéré', 'badge_class': 'badge-exonere'})

        timeline.append({
            'inscription': insc,
            'badges': badges,
            'evenements': ev_annee,
            'transition': transition,
            'transition_meta': meta,
            'ev_transition': ev_transition,
            'est_derniere': insc_suivante is None,
        })

    # Formulaire d'ajout d'événement manuel (POST)
    annees = AnneeScolaire.objects.order_by('-libelle')
    if request.method == 'POST':
        type_ev = request.POST.get('type_evenement', '').strip()
        annee_id = request.POST.get('annee_scolaire', '').strip()
        motif = request.POST.get('motif', '').strip()
        etab_transfert = request.POST.get('etablissement_transfert', '').strip()
        date_ev = request.POST.get('date_evenement', '').strip()

        annee_ev = AnneeScolaire.objects.filter(pk=annee_id).first() if annee_id else None
        if type_ev and annee_ev:
            from datetime import date as _date
            EvenementParcours.objects.create(
                eleve=eleve,
                type_evenement=type_ev,
                annee_scolaire=annee_ev,
                motif=motif,
                etablissement_transfert=etab_transfert,
                date_evenement=date_ev or _date.today(),
                enregistre_par=request.user,
            )
            messages.success(request, "Événement enregistré.")
        else:
            messages.error(request, "Type d'événement et année scolaire requis.")
        return redirect('inscriptions:eleve_parcours', pk=eleve.pk)

    return render(request, 'inscriptions/eleve_parcours.html', {
        'eleve': eleve,
        'timeline': timeline,
        'annees': annees,
        'types_evenement': EvenementParcours.TypeEvenement.choices,
        'nb_annees': len(inscriptions),
        'nb_redoublements': sum(1 for e in timeline if e['transition'] == 'REDOUBLEMENT'),
    })


@login_required
def evenement_parcours_supprimer(request, pk):
    """Supprime un événement de parcours."""
    ev = get_object_or_404(EvenementParcours, pk=pk)
    eleve_pk = ev.eleve.pk
    if request.method == 'POST':
        ev.delete()
        messages.success(request, "Événement supprimé.")
    return redirect('inscriptions:eleve_parcours', pk=eleve_pk)


# ═══════════════════════════════════════════════════════════════════
# TRANSFERTS INTER-ÉTABLISSEMENTS
# ═══════════════════════════════════════════════════════════════════

@login_required
def transfert_inter_list(request):
    """Liste tous les transferts inter-établissements de l'établissement."""
    etab = getattr(request.user, 'etablissement', None)
    qs = (
        TransfertEleve.objects
        .select_related('inscription__eleve', 'inscription__classe', 'inscription__annee_scolaire', 'demandeur')
        .filter(inscription__classe__etablissement=etab)
        .order_by('-date_demande')
    ) if etab else TransfertEleve.objects.none()

    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '').strip()
    if statut:
        qs = qs.filter(statut=statut)
    if q:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=q) |
            Q(inscription__eleve__prenom__icontains=q) |
            Q(inscription__eleve__matricule__icontains=q) |
            Q(etablissement_destination__icontains=q)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inscriptions/transfert_inter_list.html', {
        'page_obj': page_obj,
        'statut': statut,
        'q': q,
        'statut_choices': TransfertEleve.StatutChoices.choices,
        'nb_en_attente': qs.filter(statut='EN_ATTENTE').count() if not statut else 0,
    })


@login_required
def transfert_inter_demander(request, inscription_id):
    """Formulaire de demande de transfert inter-établissements."""
    etab = getattr(request.user, 'etablissement', None)
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe', 'annee_scolaire'),
        pk=inscription_id,
    )
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:eleve_list')
    if inscription.statut == 'ABANDON':
        messages.error(request, "Cet élève est déjà en statut Abandon.")
        return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)
    # Vérifier qu'il n'y a pas déjà un transfert en attente
    if TransfertEleve.objects.filter(inscription=inscription, statut='EN_ATTENTE').exists():
        messages.warning(request, "Une demande de transfert est déjà en cours pour cet élève.")
        return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)

    if request.method == 'POST':
        dest = request.POST.get('etablissement_destination', '').strip()
        motif = request.POST.get('motif', '').strip()
        if not dest:
            messages.error(request, "L'établissement de destination est obligatoire.")
        else:
            transfert = TransfertEleve.objects.create(
                inscription=inscription,
                etablissement_destination=dest,
                motif=motif,
                demandeur=request.user,
            )
            messages.success(request, f"Demande de transfert créée pour {inscription.eleve.get_nom_complet()}.")
            return redirect('inscriptions:transfert_inter_detail', pk=transfert.pk)

    return render(request, 'inscriptions/transfert_inter_form.html', {
        'inscription': inscription,
    })


@login_required
def transfert_inter_detail(request, pk):
    """Détail d'un transfert inter-établissements."""
    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(
        TransfertEleve.objects.select_related(
            'inscription__eleve', 'inscription__classe', 'inscription__annee_scolaire',
            'demandeur', 'traite_par',
        ),
        pk=pk,
    )
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')

    # Situation financière
    from finances.models import Paiement, Echeancier
    paiements = Paiement.objects.filter(inscription=transfert.inscription).order_by('date_paiement')
    total_paye = sum(p.montant for p in paiements)
    echeances = Echeancier.objects.filter(inscription=transfert.inscription)
    total_du = sum(e.montant_du for e in echeances if not e.paye)

    # Historique des inscriptions
    inscriptions_historique = (
        Inscription.objects
        .filter(eleve=transfert.inscription.eleve)
        .select_related('classe', 'annee_scolaire')
        .order_by('annee_scolaire__date_debut')
    )

    return render(request, 'inscriptions/transfert_inter_detail.html', {
        'transfert': transfert,
        'paiements': paiements,
        'total_paye': total_paye,
        'total_du': total_du,
        'inscriptions_historique': inscriptions_historique,
        'can_approve': request.user.role in ('SUPER_ADMIN', 'DIRECTEUR'),
    })


@login_required
@require_POST
def transfert_inter_approuver(request, pk):
    """Approuve un transfert : marque l'inscription ABANDON + crée EvenementParcours."""
    if not hasattr(request.user, 'role') or request.user.role not in ('SUPER_ADMIN', 'DIRECTEUR'):
        messages.error(request, "Vous n'avez pas les droits pour approuver un transfert.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(
        TransfertEleve.objects.select_related('inscription__eleve', 'inscription__annee_scolaire'),
        pk=pk,
    )
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')
    if transfert.statut != 'EN_ATTENTE':
        messages.warning(request, "Ce transfert a déjà été traité.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    from django.utils import timezone

    # Mettre à jour le transfert
    transfert.statut = 'APPROUVE'
    transfert.date_traitement = timezone.now().date()
    transfert.traite_par = request.user
    transfert.notes_admin = request.POST.get('notes_admin', '').strip()
    transfert.save(update_fields=['statut', 'date_traitement', 'traite_par', 'notes_admin'])

    # Marquer l'inscription comme abandon
    ins = transfert.inscription
    ins.statut = 'ABANDON'
    ins.save(update_fields=['statut'])

    # Mettre à jour l'élève (dernière classe connue)
    eleve = ins.eleve
    eleve.last_classe = ins.classe.nom
    eleve.last_annee = ins.annee_scolaire.libelle
    eleve.etablissement_origine = ins.classe.etablissement.nom if hasattr(ins.classe, 'etablissement') else ''
    eleve.save(update_fields=['last_classe', 'last_annee', 'etablissement_origine'])

    # Créer l'événement de parcours
    EvenementParcours.objects.create(
        eleve=eleve,
        type_evenement=EvenementParcours.TypeEvenement.TRANSFERT_SORTANT,
        annee_scolaire=ins.annee_scolaire,
        inscription=ins,
        date_evenement=transfert.date_traitement,
        motif=transfert.motif,
        etablissement_transfert=transfert.etablissement_destination,
        enregistre_par=request.user,
    )

    messages.success(request, f"Transfert approuvé. {eleve.get_nom_complet()} est désormais marqué(e) en départ.")
    return redirect('inscriptions:transfert_inter_detail', pk=pk)


@login_required
@require_POST
def transfert_inter_refuser(request, pk):
    """Refuse un transfert."""
    if not hasattr(request.user, 'role') or request.user.role not in ('SUPER_ADMIN', 'DIRECTEUR'):
        messages.error(request, "Vous n'avez pas les droits pour refuser un transfert.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(TransfertEleve, pk=pk)
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')
    if transfert.statut != 'EN_ATTENTE':
        messages.warning(request, "Ce transfert a déjà été traité.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    from django.utils import timezone
    transfert.statut = 'REFUSE'
    transfert.date_traitement = timezone.now().date()
    transfert.traite_par = request.user
    transfert.notes_admin = request.POST.get('notes_admin', '').strip()
    transfert.save(update_fields=['statut', 'date_traitement', 'traite_par', 'notes_admin'])

    messages.success(request, "Transfert refusé.")
    return redirect('inscriptions:transfert_inter_detail', pk=pk)


@login_required
def transfert_inter_dossier_pdf(request, pk):
    """Génère le dossier de transfert PDF : infos élève, cursus, situation financière."""
    if _WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur le serveur.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(
        TransfertEleve.objects.select_related(
            'inscription__eleve', 'inscription__classe__cycle',
            'inscription__annee_scolaire', 'demandeur', 'traite_par',
        ),
        pk=pk,
    )
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')

    eleve = transfert.inscription.eleve

    # Cursus complet
    inscriptions_historique = (
        Inscription.objects
        .filter(eleve=eleve)
        .select_related('classe', 'annee_scolaire')
        .order_by('annee_scolaire__date_debut')
    )

    # Situation financière
    from finances.models import Paiement, Echeancier
    paiements = list(Paiement.objects.filter(inscription=transfert.inscription).order_by('date_paiement'))
    total_paye = sum(p.montant for p in paiements)
    echeances = list(Echeancier.objects.filter(inscription=transfert.inscription))
    total_du = sum(e.montant_du for e in echeances if not e.paye)

    etab_context = get_etablissement_context(etab, request)

    html_string = render_to_string('inscriptions/pdf/dossier_transfert.html', {
        'transfert': transfert,
        'eleve': eleve,
        'inscriptions_historique': inscriptions_historique,
        'paiements': paiements,
        'total_paye': total_paye,
        'total_du': total_du,
        'echeances': echeances,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
    })

    pdf_file = _WeasyHTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    nom = f"{eleve.nom}_{eleve.prenom}".replace(' ', '_')
    filename = f"Dossier_Transfert_{nom}.pdf"
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
