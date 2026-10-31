"""Tableau de bord, recherche globale, pilotage et assistant de démarrage."""

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from personnel.models import MembrePersonnel
from inscriptions.models import Eleve, Inscription, StatutInscriptionChoices
from parametres.models import AnneeScolaire, Classe
from finances.models import Paiement


@login_required
def home(request):
    """Tableau de bord principal — adapté au rôle de l'utilisateur."""
    role = request.user.role

    # Rediriger les portails dédiés
    if role == 'PARENT':
        return redirect('core:portail_parent')
    if role == 'ELEVE':
        return redirect('core:portail_eleve')

    annee_courante = AnneeScolaire.objects.filter(
        etablissement=request.user.etablissement, est_courante=True
    ).first() if request.user.etablissement else AnneeScolaire.objects.filter(est_courante=True).first()
    etab = getattr(request.user, 'etablissement', None)

    # ── Base commune (tous les rôles) ─────────────────────────────────
    inscriptions_annee = (
        Inscription.objects.filter(annee_scolaire=annee_courante)
        .exclude(statut=StatutInscriptionChoices.ABANDON).count()
        if annee_courante else 0
    )
    nb_classes = Classe.objects.filter(etablissement=etab, actif=True).count() if etab else 0

    # ── Calendrier scolaire ─────────────────────────────────────────────
    from parametres.models import EvenementCalendrier
    if annee_courante and etab:
        evenements_calendrier = EvenementCalendrier.objects.filter(
            annee_scolaire=annee_courante,
            etablissement=etab,
        ).order_by('date_debut')[:10]
    else:
        evenements_calendrier = []

    context = {
        'annee_courante': annee_courante,
        'inscriptions_annee': inscriptions_annee,
        'nb_classes': nb_classes,
        'role': role,
        'evenements_calendrier': evenements_calendrier,
    }

    # ── DIRECTEUR / CENSEUR / SUPER_ADMIN ─────────────────────────────
    if role in ('DIRECTEUR', 'CENSEUR', 'SUPER_ADMIN'):
        from presences.models import Presence, Justification
        from viescolaire.models import SanctionDisciplinaire
        from parametres.models import Cycle
        from django.utils import timezone

        context['total_eleves'] = Eleve.objects.filter(
            inscriptions__annee_scolaire=annee_courante
        ).distinct().count() if annee_courante else Eleve.objects.count()
        context['total_personnel'] = MembrePersonnel.objects.filter(etablissement=etab).count()

        qs_fin = (
            Paiement.objects.filter(inscription__annee_scolaire=annee_courante)
            if annee_courante else Paiement.objects.none()
        )
        context['encaissements_annee'] = qs_fin.aggregate(total=Sum('montant'))['total'] or 0
        context['nb_paiements'] = qs_fin.count()

        context['nb_absences_aujourd_hui'] = Presence.objects.filter(
            statut='ABSENT', appel__date=timezone.now().date(), appel__classe__etablissement=etab,
        ).count()
        context['nb_justifications_attente'] = Justification.objects.filter(
            statut='EN_ATTENTE',
            inscription__annee_scolaire=annee_courante,
        ).count() if annee_courante else 0
        context['nb_sanctions_recentes'] = SanctionDisciplinaire.objects.filter(
            inscription__annee_scolaire=annee_courante,
            date_sanction__gte=timezone.now().date() - timezone.timedelta(days=7),
        ).count() if annee_courante else 0

        nb_par_cycle = dict(
            Inscription.objects.filter(
                annee_scolaire=annee_courante,
                classe__cycle__etablissement=etab,
            ).exclude(statut=StatutInscriptionChoices.ABANDON)
            .values('classe__cycle_id')
            .annotate(nb=Count('id'))
            .values_list('classe__cycle_id', 'nb')
        ) if (annee_courante and etab) else {}
        cycles = Cycle.objects.filter(etablissement=etab, actif=True).order_by('ordre') if etab else []
        context['repartition_cycles'] = [
            {'cycle': c, 'nb': nb_par_cycle.get(c.pk, 0)} for c in cycles
        ]

        # ── Widget IA décrochage ──────────────────────────────────────
        from pedagogie.models import RisqueDecrochage
        if annee_courante:
            risques_qs = RisqueDecrochage.objects.filter(
                inscription__annee_scolaire=annee_courante,
            ).select_related('inscription__eleve', 'inscription__classe')

            context['risques_critiques'] = list(
                risques_qs.filter(niveau=RisqueDecrochage.NiveauChoices.CRITIQUE)
                .order_by('-score')[:8]
            )
            context['risques_eleves'] = list(
                risques_qs.filter(niveau=RisqueDecrochage.NiveauChoices.ELEVE)
                .order_by('-score')[:8]
            )
            context['nb_risques_critiques'] = risques_qs.filter(
                niveau=RisqueDecrochage.NiveauChoices.CRITIQUE
            ).count()
            context['nb_risques_eleves'] = risques_qs.filter(
                niveau=RisqueDecrochage.NiveauChoices.ELEVE
            ).count()
            context['nb_risques_moderes'] = risques_qs.filter(
                niveau=RisqueDecrochage.NiveauChoices.MODERE
            ).count()
        else:
            context['risques_critiques'] = []
            context['risques_eleves'] = []
            context['nb_risques_critiques'] = 0
            context['nb_risques_eleves'] = 0
            context['nb_risques_moderes'] = 0

    # ── ENSEIGNANT ────────────────────────────────────────────────────
    elif role == 'ENSEIGNANT':
        from core.utils import filtre_enseignant
        from pedagogie.models import Enseignement, Evaluation, Resultat

        # Périmètre de l'enseignant : ses enseignements (fiche du personnel reliée par e-mail).
        mes_enseignements = Enseignement.objects.filter(
            annee_scolaire=annee_courante, est_actif=True, personnel=filtre_enseignant(request.user),
        ) if annee_courante else Enseignement.objects.none()
        context['nb_enseignements'] = mes_enseignements.count()

        context['evaluations_recentes'] = list(
            Evaluation.objects
            .filter(enseignement__in=mes_enseignements)
            .select_related('enseignement__classe', 'enseignement__matiere')
            .order_by('-date_planifiee')[:5]
        )

        context['nb_evaluations_annee'] = 0
        context['nb_eleves_sans_notes'] = 0
        if annee_courante:
            context['nb_evaluations_annee'] = Evaluation.objects.filter(
                trimestre__annee_scolaire=annee_courante
            ).count()
            context['nb_eleves_sans_notes'] = Resultat.objects.filter(
                trimestre__annee_scolaire=annee_courante,
                moyenne__isnull=True,
            ).values('inscription').distinct().count()

    # ── COMPTABLE ─────────────────────────────────────────────────────
    elif role == 'COMPTABLE':
        from django.utils import timezone

        aujourd_hui = timezone.now().date()
        debut_mois = aujourd_hui.replace(day=1)

        paiements_aujourd_hui = (
            Paiement.objects.filter(date_paiement=aujourd_hui)
            .select_related('inscription__eleve')
            .order_by('-created_at')[:10]
        )
        context['paiements_aujourd_hui'] = paiements_aujourd_hui
        context['total_aujourd_hui'] = (
            Paiement.objects.filter(date_paiement=aujourd_hui)
            .aggregate(t=Sum('montant'))['t'] or 0
        )
        context['total_mois'] = (
            Paiement.objects.filter(
                date_paiement__gte=debut_mois,
                inscription__annee_scolaire=annee_courante,
            ).aggregate(t=Sum('montant'))['t'] or 0
        ) if annee_courante else 0
        context['encaissements_annee'] = (
            Paiement.objects.filter(inscription__annee_scolaire=annee_courante)
            .aggregate(t=Sum('montant'))['t'] or 0
        ) if annee_courante else 0
        context['nb_redevables'] = (
            Inscription.objects.filter(annee_scolaire=annee_courante)
            .exclude(statut=StatutInscriptionChoices.ABANDON)
            .exclude(paiements__isnull=False)
            .distinct().count()
        ) if annee_courante else 0

    # ── SECRETAIRE ────────────────────────────────────────────────────
    elif role == 'SECRETAIRE':
        from django.utils import timezone
        from documents.models import Document

        context['total_eleves'] = Eleve.objects.count()
        context['inscriptions_recentes'] = (
            Inscription.objects
            .filter(annee_scolaire=annee_courante)
            .select_related('eleve', 'classe')
            .order_by('-created_at')[:8]
        ) if annee_courante else []
        context['nb_docs_semaine'] = Document.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()

    # ── AVS ───────────────────────────────────────────────────────────
    elif role == 'AVS':
        from presences.models import Presence, Justification, Appel
        from viescolaire.models import SanctionDisciplinaire
        from django.utils import timezone

        aujourd_hui = timezone.now().date()
        context['nb_absences_aujourd_hui'] = Presence.objects.filter(
            statut='ABSENT', appel__date=aujourd_hui
        ).count()
        context['nb_retards_aujourd_hui'] = Presence.objects.filter(
            statut='RETARD', appel__date=aujourd_hui
        ).count()
        context['nb_appels_aujourd_hui'] = Appel.objects.filter(date=aujourd_hui).count()
        context['nb_justifications_attente'] = Justification.objects.filter(
            statut='EN_ATTENTE',
            inscription__annee_scolaire=annee_courante,
        ).count() if annee_courante else 0
        context['sanctions_recentes'] = (
            SanctionDisciplinaire.objects
            .filter(inscription__annee_scolaire=annee_courante)
            .select_related('inscription__eleve', 'type_sanction')
            .order_by('-date_sanction')[:5]
        ) if annee_courante else []

    if role in ('SUPER_ADMIN', 'DIRECTEUR') or request.user.is_superuser:
        from core.exploitation import alertes_en_cache
        context['alertes_exploitation'] = alertes_en_cache()

    return render(request, 'core/home.html', context)


