"""Réinscriptions, passage de classe et préparation de la rentrée."""

import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from .. import services
from ..models import Eleve, Inscription, StatutInscriptionChoices
from parametres.models import AnneeScolaire, Classe, StatutEleve
from parametres.niveaux import rang_niveau


def _contexte_rentree(request):
    """Établissement, année courante et année suivante (None si elle n'est pas encore créée)."""
    etab = getattr(request.user, 'etablissement', None)
    annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first() if etab else None
    annee_suiv = services.annee_suivante(annee_courante) if annee_courante else None
    return etab, annee_courante, annee_suiv


def _classes_par_niveau(etab):
    classes = list(Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle'))
    classes.sort(key=lambda c: (rang_niveau(c.niveau), c.nom))
    return classes


def _uuids(valeurs):
    """Ne conserve que les identifiants bien formés (un paramètre altéré ne doit pas provoquer d'erreur 500)."""
    propres = []
    for valeur in valeurs:
        try:
            propres.append(uuid.UUID(str(valeur)))
        except ValueError:
            continue
    return propres


@login_required
def reinscription_list(request):
    """Passage de classe : élèves de l'année courante (hors abandon) non encore inscrits pour l'année suivante,
    avec la dernière décision du conseil de classe et la classe de destination proposée. Réinscription par lot
    (``passage_classe``) ou un par un (``reinscrire_eleve``)."""
    etab, annee_courante, annee_suiv = _contexte_rentree(request)
    if not annee_suiv:
        messages.warning(request, "Aucune année scolaire suivante trouvée pour la réinscription.")
    classe_filtre = request.GET.get('classe', '') if _uuids([request.GET.get('classe', '')]) else ''
    lignes, classes, classes_courantes = [], [], []
    if annee_courante and annee_suiv:
        classes = _classes_par_niveau(etab)
        classes_courantes = sorted(
            Classe.objects.filter(inscriptions__annee_scolaire=annee_courante, etablissement=etab).distinct(),
            key=lambda c: (rang_niveau(c.niveau), c.nom))
        inscriptions = (
            Inscription.objects.filter(annee_scolaire=annee_courante, classe__etablissement=etab)
            .exclude(statut=StatutInscriptionChoices.ABANDON)
            .exclude(eleve__inscriptions__annee_scolaire=annee_suiv)
            .select_related('eleve', 'classe', 'statut_eleve')
        )
        if classe_filtre:
            inscriptions = inscriptions.filter(classe_id=classe_filtre)
        decisions = services.decisions_par_inscription(annee_courante)
        for ins in sorted(inscriptions, key=lambda i: (rang_niveau(i.classe.niveau), i.classe.nom,
                                                       i.eleve.nom, i.eleve.prenom)):
            decision = decisions.get(ins.pk, '')
            lignes.append({
                'inscription': ins,
                'decision': services.libelle_decision(decision),
                'proposee': services.classe_proposee(ins, decision, classes),
            })
    return render(request, 'inscriptions/reinscription_list.html', {
        'lignes': lignes,
        'classes': classes,
        'classes_courantes': classes_courantes,
        'classe_filtre': classe_filtre,
        'annee_courante': annee_courante,
        'annee_suivante': annee_suiv,
    })


@login_required
@require_POST
def passage_classe(request):
    """Réinscrit par lot les élèves cochés dans la classe choisie pour l'année suivante ; chaque refus
    (classe complète, année clôturée, déjà inscrit) est signalé sans bloquer les autres."""
    etab, annee_courante, annee_suiv = _contexte_rentree(request)
    retour = reverse('inscriptions:reinscription_list')
    if _uuids([request.POST.get('classe_filtre', '')]):
        retour += '?classe=' + request.POST['classe_filtre']
    if not annee_suiv:
        messages.error(request, "Aucune année scolaire suivante : créez-la dans Paramètres → Années scolaires.")
        return redirect(retour)
    classes = {str(c.pk): c for c in Classe.objects.filter(etablissement=etab, actif=True)}
    inscriptions = (
        Inscription.objects.filter(pk__in=_uuids(request.POST.getlist('inscriptions')), annee_scolaire=annee_courante,
                                   classe__etablissement=etab)
        .exclude(statut=StatutInscriptionChoices.ABANDON)
        .select_related('eleve', 'classe', 'statut_eleve')
    )
    faits, erreurs = 0, []
    for ins in inscriptions:
        nom = ins.eleve.get_nom_complet()
        classe = classes.get(request.POST.get(f'classe_{ins.pk}', ''))
        if not classe:
            erreurs.append(f"{nom} : aucune classe de destination choisie.")
            continue
        try:
            services.reinscrire(ins, classe, annee_suiv)
            faits += 1
        except services.InscriptionImpossible as exc:
            erreurs.append(f"{nom} : {exc}")
    if faits:
        messages.success(request, f"{faits} élève(s) inscrit(s) pour {annee_suiv.libelle}.")
    elif not erreurs:
        messages.warning(request, "Aucun élève coché.")
    for erreur in erreurs[:10]:
        messages.error(request, erreur)
    if len(erreurs) > 10:
        messages.error(request, f"… et {len(erreurs) - 10} autre(s) élève(s) non inscrit(s).")
    return redirect(retour)


@login_required
def reinscrire_eleve(request, pk):
    """Réinscrit un élève pour l'année suivante : classe proposée d'après la décision du conseil, statut élève
    repris (modifiable), capacité et clôture contrôlées."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab, annee_courante, annee_suiv = _contexte_rentree(request)
    if not annee_suiv:
        messages.error(request, "Aucune année scolaire suivante : créez-la dans Paramètres → Années scolaires.")
        return redirect('inscriptions:reinscription_list')
    inscription = (
        Inscription.objects.filter(eleve=eleve, annee_scolaire=annee_courante, classe__etablissement=etab)
        .exclude(statut=StatutInscriptionChoices.ABANDON).select_related('classe', 'statut_eleve').first()
    )
    if not inscription:
        messages.error(request, f"{eleve.get_nom_complet()} n'a pas d'inscription active pour {annee_courante.libelle} "
                                "dans votre établissement.")
        return redirect('inscriptions:reinscription_list')
    classes = _classes_par_niveau(etab)
    statuts = StatutEleve.objects.filter(etablissement=etab, actif=True).order_by('ordre', 'nom')
    decision = services.decisions_par_inscription(annee_courante).get(inscription.pk, '')
    proposee = services.classe_proposee(inscription, decision, classes)
    classe_choisie = proposee

    if request.method == 'POST':
        classe_choisie = next((c for c in classes if str(c.pk) == request.POST.get('classe', '')), None)
        statut = statuts.filter(pk__in=_uuids([request.POST.get('statut_eleve', '')])).first()
        if not classe_choisie:
            messages.error(request, "Veuillez sélectionner une classe.")
        else:
            try:
                services.reinscrire(inscription, classe_choisie, annee_suiv, statut)
            except services.InscriptionImpossible as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"{eleve.get_nom_complet()} inscrit(e) en {classe_choisie.nom} "
                                          f"pour {annee_suiv.libelle}.")
                return redirect('inscriptions:reinscription_list')

    return render(request, 'inscriptions/reinscrire_eleve.html', {
        'eleve': eleve,
        'inscription': inscription,
        'classes': classes,
        'statuts': statuts,
        'classe_choisie': classe_choisie,
        'decision': services.libelle_decision(decision),
        'annee': annee_suiv,
    })
