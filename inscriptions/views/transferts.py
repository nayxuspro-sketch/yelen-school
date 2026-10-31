"""Transferts inter-établissements : demande, décision et dossier PDF."""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from ..models import Inscription, EvenementParcours, StatutInscriptionChoices, TransfertEleve
from core.utils import get_etablissement_context
from parametres.droits import autorise_url
logger = logging.getLogger(__name__)
try:
    from core.pdf import HTML as _WeasyHTML
except (ImportError, OSError) as exc:  # libpango/cairo absents
    logger.error("WeasyPrint indisponible, génération PDF désactivée : %s", exc)
    # Le serveur peut démarrer sans les bibliothèques système PDF ; les vues
    # concernées afficheront un message d'indisponibilité.
    _WeasyHTML = None


@login_required
def transfert_inter_list(request):
    """Liste tous les transferts inter-établissements de l'établissement."""
    etab = getattr(request.user, 'etablissement', None)
    qs = (
        TransfertEleve.objects
        .select_related('inscription__eleve', 'inscription__classe', 'inscription__annee_scolaire', 'demandeur')
        .filter(inscription__classe__etablissement=etab)
        .order_by('-date_demande')
    ) if etab else TransfertEleve.objects.none()

    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '').strip()
    if statut:
        qs = qs.filter(statut=statut)
    if q:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=q) |
            Q(inscription__eleve__prenom__icontains=q) |
            Q(inscription__eleve__matricule__icontains=q) |
            Q(etablissement_destination__icontains=q)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inscriptions/transfert_inter_list.html', {
        'page_obj': page_obj,
        'statut': statut,
        'q': q,
        'statut_choices': TransfertEleve.StatutChoices.choices,
        'nb_en_attente': qs.filter(statut='EN_ATTENTE').count() if not statut else 0,
    })


@login_required
def transfert_inter_demander(request, inscription_id):
    """Formulaire de demande de transfert inter-établissements."""
    etab = getattr(request.user, 'etablissement', None)
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe', 'annee_scolaire'),
        pk=inscription_id,
    )
    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:eleve_list')
    if inscription.statut == StatutInscriptionChoices.ABANDON:
        messages.error(request, "Cet élève est déjà en statut Abandon.")
        return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)
    # Vérifier qu'il n'y a pas déjà un transfert en attente
    if TransfertEleve.objects.filter(inscription=inscription, statut='EN_ATTENTE').exists():
        messages.warning(request, "Une demande de transfert est déjà en cours pour cet élève.")
        return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)

    if request.method == 'POST':
        dest = request.POST.get('etablissement_destination', '').strip()
        motif = request.POST.get('motif', '').strip()
        if not dest:
            messages.error(request, "L'établissement de destination est obligatoire.")
        else:
            transfert = TransfertEleve.objects.create(
                inscription=inscription,
                etablissement_destination=dest,
                motif=motif,
                demandeur=request.user,
            )
            messages.success(request, f"Demande de transfert créée pour {inscription.eleve.get_nom_complet()}.")
            return redirect('inscriptions:transfert_inter_detail', pk=transfert.pk)

    return render(request, 'inscriptions/transfert_inter_form.html', {
        'inscription': inscription,
    })


@login_required
def transfert_inter_detail(request, pk):
    """Détail d'un transfert inter-établissements."""
    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(
        TransfertEleve.objects.select_related(
            'inscription__eleve', 'inscription__classe', 'inscription__annee_scolaire',
            'demandeur', 'traite_par',
        ),
        pk=pk,
    )
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')

    # Situation financière
    from finances.models import Paiement, Echeancier
    paiements = Paiement.objects.filter(inscription=transfert.inscription).order_by('date_paiement')
    total_paye = sum(p.montant for p in paiements)
    echeances = Echeancier.objects.filter(inscription=transfert.inscription)
    total_du = sum(e.montant_du for e in echeances if not e.paye)

    # Historique des inscriptions
    inscriptions_historique = (
        Inscription.objects
        .filter(eleve=transfert.inscription.eleve)
        .select_related('classe', 'annee_scolaire')
        .order_by('annee_scolaire__date_debut')
    )

    return render(request, 'inscriptions/transfert_inter_detail.html', {
        'transfert': transfert,
        'paiements': paiements,
        'total_paye': total_paye,
        'total_du': total_du,
        'inscriptions_historique': inscriptions_historique,
        'can_approve': autorise_url(request, 'inscriptions:transfert_inter_approuver'),
    })


