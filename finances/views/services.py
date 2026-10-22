"""Services annexes facturés — cantine, transport, internat : configuration, abonnements des élèves, listes d'abonnés.

Un service encaisse sur une rubrique de paiement ; chaque formule (zone, régime, repas…) a un tarif par période.
L'abonnement d'un élève fige le montant dû (tarif × périodes entre ses dates), qui s'ajoute à sa situation
financière : paiements, redevables, relances et Mobile Money le voient sans traitement particulier.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.excel import ExcelExport
from core.importation import en_date
from inscriptions.models import Inscription
from parametres.models import Classe, RubriquePaiement

from ..models import (
    CODES_RUBRIQUE_SERVICE, AbonnementService, FormuleService, Paiement, PeriodiciteService, Remboursement,
    ServiceAnnexe, TypeService,
)
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from ..selectors import annee_de_reference
from .commun import _require_finance_role, _require_same_establishment


def _etab(request):
    return getattr(request.user, 'etablissement', None)


def _services(etab):
    if etab is None:
        return ServiceAnnexe.objects.none()
    return ServiceAnnexe.objects.filter(etablissement=etab).select_related('rubrique').prefetch_related('formules')


def _abonnements(service):
    return (
        AbonnementService.objects.filter(formule__service=service, actif=True, is_active=True)
        .select_related('inscription__eleve', 'inscription__classe', 'formule')
    )


def _montant(brut):
    """Champ montant → Decimal strictement positif, ou None."""
    try:
        montant = Decimal((brut or '').replace(' ', '').replace(',', '.'))
    except InvalidOperation:
        return None
    return montant if montant.is_finite() and montant > 0 else None


def _dates(post, annee):
    """Dates de début et de fin du formulaire ; à défaut, aujourd'hui (dans l'année) → fin de l'année scolaire."""
    aujourd_hui = timezone.localdate()
    try:
        debut = en_date(post.get('date_debut'))
        fin = en_date(post.get('date_fin'))
    except ValueError:
        return None, None, "Dates invalides (jj/mm/aaaa)."
    if debut is None:
        debut = min(max(aujourd_hui, annee.date_debut), annee.date_fin) if annee else aujourd_hui
    if fin is None:
        fin = annee.date_fin if annee else debut
    if fin < debut:
        return None, None, "La date de fin précède la date de début."
    return debut, fin, None


# ── Services et formules ─────────────────────────────────────────────────

@login_required
def service_list(request):
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = _etab(request)
    annee = annee_de_reference(etab)
    services = list(_services(etab))
    abonnes = {
        s['formule__service_id']: s for s in AbonnementService.objects.filter(
            formule__service__in=services, actif=True, is_active=True, inscription__annee_scolaire=annee,
        ).values('formule__service_id').annotate(nb=Count('id'), du=Sum('montant_total'))
    }
    verses = {
        p['rubrique_id']: p['s'] for p in Paiement.objects.filter(
            rubrique__in=[s.rubrique_id for s in services], inscription__annee_scolaire=annee,
        ).values('rubrique_id').annotate(s=Sum('montant'))
    }
    for service in services:
        ligne = abonnes.get(service.pk, {})
        service.nb_abonnes = ligne.get('nb', 0)
        service.total_du = ligne.get('du') or Decimal('0')
        service.total_verse = verses.get(service.rubrique_id) or Decimal('0')
    return render(request, 'finances/services/service_list.html', {
        'services': services, 'annee': annee, 'types': TypeService.choices,
    })


