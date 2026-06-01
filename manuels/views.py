from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from finances.models import Paiement
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe, RubriquePaiement

from .models import AttributionManuel, EtatManuel, ExemplaireManuel, ManuelScolaire


# ── Helpers ────────────────────────────────────────────────────────────────

def _etab(request):
    return request.user.etablissement


def _annee_courante(etab):
    return AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()


def _get_annees(etab):
    return AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle')


# ── Catalogue ──────────────────────────────────────────────────────────────

@login_required
def catalogue(request):
    etab = _etab(request)
    cycle_filter = request.GET.get('cycle', '')
    qs = ManuelScolaire.objects.filter(etablissement=etab, actif=True).select_related('matiere', 'classe')
    if cycle_filter:
        qs = qs.filter(cycle=cycle_filter)
    from core.models import CycleChoices
    return render(request, 'manuels/catalogue.html', {
        'manuels': qs,
        'cycles': CycleChoices.choices,
        'cycle_sel': cycle_filter,
    })


@login_required
def manuel_form(request, pk=None):
    etab = _etab(request)
    instance = get_object_or_404(ManuelScolaire, pk=pk, etablissement=etab) if pk else None
    from core.models import CycleChoices
    from pedagogie.models import Matiere
    matieres = Matiere.objects.all().order_by('code')
    classes = Classe.objects.filter(etablissement=etab).order_by('nom')
    error = None

    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        auteur = request.POST.get('auteur', '').strip()
        editeur = request.POST.get('editeur', '').strip()
        isbn = request.POST.get('isbn', '').strip()
        cycle = request.POST.get('cycle', '')
        classe_id = request.POST.get('classe') or None
        matiere_id = request.POST.get('matiere') or None
        annee_ed = request.POST.get('annee_edition', '').strip() or None
        prix_str = request.POST.get('prix_remplacement', '0').strip()

        if not titre:
            error = "Le titre est obligatoire."
        if not error:
            try:
                prix = Decimal(prix_str.replace(' ', '').replace(',', '.'))
            except (InvalidOperation, ValueError):
                prix = Decimal('0')
            kwargs = dict(
                titre=titre, auteur=auteur, editeur=editeur, isbn=isbn,
                cycle=cycle,
                classe_id=classe_id,
                matiere_id=matiere_id,
                annee_edition=int(annee_ed) if annee_ed else None,
                prix_remplacement=prix,
            )
            if instance:
                for k, v in kwargs.items():
                    setattr(instance, k, v)
                instance.save()
                messages.success(request, "Manuel mis à jour.")
            else:
                ManuelScolaire.objects.create(etablissement=etab, **kwargs)
                messages.success(request, "Manuel ajouté au catalogue.")
            return redirect('manuels:catalogue')

    return render(request, 'manuels/manuel_form.html', {
        'instance': instance,
        'cycles': CycleChoices.choices,
        'matieres': matieres,
        'classes': classes,
        'error': error,
    })


@login_required
def manuel_detail(request, pk):
    etab = _etab(request)
    manuel = get_object_or_404(ManuelScolaire, pk=pk, etablissement=etab)
    exemplaires = manuel.exemplaires.filter(actif=True).prefetch_related('attributions')
    return render(request, 'manuels/manuel_detail.html', {
        'manuel': manuel,
        'exemplaires': exemplaires,
        'etats': EtatManuel.choices,
    })


@login_required
@require_POST
def manuel_delete(request, pk):
    etab = _etab(request)
    manuel = get_object_or_404(ManuelScolaire, pk=pk, etablissement=etab)
    if manuel.exemplaires.filter(actif=True).exists():
        messages.error(request, "Impossible de supprimer un manuel ayant des exemplaires actifs.")
        return redirect('manuels:manuel_detail', pk=pk)
    manuel.actif = False
    manuel.save()
    messages.success(request, "Manuel retiré du catalogue.")
    return redirect('manuels:catalogue')


# ── Exemplaires ────────────────────────────────────────────────────────────

