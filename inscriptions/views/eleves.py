"""Liste, fiche, création, modification et exports des élèves (dossier et données personnelles)."""

import logging
import uuid
from django.shortcuts import render, get_object_or_404, redirect
import os
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from ..models import Eleve, Inscription, StatutInscriptionChoices
from ..forms import EleveForm
from parametres.models import AnneeScolaire, Classe
from core.utils import get_etablissement_context
from core.statistiques import statistiques_eleves
from parametres.droits import autorise_url
logger = logging.getLogger(__name__)
try:
    from core.pdf import HTML as _WeasyHTML
except (ImportError, OSError) as exc:  # libpango/cairo absents
    logger.error("WeasyPrint indisponible, génération PDF désactivée : %s", exc)
    # Le serveur peut démarrer sans les bibliothèques système PDF ; les vues
    # concernées afficheront un message d'indisponibilité.
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
            ).exclude(inscriptions__statut=StatutInscriptionChoices.ABANDON).distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut=StatutInscriptionChoices.ABANDON,
            ).distinct()
        elif statut_filter == 'non_inscrit':
            eleves = eleves.exclude(
                inscriptions__annee_scolaire=annee_courante,
            )
        elif statut_filter == 'inactif':
            eleves = eleves.filter(is_active=False)

    # Statistiques sur l'ensemble filtré (toutes pages) : un seul parcours (pk, genre, date)
    stats = statistiques_eleves(
        (genre, date_naissance)
        for _pk, genre, date_naissance
        in eleves.order_by().values_list('pk', 'genre', 'date_naissance').distinct()
    )

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
        'stats': stats,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'inscriptions/partials/eleve_table.html', context)

    return render(request, 'inscriptions/eleve_list.html', context)


