import logging
from datetime import date as date_module

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import MembrePersonnel, InscriptionPersonnel, SalairePersonnel, CongePersonnel, AbsencePersonnel
from .forms import (
    MembrePersonnelForm, InscriptionPersonnelForm,
    SalairePersonnelForm, CongePersonnelForm, AbsencePersonnelForm,
)
from .selectors import annee_courante, avec_inscriptions_annee, personnel_filtre
from parametres.models import AnneeScolaire, Cycle
from core.utils import get_etablissement_context

from licences.decorators import requires_licence_feature
from licences.pdf_utils import inject_licence_filigrane_context

logger = logging.getLogger(__name__)
@login_required
@requires_licence_feature('gestion_personnel')
def personnel_list(request):
    """Liste des membres du personnel regroupés par cycle."""
    query = request.GET.get('q', '')
    show_all = request.GET.get('tous') == '1'

    etab = getattr(request.user, 'etablissement', None)

    personnel = MembrePersonnel.objects.all()
    if etab:
        personnel = personnel.filter(etablissement=etab)
    if not show_all:
        personnel = personnel.filter(is_active=True)
    if query:
        personnel = personnel.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(matricule__icontains=query)
        )

    # Colonne « Inscription annuelle » : inscriptions actives de l'année courante, préchargées
    annee = annee_courante(etab)
    personnel = avec_inscriptions_annee(personnel, annee)

    # Grouper par cycle
    cycles = Cycle.objects.filter(etablissement=etab).order_by('ordre', 'nom') if etab else Cycle.objects.none()
    cycles_personnel = [
        {'cycle': cycle, 'membres': personnel.filter(cycles=cycle)}
        for cycle in cycles
    ]
    sans_cycle = personnel.filter(cycles__isnull=True)

    nb_inactifs = MembrePersonnel.objects.filter(is_active=False)
    if etab:
        nb_inactifs = nb_inactifs.filter(etablissement=etab)

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
    membres = list(personnel_filtre(etab, query, show_all, ids))

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
    """Détails d'un membre du personnel."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel, pk=pk)
    
    if etab and membre.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Ce membre n'appartient pas à votre établissement.")
        return redirect('personnel:personnel_list')
    
    inscriptions = membre.inscriptions.all()

    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(membre.etablissement, request)
    identite = etab_context.get('identite')
    est_public = identite and identite.type_etablissement == 'PUBLIC'

    context = {
        'membre': membre,
        'inscriptions': inscriptions,
        'est_public': est_public,
    }
    return render(request, 'personnel/personnel_detail.html', context)

@login_required
@requires_licence_feature('gestion_personnel')
def personnel_create(request):
    """Création d'un nouveau membre du personnel."""
    if request.method == 'POST':
        form = MembrePersonnelForm(request.POST, request.FILES)
        if form.is_valid():
            membre = form.save()
            messages.success(request, f"Membre {membre.get_nom_complet()} créé avec succès.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        form = MembrePersonnelForm()
    
    return render(request, 'personnel/personnel_form.html', {'form': form, 'title': "Ajouter un membre"})

@login_required
@requires_licence_feature('gestion_personnel')
def personnel_update(request, pk):
    """Modification d'un membre du personnel."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel, pk=pk)
    
    if etab and membre.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Ce membre n'appartient pas à votre établissement.")
        return redirect('personnel:personnel_list')
    
    if request.method == 'POST':
        form = MembrePersonnelForm(request.POST, request.FILES, instance=membre)
        if form.is_valid():
            membre = form.save()
            messages.success(request, f"Membre {membre.get_nom_complet()} mis à jour.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        form = MembrePersonnelForm(instance=membre)
    
    return render(request, 'personnel/personnel_form.html', {'form': form, 'title': "Modifier le membre", 'membre': membre})

@login_required
@requires_licence_feature('gestion_personnel')
def toggle_active(request, pk):
    """Active ou désactive un membre du personnel."""
    if request.method != 'POST':
        return redirect('personnel:detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel, pk=pk)
    
    if etab and membre.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('personnel:personnel_list')
    
    membre.is_active = not membre.is_active
    membre.save(update_fields=['is_active'])

    action = "réactivé" if membre.is_active else "désactivé"
    messages.success(request, f"{membre.get_nom_complet()} a été {action}.")
    return redirect('personnel:detail', pk=pk)


@login_required
@requires_licence_feature('gestion_personnel')
def inscription_create(request, pk):
    """Inscription annuelle d'un membre du personnel."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel, pk=pk)
    
    if etab and membre.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('personnel:personnel_list')
    
    if request.method == 'POST':
        form = InscriptionPersonnelForm(request.POST, instance=InscriptionPersonnel(personnel=membre))
        if form.is_valid():
            form.save()
            messages.success(request, f"Inscription enregistrée pour {membre.get_nom_complet()}.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        etab = getattr(request.user, 'etablissement', None)
        annee_courante = AnneeScolaire.objects.filter(
            etablissement=etab, est_courante=True
        ).first() if etab else AnneeScolaire.objects.filter(est_courante=True).first()
        form = InscriptionPersonnelForm(initial={'annee_scolaire': annee_courante})

    return render(request, 'personnel/inscription_form.html', {
        'form': form,
        'membre': membre,
        'titre': 'Nouvelle inscription',
    })


@login_required
@requires_licence_feature('gestion_personnel')
def inscription_edit(request, inscription_id):
    """Modification d'une inscription annuelle du personnel."""
    etab = getattr(request.user, 'etablissement', None)
    inscription = get_object_or_404(
        InscriptionPersonnel.objects.select_related('personnel'), pk=inscription_id
    )
    
    if etab and inscription.personnel.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('personnel:personnel_list')
    
    membre = inscription.personnel
    
    if request.method == 'POST':
        form = InscriptionPersonnelForm(request.POST, instance=inscription)
        if form.is_valid():
            form.save()
            messages.success(request, "Inscription mise à jour.")
            return redirect('personnel:detail', pk=membre.pk)
    else:
        form = InscriptionPersonnelForm(instance=inscription)

    return render(request, 'personnel/inscription_form.html', {
        'form': form,
        'membre': membre,
        'inscription': inscription,
        'titre': 'Modifier l\'inscription',
    })


@login_required
@require_POST
def inscription_delete(request, inscription_id):
    """Suppression d'une inscription annuelle du personnel."""
    inscription = get_object_or_404(
        InscriptionPersonnel.objects.select_related('personnel'), pk=inscription_id
    )
    membre = inscription.personnel
    inscription.delete()
    messages.success(request, "Inscription supprimée.")
    return redirect('personnel:detail', pk=membre.pk)


@login_required
@requires_licence_feature('gestion_personnel')
def contrat_travail(request, pk):
    """Aperçu et génération PDF du contrat de travail (établissements non-publics uniquement)."""
    membre = get_object_or_404(
        MembrePersonnel.objects.select_related('etablissement').prefetch_related('cycles'),
        pk=pk
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

    inscription_courante = InscriptionPersonnel.objects.filter(
        personnel=membre, annee_scolaire=annee
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
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel.objects.select_related('etablissement'), pk=pk,
                               **({'etablissement': etab} if etab else {}))
    annee = AnneeScolaire.objects.filter(etablissement=membre.etablissement, est_courante=True).first()
    inscription = InscriptionPersonnel.objects.filter(personnel=membre, annee_scolaire=annee).select_related('poste', 'cycle').first() if annee else None
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
        MembrePersonnel.objects.select_related('etablissement').prefetch_related('cycles'),
        pk=pk
    )

    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(membre.etablissement, request)

    # Inscription courante pour récupérer le poste
    from parametres.models import AnneeScolaire
    annee = AnneeScolaire.objects.filter(
        etablissement=membre.etablissement, est_courante=True
    ).first()

    inscription_courante = InscriptionPersonnel.objects.filter(
        personnel=membre, annee_scolaire=annee
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


# ═══════════════════════════════════════════════════════════════════
# SALAIRES
# ═══════════════════════════════════════════════════════════════════

@login_required
@requires_licence_feature('gestion_personnel')
def salaire_list(request):
    """Liste des bulletins de salaire de l'établissement."""
    etab = getattr(request.user, 'etablissement', None)
    qs = SalairePersonnel.objects.select_related('personnel', 'annee_scolaire')
    if etab:
        qs = qs.filter(personnel__etablissement=etab)

    mois_filtre = request.GET.get('mois', '')
    annee_filtre = request.GET.get('annee', str(date_module.today().year))
    statut_filtre = request.GET.get('statut', '')
    personnel_id = request.GET.get('personnel', '')

    if mois_filtre:
        qs = qs.filter(mois=mois_filtre)
    if annee_filtre:
        qs = qs.filter(annee=annee_filtre)
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if personnel_id:
        qs = qs.filter(personnel__pk=personnel_id)

    context = {
        'salaires': qs,
        'mois_filtre': mois_filtre,
        'annee_filtre': annee_filtre,
        'statut_filtre': statut_filtre,
        'mois_choices': SalairePersonnel.MOIS_CHOICES,
        'statut_choices': SalairePersonnel.StatutChoices.choices,
        'annee_courante': date_module.today().year,
    }
    return render(request, 'personnel/salaire_list.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def salaire_create(request, pk=None):
    """Créer un bulletin de salaire (pour un membre spécifique ou depuis la liste)."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel, pk=pk) if pk else None

    today = date_module.today()
    annee_courante = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    initial = {
        'annee': today.year,
        'mois': today.month,
        'annee_scolaire': annee_courante,
    }
    if membre:
        initial['personnel'] = membre
        # Pré-calculer la prime d'ancienneté si salaire_base disponible
        dernier = SalairePersonnel.objects.filter(personnel=membre).order_by('-annee', '-mois').first()
        if dernier:
            initial['salaire_base'] = dernier.salaire_base
            initial['indemnite_transport'] = dernier.indemnite_transport
            initial['indemnite_logement'] = dernier.indemnite_logement
            initial['prime_anciennete'] = SalairePersonnel.calculer_prime_anciennete(
                membre, dernier.salaire_base
            )

    if request.method == 'POST':
        form = SalairePersonnelForm(request.POST, etablissement=etab)
        if form.is_valid():
            salaire = form.save(commit=False)
            salaire.created_by = request.user
            salaire.save()
            messages.success(
                request,
                f"Bulletin de salaire de {salaire.personnel.get_nom_complet()} "
                f"({salaire.get_mois_display()} {salaire.annee}) enregistré."
            )
            return redirect('personnel:salaire_detail', pk=salaire.pk)
    else:
        form = SalairePersonnelForm(initial=initial, etablissement=etab)

    return render(request, 'personnel/salaire_form.html', {
        'form': form,
        'membre': membre,
        'titre': 'Nouveau bulletin de salaire',
    })


@login_required
@requires_licence_feature('gestion_personnel')
def salaire_detail(request, pk):
    """Détail d'un bulletin de salaire (aperçu + PDF)."""
    salaire = get_object_or_404(
        SalairePersonnel.objects.select_related('personnel', 'annee_scolaire', 'created_by'),
        pk=pk
    )
    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(salaire.personnel.etablissement, request)

    context = {'salaire': salaire, **etab_context}

    if request.GET.get('format') == 'pdf':
        try:
            from core.pdf import HTML
            from django.template.loader import render_to_string
            html_str = render_to_string('personnel/pdf/bulletin_salaire.html', context, request=request)
            pdf = HTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()
            nom = f"{salaire.personnel.nom}_{salaire.personnel.prenom}".replace(' ', '_')
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'inline; filename="salaire_{nom}_{salaire.mois:02d}_{salaire.annee}.pdf"'
            )
            return response
        except ImportError:
            messages.error(request, "WeasyPrint n'est pas installé.")

    return render(request, 'personnel/salaire_detail.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def salaire_update(request, pk):
    """Modifier un bulletin de salaire (seulement si BROUILLON)."""
    salaire = get_object_or_404(SalairePersonnel, pk=pk)
    if salaire.statut != SalairePersonnel.StatutChoices.BROUILLON:
        messages.error(request, "Seuls les bulletins en brouillon peuvent être modifiés.")
        return redirect('personnel:salaire_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    if request.method == 'POST':
        form = SalairePersonnelForm(request.POST, instance=salaire, etablissement=etab)
        if form.is_valid():
            form.save()
            messages.success(request, "Bulletin mis à jour.")
            return redirect('personnel:salaire_detail', pk=pk)
    else:
        form = SalairePersonnelForm(instance=salaire, etablissement=etab)

    return render(request, 'personnel/salaire_form.html', {
        'form': form,
        'salaire': salaire,
        'titre': 'Modifier le bulletin de salaire',
    })


@login_required
@require_POST
def salaire_valider(request, pk):
    """Passer un bulletin de BROUILLON → VALIDE."""
    salaire = get_object_or_404(SalairePersonnel, pk=pk)
    if salaire.statut == SalairePersonnel.StatutChoices.BROUILLON:
        salaire.statut = SalairePersonnel.StatutChoices.VALIDE
        salaire.save(update_fields=['statut'])
        messages.success(request, "Bulletin validé.")
    return redirect('personnel:salaire_detail', pk=pk)


@login_required
@require_POST
def salaire_payer(request, pk):
    """Passer un bulletin de VALIDE → PAYE."""
    salaire = get_object_or_404(SalairePersonnel, pk=pk)
    if salaire.statut == SalairePersonnel.StatutChoices.VALIDE:
        salaire.statut = SalairePersonnel.StatutChoices.PAYE
        salaire.date_paiement = date_module.today()
        salaire.reference_paiement = request.POST.get('reference_paiement', '')
        salaire.save(update_fields=['statut', 'date_paiement', 'reference_paiement'])
        messages.success(request, "Paiement enregistré.")
    return redirect('personnel:salaire_detail', pk=pk)


@login_required
@require_POST
def salaire_delete(request, pk):
    """Supprimer un bulletin (seulement BROUILLON)."""
    salaire = get_object_or_404(SalairePersonnel, pk=pk)
    if salaire.statut != SalairePersonnel.StatutChoices.BROUILLON:
        messages.error(request, "Seuls les bulletins en brouillon peuvent être supprimés.")
        return redirect('personnel:salaire_detail', pk=pk)
    membre_pk = salaire.personnel.pk
    salaire.delete()
    messages.success(request, "Bulletin supprimé.")
    return redirect('personnel:detail', pk=membre_pk)


# ═══════════════════════════════════════════════════════════════════
# CONGÉS
# ═══════════════════════════════════════════════════════════════════

@login_required
@requires_licence_feature('gestion_personnel')
def conge_list(request):
    """Liste des congés de l'établissement."""
    etab = getattr(request.user, 'etablissement', None)
    qs = CongePersonnel.objects.select_related('personnel', 'approuve_par')
    if etab:
        qs = qs.filter(personnel__etablissement=etab)

    statut_filtre = request.GET.get('statut', '')
    type_filtre = request.GET.get('type', '')
    personnel_id = request.GET.get('personnel', '')

    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)
    if type_filtre:
        qs = qs.filter(type_conge=type_filtre)
    if personnel_id:
        qs = qs.filter(personnel__pk=personnel_id)

    context = {
        'conges': qs,
        'statut_filtre': statut_filtre,
        'type_filtre': type_filtre,
        'statut_choices': CongePersonnel.StatutChoices.choices,
        'type_choices': CongePersonnel.TypeCongeChoices.choices,
        'annee_courante': date_module.today().year,
    }
    return render(request, 'personnel/conge_list.html', context)


@login_required
@requires_licence_feature('gestion_personnel')
def conge_create(request, pk=None):
    """Créer une demande de congé."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel, pk=pk) if pk else None

    initial = {}
    if membre:
        initial['personnel'] = membre

    if request.method == 'POST':
        form = CongePersonnelForm(request.POST, etablissement=etab)
        if form.is_valid():
            conge = form.save(commit=False)
            conge.created_by = request.user
            conge.save()
            messages.success(
                request,
                f"Congé de {conge.personnel.get_nom_complet()} enregistré "
                f"({conge.nombre_jours} jours ouvrables)."
            )
            if membre:
                return redirect('personnel:detail', pk=membre.pk)
            return redirect('personnel:conge_list')
    else:
        form = CongePersonnelForm(initial=initial, etablissement=etab)

    annee = date_module.today().year
    jours_info = None
    if membre:
        jours_info = {
            'pris': CongePersonnel.jours_pris_annee(membre, annee),
            'restants': CongePersonnel.jours_restants(membre, annee),
            'droits': CongePersonnel.DROITS_ANNUELS,
            'annee': annee,
        }

    return render(request, 'personnel/conge_form.html', {
        'form': form,
        'membre': membre,
        'jours_info': jours_info,
        'titre': 'Nouvelle demande de congé',
    })


@login_required
@require_POST
def conge_approuver(request, pk):
    """Approuver une demande de congé."""
    conge = get_object_or_404(CongePersonnel, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    directeur = MembrePersonnel.objects.filter(
        etablissement=etab, est_directeur=True, is_active=True
    ).first() if etab else None

    conge.statut = CongePersonnel.StatutChoices.APPROUVE
    conge.date_approbation = date_module.today()
    conge.approuve_par = directeur
    conge.save(update_fields=['statut', 'date_approbation', 'approuve_par'])
    messages.success(request, f"Congé de {conge.personnel.get_nom_complet()} approuvé.")
    return redirect('personnel:detail', pk=conge.personnel.pk)


@login_required
@requires_licence_feature('gestion_personnel')
def conge_autorisation_pdf(request, pk):
    """Génère le PDF d'autorisation de jouissance de congé."""
    conge = get_object_or_404(
        CongePersonnel.objects.select_related(
            'personnel', 'personnel__etablissement', 'approuve_par'
        ),
        pk=pk
    )
    etab = conge.personnel.etablissement

    from core.utils import get_etablissement_context
    etab_context = get_etablissement_context(etab, request)
    identite = etab_context.get('identite')

    # ── Signataire configuré ──────────────────────────────────────
    from parametres.models import TypeDocument, SignataireDocument, AnneeScolaire
    type_doc, _ = TypeDocument.objects.get_or_create(
        code='CONGE_PERSONNEL',
        defaults={
            'libelle': 'Autorisation de Congé Personnel',
            'categorie': 'PERSONNEL',
            'actif': True,
        }
    )
    annee_courante = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first()
    signataire = SignataireDocument.objects.get_signataire(
        cycle=None,
        type_document=type_doc,
        annee_scolaire=annee_courante,
    )
    sig_membre = signataire.get_membre_personnel() if signataire else None

    # ── URLs signature et cachet (depuis IdentiteEtablissement) ──
    signature_url = None
    cachet_url = None
    if identite:
        if identite.signature_directeur:
            signature_url = request.build_absolute_uri(identite.signature_directeur.url)
        if identite.cachet_etablissement:
            cachet_url = request.build_absolute_uri(identite.cachet_etablissement.url)

    context = {
        'conge': conge,
        'today': date_module.today(),
        'signataire': signataire,
        'sig_membre': sig_membre,
        'signature_url': signature_url,
        'cachet_url': cachet_url,
        **etab_context,
    }

    try:
        from core.pdf import HTML
        from django.template.loader import render_to_string
        html_str = render_to_string(
            'personnel/pdf/autorisation_conge.html', context, request=request
        )
        pdf = HTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()
        nom = f"{conge.personnel.nom}_{conge.personnel.prenom}".replace(' ', '_')
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="autorisation_conge_{nom}.pdf"'
        )
        return response
    except ImportError:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('personnel:detail', pk=conge.personnel.pk)


@login_required
@require_POST
def conge_refuser(request, pk):
    """Refuser une demande de congé."""
    conge = get_object_or_404(CongePersonnel, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    directeur = MembrePersonnel.objects.filter(
        etablissement=etab, est_directeur=True, is_active=True
    ).first() if etab else None

    conge.statut = CongePersonnel.StatutChoices.REFUSE
    conge.date_approbation = date_module.today()
    conge.approuve_par = directeur
    conge.observations = request.POST.get('motif_refus', conge.observations)
    conge.save(update_fields=['statut', 'date_approbation', 'approuve_par', 'observations'])
    messages.success(request, f"Congé de {conge.personnel.get_nom_complet()} refusé.")
    return redirect('personnel:detail', pk=conge.personnel.pk)



# ─── PAIE DU MOIS ──────────────────────────────────────────────────────

def _mois_annee(source):
    """(mois, année) demandés — par défaut le mois courant."""
    today = date_module.today()
    try:
        mois = int(source.get('mois', today.month))
    except (TypeError, ValueError):
        mois = today.month
    try:
        annee = int(source.get('annee', today.year))
    except (TypeError, ValueError):
        annee = today.year
    return (mois if 1 <= mois <= 12 else today.month), annee


def _url_paie(mois, annee):
    from django.urls import reverse
    return f"{reverse('personnel:paie_mois')}?mois={mois}&annee={annee}"


@login_required
@requires_licence_feature('gestion_personnel')
def paie_mois(request):
    """Paie du mois : bulletins du mois (statuts, totaux), agents sans bulletin, préparation et validation en masse,
    livre de paie et bulletins en lot."""
    from . import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.GET)
    contexte = paie.livre(etab, mois, annee) if etab else {'salaires': [], 'sans_bulletin': [], 'totaux': {},
                                                            'par_statut': {}, 'mois': mois, 'annee': annee,
                                                            'libelle_mois': paie.MOIS[mois]}
    contexte.update({'mois_choices': SalairePersonnel.MOIS_CHOICES, 'annee_courante': date_module.today().year,
                     'annees': range(date_module.today().year - 3, date_module.today().year + 2)})
    return render(request, 'personnel/paie_mois.html', contexte)


@login_required
@require_POST
@requires_licence_feature('gestion_personnel')
def paie_preparer(request):
    """Crée les brouillons du mois pour tous les agents permanents sans bulletin."""
    from . import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.POST)
    annee_scolaire = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    if etab is None or annee_scolaire is None:
        messages.error(request, "Aucune année scolaire courante : la paie ne peut pas être préparée.")
        return redirect(_url_paie(mois, annee))
    crees, sans_reference = paie.preparer(etab, mois, annee, annee_scolaire, request.user)
    texte = f"{len(crees)} bulletin{'s' if len(crees) > 1 else ''} de {paie.MOIS[mois]} {annee} préparé{'s' if len(crees) > 1 else ''} en brouillon."
    if sans_reference:
        texte += (f" {len(sans_reference)} agent{'s' if len(sans_reference) > 1 else ''} sans bulletin de référence à saisir "
                  f"à la main : {', '.join(m.get_nom_complet() for m in sans_reference[:5])}"
                  f"{'…' if len(sans_reference) > 5 else ''}.")
    messages.success(request, texte)
    return redirect(_url_paie(mois, annee))


@login_required
@require_POST
@requires_licence_feature('gestion_personnel')
def paie_valider(request):
    """Valide tous les brouillons du mois."""
    from . import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.POST)
    nb = paie.valider_brouillons(etab, mois, annee) if etab else 0
    messages.success(request, f"{nb} bulletin{'s' if nb > 1 else ''} validé{'s' if nb > 1 else ''}." if nb else "Aucun brouillon à valider.")
    return redirect(_url_paie(mois, annee))


@login_required
@requires_licence_feature('gestion_personnel')
def livre_paie_pdf(request):
    """Livre de paie du mois (A4 paysage) : une ligne par agent, totaux, signataire."""
    from core.pdf import HTML
    from . import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.GET)
    if etab is None:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('personnel:salaire_list')
    contexte = {**paie.livre(etab, mois, annee), **get_etablissement_context(etab, request), 'now': timezone.now()}
    html_str = render_to_string('personnel/pdf/livre_paie.html', contexte, request=request)
    pdf = HTML(string=html_str, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="livre_paie_{annee}_{mois:02d}.pdf"'
    return response


@login_required
@requires_licence_feature('gestion_personnel')
def bulletins_paie_lot_pdf(request):
    """Tous les bulletins de salaire du mois dans un seul PDF (un bulletin par page, même gabarit que l'unitaire)."""
    from core.pdf import HTML
    from . import paie
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_annee(request.GET)
    if etab is None:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('personnel:salaire_list')
    etab_context = get_etablissement_context(etab, request)
    fragments = [
        render_to_string('personnel/pdf/bulletin_salaire.html', {'salaire': salaire, **etab_context}, request=request)
        for salaire in paie.salaires_du_mois(etab, mois, annee)
    ]
    pdf = HTML.lot(fragments, base_url=request.build_absolute_uri('/'))
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="bulletins_salaire_{annee}_{mois:02d}.pdf"'
    return response


# ═══════════════════════════════════════════════════════════════════
# ABSENCES DU PERSONNEL
# ═══════════════════════════════════════════════════════════════════

def _mois_demande(request):
    """(mois, année) du paramètre ``mois=AAAA-MM`` ; mois courant par défaut."""
    valeur = request.GET.get('mois', '')
    try:
        annee, mois = (int(v) for v in valeur.split('-'))
        if not 1 <= mois <= 12:
            raise ValueError
        return mois, annee
    except (TypeError, ValueError):
        today = date_module.today()
        return today.month, today.year


def _bilan_absences(etab, mois, annee):
    """Par agent ayant au moins une absence sur le mois : absences, jours, jours non justifiés, jours retenus."""
    import calendar
    debut, fin = date_module(annee, mois, 1), date_module(annee, mois, calendar.monthrange(annee, mois)[1])
    lignes = {}
    for a in (AbsencePersonnel.objects.filter(personnel__etablissement=etab, date_debut__lte=fin, date_fin__gte=debut)
              .select_related('personnel').order_by('personnel__nom', 'personnel__prenom')):
        ligne = lignes.setdefault(a.personnel_id, {'membre': a.personnel, 'absences': 0, 'jours': 0, 'non_justifies': 0, 'retenus': 0})
        jours = (min(a.date_fin, fin) - max(a.date_debut, debut)).days + 1
        ligne['absences'] += 1
        ligne['jours'] += jours
        if not a.justifiee:
            ligne['non_justifies'] += jours
            if a.retenue:
                ligne['retenus'] += jours
    return list(lignes.values()), debut, fin


@login_required
def absence_list(request):
    """Absences du personnel : liste du mois (ou d'un agent) et bilan par agent."""
    etab = getattr(request.user, 'etablissement', None)
    mois, annee = _mois_demande(request)
    bilan, debut, fin = _bilan_absences(etab, mois, annee) if etab else ([], None, None)
    qs = AbsencePersonnel.objects.filter(personnel__etablissement=etab).select_related('personnel', 'created_by')
    membre_id = request.GET.get('personnel')
    membre = MembrePersonnel.objects.filter(pk=membre_id, etablissement=etab).first() if membre_id else None
    if membre:
        qs = qs.filter(personnel=membre)
    elif debut:
        qs = qs.filter(date_debut__lte=fin, date_fin__gte=debut)
    return render(request, 'personnel/absence_list.html', {
        'absences': qs[:300], 'bilan': bilan, 'membre': membre,
        'mois_param': f"{annee:04d}-{mois:02d}", 'mois_libelle': date_module(annee, mois, 1),
    })


@login_required
def absence_create(request, pk=None):
    """Enregistrer une absence (depuis la liste ou la fiche de l'agent)."""
    etab = getattr(request.user, 'etablissement', None)
    membre = get_object_or_404(MembrePersonnel, pk=pk, etablissement=etab) if pk else None
    if request.method == 'POST':
        form = AbsencePersonnelForm(request.POST, etablissement=etab)
        if form.is_valid():
            absence = form.save(commit=False)
            absence.created_by = request.user
            absence.save()
            messages.success(request, f"Absence de {absence.personnel.get_nom_complet()} enregistrée "
                                      f"({absence.nombre_jours} jour(s){', retenue proposée sur la paie' if absence.a_retenir else ''}).")
            return redirect('personnel:detail', pk=membre.pk) if membre else redirect('personnel:absence_list')
    else:
        form = AbsencePersonnelForm(initial={'personnel': membre, 'date_debut': date_module.today(), 'date_fin': date_module.today()},
                                    etablissement=etab)
    return render(request, 'personnel/absence_form.html', {'form': form, 'membre': membre, 'titre': "Nouvelle absence"})


@login_required
@require_POST
def absence_delete(request, pk):
    etab = getattr(request.user, 'etablissement', None)
    absence = get_object_or_404(AbsencePersonnel, pk=pk, personnel__etablissement=etab)
    membre_id = absence.personnel_id
    absence.delete()
    messages.success(request, "Absence supprimée.")
    suivant = request.POST.get('suivant')
    return redirect('personnel:detail', pk=membre_id) if suivant == 'fiche' else redirect('personnel:absence_list')
