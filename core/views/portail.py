"""Portails parent et élève (notes, bulletins, vie scolaire, notifications, push)."""

import io
import json
import os
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire
from licences.decorators import requires_licence_feature


PORTAILS = {
    'PARENT': {
        'role': 'PARENT', 'prefixe': '/portail/parent/', 'titre': 'Portail Parent', 'court': 'YELEN Parent',
        'manifest': '/manifest.json', 'sw': '/sw.js', 'cache': 'yelen-parent-v4',
        'accueil': 'core:portail_parent', 'vie_scolaire': 'core:portail_parent_vie_scolaire',
        'bulletins': 'core:portail_parent_bulletins', 'bulletin': 'core:portail_parent_bulletin',
        'cahier': 'core:portail_parent_cahier', 'notifications': 'core:portail_parent_notifications',
        'document': 'core:portail_parent_document', 'carte': 'core:portail_parent_carte',
    },
    'ELEVE': {
        'role': 'ELEVE', 'prefixe': '/portail/eleve/', 'titre': 'Portail Élève', 'court': 'YELEN Élève',
        'manifest': '/manifest-eleve.json', 'sw': '/sw-eleve.js', 'cache': 'yelen-eleve-v1',
        'accueil': 'core:portail_eleve', 'vie_scolaire': 'core:portail_eleve_vie_scolaire',
        'bulletins': 'core:portail_eleve_bulletins', 'bulletin': 'core:portail_eleve_bulletin',
        'cahier': 'core:portail_eleve_cahier', 'notifications': 'core:portail_eleve_notifications',
        'document': 'core:portail_eleve_document', 'carte': 'core:portail_eleve_carte',
    },
}


_REFUS_PORTAIL = "Accès réservé aux parents et aux élèves."


def _portail(request):
    """Configuration du portail du rôle connecté (PARENT ou ELEVE) — None pour les autres rôles. Le parent voit
    tous ses enfants (``eleves_lies``), l'élève son propre dossier (un seul élève lié). Les vues la nomment ``config``
    pour ne pas masquer le module ``core.portail``."""
    return PORTAILS.get(getattr(request.user, 'role', None))


@login_required
@requires_licence_feature('portail_parents')
def portail_parent(request):
    """Accueil du portail (parent : chaque enfant ; élève : son dossier) — PWA installable."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)

    from presences.models import Presence
    from pedagogie.models import MoyenneGenerale
    from pedagogie.notes_access import inscription_autorisee_notes
    from finances.models import Echeancier, Paiement
    from finances.views.commun import _situations_financieres_en_lot
    from core import portail

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
        if inscription and annee and inscription_autorisee_notes(inscription):
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

        situation = _situations_financieres_en_lot([inscription])[inscription.pk] if inscription else None
        total_paye = situation['total_paye'] if situation else 0
        prochaine_echeance = (
            Echeancier.objects.filter(inscription=inscription, is_active=True, paye=False, date_limite__gte=today)
            .order_by('date_limite').first()
        ) if inscription and situation and situation['reste_a_payer'] > 0 else None
        derniers_paiements = list(
            Paiement.objects.filter(inscription=inscription).select_related('rubrique')
            .order_by('-date_paiement', '-created_at')[:5]
        ) if inscription else []

        enfants.append({
            'eleve': eleve,
            'inscription': inscription,
            'derniere_mg': derniere_mg,
            'nb_absences_recentes': nb_absences_recentes,
            'total_paye': total_paye,
            'situation': situation,
            'prochaine_echeance': prochaine_echeance,
            'derniers_paiements': derniers_paiements,
            'devoirs_a_venir': portail.devoirs_a_venir(inscription) if inscription else [],
        })

    from core import push

    return render(request, 'core/portail_parent.html', {
        'enfants': enfants,
        'annee': annee,
        'portail': config,
        'push_cle_publique': push.cle_publique(),
    })


@login_required
@requires_licence_feature('portail_parents')
def portail_parent_bulletins(request):
    """Page bulletins PWA pour les parents."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)

    from bulletins.models import Bulletin
    from finances.blocage import motif_blocage_bulletin
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
            .select_related('classe', 'statut_eleve')
            .first()
        ) if annee else None

        bulletins = []
        blocage = motif_blocage_bulletin(inscription) if inscription else None
        if inscription and not blocage:
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
                'blocage': blocage,
            })

    from documents.models import Document
    documents = list(
        Document.objects.filter(inscription__eleve__in=eleves).exclude(fichier='')
        .select_related('type_document', 'inscription__eleve', 'annee_scolaire').order_by('-created_at')[:30]
    )
    return render(request, 'core/portail_parent_bulletins.html', {
        'enfants': enfants,
        'annee': annee,
        'portail': config,
        'documents': documents,
    })


