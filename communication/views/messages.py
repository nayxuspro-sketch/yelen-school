"""Messagerie aux parents, simulateur SMS et webhook de réception SMS."""
import logging
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from inscriptions.models import Eleve
from parametres.models import AnneeScolaire

from ..models import MessageParent, ReponseParent
from .commun import _get_etab, _sigle

logger = logging.getLogger(__name__)


# ─── LISTE ────────────────────────────────────────────────────────────

def _filtrer_messages(qs, type_filter, statut_filter, q):
    if type_filter:
        qs = qs.filter(type=type_filter)
    if statut_filter:
        qs = qs.filter(statut=statut_filter)
    if q:
        qs = qs.filter(Q(eleve__nom__icontains=q) | Q(eleve__prenom__icontains=q) | Q(objet__icontains=q))
    return qs


@login_required
def message_list(request):
    etab = _get_etab(request)
    base_qs = (
        MessageParent.objects
        .filter(etablissement=etab)
        .select_related('eleve', 'annee_scolaire', 'envoye_par', 'sms')
        if etab else MessageParent.objects.none()
    )

    nb_total = base_qs.count()
    nb_repondu = base_qs.filter(statut='REPONDU').count()
    nb_en_attente = base_qs.filter(statut='ENVOYE').count()

    type_filter = request.GET.get('type', '')
    statut_filter = request.GET.get('statut', '')
    q = request.GET.get('q', '')
    qs = _filtrer_messages(base_qs, type_filter, statut_filter, q)

    ctx = {
        'messages_parents': qs,   # pas « messages » : la clé masquerait les messages flash de Django dans base.html
        'nb_affiches': qs.count(),
        'type_choices': MessageParent.TYPE_CHOICES,
        'statut_choices': MessageParent.STATUT_CHOICES,
        'type_filter': type_filter,
        'statut_filter': statut_filter,
        'q': q,
        'nb_total': nb_total,
        'nb_repondu': nb_repondu,
        'nb_en_attente': nb_en_attente,
    }
    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'stats':
        return render(request, 'communication/partials/message_stats.html', ctx)

    tpl = ('communication/partials/message_list.html'
           if request.headers.get('HX-Request')
           else 'communication/messages_list.html')
    return render(request, tpl, ctx)


# ─── CRÉATION ─────────────────────────────────────────────────────────

