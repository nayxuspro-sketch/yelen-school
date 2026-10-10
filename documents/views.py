"""
Module Documents - Views
========================
YELEN SCHOOL v3.4 - Génération des documents officiels

Gère :
- Liste des documents générés
- Génération d'un certificat de scolarité (PDF via WeasyPrint)
- Liste alphabétique de classe (PDF)
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator

from django.db.models import Q
from parametres.models import TypeDocument, AnneeScolaire, Classe, Cycle, SignataireDocument
from inscriptions.models import Inscription

from .models import Document
from core.utils import get_etablissement_context
from core.models import RoleChoices

# P2 — filigrane PDF avec licence
try:
    from licences.pdf_utils import inject_licence_filigrane_context
except ImportError:
    def inject_licence_filigrane_context(context, user, etablissement=None):
        return context


def _can_generate_document(user):
    """Vérifie si l'utilisateur peut générer des documents officiels."""
    if user.role in (RoleChoices.SUPER_ADMIN, RoleChoices.DIRECTEUR, RoleChoices.CENSEUR):
        return True
    if user.role == RoleChoices.SECRETAIRE:
        return True
    if user.role == RoleChoices.COMPTABLE:
        return True
    return False


@login_required
def document_list(request):
    """Liste des documents générés avec filtres par année, type et recherche."""
    etab = getattr(request.user, 'etablissement', None)
    query = request.GET.get('q', '').strip()
    annee_id = request.GET.get('annee_id', '').strip()
    type_id = request.GET.get('type_id', '').strip()
    page_number = request.GET.get('page', 1)

    annees_qs = AnneeScolaire.objects.order_by('-libelle')
    if etab:
        annees_qs = annees_qs.filter(etablissement=etab)

    annee_selectionnee = None
    if annee_id:
        annee_selectionnee = annees_qs.filter(pk=annee_id).first()
    if not annee_selectionnee:
        annee_selectionnee = annees_qs.filter(est_courante=True).first()

    types_qs = TypeDocument.objects.filter(actif=True).order_by('libelle')

    qs = Document.objects.select_related(
        'type_document', 'annee_scolaire',
        'inscription__eleve', 'classe', 'genere_par'
    ).order_by('-created_at')

    if etab:
        qs = qs.filter(annee_scolaire__etablissement=etab)
    if annee_selectionnee:
        qs = qs.filter(annee_scolaire=annee_selectionnee)
    if type_id:
        qs = qs.filter(type_document_id=type_id)
    if query:
        qs = qs.filter(
            Q(numero_document__icontains=query) |
            Q(inscription__eleve__nom__icontains=query) |
            Q(inscription__eleve__prenom__icontains=query) |
            Q(type_document__libelle__icontains=query) |
            Q(classe__nom__icontains=query) |
            Q(observations__icontains=query)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)

    return render(request, 'documents/document_list.html', {
        'documents': page_obj,
        'page_obj': page_obj,
        'query': query,
        'annees': annees_qs,
        'annee_selectionnee': annee_selectionnee,
        'types': types_qs,
        'type_id': type_id,
    })


