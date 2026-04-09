"""
Module Présences - Views
=========================
YELEN SCHOOL v3.4
"""

import csv
from datetime import date
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from parametres.models import Classe, AnneeScolaire, Cycle
from inscriptions.models import Inscription
from personnel.models import MembrePersonnel
from pedagogie.models import Matiere
from .models import Appel, Presence, Justification


def _get_annee_courante(etablissement):
    return AnneeScolaire.objects.filter(
        etablissement=etablissement, est_courante=True
    ).first()


def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


# ─── Appels ────────────────────────────────────────────────────────────────────

def _build_appel_groupes(qs):
    """Groupe un queryset d'appels par date puis par classe."""
    appels = list(qs)
    groupes_dates = []
    for date_val, appels_date in groupby(appels, key=lambda a: a.date):
        appels_date = list(appels_date)
        groupes_classes = []
        for classe, appels_classe in groupby(appels_date, key=lambda a: a.classe_id):
            appels_classe = list(appels_classe)
            groupes_classes.append({'classe': appels_classe[0].classe, 'appels': appels_classe})
        groupes_dates.append({'date': date_val, 'groupes_classes': groupes_classes})
    return groupes_dates


@login_required
def appel_list(request):
    """Liste des appels récents avec filtres."""
    etab = _get_etab(request)
    annee = _get_annee_courante(etab)

    # Filtres GET
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    classe_id = request.GET.get('classe', '')

    qs = Appel.objects.select_related(
        'classe', 'classe__cycle', 'matiere', 'effectue_par'
    )
    if annee:
        qs = qs.filter(annee_scolaire=annee)
    if date_debut:
        qs = qs.filter(date__gte=date_debut)
    if date_fin:
        qs = qs.filter(date__lte=date_fin)
    if classe_id:
        qs = qs.filter(classe_id=classe_id)

    qs = qs.order_by('-date', 'classe__nom')
    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(page_number)

    classes = Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle').order_by('cycle__ordre', 'nom')

    nb_justifications_attente = Justification.objects.filter(
        inscription__annee_scolaire=annee,
        statut=Justification.StatutChoices.EN_ATTENTE,
    ).count() if annee else 0

    return render(request, 'presences/appel_list.html', {
        'groupes_dates': _build_appel_groupes(page_obj.object_list),
        'page_obj': page_obj,
        'annee': annee,
        'classes': classes,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'classe_id': classe_id,
        'nb_justifications_attente': nb_justifications_attente,
    })


@login_required
def appel_csv(request):
    """Export CSV des appels avec leurs présences."""
    etab = _get_etab(request)
    annee = _get_annee_courante(etab)
    
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    classe_id = request.GET.get('classe', '')
    
    qs = Appel.objects.select_related(
        'classe', 'classe__cycle', 'matiere', 'effectue_par'
    ).prefetch_related('presences__inscription__eleve')
    
    if annee:
        qs = qs.filter(annee_scolaire=annee)
    if date_debut:
        qs = qs.filter(date__gte=date_debut)
    if date_fin:
        qs = qs.filter(date__lte=date_fin)
    if classe_id:
        qs = qs.filter(classe_id=classe_id)
    
    qs = qs.order_by('-date', 'classe__nom')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    nom_fichier = f"appels_{date_debut or 'tout'}_{date_fin or 'tout'}.csv".replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Date', 'Classe', 'Cycle', 'Matière', 'Effectué par',
        'Présent', 'Absent', 'Retard', 'Total élève'
    ])
    
    for appel in qs:
        presences = appel.presences.all()
        presents = presences.filter(statut='PRESENT').count()
        absents = presences.filter(statut='ABSENT').count()
        retards = presences.filter(statut='RETARD').count()
        
        writer.writerow([
            appel.date.strftime('%d/%m/%Y'),
            appel.classe.nom,
            appel.classe.cycle.nom if appel.classe.cycle else '',
            appel.matiere.nom if appel.matiere else '',
            appel.effectue_par.get_full_name() if appel.effectue_par else '',
            presents,
            absents,
            retards,
            presences.count(),
        ])
    
    return response