@login_required
def message_create(request):
    etab = _get_etab(request)
    annee = (AnneeScolaire.objects
             .filter(etablissement=etab, est_courante=True)
             .first()) if etab else None

    eleves = (
        Eleve.objects
        .filter(inscriptions__annee_scolaire=annee,
                inscriptions__classe__etablissement=etab)
        .distinct()
        .order_by('nom', 'prenom')
        if (etab and annee) else Eleve.objects.none()
    )

    ctx = {
        'type_choices': MessageParent.TYPE_CHOICES,
        'eleves': eleves,
        'annee': annee,
    }

    if request.method == 'POST':
        if not etab:
            ctx['error'] = "Votre compte n'est pas associé à un établissement."
            return render(request, 'communication/partials/message_form.html', ctx)

        eleve_pk = request.POST.get('eleve', '').strip()
        type_msg = request.POST.get('type', '').strip()
        objet = request.POST.get('objet', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        creneaux_txt = request.POST.get('creneaux', '').strip()
        envoyer_sms_flag = 'envoyer_sms' in request.POST

        if not (eleve_pk and type_msg and objet and contenu):
            ctx['error'] = "Élève, type, objet et contenu sont obligatoires."
            return render(request, 'communication/partials/message_form.html', ctx)

        eleve = get_object_or_404(Eleve, pk=eleve_pk)
        telephone = eleve.telephone_parent or eleve.tuteur_telephone or ''
        creneaux = [c.strip() for c in creneaux_txt.splitlines() if c.strip()]

        if envoyer_sms_flag:
            from .. import bidirectionnel
            if not telephone:
                ctx['error'] = (f"Aucun numéro de parent ni de tuteur sur la fiche de {eleve.prenom} {eleve.nom} : "
                                "complétez la fiche élève ou décochez l'envoi par SMS.")
                return render(request, 'communication/partials/message_form.html', ctx)
            texte_sms = bidirectionnel.texte_sms(MessageParent(type=type_msg, objet=objet, contenu=contenu,
                                                               creneaux_proposes=creneaux), _sigle(etab))
            if len(texte_sms) > bidirectionnel.LONGUEUR_SMS:
                ctx['error'] = (f"Le SMS ferait {len(texte_sms)} caractères pour {bidirectionnel.LONGUEUR_SMS} maximum : "
                                "raccourcissez l'objet, le contenu ou les créneaux.")
                return render(request, 'communication/partials/message_form.html', ctx)

        msg = MessageParent.objects.create(
            etablissement=etab,
            eleve=eleve,
            annee_scolaire=annee,
            type=type_msg,
            objet=objet,
            contenu=contenu,
            creneaux_proposes=creneaux,
            telephone_utilise=telephone,
            envoye_par=request.user,
            date_expiration=timezone.now() + timezone.timedelta(days=30),
        )

        if envoyer_sms_flag:
            from core.tasks import envoyer_sms_async
            # Le message est envoyé en clair, le parent répond en répondant au SMS (pas de lien : le serveur
            # de l'école n'est pas joignable depuis l'extérieur). Le lien reste sur la fiche du message.
            msg.sms = envoyer_sms_async(telephone, texte_sms)
            msg.sms_envoye = msg.sms is not None
            msg.date_envoi_sms = timezone.now() if msg.sms_envoye else None
            msg.save(update_fields=['sms', 'sms_envoye', 'date_envoi_sms'])
            if msg.sms is None:
                messages.warning(request, "Les SMS sont désactivés (Paramètres → Configuration SMS) : message enregistré, SMS non envoyé.")

        return HttpResponse('', headers={'HX-Trigger': 'messageCreated'})

    return render(request, 'communication/partials/message_form.html', ctx)


@login_required
@require_POST
def message_renvoyer_sms(request, pk):
    """(Re)met en file le SMS d'un message : jamais envoyé (case décochée, SMS désactivés à l'époque), en échec,
    ou envoyé dans l'ancien format avec un lien. Le texte est recomposé et le numéro relu sur la fiche élève."""
    from core.tasks import envoyer_sms_async
    from .. import bidirectionnel

    etab = _get_etab(request)
    msg = get_object_or_404(MessageParent.objects.select_related('eleve'), pk=pk, etablissement=etab)
    suivant = _suivant_ou(request, reverse('communication:message_detail', args=[msg.pk]))

    telephone = msg.eleve.telephone_parent or msg.eleve.tuteur_telephone or msg.telephone_utilise
    texte = bidirectionnel.texte_sms(msg, _sigle(etab))
    if not telephone:
        messages.error(request, f"Aucun numéro de parent ni de tuteur sur la fiche de {msg.eleve.prenom} {msg.eleve.nom} : SMS non envoyé.")
        return redirect(suivant)
    if len(texte) > bidirectionnel.LONGUEUR_SMS:
        messages.error(request, f"Le SMS ferait {len(texte)} caractères pour {bidirectionnel.LONGUEUR_SMS} maximum : "
                                "créez un message plus court.")
        return redirect(suivant)
    sms = envoyer_sms_async(telephone, texte)
    if sms is None:
        messages.error(request, "Les SMS sont désactivés (Paramètres → Configuration SMS) : SMS non envoyé.")
        return redirect(suivant)
    msg.sms = sms
    msg.sms_envoye = True
    msg.date_envoi_sms = timezone.now()
    msg.telephone_utilise = telephone
    msg.save(update_fields=['sms', 'sms_envoye', 'date_envoi_sms', 'telephone_utilise'])
    messages.success(request, f"SMS mis en file pour {telephone} : « {msg.objet} ».")
    return redirect(suivant)


def _suivant_ou(request, defaut):
    """URL de retour ``next`` du formulaire si elle est locale, sinon ``defaut``."""
    suivant = request.POST.get('next', '')
    if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()},
                                                   require_https=request.is_secure()):
        return suivant
    return defaut


