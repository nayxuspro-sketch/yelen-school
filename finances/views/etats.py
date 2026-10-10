"""États et bilans : redevables, exonérés, bilan des encaissements, certificat.

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.core.exceptions import ValidationError
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal
import csv
import io
from ..models import Paiement
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, RubriquePaiement
from core.utils import get_etablissement_context
from ..permissions import FINANCE_VIEW_ROLES
from .commun import (
    WeasyHTML,
    _situations_financieres_en_lot,
    _require_finance_role,
    _require_same_establishment,
    _calcul_situation_financiere,
)


@login_required
def liste_redevables(request):
    """Liste des élèves redevables (ayant un reste à payer > 0)."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    
    annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    if not annee_courante:
        messages.warning(request, "Aucune année scolaire active.")
        return redirect('finances:paiement_list')
    
    query = request.GET.get('q', '').strip()
    
    # Toutes les inscriptions de l'année
    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee_courante,
        classe__etablissement=etab,
    ).exclude(statut='ABANDON').select_related('eleve', 'classe', 'classe__cycle', 'statut_eleve')
    
    if query:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=query) |
            Q(eleve__prenom__icontains=query) |
            Q(eleve__matricule__icontains=query) |
            Q(classe__nom__icontains=query)
        )
    
    # Regrouper par cycle puis par classe
    cycles_dict = {}
    total_redevable = Decimal('0')
    nb_redevables = 0
    
    # Situations financières calculées en lot (4 requêtes) au lieu de 4 par élève
    situations = _situations_financieres_en_lot(inscriptions)

    for inscr in inscriptions:
        classe = inscr.classe
        cycle = classe.cycle

        sit = situations[inscr.pk]
        total_du = sit['total_du']
        total_paye = sit['total_paye']
        reste = sit['reste_a_payer']

        if reste > 0:
            nb_redevables += 1
            total_redevable += reste

            # Ajouter au cycle
            if cycle.nom not in cycles_dict:
                cycles_dict[cycle.nom] = {
                    'cycle': cycle,
                    'classes': {},
                    'total': Decimal('0'),
                }
            
            # Ajouter à la classe
            if classe.nom not in cycles_dict[cycle.nom]['classes']:
                cycles_dict[cycle.nom]['classes'][classe.nom] = {
                    'classe': classe,
                    'eleves': [],
                    'total': Decimal('0'),
                }
            
            cycles_dict[cycle.nom]['classes'][classe.nom]['eleves'].append({
                'inscription': inscr,
                'total_du': total_du,
                'total_paye': total_paye,
                'reste': reste,
                'derniere_relance': None,  # rempli après la boucle
            })
            cycles_dict[cycle.nom]['classes'][classe.nom]['total'] += reste
            cycles_dict[cycle.nom]['total'] += reste

    # Enrichir chaque élève avec sa dernière relance
    from ..models import HistoriqueRelance
    inscription_ids = [
        item['inscription'].pk
        for c in cycles_dict.values()
        for cl in c['classes'].values()
        for item in cl['eleves']
    ]
    if inscription_ids:
        from django.db.models import Max
        relances_map = {
            r['inscription_id']: r['date_relance__max']
            for r in HistoriqueRelance.objects.filter(inscription_id__in=inscription_ids)
            .values('inscription_id')
            .annotate(date_relance__max=Max('date_relance'))
        }
        for c in cycles_dict.values():
            for cl in c['classes'].values():
                for item in cl['eleves']:
                    item['derniere_relance'] = relances_map.get(item['inscription'].pk)

    # Convertir en liste triée
    cycles_list = []
    for cycle_nom in sorted(cycles_dict.keys()):
        cycle_data = cycles_dict[cycle_nom]
        classes_list = []
        for classe_nom in sorted(cycle_data['classes'].keys()):
            classe_data = cycle_data['classes'][classe_nom]
            # Trier les élèves par reste décroissant
            classe_data['eleves'].sort(key=lambda x: (x['inscription'].eleve.nom, x['inscription'].eleve.prenom))
            classes_list.append(classe_data)
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })
    
    context = {
        'cycles_list': cycles_list,
        'total_redevable': total_redevable,
        'nb_redevables': nb_redevables,
        'annee_courante': annee_courante,
        'query': query,
    }
    return render(request, 'finances/liste_redevables.html', context)