@login_required
def appel_print(request):
    """Vue d'impression des appels (filtrée)."""
    etab = _get_etab(request)
    annee = _get_annee_courante(etab)

    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    classe_id = request.GET.get('classe', '')

    qs = Appel.objects.select_related(
        'classe', 'classe__cycle', 'matiere', 'effectue_par'
    )
    if annee:
        qs = qs.filter(annee_scolaire=annee)
    if date_debut:
        qs = qs.filter(date__gte=date_debut)
    if date_fin:
        qs = qs.filter(date__lte=date_fin)
    if classe_id:
        qs = qs.filter(classe_id=classe_id)

    return render(request, 'presences/appel_print.html', {
        'groupes_dates': _build_appel_groupes(qs),
        'annee': annee,
        'date_debut': date_debut,
        'date_fin': date_fin,
    })


@login_required
def classe_select(request):
    """Sélection de la classe pour démarrer un nouvel appel."""
    etab = _get_etab(request)
    annee = _get_annee_courante(etab)

    cycles = Cycle.objects.filter(etablissement=etab).order_by('ordre', 'nom')
    classes_qs = Classe.objects.filter(
        etablissement=etab, actif=True
    ).select_related('cycle').order_by('cycle__ordre', 'nom')

    # Regrouper par cycle
    classes_par_cycle = []
    for cycle in cycles:
        classes = [c for c in classes_qs if c.cycle_id == cycle.id]
        if classes:
            classes_par_cycle.append({'cycle': cycle, 'classes': classes})

    return render(request, 'presences/classe_select.html', {
        'classes_par_cycle': classes_par_cycle,
        'annee': annee,
    })


@login_required
def appel_create(request, classe_id):
    """Créer un appel pour une classe."""
    etab = _get_etab(request)
    classe = get_object_or_404(Classe, pk=classe_id, etablissement=etab)
    annee = _get_annee_courante(etab)

    if request.method == 'POST':
        date_appel = request.POST.get('date') or date.today()
        matiere_id = request.POST.get('matiere') or None

        # Vérifier si un appel existe déjà pour cette combinaison
        appel_existant = Appel.objects.filter(
            classe=classe,
            annee_scolaire=annee,
            matiere_id=matiere_id,
            date=date_appel,
        ).first()

        if appel_existant:
            messages.warning(
                request,
                "Un appel existe déjà pour cette classe, cette date et cette matière. "
                "Vous avez été redirigé vers l'appel existant."
            )
            return redirect('presences:appel_saisie', appel_id=appel_existant.pk)

        appel = Appel.objects.create(
            classe=classe,
            annee_scolaire=annee,
            matiere_id=matiere_id,
            date=date_appel,
            heure_debut=request.POST.get('heure_debut') or None,
            heure_fin=request.POST.get('heure_fin') or None,
        )

        inscriptions = Inscription.objects.filter(
            classe=classe,
            annee_scolaire=annee
        ).exclude(statut='ABANDON').select_related('eleve')

        Presence.objects.bulk_create([
            Presence(appel=appel, inscription=ins, statut=Presence.StatutChoices.PRESENT)
            for ins in inscriptions
        ])

        return redirect('presences:appel_saisie', appel_id=appel.pk)

    matieres = Matiere.objects.order_by('code')

    return render(request, 'presences/appel_form.html', {
        'classe': classe,
        'matieres': matieres,
        'today': date.today().isoformat(),
    })