def _supprimer_messages_parents(request, qs, suivant):
    """Supprime les messages (réponses en cascade, fichiers justificatifs effacés) ; les SMS reçus des parents
    restent dans Messages reçus, détachés du message."""
    for reponse in ReponseParent.objects.filter(message__in=qs).exclude(justificatif=''):
        reponse.justificatif.delete(save=False)
    _, details = qs.delete()
    nb = details.get(MessageParent._meta.label, 0)   # les réponses supprimées en cascade ne sont pas comptées
    messages.success(request, f"{nb} message(s) parent(s) supprimé(s).")
    return redirect(suivant)


@login_required
@require_POST
def message_supprimer_filtre(request):
    """Supprime les messages de la vue courante : type et / ou statut obligatoires (jamais toute la boîte d'un
    clic), recherche éventuelle comprise."""
    type_filter = request.POST.get('type', '') if request.POST.get('type', '') in dict(MessageParent.TYPE_CHOICES) else ''
    statut_filter = request.POST.get('statut', '') if request.POST.get('statut', '') in dict(MessageParent.STATUT_CHOICES) else ''
    q = request.POST.get('q', '').strip()
    suivant = reverse('communication:message_list') + '?' + urlencode({'type': type_filter, 'statut': statut_filter, 'q': q})
    if not (type_filter or statut_filter):
        messages.error(request, "Choisissez un type et / ou un statut avant de supprimer.")
        return redirect(suivant)
    qs = _filtrer_messages(MessageParent.objects.filter(etablissement=_get_etab(request)), type_filter, statut_filter, q)
    return _supprimer_messages_parents(request, qs, suivant)


@login_required
@require_POST
def message_supprimer_selection(request):
    """Supprime les messages cochés dans la liste (``ids``)."""
    suivant = _suivant_ou(request, reverse('communication:message_list'))
    ids = [i for i in request.POST.getlist('ids') if re.fullmatch(r'[0-9a-fA-F-]{36}', i)]
    if not ids:
        messages.error(request, "Cochez au moins un message à supprimer.")
        return redirect(suivant)
    qs = MessageParent.objects.filter(pk__in=ids, etablissement=_get_etab(request))
    return _supprimer_messages_parents(request, qs, suivant)


@login_required
@require_POST
def message_supprimer(request, pk):
    qs = MessageParent.objects.filter(pk=pk, etablissement=_get_etab(request))
    get_object_or_404(qs)
    return _supprimer_messages_parents(request, qs, _suivant_ou(request, reverse('communication:message_list')))


# ─── DÉTAIL ───────────────────────────────────────────────────────────

@login_required
def message_detail(request, pk):
    etab = _get_etab(request)
    msg = get_object_or_404(MessageParent, pk=pk, etablissement=etab)
    reponse = getattr(msg, 'reponse', None)
    return render(request, 'communication/message_detail.html', {
        'msg': msg,
        'reponse': reponse,
        'lien_reponse': msg.get_lien_reponse(request),
    })


@login_required
def justificatif_download(request, pk):
    """
    S4 — téléchargement sécurisé des justificatifs parentaux.
    Accès réservé au staff de l'établissement (pas d'accès public via /media/).
    """
    import os
    from django.http import FileResponse, Http404

    etab = _get_etab(request)
    # Filtre par établissement pour cloisonnement
    reponse = get_object_or_404(ReponseParent, pk=pk, message__etablissement=etab)

    if not reponse.justificatif:
        raise Http404("Aucun justificatif.")

    # Vérification que le fichier existe physiquement
    if not reponse.justificatif.storage.exists(reponse.justificatif.name):
        raise Http404("Fichier introuvable.")

    # Nom de fichier pour Content-Disposition
    filename = os.path.basename(reponse.justificatif.name)

    # FileResponse avec streaming (sécurisé, pas d'exposition du chemin MEDIA)
    return FileResponse(
        reponse.justificatif.open('rb'),
        as_attachment=False,
        filename=filename,
    )


