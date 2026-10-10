"""
Module Vacations - Views
========================
YELEN SCHOOL v3.4
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.template.loader import render_to_string

from parametres.models import AnneeScolaire
from core.utils import get_etablissement_context
from .models import ContratVacation, HeureVacation, BulletinVacation
from .forms import ContratVacationForm


from licences.decorators import requires_licence_feature
@login_required
@requires_licence_feature('vacations')
def contrat_list(request):
    """Liste des contrats de vacation actifs."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    contrats = ContratVacation.objects.filter(
        annee_scolaire=annee_courante,
        actif=True
    ).select_related('personnel', 'enseignement__matiere', 'enseignement__classe')

    return render(request, 'vacations/contrat_list.html', {
        'contrats': contrats,
        'annee_courante': annee_courante,
    })


@login_required
@requires_licence_feature('vacations')
def contrat_create(request):
    """Créer un nouveau contrat de vacation."""
    if request.method == 'POST':
        form = ContratVacationForm(request.POST)
        if form.is_valid():
            contrat = form.save()
            messages.success(request, f"Contrat créé pour {contrat.personnel.get_nom_complet}.")
            return redirect('vacations:contrat_list')
    else:
        form = ContratVacationForm()

    return render(request, 'vacations/contrat_form.html', {
        'form': form,
        'title': 'Nouveau contrat de vacation'
    })


@login_required
@requires_licence_feature('vacations')
def saisie_heures(request, contrat_id):
    """Saisie mensuelle des heures pour un contrat."""
    etab = getattr(request.user, 'etablissement', None)
    contrat = get_object_or_404(
        ContratVacation.objects.select_related(
            'personnel', 'annee_scolaire'
        ),
        pk=contrat_id
    )
    
    if etab and contrat.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('vacations:contrat_list')

    # Récupérer ou créer les enregistrements pour les mois de l'année scolaire
    heures_list = HeureVacation.objects.filter(
        contrat=contrat
    ).order_by('annee', 'mois')

    if request.method == 'POST':
        mois = int(request.POST.get('mois'))
        annee = int(request.POST.get('annee'))
        effectuees = Decimal(request.POST.get('heures_effectuees', '0').replace(',', '.'))
        annulees = Decimal(request.POST.get('heures_annulees', '0').replace(',', '.'))
        obs = request.POST.get('observations', '')

        heure, _ = HeureVacation.objects.update_or_create(
            contrat=contrat,
            mois=mois,
            annee=annee,
            defaults={
                'heures_effectuees': effectuees,
                'heures_annulees': annulees,
                'observations': obs,
            }
        )
        messages.success(request, f"Heures de {heure.get_mois_display()} {annee} enregistrées.")
        return redirect('vacations:saisie_heures', contrat_id=contrat.pk)

    # Années scolaires disponibles pour la saisie
    from parametres.models import AnneeScolaire
    etab = getattr(contrat.annee_scolaire, 'etablissement', None)
    if etab:
        annees_scolaires = AnneeScolaire.objects.filter(
            etablissement=etab
        ).order_by('-date_debut')
    else:
        annees_scolaires = AnneeScolaire.objects.none()

    # Liste des années pour le formulaire (year, libelle)
    if annees_scolaires:
        annees_list = [(a.date_debut.year, a.libelle) for a in annees_scolaires]
    else:
        # Fallback si aucune année scolaire
        annees_list = [(contrat.annee_scolaire.date_debut.year, contrat.annee_scolaire.libelle)]

    return render(request, 'vacations/saisie_heures.html', {
        'contrat': contrat,
        'heures_list': heures_list,
        'mois_choices': HeureVacation.MOIS_CHOICES,
        'annees_list': annees_list,
    })


@login_required
@requires_licence_feature('vacations')
def valider_heure(request, heure_id):
    """Valider une saisie d'heures."""
    etab = getattr(request.user, 'etablissement', None)
    heure = get_object_or_404(HeureVacation, pk=heure_id)
    
    if etab and heure.contrat.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('vacations:contrat_list')
    
    heure.est_valide = True
    heure.save(update_fields=['est_valide'])
    messages.success(request, f"Heures de {heure.get_mois_display()} {heure.annee} validées.")
    return redirect('vacations:saisie_heures', contrat_id=heure.contrat.pk)