@login_required
def appel_saisie(request, appel_id):
    """Saisie des présences pour un appel."""
    appel = get_object_or_404(
        Appel.objects.select_related('classe', 'matiere'),
        pk=appel_id
    )

    if appel.est_clos:
        messages.warning(request, "Cet appel est clôturé, la saisie n'est plus possible.")

    presences = appel.presences.select_related(
        'inscription__eleve'
    ).order_by('inscription__eleve__nom', 'inscription__eleve__prenom')

    if request.method == 'POST' and not appel.est_clos:
        for presence in presences:
            statut = request.POST.get(f'statut_{presence.pk}', Presence.StatutChoices.PRESENT)
            minutes = request.POST.get(f'retard_{presence.pk}', 0)
            presence.statut = statut
            presence.minutes_retard = int(minutes) if minutes else 0
            presence.save(update_fields=['statut', 'minutes_retard'])

        if request.POST.get('clore'):
            appel.est_clos = True
            appel.save(update_fields=['est_clos'])
            messages.success(request, "Appel clôturé avec succès.")
            return redirect('presences:appel_list')

        messages.success(request, "Présences enregistrées.")
        return redirect('presences:appel_saisie', appel_id=appel.pk)

    return render(request, 'presences/appel_saisie.html', {
        'appel': appel,
        'presences': presences,
        'statuts': Presence.StatutChoices.choices,
    })


# ─── Bilan élève ───────────────────────────────────────────────────────────────

@login_required
def bilan_eleve(request, inscription_id):
    """Bilan d'absences d'un élève pour l'année en cours."""
    etab = _get_etab(request)
    qs = Inscription.objects.select_related('eleve', 'classe', 'annee_scolaire')
    if etab:
        qs = qs.filter(classe__etablissement=etab)
    inscription = get_object_or_404(qs, pk=inscription_id)

    presences = Presence.objects.filter(
        inscription=inscription
    ).select_related('appel__matiere').order_by('-appel__date')

    stats = {
        'total': presences.count(),
        'presents': presences.filter(statut=Presence.StatutChoices.PRESENT).count(),
        'absents': presences.filter(statut=Presence.StatutChoices.ABSENT).count(),
        'retards': presences.filter(statut=Presence.StatutChoices.RETARD).count(),
        'excuses': presences.filter(statut=Presence.StatutChoices.EXCUSE).count(),
    }

    justifications = Justification.objects.filter(inscription=inscription).order_by('-date_debut')

    return render(request, 'presences/bilan_eleve.html', {
        'inscription': inscription,
        'presences': presences,
        'stats': stats,
        'justifications': justifications,
    })


# ─── Justifications ────────────────────────────────────────────────────────────

@login_required
def justification_list(request):
    """Liste de toutes les justifications."""
    etab = _get_etab(request)
    annee = _get_annee_courante(etab)

    statut = request.GET.get('statut', '')
    classe_id = request.GET.get('classe', '')
    q = request.GET.get('q', '').strip()

    qs = Justification.objects.filter(
        inscription__annee_scolaire=annee
    ).select_related(
        'inscription__eleve', 'inscription__classe', 'traitee_par'
    ).order_by('-date_debut')

    if statut:
        qs = qs.filter(statut=statut)
    if classe_id:
        qs = qs.filter(inscription__classe_id=classe_id)
    if q:
        qs = qs.filter(
            inscription__eleve__nom__icontains=q
        ) | qs.filter(
            inscription__eleve__prenom__icontains=q
        )

    # Statistiques globales
    base_qs = Justification.objects.filter(inscription__annee_scolaire=annee)
    stats = {
        'total': base_qs.count(),
        'en_attente': base_qs.filter(statut=Justification.StatutChoices.EN_ATTENTE).count(),
        'acceptees': base_qs.filter(statut=Justification.StatutChoices.ACCEPTEE).count(),
        'refusees': base_qs.filter(statut=Justification.StatutChoices.REFUSEE).count(),
    }

    classes = Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle').order_by('cycle__ordre', 'nom')

    return render(request, 'presences/justification_list.html', {
        'justifications': qs,
        'statuts': Justification.StatutChoices.choices,
        'statut_filtre': statut,
        'classe_id': classe_id,
        'q': q,
        'annee': annee,
        'stats': stats,
        'classes': classes,
    })


