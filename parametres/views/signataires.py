"""Signataires des documents officiels (par cycle et catégorie)."""
import logging

from django.db import DatabaseError
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from ..forms import (
    SignataireForm,
)
from ..views.commun import _get_etab
from ..models import (
    Cycle, AnneeScolaire, TypeDocument, SignataireDocument, CoSignataire,
    TitreFonction, TitreHonorifiquePersonnel,
)
from personnel.models import MembrePersonnel

logger = logging.getLogger(__name__)


# ─── SIGNATAIRES ─────────────────────────────────────────────────────

@login_required
def signataire_config(request):
    """
    Interface tabulaire : onglet par cycle × cartes par catégorie de documents.
    GET  : affiche la grille de configuration.
    POST : enregistre le signataire pour un cycle × catégorie × année.
    """
    etab = _get_etab(request)
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_id = request.GET.get('annee') or request.POST.get('annee_id')
    annee = AnneeScolaire.objects.filter(id=annee_id, etablissement=etab).first() \
            if annee_id else AnneeScolaire.objects.get_annee_courante(etablissement=etab)

    if request.method == 'POST':
        annee_id = request.POST.get('annee_id')
        annee = AnneeScolaire.objects.filter(id=annee_id, etablissement=etab).first() \
            if annee_id else AnneeScolaire.objects.get_annee_courante(etablissement=etab)
        cycle_id = request.POST.get('cycle_id')
        categorie = request.POST.get('categorie')
        retour = f"{request.path}?annee={annee.id if annee else ''}"

        form = SignataireForm(request.POST, request.FILES, etablissement=etab)
        if form.is_valid() and cycle_id and categorie and annee:
            membre = form.cleaned_data['membre_personnel']
            fonction = form.cleaned_data['fonction'] or 'Le Directeur'
            titre_h = form.cleaned_data['titre_honorifique']
            try:
                cycle = Cycle.objects.get(id=cycle_id, etablissement=etab)
                retour += f"&cycle={cycle.id}"  # rouvre l'onglet du cycle enregistré
                types = TypeDocument.objects.filter(
                    Q(cycle=cycle) | Q(cycle__isnull=True),
                    categorie=categorie,
                    actif=True,
                )
                for td in types:
                    SignataireDocument.objects.update_or_create(
                        cycle=cycle,
                        type_document=td,
                        annee_scolaire=annee,
                        defaults={
                            'membre_personnel_id': membre.id,
                            'fonction': fonction,
                            'titre_honorifique': titre_h,
                            'titres_honorifiques': [titre_h] if titre_h else [],
                            'actif': True,
                        }
                    )
                form.appliquer_signature(membre)
                libelle_cat = TypeDocument.CategorieChoices(categorie).label
                messages.success(request, f"Signataire enregistré pour {cycle.nom} · {libelle_cat}.")
            except (DatabaseError, ValidationError, ValueError, OSError) as e:
                logger.exception("Enregistrement du signataire impossible")
                messages.error(request, f"Erreur : {e}")
        elif form.errors.get('signature'):
            messages.error(request, f"Signature scannée refusée : {' '.join(form.errors['signature'])}")
        else:
            details = ' '.join(f"{champ} : {' '.join(errs)}" for champ, errs in form.errors.items())
            messages.error(request, f"Signataire non enregistré. {details or 'Année scolaire, cycle ou catégorie manquant.'}")
        return redirect(retour)

    # ── Construction des données pour le template ──
    cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre')
    personnel = MembrePersonnel.objects.filter(etablissement=etab, is_active=True).order_by('nom', 'prenom')
    categories = TypeDocument.CategorieChoices.choices
    cycle_actif_id = request.GET.get('cycle', '')

    cycles_data = []
    for cycle in cycles:
        total_configured = 0
        total_docs = 0
        categories_data = []
        for cat_val, cat_label in categories:
            type_docs = list(TypeDocument.objects.filter(
                Q(cycle=cycle) | Q(cycle__isnull=True),
                categorie=cat_val,
                actif=True,
            ))
            if not type_docs:
                continue
            sigs = {}
            if annee:
                for td in type_docs:
                    sig = SignataireDocument.objects.filter(
                        cycle=cycle, type_document=td, annee_scolaire=annee, actif=True
                    ).first()
                    sigs[str(td.id)] = sig
            configured = sum(1 for s in sigs.values() if s)
            total_configured += configured
            total_docs += len(type_docs)

            # Signataire "représentatif" pour pré-remplir le formulaire
            sig_ref = next((s for s in sigs.values() if s), None)
            membre_ref = sig_ref.get_membre_personnel() if sig_ref else None
            categories_data.append({
                'value':      cat_val,
                'label':      cat_label,
                'type_docs':  type_docs,
                'configured': configured,
                'total':      len(type_docs),
                'sig_ref':    sig_ref,
                'signature':  membre_ref.signature if membre_ref and membre_ref.signature else None,
            })
        cycles_data.append({
            'cycle':             cycle,
            'categories':        categories_data,
            'total_configured':  total_configured,
            'total_docs':        total_docs,
            'actif':             str(cycle.id) == cycle_actif_id,
        })
    if cycles_data and not any(cd['actif'] for cd in cycles_data):
        cycles_data[0]['actif'] = True

    return render(request, 'parametres/signataire_config_tabs.html', {
        'annees':              annees,
        'annee':               annee,
        'cycles_data':         cycles_data,
        'personnel':           personnel,
        'fonctions':           TitreFonction.objects.filter(actif=True).order_by('nom'),
        'titres_honorifiques': TitreHonorifiquePersonnel.objects.filter(actif=True).order_by('nom'),
    })


