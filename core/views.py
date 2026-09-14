from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from django.http import HttpResponseForbidden, HttpResponse, JsonResponse

from personnel.models import MembrePersonnel
from inscriptions.models import Eleve, Inscription
from parametres.models import AnneeScolaire, Classe
from finances.models import Paiement


@login_required
def home(request):
    """Tableau de bord principal — adapté au rôle de l'utilisateur."""
    role = request.user.role

    # Rediriger les portails dédiés
    if role == 'PARENT':
        return redirect('core:portail_parent')
    if role == 'ELEVE':
        return redirect('core:portail_eleve')

    annee_courante = AnneeScolaire.objects.filter(
        etablissement=request.user.etablissement, est_courante=True
    ).first() if request.user.etablissement else AnneeScolaire.objects.filter(est_courante=True).first()
    etab = getattr(request.user, 'etablissement', None)

    # ── Base commune (tous les rôles) ─────────────────────────────────
    inscriptions_annee = (
        Inscription.objects.filter(annee_scolaire=annee_courante)
        .exclude(statut='ABANDON').count()
        if annee_courante else 0
    )
    nb_classes = Classe.objects.filter(etablissement=etab, actif=True).count() if etab else 0

    # ── Calendrier scolaire ─────────────────────────────────────────────
    from parametres.models import EvenementCalendrier
    if annee_courante and etab:
        evenements_calendrier = EvenementCalendrier.objects.filter(
            annee_scolaire=annee_courante,
            etablissement=etab,
        ).order_by('date_debut')[:10]
    else:
        evenements_calendrier = []
    
    context = {
        'annee_courante': annee_courante,
        'inscriptions_annee': inscriptions_annee,
        'nb_classes': nb_classes,
        'role': role,
        'evenements_calendrier': evenements_calendrier,
    }

    # ── DIRECTEUR / CENSEUR / SUPER_ADMIN ─────────────────────────────
    if role in ('DIRECTEUR', 'CENSEUR', 'SUPER_ADMIN'):
        from presences.models import Presence, Justification
        from viescolaire.models import SanctionDisciplinaire
        from parametres.models import Cycle
        from django.utils import timezone

        context['total_eleves'] = Eleve.objects.filter(
            inscriptions__annee_scolaire=annee_courante
        ).distinct().count() if annee_courante else Eleve.objects.count()
        context['total_personnel'] = MembrePersonnel.objects.count()

        qs_fin = (
            Paiement.objects.filter(inscription__annee_scolaire=annee_courante)
            if annee_courante else Paiement.objects.none()
        )
        context['encaissements_annee'] = qs_fin.aggregate(total=Sum('montant'))['total'] or 0
        context['nb_paiements'] = qs_fin.count()

        context['nb_absences_aujourd_hui'] = Presence.objects.filter(
            statut='ABSENT', appel__date=timezone.now().date()
        ).count()
        context['nb_justifications_attente'] = Justification.objects.filter(
            statut='EN_ATTENTE',
            inscription__annee_scolaire=annee_courante,
        ).count() if annee_courante else 0
        context['nb_sanctions_recentes'] = SanctionDisciplinaire.objects.filter(
            inscription__annee_scolaire=annee_courante,
            date_sanction__gte=timezone.now().date() - timezone.timedelta(days=7),
        ).count() if annee_courante else 0

        nb_par_cycle = dict(
            Inscription.objects.filter(
                annee_scolaire=annee_courante,
                classe__cycle__etablissement=etab,
            ).exclude(statut='ABANDON')
            .values('classe__cycle_id')
            .annotate(nb=Count('id'))
            .values_list('classe__cycle_id', 'nb')
        ) if (annee_courante and etab) else {}
        cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre') if etab else []
        context['repartition_cycles'] = [
            {'cycle': c, 'nb': nb_par_cycle.get(c.pk, 0)} for c in cycles
        ]

        # ── Widget IA décrochage ──────────────────────────────────────
        from pedagogie.models import RisqueDecrochage
        if annee_courante:
            risques_qs = RisqueDecrochage.objects.filter(
                inscription__annee_scolaire=annee_courante,
            ).select_related('inscription__eleve', 'inscription__classe')

            context['risques_critiques'] = list(
                risques_qs.filter(niveau=RisqueDecrochage.NiveauChoices.CRITIQUE)
                .order_by('-score')[:8]
            )
            context['risques_eleves'] = list(
                risques_qs.filter(niveau=RisqueDecrochage.NiveauChoices.ELEVE)
                .order_by('-score')[:8]
            )
            context['nb_risques_critiques'] = risques_qs.filter(
                niveau=RisqueDecrochage.NiveauChoices.CRITIQUE
            ).count()
            context['nb_risques_eleves'] = risques_qs.filter(
                niveau=RisqueDecrochage.NiveauChoices.ELEVE
            ).count()
            context['nb_risques_moderes'] = risques_qs.filter(
                niveau=RisqueDecrochage.NiveauChoices.MODERE
            ).count()
        else:
            context['risques_critiques'] = []
            context['risques_eleves'] = []
            context['nb_risques_critiques'] = 0
            context['nb_risques_eleves'] = 0
            context['nb_risques_moderes'] = 0

    # ── ENSEIGNANT ────────────────────────────────────────────────────
    elif role == 'ENSEIGNANT':
        from pedagogie.models import Enseignement, Evaluation, Resultat

        context['nb_issements'] = Enseignement.objects.filter(
            annee_scolaire=annee_courante, est_actif=True
        ).count() if annee_courante else 0

        evaluations_recentes = []
        if annee_courante:
            try:
                evaluations_recentes = (
                    Evaluation.objects
                    .filter(trimestre__annee_scolaire=annee_courante)
                    .select_related('trimestre', 'type_evaluation')
                    .order_by('-date_planifiee')[:5]
                )
            except Exception:
                pass
        context['evaluations_recentes'] = evaluations_recentes

        context['nb_evaluations_annee'] = 0
        if annee_courante:
            try:
                context['nb_evaluations_annee'] = Evaluation.objects.filter(
                    trimestre__annee_scolaire=annee_courante
                ).count()
            except Exception:
                pass

        context['nb_eleves_sans_notes'] = 0
        if annee_courante:
            try:
                context['nb_eleves_sans_notes'] = Resultat.objects.filter(
                    trimestre__annee_scolaire=annee_courante,
                    moyenne__isnull=True,
                ).values('inscription').distinct().count()
            except Exception:
                pass

    # ── COMPTABLE ─────────────────────────────────────────────────────
    elif role == 'COMPTABLE':
        from django.utils import timezone

        aujourd_hui = timezone.now().date()
        debut_mois = aujourd_hui.replace(day=1)

        paiements_aujourd_hui = (
            Paiement.objects.filter(date_paiement=aujourd_hui)
            .select_related('inscription__eleve')
            .order_by('-created_at')[:10]
        )
        context['paiements_aujourd_hui'] = paiements_aujourd_hui
        context['total_aujourd_hui'] = (
            Paiement.objects.filter(date_paiement=aujourd_hui)
            .aggregate(t=Sum('montant'))['t'] or 0
        )
        context['total_mois'] = (
            Paiement.objects.filter(
                date_paiement__gte=debut_mois,
                inscription__annee_scolaire=annee_courante,
            ).aggregate(t=Sum('montant'))['t'] or 0
        ) if annee_courante else 0
        context['encaissements_annee'] = (
            Paiement.objects.filter(inscription__annee_scolaire=annee_courante)
            .aggregate(t=Sum('montant'))['t'] or 0
        ) if annee_courante else 0
        context['nb_redevables'] = (
            Inscription.objects.filter(annee_scolaire=annee_courante)
            .exclude(statut='ABANDON')
            .exclude(paiements__isnull=False)
            .distinct().count()
        ) if annee_courante else 0

    # ── SECRETAIRE ────────────────────────────────────────────────────
    elif role == 'SECRETAIRE':
        from django.utils import timezone
        from documents.models import Document

        context['total_eleves'] = Eleve.objects.count()
        context['inscriptions_recentes'] = (
            Inscription.objects
            .filter(annee_scolaire=annee_courante)
            .select_related('eleve', 'classe')
            .order_by('-created_at')[:8]
        ) if annee_courante else []
        context['nb_docs_semaine'] = Document.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()

    # ── AVS ───────────────────────────────────────────────────────────
    elif role == 'AVS':
        from presences.models import Presence, Justification, Appel
        from viescolaire.models import SanctionDisciplinaire
        from django.utils import timezone

        aujourd_hui = timezone.now().date()
        context['nb_absences_aujourd_hui'] = Presence.objects.filter(
            statut='ABSENT', appel__date=aujourd_hui
        ).count()
        context['nb_retards_aujourd_hui'] = Presence.objects.filter(
            statut='RETARD', appel__date=aujourd_hui
        ).count()
        context['nb_appels_aujourd_hui'] = Appel.objects.filter(date=aujourd_hui).count()
        context['nb_justifications_attente'] = Justification.objects.filter(
            statut='EN_ATTENTE',
            inscription__annee_scolaire=annee_courante,
        ).count() if annee_courante else 0
        context['sanctions_recentes'] = (
            SanctionDisciplinaire.objects
            .filter(inscription__annee_scolaire=annee_courante)
            .select_related('inscription__eleve', 'type_sanction')
            .order_by('-date_sanction')[:5]
        ) if annee_courante else []

    return render(request, 'core/home.html', context)