@login_required
def exemplaire_form(request, manuel_pk, pk=None):
    etab = _etab(request)
    manuel = get_object_or_404(ManuelScolaire, pk=manuel_pk, etablissement=etab)
    instance = get_object_or_404(ExemplaireManuel, pk=pk, manuel=manuel) if pk else None
    if request.method == 'POST':
        etat = request.POST.get('etat', EtatManuel.NEUF)
        annee_acq = request.POST.get('annee_acquisition', '').strip() or None
        if instance:
            instance.etat = etat
            instance.annee_acquisition = int(annee_acq) if annee_acq else None
            instance.save()
            messages.success(request, f"Exemplaire {instance.code_exemplaire} mis à jour.")
        else:
            nombre = int(request.POST.get('nombre', 1))
            codes = []
            for _ in range(nombre):
                ex = ExemplaireManuel.objects.create(
                    manuel=manuel,
                    etat=etat,
                    annee_acquisition=int(annee_acq) if annee_acq else None,
                )
                codes.append(ex.code_exemplaire)
            messages.success(request, f"{nombre} exemplaire(s) créé(s) : {', '.join(codes)}.")
        return redirect('manuels:manuel_detail', pk=manuel_pk)

    return render(request, 'manuels/exemplaire_form.html', {
        'manuel': manuel,
        'instance': instance,
        'etats': EtatManuel.choices,
        'today_year': date.today().year,
    })


@login_required
@require_POST
def exemplaire_delete(request, manuel_pk, pk):
    etab = _etab(request)
    manuel = get_object_or_404(ManuelScolaire, pk=manuel_pk, etablissement=etab)
    ex = get_object_or_404(ExemplaireManuel, pk=pk, manuel=manuel)
    if ex.attributions.filter(date_retour__isnull=True).exists():
        messages.error(request, "Cet exemplaire est actuellement attribué à un élève.")
        return redirect('manuels:manuel_detail', pk=manuel_pk)
    ex.actif = False
    ex.save()
    messages.success(request, f"Exemplaire {ex.code_exemplaire} désactivé.")
    return redirect('manuels:manuel_detail', pk=manuel_pk)


# ── Attributions ───────────────────────────────────────────────────────────

@login_required
def attributions_list(request):
    etab = _etab(request)
    annee_courante = _annee_courante(etab)
    annees = _get_annees(etab)
    annee_id = request.GET.get('annee')
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    qs = AttributionManuel.objects.filter(
        exemplaire__manuel__etablissement=etab,
        date_retour__isnull=True,
    ).select_related(
        'exemplaire__manuel', 'inscription__eleve', 'inscription__classe'
    ).order_by('inscription__eleve__nom')

    if annee_sel:
        qs = qs.filter(inscription__annee_scolaire=annee_sel)

    return render(request, 'manuels/attributions_list.html', {
        'attributions': qs,
        'annees': annees,
        'annee_sel': annee_sel,
    })


@login_required
def attribution_form(request, exemplaire_pk=None):
    etab = _etab(request)
    annee_courante = _annee_courante(etab)

    # Pré-sélection si exemplaire fourni en URL
    exemplaire_sel = None
    if exemplaire_pk:
        exemplaire_sel = get_object_or_404(ExemplaireManuel, pk=exemplaire_pk, manuel__etablissement=etab)

    manuels = ManuelScolaire.objects.filter(etablissement=etab, actif=True)
    classes = Classe.objects.filter(etablissement=etab).order_by('nom')
    error = None

    if request.method == 'POST':
        ex_pk = request.POST.get('exemplaire')
        insc_pk = request.POST.get('inscription')
        date_attr = request.POST.get('date_attribution') or str(date.today())
        etat_sortie = request.POST.get('etat_sortie', EtatManuel.BON)

        exemplaire = get_object_or_404(ExemplaireManuel, pk=ex_pk, manuel__etablissement=etab)
        inscription = get_object_or_404(Inscription, pk=insc_pk, annee_scolaire__etablissement=etab)

        if not exemplaire.est_disponible:
            error = "Cet exemplaire est déjà attribué à un élève."
        else:
            AttributionManuel.objects.create(
                exemplaire=exemplaire,
                inscription=inscription,
                date_attribution=date_attr,
                etat_sortie=etat_sortie,
            )
            messages.success(
                request,
                f"Manuel {exemplaire.code_exemplaire} attribué à "
                f"{inscription.eleve.nom} {inscription.eleve.prenom}."
            )
            return redirect('manuels:attributions_list')

    # Exemplaires disponibles pour HTMX select (tout charger initialement)
    exemplaires_dispo = ExemplaireManuel.objects.filter(
        manuel__etablissement=etab, actif=True
    ).select_related('manuel')

    inscriptions = Inscription.objects.none()
    classe_id = request.GET.get('classe')
    if classe_id and annee_courante:
        inscriptions = Inscription.objects.filter(
            classe_id=classe_id,
            annee_scolaire=annee_courante,
        ).select_related('eleve').order_by('eleve__nom')

    return render(request, 'manuels/attribution_form.html', {
        'exemplaire_sel': exemplaire_sel,
        'exemplaires_dispo': exemplaires_dispo,
        'manuels': manuels,
        'classes': classes,
        'inscriptions': inscriptions,
        'classe_sel': classe_id,
        'etats': EtatManuel.choices,
        'today': str(date.today()),
        'error': error,
    })