@login_required
def certificat_scolarite(request, inscription_id):
    """Génère un certificat de scolarité pour un élève."""
    # Vérification du rôle - seul le personnel autorisé peut générer des documents
    if not _can_generate_document(request.user):
        messages.error(request, "Vous n'êtes pas autorisé à générer des documents officiels.")
        return redirect('documents:document_list')
    
    # Vérification que l'inscription appartient à l'établissement de l'utilisateur
    etab_user = request.user.etablissement
    inscription = get_object_or_404(
        Inscription.objects.select_related(
            'eleve', 'classe__cycle', 'annee_scolaire'
        ),
        pk=inscription_id
    )
    
    # IDOR - Vérification que l'élève appartient à l'établissement de l'utilisateur
    if etab_user and inscription.annee_scolaire.etablissement != etab_user:
        messages.error(request, "Vous n'avez pas accès à ce document.")
        return redirect('documents:document_list')

    type_doc, _ = TypeDocument.objects.get_or_create(
        code='CERT_SCOL',
        defaults={
            'libelle': 'Certificat de Scolarité',
            'categorie': 'SCOLARITE',
            'actif': True,
        }
    )

    etab = inscription.annee_scolaire.etablissement
    etab_context = get_etablissement_context(etab, request)
    annee = inscription.annee_scolaire
    cycle = inscription.classe.cycle

    # Résoudre le signataire (même logique que {% signataire_auto %})
    signataire = SignataireDocument.objects.get_signataire(
        cycle=cycle,
        type_document=type_doc,
        annee_scolaire=annee,
    )
    sig_membre = signataire.get_membre_personnel() if signataire else None

    context = {
        'inscription': inscription,
        'eleve': inscription.eleve,
        'classe': inscription.classe,
        'annee_scolaire': annee,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'signataire': signataire,
        'sig_membre': sig_membre,
    }
    # P2 — filigrane licence
    context = inject_licence_filigrane_context(context, request.user, etab)

    if request.GET.get('format') == 'pdf':
        try:
            from core.pdf import HTML
            from django.template.loader import render_to_string
            from django.core.files.base import ContentFile

            sig_nom = ''
            if sig_membre:
                sig_nom = f"{sig_membre.nom} {sig_membre.prenom}"
            doc = Document.objects.create(
                type_document=type_doc,
                annee_scolaire=annee,
                inscription=inscription,
                genere_par=request.user,
                signataire_nom=sig_nom,
            )
            context['document'] = doc

            # Retirer les titres honorifiques du PDF certificat (en mémoire uniquement)
            if signataire:
                signataire.titre_honorifique = ''
                signataire.titres_honorifiques = []

            html_string = render_to_string(
                'documents/pdf/certificat_scolarite.html',
                context,
                request=request,
            ).strip()
            base_url = request.build_absolute_uri('/')
            pdf = HTML(string=html_string, base_url=base_url).write_pdf(
                presentational_hints=True,
            )

            nom = inscription.eleve.nom.replace(' ', '_')
            doc.fichier.save(
                f"certificat_{nom}_{doc.numero_document}.pdf",
                ContentFile(pdf), save=True
            )

            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="certificat_{nom}.pdf"'
            return response
        except ImportError:
            messages.error(request, "WeasyPrint n'est pas installé.")
            return redirect('documents:document_list')

    return render(request, 'documents/certificat_preview.html', context)


@login_required
def liste_classes_selector(request):
    """Sélection de la classe et de l'année scolaire pour la liste alphabétique."""
    annees = AnneeScolaire.objects.order_by('-libelle')
    annee_courante = annees.filter(est_courante=True).first()

    # Année sélectionnée via le formulaire (GET ?annee_id=)
    annee_id = request.GET.get('annee_id')
    annee_selectionnee = None
    if annee_id:
        annee_selectionnee = AnneeScolaire.objects.filter(pk=annee_id).first()
    if not annee_selectionnee:
        annee_selectionnee = annee_courante

    # Classes ayant au moins une inscription pour l'année sélectionnée
    classes_ids = (
        Inscription.objects
        .filter(annee_scolaire=annee_selectionnee)
        .values_list('classe_id', flat=True)
        .distinct()
    )
    classes = (
        Classe.objects
        .filter(pk__in=classes_ids)
        .select_related('cycle')
        .order_by('cycle__ordre', 'nom')
    )

    # Regrouper par cycle
    cycles_dict: dict = {}
    for c in classes:
        label = c.cycle.nom if c.cycle else 'Autres'
        cycles_dict.setdefault(label, []).append(c)

    return render(request, 'documents/liste_classes_selector.html', {
        'annees': annees,
        'annee_selectionnee': annee_selectionnee,
        'cycles_dict': cycles_dict,
    })


