"""Journal d'audit : consultation, détail et export PDF."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


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
        from core.pdf import HTML as WeasyHTML
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
