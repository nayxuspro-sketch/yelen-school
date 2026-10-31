"""Préinscriptions en ligne : dépôt, décision et inscription."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from .. import services
from parametres.models import AnneeScolaire, Classe

from .rentree import _uuids


def _annee_preinscription(request, etab):
    """Année affichée : ``?annee=`` sinon l'année suivante si elle existe (campagne de rentrée), sinon la courante."""
    from ..models import PreInscription  # noqa: F401 — import local pour garder l'en-tête du module inchangé
    annees = list(AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')) if etab else []
    voulue = request.GET.get('annee') or request.POST.get('annee_filtre') or ''
    for a in annees:
        if str(a.pk) == voulue:
            return a, annees
    courante = next((a for a in annees if a.est_courante), None)
    suivante = services.annee_suivante(courante) if courante else None
    return suivante or courante, annees


@login_required
def preinscription_list(request):
    """Demandes d'inscription de nouveaux élèves : filtres, synthèse par classe (demandes / places), décisions."""
    from ..models import PreInscription
    from ..preinscriptions import synthese_par_classe
    etab = getattr(request.user, 'etablissement', None)
    annee, annees = _annee_preinscription(request, etab)
    statut = request.GET.get('statut', '')
    classe_id = request.GET.get('classe', '')
    demandes = (PreInscription.objects.filter(etablissement=etab, annee_scolaire=annee)
                .select_related('classe_demandee', 'created_by', 'decidee_par', 'inscription__eleve')) if (etab and annee) else PreInscription.objects.none()
    if statut in PreInscription.Statut.values:
        demandes = demandes.filter(statut=statut)
    if classe_id:
        demandes = demandes.filter(classe_demandee_id__in=_uuids([classe_id]))
    compteurs = {s: 0 for s, _ in PreInscription.Statut.choices}
    for ligne in PreInscription.objects.filter(etablissement=etab, annee_scolaire=annee).values_list('statut', flat=True) if (etab and annee) else []:
        compteurs[ligne] += 1
    return render(request, 'inscriptions/preinscription_list.html', {
        'annee': annee, 'annees': annees, 'statut': statut, 'classe_id': classe_id,
        'statuts': PreInscription.Statut.choices, 'compteurs': compteurs, 'total': sum(compteurs.values()),
        'demandes': demandes.order_by('statut', 'classe_demandee__nom', 'nom', 'prenom'),
        'synthese': synthese_par_classe(etab, annee) if (etab and annee) else [],
        'classes': Classe.objects.filter(etablissement=etab, actif=True).order_by('cycle__ordre', 'nom') if etab else [],
    })


@login_required
def preinscription_form(request, pk=None):
    """Enregistrer ou corriger une demande (une demande inscrite n'est plus modifiable)."""
    from ..forms import PreInscriptionForm
    from ..models import PreInscription
    etab = getattr(request.user, 'etablissement', None)
    pre = get_object_or_404(PreInscription, pk=pk, etablissement=etab) if pk else None
    if pre is not None and pre.statut == PreInscription.Statut.INSCRITE:
        messages.info(request, "Cette demande a déjà donné lieu à une inscription : modifiez la fiche de l'élève.")
        return redirect('inscriptions:preinscription_list')
    annee, _annees = _annee_preinscription(request, etab)
    if request.method == 'POST':
        form = PreInscriptionForm(request.POST, instance=pre, etablissement=etab, annee_defaut=annee)
        if form.is_valid():
            demande = form.save(commit=False)
            if pre is None:
                demande.created_by = request.user
            demande.save()
            messages.success(request, f"Pré-inscription de {demande.get_nom_complet()} enregistrée "
                                      f"({demande.classe_demandee.nom}, {demande.annee_scolaire.libelle}).")
            return redirect(f"{reverse('inscriptions:preinscription_list')}?annee={demande.annee_scolaire_id}")
    else:
        form = PreInscriptionForm(instance=pre, etablissement=etab, annee_defaut=annee)
    return render(request, 'inscriptions/preinscription_form.html', {'form': form, 'pre': pre})


@login_required
@require_POST
def preinscription_decider(request, pk):
    """Accepter, refuser ou remettre en attente une demande."""
    from django.utils import timezone
    from ..models import PreInscription
    etab = getattr(request.user, 'etablissement', None)
    pre = get_object_or_404(PreInscription, pk=pk, etablissement=etab)
    decision = request.POST.get('decision', '')
    if pre.statut == PreInscription.Statut.INSCRITE or decision not in ('ACCEPTEE', 'REFUSEE', 'EN_ATTENTE'):
        messages.error(request, "Décision impossible sur cette demande.")
    else:
        pre.statut = decision
        pre.decidee_par = request.user if decision != 'EN_ATTENTE' else None
        pre.decidee_le = timezone.now() if decision != 'EN_ATTENTE' else None
        pre.save(update_fields=['statut', 'decidee_par', 'decidee_le', 'updated_at'])
        messages.success(request, f"Demande de {pre.get_nom_complet()} : {pre.get_statut_display().lower()}.")
    return redirect(f"{reverse('inscriptions:preinscription_list')}?annee={pre.annee_scolaire_id}")


@login_required
@require_POST
def preinscription_inscrire(request, pk):
    """Crée l'élève et son inscription depuis la demande, puis ouvre l'inscription pour la compléter."""
    from ..models import PreInscription
    from ..preinscriptions import inscrire
    etab = getattr(request.user, 'etablissement', None)
    pre = get_object_or_404(PreInscription.objects.select_related('annee_scolaire', 'classe_demandee', 'etablissement'),
                            pk=pk, etablissement=etab)
    if pre.statut == PreInscription.Statut.REFUSEE:
        messages.error(request, "Demande refusée : remettez-la en attente ou acceptez-la avant d'inscrire l'élève.")
        return redirect(f"{reverse('inscriptions:preinscription_list')}?annee={pre.annee_scolaire_id}")
    inscription, erreur = inscrire(pre, request.user)
    if erreur:
        messages.error(request, erreur)
        return redirect(f"{reverse('inscriptions:preinscription_list')}?annee={pre.annee_scolaire_id}")
    messages.success(request, f"{pre.get_nom_complet()} inscrit(e) en {pre.classe_demandee.nom} "
                              f"(matricule {inscription.eleve.matricule}) : complétez l'inscription (statut, photo…).")
    return redirect('inscriptions:inscription_update', pk=inscription.pk)
