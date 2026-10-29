import logging
import re
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from inscriptions.models import Eleve
from parametres.models import AnneeScolaire

from .models import MessageParent, ReponseParent

logger = logging.getLogger(__name__)


def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


# ─── LISTE ────────────────────────────────────────────────────────────

@login_required
def message_list(request):
    etab = _get_etab(request)
    base_qs = (
        MessageParent.objects
        .filter(etablissement=etab)
        .select_related('eleve', 'annee_scolaire', 'envoye_par')
        if etab else MessageParent.objects.none()
    )

    nb_total = base_qs.count()
    nb_repondu = base_qs.filter(statut='REPONDU').count()
    nb_en_attente = base_qs.filter(statut='ENVOYE').count()

    type_filter = request.GET.get('type', '')
    statut_filter = request.GET.get('statut', '')
    q = request.GET.get('q', '')

    qs = base_qs
    if type_filter:
        qs = qs.filter(type=type_filter)
    if statut_filter:
        qs = qs.filter(statut=statut_filter)
    if q:
        qs = qs.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(objet__icontains=q)
        )

    ctx = {
        'messages': qs,
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

        if envoyer_sms_flag and telephone:
            from core.tasks import envoyer_sms_async
            lien = msg.get_lien_reponse(request)
            sms_text = f"{objet} — Répondez : {lien}"
            envoyer_sms_async(telephone, sms_text[:160])
            msg.sms_envoye = True
            msg.date_envoi_sms = timezone.now()
            msg.save(update_fields=['sms_envoye', 'date_envoi_sms'])

        return HttpResponse('', headers={'HX-Trigger': 'messageCreated'})

    return render(request, 'communication/partials/message_form.html', ctx)


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
    from .models import IncomingSMSLog
    logs = IncomingSMSLog.objects.all()[:20]
    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'history':
        return render(request, 'communication/partials/sms_direct_history.html', {
            'logs': logs,
        })
    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'count':
        return render(request, 'communication/partials/sms_direct_count.html', {
            'logs': logs,
        })
    return render(request, 'communication/sms_direct.html', {
        'logs': logs,
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

    from .models import IncomingSMSLog
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
    from .sms_recus import identifiant_message, traiter_sms_recu

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


# ─── CAMPAGNES SMS CIBLÉES ────────────────────────────────────────────

_ROLES_CAMPAGNE = ('SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR', 'SECRETAIRE', 'COMPTABLE')


def _refus_campagne(request):
    if request.user.role in _ROLES_CAMPAGNE or request.user.is_superuser:
        return None
    return render(request, 'core/access_denied.html', {
        'message': "Les campagnes SMS sont réservées à la direction, au secrétariat et à la comptabilité.",
    }, status=403)


def _sigle(etab):
    from parametres.models import IdentiteEtablissement
    identite = IdentiteEtablissement.objects.filter(etablissement=etab).first()
    return (identite.sigle or identite.nom_etablissement) if identite else (etab.nom if etab else '')


@login_required
def campagne_list(request):
    """Historique des campagnes SMS de l'établissement, avec envoyés / échecs / en attente."""
    from core.models import CampagneSms
    refus = _refus_campagne(request)
    if refus:
        return refus
    campagnes = list(CampagneSms.objects.filter(etablissement=_get_etab(request)).select_related('envoyee_par')[:50])
    for c in campagnes:
        c.suivi = c.bilan()
    return render(request, 'communication/campagne_list.html', {'campagnes': campagnes})


def _criteres(request, cible):
    from core.models import CampagneSms
    if cible == CampagneSms.Cible.PARENTS_CLASSES:
        return {'classes': request.POST.getlist('classes')}
    if cible == CampagneSms.Cible.PARENTS_ABSENTS:
        return {'date': request.POST.get('date') or timezone.localdate().isoformat()}
    return {}


@login_required
def campagne_nouvelle(request):
    """Composer une campagne : public, message à variables ; l'aperçu compte les destinataires et montre les textes
    rendus, puis « Envoyer » met les SMS en file."""
    from core.models import CampagneSms
    from core.sms import sms_actifs
    from parametres.models import Classe
    from . import campagnes

    refus = _refus_campagne(request)
    if refus:
        return refus
    etab = _get_etab(request)
    annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    contexte = {
        'cibles': CampagneSms.Cible.choices, 'variables': campagnes.VARIABLES, 'longueur_sms': campagnes.LONGUEUR_SMS,
        'classes': Classe.objects.filter(etablissement=etab, actif=True).order_by('cycle__ordre', 'nom'),
        'annee': annee, 'sms_actifs': sms_actifs(), 'today': timezone.localdate(),
        'titre': '', 'message': '', 'cible': CampagneSms.Cible.PARENTS_TOUS, 'classes_choisies': [], 'date': '',
    }
    if request.method != 'POST':
        return render(request, 'communication/campagne_form.html', contexte)

    titre = ' '.join(request.POST.get('titre', '').split())[:120]
    modele = request.POST.get('message', '').strip()
    cible = request.POST.get('cible', '')
    criteres = _criteres(request, cible)
    contexte.update({'titre': titre, 'message': modele, 'cible': cible,
                     'classes_choisies': criteres.get('classes', []), 'date': criteres.get('date', '')})
    erreurs = []
    if cible not in CampagneSms.Cible.values:
        erreurs.append("Choisissez le public de la campagne.")
    if not titre:
        erreurs.append("Donnez un titre à la campagne (il n'est pas envoyé, il sert au suivi).")
    if not modele:
        erreurs.append("Rédigez le message.")
    if cible == CampagneSms.Cible.PARENTS_CLASSES and not criteres['classes']:
        erreurs.append("Cochez au moins une classe.")
    if annee is None and cible != CampagneSms.Cible.PERSONNEL:
        erreurs.append("Aucune année scolaire courante.")
    if erreurs:
        for e in erreurs:
            messages.error(request, e)
        return render(request, 'communication/campagne_form.html', contexte)

    liste, compteurs = campagnes.destinataires(etab, annee, cible, criteres, sigle=_sigle(etab))
    if request.POST.get('confirmer') == '1':
        if not sms_actifs():
            messages.error(request, "Les SMS sont désactivés (Paramètres → Configuration SMS) : campagne non envoyée.")
            return render(request, 'communication/campagne_form.html', contexte)
        if not liste:
            messages.error(request, "Aucun destinataire joignable : campagne non envoyée.")
            return render(request, 'communication/campagne_form.html', contexte)
        campagne = campagnes.lancer(etab, annee, titre, modele, cible, criteres, liste, request.user)
        messages.success(request, f"Campagne « {campagne.titre} » : {len(liste)} SMS mis en file, envoi en cours.")
        return redirect('communication:campagne_detail', pk=campagne.pk)

    rendus, plus_long = campagnes.apercu(modele, liste)
    contexte.update({'apercu': True, 'rendus': rendus[:30], 'nb_destinataires': len(liste),
                     'nb_sans_numero': compteurs['sans_numero'], 'plus_long': plus_long})
    return render(request, 'communication/campagne_form.html', contexte)


@login_required
def campagne_detail(request, pk):
    """Suivi d'une campagne : destinataire, statut, erreur ; renvoi des échecs."""
    from core.models import CampagneSms
    refus = _refus_campagne(request)
    if refus:
        return refus
    campagne = get_object_or_404(CampagneSms, pk=pk, etablissement=_get_etab(request))
    return render(request, 'communication/campagne_detail.html', {
        'campagne': campagne, 'suivi': campagne.bilan(),
        'sms': campagne.sms.order_by('destinataire', 'numero'),
    })


@login_required
@require_POST
def campagne_renvoyer(request, pk):
    from core.models import CampagneSms
    from . import campagnes
    refus = _refus_campagne(request)
    if refus:
        return refus
    campagne = get_object_or_404(CampagneSms, pk=pk, etablissement=_get_etab(request))
    nb = campagnes.renvoyer_echecs(campagne)
    messages.success(request, f"{nb} SMS remis en file." if nb else "Aucun SMS en échec.")
    return redirect('communication:campagne_detail', pk=campagne.pk)


# ─── MESSAGES REÇUS — BOÎTE DES SMS DES PARENTS ───────────────────────

def _cle_numero(numero):
    """Huit derniers chiffres d'un numéro, quel que soit son format (« +226 70 11 22 33 », « 70112233 », « 0022670112233 »)."""
    return re.sub(r'\D', '', numero or '')[-8:]


def _familles_par_numero(numeros):
    """{clé de numéro: [élèves dont un numéro de famille porte cette clé]}, classe courante sur chaque élève —
    deux requêtes pour toute la page, tolérantes aux espaces et préfixes des fiches (« 70 11 22 33 » = « +22670112233 »)."""
    from inscriptions.models import Inscription
    cles = {cle for cle in map(_cle_numero, numeros) if len(cle) == 8}
    if not cles:
        return {}
    filtre = Q()
    for cle in cles:
        motif = r'\D*'.join(cle) + r'\D*$'
        filtre |= Q(telephone_parent__regex=motif) | Q(tuteur_telephone__regex=motif) | Q(telephone_urgence__regex=motif)
    eleves = list(Eleve.objects.filter(filtre).order_by('nom', 'prenom'))
    classes = dict(Inscription.objects.filter(eleve__in=eleves, annee_scolaire__est_courante=True)
                   .values_list('eleve_id', 'classe__nom'))
    familles = {}
    for eleve in eleves:
        eleve.classe_courante = classes.get(eleve.pk, '')
        for brut in (eleve.telephone_parent, eleve.tuteur_telephone, eleve.telephone_urgence):
            cle = _cle_numero(brut)
            if cle in cles and eleve not in familles.setdefault(cle, []):
                familles[cle].append(eleve)
    return familles


def _nb_messages_libres_non_lus():
    from .models import IncomingSMSLog
    return IncomingSMSLog.objects.filter(command_type=IncomingSMSLog.LIBRE, lu_le__isnull=True).count()


def _retour_messages_recus(request):
    suivant = request.POST.get('next', '')
    if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()},
                                                   require_https=request.is_secure()):
        return redirect(suivant)
    return redirect('communication:messages_recus')


@login_required
def messages_recus(request):
    """Boîte des SMS reçus des parents : messages libres (hors commande) à lire et à traiter ; commandes
    automatiques en consultation. Filtres type / état, famille identifiée par le numéro, lu / non lu, réponse."""
    from core.sms import sms_actifs
    from .models import IncomingSMSLog

    type_ = request.GET.get('type') if request.GET.get('type') in ('commandes', 'tous') else 'libres'
    etat = request.GET.get('etat') if request.GET.get('etat') in ('non_lus', 'lus') else ''
    qs = IncomingSMSLog.objects.select_related('eleve', 'lu_par')
    if type_ == 'libres':
        qs = qs.filter(command_type=IncomingSMSLog.LIBRE)
    elif type_ == 'commandes':
        qs = qs.exclude(command_type=IncomingSMSLog.LIBRE)
    if etat:
        qs = qs.filter(lu_le__isnull=(etat == 'non_lus'))
    page_obj = Paginator(qs, 50).get_page(request.GET.get('page'))
    familles = _familles_par_numero([m.sender_number for m in page_obj])
    for m in page_obj:
        m.famille = familles.get(_cle_numero(m.sender_number), [])
    return render(request, 'communication/messages_recus.html', {
        'page_obj': page_obj,
        'type': type_,
        'etat': etat,
        'filtres': urlencode({cle: valeur for cle, valeur in (('type', type_), ('etat', etat)) if valeur}),
        'non_lus': _nb_messages_libres_non_lus(),
        'sms_actifs': sms_actifs(),
    })


@login_required
def messages_recus_compteur(request):
    """Partiel HTMX — pastille du menu : nombre de messages libres non lus."""
    return render(request, 'communication/partials/messages_recus_compteur.html', {'nb': _nb_messages_libres_non_lus()})


@login_required
@require_POST
def messages_recus_marquer(request, pk):
    """Marque un message lu (``etat=lu``) ou non lu (``etat=non_lu``)."""
    from .models import IncomingSMSLog
    message = get_object_or_404(IncomingSMSLog, pk=pk)
    if request.POST.get('etat') == 'non_lu':
        IncomingSMSLog.objects.filter(pk=message.pk).update(lu_le=None, lu_par=None)
    else:
        IncomingSMSLog.objects.filter(pk=message.pk).update(lu_le=timezone.now(), lu_par=request.user)
    return _retour_messages_recus(request)


@login_required
@require_POST
def messages_recus_tout_lu(request):
    """Marque lus tous les messages libres non lus."""
    from .models import IncomingSMSLog
    nb = IncomingSMSLog.objects.filter(command_type=IncomingSMSLog.LIBRE, lu_le__isnull=True) \
        .update(lu_le=timezone.now(), lu_par=request.user)
    messages.success(request, f"{nb} message(s) marqué(s) comme lu(s).")
    return _retour_messages_recus(request)


@login_required
@require_POST
def messages_recus_repondre(request, pk):
    """Répond par SMS (160 caractères max.) au numéro du message : la réponse part par la file SMS et le message
    est marqué lu."""
    from core.sms import _normaliser_numero
    from core.tasks import envoyer_sms_async
    from .models import IncomingSMSLog

    message = get_object_or_404(IncomingSMSLog, pk=pk)
    texte = ' '.join(request.POST.get('texte', '').split())
    if not texte or len(texte) > 160:
        messages.error(request, "La réponse doit compter entre 1 et 160 caractères.")
        return _retour_messages_recus(request)
    numero = _normaliser_numero(message.sender_number)
    if envoyer_sms_async(numero, texte) is None:
        messages.error(request, "Les SMS sont désactivés (Paramètres → Configuration SMS) : réponse non envoyée.")
        return _retour_messages_recus(request)
    IncomingSMSLog.objects.filter(pk=message.pk, lu_le__isnull=True).update(lu_le=timezone.now(), lu_par=request.user)
    messages.success(request, f"Réponse mise en file pour {numero}.")
    return _retour_messages_recus(request)