@login_required
def justification_create(request, inscription_id):
    """Créer une justification d'absence pour un élève."""
    etab = getattr(request.user, 'etablissement', None)
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe'),
        pk=inscription_id
    )
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('presences:appel_list')

    if request.method == 'POST':
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')
        motif = request.POST.get('motif', '').strip()
        document = request.FILES.get('document')

        if not all([date_debut, date_fin, motif]):
            messages.error(request, "La date de début, date de fin et le motif sont obligatoires.")
        elif date_fin < date_debut:
            messages.error(request, "La date de fin ne peut pas être antérieure à la date de début.")
        else:
            Justification.objects.create(
                inscription=inscription,
                date_debut=date_debut,
                date_fin=date_fin,
                motif=motif,
                document=document,
            )
            messages.success(request, "Justification enregistrée avec succès.")
            return redirect('presences:bilan_eleve', inscription_id=inscription.pk)

    return render(request, 'presences/justification_form.html', {
        'inscription': inscription,
    })


@login_required
def justification_process(request, justification_id):
    """Accepter ou refuser une justification."""
    justification = get_object_or_404(
        Justification.objects.select_related('inscription__eleve', 'inscription__classe'),
        pk=justification_id
    )

    # Absences de l'élève dans la période concernée
    absences_concernees = Presence.objects.filter(
        inscription=justification.inscription,
        statut__in=[Presence.StatutChoices.ABSENT, Presence.StatutChoices.EXCUSE],
        appel__date__range=(justification.date_debut, justification.date_fin)
    ).select_related('appel__matiere').order_by('appel__date')

    if request.method == 'POST':
        decision = request.POST.get('decision')
        observation = request.POST.get('observation', '').strip()

        if decision in ('ACCEPTEE', 'REFUSEE'):
            traitee_par = None

            justification.statut = decision
            justification.observation_traitement = observation
            justification.date_traitement = date.today()
            justification.traitee_par = traitee_par
            justification.save(update_fields=[
                'statut', 'observation_traitement', 'date_traitement', 'traitee_par'
            ])

            # Si acceptée → marquer les absences de la période comme EXCUSE
            if decision == 'ACCEPTEE':
                Presence.objects.filter(
                    inscription=justification.inscription,
                    statut=Presence.StatutChoices.ABSENT,
                    appel__date__range=(justification.date_debut, justification.date_fin)
                ).update(statut=Presence.StatutChoices.EXCUSE)
                nb = absences_concernees.filter(statut=Presence.StatutChoices.ABSENT).count()
                messages.success(request, f"Justification acceptée. {nb} absence(s) excusée(s).")
            else:
                messages.success(request, "Justification refusée.")

            return redirect('presences:justification_list')

    return render(request, 'presences/justification_process.html', {
        'justification': justification,
        'absences_concernees': absences_concernees,
    })


@login_required
def bilan_annuel(request):
    """Bilan HTML d'absences/retards par élève sur l'année, filtrable par classe."""
    etab = _get_etab(request)
    annee = _get_annee_courante(etab)

    classe_id = request.GET.get('classe', '')

    presences_qs = Presence.objects.select_related(
        'inscription__eleve', 'inscription__classe'
    )
    if annee:
        presences_qs = presences_qs.filter(appel__annee_scolaire=annee)
    if etab:
        presences_qs = presences_qs.filter(appel__classe__etablissement=etab)
    if classe_id:
        presences_qs = presences_qs.filter(inscription__classe_id=classe_id)

    lignes = (
        presences_qs
        .values(
            'inscription__pk',
            'inscription__eleve__nom',
            'inscription__eleve__prenom',
            'inscription__eleve__matricule',
            'inscription__classe__pk',
            'inscription__classe__nom',
        )
        .annotate(
            total=Count('id'),
            presents=Count('id', filter=Q(statut=Presence.StatutChoices.PRESENT)),
            absents=Count('id', filter=Q(statut=Presence.StatutChoices.ABSENT)),
            retards=Count('id', filter=Q(statut=Presence.StatutChoices.RETARD)),
            excuses=Count('id', filter=Q(statut=Presence.StatutChoices.EXCUSE)),
        )
        .order_by('inscription__classe__nom', 'inscription__eleve__nom', 'inscription__eleve__prenom')
    )

    # Calcul du % présence + totaux globaux
    lignes_list = []
    totaux = {'total': 0, 'presents': 0, 'absents': 0, 'retards': 0, 'excuses': 0}
    for row in lignes:
        total = row['total'] or 0
        presents = row['presents'] or 0
        pct = round(presents / total * 100, 1) if total else 0
        lignes_list.append({**row, 'pct_presence': pct})
        totaux['total'] += total
        totaux['presents'] += presents
        totaux['absents'] += row['absents'] or 0
        totaux['retards'] += row['retards'] or 0
        totaux['excuses'] += row['excuses'] or 0

    classes = Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle').order_by('cycle__ordre', 'nom')
    classe_selectionnee = classes.filter(pk=classe_id).first() if classe_id else None

    return render(request, 'presences/bilan_annuel.html', {
        'lignes': lignes_list,
        'totaux': totaux,
        'annee': annee,
        'classes': classes,
        'classe_id': classe_id,
        'classe_selectionnee': classe_selectionnee,
    })