@login_required
@require_POST
def transfert_inter_approuver(request, pk):
    """Approuve un transfert : marque l'inscription ABANDON + crée EvenementParcours."""
    if not autorise_url(request, 'inscriptions:transfert_inter_approuver'):
        messages.error(request, "Vous n'avez pas les droits pour approuver un transfert.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(
        TransfertEleve.objects.select_related('inscription__eleve', 'inscription__annee_scolaire'),
        pk=pk,
    )
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')
    if transfert.statut != 'EN_ATTENTE':
        messages.warning(request, "Ce transfert a déjà été traité.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    from django.utils import timezone

    # Mettre à jour le transfert
    transfert.statut = 'APPROUVE'
    transfert.date_traitement = timezone.now().date()
    transfert.traite_par = request.user
    transfert.notes_admin = request.POST.get('notes_admin', '').strip()
    transfert.save(update_fields=['statut', 'date_traitement', 'traite_par', 'notes_admin'])

    # Marquer l'inscription comme abandon
    ins = transfert.inscription
    ins.statut = StatutInscriptionChoices.ABANDON
    ins.save(update_fields=['statut'])

    # Mettre à jour l'élève (dernière classe connue)
    eleve = ins.eleve
    eleve.last_classe = ins.classe.nom
    eleve.last_annee = ins.annee_scolaire.libelle
    eleve.etablissement_origine = ins.classe.etablissement.nom if hasattr(ins.classe, 'etablissement') else ''
    eleve.save(update_fields=['last_classe', 'last_annee', 'etablissement_origine'])

    # Créer l'événement de parcours
    EvenementParcours.objects.create(
        eleve=eleve,
        type_evenement=EvenementParcours.TypeEvenement.TRANSFERT_SORTANT,
        annee_scolaire=ins.annee_scolaire,
        inscription=ins,
        date_evenement=transfert.date_traitement,
        motif=transfert.motif,
        etablissement_transfert=transfert.etablissement_destination,
        enregistre_par=request.user,
    )

    messages.success(request, f"Transfert approuvé. {eleve.get_nom_complet()} est désormais marqué(e) en départ.")
    return redirect('inscriptions:transfert_inter_detail', pk=pk)


@login_required
@require_POST
def transfert_inter_refuser(request, pk):
    """Refuse un transfert."""
    if not autorise_url(request, 'inscriptions:transfert_inter_refuser'):
        messages.error(request, "Vous n'avez pas les droits pour refuser un transfert.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(TransfertEleve, pk=pk)
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')
    if transfert.statut != 'EN_ATTENTE':
        messages.warning(request, "Ce transfert a déjà été traité.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    from django.utils import timezone
    transfert.statut = 'REFUSE'
    transfert.date_traitement = timezone.now().date()
    transfert.traite_par = request.user
    transfert.notes_admin = request.POST.get('notes_admin', '').strip()
    transfert.save(update_fields=['statut', 'date_traitement', 'traite_par', 'notes_admin'])

    messages.success(request, "Transfert refusé.")
    return redirect('inscriptions:transfert_inter_detail', pk=pk)


@login_required
def transfert_inter_dossier_pdf(request, pk):
    """Génère le dossier de transfert PDF : infos élève, cursus, situation financière."""
    if _WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur le serveur.")
        return redirect('inscriptions:transfert_inter_detail', pk=pk)

    etab = getattr(request.user, 'etablissement', None)
    transfert = get_object_or_404(
        TransfertEleve.objects.select_related(
            'inscription__eleve', 'inscription__classe__cycle',
            'inscription__annee_scolaire', 'demandeur', 'traite_par',
        ),
        pk=pk,
    )
    if etab and transfert.inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé.")
        return redirect('inscriptions:transfert_inter_list')

    eleve = transfert.inscription.eleve

    # Cursus complet
    inscriptions_historique = (
        Inscription.objects
        .filter(eleve=eleve)
        .select_related('classe', 'annee_scolaire')
        .order_by('annee_scolaire__date_debut')
    )

    # Situation financière
    from finances.models import Paiement, Echeancier
    paiements = list(Paiement.objects.filter(inscription=transfert.inscription).order_by('date_paiement'))
    total_paye = sum(p.montant for p in paiements)
    echeances = list(Echeancier.objects.filter(inscription=transfert.inscription))
    total_du = sum(e.montant_du for e in echeances if not e.paye)

    etab_context = get_etablissement_context(etab, request)

    html_string = render_to_string('inscriptions/pdf/dossier_transfert.html', {
        'transfert': transfert,
        'inscription': transfert.inscription,
        'eleve': eleve,
        'inscriptions_historique': inscriptions_historique,
        'paiements': paiements,
        'total_paye': total_paye,
        'total_du': total_du,
        'echeances': echeances,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
    })

    pdf_file = _WeasyHTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    nom = f"{eleve.nom}_{eleve.prenom}".replace(' ', '_')
    filename = f"Dossier_Transfert_{nom}.pdf"
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