@login_required
def service_form(request, pk=None):
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = _etab(request)
    service = get_object_or_404(ServiceAnnexe, pk=pk, etablissement=etab) if pk else None
    rubriques = RubriquePaiement.objects.filter(etablissement=etab).order_by('ordre', 'nom') if etab else []

    if request.method == 'POST' and etab is not None:
        type_service = request.POST.get('type_service', '')
        nom = request.POST.get('nom', '').strip()[:100]
        periodicite = request.POST.get('periodicite', '')
        rubrique = rubriques.filter(pk=request.POST.get('rubrique')).first() if request.POST.get('rubrique') else None
        erreurs = []
        if type_service not in TypeService.values:
            erreurs.append("Choisissez le type de service.")
        if not nom:
            erreurs.append("Le nom est obligatoire.")
        if periodicite not in PeriodiciteService.values:
            erreurs.append("Choisissez la périodicité des tarifs.")
        if nom and ServiceAnnexe.objects.filter(etablissement=etab, nom__iexact=nom).exclude(pk=pk).exists():
            erreurs.append(f"Un service « {nom} » existe déjà.")
        if erreurs:
            for erreur in erreurs:
                messages.error(request, erreur)
        else:
            if rubrique is None:
                # Rubrique dédiée créée à la volée : les encaissements du service y sont isolés dans les bilans.
                rubrique, _ = RubriquePaiement.objects.get_or_create(
                    etablissement=etab, code=CODES_RUBRIQUE_SERVICE[type_service],
                    defaults={'nom': nom, 'obligatoire': False, 'ordre': 90},
                )
            if service is None:
                service = ServiceAnnexe(etablissement=etab)
            service.type_service, service.nom, service.periodicite, service.rubrique = type_service, nom, periodicite, rubrique
            service.actif = request.POST.get('actif', 'on') == 'on'
            service.save()
            messages.success(request, f"Service « {service.nom} » enregistré.")
            return redirect('finances:service_list')

    post = request.POST if request.method == 'POST' else None
    valeurs = {
        'type_service': post.get('type_service', '') if post else (service.type_service if service else ''),
        'nom': post.get('nom', '') if post else (service.nom if service else ''),
        'periodicite': post.get('periodicite', '') if post else (service.periodicite if service else 'MENSUEL'),
        'rubrique': post.get('rubrique', '') if post else (str(service.rubrique_id) if service else ''),
        'actif': post.get('actif') == 'on' if post else (service.actif if service else True),
    }
    return render(request, 'finances/services/service_form.html', {
        'service': service, 'rubriques': rubriques, 'types': TypeService.choices,
        'periodicites': PeriodiciteService.choices, 'valeurs': valeurs,
    })


@login_required
def formule_form(request, service_id=None, pk=None):
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = _etab(request)
    formule = get_object_or_404(FormuleService, pk=pk, service__etablissement=etab) if pk else None
    service = formule.service if formule else get_object_or_404(ServiceAnnexe, pk=service_id, etablissement=etab)

    if request.method == 'POST':
        libelle = request.POST.get('libelle', '').strip()[:100]
        montant = _montant(request.POST.get('montant'))
        if not libelle:
            messages.error(request, "Le libellé est obligatoire.")
        elif montant is None:
            messages.error(request, "Montant invalide : indiquez un nombre strictement positif.")
        elif FormuleService.objects.filter(service=service, libelle__iexact=libelle).exclude(pk=pk).exists():
            messages.error(request, f"La formule « {libelle} » existe déjà pour ce service.")
        else:
            if formule is None:
                formule = FormuleService(service=service)
            formule.libelle, formule.montant = libelle, montant
            formule.actif = request.POST.get('actif', 'on') == 'on'
            formule.save()
            messages.success(request, f"Formule « {formule.libelle} » enregistrée.")
            return redirect('finances:service_list')

    post = request.POST if request.method == 'POST' else None
    valeurs = {
        'libelle': post.get('libelle', '') if post else (formule.libelle if formule else ''),
        'montant': post.get('montant', '') if post else (int(formule.montant) if formule else ''),
        'actif': post.get('actif') == 'on' if post else (formule.actif if formule else True),
    }
    return render(request, 'finances/services/formule_form.html', {'service': service, 'formule': formule, 'valeurs': valeurs})


# ── Abonnés d'un service ─────────────────────────────────────────────────