@login_required
def liste_classe_pdf(request, classe_id):
    """Liste alphabétique d'une classe — prévisualisation HTML et export PDF."""
    etab = getattr(request.user, 'etablissement', None)
    classe = get_object_or_404(Classe.objects.select_related('cycle'), pk=classe_id)
    
    if etab and classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette classe n'appartient pas à votre établissement.")
        return redirect('documents:document_list')

    # Année : priorité au paramètre GET, sinon année courante
    annee_id = request.GET.get('annee_id')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee = AnneeScolaire.objects.filter(est_courante=True).first()

    inscriptions = (
        Inscription.objects
        .filter(classe=classe, annee_scolaire=annee)
        .select_related('eleve', 'statut_eleve')
        .order_by('eleve__nom', 'eleve__prenom')
    )

    # Évaluer le queryset une seule fois pour les calculs
    inscriptions_list = list(inscriptions)

    nb_total   = len(inscriptions_list)
    nb_garcons = sum(1 for i in inscriptions_list if i.eleve.genre == 'M')
    nb_filles  = sum(1 for i in inscriptions_list if i.eleve.genre == 'F')

    # Répartition des âges par genre
    import datetime as _dt
    today = _dt.date.today()

    AGE_BRACKETS = [
        ( 0,  5, "≤ 5 ans"),
        ( 6,  8, "6 – 8 ans"),
        ( 9, 11, "9 – 11 ans"),
        (12, 14, "12 – 14 ans"),
        (15, 17, "15 – 17 ans"),
        (18, 20, "18 – 20 ans"),
        (21, 999, "> 20 ans"),
    ]

    n = len(AGE_BRACKETS)
    cg = [0] * n   # garçons par tranche (indexé comme AGE_BRACKETS)
    cf = [0] * n   # filles  par tranche
    nb_sd_g = 0
    nb_sd_f = 0

    for ins in inscriptions_list:
        dn = ins.eleve.date_naissance
        genre = ins.eleve.genre
        if not dn:
            if genre == 'M':
                nb_sd_g = nb_sd_g + 1
            else:
                nb_sd_f = nb_sd_f + 1
            continue
        age = (_dt.date.today() - dn).days // 365
        for idx, (min_a, max_a, _lbl) in enumerate(AGE_BRACKETS):
            if min_a <= age <= max_a:
                if genre == 'M':
                    cg[idx] = cg[idx] + 1
                else:
                    cf[idx] = cf[idx] + 1
                break

    repartition_ages = []
    for idx, (_min, _max, lbl) in enumerate(AGE_BRACKETS):
        g = int(cg[idx])
        f = int(cf[idx])
        if g + f > 0:
            repartition_ages.append({'label': lbl, 'garcons': g, 'filles': f, 'total': g + f})
    nb_sd = nb_sd_g + nb_sd_f
    if nb_sd:
        repartition_ages.append({
            'label': 'Sans date de naissance',
            'garcons': nb_sd_g,
            'filles': nb_sd_f,
            'total': nb_sd,
        })

    # Signataire — cherche par cycle + code TypeDocument contenant "liste" et "classe"
    # Couvre : 'Liste_classe_sec', 'Liste-classe', 'liste_classe_prim', etc.
    signataire_membre = None
    signataire_fonction = None
    sig = (
        SignataireDocument.objects
        .filter(
            cycle=classe.cycle,
            actif=True,
            type_document__actif=True,
        )
        .filter(
            Q(type_document__code__icontains='liste')
            & (
                Q(type_document__code__icontains='classe')
                | Q(type_document__code__icontains='eleve')
                | Q(type_document__code__icontains='alpha')
            )
        )
        .order_by('-updated_at')
        .first()
    )
    # Repli : n'importe quel signataire actif pour ce cycle
    if not sig:
        sig = SignataireDocument.objects.filter(
            cycle=classe.cycle, actif=True
        ).order_by('-updated_at').first()
    if sig:
        signataire_membre = sig.get_membre_personnel()
        signataire_fonction = sig.fonction or sig.titre or 'Le Directeur'

    etab = annee.etablissement if annee else None
    etab_context = get_etablissement_context(etab, request) if etab else {}

    context = {
        'classe': classe,
        'inscriptions': inscriptions_list,
        'annee_scolaire': annee,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'nb_total': nb_total,
        'nb_filles': nb_filles,
        'nb_garcons': nb_garcons,
        'repartition_ages': repartition_ages,
        'signataire_membre': signataire_membre,
        'signataire_fonction': signataire_fonction,
    }
    context = inject_licence_filigrane_context(context, request.user, etab)

    if request.GET.get('format') == 'pdf':
        try:
            from core.pdf import HTML
            html_content = render(request, 'documents/pdf/liste_classe.html', context)
            pdf = HTML(string=html_content.content.decode()).write_pdf()

            # Trace : TypeDocument le plus proche du concept "liste de classe"
            trace_type_doc = TypeDocument.objects.filter(
                Q(code__icontains='liste')
                & (Q(code__icontains='classe') | Q(code__icontains='eleve') | Q(code__icontains='alpha')),
                actif=True,
            ).first()
            if annee:
                Document.objects.create(
                    type_document=trace_type_doc,
                    annee_scolaire=annee,
                    classe=classe,
                    genere_par=request.user,
                )

            nom_fichier = f"liste_{classe.nom.replace(' ', '_')}.pdf"
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
            return response
        except ImportError:
            messages.error(request, "WeasyPrint n'est pas installé.")

    return render(request, 'documents/liste_classe_preview.html', context)