@login_required
@requires_licence_feature('portail_parents')
def portail_bulletin(request, pk):
    """Consultation d'un bulletin publié depuis le portail (élève : lecture seule, sans accusé de réception)."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)
    from bulletins.models import Bulletin
    from finances.blocage import motif_blocage_bulletin
    from pedagogie.models import MoyenneGenerale
    bulletin = get_object_or_404(
        Bulletin.objects.select_related('inscription__eleve', 'inscription__classe', 'trimestre'),
        pk=pk, est_publie=True, inscription__eleve__in=request.user.eleves_lies.all(),
    )
    blocage = motif_blocage_bulletin(bulletin.inscription)
    if blocage:
        return render(request, 'bulletins/bulletin_parent.html', {'erreur': blocage})
    mg = MoyenneGenerale.objects.filter(inscription=bulletin.inscription, trimestre=bulletin.trimestre).first()
    return render(request, 'bulletins/bulletin_parent.html', {
        'bulletin': bulletin, 'mg': mg, 'token_valide': False, 'eleve': bulletin.inscription.eleve,
        'classe': bulletin.inscription.classe, 'trimestre': bulletin.trimestre,
    })


@login_required
@requires_licence_feature('portail_parents')
def portail_document(request, pk):
    """Téléchargement d'un document délivré à l'élève (certificat, attestation…) depuis le portail."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)
    from documents.models import Document
    document = get_object_or_404(Document.objects.exclude(fichier=''), pk=pk,
                                 inscription__eleve__in=request.user.eleves_lies.all())
    return FileResponse(document.fichier.open('rb'), as_attachment=True,
                        filename=os.path.basename(document.fichier.name))


@login_required
@requires_licence_feature('portail_parents')
def portail_carte_scolaire(request, pk):
    """Carte scolaire en PDF depuis le portail : l'élève pour lui-même, le parent pour ses enfants. C'est la pièce que
    l'élève présente à l'entrée ; le matricule qui y figure est son identifiant de connexion."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)
    from django.http import Http404
    from inscriptions.models import Eleve
    from inscriptions.views.documents import pdf_carte_scolaire

    eleve = get_object_or_404(Eleve, pk=pk, pk__in=request.user.eleves_lies.values('pk'))
    inscription = (
        Inscription.objects.filter(eleve=eleve, annee_scolaire__etablissement=request.user.etablissement,
                                   annee_scolaire__est_courante=True)
        .select_related('classe', 'annee_scolaire').first()
    ) or Inscription.objects.filter(eleve=eleve).select_related('classe', 'annee_scolaire').first()
    if inscription is None:
        raise Http404("Aucune inscription : la carte scolaire ne peut pas être établie.")
    pdf = pdf_carte_scolaire(request, eleve, inscription)
    if pdf is None:
        messages.error(request, "WeasyPrint n'est pas installé : la carte scolaire est indisponible.")
        return redirect(config['accueil'])
    return FileResponse(io.BytesIO(pdf), as_attachment=False, content_type='application/pdf',
                        filename=f"Carte_{eleve.nom}_{eleve.prenom}.pdf".replace(' ', '_'))


@login_required
@requires_licence_feature('portail_parents')
def portail_parent_notifications(request):
    """Page notifications PWA pour les parents."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)

    from core.models import Notification

    if request.method == 'POST' and request.POST.get('action') == 'tout_lu':
        Notification.objects.filter(destinataire=request.user, lu=False).update(lu=True)
        return redirect(config['notifications'])

    qs = Notification.objects.filter(destinataire=request.user)
    nb_non_lues = qs.filter(lu=False).count()
    qs.filter(lu=False).update(lu=True)
    notifications = qs.order_by('-created_at')[:50]

    from core import push

    return render(request, 'core/portail_parent_notifications.html', {
        'notifications': notifications,
        'nb_non_lues': nb_non_lues,
        'portail': config,
        'push_cle_publique': push.cle_publique(),
    })


def _reponse_push(ok, message, statut=200):
    return JsonResponse({'ok': ok, 'message': message}, status=statut)


def _requete_push(request):
    """(corps JSON, None) ou (None, réponse de refus)."""
    try:
        return json.loads(request.body or b'{}'), None
    except ValueError:
        return None, _reponse_push(False, "Requête illisible.", 400)


@login_required
@require_POST
def push_abonner(request):
    """Enregistre l'abonnement Web Push de l'appareil (``PushSubscription.toJSON()``)."""
    from core import push
    donnees, refus = _requete_push(request)
    if refus:
        return refus
    try:
        push.enregistrer_abonnement(request.user, donnees, request.META.get('HTTP_USER_AGENT', ''))
    except ValueError as erreur:
        return _reponse_push(False, str(erreur), 400)
    return _reponse_push(True, "Notifications activées sur cet appareil.")


@login_required
@require_POST
def push_desabonner(request):
    """Retire l'abonnement de l'appareil (``{endpoint}``)."""
    from core import push
    donnees, refus = _requete_push(request)
    if refus:
        return refus
    push.supprimer_abonnement(request.user, (donnees or {}).get('endpoint'))
    return _reponse_push(True, "Notifications désactivées sur cet appareil.")