@login_required
def inscription_par_classe(request):
    """HTMX : renvoie les élèves d'une classe pour le formulaire d'attribution."""
    etab = _etab(request)
    annee_courante = _annee_courante(etab)
    classe_id = request.GET.get('classe_sel') or request.GET.get('classe')
    inscriptions = Inscription.objects.none()
    if classe_id and annee_courante:
        inscriptions = Inscription.objects.filter(
            classe_id=classe_id,
            annee_scolaire=annee_courante,
        ).select_related('eleve').order_by('eleve__nom')
    return render(request, 'manuels/partials/eleves_options.html', {
        'inscriptions': inscriptions,
    })


@login_required
def exemplaires_par_manuel(request):
    """HTMX : renvoie les exemplaires disponibles d'un manuel."""
    etab = _etab(request)
    manuel_pk = request.GET.get('manuel_sel') or request.GET.get('manuel')
    exemplaires = ExemplaireManuel.objects.none()
    if manuel_pk:
        tous = ExemplaireManuel.objects.filter(
            manuel_id=manuel_pk, manuel__etablissement=etab, actif=True
        )
        exemplaires = [e for e in tous if e.est_disponible]
    return render(request, 'manuels/partials/exemplaires_options.html', {
        'exemplaires': exemplaires,
    })


@login_required
def attribution_retour(request, pk):
    etab = _etab(request)
    attribution = get_object_or_404(
        AttributionManuel, pk=pk,
        exemplaire__manuel__etablissement=etab,
        date_retour__isnull=True,
    )
    error = None

    if request.method == 'POST':
        d_retour = request.POST.get('date_retour') or str(date.today())
        etat_ret = request.POST.get('etat_retour', EtatManuel.BON)
        observation = request.POST.get('observation', '').strip()
        attribution.date_retour = d_retour
        attribution.etat_retour = etat_ret
        attribution.observation = observation
        attribution.exemplaire.etat = etat_ret
        attribution.exemplaire.save()
        attribution.save()
        messages.success(request, "Retour enregistré.")
        return redirect('manuels:attributions_list')

    return render(request, 'manuels/attribution_retour.html', {
        'attribution': attribution,
        'etats': EtatManuel.choices,
        'today': str(date.today()),
        'error': error,
    })


# ── Manuels non rendus ─────────────────────────────────────────────────────

@login_required
def non_rendus(request):
    etab = _etab(request)
    annees = _get_annees(etab)
    annee_id = request.GET.get('annee')
    annee_courante = _annee_courante(etab)
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    qs = AttributionManuel.objects.filter(
        exemplaire__manuel__etablissement=etab,
        date_retour__isnull=True,
    ).select_related(
        'exemplaire__manuel', 'inscription__eleve', 'inscription__classe', 'inscription__annee_scolaire'
    ).order_by('inscription__eleve__nom')

    if annee_sel:
        qs = qs.filter(inscription__annee_scolaire=annee_sel)

    return render(request, 'manuels/non_rendus.html', {
        'attributions': qs,
        'annees': annees,
        'annee_sel': annee_sel,
    })