@login_required
def signataires_list(request):
    etab = _get_etab(request)
    cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre')
    context = {
        'cycles': cycles,
        'active_cycle': cycles.first(),
    }
    return render(request, 'parametres/signataires_config.html', context)


@login_required
def signataires_list_detail(request, cycle_id):
    cycle = get_object_or_404(Cycle, id=cycle_id)
    etab = cycle.etablissement
    annee = AnneeScolaire.objects.get_annee_courante(etablissement=etab)

    if not annee:
        return HttpResponse(
            '<div class="p-12 text-center text-slate-500">'
            'Aucune année scolaire active trouvée.'
            '</div>',
            status=400
        )

    types_documents = TypeDocument.objects.filter(
        Q(cycle=cycle) | Q(cycle__isnull=True),
        actif=True,
    )
    signataires = {
        s.type_document_id: s
        for s in SignataireDocument.objects.filter(cycle=cycle, annee_scolaire=annee)
    }

    docs_config = [
        {'type': td, 'signataire': signataires.get(td.id)}
        for td in types_documents
    ]

    return render(request, 'parametres/partials/signataires_list_detail.html', {
        'cycle': cycle,
        'docs_config': docs_config,
    })


_TITRES_HONORIFIQUES_PREDEFINED = [
    "M. le Directeur",
    "Mme la Directrice",
    "M. le Proviseur",
    "Mme la Proviseure",
    "M. le Censeur",
    "Mme la Censeure",
    "M. le Sous-Directeur",
    "Mme la Sous-Directrice",
    "M. le Chef d'Établissement",
    "Mme la Chef d'Établissement",
    "Le Directeur",
    "La Directrice",
    "Le Proviseur",
    "Dr.",
    "Pr.",
    "M.",
    "Mme",
]