@login_required
def recherche_globale(request):
    """Recherche globale : élèves, personnel, classes. Retourne un partial HTMX."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return render(request, 'core/partials/recherche_resultats.html', {'resultats': [], 'q': q})

    etab = getattr(request.user, 'etablissement', None)

    eleves = (
        Eleve.objects.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(matricule__icontains=q)
        ).only('id', 'nom', 'prenom', 'matricule')[:6]
    )

    personnel = (
        MembrePersonnel.objects.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(matricule__icontains=q) | Q(fonction__icontains=q)
        ).only('id', 'nom', 'prenom', 'matricule', 'fonction')[:6]
    )

    classes_qs = Classe.objects.filter(nom__icontains=q).only('id', 'nom', 'niveau')
    if etab:
        classes_qs = classes_qs.filter(etablissement=etab)
    classes = classes_qs[:6]

    resultats = [
        {'categorie': 'Élèves', 'icone': 'eleve', 'items': [
            {'label': f"{e.nom.upper()} {e.prenom}", 'sub': e.matricule, 'url': f"/inscriptions/eleve/{e.pk}/"}
            for e in eleves
        ]},
        {'categorie': 'Personnel', 'icone': 'personnel', 'items': [
            {'label': f"{m.nom.upper()} {m.prenom}", 'sub': m.fonction or m.matricule, 'url': f"/personnel/{m.pk}/"}
            for m in personnel
        ]},
        {'categorie': 'Classes', 'icone': 'classe', 'items': [
            {'label': c.nom, 'sub': c.get_niveau_display() if hasattr(c, 'get_niveau_display') else c.niveau, 'url': "/parametres/classes/"}
            for c in classes
        ]},
    ]
    # Ne garder que les catégories avec des résultats
    resultats = [r for r in resultats if r['items']]

    return render(request, 'core/partials/recherche_resultats.html', {'resultats': resultats, 'q': q})


@login_required
def audit_log_list(request):
    """Liste du journal d'audit avec filtres."""
    if request.user.role not in ['SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR']:
        return render(request, 'core/access_denied.html', {
            'message': "Vous n'avez pas accès au journal d'audit."
        })
    
    from core.models import AuditLog
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    query = request.GET.get('q', '')
    app_filter = request.GET.get('app', '')
    action_filter = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    page_number = request.GET.get('page', 1)
    
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    
    if query:
        logs = logs.filter(
            Q(object_repr__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query)
        )
    
    if app_filter:
        logs = logs.filter(app_label=app_filter)
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    apps = AuditLog.objects.values_list('app_label', flat=True).distinct()
    
    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/audit_log_list.html', {
        'logs': page_obj,
        'page_obj': page_obj,
        'query': query,
        'app_filter': app_filter,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'apps': sorted(set(apps)),
    })