def _bilan_paiements_qs(etab, annee_id, date_debut, date_fin, rub_id):
    """
    Retourne (annee_selected, rub_selected, paiements_qs) selon les filtres GET.
    Factorise la logique commune aux vues bilan HTML, PDF et CSV.
    """
    annee_selected = None
    try:
        if annee_id:
            annee_selected = get_object_or_404(
                AnneeScolaire, pk=annee_id, etablissement=etab
            )

        rub_selected = None
        if rub_id:
            rub_selected = get_object_or_404(
                RubriquePaiement, pk=rub_id, etablissement=etab
            )
    except (ValueError, ValidationError) as exc:
        raise Http404("Filtre financier invalide.") from exc

    paiements = (
        Paiement.objects
        .filter(inscription__classe__etablissement=etab)
        .select_related(
            'inscription__eleve',
            'inscription__classe__cycle',
            'rubrique',
        )
        .order_by('-date_paiement', '-created_at')
    )
    if annee_selected:
        paiements = paiements.filter(inscription__annee_scolaire=annee_selected)
    if date_debut:
        paiements = paiements.filter(date_paiement__gte=date_debut)
    if date_fin:
        paiements = paiements.filter(date_paiement__lte=date_fin)
    if rub_selected:
        paiements = paiements.filter(rubrique=rub_selected)

    return annee_selected, rub_selected, paiements