@login_required
@require_POST
def facturer_non_rendu(request, pk):
    """Génère un paiement dans finances pour le manuel non rendu et notifie les parents par SMS."""
    etab = _etab(request)
    attribution = get_object_or_404(
        AttributionManuel, pk=pk,
        exemplaire__manuel__etablissement=etab,
        date_retour__isnull=True,
        facture_genere=False,
    )
    manuel = attribution.exemplaire.manuel
    inscription = attribution.inscription
    eleve = inscription.eleve

    if manuel.prix_remplacement <= 0:
        messages.warning(request, "Prix de remplacement non défini pour ce manuel.")
        return redirect('manuels:non_rendus')

    # Rubrique et paiement
    rubrique, _ = RubriquePaiement.objects.get_or_create(
        etablissement=etab,
        code='MNR',
        defaults={'nom': 'Manuel non rendu', 'obligatoire': False},
    )
    Paiement.objects.create(
        inscription=inscription,
        rubrique=rubrique,
        montant=manuel.prix_remplacement,
        date_paiement=date.today(),
        mode_paiement='ESPECES',
        observation=f"Manuel non rendu : {manuel.titre} ({attribution.exemplaire.code_exemplaire})",
    )
    attribution.facture_genere = True
    attribution.save()

    # ── Notification SMS aux parents ──────────────────────────────────────────
    _notifier_parents_manuel_non_rendu(eleve, manuel, etab)

    messages.success(
        request,
        f"Frais de {manuel.prix_remplacement:,.0f} FCFA facturés à "
        f"{eleve.nom} {eleve.prenom}. Les parents ont été notifiés par SMS."
    )
    return redirect('manuels:non_rendus')


def _notifier_parents_manuel_non_rendu(eleve, manuel, etab):
    """Envoie un SMS aux parents d'un élève pour signaler la facturation d'un manuel non rendu."""
    from django.conf import settings
    from core.notifications import creer_notification
    from core.tasks import envoyer_sms_async

    titre = f"Manuel non rendu — {manuel.titre}"
    message_inapp = (
        f"{eleve.nom} {eleve.prenom} n'a pas rendu le manuel « {manuel.titre} ». "
        f"Des frais de {manuel.prix_remplacement:,.0f} FCFA ont été ajoutés à ses frais scolaires."
    )
    sms_texte = (
        f"[{etab.nom}] Manuel non rendu : {eleve.nom} {eleve.prenom} "
        f"doit restituer '{manuel.titre}'. "
        f"Frais factures : {manuel.prix_remplacement:,.0f} FCFA."
    )

    sms_active = getattr(settings, 'SMS_ENABLED', False)

    # 1. Notification in-app pour les parents avec compte (sans SMS délégué à creer_notification)
    parents_comptes = eleve.utilisateurs_lies.filter(role='PARENT', is_active=True)
    for parent in parents_comptes:
        creer_notification(parent, 'GENERAL', titre, message_inapp,
                           lien='/manuels/non-rendus/', envoyer_sms=False)

    if not sms_active:
        return

    # 2. Collecter TOUS les numéros disponibles :
    #    - téléphones des comptes parents (peut être vide même si le compte existe)
    #    - numéros directs dans la fiche élève (fallback universel)
    numeros = set()
    for parent in parents_comptes:
        if getattr(parent, 'telephone', ''):
            numeros.add(parent.telephone.strip())
    for num in [eleve.telephone_parent, eleve.tuteur_telephone, eleve.telephone_urgence]:
        if num and num.strip():
            numeros.add(num.strip())

    for numero in numeros:
        try:
            envoyer_sms_async(numero, sms_texte)
        except Exception:
            pass


# ── Export PDF inventaire par classe ───────────────────────────────────────