# ─── RÉPONSE PARENT (vue publique, sans authentification) ────────────

def repondre(request, token):
    msg = get_object_or_404(MessageParent, token=token)

    # S3 — expiration du lien public
    if not msg.est_valide:
        return render(request, 'communication/repondre.html', {
            'msg': msg,
            'lien_expire': True,
        })

    reponse_existante = getattr(msg, 'reponse', None)

    if msg.statut == MessageParent.STATUT_ENVOYE:
        msg.statut = MessageParent.STATUT_LU
        msg.save(update_fields=['statut'])

    if reponse_existante:
        return render(request, 'communication/repondre.html', {
            'msg': msg,
            'reponse': reponse_existante,
            'deja_repondu': True,
        })

    if request.method == 'POST':
        creneau_choisi = request.POST.get('creneau_choisi', '')
        accuse = 'accuse_reception' in request.POST
        date_reglement = request.POST.get('date_reglement_prevue') or None
        commentaire = request.POST.get('commentaire', '').strip()
        justificatif_fichier = request.FILES.get('justificatif')

        reponse = ReponseParent(
            message=msg,
            creneau_choisi=creneau_choisi,
            accuse_reception=accuse,
            date_reglement_prevue=date_reglement,
            commentaire=commentaire,
        )
        if justificatif_fichier:
            reponse.justificatif = justificatif_fichier
        reponse.save()

        msg.statut = MessageParent.STATUT_REPONDU
        msg.save(update_fields=['statut'])

        return render(request, 'communication/repondre.html', {
            'msg': msg,
            'reponse': reponse,
            'succes': True,
        })

    return render(request, 'communication/repondre.html', {
        'msg': msg,
    })


# ─── SMS DIRECT — SIMULATEUR / INTERFACE PARENT ──────────────────

@login_required
def sms_direct_simulateur(request):
    """Interface HTMX de simulation du SMS Direct (Parent-SMS)."""
    from ..models import IncomingSMSLog
    logs = IncomingSMSLog.objects.filter(is_active=True)[:20]
    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'history':
        return render(request, 'communication/partials/sms_direct_history.html', {
            'logs': logs,
        })
    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'count':
        return render(request, 'communication/partials/sms_direct_count.html', {
            'logs': logs,
        })
    from ..models import CommandeSms
    return render(request, 'communication/sms_direct.html', {
        'logs': logs,
        'commandes_perso': CommandeSms.objects.filter(etablissement=_get_etab(request)),
    })


@login_required
@require_POST
def sms_direct_envoyer(request):
    """Envoie une commande SMS simulée et retourne la réponse."""
    import json
    from django.test.client import RequestFactory

    phone = request.POST.get('phone', '').strip()
    message = request.POST.get('message', '').strip()

    if not phone or not message:
        return HttpResponse(
            '<div class="alert alert-danger">Numéro et message requis.</div>',
            headers={'HX-Trigger': 'smsError'},
        )

    factory = RequestFactory()
    req = factory.post('/communication/webhook/sms/', {
        'phoneNumber': phone,
        'message': message,
    })
    req.META['SERVER_NAME'] = request.META.get('SERVER_NAME', 'localhost')
    req.META['SERVER_PORT'] = request.META.get('SERVER_PORT', '8000')
    # Marqueur Python interne : il ne peut pas être forgé par une requête HTTP
    # et permet à l'interface authentifiée de réutiliser le même traitement
    # sans passer par l'authentification du webhook externe.
    req._yelen_internal_sms = True

    from django.test.utils import override_settings
    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        resp = webhook_incoming_sms(req)

    try:
        data = json.loads(resp.content)
    except ValueError:
        logger.exception("Envoi SMS direct : réponse illisible")
        data = {'status': 'error', 'response': 'Erreur de traitement'}

    from ..models import IncomingSMSLog
    dernier_log = IncomingSMSLog.objects.filter(sender_number=phone).order_by('-created_at').first()
    if dernier_log and dernier_log.lu_le is None:  # saisi et lu à l'écran par l'utilisateur : rien à traiter dans « Messages reçus »
        IncomingSMSLog.objects.filter(pk=dernier_log.pk).update(lu_le=timezone.now(), lu_par=request.user)

    response = render(request, 'communication/partials/sms_direct_result.html', {
        'data': data,
        'phone': phone,
        'message': message,
        'log': dernier_log,
    })
    response['HX-Trigger'] = 'smsHistoryUpdated'
    return response


