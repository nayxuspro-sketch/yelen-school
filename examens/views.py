"""
Module Examens - Views
=======================
YELEN SCHOOL v3.4
"""

import csv
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect

from parametres.models import AnneeScolaire, Classe
from inscriptions.models import Inscription
from .models import SessionExamen, CentreExamen, InscriptionExamen, SalleExamen, PlacementExamen
from .forms import SessionExamenForm, CentreExamenForm, SalleExamenForm

try:
    from weasyprint import HTML as WeasyHTML
except ImportError:
    WeasyHTML = None


# ── Sessions ──────────────────────────────────────────────────────────────────

@login_required
def session_list(request):
    etab = getattr(request.user, 'etablissement', None)
    annee_id = request.GET.get('annee_id', '').strip()

    annees_qs = AnneeScolaire.objects.order_by('-libelle')
    if etab:
        annees_qs = annees_qs.filter(etablissement=etab)

    annee_selectionnee = None
    if annee_id:
        annee_selectionnee = annees_qs.filter(pk=annee_id).first()
    if not annee_selectionnee:
        annee_selectionnee = annees_qs.filter(est_courante=True).first()

    sessions = SessionExamen.objects.select_related('annee_scolaire').order_by('-date_debut')
    if etab:
        sessions = sessions.filter(annee_scolaire__etablissement=etab)
    if annee_selectionnee:
        sessions = sessions.filter(annee_scolaire=annee_selectionnee)

    return render(request, 'examens/session_list.html', {
        'sessions': sessions,
        'annees': annees_qs,
        'annee_selectionnee': annee_selectionnee,
    })


@login_required
def session_create(request):
    form = SessionExamenForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        session = form.save()
        messages.success(request, f"Session « {session.libelle} » créée.")
        return redirect('examens:session_detail', session_id=session.pk)
    return render(request, 'examens/session_form.html', {
        'form': form,
        'titre': 'Nouvelle session d\'examen',
        'submit_label': 'Créer la session',
    })


@login_required
def session_edit(request, session_id):
    session = get_object_or_404(SessionExamen, pk=session_id)
    form = SessionExamenForm(request.POST or None, instance=session)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Session « {session.libelle} » mise à jour.")
        return redirect('examens:session_detail', session_id=session.pk)
    return render(request, 'examens/session_form.html', {
        'form': form,
        'session': session,
        'titre': f'Modifier — {session.libelle}',
        'submit_label': 'Enregistrer',
    })


@login_required
def session_detail(request, session_id):
    etab = getattr(request.user, 'etablissement', None)
    session = get_object_or_404(
        SessionExamen.objects.select_related('annee_scolaire'), pk=session_id
    )
    
    if etab and session.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('examens:session_list')
    
    salles_qs = SalleExamen.objects.annotate(nb_places_prises=Count('placements'))
    centres = session.centres.prefetch_related(
        Prefetch('salles', queryset=salles_qs),
        'candidats__inscription__eleve',
    )

    for centre in centres:
        for salle in centre.salles.all():
            salle.places_restantes = max(salle.capacite - salle.nb_places_prises, 0)
    
    nb_inscrits = session.inscriptions_examen.count()
    nb_admis = session.inscriptions_examen.filter(statut='ADMIS').count()
    taux_reussite = round((nb_admis / nb_inscrits * 100), 1) if nb_inscrits else 0

    # Classes de l'année pour le formulaire d'inscription
    classes = Classe.objects.filter(
        inscriptions__annee_scolaire=session.annee_scolaire
    ).distinct().order_by('cycle__ordre', 'nom')

    return render(request, 'examens/session_detail.html', {
        'session': session,
        'centres': centres,
        'nb_inscrits': nb_inscrits,
        'nb_admis': nb_admis,
        'taux_reussite': taux_reussite,
        'classes': classes,
    })


# ── Inscription d'une classe ──────────────────────────────────────────────────