@login_required
def eleve_list_csv(request):
    """Export CSV de la liste des eleves (memes filtres qu'eleve_list)."""
    import csv
    from core.models import AuditLog

    if not autorise_url(request, 'inscriptions:eleve_list_csv'):
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
        id_list = []
        for raw in ids.split(','):
            raw = raw.strip()
            if raw:
                try:
                    id_list.append(uuid.UUID(raw))
                except (ValueError, AttributeError):
                    pass
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
        logger.exception("Journal d'audit indisponible pour l'export CSV")  # l'export n'est pas bloqué

    if annee_courante:
        if classe_id:
            eleves = eleves.filter(
                inscriptions__classe_id=classe_id,
                inscriptions__annee_scolaire=annee_courante,
            ).distinct()
        if statut_filter == 'inscrit':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
            ).exclude(inscriptions__statut=StatutInscriptionChoices.ABANDON).distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut=StatutInscriptionChoices.ABANDON,
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
        statut_inscription = 'Désactivé' if not eleve.is_active else (
            insc.get_statut_display() if insc and hasattr(insc, 'get_statut_display')
            else (insc.statut if insc else '')
        )
        writer.writerow([
            eleve.matricule or '',
            eleve.nom,
            eleve.prenom,
            eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
            eleve.get_genre_display() if hasattr(eleve, 'get_genre_display') else (eleve.genre or ''),
            insc.classe.nom if insc and insc.classe else '',
            insc.statut_eleve.nom if insc and insc.statut_eleve else '',
            statut_inscription,
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

    if not autorise_url(request, 'inscriptions:eleve_list_xlsx'):
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
        id_list = []
        for raw in ids.split(','):
            raw = raw.strip()
            if raw:
                try:
                    id_list.append(uuid.UUID(raw))
                except (ValueError, AttributeError):
                    pass
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
            ).exclude(inscriptions__statut=StatutInscriptionChoices.ABANDON).distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut=StatutInscriptionChoices.ABANDON,
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
        statut_inscription = 'Désactivé' if not eleve.is_active else (
            insc.get_statut_display() if insc and hasattr(insc, 'get_statut_display')
            else (insc.statut if insc else '')
        )
        wb.add_row([
            eleve.matricule or '',
            eleve.nom,
            eleve.prenom,
            eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
            eleve.get_genre_display() if hasattr(eleve, 'get_genre_display') else (eleve.genre or ''),
            insc.classe.nom if insc and insc.classe else '',
            insc.statut_eleve.nom if insc and insc.statut_eleve else '',
            statut_inscription,
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
        id_list = []
        for raw in ids.split(','):
            raw = raw.strip()
            if raw:
                try:
                    id_list.append(uuid.UUID(raw))
                except (ValueError, AttributeError):
                    pass
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
            ).exclude(inscriptions__statut=StatutInscriptionChoices.ABANDON).distinct()
        elif statut_filter == 'abandon':
            eleves = eleves.filter(
                inscriptions__annee_scolaire=annee_courante,
                inscriptions__statut=StatutInscriptionChoices.ABANDON,
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
        'inscrit': 'Inscrits', 'abandon': 'Abandon', 'non_inscrit': 'Non inscrits',
        'inactif': 'Désactivés',
    }
    filtre_statut = filtre_statut_labels.get(statut_filter, '')

    rows = []
    couples = []  # (genre, date de naissance) pour les tableaux statistiques
    for eleve in eleves:
        insc = inscriptions_index.get(str(eleve.pk))
        couples.append((eleve.genre, eleve.date_naissance))
        rows.append({
            'matricule': eleve.matricule or '',
            'nom': eleve.nom.upper(),
            'prenom': eleve.prenom,
            'date_naissance': eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
            'genre': eleve.get_genre_display() if hasattr(eleve, 'get_genre_display') else (eleve.genre or ''),
            'classe': insc.classe.nom if insc and insc.classe else '',
            'statut_inscription': 'Désactivé' if not eleve.is_active else (insc.statut if insc else ''),
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
        'stats': statistiques_eleves(couples),
        **ctx_etab,   # identite, etablissement, logo_url, etab_logo_url → en-tête du socle PDF
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
@login_required
def eleve_dossier(request, pk):
    """Dossier documentaire de l'élève : pièces d'inscription déposées et documents délivrés (date, signataire)."""
    from documents.models import Document
    from ..forms import PieceDossierForm
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    inscription = eleve.inscriptions.select_related('annee_scolaire', 'classe').order_by('-annee_scolaire__date_debut').first()
    if request.method == 'POST':
        form = PieceDossierForm(request.POST, request.FILES)
        if form.is_valid():
            piece = form.save(commit=False)
            piece.eleve = eleve
            piece.inscription = inscription
            piece.created_by = request.user
            piece.save()
            messages.success(request, f"Pièce déposée : {piece.get_type_piece_display()}.")
            return redirect('inscriptions:eleve_dossier', pk=eleve.pk)
    else:
        form = PieceDossierForm()
    pieces = eleve.pieces_dossier.select_related('inscription__annee_scolaire')
    documents = (
        Document.objects.filter(inscription__eleve=eleve).exclude(fichier='')
        .select_related('type_document', 'annee_scolaire').order_by('-created_at')
    )
    return render(request, 'inscriptions/eleve_dossier.html', {
        'eleve': eleve, 'inscription': inscription, 'pieces': pieces, 'documents': documents, 'form': form,
    })


@login_required
def piece_dossier_telecharger(request, pk):
    from ..models import PieceDossier
    piece = get_object_or_404(PieceDossier.objects.select_related('eleve'), pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    if etab and piece.eleve.inscriptions.exists() and not piece.eleve.inscriptions.filter(classe__etablissement=etab).exists():
        raise Http404
    return FileResponse(piece.fichier.open('rb'), as_attachment=True, filename=os.path.basename(piece.fichier.name))


@login_required
@require_POST
def piece_dossier_supprimer(request, pk):
    from ..models import PieceDossier
    piece = get_object_or_404(PieceDossier, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    if etab and piece.eleve.inscriptions.exists() and not piece.eleve.inscriptions.filter(classe__etablissement=etab).exists():
        raise Http404
    eleve_pk = piece.eleve_id
    piece.fichier.delete(save=False)
    piece.delete()
    messages.success(request, "Pièce supprimée du dossier.")
    return redirect('inscriptions:eleve_dossier', pk=eleve_pk)


@login_required
def eleve_export_donnees(request, pk):
    """Dossier complet d'un élève en JSON (droit d'accès — loi n° 001-2021/AN)."""
    from core.audit import record_audit
    from core.donnees_personnelles import exporter_dossier
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    record_audit(instance=eleve, action='EXPORT', user=request.user, request=request, reason="Export du dossier de l'élève (droit d'accès)")
    reponse = JsonResponse(exporter_dossier(eleve), json_dumps_params={'ensure_ascii': False, 'indent': 2})
    reponse['Content-Disposition'] = f'attachment; filename="dossier-{eleve.matricule or eleve.pk}.json"'
    return reponse


def eleve_detail(request, pk):
    """Détails d'un élève."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)

    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')

    inscriptions = eleve.inscriptions.all().order_by('-annee_scolaire__date_debut')

    last_inscription = eleve.inscriptions.exclude(
        statut=StatutInscriptionChoices.ABANDON
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
    etab = getattr(request.user, 'etablissement', None)

    if request.method == 'POST':
        form = EleveForm(request.POST, request.FILES, etablissement=etab)
        if form.is_valid():
            eleve = form.save(commit=False)
            if etab:
                eleve._etablissement_code = etab.code
            eleve.save()
            messages.success(request, f"Élève {eleve.get_nom_complet()} créé avec succès.")
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        form = EleveForm(etablissement=etab)

    return render(request, 'inscriptions/eleve_form.html', {
        'form': form,
        'title': "Inscrire un nouvel élève"
    })


def _initial_depuis_preinscription(eleve):
    """Élève issu d'une pré-inscription : le « parent / tuteur » saisi à la demande a été enregistré comme tuteur
    alors qu'il s'agit du père. Le formulaire de modification présente donc ce nom dans « Nom du père » et laisse
    « Nom du tuteur » vide ; l'enregistrement reporte la valeur au bon endroit (5.52.3)."""
    if eleve.nom_pere or not eleve.tuteur_nom:
        return {}
    if not eleve.inscriptions.filter(pre_inscription__isnull=False).exists():
        return {}
    return {'nom_pere': eleve.tuteur_nom, 'tuteur_nom': ''}


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
        form = EleveForm(instance=eleve, initial=_initial_depuis_preinscription(eleve))

    return render(request, 'inscriptions/eleve_form.html', {
        'form': form,
        'title': "Modifier le profil",
        'eleve': eleve
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