@login_required
@require_POST
def push_test(request):
    """Envoie immédiatement une notification de test à l'appareil (``{endpoint}``) et rend compte du résultat."""
    from core import push
    from core.models import AbonnementPush
    donnees, refus = _requete_push(request)
    if refus:
        return refus
    abonnement = AbonnementPush.objects.filter(utilisateur=request.user, endpoint=(donnees or {}).get('endpoint') or '').first()
    if abonnement is None:
        return _reponse_push(False, "Cet appareil n'est pas abonné : activez d'abord les notifications.", 404)
    resultat = push.envoyer(abonnement, {
        'titre': "Notification de test", 'message': "Les notifications de YELEN SCHOOL fonctionnent sur cet appareil.",
        'url': push.page_notifications(request.user), 'tag': 'test',
    })
    messages_resultat = {
        push.OK: "Notification de test envoyée : elle s'affiche dans quelques secondes.",
        push.EXPIRE: "Cet appareil n'est plus abonné : désactivez puis réactivez les notifications.",
        push.INJOIGNABLE: "Le serveur de l'école n'a pas pu joindre le service de notifications (accès Internet du serveur ?).",
        push.REFUSE: "Le service de notifications a refusé l'envoi ; réessayez plus tard.",
    }
    return _reponse_push(resultat == push.OK, messages_resultat[resultat])


@login_required
@requires_licence_feature('portail_parents')
def portail_parent_vie_scolaire(request):
    """Vie scolaire PWA : emploi du temps, absences et retards, justificatifs, sanctions, notes récentes et moyennes
    par matière, pour chaque enfant (parent) ou pour l'élève connecté."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)
    from core import portail

    annee = AnneeScolaire.objects.filter(etablissement=request.user.etablissement, est_courante=True).first()
    enfants = []
    for eleve in request.user.eleves_lies.all():
        inscription = (
            Inscription.objects.filter(eleve=eleve, annee_scolaire=annee).select_related('classe').first()
        ) if annee else None
        if inscription is None:
            continue
        compteurs, absences = portail.assiduite(inscription)
        enfants.append({
            'eleve': eleve,
            'inscription': inscription,
            'edt': portail.emploi_du_temps(inscription),
            'compteurs': compteurs,
            'absences': absences,
            'justifications': portail.justifications(inscription),
            'sanctions': portail.sanctions(inscription),
            'notes_recentes': portail.notes_recentes(inscription),
            'moyennes_periodes': portail.moyennes_par_periode(inscription),
            'prets': portail.prets_en_cours(inscription),
        })
    return render(request, 'core/portail_parent_vie_scolaire.html', {
        'enfants': enfants,
        'annee': annee,
        'portail': config,
        'today': timezone.localdate(),
    })


@login_required
@requires_licence_feature('portail_parents')
def portail_parent_cahier(request):
    """Cahier de textes PWA : travail à faire et cours des 30 derniers jours, pour chaque enfant."""
    config = _portail(request)
    if not config:
        return HttpResponseForbidden(_REFUS_PORTAIL)
    from core import portail

    annee = AnneeScolaire.objects.filter(etablissement=request.user.etablissement, est_courante=True).first()
    enfants = []
    for eleve in request.user.eleves_lies.all():
        inscription = (
            Inscription.objects.filter(eleve=eleve, annee_scolaire=annee).select_related('classe').first()
        ) if annee else None
        if inscription is None:
            continue
        enfants.append({
            'eleve': eleve,
            'inscription': inscription,
            'devoirs': portail.devoirs_a_venir(inscription, limite=50),
            'cours': portail.cahier_de_textes(inscription),
        })
    return render(request, 'core/portail_parent_cahier.html', {
        'enfants': enfants,
        'annee': annee,
        'portail': config,
        'today': timezone.localdate(),
    })


@login_required
@require_POST
@requires_licence_feature('portail_parents')
def portail_parent_justifier(request):
    """Dépôt d'un justificatif d'absence par le parent (période, motif, pièce jointe) : « En attente » jusqu'à la
    décision du secrétariat."""
    if request.user.role != 'PARENT':
        return HttpResponseForbidden("Accès réservé aux parents.")
    from django.core.exceptions import ValidationError
    from core import portail

    inscription = Inscription.objects.filter(
        pk=request.POST.get('inscription') or None, eleve__in=request.user.eleves_lies.all(),
    ).select_related('eleve').first()
    if inscription is None:
        messages.error(request, "Enfant introuvable.")
        return redirect('core:portail_parent_vie_scolaire')
    try:
        justification = portail.deposer_justification(
            inscription, request.user, request.POST.get('date_debut'), request.POST.get('date_fin'),
            request.POST.get('motif'), request.FILES.get('document'),
        )
    except (ValueError, ValidationError) as exc:
        messages.error(request, ' '.join(exc.messages) if hasattr(exc, 'messages') else str(exc))
        return redirect('core:portail_parent_vie_scolaire')
    messages.success(request, f"Justificatif déposé pour {inscription.eleve.get_nom_complet()} "
                              f"({justification.nb_jours} jour{'s' if justification.nb_jours > 1 else ''}). "
                              "Le secrétariat l'examinera.")
    return redirect('core:portail_parent_vie_scolaire')