@login_required
def bilan_encaissements(request):
    """Bilan des encaissements par année scolaire et période."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle')
    rubriques = RubriquePaiement.objects.filter(etablissement=etab, actif=True).order_by('nom')

    annee_id = request.GET.get('annee')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    rub_id = request.GET.get('rubrique')

    # Année courante par défaut
    if not annee_id:
        annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
        if annee_courante:
            annee_id = annee_courante.pk

    annee_selected, rub_selected, paiements = _bilan_paiements_qs(
        etab, annee_id, date_debut, date_fin, rub_id
    )
    
    # Statistiques
    total_encaissement = paiements.aggregate(Sum('montant'))['montant__sum'] or 0
    nb_paiements = paiements.count()

    # Par mode de paiement (agrégation ORM sur le queryset filtré)
    par_mode = {
        (row['mode_paiement'] or 'Non défini'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
        }
        for row in paiements
        .values('mode_paiement')
        .annotate(count=Count('id'), total=Sum('montant'))
    }

    # Par jour (agrégation ORM)
    par_jour = {
        row['jour'].strftime('%d/%m/%Y'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
            'date': row['jour'],
        }
        for row in paiements
        .annotate(jour=TruncDate('date_paiement'))
        .values('jour')
        .annotate(count=Count('id'), total=Sum('montant'))
        .order_by('-jour')
    }
    
    # Par cycle et classe (une seule passe sur les paiements déjà chargés)
    cycles_dict = {}
    for p in paiements:
        cycle = p.inscription.classe.cycle if p.inscription.classe else None
        classe = p.inscription.classe
        if not cycle or not classe:
            continue

        cycle_key = cycle.pk
        if cycle_key not in cycles_dict:
            cycles_dict[cycle_key] = {
                'cycle': cycle,
                'ordre': cycle.ordre if hasattr(cycle, 'ordre') else 0,
                'classes': {},
                'total': Decimal('0'),
            }

        classe_key = classe.pk
        if classe_key not in cycles_dict[cycle_key]['classes']:
            cycles_dict[cycle_key]['classes'][classe_key] = {
                'classe': classe,
                'paiements': [],
                'total': Decimal('0'),
            }

        cycles_dict[cycle_key]['classes'][classe_key]['paiements'].append(p)
        cycles_dict[cycle_key]['classes'][classe_key]['total'] += p.montant
        cycles_dict[cycle_key]['total'] += p.montant

    cycles_list = []
    for cycle_data in sorted(cycles_dict.values(), key=lambda c: (c['ordre'], c['cycle'].nom)):
        classes_list = sorted(
            cycle_data['classes'].values(),
            key=lambda c: c['classe'].nom,
        )
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })
    
    context = {
        'annees': annees,
        'rubriques': rubriques,
        'annee_selected': annee_selected,
        'rub_selected': rub_selected,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'cycles_list': cycles_list,
        'total_encaissement': total_encaissement,
        'nb_paiements': nb_paiements,
        'par_mode': par_mode,
        'par_jour': par_jour,
    }
    return render(request, 'finances/bilan_encaissements.html', context)


@login_required
def bilan_encaissements_pdf(request):
    """Génère un PDF du bilan des encaissements."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:bilan_encaissements')
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    etab_context = get_etablissement_context(etab, request)

    annee_id = request.GET.get('annee')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    rub_id = request.GET.get('rubrique')

    annee_selected, rub_selected, paiements = _bilan_paiements_qs(
        etab, annee_id, date_debut, date_fin, rub_id
    )

    total_encaissement = paiements.aggregate(Sum('montant'))['montant__sum'] or 0
    nb_paiements = paiements.count()

    par_mode = {
        (row['mode_paiement'] or 'Non défini'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
        }
        for row in paiements
        .values('mode_paiement')
        .annotate(count=Count('id'), total=Sum('montant'))
    }

    par_jour = {
        row['jour'].strftime('%d/%m/%Y'): {
            'count': row['count'],
            'total': row['total'] or Decimal('0'),
            'date': row['jour'],
        }
        for row in paiements
        .annotate(jour=TruncDate('date_paiement'))
        .values('jour')
        .annotate(count=Count('id'), total=Sum('montant'))
        .order_by('-jour')
    }

    # Par cycle et classe (clé par PK pour éviter les collisions de noms)
    cycles_dict = {}
    for p in paiements:
        cycle = p.inscription.classe.cycle if p.inscription.classe else None
        classe = p.inscription.classe
        if not cycle or not classe:
            continue

        cycle_key = cycle.pk
        if cycle_key not in cycles_dict:
            cycles_dict[cycle_key] = {
                'cycle': cycle,
                'ordre': cycle.ordre if hasattr(cycle, 'ordre') else 0,
                'classes': {},
                'total': Decimal('0'),
            }

        classe_key = classe.pk
        if classe_key not in cycles_dict[cycle_key]['classes']:
            cycles_dict[cycle_key]['classes'][classe_key] = {
                'classe': classe,
                'paiements': [],
                'total': Decimal('0'),
            }

        cycles_dict[cycle_key]['classes'][classe_key]['paiements'].append(p)
        cycles_dict[cycle_key]['classes'][classe_key]['total'] += p.montant
        cycles_dict[cycle_key]['total'] += p.montant

    cycles_list = []
    for cycle_data in sorted(cycles_dict.values(), key=lambda c: (c['ordre'], c['cycle'].nom)):
        classes_list = sorted(
            cycle_data['classes'].values(),
            key=lambda c: c['classe'].nom,
        )
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })

    html_string = render_to_string('finances/pdf/bilan_encaissements.html', {
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'annee_selected': annee_selected,
        'rub_selected': rub_selected,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'cycles_list': cycles_list,
        'total_encaissement': total_encaissement,
        'nb_paiements': nb_paiements,
        'par_mode': par_mode,
        'par_jour': par_jour,
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Bilan_Encaissements_{annee_selected.libelle if annee_selected else 'Tous'}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def bilan_encaissements_csv(request):
    """Export CSV du bilan des encaissements (mêmes filtres que la vue HTML)."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annee_id = request.GET.get('annee')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    rub_id = request.GET.get('rubrique')

    annee_selected, rub_selected, paiements = _bilan_paiements_qs(
        etab, annee_id, date_debut, date_fin, rub_id
    )

    nom_fichier = f"bilan_encaissements_{annee_selected.libelle if annee_selected else 'tous'}.csv".replace(' ', '_')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Date', 'Élève', 'Matricule', 'Classe', 'Cycle', 'Rubrique', 'Montant (FCFA)', 'Mode de paiement'])

    for p in paiements:
        eleve = p.inscription.eleve
        classe = p.inscription.classe
        writer.writerow([
            p.date_paiement.strftime('%d/%m/%Y') if p.date_paiement else '',
            f"{eleve.nom} {eleve.prenom}",
            eleve.matricule or '',
            classe.nom if classe else '',
            classe.cycle.nom if classe and classe.cycle else '',
            p.rubrique.nom if p.rubrique else '',
            str(p.montant),
            p.mode_paiement or '',
        ])

    return response


@login_required
def bilan_encaissements_xlsx(request):
    """Export Excel du bilan des encaissements (mêmes filtres que la vue HTML)."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    from core.excel import ExcelExport

    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annee_id = request.GET.get('annee')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    rub_id = request.GET.get('rubrique')

    annee_selected, rub_selected, paiements = _bilan_paiements_qs(
        etab, annee_id, date_debut, date_fin, rub_id
    )

    titre = f"Bilan des encaissements{' — ' + annee_selected.libelle if annee_selected else ''}"
    nom_fichier = f"bilan_encaissements{'_' + annee_selected.libelle if annee_selected else ''}.xlsx".replace(' ', '_')

    wb = ExcelExport("Encaissements")
    wb.add_title(titre, subtitle=etab.nom)
    wb.add_header(['Date', 'Élève', 'Matricule', 'Classe', 'Cycle', 'Rubrique', 'Montant (FCFA)', 'Mode de paiement'])

    total = 0
    for p in paiements:
        eleve = p.inscription.eleve
        classe = p.inscription.classe
        montant = float(p.montant) if p.montant else 0
        total += montant
        wb.add_row([
            p.date_paiement.strftime('%d/%m/%Y') if p.date_paiement else '',
            f"{eleve.nom} {eleve.prenom}",
            eleve.matricule or '',
            classe.nom if classe else '',
            classe.cycle.nom if classe and classe.cycle else '',
            p.rubrique.nom if p.rubrique else '',
            montant,
            p.mode_paiement or '',
        ])

    wb.add_separator()
    wb.add_row(['', '', '', '', '', 'TOTAL', total, ''])

    return wb.response(nom_fichier)


@login_required
def liste_redevables_pdf(request):
    """Génère un PDF de la liste des élèves redevables."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:liste_redevables')
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    
    annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
    if not annee_courante:
        messages.warning(request, "Aucune année scolaire active.")
        return redirect('finances:paiement_list')
    
    etab_context = get_etablissement_context(etab, request)
    
    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee_courante,
        classe__etablissement=etab,
    ).exclude(statut='ABANDON').select_related('eleve', 'classe', 'classe__cycle', 'statut_eleve')

    cycles_dict = {}
    total_redevable = Decimal('0')
    nb_redevables = 0
    
    # Situations financières calculées en lot (4 requêtes) au lieu de 4 par élève
    situations = _situations_financieres_en_lot(inscriptions)

    for inscr in inscriptions:
        classe = inscr.classe
        cycle = classe.cycle

        sit = situations[inscr.pk]
        total_du = sit['total_du']
        total_paye = sit['total_paye']
        reste = sit['reste_a_payer']

        if reste > 0:
            nb_redevables += 1
            total_redevable += reste

            if cycle.nom not in cycles_dict:
                cycles_dict[cycle.nom] = {
                    'cycle': cycle,
                    'classes': {},
                    'total': Decimal('0'),
                }
            
            if classe.nom not in cycles_dict[cycle.nom]['classes']:
                cycles_dict[cycle.nom]['classes'][classe.nom] = {
                    'classe': classe,
                    'eleves': [],
                    'total': Decimal('0'),
                }
            
            cycles_dict[cycle.nom]['classes'][classe.nom]['eleves'].append({
                'inscription': inscr,
                'total_du': total_du,
                'total_paye': total_paye,
                'reste': reste,
            })
            cycles_dict[cycle.nom]['classes'][classe.nom]['total'] += reste
            cycles_dict[cycle.nom]['total'] += reste
    
    cycles_list = []
    for cycle_nom in sorted(cycles_dict.keys()):
        cycle_data = cycles_dict[cycle_nom]
        classes_list = []
        for classe_nom in sorted(cycle_data['classes'].keys()):
            classe_data = cycle_data['classes'][classe_nom]
            classe_data['eleves'].sort(key=lambda x: (x['inscription'].eleve.nom, x['inscription'].eleve.prenom))
            classes_list.append(classe_data)
        cycles_list.append({
            'cycle': cycle_data['cycle'],
            'classes': classes_list,
            'total': cycle_data['total'],
        })
    
    html_string = render_to_string('finances/pdf/liste_redevables.html', {
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'cycles_list': cycles_list,
        'total_redevable': total_redevable,
        'nb_redevables': nb_redevables,
        'annee_courante': annee_courante,
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Redevables_{annee_courante.libelle}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def liste_exoneres(request):
    """Liste des élèves exonérés de paiement, regroupés par classe."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle')
    annee_id = request.GET.get('annee')
    annee = None
    if annee_id:
        annee = annees.filter(pk=annee_id).first()
    if not annee:
        annee = annees.filter(est_courante=True).first() or annees.first()

    query = request.GET.get('q', '').strip()

    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee,
        classe__etablissement=etab,
        est_exonere=True,
    ).select_related('eleve', 'classe', 'classe__cycle').order_by(
        'classe__cycle__ordre', 'classe__nom', 'eleve__nom', 'eleve__prenom'
    )

    if query:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=query) |
            Q(eleve__prenom__icontains=query) |
            Q(eleve__matricule__icontains=query)
        )

    # Regrouper par classe
    classes_dict = {}
    for inscr in inscriptions:
        key = str(inscr.classe_id)
        if key not in classes_dict:
            classes_dict[key] = {
                'classe': inscr.classe,
                'cycle': inscr.classe.cycle,
                'eleves': [],
            }
        classes_dict[key]['eleves'].append(inscr)

    groupes = sorted(classes_dict.values(), key=lambda g: (
        g['cycle'].ordre if g['cycle'] else 99,
        g['classe'].nom,
    ))

    return render(request, 'finances/liste_exoneres.html', {
        'annees': annees,
        'annee': annee,
        'groupes': groupes,
        'total': inscriptions.count(),
        'query': query,
    })


