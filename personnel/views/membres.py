"""Vues du dossier personnel : annuaire, exports, affectations, contrat, attestation et badge."""
import logging
from datetime import date as date_module

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.utils import get_etablissement_context
from licences.decorators import requires_licence_feature
from licences.pdf_utils import inject_licence_filigrane_context
from parametres.models import AnneeScolaire

from ..forms import InscriptionPersonnelForm, MembrePersonnelForm
from ..models import InscriptionPersonnel, MembrePersonnel
from ..selectors import (
    absences_visibles, annee_courante, avec_inscriptions_annee, cycles_accessibles,
    inscriptions_visibles, membres_dans_cycle, membres_visibles, personnel_filtre,
)
from yelen_school.cycle_filter import get_cycle_ids

logger = logging.getLogger(__name__)


@login_required
@requires_licence_feature('gestion_personnel')
def personnel_list(request):
    """Liste des membres du personnel regroupés par cycle."""
    query = request.GET.get('q', '')
    show_all = request.GET.get('tous') == '1'

    etab = getattr(request.user, 'etablissement', None)

    personnel = personnel_filtre(etab, query, show_all, request=request)

    # Colonne « Inscription annuelle » : inscriptions actives de l'année courante, limitées aux cycles autorisés.
    annee = annee_courante(etab)
    personnel = avec_inscriptions_annee(personnel, annee, request=request)

    # Ne présenter que les cycles autorisés ; les affectations annuelles et la classe de rattachement
    # complètent la relation cycles de la fiche, parfois absente sur les anciennes données.
    cycles = cycles_accessibles(request, etab).order_by('ordre', 'nom')
    cycles_personnel = [
        {'cycle': cycle, 'membres': membres_dans_cycle(personnel, cycle)}
        for cycle in cycles
    ]
    if get_cycle_ids(request) is None:
        sans_cycle = personnel.filter(
            cycles__isnull=True, inscriptions__isnull=True, classe_affectation__isnull=True
        ).distinct()
    else:
        sans_cycle = personnel.none()

    nb_inactifs = MembrePersonnel.objects.filter(is_active=False)
    if etab:
        nb_inactifs = nb_inactifs.filter(etablissement=etab)
    nb_inactifs = membres_visibles(request, nb_inactifs)

    context = {
        'personnel_list': personnel,
        'cycles_personnel': cycles_personnel,
        'sans_cycle': sans_cycle,
        'query': query,
        'show_all': show_all,
        'nb_inactifs': nb_inactifs.count(),
        'annee_courante': annee,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'personnel/partials/personnel_table.html', context)

    return render(request, 'personnel/personnel_list.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def personnel_list_csv(request):
    """Export CSV de la liste du personnel (memes filtres que personnel_list)."""
    import csv
    etab = getattr(request.user, 'etablissement', None)
    personnel = personnel_filtre(
        etab, request.GET.get('q', ''), request.GET.get('tous') == '1', request.GET.get('ids', ''),
        request=request,
    )

    nom_fichier = 'personnel'
    if etab:
        nom_fichier += f'_{etab.code}'
    nom_fichier += '.csv'

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Matricule', 'Nom', 'Prenom', 'Genre', 'Date de naissance',
        'Telephone', 'Email', 'Fonction', 'Cycles', 'Actif',
    ])

    for m in personnel:
        writer.writerow([
            m.matricule or '',
            m.nom,
            m.prenom,
            m.get_genre_display() if hasattr(m, 'get_genre_display') else (m.genre or ''),
            m.date_naissance.strftime('%d/%m/%Y') if m.date_naissance else '',
            m.telephone or '',
            m.email or '',
            m.fonction or '',
            ', '.join(c.nom for c in m.cycles.all()),
            'Oui' if m.is_active else 'Non',
        ])

    return response


def titre_liste_personnel(etab):
    """Titre des exports : « Liste du personnel – Année scolaire <année courante> »."""
    annee = annee_courante(etab)
    return f"Liste du personnel – Année scolaire {annee}" if annee else "Liste du personnel"