@login_required
def signataire_edit(request, cycle_id, document_type_id):
    cycle = get_object_or_404(Cycle, id=cycle_id)
    doc_type = get_object_or_404(TypeDocument, id=document_type_id)
    etab = cycle.etablissement
    annee = AnneeScolaire.objects.get_annee_courante(etablissement=etab)

    if not annee:
        return HttpResponse('Aucune année scolaire active trouvée.', status=400)

    signataire = SignataireDocument.objects.filter(
        cycle=cycle, type_document=doc_type, annee_scolaire=annee
    ).first()

    initial = {}
    if signataire:
        membre = signataire.get_membre_personnel()
        initial = {
            'membre_personnel': membre,
            'fonction': signataire.fonction,
            'titre_honorifique': signataire.titre_honorifique,
        }

    if request.method == 'POST':
        form = SignataireForm(request.POST, etablissement=etab)
        if form.is_valid():
            membre = form.cleaned_data['membre_personnel']
            fonction = form.cleaned_data['fonction']
            titre = form.cleaned_data['titre_honorifique']
            if signataire:
                signataire.set_membre_personnel(membre)
                signataire.fonction = fonction
                signataire.titre_honorifique = titre
                signataire.titres_honorifiques = [titre] if titre else []
                signataire.save()
            else:
                SignataireDocument.objects.create(
                    cycle=cycle,
                    type_document=doc_type,
                    annee_scolaire=annee,
                    membre_personnel_id=membre.id,
                    fonction=fonction,
                    titre_honorifique=titre,
                    titres_honorifiques=[titre] if titre else [],
                )
            return HttpResponse(status=204, headers={'HX-Trigger': 'signataireUpdated'})
    else:
        form = SignataireForm(initial=initial, etablissement=etab)

    return render(request, 'parametres/partials/signataire_form.html', {
        'cycle': cycle,
        'cycles': Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre'),
        'categories': TypeDocument.CategorieChoices.choices,
        'doc_type': doc_type,
        'signataire': signataire,
        'personnel': MembrePersonnel.objects.filter(etablissement=etab, is_active=True).order_by('nom', 'prenom'),
        'form': form,
        'fonctions': TitreFonction.objects.filter(actif=True).order_by('nom'),
        'titres_honorifiques': list(
            TitreHonorifiquePersonnel.objects.filter(actif=True).values_list('nom', flat=True)
        ),
    })