@login_required
def inscrire_classe(request, session_id, classe_id):
    session = get_object_or_404(SessionExamen, pk=session_id)
    classe = get_object_or_404(Classe, pk=classe_id)

    inscriptions_scolaires = (
        Inscription.objects
        .filter(classe=classe, annee_scolaire=session.annee_scolaire)
        .exclude(statut='ABANDON')
        .select_related('eleve')
    )

    if request.method == 'POST':
        centre_id = request.POST.get('centre')
        centre = get_object_or_404(CentreExamen, pk=centre_id) if centre_id else None
        count = 0
        for ins in inscriptions_scolaires:
            _, created = InscriptionExamen.objects.get_or_create(
                session=session,
                inscription=ins,
                defaults={'centre': centre}
            )
            if created:
                count += 1
        messages.success(request, f"{count} élève(s) inscrit(s) à « {session} ».")
        return redirect('examens:session_detail', session_id=session.pk)

    centres = session.centres.all()
    deja_inscrits = set(
        InscriptionExamen.objects
        .filter(session=session, inscription__in=inscriptions_scolaires)
        .values_list('inscription_id', flat=True)
    )
    return render(request, 'examens/inscrire_classe.html', {
        'session': session,
        'classe': classe,
        'inscriptions_scolaires': inscriptions_scolaires,
        'centres': centres,
        'deja_inscrits': deja_inscrits,
    })


# ── Saisie des résultats ──────────────────────────────────────────────────────

@login_required
def saisie_resultats(request, session_id):
    etab = getattr(request.user, 'etablissement', None)
    session = get_object_or_404(SessionExamen, pk=session_id)
    
    if etab and session.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('examens:session_list')
    
    candidats = session.inscriptions_examen.select_related(
        'inscription__eleve', 'centre'
    ).order_by('numero_table', 'inscription__eleve__nom')

    if request.method == 'POST':
        erreurs_moyenne = []
        for candidat in candidats:
            statut = request.POST.get(f'statut_{candidat.pk}')
            moyenne = request.POST.get(f'moyenne_{candidat.pk}')
            mention = request.POST.get(f'mention_{candidat.pk}', '')
            if statut:
                candidat.statut = statut
                candidat.mention = mention
                if moyenne:
                    try:
                        candidat.moyenne_examen = Decimal(moyenne.replace(',', '.'))
                    except InvalidOperation:
                        erreurs_moyenne.append(
                            candidat.inscription.eleve.get_nom_complet()
                        )
                candidat.save(update_fields=['statut', 'moyenne_examen', 'mention'])
        if erreurs_moyenne:
            messages.warning(
                request,
                f"Moyenne invalide ignorée pour : {', '.join(erreurs_moyenne)}."
            )
        messages.success(request, "Résultats enregistrés.")
        return redirect('examens:session_detail', session_id=session.pk)

    return render(request, 'examens/saisie_resultats.html', {
        'session': session,
        'candidats': candidats,
        'statuts': InscriptionExamen.StatutChoices.choices,
    })


# ── Export CSV des résultats ─────────────────────────────────────────────────

@login_required
def session_resultats_csv(request, session_id):
    """Export CSV des resultats d'une session d'examen."""
    session = get_object_or_404(
        SessionExamen.objects.select_related('annee_scolaire'), pk=session_id
    )

    candidats = (
        session.inscriptions_examen
        .select_related(
            'inscription__eleve',
            'inscription__classe',
            'centre',
        )
        .order_by('centre__nom', 'numero_table', 'inscription__eleve__nom')
    )

    nom_fichier = f"resultats_{session.libelle}_{session.annee_scolaire}".replace(' ', '_') + '.csv'
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'N° Table', 'Nom', 'Prenom', 'Matricule',
        'Classe', 'Centre', 'Statut', 'Moyenne', 'Mention',
    ])

    for c in candidats:
        eleve = c.inscription.eleve
        writer.writerow([
            c.numero_table or '',
            eleve.nom,
            eleve.prenom,
            eleve.matricule or '',
            c.inscription.classe.nom if c.inscription.classe else '',
            c.centre.nom if c.centre else '',
            c.get_statut_display(),
            str(c.moyenne_examen) if c.moyenne_examen is not None else '',
            c.mention or '',
        ])

    return response


# ── Centres ───────────────────────────────────────────────────────────────────