@login_required
def liste_personnel_selector(request):
    """Sélection du cycle pour la liste du personnel avec année scolaire."""
    from personnel.models import MembrePersonnel, InscriptionPersonnel
    from parametres.models import AnneeScolaire

    etab = getattr(request.user, 'etablissement', None)

    # Gestion de l'année scolaire
    annee_id = request.GET.get('annee_id')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id, etablissement=etab)
    else:
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()

    # Annees scolaires disponibles pour le select
    annees = []
    if etab:
        annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')

    cycles = (
        Cycle.objects
        .filter(etablissement=etab)
        .order_by('ordre', 'nom')
    ) if etab else Cycle.objects.none()

    cycles_ids = []
    if annee:
        cycles_ids = list(
            InscriptionPersonnel.objects
            .filter(annee_scolaire=annee, est_actif=True)
            .values_list('cycle__id', flat=True)
            .distinct()
        )
    cycles_avec_inscriptions = set(cycles_ids)

    return render(request, 'documents/liste_personnel_selector.html', {
        'cycles': cycles,
        'annee_selectionnee': annee,
        'annees': annees,
        'cycles_avec_inscriptions': cycles_avec_inscriptions,
    })


@login_required
def liste_personnel_pdf(request, cycle_id):
    """Liste alphabétique du personnel d'un cycle et année scolaire — prévisualisation HTML et export PDF."""
    from personnel.models import InscriptionPersonnel

    etab = getattr(request.user, 'etablissement', None)
    cycle = get_object_or_404(Cycle, pk=cycle_id)
    
    if etab and cycle.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Ce cycle n'appartient pas à votre établissement.")
        return redirect('documents:document_list')

    annee_id = request.GET.get('annee_id')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()

    inscriptions = (
        InscriptionPersonnel.objects
        .filter(cycle=cycle, annee_scolaire=annee, est_actif=True)
        .select_related('personnel', 'poste')
        .order_by('personnel__nom', 'personnel__prenom')
    )

    CAT_LABELS = {
        'DIRECTION': 'Direction',
        'ENSEIGNEMENT': 'Enseignement',
        'ADMINISTRATION': 'Administration',
        'VIE_SCOLAIRE': 'Vie Scolaire',
        'TECHNIQUE': 'Personnel Technique',
    }

    membres_list = []
    for ins in inscriptions:
        poste = ins.poste
        cat_val = getattr(poste, 'categorie', '') if poste else ''
        cat_label = CAT_LABELS.get(cat_val, cat_val or 'Autre')
        membres_list.append({
            'personnel': ins.personnel,
            'poste': poste,
            'categorie': cat_label,
        })

    nb_total  = len(membres_list)
    nb_hommes = sum(1 for m in membres_list if m['personnel'].genre == 'M')
    nb_femmes = sum(1 for m in membres_list if m['personnel'].genre == 'F')

    # ── Répartition par catégorie × genre ───────────────────────────────
    from collections import defaultdict
    repartition_cat = defaultdict(lambda: {'H': 0, 'F': 0, 'total': 0})
    for m in membres_list:
        cat = m['categorie'] or 'Autre'
        genre = m['personnel'].genre
        repartition_cat[cat]['total'] += 1
        if genre == 'M':
            repartition_cat[cat]['H'] += 1
        else:
            repartition_cat[cat]['F'] += 1

    repartition_cycles_data = []
    for cat, vals in sorted(repartition_cat.items()):
        if vals['total'] > 0:
            repartition_cycles_data.append({
                'categorie': cat,
                'hommes': vals['H'],
                'femmes': vals['F'],
                'total': vals['total'],
            })

    # Signataire — cherche par cycle + code TypeDocument contenant "liste" et "personnel"
    signataire_membre = None
    signataire_fonction = None
    sig = (
        SignataireDocument.objects
        .filter(
            cycle=cycle,
            actif=True,
            type_document__actif=True,
        )
        .filter(
            Q(type_document__code__icontains='liste')
            & Q(type_document__code__icontains='personnel')
        )
        .order_by('-updated_at')
        .first()
    )
    if not sig:
        sig = SignataireDocument.objects.filter(
            cycle=cycle, actif=True
        ).order_by('-updated_at').first()
    if sig:
        signataire_membre = sig.get_membre_personnel()
        signataire_fonction = sig.fonction or sig.titre or 'Le Directeur'

    etab = annee.etablissement if annee else None
    etab_context = get_etablissement_context(etab, request) if etab else {}

    context = {
        'cycle': cycle,
        'membres': membres_list,
        'annee_scolaire': annee,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'nb_total': nb_total,
        'nb_hommes': nb_hommes,
        'nb_femmes': nb_femmes,
        'repartition_cycles_data': repartition_cycles_data,
        'signataire_membre': signataire_membre,
        'signataire_fonction': signataire_fonction,
    }
    context = inject_licence_filigrane_context(context, request.user, etab)

    if request.GET.get('format') == 'pdf':
        try:
            from core.pdf import HTML
            html_content = render(request, 'documents/pdf/liste_personnel.html', context)
            pdf = HTML(string=html_content.content.decode()).write_pdf()

            nom_fichier = f"personnel_{cycle.nom.replace(' ', '_')}.pdf"
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
            return response
        except ImportError:
            messages.error(request, "WeasyPrint n'est pas installé.")

    return render(request, 'documents/liste_personnel_preview.html', context)