@login_required
def signataires_matricule(request):
    """
    Fenêtre unique de paramétrage des signataires : grille matricielle
    (lignes = types de documents par catégorie ; colonnes = cycles).
    Une seule page pour configurer tous les signataires de tous les cycles
    sur l'année scolaire choisie.
    """
    etab = _get_etab(request)
    if not etab:
        return render(request, 'parametres/signataires_matricule.html', {
            'error': "Votre compte n'est pas associé à un établissement.",
        })

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_id = request.GET.get('annee') or request.POST.get('annee_id')
    annee = AnneeScolaire.objects.filter(id=annee_id, etablissement=etab).first() \
        if annee_id else AnneeScolaire.objects.get_annee_courante(etablissement=etab)

    cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')
    personnel = MembrePersonnel.objects.filter(etablissement=etab, is_active=True).order_by('nom', 'prenom')

    # ── POST : gestion des signataires et cosignataires ──
    if request.method == 'POST' and annee:
        action = request.POST.get('action', 'save_signataire')
        cycle_id = request.POST.get('cycle_id')
        type_document_id = request.POST.get('type_document_id')
        try:
            cycle = Cycle.objects.get(id=cycle_id, etablissement=etab)
            td = TypeDocument.objects.get(id=type_document_id, actif=True)
        except (Cycle.DoesNotExist, TypeDocument.DoesNotExist) as e:
            messages.error(request, f"Erreur : {e}")
            return redirect(f"{request.path}?annee={annee.id if annee else ''}")

        # ── 1. Sauvegarde du signataire principal ──
        if action == 'save_signataire':
            membre_id = request.POST.get('membre_personnel') or None
            fonction = request.POST.get('fonction') or 'Le Directeur'
            titre = request.POST.get('titre_honorifique') or ''
            try:
                if not membre_id:
                    existant = SignataireDocument.objects.filter(
                        cycle=cycle, type_document=td, annee_scolaire=annee,
                        actif=True,
                    ).first()
                    if existant and existant.membre_personnel_id:
                        membre_id = existant.membre_personnel_id
                    if not membre_id:
                        messages.error(request, "Veuillez sélectionner un membre du personnel.")
                else:
                    SignataireDocument.objects.update_or_create(
                        cycle=cycle,
                        type_document=td,
                        annee_scolaire=annee,
                        defaults={
                            'membre_personnel_id': membre_id,
                            'fonction': fonction,
                            'titre_honorifique': titre,
                            'titres_honorifiques': [titre] if titre else [],
                            'actif': True,
                        },
                    )
                    messages.success(
                        request,
                        f"Signataire enregistré pour {cycle.nom} · {td.libelle}."
                    )
            except (DatabaseError, ValidationError) as e:
                logger.exception("Mise à jour du signataire matriciel impossible")
                messages.error(request, f"Erreur : {e}")

        # ── 2. Ajout d'un cosignataire ──
        elif action == 'add_cosignataire':
            try:
                sig, _ = SignataireDocument.objects.update_or_create(
                    cycle=cycle,
                    type_document=td,
                    annee_scolaire=annee,
                    defaults={
                        'membre_personnel_id': None,
                        'fonction': 'Le Directeur',
                        'titre_honorifique': '',
                        'titres_honorifiques': [],
                        'actif': True,
                    },
                )
                membre_id = request.POST.get('membre_personnel') or None
                fonction = request.POST.get('fonction') or ''
                try:
                    ordre = int(request.POST.get('ordre', 2) or 2)
                except ValueError:
                    ordre = 2
                titres = request.POST.getlist('titres_honorifiques') or []
                if not membre_id:
                    messages.error(request, "Veuillez sélectionner un membre du personnel.")
                else:
                    CoSignataire.objects.create(
                        signataire_principal=sig,
                        membre_personnel_id=membre_id,
                        fonction=fonction,
                        titres_honorifiques=titres,
                        ordre=ordre,
                        actif=True,
                    )
                    messages.success(request, "Co-signataire ajouté.")
            except (DatabaseError, ValidationError, ValueError) as e:
                logger.exception("Ajout du cosignataire impossible")
                messages.error(request, f"Erreur : {e}")

        # ── 3. Suppression d'un cosignataire ──
        elif action == 'delete_cosignataire':
            try:
                cs_id = request.POST.get('cosignataire_id')
                CoSignataire.objects.filter(id=cs_id, actif=True).update(actif=False)
                messages.success(request, "Co-signataire supprimé.")
            except (DatabaseError, ValidationError) as e:
                logger.exception("Suppression du cosignataire impossible")
                messages.error(request, f"Erreur : {e}")

        return redirect(f"{request.path}?annee={annee.id if annee else ''}")

    if not annee:
        return render(request, 'parametres/signataires_matricule.html', {
            'annees': annees,
            'annee': None,
            'error': "Aucune année scolaire trouvée.",
        })

    # ── Signataires existants pour l'année ──
    signataires = {
        (s.cycle_id, s.type_document_id): s
        for s in SignataireDocument.objects.filter(
            annee_scolaire=annee,
            cycle__in=cycles,
            actif=True,
        )
    }

    # ── Cosignataires par signataire principal ──
    cosignataires_par_sig = {}
    for sig in signataires.values():
        cosignataires_par_sig[sig.id] = [
            {
                'id': cs.id,
                'membre': cs.get_membre_personnel(),
                'fonction': cs.fonction,
                'titres_honorifiques': cs.titres_honorifiques or [],
                'ordre': cs.ordre,
            }
            for cs in sig.co_signataires.filter(actif=True).order_by('ordre')
        ]

    # ── Types de documents actifs, groupés par catégorie ──
    types_documents = TypeDocument.objects.filter(actif=True).order_by('categorie', 'libelle')
    categories = TypeDocument.CategorieChoices.choices

    # ── Matrice : une ligne par type de document, une cellule par cycle ──
    matrice = []
    cat_precedente = None
    for cat_val, cat_label in categories:
        types_cat = [td for td in types_documents if td.categorie == cat_val]
        if not types_cat:
            continue
        for td in types_cat:
            cellules = []
            for cycle in cycles:
                applicable = (td.cycle_id is None) or (td.cycle_id == cycle.id)
                sig = signataires.get((cycle.id, td.id)) if applicable else None
                membre = sig.get_membre_personnel() if sig else None
                cellules.append({
                    'cycle': cycle,
                    'applicable': applicable,
                    'signataire': sig,
                    'membre': membre,
                    'configuré': sig is not None,
                    'cosignataires': cosignataires_par_sig.get(sig.id, []) if sig else [],
                })
            matrice.append({
                'categorie': cat_val,
                'cat_label': cat_label,
                'type': td,
                'is_first_in_category': (cat_val != cat_precedente),
                'type_cat_count': len(types_cat),
                'cellules': cellules,
            })
            cat_precedente = cat_val

    return render(request, 'parametres/signataires_matricule.html', {
        'annees': annees,
        'annee': annee,
        'matrice': matrice,
        'categories': categories,
        'cycles': cycles,
        'personnel': personnel,
        'fonctions': TitreFonction.objects.filter(actif=True).order_by('nom'),
        'titres_honorifiques': TitreHonorifiquePersonnel.objects.filter(actif=True).order_by('nom'),
    })