@login_required
def bilan_csv(request):
    """Export CSV du bilan de presences par eleve (memes filtres qu'appel_list)."""
    etab = _get_etab(request)
    annee = _get_annee_courante(etab)

    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    classe_id = request.GET.get('classe', '')

    presences_qs = Presence.objects.select_related(
        'inscription__eleve', 'inscription__classe'
    )
    if annee:
        presences_qs = presences_qs.filter(appel__annee_scolaire=annee)
    if etab:
        presences_qs = presences_qs.filter(appel__classe__etablissement=etab)
    if date_debut:
        presences_qs = presences_qs.filter(appel__date__gte=date_debut)
    if date_fin:
        presences_qs = presences_qs.filter(appel__date__lte=date_fin)
    if classe_id:
        presences_qs = presences_qs.filter(inscription__classe_id=classe_id)

    # Agréger par inscription
    stats = (
        presences_qs
        .values(
            'inscription__eleve__nom',
            'inscription__eleve__prenom',
            'inscription__eleve__matricule',
            'inscription__classe__nom',
        )
        .annotate(
            total=Count('id'),
            presents=Count('id', filter=Q(statut=Presence.StatutChoices.PRESENT)),
            absents=Count('id', filter=Q(statut=Presence.StatutChoices.ABSENT)),
            retards=Count('id', filter=Q(statut=Presence.StatutChoices.RETARD)),
            excuses=Count('id', filter=Q(statut=Presence.StatutChoices.EXCUSE)),
        )
        .order_by('inscription__classe__nom', 'inscription__eleve__nom', 'inscription__eleve__prenom')
    )

    nom_fichier = 'bilan_presences'
    if annee:
        nom_fichier += f'_{annee.libelle}'.replace(' ', '_')
    nom_fichier += '.csv'

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nom', 'Prenom', 'Matricule', 'Classe', 'Total appels', 'Presents', 'Absents', 'Retards', 'Excuses', '% Presence'])

    for row in stats:
        total = row['total'] or 0
        presents = row['presents'] or 0
        pct = round(presents / total * 100, 1) if total else 0
        writer.writerow([
            row['inscription__eleve__nom'],
            row['inscription__eleve__prenom'],
            row['inscription__eleve__matricule'] or '',
            row['inscription__classe__nom'],
            total,
            presents,
            row['absents'] or 0,
            row['retards'] or 0,
            row['excuses'] or 0,
            pct,
        ])

    return response


# ─── QR-code / Pointage ──────────────────────────────���─────────────────────────

@login_required
def qr_eleve_image(request, inscription_id):
    """Retourne le QR code PNG d'un élève (encode son matricule)."""
    import io
    import qrcode
    from django.http import HttpResponse as _HR

    inscription = get_object_or_404(Inscription, pk=inscription_id)
    matricule   = inscription.eleve.matricule or str(inscription.pk)

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(matricule)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    resp = _HR(buf.read(), content_type='image/png')
    resp['Cache-Control'] = 'max-age=3600'
    return resp