@login_required
def abonnes_list(request, pk):
    """Liste des élèves abonnés (cuisine, chauffeur, surveillant d'internat) avec leur solde sur la rubrique."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = _etab(request)
    service = get_object_or_404(_services(etab), pk=pk)
    annee = annee_de_reference(etab)
    abonnements = _abonnements(service).filter(inscription__annee_scolaire=annee)
    classes = Classe.objects.filter(inscriptions__in=[a.inscription_id for a in abonnements]).distinct().order_by('nom')
    classe_id, formule_id = request.GET.get('classe', ''), request.GET.get('formule', '')
    if classe_id:
        abonnements = abonnements.filter(inscription__classe_id=classe_id)
    if formule_id:
        abonnements = abonnements.filter(formule_id=formule_id)
    abonnements = list(abonnements.order_by('inscription__classe__nom', 'inscription__eleve__nom',
                                            'inscription__eleve__prenom'))

    ids = [a.inscription_id for a in abonnements]
    verses = {
        p['inscription_id']: p['s'] for p in Paiement.objects.filter(inscription_id__in=ids, rubrique=service.rubrique)
        .values('inscription_id').annotate(s=Sum('montant'))
    }
    rembourses = {
        r['paiement__inscription_id']: r['s'] for r in Remboursement.objects.filter(
            paiement__inscription_id__in=ids, paiement__rubrique=service.rubrique,
        ).values('paiement__inscription_id').annotate(s=Sum('montant'))
    }
    du_par_inscription = {}
    for a in abonnements:
        du_par_inscription[a.inscription_id] = du_par_inscription.get(a.inscription_id, Decimal('0')) + a.montant_total
    for a in abonnements:
        verse = (verses.get(a.inscription_id) or Decimal('0')) - (rembourses.get(a.inscription_id) or Decimal('0'))
        # Les versements de la rubrique couvrent d'abord les abonnements les plus anciens.
        a.verse = min(max(verse, Decimal('0')), a.montant_total)
        verses[a.inscription_id] = verse - a.verse
        rembourses.pop(a.inscription_id, None)
        a.reste = a.montant_total - a.verse
    totaux = {
        'du': sum((a.montant_total for a in abonnements), Decimal('0')),
        'verse': sum((a.verse for a in abonnements), Decimal('0')),
    }
    totaux['reste'] = totaux['du'] - totaux['verse']

    if request.GET.get('format') == 'xlsx':
        wb = ExcelExport(f"Abonnés {service.nom}")
        wb.add_title(f"{service.nom} — élèves abonnés", f"{annee.libelle if annee else ''} · {len(abonnements)} abonné(s)")
        wb.add_header(['Classe', 'Matricule', 'Nom', 'Prénom(s)', 'Formule', 'Du', 'Au', 'Périodes',
                       'Montant dû', 'Versé', 'Reste', 'Téléphone parents'])
        for a in abonnements:
            e = a.inscription.eleve
            wb.add_row([a.inscription.classe.nom, e.matricule, e.nom, e.prenom, a.formule.libelle,
                        a.date_debut.strftime('%d/%m/%Y'), a.date_fin.strftime('%d/%m/%Y'), a.nb_periodes,
                        int(a.montant_total), int(a.verse), int(a.reste), e.telephone_parent])
        return wb.response(f"abonnes_{service.type_service.lower()}.xlsx")

    return render(request, 'finances/services/abonnes_list.html', {
        'service': service, 'annee': annee, 'abonnements': abonnements, 'classes': classes,
        'formules': service.formules.all(), 'classe_id': classe_id, 'formule_id': formule_id, 'totaux': totaux,
        'nb_eleves': len(du_par_inscription),
    })


# ── Abonnements ──────────────────────────────────────────────────────────

def _formules_disponibles(etab):
    return (
        FormuleService.objects.filter(service__etablissement=etab, service__actif=True, actif=True)
        .select_related('service').order_by('service__type_service', 'service__nom', 'montant')
    )


@login_required
def abonnement_form(request, inscription_id=None, pk=None):
    """Souscription (depuis la situation financière de l'élève) ou modification d'un abonnement."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    abonnement = get_object_or_404(AbonnementService.objects.select_related('formule__service'), pk=pk) if pk else None
    inscription = abonnement.inscription if abonnement else get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe', 'annee_scolaire'), pk=inscription_id)
    _require_same_establishment(request, inscription)
    formules = _formules_disponibles(inscription.classe.etablissement_id)
    annee = inscription.annee_scolaire

    if request.method == 'POST':
        formule = formules.filter(pk=request.POST.get('formule')).first() if request.POST.get('formule') else None
        debut, fin, erreur = _dates(request.POST, annee)
        if formule is None:
            erreur = "Choisissez une formule."
        elif erreur is None:
            doublon = AbonnementService.objects.filter(
                inscription=inscription, formule__service=formule.service, actif=True, is_active=True,
            ).exclude(pk=pk).exists()
            if doublon:
                erreur = f"{inscription.eleve} est déjà abonné(e) à « {formule.service.nom} » : modifiez cet abonnement."
        if erreur:
            messages.error(request, erreur)
        else:
            if abonnement is None:
                abonnement = AbonnementService(inscription=inscription)
            abonnement.formule, abonnement.date_debut, abonnement.date_fin = formule, debut, fin
            abonnement.observation = request.POST.get('observation', '').strip()[:200]
            abonnement.calculer()
            abonnement.save()
            messages.success(request, f"{formule.service.nom} : {abonnement.periodes_libelle}, "
                                      f"{int(abonnement.montant_total):,} FCFA dus.".replace(',', ' '))
            return redirect('finances:situation_eleve', inscription_id=inscription.pk)

    debut, fin, _ = _dates({}, annee)
    if abonnement is not None:
        debut, fin = abonnement.date_debut, abonnement.date_fin
    post = request.POST if request.method == 'POST' else None
    valeurs = {
        'formule': post.get('formule', '') if post else (str(abonnement.formule_id) if abonnement else ''),
        'observation': post.get('observation', '') if post else (abonnement.observation if abonnement else ''),
        'date_debut': (post and post.get('date_debut')) or debut.strftime('%Y-%m-%d'),
        'date_fin': (post and post.get('date_fin')) or fin.strftime('%Y-%m-%d'),
    }
    return render(request, 'finances/services/abonnement_form.html', {
        'inscription': inscription, 'abonnement': abonnement, 'formules': formules, 'valeurs': valeurs,
    })


@login_required
@require_POST
def abonnement_annuler(request, pk):
    """Annule un abonnement (plus rien n'est dû) ; conservé pour l'historique."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    abonnement = get_object_or_404(AbonnementService.objects.select_related('inscription__classe', 'formule__service'), pk=pk)
    _require_same_establishment(request, abonnement.inscription)
    abonnement.actif = False
    abonnement.save(update_fields=['actif', 'updated_at'])
    messages.success(request, f"Abonnement « {abonnement.formule.service.nom} » annulé.")
    return redirect('finances:situation_eleve', inscription_id=abonnement.inscription_id)


@login_required
def abonnement_classe(request, pk):
    """Abonne d'un coup les élèves cochés d'une classe à une formule du service."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = _etab(request)
    service = get_object_or_404(_services(etab), pk=pk)
    annee = annee_de_reference(etab)
    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('cycle__ordre', 'niveau', 'nom')
    formules = service.formules.filter(actif=True)
    classe_id = request.POST.get('classe') or request.GET.get('classe', '')
    classe = classes.filter(pk=classe_id).first() if classe_id else None
    eleves = []
    if classe is not None and annee is not None:
        deja = set(_abonnements(service).filter(inscription__classe=classe).values_list('inscription_id', flat=True))
        eleves = list(Inscription.objects.filter(classe=classe, annee_scolaire=annee).exclude(statut='ABANDON')
                      .select_related('eleve').order_by('eleve__nom', 'eleve__prenom'))
        for ins in eleves:
            ins.deja_abonne = ins.pk in deja

    if request.method == 'POST' and request.POST.get('valider'):
        formule = formules.filter(pk=request.POST.get('formule')).first()
        debut, fin, erreur = _dates(request.POST, annee)
        choisis = [ins for ins in eleves if str(ins.pk) in request.POST.getlist('inscriptions') and not ins.deja_abonne]
        if formule is None:
            erreur = "Choisissez une formule."
        elif not choisis:
            erreur = erreur or "Cochez au moins un élève non encore abonné."
        if erreur:
            messages.error(request, erreur)
        else:
            with transaction.atomic():
                for ins in choisis:
                    abonnement = AbonnementService(inscription=ins, formule=formule, date_debut=debut, date_fin=fin)
                    abonnement.calculer()
                    abonnement.save()
            messages.success(request, f"{len(choisis)} élève(s) de {classe.nom} abonné(s) à « {service.nom} — "
                                      f"{formule.libelle} ».")
            return redirect('finances:abonnes_list', pk=service.pk)

    debut, fin, _ = _dates({}, annee)
    return render(request, 'finances/services/abonnement_classe.html', {
        'service': service, 'annee': annee, 'classes': classes, 'classe': classe, 'formules': formules,
        'eleves': eleves, 'date_debut': request.POST.get('date_debut') or debut.strftime('%Y-%m-%d'),
        'date_fin': request.POST.get('date_fin') or fin.strftime('%Y-%m-%d'),
        'formule_id': request.POST.get('formule', ''),
        'nb_restants': sum(1 for e in eleves if not e.deja_abonne),
    })
