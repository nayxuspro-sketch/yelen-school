"""Centre de notifications de l'application."""

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required


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
    from core import push
    context['push_cle_publique'] = push.cle_publique()      # carte « Notifications sur cet appareil »
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