@login_required
@requires_licence_feature('vacations')
def invalider_heure(request, heure_id):
    """Invalider une saisie d'heures."""
    etab = getattr(request.user, 'etablissement', None)
    heure = get_object_or_404(HeureVacation, pk=heure_id)
    
    if etab and heure.contrat.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('vacations:contrat_list')
    heure.est_valide = False
    heure.save(update_fields=['est_valide'])
    messages.warning(request, f"Heures de {heure.get_mois_display()} {heure.annee} invalidées.")
    return redirect('vacations:saisie_heures', contrat_id=heure.contrat.pk)


@login_required
@requires_licence_feature('vacations')
def bulletin_list(request):
    """Liste des bulletins de vacation avec filtre par etablissement et pagination."""
    etab = getattr(request.user, 'etablissement', None)
    page_number = request.GET.get('page', 1)

    # Années scolaires disponibles pour le filtre
    if etab:
        annees_scolaires = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    else:
        annees_scolaires = AnneeScolaire.objects.order_by('-date_debut')[:10]

    # Tous les bulletins sans filtre par année scolaire
    qs = BulletinVacation.objects.select_related('personnel', 'annee_scolaire').order_by(
        '-annee', '-mois', 'personnel__nom'
    )

    # Filtres
    mois_filter = request.GET.get('mois')
    annee_filter = request.GET.get('annee')
    statut_filter = request.GET.get('statut')

    if mois_filter:
        qs = qs.filter(mois=int(mois_filter))
    if annee_filter:
        qs = qs.filter(annee_scolaire__date_debut__year=int(annee_filter))
    if statut_filter:
        qs = qs.filter(statut=statut_filter)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)

    return render(request, 'vacations/bulletin_list.html', {
        'bulletins': page_obj,
        'page_obj': page_obj,
        'annee_courante': None,
        'mois_choices': HeureVacation.MOIS_CHOICES,
        'annees_scolaires': annees_scolaires,
        'current_month': int(request.GET.get('mois', date.today().month)),
        'current_year': int(request.GET.get('annee', date.today().year)),
    })


@login_required
@requires_licence_feature('vacations')
def generer_bulletin(request, contrat_id, mois, annee):
    """Génère ou régénère le bulletin de vacation d'un vacataire pour un mois."""
    contrat = get_object_or_404(ContratVacation, pk=contrat_id)

    bulletin, _ = BulletinVacation.objects.get_or_create(
        personnel=contrat.personnel,
        annee_scolaire=contrat.annee_scolaire,
        mois=mois,
        annee=annee,
        defaults={'statut': BulletinVacation.StatutChoices.BROUILLON}
    )
    bulletin.calculer_totaux()

    messages.success(
        request,
        f"Bulletin de {bulletin.get_mois_display()} {annee} généré : "
        f"{bulletin.total_heures}h — {bulletin.montant_total:,.0f} FCFA"
    )
    return redirect('vacations:bulletin_list')


