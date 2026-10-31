"""Configuration de la passerelle SMS et état de réception."""

import logging
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
logger = logging.getLogger(__name__)


_ADRESSES_LOCALES = ('localhost', '127.0.0.1', '[::1]')


def _url_webhook_sms(request):
    """URL du webhook telle que le téléphone passerelle doit l'appeler : l'app SMS Gateway n'accepte que https://,
    donc toujours en HTTPS, sur le port du proxy TLS, avec une adresse du serveur joignable depuis le réseau — même
    quand la page est ouverte en http://localhost:8000 sur le serveur. Retourne (url, avertissement bloquant ou '')."""
    import os
    import re
    from django.http.request import split_domain_port

    chemin = '/communication/webhook/sms/'
    domaine, port = split_domain_port(request.get_host())
    if request.is_secure():
        port = port or '443'
    elif os.environ.get('YELEN_HTTPS', 'false').lower() == 'true':
        port = os.environ.get('YELEN_HTTPS_PORT', '8443')
    else:
        return request.build_absolute_uri(chemin), (
            "Le HTTPS n'est pas activé sur ce serveur : l'app SMS Gateway refuse les adresses http://. "
            "Lancez activer-https.bat (guide §9.3) puis revenez ici.")
    if domaine in _ADRESSES_LOCALES:
        # Page ouverte sur le serveur lui-même : adresse LAN inscrite par activer-https (YELEN_HTTPS_HOSTS = IP,NOMPC,…).
        domaine = next((h for h in re.split(r'[,; ]+', os.environ.get('YELEN_HTTPS_HOSTS', ''))
                        if re.fullmatch(r'\d{1,3}(\.\d{1,3}){3}', h) and not h.startswith('127.')), domaine)
    url = f"https://{domaine}{'' if port == '443' else ':' + port}{chemin}"
    avertissement = ''
    if domaine in _ADRESSES_LOCALES:
        avertissement = ("Adresse non joignable depuis le téléphone : ouvrez cette page par l'adresse IP du serveur "
                         "(https://<IP du serveur>:8443/).")
    return url, avertissement


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

    # URL que le téléphone passerelle appellera pour chaque SMS reçu. L'app SMS Gateway ne peut pas ajouter
    # d'en-tête : sans secret HMAC configuré, le jeton du webhook voyage dans l'URL (page réservée aux administrateurs).
    webhook_url, webhook_avertissement = _url_webhook_sms(request)
    jeton = settings.SMS_WEBHOOK_TOKEN
    if jeton and not jeton.lower().startswith(('generer-', 'votre-', 'changez')) \
            and not (settings.SMS_WEBHOOK_HMAC_SECRET or settings.SMS_WEBHOOK_SECRET):
        webhook_url += f'?token={jeton}'

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
                            new_lines.append('# Backend HTTP — app Android "SMS Gateway"')
                        new_lines.append(f'{var}={form_values[var]}')

                env_file.write_text('\n'.join(new_lines), encoding='utf-8')

                from core.sms import set_sms_config_runtime
                set_sms_config_runtime(**form_values)

                messages.success(request, "Configuration SMS enregistrée et appliquée immédiatement (sans redémarrage).")
                return redirect('core:sms_configuration')
            except Exception as e:
                logger.exception("Enregistrement de la configuration SMS impossible")
                messages.error(request, f"Erreur lors de l'enregistrement : {e}")

        elif 'tester' in request.POST:
            test_result = tester_modem()

        elif 'relever_maintenant' in request.POST:
            from communication.sms_recus import relever_boite_reception
            bilan = relever_boite_reception()
            if bilan['ok']:
                messages.success(request, f"Boîte de réception relevée : {bilan['nouveaux']} nouveau(x) SMS traité(s), "
                                          f"{bilan['ignores']} déjà connu(s) ou antérieur(s).")
            else:
                messages.error(request, f"Relève impossible — {bilan['motif']}")
            return redirect('core:sms_configuration')

        elif 'enregistrer_webhook' in request.POST:
            from core.sms import enregistrer_webhook
            succes, motif = (False, webhook_avertissement) if webhook_avertissement else enregistrer_webhook(webhook_url)
            if succes:
                messages.success(request, "Webhook enregistré sur le téléphone passerelle : les SMS reçus seront transmis à YELEN.")
            else:
                messages.error(request, f"Webhook non enregistré — {motif}")
            return redirect('core:sms_configuration')

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
        'webhook_avertissement': webhook_avertissement,
        **_etat_reception_sms(),
    })


def _etat_reception_sms():
    """Diagnostic de la réception des SMS des parents : dernière relève de la boîte du téléphone (service « sms »),
    dernier SMS reçu et sort de la réponse envoyée."""
    from datetime import datetime, timedelta
    from communication.models import IncomingSMSLog
    from communication.sms_recus import etat_releve
    from core.models import SmsSortant

    releve = etat_releve()
    if releve:
        for cle in ('quand', 'dernier'):
            try:
                releve[cle] = datetime.fromisoformat(releve.get(cle) or '')
            except ValueError:
                releve[cle] = None
    dernier = IncomingSMSLog.objects.order_by('-created_at').first()
    reponse = None
    if dernier is not None and dernier.response_text:
        reponse = SmsSortant.objects.filter(
            numero=dernier.sender_number, created_at__gte=dernier.created_at - timedelta(seconds=5),
        ).order_by('created_at').first()
    return {
        'releve': releve,
        'releve_perimee': bool(releve and releve['quand'] and timezone.now() - releve['quand'] > timedelta(minutes=2)),
        'dernier_recu': dernier,
        'derniere_reponse': reponse,
    }