# ─── Convocations ─────────────────────────────────────────────────────────────

TYPES_CONVOCATION = [
    ('CONSEIL',   'Conseil de classe'),
    ('SANCTION',  'Sanction disciplinaire'),
    ('REUNION',   'Réunion parents-professeurs'),
    ('AUTRE',     'Autre'),
]


@login_required
def convocation_form(request):
    """
    Formulaire de convocation : sélection classe + élève(s), type,
    date / heure / lieu / objet / corps.
    """
    etab = getattr(request.user, 'etablissement', None)

    annees = AnneeScolaire.objects.filter(est_courante=True)
    if etab:
        annees = annees.filter(etablissement=etab)
    annee_courante = annees.first()

    classes = (
        Classe.objects.filter(etablissement=etab, actif=True)
        .select_related('cycle').order_by('cycle__ordre', 'nom')
    ) if etab else []

    classe_id    = request.GET.get('classe') or request.POST.get('classe')
    inscriptions = []
    if classe_id and annee_courante:
        inscriptions = (
            Inscription.objects
            .filter(classe_id=classe_id, annee_scolaire=annee_courante)
            .exclude(statut='ABANDON')
            .select_related('eleve')
            .order_by('eleve__nom')
        )

    if request.method == 'POST':
        inscription_ids = request.POST.getlist('inscriptions')
        type_conv  = request.POST.get('type_convocation', 'AUTRE')
        date_conv  = request.POST.get('date_convocation', '')
        heure_conv = request.POST.get('heure_convocation', '')
        lieu_conv  = request.POST.get('lieu', '').strip()
        objet_conv = request.POST.get('objet', '').strip()
        corps_conv = request.POST.get('corps', '').strip()
        format_out = request.POST.get('format', 'apercu')

        if not inscription_ids:
            messages.error(request, "Sélectionnez au moins un élève.")
        else:
            inscriptions_sel = (
                Inscription.objects
                .filter(pk__in=inscription_ids)
                .select_related('eleve', 'classe', 'annee_scolaire')
            )
            type_label = dict(TYPES_CONVOCATION).get(type_conv, type_conv)
            type_doc, _ = TypeDocument.objects.get_or_create(
                code='CONVOCATION',
                defaults={'libelle': 'Convocation', 'categorie': 'ADMINISTRATIF', 'actif': True}
            )

            if format_out == 'pdf':
                from core.pdf import HTML
                from django.template.loader import render_to_string
                from django.core.files.base import ContentFile

                base_url = request.build_absolute_uri('/')
                pages = []
                docs_created = []

                for inscr in inscriptions_sel:
                    etab_i   = inscr.annee_scolaire.etablissement
                    etab_ctx = get_etablissement_context(etab_i, request)
                    sig = SignataireDocument.objects.get_signataire(
                        cycle=inscr.classe.cycle,
                        type_document=type_doc,
                        annee_scolaire=inscr.annee_scolaire,
                    )
                    sig_membre = sig.get_membre_personnel() if sig else None
                    doc = Document.objects.create(
                        type_document=type_doc,
                        annee_scolaire=inscr.annee_scolaire,
                        inscription=inscr,
                        genere_par=request.user,
                        signataire_nom=f"{sig_membre.nom} {sig_membre.prenom}" if sig_membre else '',
                    )
                    docs_created.append(doc)
                    conv_ctx = {
                        'inscription': inscr,
                        'eleve': inscr.eleve,
                        'classe': inscr.classe,
                        'annee_scolaire': inscr.annee_scolaire,
                        'type_label': type_label,
                        'date_conv': date_conv,
                        'heure_conv': heure_conv,
                        'lieu': lieu_conv,
                        'objet': objet_conv,
                        'corps': corps_conv,
                        'signataire': sig,
                        'sig_membre': sig_membre,
                        'identite': etab_ctx.get('identite'),
                        'logo_url': etab_ctx.get('logo_url'),
                        'etablissement': etab_i,
                        'document': doc,
                    }
                    conv_ctx = inject_licence_filigrane_context(conv_ctx, request.user, etab_i)
                    pages.append(render_to_string(
                        'documents/pdf/convocation.html',
                        conv_ctx,
                        request=request,
                    ))

                pdf = HTML(string=''.join(pages), base_url=base_url).write_pdf()

                # Archive le PDF sur chaque document créé
                for doc in docs_created:
                    nom_el = doc.inscription.eleve.nom.replace(' ', '_')
                    doc.fichier.save(
                        f"convocation_{nom_el}_{doc.numero_document}.pdf",
                        ContentFile(pdf), save=True
                    )

                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = 'inline; filename="convocations.pdf"'
                return response

            return render(request, 'documents/convocation_preview.html', {
                'inscriptions_sel': inscriptions_sel,
                'type_label': type_label,
                'type_conv': type_conv,
                'date_conv': date_conv,
                'heure_conv': heure_conv,
                'lieu': lieu_conv,
                'objet': objet_conv,
                'corps': corps_conv,
                'classes': classes,
                'types_convocation': TYPES_CONVOCATION,
                'annee_courante': annee_courante,
            })

    return render(request, 'documents/convocation_form.html', {
        'classes': classes,
        'inscriptions': inscriptions,
        'classe_id': classe_id or '',
        'types_convocation': TYPES_CONVOCATION,
        'annee_courante': annee_courante,
    })