@login_required
@requires_licence_feature('gestion_personnel')
def personnel_list_xlsx(request):
    """Export Excel de la liste du personnel (mêmes filtres que personnel_list)."""
    from core.excel import ExcelExport

    etab = getattr(request.user, 'etablissement', None)
    personnel = personnel_filtre(
        etab, request.GET.get('q', ''), request.GET.get('tous') == '1', request.GET.get('ids', ''),
        request=request,
    )

    nom_fichier = f"personnel{'_' + etab.code if etab else ''}.xlsx"

    wb = ExcelExport("Personnel")
    wb.add_title(titre_liste_personnel(etab), subtitle=etab.nom if etab else '')
    wb.add_header(['Matricule', 'Nom', 'Prénom', 'Genre', 'Date de naissance', 'Téléphone', 'Email', 'Fonction', 'Cycles', 'Actif'])

    for m in personnel:
        wb.add_row([
            m.matricule or '',
            m.nom,
            m.prenom,
            m.get_genre_display() if hasattr(m, 'get_genre_display') else (m.genre or ''),
            m.date_naissance.strftime('%d/%m/%Y') if m.date_naissance else '',
            m.telephone or '',
            m.email or '',
            m.fonction or '',
            ', '.join(c.nom for c in m.cycles.all()),
            'Oui' if m.is_active else 'Non',
        ])

    return wb.response(nom_fichier)


@login_required
@requires_licence_feature('gestion_personnel')
def personnel_list_pdf(request):
    """Export PDF de la liste du personnel (mêmes filtres que personnel_list, CSV et Excel)."""
    try:
        from core.pdf import HTML
    except (ImportError, OSError) as exc:  # libpango/cairo absents
        logger.error("WeasyPrint indisponible, génération PDF désactivée : %s", exc)
        messages.error(request, "La génération PDF n'est pas disponible sur ce serveur (WeasyPrint manquant).")
        return redirect('personnel:personnel_list')

    etab = getattr(request.user, 'etablissement', None)
    query = request.GET.get('q', '').strip()
    show_all = request.GET.get('tous') == '1'
    ids = request.GET.get('ids', '')
    membres = list(personnel_filtre(etab, query, show_all, ids, request=request))

    etab_context = get_etablissement_context(etab, request) if etab else {}
    context = {
        'etablissement': etab,  # requis par le filigrane de licence (pdf/partials/filigrane_licence.html)
        'membres': membres,
        'nb_total': len(membres),
        'nb_hommes': sum(1 for m in membres if m.genre == 'M'),
        'nb_femmes': sum(1 for m in membres if m.genre == 'F'),
        'nb_inactifs': sum(1 for m in membres if not m.is_active),
        'query': query,
        'show_all': show_all,
        'selection': bool(ids),
        'etab_nom': etab.nom if etab else 'YELEN SCHOOL',
        'titre': titre_liste_personnel(etab),
        'date_edition': timezone.localtime().strftime('%d/%m/%Y à %H:%M'),
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url') or etab_context.get('etab_logo_url'),
    }
    context = inject_licence_filigrane_context(context, request.user, etab)

    html_str = render_to_string('personnel/pdf/liste_personnel.html', context)
    pdf = HTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()

    nom_fichier = f"personnel{'_' + etab.code if etab else ''}.pdf"
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
    return response