@login_required
def audit_log_pdf(request):
    """Export PDF du journal d'audit avec filtres."""
    if request.user.role not in ['SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR']:
        return render(request, 'core/access_denied.html', {
            'message': "Vous n'avez pas accès au journal d'audit."
        })

    from core.models import AuditLog
    from django.db.models import Q
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from datetime import datetime

    try:
        from weasyprint import HTML as WeasyHTML
    except ImportError:
        return HttpResponse("WeasyPrint non installé — impossible de générer le PDF.", status=503)

    query = request.GET.get('q', '')
    app_filter = request.GET.get('app', '')
    action_filter = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    logs = AuditLog.objects.select_related('user').order_by('-timestamp')

    if query:
        logs = logs.filter(
            Q(object_repr__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query)
        )

    if app_filter:
        logs = logs.filter(app_label=app_filter)

    if action_filter:
        logs = logs.filter(action=action_filter)

    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)

    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    etab = getattr(request.user, 'etablissement', None)

    from core.utils import get_etablissement_context
    etab_ctx = get_etablissement_context(etab, request=request)

    html_string = render_to_string('core/pdf/audit_log.html', {
        'logs': list(logs),
        'now': datetime.now(),
        'query': query,
        'app_filter': app_filter,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        **etab_ctx,
    }, request=request)

    pdf = WeasyHTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    nom_fichier = f"journal_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
    return response


@login_required
def audit_log_detail(request, pk):
    """Détails d'une entrée d'audit."""
    if request.user.role not in ['SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR']:
        return render(request, 'core/access_denied.html', {
            'message': "Vous n'avez pas accès au journal d'audit."
        })
    
    from core.models import AuditLog
    from django.shortcuts import get_object_or_404
    
    log = get_object_or_404(AuditLog, pk=pk)
    
    return render(request, 'core/audit_log_detail.html', {
        'log': log,
    })


# ── Portail Parent ────────────────────────────────────────────────────────────

@login_required
def notifications_list(request):
    """Liste des notifications de l'utilisateur connecté."""
    from core.models import Notification
    notifications = Notification.objects.filter(
        destinataire=request.user
    ).order_by('-created_at')[:50]
    nb_non_lues = Notification.objects.filter(
        destinataire=request.user, lu=False
    ).count()
    context = {
        'notifications': notifications,
        'nb_non_lues': nb_non_lues,
    }
    if request.GET.get('_partial') == 'header':
        return render(request, 'core/partials/notifications_header.html', context)
    return render(request, 'core/notifications.html', context)