@login_required
def signataire_formulaire(request):
    """
    Page standalone pour créer/modifier un signataire avec 5 sélecteurs.
    Accessible directement depuis le menu latéral.
    """
    etab = _get_etab(request)
    if not etab:
        return render(request, 'parametres/signataire_formulaire.html', {
            'error': "Votre compte n'est pas associé à un établissement.",
        })

    annee_courante = AnneeScolaire.objects.get_annee_courante(etablissement=etab)
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    cycles = Cycle.objects.filter(etablissement=etab).order_by('ordre', 'nom')
    personnel = MembrePersonnel.objects.filter(etablissement=etab).order_by('nom', 'prenom')

    titres_fonctions = TitreFonction.objects.filter(actif=True).order_by('nom')
    titres_honorifiques = list(
        TitreHonorifiquePersonnel.objects.filter(actif=True).values_list('nom', flat=True)
    )

    annee = annee_courante
    selected_annee_id = str(annee.id) if annee else ''

    context = {
        'annees': annees,
        'cycles': cycles,
        'categories': TypeDocument.CategorieChoices.choices,
        'personnel': personnel,
        'fonctions': titres_fonctions,
        'titres_honorifiques': titres_honorifiques,
        'annee': annee,
        'selected_annee_id': selected_annee_id,
        'selected_cycle_id': '',
        'selected_categorie': '',
        'selected_fonction': '',
        'selected_membre_id': '',
        'selected_titre': '',
    }

    if request.method == 'POST':
        annee_id = request.POST.get('annee_id')
        cycle_id = request.POST.get('cycle_id')
        categorie = request.POST.get('categorie')

        if annee_id:
            try:
                annee = AnneeScolaire.objects.get(id=annee_id, etablissement=etab)
                selected_annee_id = str(annee.id)
            except AnneeScolaire.DoesNotExist:
                annee = annee_courante
                selected_annee_id = str(annee.id) if annee else ''

        form = SignataireForm(request.POST, etablissement=etab)
        context.update({
            'form': form,
            'annee': annee,
            'selected_annee_id': selected_annee_id,
            'selected_cycle_id': cycle_id or '',
            'selected_categorie': categorie or '',
        })

        if not form.is_valid() or not all([cycle_id, categorie, annee]):
            if not all([cycle_id, categorie]):
                context['error'] = "Le cycle et la catégorie sont obligatoires."
            elif not annee:
                context['error'] = "Aucune année scolaire active trouvée."
            return render(request, 'parametres/signataire_formulaire.html', context)

        membre = form.cleaned_data['membre_personnel']
        fonction = form.cleaned_data['fonction']
        titre = form.cleaned_data['titre_honorifique']

        try:
            cycles_cibles = (
                list(Cycle.objects.filter(etablissement=etab))
                if cycle_id == 'all'
                else [Cycle.objects.get(id=cycle_id, etablissement=etab)]
            )
            results = []
            for cycle in cycles_cibles:
                types_docs = TypeDocument.objects.filter(
                    actif=True, categorie=categorie
                ).filter(Q(cycle=cycle) | Q(cycle__isnull=True))
                for td in types_docs:
                    _, created = SignataireDocument.objects.update_or_create(
                        cycle=cycle,
                        type_document=td,
                        annee_scolaire=annee,
                        defaults={
                            'membre_personnel_id': str(membre.id),
                            'fonction': fonction,
                            'titre_honorifique': titre,
                            'titres_honorifiques': [titre] if titre else [],
                            'actif': True,
                        }
                    )
                    results.append(created)
            created_count = sum(1 for c in results if c)
            updated_count = len(results) - created_count
            messages.success(
                request,
                f"{created_count} signataire(s) créé(s), {updated_count} mis à jour."
            )
            return redirect('parametres:signataires_list')
        except (DatabaseError, ValidationError, ValueError) as e:
            logger.exception("Enregistrement des signataires impossible")
            context['error'] = f"Erreur : {str(e)}"
    else:
        context['form'] = SignataireForm(etablissement=etab)

    return render(request, 'parametres/signataire_formulaire.html', context)
