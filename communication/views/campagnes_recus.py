"""Campagnes SMS ciblées, journal des SMS reçus et catalogue de commandes SMS."""
import logging
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from inscriptions.models import Eleve
from parametres.models import AnneeScolaire

from .commun import _get_etab, _sigle

logger = logging.getLogger(__name__)


# ─── CAMPAGNES SMS CIBLÉES ────────────────────────────────────────────

_ROLES_CAMPAGNE = ('SUPER_ADMIN', 'DIRECTEUR', 'CENSEUR', 'SECRETAIRE', 'COMPTABLE')


def _refus_campagne(request):
    if request.user.role in _ROLES_CAMPAGNE or request.user.is_superuser:
        return None
    return render(request, 'core/access_denied.html', {
        'message': "Les campagnes SMS sont réservées à la direction, au secrétariat et à la comptabilité.",
    }, status=403)


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
    from .. import campagnes

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
    from .. import campagnes
    refus = _refus_campagne(request)
    if refus:
        return refus
    campagne = get_object_or_404(CampagneSms, pk=pk, etablissement=_get_etab(request))
    nb = campagnes.renvoyer_echecs(campagne)
    messages.success(request, f"{nb} SMS remis en file." if nb else "Aucun SMS en échec.")
    return redirect('communication:campagne_detail', pk=campagne.pk)


@login_required
@require_POST
def campagne_supprimer(request, pk):
    """Supprime une campagne et ses SMS ; ceux encore en attente ne partiront pas."""
    from core.models import CampagneSms
    refus = _refus_campagne(request)
    if refus:
        return refus
    campagne = get_object_or_404(CampagneSms, pk=pk, etablissement=_get_etab(request))
    titre, nb_sms = campagne.titre, campagne.sms.count()
    campagne.delete()
    messages.success(request, f"Campagne « {titre} » supprimée ({nb_sms} SMS).")
    return redirect('communication:campagne_list')


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
    from ..models import IncomingSMSLog
    return IncomingSMSLog.objects.filter(is_active=True, command_type__in=IncomingSMSLog.A_LIRE, lu_le__isnull=True).count()


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
    from ..models import IncomingSMSLog

    type_ = request.GET.get('type') if request.GET.get('type') in ('commandes', 'ignores', 'tous') else 'libres'
    etat = request.GET.get('etat') if request.GET.get('etat') in ('non_lus', 'lus') else ''
    qs = IncomingSMSLog.objects.filter(is_active=True).select_related('eleve', 'lu_par', 'message_parent')
    if type_ == 'libres':
        qs = qs.filter(command_type__in=IncomingSMSLog.A_LIRE)
    elif type_ == 'commandes':
        qs = qs.exclude(command_type__in=IncomingSMSLog.A_LIRE + ('REFUSE',))
    elif type_ == 'ignores':
        qs = qs.filter(command_type='REFUSE')
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
    from ..models import IncomingSMSLog
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
    from ..models import IncomingSMSLog
    nb = IncomingSMSLog.objects.filter(is_active=True, command_type__in=IncomingSMSLog.A_LIRE, lu_le__isnull=True) \
        .update(lu_le=timezone.now(), lu_par=request.user)
    messages.success(request, f"{nb} message(s) marqué(s) comme lu(s).")
    return _retour_messages_recus(request)


def _supprimer_messages_recus(request, qs):
    """Retire des messages de la boîte. La ligne est conservée inactive : la relève de la boîte du téléphone
    reconnaît encore l'identifiant du SMS et ne le retraite pas (sinon il réapparaîtrait avec une nouvelle
    réponse automatique au parent)."""
    from ..models import IncomingSMSLog
    nb = IncomingSMSLog.objects.filter(pk__in=list(qs.values_list('pk', flat=True))) \
        .update(is_active=False, updated_at=timezone.now())
    messages.success(request, f"{nb} message(s) supprimé(s).")
    return _retour_messages_recus(request)


@login_required
@require_POST
def messages_recus_supprimer(request, pk):
    from ..models import IncomingSMSLog
    return _supprimer_messages_recus(request, IncomingSMSLog.objects.filter(pk=pk, is_active=True))