@login_required
def liste_exoneres_pdf(request):
    """Génère le PDF de la liste des élèves exonérés, regroupés par classe."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:liste_exoneres')
    etab = request.user.etablissement
    if not etab:
        return redirect('finances:paiement_list')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-libelle')
    annee_id = request.GET.get('annee')
    annee = None
    if annee_id:
        annee = annees.filter(pk=annee_id).first()
    if not annee:
        annee = annees.filter(est_courante=True).first() or annees.first()

    etab_context = get_etablissement_context(etab, request)

    inscriptions = Inscription.objects.filter(
        annee_scolaire=annee,
        classe__etablissement=etab,
        est_exonere=True,
    ).select_related('eleve', 'classe', 'classe__cycle').order_by(
        'classe__cycle__ordre', 'classe__nom', 'eleve__nom', 'eleve__prenom'
    )

    classes_dict = {}
    for inscr in inscriptions:
        key = str(inscr.classe_id)
        if key not in classes_dict:
            classes_dict[key] = {
                'classe': inscr.classe,
                'cycle': inscr.classe.cycle,
                'eleves': [],
            }
        classes_dict[key]['eleves'].append(inscr)

    groupes = sorted(classes_dict.values(), key=lambda g: (
        g['cycle'].ordre if g['cycle'] else 99,
        g['classe'].nom,
    ))

    html_string = render_to_string('finances/pdf/liste_exoneres.html', {
        'etablissement': etab,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'groupes': groupes,
        'total': inscriptions.count(),
        'annee': annee,
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Exoneres_{annee.libelle if annee else 'liste'}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


@login_required
def certificat_non_redevabilite(request, inscription_id):
    """Génère le certificat de non-redevabilité en PDF."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé.")
        return redirect('finances:paiement_list')
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    _require_same_establishment(request, inscription)
    etablissement = inscription.classe.etablissement
    
    etab_context = get_etablissement_context(etablissement, request)
    
    sit = _calcul_situation_financiere(inscription)
    total_paye = sit['total_paye']
    total_du = sit['total_du']
    reste_a_payer = sit['reste_a_payer']
    est_regulier = reste_a_payer <= 0
    
    html_string = render_to_string('finances/pdf/certificat_non_redevabilite.html', {
        'inscription': inscription,
        'etablissement': etablissement,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'total_du': total_du,
        'total_paye': total_paye,
        'reste_a_payer': reste_a_payer,
        'est_regulier': est_regulier,
        'annee_scolaire': inscription.annee_scolaire,
        'date_du_jour': timezone.now().strftime('%d/%m/%Y'),
        'now': timezone.now(),
    }, request=request)
    buffer = io.BytesIO()
    WeasyHTML(string=html_string).write_pdf(buffer)
    nom = f"Certificat_Non_Redevabilite_{inscription.eleve.nom}_{inscription.id.hex[:8]}.pdf".replace(" ", "_")
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response