@login_required
@requires_licence_feature('vacations')
def generer_tous_bulletins(request):
    """Génère les bulletins pour tous les contrats actifs - mois en cours par défaut."""
    from datetime import date

    # Récupérer les paramètres de mois/annee (optionnel)
    mois_param = request.GET.get('mois')
    annee_param = request.GET.get('annee')

    mois_actuel = int(mois_param) if mois_param else date.today().month
    annee_actuelle = int(annee_param) if annee_param else date.today().year

    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(
        est_courante=True,
        **(({'etablissement': etab}) if etab else {}),
    ).first()

    if not annee_courante:
        messages.error(request, "Aucune année scolaire active trouvée.")
        return redirect('vacations:bulletin_list')

    contrats = ContratVacation.objects.filter(
        annee_scolaire=annee_courante,
        actif=True
    ).select_related('personnel')

    count = 0
    bulletins_crees = []

    for contrat in contrats:
        heures = HeureVacation.objects.filter(
            contrat=contrat,
            mois=mois_actuel,
            annee=annee_actuelle,
            est_valide=True
        )

        if heures.exists():
            bulletin, created = BulletinVacation.objects.get_or_create(
                personnel=contrat.personnel,
                annee_scolaire=contrat.annee_scolaire,
                mois=mois_actuel,
                annee=annee_actuelle,
                defaults={'statut': BulletinVacation.StatutChoices.BROUILLON}
            )
            bulletin.calculer_totaux()
            count += 1
            bulletins_crees.append(f"{contrat.personnel.get_nom_complet()}: {bulletin.total_heures}h")

    if count == 0:
        messages.warning(request, f"Aucune heure validée trouvée pour {date(annee_actuelle, mois_actuel, 1):%B %Y}.")
    else:
        extra = '...' if count > 3 else ''
        messages.success(request, f"{count} bulletin(s) généré(s) : {', '.join(bulletins_crees[:3])}{extra}")

    return redirect('vacations:bulletin_list')


@login_required
@requires_licence_feature('vacations')
def valider_bulletin(request, bulletin_id):
    """Valider un bulletin de vacation."""
    etab = getattr(request.user, 'etablissement', None)
    bulletin = get_object_or_404(BulletinVacation, pk=bulletin_id)
    
    if etab and bulletin.contrat.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('vacations:bulletin_list')
    
    bulletin.statut = BulletinVacation.StatutChoices.VALIDE
    bulletin.save(update_fields=['statut'])
    messages.success(request, f"Bulletin de {bulletin.get_mois_display()} {bulletin.annee} validé.")
    return redirect('vacations:bulletin_list')


@login_required
@requires_licence_feature('vacations')
def payer_bulletin(request, bulletin_id):
    etab = getattr(request.user, 'etablissement', None)
    bulletin = get_object_or_404(BulletinVacation, pk=bulletin_id)
    
    if etab and bulletin.contrat.annee_scolaire.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('vacations:bulletin_list')
    
    """Marquer un bulletin comme payé."""
    bulletin.statut = BulletinVacation.StatutChoices.PAYE
    from django.utils import timezone
    bulletin.date_paiement = timezone.now().date()
    bulletin.save(update_fields=['statut', 'date_paiement'])
    messages.success(request, f"Bulletin de {bulletin.get_mois_display()} {bulletin.annee} marqué comme payé.")
    return redirect('vacations:bulletin_list')


@login_required
@requires_licence_feature('vacations')
def bulletin_vacation_pdf(request, bulletin_id):
    """Génère le PDF d'un bulletin de vacation."""
    bulletin = get_object_or_404(
        BulletinVacation.objects.select_related(
            'personnel', 'annee_scolaire'
        ),
        pk=bulletin_id
    )

    # Détail des heures par contrat pour ce mois
    heures = (
        HeureVacation.objects
        .filter(
            contrat__personnel=bulletin.personnel,
            contrat__annee_scolaire=bulletin.annee_scolaire,
            mois=bulletin.mois,
            annee=bulletin.annee,
        )
        .select_related(
            'contrat__enseignement__matiere',
            'contrat__enseignement__classe',
            'contrat',
        )
        .order_by('contrat__enseignement__matiere__nom')
    )

    etab = getattr(request.user, 'etablissement', None)
    etab_context = get_etablissement_context(etab, request) if etab else {}

    context = {
        'bulletin': bulletin,
        'heures': heures,
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
    }

    try:
        from core.pdf import HTML
        html_string = render_to_string(
            'vacations/pdf/bulletin.html', context, request=request
        )
        pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        nom = (
            f"bulletin_vacation_{bulletin.personnel.nom}_{bulletin.get_mois_display()}_{bulletin.annee}"
            .replace(' ', '_')
        )
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{nom}.pdf"'
        return response
    except ImportError:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('vacations:bulletin_list')
