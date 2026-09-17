from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from inscriptions.models import Eleve
from parametres.models import AnneeScolaire

from .models import MessageParent, ReponseParent


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

    from django.test.utils import override_settings
    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        resp = webhook_incoming_sms(req)

    try:
        data = json.loads(resp.content)
    except Exception:
        data = {'status': 'error', 'response': 'Erreur de traitement'}

    from .models import IncomingSMSLog
    dernier_log = IncomingSMSLog.objects.filter(sender_number=phone).order_by('-created_at').first()

    return render(request, 'communication/partials/sms_direct_result.html', {
        'data': data,
        'phone': phone,
        'message': message,
        'log': dernier_log,
    })


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
    import re
    from django.views.decorators.csrf import csrf_exempt
    from django.http import JsonResponse, HttpResponse
    from django.conf import settings
    from django.core.cache import cache
    from core.sms import _normaliser_numero
    from core.tasks import envoyer_sms_async
    from inscriptions.models import Eleve, Inscription
    from pedagogie.models import MoyenneGenerale
    from presences.models import Presence
    from finances.views import _calcul_situation_financiere
    from .models import IncomingSMSLog

    # ── Rate limiting par IP (A1) ──────────────────────────────────────
    remote_ip = request.META.get('REMOTE_ADDR', '') or 'unknown'
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    client_ip = (forwarded_for.split(',')[0].strip() if forwarded_for else remote_ip)
    rl_key = f"sms_webhook_rl:{client_ip}"
    rl_limit = getattr(settings, 'SMS_WEBHOOK_RATE_LIMIT', 30)
    try:
        count = cache.get(rl_key, 0)
        if count >= rl_limit:
            return JsonResponse(
                {'status': 'error', 'message': 'Trop de requêtes. Réessayez dans une minute.'},
                status=429,
            )
        cache.set(rl_key, count + 1, 60)
    except Exception:
        # Si le cache est indisponible, on ne bloque pas (fail-open pour disponibilité)
        pass

    # ── Authentification du webhook ────────────────────────────────────
    # Vérification IP (si une liste d'IP autorisées est configurée)
    if settings.SMS_ALLOWED_IPS:
        if client_ip not in settings.SMS_ALLOWED_IPS:
            return JsonResponse(
                {'status': 'error', 'message': 'Accès non autorisé.'},
                status=403,
            )

    # Vérification du token partagé (passé en paramètre GET ou header X-SMS-Token)
    token = (request.GET.get('token', '')
             or request.META.get('HTTP_X_SMS_TOKEN', ''))
    if settings.SMS_WEBHOOK_TOKEN and token != settings.SMS_WEBHOOK_TOKEN:
        return JsonResponse(
            {'status': 'error', 'message': 'Token invalide.'},
            status=403,
        )

    # Vérification HMAC (A1) — si SMS_WEBHOOK_SECRET configuré
    webhook_secret = getattr(settings, 'SMS_WEBHOOK_SECRET', '')
    if webhook_secret:
        signature = request.META.get('HTTP_X_SMS_SIGNATURE', '')
        if not signature:
            return JsonResponse(
                {'status': 'error', 'message': 'Signature manquante.'},
                status=403,
            )
        # HMAC-SHA256 du body brut
        expected = hmac.new(
            webhook_secret.encode('utf-8'),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        # Comparaison constant-time
        if not hmac.compare_digest(expected, signature):
            return JsonResponse(
                {'status': 'error', 'message': 'Signature invalide.'},
                status=403,
            )

    sender_number = ""
    message_text = ""

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                sender_number = data.get('phoneNumber') or data.get('phone') or data.get('sender') or data.get('from') or ""
                message_text = data.get('message') or data.get('text') or data.get('msg') or ""
            except json.JSONDecodeError:
                pass
        else:
            sender_number = request.POST.get('phoneNumber') or request.POST.get('phone') or request.POST.get('sender') or request.POST.get('from') or ""
            message_text = request.POST.get('message') or request.POST.get('text') or request.POST.get('msg') or ""
    else:
        sender_number = request.GET.get('phoneNumber') or request.GET.get('phone') or request.GET.get('sender') or request.GET.get('from') or ""
        message_text = request.GET.get('message') or request.GET.get('text') or request.GET.get('msg') or ""

    sender_number = str(sender_number).strip()
    message_text = str(message_text).strip()

    if not sender_number or not message_text:
        return JsonResponse({'status': 'error', 'message': 'Missing phoneNumber or message'}, status=400)

    try:
        sender_normalized = _normaliser_numero(sender_number)
    except Exception:
        sender_normalized = sender_number

    clean_msg = re.sub(r'\s+', ' ', message_text).strip().upper()

    command_type = 'INVALID'
    eleve = None
    response_text = ""
    is_authorized = False
    processed_successfully = False
    error_message = ""

    help_pattern = re.compile(r'^(HELP|AIDE)$')
    note_pattern = re.compile(r'^NOTE\s+([A-Z0-9\-]+)(?:\s+(T\d+|\d+))?$')
    solde_pattern = re.compile(r'^SOLDE\s+([A-Z0-9\-]+)$')
    abs_pattern = re.compile(r'^ABS(?:ENCE)?\s+([A-Z0-9\-]+)$')

    if help_pattern.match(clean_msg):
        command_type = 'HELP'
        response_text = "Yelen - Commandes: NOTE <matricule> [trimestre] (ex: NOTE BF-2026-0001 T1), SOLDE <matricule> (situation finance), ABS <matricule> (absences)."
        is_authorized = True
        processed_successfully = True
    else:
        match_note = note_pattern.match(clean_msg)
        match_solde = solde_pattern.match(clean_msg)
        match_abs = abs_pattern.match(clean_msg)

        matricule = ""
        trim_str = ""

        if match_note:
            command_type = 'NOTE'
            matricule = match_note.group(1)
            trim_str = match_note.group(2) or ""
        elif match_solde:
            command_type = 'SOLDE'
            matricule = match_solde.group(1)
        elif match_abs:
            command_type = 'ABS'
            matricule = match_abs.group(1)

        if command_type != 'INVALID':
            eleve = Eleve.objects.filter(matricule__iexact=matricule).first()
            if not eleve:
                error_message = f"Eleve avec le matricule {matricule} introuvable."
                response_text = f"Yelen - Eleve avec le matricule {matricule} introuvable."
            else:
                candidate_numbers = [
                    eleve.telephone_parent,
                    eleve.tuteur_telephone,
                    eleve.telephone_urgence,
                    eleve.telephone if hasattr(eleve, 'telephone') else ''
                ]
                normalized_candidates = []
                for c in candidate_numbers:
                    if c and str(c).strip():
                        try:
                            normalized_candidates.append(_normaliser_numero(str(c)))
                        except Exception:
                            pass

                master_numbers = getattr(settings, 'MASTER_SMS_NUMBERS', [])
                for mn in master_numbers:
                    if mn:
                        try:
                            normalized_candidates.append(_normaliser_numero(str(mn)))
                        except Exception:
                            pass

                if sender_normalized in normalized_candidates:
                    is_authorized = True
                    inscription = Inscription.objects.filter(eleve=eleve, annee_scolaire__est_courante=True).first()
                    if not inscription:
                        inscription = Inscription.objects.filter(eleve=eleve).order_by('-annee_scolaire__date_debut').first()

                    if not inscription:
                        error_message = "Aucune inscription trouvee pour cet eleve."
                        response_text = f"Yelen - {eleve.prenom} {eleve.nom} n'est inscrit dans aucune classe."
                    else:
                        if command_type == 'NOTE':
                            trim_num = None
                            if trim_str:
                                digits = re.findall(r'\d+', trim_str)
                                if digits:
                                    trim_num = int(digits[0])

                            mg_qs = MoyenneGenerale.objects.filter(inscription=inscription)
                            if trim_num is not None:
                                mg = mg_qs.filter(trimestre__numero=trim_num).first()
                                trim_label = f"T{trim_num}"
                            else:
                                mg = mg_qs.order_by('-trimestre__numero').first()
                                trim_label = mg.trimestre.nom if mg else "Trimestre"

                            if mg and mg.moyenne is not None:
                                total_eleves = Inscription.objects.filter(
                                    classe=inscription.classe,
                                    annee_scolaire=inscription.annee_scolaire
                                ).exclude(statut='ABANDON').count()

                                rang_str = f"{mg.rang}/{total_eleves}" if mg.rang else "N/A"
                                response_text = f"Yelen - {eleve.prenom} {eleve.nom} ({inscription.classe.nom}) - {trim_label}: Moy: {mg.moyenne}/20, Rang: {rang_str}."
                                processed_successfully = True
                            else:
                                error_message = f"Aucune moyenne trouvee pour la periode {trim_label}."
                                response_text = f"Yelen - Aucune moyenne trouvee pour {eleve.prenom} {eleve.nom} ({trim_label})."

                        elif command_type == 'SOLDE':
                            try:
                                sit = _calcul_situation_financiere(inscription)
                                total_du = sit['total_du']
                                total_paye = sit['total_paye']
                                reste = sit['reste_a_payer']

                                response_text = f"Yelen - {eleve.prenom} {eleve.nom} ({inscription.classe.nom}): Du {int(total_du)} FCFA, Paye {int(total_paye)} FCFA, Reste {int(reste)} FCFA."
                                processed_successfully = True
                            except Exception as e:
                                error_message = f"Erreur calcul solde: {str(e)}"
                                response_text = f"Yelen - Erreur lors de la recuperation du solde de {eleve.prenom} {eleve.nom}."

                        elif command_type == 'ABS':
                            try:
                                total_abs = Presence.objects.filter(inscription=inscription, statut=Presence.StatutChoices.ABSENT).count()
                                abs_justifiees = Presence.objects.filter(inscription=inscription, statut=Presence.StatutChoices.EXCUSE).count()
                                response_text = f"Yelen - {eleve.prenom} {eleve.nom} ({inscription.classe.nom}): {total_abs} absence(s) non justifiee(s), {abs_justifiees} excusee(s) cette annee."
                                processed_successfully = True
                            except Exception as e:
                                error_message = f"Erreur assiduite: {str(e)}"
                                response_text = f"Yelen - Erreur lors de la recuperation des absences de {eleve.prenom} {eleve.nom}."
                else:
                    error_message = f"Sender {sender_normalized} not authorized for matricule {matricule}."
                    response_text = "Yelen - Ce numero de telephone n'est pas autorise a consulter les informations de cet eleve."
        else:
            error_message = f"Commande invalide: '{message_text}'"
            response_text = "Yelen - Commande invalide. Envoyez AIDE pour obtenir la liste des commandes disponibles."

    log = IncomingSMSLog.objects.create(
        sender_number=sender_number,
        message_text=message_text,
        command_type=command_type,
        eleve=eleve,
        response_text=response_text[:160],
        is_authorized=is_authorized,
        processed_successfully=processed_successfully,
        error_message=error_message,
    )

    if response_text:
        envoyer_sms_async(sender_number, response_text[:160])

    return JsonResponse({
        'status': 'success' if processed_successfully else 'error',
        'response': response_text[:160],
        'log_id': str(log.pk)
    })