@login_required
def notification_marquer_lu(request, pk):
    """Marque une notification comme lue (HTMX)."""
    from core.models import Notification
    from django.shortcuts import get_object_or_404
    from uuid import UUID
    
    try:
        if isinstance(pk, UUID):
            pk_uuid = pk
        else:
            pk_uuid = UUID(str(pk))
        notif = get_object_or_404(Notification, pk=pk_uuid, destinataire=request.user)
    except (ValueError, TypeError):
        try:
            pk_int = int(pk)
            notif = get_object_or_404(Notification, pk=pk_int, destinataire=request.user)
        except (ValueError, TypeError):
            from django.http import Http404
            raise Http404("Notification non trouvée")
    
    notif.lu = True
    notif.save(update_fields=['lu'])
    response = render(request, 'core/partials/notification_item.html', {'notif': notif})
    response['HX-Trigger'] = 'notificationsUpdated'
    return response


@login_required
def notifications_marquer_tout_lu(request):
    """Marque toutes les notifications comme lues."""
    from core.models import Notification
    from django.views.decorators.http import require_POST
    Notification.objects.filter(destinataire=request.user, lu=False).update(lu=True)
    return redirect('core:notifications_list')


@login_required
def notifications_badge(request):
    """Partial HTMX — badge avec le nombre de notifications non lues."""
    from core.models import Notification
    nb = Notification.objects.filter(
        destinataire=request.user, lu=False
    ).count()
    return render(request, 'core/partials/notifications_badge.html', {'nb': nb})


@login_required
def portail_parent(request):
    """Tableau de bord pour le rôle PARENT (PWA-ready)."""
    if request.user.role != 'PARENT':
        return HttpResponseForbidden("Accès réservé aux parents.")

    from presences.models import Presence
    from pedagogie.models import MoyenneGenerale, CahierTextes
    from finances.models import Paiement
    from django.utils import timezone

    today = timezone.now().date()
    annee = AnneeScolaire.objects.filter(
        etablissement=request.user.etablissement, est_courante=True
    ).first()

    eleves = request.user.eleves_lies.all().select_related()

    enfants = []
    for eleve in eleves:
        inscription = (
            Inscription.objects
            .filter(eleve=eleve, annee_scolaire=annee)
            .select_related('classe', 'statut_eleve')
            .first()
        ) if annee else None

        derniere_mg = None
        if inscription and annee:
            derniere_mg = (
                MoyenneGenerale.objects
                .filter(inscription=inscription)
                .select_related('trimestre')
                .order_by('-trimestre__numero')
                .first()
            )

        nb_absences_recentes = 0
        if inscription:
            depuis = today - timezone.timedelta(days=30)
            nb_absences_recentes = Presence.objects.filter(
                inscription=inscription,
                statut='ABSENT',
                appel__date__gte=depuis,
            ).count()

        total_paye = (
            Paiement.objects.filter(inscription=inscription)
            .aggregate(total=Sum('montant'))['total'] or 0
        ) if inscription else 0

        # Devoirs à venir (de la classe de l'élève, non encore échus)
        devoirs_a_venir = []
        if inscription:
            devoirs_a_venir = list(
                CahierTextes.objects.filter(
                    enseignement__classe=inscription.classe,
                    enseignement__annee_scolaire=annee,
                    date_remise_devoirs__gte=today,
                    devoirs__gt='',
                ).select_related('enseignement__matiere')
                .order_by('date_remise_devoirs')[:5]
            )

        enfants.append({
            'eleve': eleve,
            'inscription': inscription,
            'derniere_mg': derniere_mg,
            'nb_absences_recentes': nb_absences_recentes,
            'total_paye': total_paye,
            'devoirs_a_venir': devoirs_a_venir,
        })

    return render(request, 'core/portail_parent.html', {
        'enfants': enfants,
        'annee': annee,
    })


@login_required
def portail_parent_bulletins(request):
    """Page bulletins PWA pour les parents."""
    if request.user.role != 'PARENT':
        return HttpResponseForbidden("Accès réservé aux parents.")

    from bulletins.models import Bulletin
    from pedagogie.models import MoyenneGenerale

    annee = AnneeScolaire.objects.filter(
        etablissement=request.user.etablissement, est_courante=True
    ).first()

    eleves = request.user.eleves_lies.all().select_related()

    enfants = []
    for eleve in eleves:
        inscription = (
            Inscription.objects
            .filter(eleve=eleve, annee_scolaire=annee)
            .select_related('classe')
            .first()
        ) if annee else None

        bulletins = []
        if inscription:
            bulletins_qs = (
                Bulletin.objects
                .filter(inscription=inscription, est_publie=True)
                .select_related('trimestre')
                .order_by('-trimestre__numero')
            )
            for b in bulletins_qs:
                mg = MoyenneGenerale.objects.filter(
                    inscription=inscription,
                    trimestre=b.trimestre,
                ).first()
                bulletins.append({'bulletin': b, 'mg': mg})

        if inscription or bulletins:
            enfants.append({
                'eleve': eleve,
                'inscription': inscription,
                'bulletins': bulletins,
            })

    return render(request, 'core/portail_parent_bulletins.html', {
        'enfants': enfants,
        'annee': annee,
    })