# ─── Circulaires ──────────────────────────────────────────────────────────────

@login_required
def circulaire_form(request):
    """
    Formulaire de circulaire : titre, objet, corps, destinataires (classes), date.
    """
    etab = getattr(request.user, 'etablissement', None)

    annees = AnneeScolaire.objects.filter(est_courante=True)
    if etab:
        annees = annees.filter(etablissement=etab)
    annee_courante = annees.first()

    classes = (
        Classe.objects.filter(etablissement=etab, actif=True)
        .select_related('cycle').order_by('cycle__ordre', 'nom')
    ) if etab else []

    if request.method == 'POST':
        titre      = request.POST.get('titre', '').strip()
        objet      = request.POST.get('objet', '').strip()
        corps      = request.POST.get('corps', '').strip()
        date_circ  = request.POST.get('date_circulaire', '')
        classe_ids = request.POST.getlist('classes')
        format_out = request.POST.get('format', 'apercu')

        if not titre:
            messages.error(request, "Le titre est obligatoire.")
        else:
            classes_sel = (
                Classe.objects.filter(pk__in=classe_ids).select_related('cycle')
                if classe_ids else []
            )
            type_doc, _ = TypeDocument.objects.get_or_create(
                code='CIRCULAIRE',
                defaults={'libelle': 'Circulaire', 'categorie': 'ADMINISTRATIF', 'actif': True}
            )
            etab_ctx = get_etablissement_context(etab, request) if etab else {}
            sig = None
            if etab:
                sig = (
                    SignataireDocument.objects
                    .filter(actif=True, type_document=type_doc).first()
                    or SignataireDocument.objects.filter(actif=True).first()
                )
            sig_membre = sig.get_membre_personnel() if sig else None

            if format_out == 'pdf':
                from core.pdf import HTML
                from django.template.loader import render_to_string

                from django.core.files.base import ContentFile

                from datetime import date as _date
                import uuid as _uuid
                doc = None
                if annee_courante:
                    doc = Document.objects.create(
                        type_document=type_doc,
                        annee_scolaire=annee_courante,
                        genere_par=request.user,
                        signataire_nom=f"{sig_membre.nom} {sig_membre.prenom}" if sig_membre else '',
                        observations=titre,
                    )
                # Numéro toujours visible même sans annee_courante
                ref_circ = (
                    doc.numero_document if (doc and doc.numero_document)
                    else f"CIRC-{_date.today().year}-{_uuid.uuid4().hex[:6].upper()}"
                )
                circ_ctx = {
                    'titre': titre,
                    'objet': objet,
                    'corps': corps,
                    'date_circulaire': date_circ,
                    'classes_sel': classes_sel,
                    'signataire': sig,
                    'sig_membre': sig_membre,
                    'identite': etab_ctx.get('identite'),
                    'logo_url': etab_ctx.get('logo_url'),
                    'etablissement': etab,
                    'annee_scolaire': annee_courante,
                    'document': doc,
                    'ref_circ': ref_circ,
                }
                circ_ctx = inject_licence_filigrane_context(circ_ctx, request.user, etab)
                html_string = render_to_string(
                    'documents/pdf/circulaire.html',
                    circ_ctx,
                    request=request,
                )
                pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
                nom = titre.replace(' ', '_')[:40]
                if doc:
                    doc.fichier.save(
                        f"circulaire_{nom}_{doc.numero_document}.pdf",
                        ContentFile(pdf), save=True
                    )
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="circulaire_{nom}.pdf"'
                return response

            return render(request, 'documents/circulaire_preview.html', {
                'titre': titre,
                'objet': objet,
                'corps': corps,
                'date_circulaire': date_circ,
                'classes_sel': classes_sel,
                'classes': classes,
                'annee_courante': annee_courante,
                'signataire': sig,
                'sig_membre': sig_membre,
                'identite': etab_ctx.get('identite'),
            })

    return render(request, 'documents/circulaire_form.html', {
        'classes': classes,
        'annee_courante': annee_courante,
    })


