from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.views.decorators.http import require_POST

from django.http import HttpResponseForbidden

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

    # ── ENSEIGNANT ────────────────────────────────────────────────────
    elif role == 'ENSEIGNANT':
        from pedagogie.models import Enseignement, Evaluation, Resultat

        context['nb_enseignements'] = Enseignement.objects.filter(
            annee_scolaire=annee_courante, est_actif=True
        ).count() if annee_courante else 0

        evaluations_recentes = (
            Evaluation.objects
            .filter(annee_scolaire=annee_courante)
            .select_related('classe', 'matiere')
            .order_by('-date_evaluation')[:5]
        ) if annee_courante else []
        context['evaluations_recentes'] = evaluations_recentes

        context['nb_evaluations_annee'] = Evaluation.objects.filter(
            annee_scolaire=annee_courante
        ).count() if annee_courante else 0

        context['nb_eleves_sans_notes'] = Resultat.objects.filter(
            trimestre__annee_scolaire=annee_courante,
            note_1__isnull=True, note_2__isnull=True,
        ).values('inscription').distinct().count() if annee_courante else 0

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
    return render(request, 'core/notifications.html', {
        'notifications': notifications,
        'nb_non_lues': nb_non_lues,
    })


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
    return render(request, 'core/partials/notification_item.html', {'notif': notif})


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
    """Tableau de bord pour le rôle PARENT."""
    if request.user.role != 'PARENT':
        return HttpResponseForbidden("Accès réservé aux parents.")

    from presences.models import Presence
    from pedagogie.models import MoyenneGenerale
    from finances.models import Paiement
    from django.utils import timezone

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

        # Dernière moyenne générale
        derniere_mg = None
        if inscription and annee:
            derniere_mg = (
                MoyenneGenerale.objects
                .filter(inscription=inscription)
                .select_related('trimestre')
                .order_by('-trimestre__numero')
                .first()
            )

        # Absences récentes (30 derniers jours)
        nb_absences_recentes = 0
        if inscription:
            depuis = timezone.now().date() - timezone.timedelta(days=30)
            nb_absences_recentes = Presence.objects.filter(
                inscription=inscription,
                statut='ABSENT',
                appel__date__gte=depuis,
            ).count()

        # Solde financier
        total_paye = (
            Paiement.objects
            .filter(inscription=inscription)
            .aggregate(total=Sum('montant'))['total'] or 0
        ) if inscription else 0

        enfants.append({
            'eleve': eleve,
            'inscription': inscription,
            'derniere_mg': derniere_mg,
            'nb_absences_recentes': nb_absences_recentes,
            'total_paye': total_paye,
        })

    return render(request, 'core/portail_parent.html', {
        'enfants': enfants,
        'annee': annee,
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

    from django.conf import settings
    from core.sms import tester_modem
    import os
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    env_file = BASE_DIR / '.env'

    backend = getattr(settings, 'SMS_BACKEND', 'http')
    config = {
        'SMS_ENABLED':        getattr(settings, 'SMS_ENABLED',        False),
        'SMS_BACKEND':        backend,
        'SMS_HTTP_URL':       getattr(settings, 'SMS_HTTP_URL',       ''),
        'SMS_HTTP_USER':      getattr(settings, 'SMS_HTTP_USER',      'admin'),
        'SMS_HTTP_PASSWORD':  getattr(settings, 'SMS_HTTP_PASSWORD', ''),
        'SMS_HTTP_TIMEOUT':   getattr(settings, 'SMS_HTTP_TIMEOUT',   10),
        'SMS_MODEM_PORT':     getattr(settings, 'SMS_MODEM_PORT',     'COM3'),
        'SMS_MODEM_BAUD':     getattr(settings, 'SMS_MODEM_BAUD',    9600),
        'SMS_MODEM_TIMEOUT':  getattr(settings, 'SMS_MODEM_TIMEOUT',  10),
    }

    test_result = None

    if request.method == 'POST':
        if 'sauvegarder' in request.POST:
            sms_enabled = request.POST.get('SMS_ENABLED', 'False')
            sms_backend = request.POST.get('SMS_BACKEND', 'http')
            sms_http_url = request.POST.get('SMS_HTTP_URL', '').strip()
            sms_http_user = request.POST.get('SMS_HTTP_USER', 'admin')
            sms_http_password = request.POST.get('SMS_HTTP_PASSWORD', '')
            sms_http_timeout = request.POST.get('SMS_HTTP_TIMEOUT', '10')
            sms_modem_port = request.POST.get('SMS_MODEM_PORT', 'COM3')
            sms_modem_baud = request.POST.get('SMS_MODEM_BAUD', '9600')
            sms_modem_timeout = request.POST.get('SMS_MODEM_TIMEOUT', '10')

            try:
                env_content = env_file.read_text(encoding='utf-8')
                lines = env_content.split('\n')
                new_lines = []
                for line in lines:
                    if line.startswith('SMS_ENABLED='):
                        new_lines.append(f'SMS_ENABLED={sms_enabled}')
                    elif line.startswith('SMS_BACKEND='):
                        new_lines.append(f'SMS_BACKEND={sms_backend}')
                    elif line.startswith('SMS_HTTP_URL='):
                        new_lines.append(f'SMS_HTTP_URL={sms_http_url}')
                    elif line.startswith('SMS_HTTP_USER='):
                        new_lines.append(f'SMS_HTTP_USER={sms_http_user}')
                    elif line.startswith('SMS_HTTP_PASSWORD='):
                        new_lines.append(f'SMS_HTTP_PASSWORD={sms_http_password}')
                    elif line.startswith('SMS_HTTP_TIMEOUT='):
                        new_lines.append(f'SMS_HTTP_TIMEOUT={sms_http_timeout}')
                    elif line.startswith('SMS_MODEM_PORT='):
                        new_lines.append(f'SMS_MODEM_PORT={sms_modem_port}')
                    elif line.startswith('SMS_MODEM_BAUD='):
                        new_lines.append(f'SMS_MODEM_BAUD={sms_modem_baud}')
                    elif line.startswith('SMS_MODEM_TIMEOUT='):
                        new_lines.append(f'SMS_MODEM_TIMEOUT={sms_modem_timeout}')
                    elif line.strip():
                        new_lines.append(line)

                env_file.write_text('\n'.join(new_lines), encoding='utf-8')
                messages.success(request, "Configuration SMS enregistrée. Veuillez redémarrer le serveur pour appliquer les changements.")
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

            if getattr(settings, 'SMS_ENABLED', False) and numeros:
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