@login_required
def portail_parent_notifications(request):
    """Page notifications PWA pour les parents."""
    if request.user.role != 'PARENT':
        return HttpResponseForbidden("Accès réservé aux parents.")

    from core.models import Notification

    if request.method == 'POST' and request.POST.get('action') == 'tout_lu':
        Notification.objects.filter(destinataire=request.user, lu=False).update(lu=True)
        return redirect('core:portail_parent_notifications')

    qs = Notification.objects.filter(destinataire=request.user)
    nb_non_lues = qs.filter(lu=False).count()
    qs.filter(lu=False).update(lu=True)
    notifications = qs.order_by('-created_at')[:50]

    return render(request, 'core/portail_parent_notifications.html', {
        'notifications': notifications,
        'nb_non_lues': nb_non_lues,
    })


# ── Portail Élève ─────────────────────────────────────────────────────────────

@login_required
def portail_eleve(request):
    """Tableau de bord pour le rôle ELEVE."""
    if request.user.role != 'ELEVE':
        return HttpResponseForbidden("Accès réservé aux élèves.")

    from presences.models import Presence
    from pedagogie.models import MoyenneGenerale
    from finances.models import Paiement
    from django.utils import timezone

    annee = AnneeScolaire.objects.filter(
        etablissement=request.user.etablissement, est_courante=True
    ).first()

    eleve = request.user.eleves_lies.first()
    if not eleve:
        return render(request, 'core/portail_eleve.html', {
            'erreur': "Aucun élève associé à votre compte. Contactez l'administration.",
            'annee': annee,
        })

    inscription = (
        Inscription.objects
        .filter(eleve=eleve, annee_scolaire=annee)
        .select_related('classe', 'statut_eleve')
        .first()
    ) if annee else None

    # Moyennes par trimestre
    moyennes = []
    if inscription:
        moyennes = (
            MoyenneGenerale.objects
            .filter(inscription=inscription)
            .select_related('trimestre')
            .order_by('trimestre__numero')
        )

    # Absences du mois
    nb_absences = 0
    nb_retards = 0
    if inscription:
        depuis = timezone.now().date() - timezone.timedelta(days=30)
        nb_absences = Presence.objects.filter(
            inscription=inscription, statut='ABSENT', appel__date__gte=depuis
        ).count()
        nb_retards = Presence.objects.filter(
            inscription=inscription, statut='RETARD', appel__date__gte=depuis
        ).count()

    # Paiements
    paiements = []
    if inscription:
        paiements = (
            Paiement.objects
            .filter(inscription=inscription)
            .order_by('-date_paiement')[:5]
        )

    return render(request, 'core/portail_eleve.html', {
        'eleve': eleve,
        'inscription': inscription,
        'moyennes': moyennes,
        'nb_absences': nb_absences,
        'nb_retards': nb_retards,
        'paiements': paiements,
        'annee': annee,
    })