@login_required
@require_POST
def messages_recus_supprimer_selection(request):
    """Supprime les messages cochés (``ids``) ou, avec ``portee=lus``, tous les messages lus de la vue courante
    (``type`` = libres / commandes / tous)."""
    from ..models import IncomingSMSLog
    qs = IncomingSMSLog.objects.filter(is_active=True)
    if request.POST.get('portee') == 'lus':
        qs = qs.filter(lu_le__isnull=False)
        if request.POST.get('type') == 'libres':
            qs = qs.filter(command_type__in=IncomingSMSLog.A_LIRE)
        elif request.POST.get('type') == 'commandes':
            qs = qs.exclude(command_type__in=IncomingSMSLog.A_LIRE)
    else:
        ids = [i for i in request.POST.getlist('ids') if re.fullmatch(r'[0-9a-fA-F-]{36}', i)]
        if not ids:
            messages.error(request, "Cochez au moins un message à supprimer.")
            return _retour_messages_recus(request)
        qs = qs.filter(pk__in=ids)
    return _supprimer_messages_recus(request, qs)


@login_required
@require_POST
def messages_recus_repondre(request, pk):
    """Répond par SMS (160 caractères max.) au numéro du message : la réponse part par la file SMS et le message
    est marqué lu."""
    from core.sms import _normaliser_numero
    from core.tasks import envoyer_sms_async
    from ..models import IncomingSMSLog

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


# ─── COMMANDES SMS DÉFINIES PAR L'ÉCOLE ──────────────────────────────

@login_required
def commandes_sms(request):
    """Commandes automatiques de l'école (mot-clé → réponse), en plus de NOTE / SOLDE / ABS / AIDE."""
    from django.db.models import Count
    from .. import commandes
    from ..models import CommandeSms

    liste = CommandeSms.objects.filter(etablissement=_get_etab(request)).annotate(nb_utilisations=Count('utilisations'))
    return render(request, 'communication/commandes_sms.html', {
        'commandes': liste,
        'integrees': commandes.COMMANDES_INTEGREES,
        'texte_aide': commandes.texte_aide(),
    })


def _formulaire_commande(request, instance=None):
    from .. import commandes
    from ..models import CommandeSms

    etab = _get_etab(request)
    contexte = {
        'instance': instance,
        'portees': CommandeSms.Portee.choices,
        'variables_ecole': commandes.VARIABLES_ECOLE,
        'variables_eleve': commandes.VARIABLES_ELEVE,
        'longueur': CommandeSms.LONGUEUR_REPONSE,
        'reserves': CommandeSms.RESERVES,
        'valeurs': {
            'mot_cle': instance.mot_cle if instance else '',
            'alias': instance.alias if instance else '',
            'portee': instance.portee if instance else CommandeSms.Portee.ECOLE,
            'description': instance.description if instance else '',
            'reponse': instance.reponse if instance else '',
            'actif': instance.actif if instance else True,
        },
        'erreurs': [],
    }
    if request.method != 'POST':
        return render(request, 'communication/commande_sms_form.html', contexte)

    champs, erreurs = commandes.valider(request.POST, etab, instance)
    contexte['valeurs'] = champs
    if erreurs:
        contexte['erreurs'] = erreurs
        return render(request, 'communication/commande_sms_form.html', contexte, status=400)
    if instance is None:
        instance = CommandeSms(etablissement=etab, created_by=request.user)
    for champ, valeur in champs.items():
        setattr(instance, champ, valeur)
    instance.save()
    messages.success(request, f"Commande {instance.mot_cle} enregistrée : les parents peuvent l'envoyer au numéro de l'école.")
    return redirect('communication:commandes_sms')


@login_required
def commande_sms_nouvelle(request):
    return _formulaire_commande(request)


@login_required
def commande_sms_modifier(request, pk):
    from ..models import CommandeSms
    return _formulaire_commande(request, get_object_or_404(CommandeSms, pk=pk, etablissement=_get_etab(request)))


@login_required
@require_POST
def commande_sms_basculer(request, pk):
    """Active / désactive une commande sans la supprimer (ex. HORAIRES pendant les vacances)."""
    from ..models import CommandeSms
    commande = get_object_or_404(CommandeSms, pk=pk, etablissement=_get_etab(request))
    commande.actif = not commande.actif
    commande.save(update_fields=['actif', 'updated_at'])
    messages.success(request, f"Commande {commande.mot_cle} {'activée' if commande.actif else 'désactivée'}.")
    return redirect('communication:commandes_sms')


@login_required
@require_POST
def commande_sms_supprimer(request, pk):
    from ..models import CommandeSms
    commande = get_object_or_404(CommandeSms, pk=pk, etablissement=_get_etab(request))
    mot = commande.mot_cle
    commande.delete()
    messages.success(request, f"Commande {mot} supprimée. Les SMS déjà reçus restent dans Messages reçus.")
    return redirect('communication:commandes_sms')