@csrf_exempt
@require_POST
def webhook_incoming_sms(request):
    """
    Webhook pour traiter les SMS entrants des parents (PWA Parent-SMS Direct).
    Supporte les formats JSON (Android SMS Gateway) et les paramètres standards POST.

    Sécurité A1 :
    - IP whitelist (SMS_ALLOWED_IPS)
    - Token partagé (SMS_WEBHOOK_TOKEN)
    - HMAC signature (SMS_WEBHOOK_SECRET) — vérifie X-SMS-Signature = HMAC-SHA256(body, secret)
    - Rate limiting par IP (SMS_WEBHOOK_RATE_LIMIT req/min)
    """
    import hashlib
    import hmac
    import json
    from django.http import JsonResponse
    from django.conf import settings
    from django.core.cache import cache
    from django.utils.crypto import constant_time_compare
    from ..sms_recus import identifiant_message, traiter_sms_recu

    # ── Authentification et limitation du webhook ─────────────────────
    # Fusion des deux protections (main A1 + distribution client) :
    #   - les appels internes (simulateur SMS, déjà derrière login_required)
    #     portent un marqueur Python non forgeable par HTTP ;
    #   - pour les appels externes : liste d'IP, rate limiting par IP, puis
    #     HMAC-SHA256 obligatoire si un secret est configuré, sinon token
    #     partagé (comparaisons en temps constant) ; hors DEBUG, un webhook
    #     sans secret ni token est refusé (503) au lieu d'être ouvert.
    internal_request = getattr(request, '_yelen_internal_sms', False)
    if not internal_request:
        remote_ip = request.META.get('REMOTE_ADDR', '') or 'unknown'
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        client_ip = (forwarded_for.split(',')[0].strip()
                     if forwarded_for else remote_ip)

        # Vérification IP (si une liste d'IP autorisées est configurée).
        if settings.SMS_ALLOWED_IPS and client_ip not in settings.SMS_ALLOWED_IPS:
            return JsonResponse(
                {'status': 'error', 'message': 'Accès non autorisé.'},
                status=403,
            )

        # Limite par adresse source (SMS_WEBHOOK_RATE_LIMIT requêtes / minute).
        rate_limit = max(1, int(getattr(settings, 'SMS_WEBHOOK_RATE_LIMIT', 60)))
        rate_key = f"yelen:sms-webhook:{client_ip}:{timezone.now().strftime('%Y%m%d%H%M')}"
        try:
            try:
                request_count = cache.incr(rate_key)
            except ValueError:
                cache.add(rate_key, 1, timeout=70)
                request_count = 1
        except Exception:
            logger.warning("Webhook SMS : cache indisponible, limitation de débit désactivée", exc_info=True)
            # Cache indisponible : on ne bloque pas (fail-open pour disponibilité)
            request_count = 0
        if request_count > rate_limit:
            return JsonResponse(
                {'status': 'error', 'message': 'Trop de requêtes. Réessayez dans une minute.'},
                status=429,
            )

        configured_token = getattr(settings, 'SMS_WEBHOOK_TOKEN', '').strip()
        if configured_token.lower().startswith(('generer-', 'votre-', 'changez')):
            configured_token = ''
        # Deux noms de variable acceptés (SMS_WEBHOOK_HMAC_SECRET = distribution
        # client, SMS_WEBHOOK_SECRET = chantier sécurité A1) ; en-tête X-SMS-Signature.
        hmac_secret = (getattr(settings, 'SMS_WEBHOOK_HMAC_SECRET', '')
                       or getattr(settings, 'SMS_WEBHOOK_SECRET', '')).strip()

        if not configured_token and not hmac_secret and not settings.DEBUG:
            return JsonResponse(
                {'status': 'error', 'message': 'Webhook SMS non configuré.'},
                status=503,
            )

        token = (request.GET.get('token', '')
                 or request.META.get('HTTP_X_SMS_TOKEN', ''))
        signature = request.META.get('HTTP_X_SMS_SIGNATURE', '').strip().lower()
        # Signature native de l'app Android SMS Gateway : X-Signature = HMAC-SHA256(corps + X-Timestamp),
        # avec la « Signing Key » de l'app (Réglages → Webhooks) comme secret. Horodatage toléré à ± 5 min.
        signature_app = request.META.get('HTTP_X_SIGNATURE', '').strip().lower()
        horodatage_app = request.META.get('HTTP_X_TIMESTAMP', '').strip()
        authenticated = False

        if hmac_secret:
            # Secret configuré → signature HMAC-SHA256 du corps brut OBLIGATOIRE.
            if not signature and not signature_app:
                return JsonResponse(
                    {'status': 'error', 'message': 'Signature manquante.'},
                    status=403,
                )
            if signature:
                expected_signature = hmac.new(
                    hmac_secret.encode('utf-8'),
                    request.body,
                    hashlib.sha256,
                ).hexdigest()
                authenticated = constant_time_compare(signature, expected_signature)
            elif horodatage_app.isdigit() and abs(int(horodatage_app) - int(timezone.now().timestamp())) <= 300:
                expected_signature = hmac.new(
                    hmac_secret.encode('utf-8'),
                    request.body + horodatage_app.encode('utf-8'),
                    hashlib.sha256,
                ).hexdigest()
                authenticated = constant_time_compare(signature_app, expected_signature)
        elif configured_token:
            authenticated = constant_time_compare(token, configured_token)
        elif settings.DEBUG:
            authenticated = True

        if not authenticated:
            return JsonResponse(
                {'status': 'error', 'message': 'Authentification webhook invalide.'},
                status=403,
            )

    sender_number = ""
    message_text = ""

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            # Enveloppe de l'app Android SMS Gateway : {"event": "sms:received", "payload": {"sender", "message", …}}.
            # Les autres événements (sms:sent, sms:delivered, system:ping…) sont acquittés sans traitement :
            # une erreur déclencherait jusqu'à 14 nouvelles tentatives côté téléphone.
            evenement = data.get('event')
            if evenement and evenement != 'sms:received':
                return JsonResponse({'status': 'ignored', 'event': evenement})
            charge = data.get('payload') if isinstance(data.get('payload'), dict) else data
            sender_number = charge.get('phoneNumber') or charge.get('phone') or charge.get('sender') or charge.get('from') or ""
            message_text = charge.get('message') or charge.get('text') or charge.get('msg') or ""
            message_id = charge.get('messageId') or ""
        else:
            sender_number = request.POST.get('phoneNumber') or request.POST.get('phone') or request.POST.get('sender') or request.POST.get('from') or ""
            message_text = request.POST.get('message') or request.POST.get('text') or request.POST.get('msg') or ""
            message_id = request.POST.get('messageId', '')
    else:
        sender_number = request.GET.get('phoneNumber') or request.GET.get('phone') or request.GET.get('sender') or request.GET.get('from') or ""
        message_text = request.GET.get('message') or request.GET.get('text') or request.GET.get('msg') or ""
        message_id = request.GET.get('messageId', '')

    sender_number = str(sender_number).strip()
    message_text = str(message_text).strip()

    if not sender_number or not message_text:
        return JsonResponse({'status': 'error', 'message': 'Missing phoneNumber or message'}, status=400)

    log, cree = traiter_sms_recu(sender_number, message_text, identifiant_message(message_id))
    if not cree:
        return JsonResponse({'status': 'duplicate', 'response': log.response_text, 'log_id': str(log.pk)})
    return JsonResponse({
        'status': 'success' if log.processed_successfully else 'error',
        'response': log.response_text,
        'log_id': str(log.pk)
    })