@login_required
def recherche_globale(request):
    """Recherche globale : élèves, personnel, classes. Retourne un partial HTMX."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return render(request, 'core/partials/recherche_resultats.html', {'resultats': [], 'q': q})

    etab = getattr(request.user, 'etablissement', None)

    eleves = (
        Eleve.objects.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(matricule__icontains=q)
        ).only('id', 'nom', 'prenom', 'matricule')[:6]
    )

    personnel = (
        MembrePersonnel.objects.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(matricule__icontains=q) | Q(fonction__icontains=q)
        ).only('id', 'nom', 'prenom', 'matricule', 'fonction')[:6]
    )

    classes_qs = Classe.objects.filter(nom__icontains=q).only('id', 'nom', 'niveau')
    if etab:
        classes_qs = classes_qs.filter(etablissement=etab)
    classes = classes_qs[:6]

    resultats = [
        {'categorie': 'Élèves', 'icone': 'eleve', 'items': [
            {'label': f"{e.nom.upper()} {e.prenom}", 'sub': e.matricule, 'url': f"/inscriptions/eleve/{e.pk}/"}
            for e in eleves
        ]},
        {'categorie': 'Personnel', 'icone': 'personnel', 'items': [
            {'label': f"{m.nom.upper()} {m.prenom}", 'sub': m.fonction or m.matricule, 'url': f"/personnel/{m.pk}/"}
            for m in personnel
        ]},
        {'categorie': 'Classes', 'icone': 'classe', 'items': [
            {'label': c.nom, 'sub': c.get_niveau_display() if hasattr(c, 'get_niveau_display') else c.niveau, 'url': "/parametres/classes/"}
            for c in classes
        ]},
    ]
    # Ne garder que les catégories avec des résultats
    resultats = [r for r in resultats if r['items']]

    return render(request, 'core/partials/recherche_resultats.html', {'resultats': resultats, 'q': q})


@login_required
def indicateurs_evolution(request):
    """Évolution pluriannuelle : effectifs, résultats, recouvrement et assiduité, année après année."""
    from core import indicateurs
    from core.pilotage import ROLES_PILOTAGE
    if request.user.role not in ROLES_PILOTAGE and not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {
            'message': "L'évolution des indicateurs est réservée à la direction.",
        }, status=403)
    etab = getattr(request.user, 'etablissement', None)
    if not etab:
        messages.error(request, "Votre compte n'est associé à aucun établissement.")
        return redirect('core:home')
    if request.method == 'POST':
        lignes = indicateurs.mettre_a_jour(etab)
        messages.success(request, f"Indicateurs recalculés pour {len(lignes)} année(s).")
        return redirect('core:indicateurs_evolution')
    return render(request, 'core/indicateurs_evolution.html', {'lignes': indicateurs.evolution(etab)})


@login_required
def demarrage(request):
    """Assistant de première configuration : étapes de mise en route, état réel et lien direct."""
    from parametres.droits import peut_acceder
    if not (request.user.is_superuser or peut_acceder(request.user, 'parametres')):
        return render(request, 'core/access_denied.html', {
            'message': "L'assistant de démarrage est réservé aux rôles qui accèdent aux paramètres.",
        }, status=403)
    etab = getattr(request.user, 'etablissement', None)
    if not etab:
        messages.error(request, "Votre compte n'est associé à aucun établissement.")
        return redirect('core:home')
    from core import demarrage as etapes_module
    liste = etapes_module.etapes(etab, request.user)
    return render(request, 'core/demarrage.html', {
        'etapes': liste, 'avancement': etapes_module.avancement(liste),
    })


@login_required
def pilotage(request):
    """Tableau de bord direction : recouvrement, impayés par classe, effectifs, absences, élèves à risque."""
    from django.core.exceptions import ValidationError
    from core.pilotage import ROLES_PILOTAGE, tableau_de_bord

    if request.user.role not in ROLES_PILOTAGE and not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {
            'message': "Le tableau de bord direction est réservé à la direction.",
        })
    from etablissements.views import etablissement_pilotable

    # Depuis la vue consolidée du réseau : un Super Admin ou un Directeur Réseau pilote un site de son groupe
    etab_reseau = etablissement_pilotable(request.user, request.GET.get('etab'))
    etab = etab_reseau or request.user.etablissement
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else AnneeScolaire.objects.none()
    annee = None
    if request.GET.get('annee_id'):
        try:
            annee = annees.filter(pk=request.GET['annee_id']).first()
        except (ValueError, ValidationError):
            annee = None
    annee = annee or annees.filter(est_courante=True).first() or annees.first()
    context = {'annees': annees, 'annee_selectionnee': annee, 'etablissement_pilote': etab, 'etab_reseau': etab_reseau}
    if annee is not None:
        context.update(tableau_de_bord(etab, annee))
    return render(request, 'core/pilotage.html', context)


@login_required
def pilotage_enseignants(request):
    """Statistiques par enseignant (année ou période) : charge, évaluations, saisie des notes, résultats des élèves,
    cahier de textes, appréciations — écran ou ``?format=pdf``."""
    from core.pilotage import ROLES_PILOTAGE
    from pedagogie.models import Trimestre
    from pedagogie.statistiques_enseignants import statistiques_enseignants

    if request.user.role not in ROLES_PILOTAGE and not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {
            'message': "Les statistiques par enseignant sont réservées à la direction.",
        })
    etab = request.user.etablissement
    annee = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first() if etab else None
    trimestres = list(Trimestre.objects.filter(annee_scolaire=annee).order_by('numero')) if annee else []
    trimestre = next((t for t in trimestres if str(t.pk) == request.GET.get('trimestre', '')), None)
    lignes = statistiques_enseignants(etab, annee, trimestre) if annee else []
    contexte = {'annee': annee, 'trimestres': trimestres, 'trimestre': trimestre, 'lignes': lignes}
    if request.GET.get('format') != 'pdf':
        return render(request, 'core/pilotage_enseignants.html', contexte)
    from django.template.loader import render_to_string
    from core.pdf import HTML
    from core.utils import get_etablissement_context
    contexte.update(get_etablissement_context(etab, request=request))
    contexte['now'] = timezone.now()
    pdf = HTML(string=render_to_string('core/pdf/statistiques_enseignants.html', contexte, request=request),
               base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="statistiques_enseignants.pdf"'
    return response