@login_required
@requires_licence_feature('gestion_personnel')
def personnel_detail(request, pk):
    """Détails d'un membre du personnel, sans affectations hors du périmètre autorisé."""
    cycle_ids = get_cycle_ids(request)
    membre = get_object_or_404(
        membres_visibles(request).select_related('etablissement', 'classe_affectation__cycle')
        .prefetch_related('cycles'),
        pk=pk,
    )
    inscriptions = inscriptions_visibles(
        membre.inscriptions.select_related('annee_scolaire', 'cycle', 'poste').order_by('-annee_scolaire'),
        request,
    )
    cycles_membre = membre.cycles.all()
    classe_affectation = membre.classe_affectation
    if cycle_ids is not None:
        cycles_membre = cycles_membre.filter(pk__in=cycle_ids)
        if classe_affectation and classe_affectation.cycle_id not in cycle_ids:
            classe_affectation = None

    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(membre.etablissement, request)
    identite = etab_context.get('identite')
    est_public = identite and identite.type_etablissement == 'PUBLIC'

    context = {
        'membre': membre,
        'inscriptions': inscriptions,
        'cycles_membre': cycles_membre,
        'classe_affectation': classe_affectation,
        'cycles_restreints': cycle_ids is not None,
        'salaires_recents': membre.salaires.all()[:4],
        'absences_recentes': absences_visibles(
            membre.absences.select_related('classe', 'matiere'), request,
        )[:4],
        'conges_recents': membre.conges.all()[:4],
        'est_public': est_public,
    }
    return render(request, 'personnel/personnel_detail.html', context)

@login_required
@requires_licence_feature('gestion_personnel')
def personnel_create(request):
    """Création d'un nouveau membre du personnel."""
    cycles_autorises = get_cycle_ids(request)
    if request.method == 'POST':
        form = MembrePersonnelForm(
            request.POST, request.FILES,
            etablissement=getattr(request.user, 'etablissement', None),
            cycles_autorises=cycles_autorises,
        )
        form.fields['cycles'].required = cycles_autorises is not None
        if form.is_valid():
            membre = form.save()
            messages.success(request, f"Membre {membre.get_nom_complet()} créé avec succès.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        form = MembrePersonnelForm(
            etablissement=getattr(request.user, 'etablissement', None),
            cycles_autorises=cycles_autorises,
        )
        form.fields['cycles'].required = cycles_autorises is not None

    return render(request, 'personnel/personnel_form.html', {'form': form, 'title': "Ajouter un membre"})

@login_required
@requires_licence_feature('gestion_personnel')
def personnel_update(request, pk):
    """Modification d'un membre du personnel."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(membres_visibles(request), pk=pk)
    
    if request.method == 'POST':
        form = MembrePersonnelForm(
            request.POST, request.FILES, instance=membre, etablissement=etab,
            cycles_autorises=get_cycle_ids(request),
        )
        if form.is_valid():
            membre = form.save()
            messages.success(request, f"Membre {membre.get_nom_complet()} mis à jour.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        form = MembrePersonnelForm(
            instance=membre, etablissement=etab, cycles_autorises=get_cycle_ids(request),
        )
    
    return render(request, 'personnel/personnel_form.html', {'form': form, 'title': "Modifier le membre", 'membre': membre})

@login_required
@requires_licence_feature('gestion_personnel')
def toggle_active(request, pk):
    """Active ou désactive un membre du personnel."""
    if request.method != 'POST':
        return redirect('personnel:detail', pk=pk)

    membre = get_object_or_404(membres_visibles(request), pk=pk)
    membre.is_active = not membre.is_active
    membre.save(update_fields=['is_active'])

    action = "réactivé" if membre.is_active else "désactivé"
    messages.success(request, f"{membre.get_nom_complet()} a été {action}.")
    return redirect('personnel:detail', pk=pk)


@login_required
@requires_licence_feature('gestion_personnel')
def inscription_create(request, pk):
    """Inscription annuelle d'un membre du personnel."""
    cycle_ids = get_cycle_ids(request)
    membre = get_object_or_404(membres_visibles(request), pk=pk)
    etab = membre.etablissement
    
    if request.method == 'POST':
        form = InscriptionPersonnelForm(
            request.POST, instance=InscriptionPersonnel(personnel=membre),
            etablissement=etab, cycles_autorises=cycle_ids,
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"Inscription enregistrée pour {membre.get_nom_complet()}.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        annee_courante = AnneeScolaire.objects.filter(
            etablissement=etab, est_courante=True
        ).first()
        form = InscriptionPersonnelForm(
            initial={'annee_scolaire': annee_courante},
            etablissement=etab, cycles_autorises=cycle_ids,
        )

    return render(request, 'personnel/inscription_form.html', {
        'form': form,
        'membre': membre,
        'titre': 'Nouvelle inscription',
    })