@login_required
def centre_create(request, session_id):
    session = get_object_or_404(SessionExamen, pk=session_id)
    form = CentreExamenForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        centre = form.save(commit=False)
        centre.session = session
        centre.save()
        messages.success(request, f"Centre « {centre.nom} » ajouté.")
        return redirect('examens:session_detail', session_id=session.pk)
    return render(request, 'examens/centre_form.html', {
        'form': form,
        'session': session,
        'titre': 'Nouveau centre d\'examen',
        'submit_label': 'Ajouter le centre',
    })


@login_required
def centre_edit(request, centre_id):
    centre = get_object_or_404(CentreExamen, pk=centre_id)
    form = CentreExamenForm(request.POST or None, instance=centre)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Centre « {centre.nom} » mis à jour.")
        return redirect('examens:session_detail', session_id=centre.session.pk)
    return render(request, 'examens/centre_form.html', {
        'form': form,
        'centre': centre,
        'session': centre.session,
        'titre': f'Modifier — {centre.nom}',
        'submit_label': 'Enregistrer',
    })


@login_required
def centre_delete(request, centre_id):
    centre = get_object_or_404(CentreExamen, pk=centre_id)
    session_id = centre.session.pk
    if request.method == 'POST':
        nb = centre.candidats.count()
        centre.delete()
        messages.warning(request, f"Centre « {centre.nom} » supprimé ({nb} candidat(s) désaffecté(s)).")
        return redirect('examens:session_detail', session_id=session_id)
    return render(request, 'examens/centre_confirm_delete.html', {'centre': centre})


# ── Salles ────────────────────────────────────────────────────────────────────

@login_required
def salle_create(request, centre_id):
    centre = get_object_or_404(CentreExamen, pk=centre_id)
    form = SalleExamenForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        salle = form.save(commit=False)
        salle.centre = centre
        salle.save()
        messages.success(request, f"Salle « {salle.nom} » créée.")
        return redirect('examens:session_detail', session_id=centre.session.pk)
    return render(request, 'examens/salle_form.html', {
        'form': form,
        'centre': centre,
        'titre': f'Nouvelle salle — {centre.nom}',
        'submit_label': 'Créer la salle',
    })


@login_required
def salle_edit(request, salle_id):
    salle = get_object_or_404(SalleExamen, pk=salle_id)
    form = SalleExamenForm(request.POST or None, instance=salle)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Salle « {salle.nom} » mise à jour.")
        return redirect('examens:session_detail', session_id=salle.centre.session.pk)
    return render(request, 'examens/salle_form.html', {
        'form': form,
        'salle': salle,
        'centre': salle.centre,
        'titre': f'Modifier — {salle.nom}',
        'submit_label': 'Enregistrer',
    })


@login_required
def salle_delete(request, salle_id):
    salle = get_object_or_404(SalleExamen, pk=salle_id)
    session_id = salle.centre.session.pk
    if request.method == 'POST':
        salle.delete()
        messages.warning(request, f"Salle « {salle.nom} » supprimée.")
        return redirect('examens:session_detail', session_id=session_id)
    return render(request, 'examens/salle_confirm_delete.html', {'salle': salle})


# ── Placements en salle ───────────────────────────────────────────────────────