@login_required
def sms_configuration(request):
    """Page de configuration et test du modem GSM (SUPER_ADMIN / DIRECTEUR uniquement)."""
    if request.user.role not in ('SUPER_ADMIN', 'DIRECTEUR'):
        return HttpResponseForbidden("Accès réservé aux administrateurs.")

    from core.sms import tester_modem, get_sms_val
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    env_file = BASE_DIR / '.env'

    config = {
        'SMS_ENABLED':        get_sms_val('SMS_ENABLED'),
        'SMS_BACKEND':        get_sms_val('SMS_BACKEND'),
        'SMS_HTTP_URL':       get_sms_val('SMS_HTTP_URL'),
        'SMS_HTTP_USER':      get_sms_val('SMS_HTTP_USER'),
        'SMS_HTTP_PASSWORD':  get_sms_val('SMS_HTTP_PASSWORD'),
        'SMS_HTTP_TIMEOUT':   get_sms_val('SMS_HTTP_TIMEOUT'),
        'SMS_MODEM_PORT':     get_sms_val('SMS_MODEM_PORT'),
        'SMS_MODEM_BAUD':     get_sms_val('SMS_MODEM_BAUD'),
        'SMS_MODEM_TIMEOUT':  get_sms_val('SMS_MODEM_TIMEOUT'),
    }

    webhook_url = request.build_absolute_uri('/communication/webhook/sms/')

    test_result = None

    SMS_VARS = [
        'SMS_ENABLED',
        'SMS_BACKEND',
        'SMS_HTTP_URL',
        'SMS_HTTP_USER',
        'SMS_HTTP_PASSWORD',
        'SMS_HTTP_TIMEOUT',
        'SMS_MODEM_PORT',
        'SMS_MODEM_BAUD',
        'SMS_MODEM_TIMEOUT',
    ]

    if request.method == 'POST':
        if 'sauvegarder' in request.POST:
            form_values = {
                'SMS_ENABLED':       request.POST.get('SMS_ENABLED', 'False'),
                'SMS_BACKEND':       request.POST.get('SMS_BACKEND', 'http'),
                'SMS_HTTP_URL':      request.POST.get('SMS_HTTP_URL', '').strip(),
                'SMS_HTTP_USER':     request.POST.get('SMS_HTTP_USER', 'admin'),
                'SMS_HTTP_PASSWORD': request.POST.get('SMS_HTTP_PASSWORD', ''),
                'SMS_HTTP_TIMEOUT':  request.POST.get('SMS_HTTP_TIMEOUT', '10'),
                'SMS_MODEM_PORT':    request.POST.get('SMS_MODEM_PORT', 'COM3'),
                'SMS_MODEM_BAUD':    request.POST.get('SMS_MODEM_BAUD', '9600'),
                'SMS_MODEM_TIMEOUT': request.POST.get('SMS_MODEM_TIMEOUT', '10'),
            }

            try:
                found = {v: False for v in SMS_VARS}
                if env_file.exists():
                    raw = env_file.read_text(encoding='utf-8')
                    lines = raw.split('\n')
                else:
                    lines = []

                new_lines = []
                for line in lines:
                    stripped = line.strip()
                    matched = False
                    for var in SMS_VARS:
                        prefix = var + '='
                        if stripped.startswith(prefix) or stripped.startswith(prefix.lower()):
                            new_lines.append(f'{var}={form_values[var]}')
                            found[var] = True
                            matched = True
                            break
                    if not matched:
                        new_lines.append(line)

                for var in SMS_VARS:
                    if not found[var]:
                        if var == 'SMS_HTTP_URL' and not any(l.strip().startswith('#') and 'HTTP' in l for l in new_lines):
                            new_lines.append(f'# Backend HTTP — app Android "SMS Gateway"')
                        new_lines.append(f'{var}={form_values[var]}')

                env_file.write_text('\n'.join(new_lines), encoding='utf-8')

                from core.sms import set_sms_config_runtime
                set_sms_config_runtime(**form_values)

                messages.success(request, "Configuration SMS enregistrée et appliquée immédiatement (sans redémarrage).")
                return redirect('core:sms_configuration')
            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement : {e}")

        elif 'tester' in request.POST:
            test_result = tester_modem()

        elif 'envoyer_test' in request.POST:
            numero = request.POST.get('numero_test', '').strip()
            if numero:
                from core.sms import envoyer_sms
                succes, motif = envoyer_sms(numero, "Test YELEN SCHOOL — message de vérification modem.")
                if succes:
                    messages.success(request, f"SMS de test envoyé à {numero}.")
                else:
                    messages.error(request, f"Échec de l'envoi du SMS à {numero} — {motif}")
            else:
                messages.warning(request, "Veuillez saisir un numéro de téléphone.")
            return redirect('core:sms_configuration')

    return render(request, 'core/sms_configuration.html', {
        'config': config,
        'test_result': test_result,
        'webhook_url': webhook_url,
    })