@login_required
@requires_licence_feature('gestion_personnel')
def inscription_edit(request, inscription_id):
    """Modification d'une inscription annuelle du personnel."""
    cycle_ids = get_cycle_ids(request)
    inscriptions = inscriptions_visibles(
        InscriptionPersonnel.objects.select_related('personnel'), request,
    ).filter(personnel__in=membres_visibles(request))
    inscription = get_object_or_404(inscriptions, pk=inscription_id)
    membre = inscription.personnel
    
    if request.method == 'POST':
        form = InscriptionPersonnelForm(
            request.POST, instance=inscription, etablissement=membre.etablissement,
            cycles_autorises=cycle_ids,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Inscription mise à jour.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        form = InscriptionPersonnelForm(
            instance=inscription, etablissement=membre.etablissement, cycles_autorises=cycle_ids,
        )

    return render(request, 'personnel/inscription_form.html', {
        'form': form,
        'membre': membre,
        'inscription': inscription,
        'titre': 'Modifier l\'inscription',
    })


@login_required
@require_POST
@requires_licence_feature('gestion_personnel')
def inscription_delete(request, inscription_id):
    """Suppression d'une inscription annuelle dans un cycle accessible."""
    inscriptions = inscriptions_visibles(
        InscriptionPersonnel.objects.select_related('personnel'), request,
    ).filter(personnel__in=membres_visibles(request))
    inscription = get_object_or_404(inscriptions, pk=inscription_id)
    membre = inscription.personnel
    inscription.delete()
    messages.success(request, "Inscription supprimée.")
    return redirect('personnel:detail', pk=membre.pk)


@login_required
@requires_licence_feature('gestion_personnel')
def contrat_travail(request, pk):
    """Aperçu et génération PDF du contrat de travail (établissements non-publics uniquement)."""
    membre = get_object_or_404(
        membres_visibles(request).select_related('etablissement').prefetch_related('cycles'),
        pk=pk,
    )

    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(membre.etablissement, request)

    identite = etab_context.get('identite')

    # Bloquer pour les établissements publics
    if identite and identite.type_etablissement == 'PUBLIC':
        messages.error(request, "Le contrat de travail n'est pas disponible pour les établissements publics.")
        return redirect('personnel:detail', pk=pk)

    from parametres.models import AnneeScolaire
    annee = AnneeScolaire.objects.filter(
        etablissement=membre.etablissement, est_courante=True
    ).first()

    inscription_courante = inscriptions_visibles(
        InscriptionPersonnel.objects.filter(personnel=membre, annee_scolaire=annee), request,
    ).select_related('poste', 'cycle').first() if annee else None

    from datetime import date as date_module
    today = date_module.today()

    # Clauses pour l'aperçu HTML (résumé lisible, même contenu que le PDF)
    type_contrat = (
        "CDD (Contrat à durée déterminée)" if membre.est_contractuel
        else "Vacation à temps partiel" if membre.est_vacataire
        else "CDI (Contrat à durée indéterminée)"
    )
    poste_str = inscription_courante.poste.titre if inscription_courante and inscription_courante.poste else membre.fonction
    cycle_str = f", cycle {inscription_courante.cycle.nom}" if inscription_courante and inscription_courante.cycle else ""
    date_debut_str = (
        inscription_courante.date_debut.strftime("%d/%m/%Y")
        if inscription_courante and inscription_courante.date_debut
        else today.strftime("%d/%m/%Y")
    )
    clauses = [
        ("Article 1 — Engagement et Fonction",
         f"L'Établissement engage l'Agent en qualité de {membre.fonction}, au poste de {poste_str}{cycle_str}."),
        ("Article 2 — Durée",
         f"Type de contrat : {type_contrat}. Prise de fonction : {date_debut_str}."),
        ("Article 3 — Rémunération",
         "Rémunération fixée selon la grille salariale interne, conformément aux dispositions légales en vigueur."),
        ("Article 4 — Obligations",
         "Exercer ses fonctions avec diligence, probité et dans le respect de l'éthique professionnelle."),
        ("Article 5 — Résiliation",
         "Préavis d'un (01) mois, sauf faute grave ou lourde dûment constatée."),
    ]

    context = {
        'membre': membre,
        'inscription': inscription_courante,
        'annee': annee,
        'today': today,
        'clauses': clauses,
        **etab_context,
    }

    if request.GET.get('format') == 'pdf':
        try:
            from core.pdf import HTML
            html = render(request, 'personnel/pdf/contrat_travail.html', context)
            pdf = HTML(string=html.content.decode()).write_pdf()
            nom = f"{membre.nom}_{membre.prenom}".replace(' ', '_')
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="contrat_{nom}.pdf"'
            return response
        except ImportError:
            messages.error(request, "WeasyPrint n'est pas installé.")
            return redirect('personnel:detail', pk=pk)

    return render(request, 'personnel/contrat_preview.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def attestation_travail(request, pk):
    """Attestation de travail (A4 portrait, signée par le signataire configuré) : aperçu HTML ou PDF (?format=pdf)."""
    membre = get_object_or_404(
        membres_visibles(request).select_related('etablissement'), pk=pk,
    )
    annee = AnneeScolaire.objects.filter(etablissement=membre.etablissement, est_courante=True).first()
    inscription = inscriptions_visibles(
        InscriptionPersonnel.objects.filter(personnel=membre, annee_scolaire=annee), request,
    ).select_related('poste', 'cycle').first() if annee else None
    type_contrat = ("contrat à durée déterminée" if membre.est_contractuel else "vacation à temps partiel" if membre.est_vacataire
                    else "contrat à durée indéterminée")
    context = {
        'membre': membre, 'inscription': inscription, 'annee_scolaire': annee, 'type_contrat': type_contrat,
        'poste': inscription.poste.titre if inscription and inscription.poste else membre.fonction,
        'today': date_module.today(),
        **get_etablissement_context(membre.etablissement, request),
    }
    if request.GET.get('format') == 'pdf':
        from core.pdf import HTML
        html = render_to_string('personnel/pdf/attestation_travail.html', context, request=request)
        pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()
        nom = f"{membre.nom}_{membre.prenom}".replace(' ', '_')
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="attestation_travail_{nom}.pdf"'
        return response
    return render(request, 'personnel/attestation_travail_preview.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def badge_personnel(request, pk):
    """Aperçu et génération PDF du badge d'un membre du personnel."""
    membre = get_object_or_404(
        membres_visibles(request).select_related('etablissement').prefetch_related('cycles'),
        pk=pk,
    )

    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(membre.etablissement, request)

    # Inscription courante pour récupérer le poste
    from parametres.models import AnneeScolaire
    annee = AnneeScolaire.objects.filter(
        etablissement=membre.etablissement, est_courante=True
    ).first()

    inscription_courante = inscriptions_visibles(
        InscriptionPersonnel.objects.filter(personnel=membre, annee_scolaire=annee), request,
    ).select_related('poste', 'cycle').first() if annee else None

    # Photo URL absolue pour WeasyPrint
    photo_url = None
    if membre.photo:
        photo_url = request.build_absolute_uri(membre.photo.url)

    context = {
        'membre': membre,
        'inscription': inscription_courante,
        'annee': annee,
        'photo_url': photo_url,
        **etab_context,
    }

    if request.GET.get('format') == 'pdf':
        try:
            from core.pdf import HTML
            html = render(request, 'personnel/pdf/badge_personnel.html', context)
            pdf = HTML(string=html.content.decode()).write_pdf()
            nom = f"{membre.nom}_{membre.prenom}".replace(' ', '_')
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="badge_{nom}.pdf"'
            return response
        except ImportError:
            messages.error(request, "WeasyPrint n'est pas installé.")
            return redirect('personnel:detail', pk=pk)

    return render(request, 'personnel/badge_preview.html', context)