@login_required
def placement_salle(request, salle_id):
    """Gestion du placement des candidats dans une salle d'examen."""
    salle = get_object_or_404(
        SalleExamen.objects.select_related('centre__session'), pk=salle_id
    )
    session = salle.centre.session

    placements = (
        salle.placements
        .select_related('candidat__inscription__eleve')
        .order_by('numero_place', 'candidat__numero_table')
    )
    nb_places = placements.count()
    places_restantes = salle.capacite - nb_places

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'placer':
            candidat_ids = request.POST.getlist('candidat_ids')
            count = 0
            for cid in candidat_ids:
                if count >= places_restantes:
                    break
                candidat = get_object_or_404(InscriptionExamen, pk=cid, session=session)
                _, created = PlacementExamen.objects.get_or_create(
                    candidat=candidat,
                    defaults={'salle': salle}
                )
                if created:
                    count += 1
            messages.success(request, f"{count} candidat(s) placé(s) dans « {salle.nom} ».")

        elif action == 'auto':
            non_places_qs = (
                InscriptionExamen.objects
                .filter(session=session, centre=salle.centre, placement__isnull=True)
                .order_by('numero_table', 'inscription__eleve__nom')
            )
            count = 0
            for candidat in non_places_qs[:places_restantes]:
                PlacementExamen.objects.get_or_create(
                    candidat=candidat,
                    defaults={'salle': salle}
                )
                count += 1
            messages.success(request, f"{count} candidat(s) assigné(s) automatiquement à « {salle.nom} ».")

        return redirect('examens:placement_salle', salle_id=salle.pk)

    non_places = (
        InscriptionExamen.objects
        .filter(session=session, centre=salle.centre, placement__isnull=True)
        .select_related('inscription__eleve')
        .order_by('numero_table', 'inscription__eleve__nom')
    )

    return render(request, 'examens/placement_salle.html', {
        'salle': salle,
        'session': session,
        'placements': placements,
        'nb_places': nb_places,
        'places_restantes': places_restantes,
        'non_places': non_places,
    })


@login_required
@require_POST
def placement_delete(request, placement_id):
    """Retire un candidat de sa salle."""
    placement = get_object_or_404(PlacementExamen, pk=placement_id)
    salle_id = placement.salle.pk
    nom = placement.candidat.inscription.eleve.get_nom_complet()
    placement.delete()
    messages.success(request, f"Placement de {nom} supprimé.")
    return redirect('examens:placement_salle', salle_id=salle_id)


# ── Liste des candidats ───────────────────────────────────────────────────────

def _candidats_qs(session, centre_id=None):
    """Queryset candidats d'une session, filtré optionnellement par centre."""
    qs = (
        session.inscriptions_examen
        .select_related('inscription__eleve', 'inscription__classe', 'centre')
        .order_by('centre__nom', 'numero_table', 'inscription__eleve__nom')
    )
    if centre_id:
        qs = qs.filter(centre_id=centre_id)
    return qs


@login_required
def candidats_session(request, session_id):
    """Liste des candidats inscrits à une session, filtrable par centre."""
    etab = getattr(request.user, 'etablissement', None)
    session = get_object_or_404(
        SessionExamen.objects.select_related('annee_scolaire'), pk=session_id
    )
    
    if etab and session.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('examens:session_list')
    )
    centres = session.centres.order_by('code_centre')
    centre_id = request.GET.get('centre', '')
    centre_selectionne = None
    if centre_id:
        centre_selectionne = centres.filter(pk=centre_id).first()

    candidats = _candidats_qs(session, centre_id or None)

    return render(request, 'examens/candidats_session.html', {
        'session': session,
        'centres': centres,
        'centre_selectionne': centre_selectionne,
        'candidats': candidats,
        'nb_total': candidats.count(),
        'statuts': InscriptionExamen.StatutChoices,
    })


@login_required
def candidats_session_pdf(request, session_id):
    """PDF : liste officielle des candidats d'une session (ou d'un centre)."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('examens:candidats_session', session_id=session_id)

    session = get_object_or_404(
        SessionExamen.objects.select_related('annee_scolaire'), pk=session_id
    )
    centre_id = request.GET.get('centre', '')
    centre_selectionne = None
    if centre_id:
        centre_selectionne = session.centres.filter(pk=centre_id).first()

    candidats = _candidats_qs(session, centre_id or None)

    from core.utils import get_etablissement_context
    etab = getattr(request.user, 'etablissement', None)
    etab_ctx = get_etablissement_context(etab, request=request)

    html_string = render_to_string('examens/pdf/liste_candidats.html', {
        'session': session,
        'centre_selectionne': centre_selectionne,
        'candidats': candidats,
        **etab_ctx,
    })
    pdf = WeasyHTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    label = centre_selectionne.code_centre if centre_selectionne else 'tous'
    nom_fichier = f"candidats_{session.libelle}_{label}".replace(' ', '_') + '.pdf'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
    return response
