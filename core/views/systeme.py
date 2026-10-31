"""Assistant intégré et sonde de santé du serveur."""

import logging
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import HttpResponseForbidden, JsonResponse
from licences.decorators import requires_licence_feature
logger = logging.getLogger(__name__)


@login_required
@requires_licence_feature('ia_predictive')
def chatbot(request):
    """Interface de l'assistant IA — moteur de requêtes local, sans API externe (direction uniquement :
    il répond avec les données de l'établissement de l'utilisateur)."""
    if request.user.role not in ('SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR', 'DIRECTEUR_RESEAU') and not request.user.is_superuser:
        return HttpResponseForbidden("L'assistant est réservé à la direction.")
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
        response_text, display_history = chat(display_history, user_message, request.user.etablissement)

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


@never_cache
def health_check(request):
    """Endpoint de healthcheck pour le load balancer / monitoring Docker."""
    from django.db import connections

    health = {'status': 'ok', 'version': settings.YELEN_VERSION}

    # Vérification base de données
    db_ok = False
    try:
        conn = connections['default']
        conn.cursor()
        db_ok = True
    except Exception:
        logger.exception("Health check : base de données indisponible")
    health['database'] = 'ok' if db_ok else 'error'

    # Vérification cache Redis
    cache_ok = False
    try:
        from django.core.cache import cache
        cache.set('_health_check', 1, 5)
        cache_ok = cache.get('_health_check') == 1
    except Exception:
        logger.exception("Health check : cache indisponible")
    health['cache'] = 'ok' if cache_ok else 'error'

    from core import mode_demo
    health['demo'] = mode_demo.actif()

    status_code = 200 if (db_ok and cache_ok) else 503
    return JsonResponse(health, status=status_code)