@login_required
def cartes_qr_classe(request, classe_id):
    """Page imprimable : cartes QR-code de tous les élèves d'une classe."""
    etab   = _get_etab(request)
    classe = get_object_or_404(Classe, pk=classe_id, etablissement=etab)
    annee  = _get_annee_courante(etab)

    inscriptions = (
        Inscription.objects
        .filter(classe=classe, annee_scolaire=annee)
        .exclude(statut='ABANDON')
        .select_related('eleve')
        .order_by('eleve__nom', 'eleve__prenom')
    )
    return render(request, 'presences/cartes_qr.html', {
        'classe': classe,
        'inscriptions': inscriptions,
        'annee': annee,
    })


@login_required
def qr_scanner(request, appel_id):
    """Page mobile de scan QR : pointe les élèves par caméra."""
    etab  = _get_etab(request)
    appel = get_object_or_404(
        Appel,
        pk=appel_id,
        classe__etablissement=etab,
    )
    if appel.est_clos:
        messages.warning(request, "Cet appel est clôturé — le pointage QR n'est plus possible.")
        return redirect('presences:appel_saisie', appel_id=appel_id)

    # Compteurs initiaux pour le contexte
    nb_presents = appel.presences.filter(statut=Presence.StatutChoices.PRESENT).count()
    nb_total    = appel.presences.count()

    return render(request, 'presences/qr_scanner.html', {
        'appel': appel,
        'nb_presents': nb_presents,
        'nb_total': nb_total,
    })


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST as _require_POST
import json as _json


@login_required
@_require_POST
def api_qr_pointer(request, appel_id):
    """
    API JSON : reçoit un matricule scanné, marque l'élève PRESENT dans l'appel.
    Payload : { "matricule": "ELV-2024-00001" }
    Réponse : { "ok": true, "statut": "PRESENT", "nom": "DIALLO Aminata", "message": "..." }
    """
    etab  = _get_etab(request)
    appel = get_object_or_404(Appel, pk=appel_id, classe__etablissement=etab)

    if appel.est_clos:
        return HttpResponse(
            _json.dumps({'ok': False, 'message': 'Appel clôturé'}),
            content_type='application/json', status=400,
        )

    try:
        data      = _json.loads(request.body)
        matricule = (data.get('matricule') or '').strip()
    except (_json.JSONDecodeError, AttributeError):
        return HttpResponse(
            _json.dumps({'ok': False, 'message': 'Données invalides'}),
            content_type='application/json', status=400,
        )

    if not matricule:
        return HttpResponse(
            _json.dumps({'ok': False, 'message': 'Matricule vide'}),
            content_type='application/json', status=400,
        )

    # Retrouver la présence dans cet appel par matricule
    presence = (
        Presence.objects
        .select_related('inscription__eleve')
        .filter(appel=appel, inscription__eleve__matricule=matricule)
        .first()
    )

    if presence is None:
        return HttpResponse(
            _json.dumps({'ok': False, 'message': f'Élève inconnu dans cette classe ({matricule})'}),
            content_type='application/json', status=404,
        )

    ancien_statut = presence.statut
    eleve = presence.inscription.eleve
    nom   = f"{eleve.nom.upper()} {eleve.prenom}"

    if ancien_statut == Presence.StatutChoices.PRESENT:
        return HttpResponse(
            _json.dumps({'ok': True, 'statut': 'PRESENT', 'nom': nom,
                         'message': f'{nom} déjà pointé présent', 'deja_present': True}),
            content_type='application/json',
        )

    presence.statut = Presence.StatutChoices.PRESENT
    presence.save(update_fields=['statut', 'updated_at'])

    nb_presents = appel.presences.filter(statut=Presence.StatutChoices.PRESENT).count()
    nb_total    = appel.presences.count()

    return HttpResponse(
        _json.dumps({
            'ok': True,
            'statut': 'PRESENT',
            'nom': nom,
            'message': f'{nom} — présent',
            'deja_present': False,
            'nb_presents': nb_presents,
            'nb_total': nb_total,
        }),
        content_type='application/json',
    )