# ─── Attestation de non-redevabilité ─────────────────────────────────────────

@login_required
def attestation_non_redevabilite(request, inscription_id):
    """
    Attestation certifiant qu'un élève a soldé la totalité de ses frais scolaires.
    """
    # Vérification du rôle
    if not _can_generate_document(request.user):
        messages.error(request, "Vous n'êtes pas autorisé à générer des documents officiels.")
        return redirect('documents:document_list')
    
    # Vérification que l'inscription appartient à l'établissement de l'utilisateur
    etab_user = request.user.etablissement
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe__cycle', 'annee_scolaire'),
        pk=inscription_id,
    )
    
    # IDOR - Vérification que l'élève appartient à l'établissement de l'utilisateur
    if etab_user and inscription.annee_scolaire.etablissement != etab_user:
        messages.error(request, "Vous n'avez pas accès à ce document.")
        return redirect('documents:document_list')

    from finances.views import _calcul_situation_financiere
    situation = _calcul_situation_financiere(inscription)
    reste = situation.get('reste_a_payer', 0)

    etab     = inscription.annee_scolaire.etablissement
    annee    = inscription.annee_scolaire
    etab_ctx = get_etablissement_context(etab, request)

    type_doc, _ = TypeDocument.objects.get_or_create(
        code='ATTESTATION',
        defaults={'libelle': 'Attestation de Non-Redevabilité', 'categorie': 'FINANCE', 'actif': True}
    )
    sig = SignataireDocument.objects.get_signataire(
        cycle=inscription.classe.cycle,
        type_document=type_doc,
        annee_scolaire=annee,
    )
    sig_membre = sig.get_membre_personnel() if sig else None

    context = {
        'inscription': inscription,
        'eleve': inscription.eleve,
        'classe': inscription.classe,
        'annee_scolaire': annee,
        'situation': situation,
        'reste': reste,
        'solde': reste == 0,
        'identite': etab_ctx.get('identite'),
        'logo_url': etab_ctx.get('logo_url'),
        'etablissement': etab,
        'signataire': sig,
        'sig_membre': sig_membre,
        'type_doc': type_doc,
    }

    doc = Document(
        type_document=type_doc,
        annee_scolaire=annee,
        inscription=inscription,
    )
    doc._generate_numero()
    context['document'] = doc

    if request.GET.get('format') == 'pdf':
        from core.pdf import HTML
        from django.template.loader import render_to_string

        from django.core.files.base import ContentFile

        doc = Document(
            type_document=type_doc,
            annee_scolaire=annee,
            inscription=inscription,
            genere_par=request.user,
            signataire_nom=f"{sig_membre.nom} {sig_membre.prenom}" if sig_membre else '',
        )
        doc._generate_numero()
        doc.save()
        context['document'] = doc

        context = inject_licence_filigrane_context(context, request.user, etab)
        html_string = render_to_string(
            'documents/pdf/attestation_non_redevabilite.html',
            context, request=request,
        )
        pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        nom = inscription.eleve.nom.replace(' ', '_')
        doc.fichier.save(
            f"attestation_{nom}_{doc.numero_document}.pdf",
            ContentFile(pdf), save=True
        )
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="attestation_{nom}.pdf"'
        return response

    return render(request, 'documents/attestation_preview.html', context)