@login_required
def reunion_parents(request):
    """Envoi SMS de convocation à une réunion parents-élèves."""
    if request.user.role not in ('SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR', 'SECRETAIRE'):
        return HttpResponseForbidden("Accès non autorisé.")

    from etablissements.models import Etablissement
    etab = getattr(request.user, 'etablissement', None)

    if request.method == 'POST':
        date   = request.POST.get('date', '').strip()
        heure  = request.POST.get('heure', '').strip()
        lieu   = request.POST.get('lieu', '').strip()
        objet  = request.POST.get('objet', '').strip()
        cibles = request.POST.get('cibles', 'tous')  # 'tous' ou uuid de classe

        if not (date and heure and lieu and objet):
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
        else:
            from inscriptions.models import Eleve, Inscription
            from parametres.models import AnneeScolaire

            annee = AnneeScolaire.objects.filter(est_courante=True).first()

            # Construire le queryset d'élèves selon la cible
            eleves_qs = Eleve.objects.filter(is_active=True)
            if etab:
                eleves_qs = eleves_qs.filter(inscriptions__classe__etablissement=etab).distinct()
            if cibles != 'tous' and annee:
                eleves_qs = eleves_qs.filter(
                    inscriptions__classe_id=cibles,
                    inscriptions__annee_scolaire=annee,
                ).distinct()
            elif annee:
                eleves_qs = eleves_qs.filter(inscriptions__annee_scolaire=annee).distinct()

            # Collecter les numéros uniques (telephone_parent ou tuteur ou urgence)
            numeros_vus = set()
            numeros = []
            for eleve in eleves_qs.only('telephone_parent', 'tuteur_telephone', 'telephone_urgence'):
                numero = (
                    eleve.telephone_parent
                    or eleve.tuteur_telephone
                    or eleve.telephone_urgence
                    or ''
                ).strip()
                if numero and numero not in numeros_vus:
                    numeros_vus.add(numero)
                    numeros.append(numero)

            from core.sms import get_sms_val
            if get_sms_val('SMS_ENABLED') and numeros:
                from core.tasks import envoyer_sms_async
                etab_nom = etab.nom if etab else 'YELEN SCHOOL'
                msg = (
                    f"Convocation reunion parents : le {date} a {heure}, "
                    f"{lieu}. Objet : {objet}. — {etab_nom}"
                )
                for numero in numeros:
                    envoyer_sms_async(numero, msg)

            messages.success(
                request,
                f"{len(numeros)} SMS de convocation envoyé(s) pour la réunion du {date}."
                if numeros else
                "Aucun numéro de parent trouvé pour les élèves sélectionnés."
            )
            return redirect('core:reunion_parents')

    # Charger les classes pour le filtre
    classes = []
    if etab:
        from parametres.models import Classe, AnneeScolaire
        annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
        if annee:
            classes = Classe.objects.filter(etablissement=etab).order_by('cycle__ordre', 'nom')

    return render(request, 'core/reunion_parents.html', {
        'classes': classes,
    })