@login_required
def inventaire_classe_pdf(request, classe_pk):
    etab = _etab(request)
    classe = get_object_or_404(Classe, pk=classe_pk, etablissement=etab)
    annee_courante = _annee_courante(etab)

    attributions = AttributionManuel.objects.filter(
        inscription__classe=classe,
        inscription__annee_scolaire=annee_courante,
        date_retour__isnull=True,
    ).select_related(
        'exemplaire__manuel', 'inscription__eleve'
    ).order_by('inscription__eleve__nom', 'exemplaire__manuel__titre')

    html = render(request, 'manuels/pdf/inventaire_classe.html', {
        'classe': classe,
        'attributions': attributions,
        'annee': annee_courante,
        'today': date.today(),
    }).content.decode('utf-8')

    from weasyprint import HTML as WP
    pdf = WP(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="inventaire_{classe.nom}_{annee_courante}.pdf"'
    )
    return response


# ── Export PDF attributions par année ──────────────────────────────────────

@login_required
def attributions_annee_pdf(request):
    etab = _etab(request)
    annees = _get_annees(etab)
    annee_id = request.GET.get('annee')
    annee_courante = _annee_courante(etab)
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    attributions = (
        AttributionManuel.objects
        .filter(inscription__annee_scolaire=annee_sel, exemplaire__manuel__etablissement=etab)
        .select_related(
            'exemplaire__manuel',
            'inscription__eleve',
            'inscription__classe',
        )
        .order_by('inscription__classe__nom', 'inscription__eleve__nom', 'exemplaire__manuel__titre')
    ) if annee_sel else AttributionManuel.objects.none()

    nb_en_cours = attributions.filter(date_retour__isnull=True).count()
    nb_rendus = attributions.filter(date_retour__isnull=False).count()

    html = render(request, 'manuels/pdf/attributions_annee.html', {
        'annee': annee_sel,
        'attributions': attributions,
        'nb_en_cours': nb_en_cours,
        'nb_rendus': nb_rendus,
        'today': date.today(),
        'etab': etab,
    }).content.decode('utf-8')

    from weasyprint import HTML as WP
    pdf = WP(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    annee_label = str(annee_sel).replace('/', '-') if annee_sel else 'export'
    response['Content-Disposition'] = f'inline; filename="attributions_{annee_label}.pdf"'
    return response


# ── Export PDF non rendus par année ────────────────────────────────────────

@login_required
def non_rendus_pdf(request):
    etab = _etab(request)
    annees = _get_annees(etab)
    annee_id = request.GET.get('annee')
    annee_courante = _annee_courante(etab)
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    attributions = (
        AttributionManuel.objects
        .filter(
            exemplaire__manuel__etablissement=etab,
            date_retour__isnull=True,
        )
        .select_related(
            'exemplaire__manuel',
            'inscription__eleve',
            'inscription__classe',
            'inscription__annee_scolaire',
        )
        .order_by('inscription__classe__nom', 'inscription__eleve__nom')
    )
    if annee_sel:
        attributions = attributions.filter(inscription__annee_scolaire=annee_sel)

    from django.db.models import Sum as _Sum
    total_du = (
        attributions.aggregate(t=_Sum('exemplaire__manuel__prix_remplacement'))['t']
        or Decimal('0')
    )
    nb_factures = attributions.filter(facture_genere=True).count()

    # Évaluer le queryset une seule fois pour le template
    attributions = list(attributions)

    from core.utils import get_etablissement_context
    etab_ctx = get_etablissement_context(etab, request)

    html = render(request, 'manuels/pdf/non_rendus_annee.html', {
        'annee': annee_sel,
        'attributions': attributions,
        'total_du': total_du,
        'nb_factures': nb_factures,
        'today': date.today(),
        'etab': etab,
        'identite': etab_ctx.get('identite'),
        'logo_url': etab_ctx.get('logo_url') or etab_ctx.get('etab_logo_url'),
    }).content.decode('utf-8')

    from weasyprint import HTML as WP
    pdf = WP(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    annee_label = str(annee_sel).replace('/', '-') if annee_sel else 'export'
    response['Content-Disposition'] = f'inline; filename="non_rendus_{annee_label}.pdf"'
    return response
