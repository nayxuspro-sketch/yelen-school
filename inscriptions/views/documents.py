"""Documents PDF de l'élève : fiche, carte scolaire, cartes d'une classe."""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from ..models import Eleve, Inscription
from parametres.models import AnneeScolaire, SignataireDocument, TypeDocument
from core.utils import get_etablissement_context
logger = logging.getLogger(__name__)
try:
    from core.pdf import HTML as _WeasyHTML
except (ImportError, OSError) as exc:  # libpango/cairo absents
    logger.error("WeasyPrint indisponible, génération PDF désactivée : %s", exc)
    # Le serveur peut démarrer sans les bibliothèques système PDF ; les vues
    # concernées afficheront un message d'indisponibilité.
    _WeasyHTML = None

from .inscriptions import _get_inscription_courante


def _signataire_carte(cycle, annee):
    """Membre du personnel qui signe la Carte d'Identité Scolaire (cycle × année, repli progressif)."""
    type_doc, _ = TypeDocument.objects.get_or_create(
        code='CARTE_ID',
        defaults={'libelle': "Carte d'Identité Scolaire", 'categorie': 'SCOLARITE', 'actif': True},
    )
    signataire = SignataireDocument.objects.get_signataire(cycle=cycle, type_document=type_doc, annee_scolaire=annee)
    return signataire.get_membre_personnel() if signataire else None


@login_required
def eleve_fiche_pdf(request, pk):
    """Fiche individuelle de l'élève (A4 portrait, signée) : identité, scolarité, famille, santé, personnes autorisées,
    parcours — pour le dossier papier et la fiche d'urgence."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)
    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')
    if _WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('inscriptions:eleve_detail', pk=pk)
    inscription = _get_inscription_courante(eleve)
    etab_doc = inscription.classe.etablissement if inscription else etab
    context = {
        'eleve': eleve,
        'inscription': inscription,
        'parcours': eleve.inscriptions.select_related('annee_scolaire', 'classe', 'statut_eleve').order_by('-annee_scolaire__date_debut'),
        'personnes': [p.strip() for p in eleve.personnes_autorisees.splitlines() if p.strip()],
        'etablissement': etab_doc,
        'today': timezone.localdate(),
        **(get_etablissement_context(etab_doc, request) if etab_doc else {}),
    }
    html_str = render_to_string('inscriptions/pdf/fiche_eleve.html', context, request=request)
    pdf = _WeasyHTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
    filename = f"Fiche_{eleve.nom}_{eleve.prenom}.pdf".replace(" ", "_")
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def contexte_carte_scolaire(request, eleve, inscription=None):
    """Contexte de rendu de la carte scolaire (portail élève compris) : identité, logo et signataire de l'établissement."""
    if inscription is None:
        inscription = _get_inscription_courante(eleve)
    etab = inscription.classe.etablissement if inscription else None
    etab_context = get_etablissement_context(etab, request) if etab else {}
    return {
        'eleve': eleve,
        'inscription': inscription,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'sig_membre': _signataire_carte(inscription.classe.cycle if inscription else None,
                                        inscription.annee_scolaire if inscription else None),
    }


def pdf_carte_scolaire(request, eleve, inscription=None):
    """PDF de la carte scolaire d'un élève (octets), ou None si WeasyPrint est indisponible."""
    if _WeasyHTML is None:
        return None
    context = contexte_carte_scolaire(request, eleve, inscription)
    html_str = render_to_string('inscriptions/pdf/carte_scolaire.html', context, request=request)
    return _WeasyHTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()


@login_required
def eleve_carte(request, pk):
    """Aperçu et génération PDF de la carte scolaire d'un élève."""
    eleve = get_object_or_404(Eleve, pk=pk)
    context = contexte_carte_scolaire(request, eleve)

    if request.GET.get('format') == 'pdf':
        pdf = pdf_carte_scolaire(request, eleve, context['inscription'])
        if pdf is None:
            messages.error(request, "WeasyPrint n'est pas installé.")
            return redirect('inscriptions:eleve_detail', pk=pk)
        filename = f"Carte_{eleve.nom}_{eleve.prenom}.pdf".replace(" ", "_")
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    return render(request, 'inscriptions/carte_preview.html', context)


@login_required
def classe_cartes_pdf(request, pk):
    """Génère un PDF avec les cartes scolaires de tous les élèves d'une classe."""
    from parametres.models import Classe as _Classe
    if _WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('inscriptions:eleve_list')

    classe = get_object_or_404(_Classe, pk=pk)
    annee_id = request.GET.get('annee')
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee = AnneeScolaire.objects.filter(est_courante=True).first()
    if not annee:
        messages.error(request, "Aucune année scolaire disponible.")
        return redirect('inscriptions:eleve_list')

    inscriptions = Inscription.objects.filter(
        classe=classe, annee_scolaire=annee
    ).select_related('eleve', 'classe__cycle', 'classe__etablissement', 'annee_scolaire', 'statut_eleve'
    ).order_by('eleve__nom', 'eleve__prenom')

    etab = classe.etablissement
    etab_context = get_etablissement_context(etab, request)

    html_str = render_to_string('inscriptions/pdf/cartes_classe.html', {
        'inscriptions': inscriptions,
        'classe': classe,
        'annee': annee,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'sig_membre': _signataire_carte(classe.cycle, annee),
    }, request=request)

    pdf = _WeasyHTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
    filename = f"Cartes_{classe.nom}_{annee.libelle}.pdf".replace(" ", "_")
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