@login_required
@require_POST
def risque_recalculer(request):
    """Déclenche le recalcul des scores de décrochage pour l'année courante."""
    if request.user.role not in ('SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    etab = getattr(request.user, 'etablissement', None)
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    if not annee:
        messages.warning(request, "Aucune année scolaire courante — recalcul impossible.")
        return redirect('core:home')

    from inscriptions.models import Inscription
    from pedagogie.models import RisqueDecrochage
    from pedagogie.utils_ia import calculer_score_risque

    qs = (
        Inscription.objects
        .filter(annee_scolaire=annee)
        .exclude(statut='ABANDON')
        .select_related('eleve', 'classe')
    )

    created = updated = erreurs = 0
    for inscription in qs.iterator(chunk_size=100):
        try:
            score, facteurs = calculer_score_risque(inscription, annee)
            niveau = RisqueDecrochage.niveau_pour_score(score)
            _, is_new = RisqueDecrochage.objects.update_or_create(
                inscription=inscription,
                defaults={'score': score, 'niveau': niveau, 'facteurs': facteurs},
            )
            if is_new:
                created += 1
            else:
                updated += 1
        except Exception:
            erreurs += 1

    total = created + updated
    if erreurs:
        messages.warning(
            request,
            f"Recalcul terminé : {total} élève(s) traité(s), {erreurs} erreur(s)."
        )
    else:
        messages.success(
            request,
            f"Recalcul terminé : {total} score(s) mis à jour."
        )
    return redirect('core:home')


# ─────────────────────────────────────────────────────────────────────────────
# PWA — Progressive Web App (Portail Parent)
# ─────────────────────────────────────────────────────────────────────────────

def app_manifest(request):
    """Web App Manifest pour l'application principale YELEN SCHOOL (staff)."""
    manifest = {
        "name": "YELEN SCHOOL",
        "short_name": "YELEN",
        "description": "Système de gestion scolaire — Burkina Faso",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#0A1628",
        "theme_color": "#00A86B",
        "lang": "fr",
        "icons": [
            {"src": "/pwa/icon/192/", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any maskable"},
            {"src": "/pwa/icon/512/", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"},
        ],
        "categories": ["education", "productivity"],
    }
    return JsonResponse(manifest)


def app_service_worker(request):
    """Service Worker de l'application principale — cache les assets, page offline en fallback."""
    sw = """
const APP_CACHE = 'yelen-app-v1';
const PRECACHE = [
  '/offline/',
  '/static/css/yelen.css',
  '/static/js/htmx.min.js',
];
const STATIC_ORIGIN = self.location.origin;
const BYPASS = ['/accounts/', '/admin/', '/api/', '/sw.js'];

// ── Install : pré-cache les assets critiques ──
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(APP_CACHE)
      .then(c => c.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

// ── Activate : purge les anciens caches ──
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== APP_CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ──
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== STATIC_ORIGIN) return;
  if (BYPASS.some(p => url.pathname.startsWith(p))) return;

  // Assets statiques : Cache First
  if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const network = fetch(e.request).then(r => {
          if (r.ok) caches.open(APP_CACHE).then(c => c.put(e.request, r.clone()));
          return r;
        });
        return cached || network;
      })
    );
    return;
  }

  // Pages : Network First, fallback cache, fallback /offline/
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r.ok) caches.open(APP_CACHE).then(c => c.put(e.request, r.clone()));
        return r;
      })
      .catch(() =>
        caches.match(e.request)
          .then(cached => cached || caches.match('/offline/'))
      )
  );
});
"""
    return HttpResponse(sw.strip(), content_type='application/javascript')


def offline_page(request):
    """Page affichée par le Service Worker quand le serveur est inaccessible."""
    return render(request, 'core/offline.html')


def pwa_manifest(request):
    """Web App Manifest pour le portail parent (installable sur Android)."""
    manifest = {
        "name": "YELEN SCHOOL — Portail Parent",
        "short_name": "YELEN Parent",
        "description": "Suivez la scolarité de vos enfants en temps réel",
        "start_url": "/portail/parent/",
        "scope": "/portail/parent/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0A1628",
        "theme_color": "#00A86B",
        "lang": "fr",
        "icons": [
            {"src": "/pwa/icon/192/", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any"},
            {"src": "/pwa/icon/512/", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any"},
        ],
    }
    return JsonResponse(manifest)


def pwa_icon(request, size):
    """Icône SVG de l'application PWA."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}">'
        f'<rect width="{size}" height="{size}" rx="{size // 5}" fill="#0A1628"/>'
        f'<text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" '
        f'font-family="Outfit,Arial,sans-serif" font-weight="700" '
        f'font-size="{size // 2}" fill="#00A86B">Y</text>'
        f'</svg>'
    )
    return HttpResponse(svg, content_type='image/svg+xml')


def pwa_service_worker(request):
    """Service Worker — cache le portail parent pour un accès hors ligne."""
    sw = (
        "const CACHE='yelen-parent-v2';\n"
        "const PRECACHE=['/portail/parent/','/static/css/yelen.css','/static/js/pwa.js'];\n"
        "self.addEventListener('install',e=>{"
        "e.waitUntil(caches.open(CACHE).then(c=>c.addAll(PRECACHE)).then(()=>self.skipWaiting()));});\n"
        "self.addEventListener('activate',e=>{"
        "e.waitUntil(caches.keys()"
        ".then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))"
        ".then(()=>self.clients.claim()));});\n"
        "self.addEventListener('fetch',e=>{"
        "if(e.request.method!=='GET')return;"
        "const u=new URL(e.request.url);"
        "if(u.pathname.startsWith('/accounts/')||u.pathname.startsWith('/api/'))return;"
        "e.respondWith(fetch(e.request).then(r=>{"
        "if(r.ok){const c=r.clone();caches.open(CACHE).then(ca=>ca.put(e.request,c));}"
        "return r;}).catch(()=>caches.match(e.request)"
        ".then(cached=>cached||caches.match('/portail/parent/'))));});\n"
    )
    return HttpResponse(sw, content_type='application/javascript')


# ─────────────────────────────────────────────────────────────────────────────
# Assistant IA Chatbot Directeur
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def chatbot(request):
    """Interface de l'assistant IA — moteur de requêtes local, sans API externe."""
    session_key = 'chatbot_display'
    display_history = request.session.get(session_key, [])

    if request.method == 'POST':
        if request.POST.get('action') == 'clear':
            request.session.pop(session_key, None)
            return redirect('core:chatbot')

        user_message = request.POST.get('message', '').strip()
        if not user_message:
            return redirect('core:chatbot')

        from core.chatbot import chat
        response_text, display_history = chat(display_history, user_message)

        request.session[session_key] = display_history
        request.session.modified = True

        if request.headers.get('HX-Request'):
            return render(request, 'core/partials/chatbot_messages.html', {
                'display_history': display_history,
            })
        return redirect('core:chatbot')

    return render(request, 'core/chatbot.html', {
        'display_history': display_history,
    })


# ── HEALTHCHECK ─────────────────────────────────────────────────────────────

@never_cache
def health_check(request):
    """Endpoint de healthcheck pour le load balancer / monitoring Docker."""
    from django.db import connections

    health = {'status': 'ok', 'version': '1.0.0'}

    # Vérification base de données
    db_ok = False
    try:
        conn = connections['default']
        conn.cursor()
        db_ok = True
    except Exception:
        pass
    health['database'] = 'ok' if db_ok else 'error'

    # Vérification cache Redis
    cache_ok = False
    try:
        from django.core.cache import cache
        cache.set('_health_check', 1, 5)
        cache_ok = cache.get('_health_check') == 1
    except Exception:
        pass
    health['cache'] = 'ok' if cache_ok else 'error'

    status_code = 200 if (db_ok and cache_ok) else 503
    return JsonResponse(health, status=status_code)
