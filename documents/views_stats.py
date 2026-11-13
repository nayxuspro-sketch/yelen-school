"""Vue d'export des statistiques officielles de l'établissement."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from core.utils import get_etablissement_context
from yelen_school.cycle_filter import get_cycle_ids
from .view_helpers import _annees_accessibles, _can_generate_document


@login_required
def statistiques_officielles(request):
    """Statistiques de rentrée et de fin d'année au format du questionnaire ministériel (écran ou Excel)."""
    if not _can_generate_document(request.user):
        messages.error(request, "Vous n'êtes pas autorisé à générer des documents officiels.")
        return redirect('documents:document_list')
    from core.excel import ExcelExport
    from .statistiques_officielles import statistiques_fin_annee, statistiques_rentree

    etab = request.user.etablissement
    annees = _annees_accessibles(request, etab).order_by('-date_debut')
    annee = None
    if request.GET.get('annee_id'):
        try:
            annee = annees.filter(pk=request.GET['annee_id']).first()
        except (ValueError, ValidationError):
            annee = None
    annee = annee or annees.filter(est_courante=True).first() or annees.first()
    if annee is None:
        return render(request, 'documents/statistiques_officielles.html', {'annees': annees})

    cycle_ids = get_cycle_ids(request)
    rentree = statistiques_rentree(annee, cycle_ids=cycle_ids)
    fin_annee = statistiques_fin_annee(annee, cycle_ids=cycle_ids)
    if request.GET.get('format') != 'xlsx':
        return render(request, 'documents/statistiques_officielles.html', {
            'annees': annees, 'annee_selectionnee': annee, 'rentree': rentree, 'fin_annee': fin_annee,
        })

    identite = get_etablissement_context(etab, request).get('identite')
    titre = f"{identite.nom_etablissement if identite else etab.nom} — {annee.libelle}"
    gft = lambda compteur: [compteur['M'], compteur['F'], compteur['T']]  # noqa: E731

    wb = ExcelExport("Rentrée")
    wb.add_title("Statistiques de rentrée — élèves et redoublants par niveau et par sexe", titre)
    wb.add_header(['Cycle', 'Niveau', 'Divisions', 'Garçons', 'Filles', 'Total',
                   'Redoublants G', 'Redoublants F', 'Redoublants T', 'Nouveaux G', 'Nouveaux F', 'Nouveaux T'])
    for ligne in rentree['lignes']:
        wb.add_row([ligne['cycle'], ligne['niveau'], ligne['divisions'],
                    *gft(ligne['effectif']), *gft(ligne['redoublants']), *gft(ligne['nouveaux'])])
    total = rentree['total']
    wb.add_row(['TOTAL', '', sum(l['divisions'] for l in rentree['lignes']),
                *gft(total['effectif']), *gft(total['redoublants']), *gft(total['nouveaux'])], highlight_color='DBEAFE')

    wb.new_sheet("Âges")
    wb.add_title("Répartition des élèves par âge, par niveau et par sexe (âge = année de la rentrée − année de naissance)", titre)
    wb.add_header(['Âge', *[f"{niveau} {sexe}" for niveau in rentree['niveaux'] for sexe in ('G', 'F')], 'Garçons', 'Filles', 'Total'])
    for ligne in rentree['ages']:
        wb.add_row([ligne['age'], *[v for c in ligne['colonnes'] for v in (c['M'], c['F'])], *gft(ligne['total'])])
    ages_total = rentree['ages_total']
    wb.add_row(['TOTAL', *[v for c in ages_total['colonnes'] for v in (c['M'], c['F'])], *gft(ages_total['total'])],
               highlight_color='DBEAFE')

    wb.new_sheet("Fin d'année")
    wb.add_title("Statistiques de fin d'année — abandons et décisions des conseils de classe", titre)
    wb.add_header(['Cycle', 'Niveau', 'Inscrits G', 'Inscrits F', 'Inscrits T', 'Abandons G', 'Abandons F', 'Abandons T',
                   'Fin d\'année G', 'Fin d\'année F', 'Fin d\'année T',
                   *[f"{libelle} {sexe}" for _, libelle in fin_annee['decisions'] for sexe in ('G', 'F', 'T')]])
    for ligne in fin_annee['lignes']:
        wb.add_row([ligne['cycle'], ligne['niveau'], *gft(ligne['inscrits']), *gft(ligne['abandons']), *gft(ligne['fin_annee']),
                    *[v for cle, _ in fin_annee['decisions'] for v in gft(ligne[cle])]])
    total = fin_annee['total']
    wb.add_row(['TOTAL', '', *gft(total['inscrits']), *gft(total['abandons']), *gft(total['fin_annee']),
                *[v for cle, _ in fin_annee['decisions'] for v in gft(total[cle])]], highlight_color='DBEAFE')
    if fin_annee['examens']:
        wb.add_separator("Résultats aux examens officiels")
        wb.add_header(['Examen', 'Session', 'Inscrits G', 'Inscrits F', 'Inscrits T', 'Présents G', 'Présents F', 'Présents T',
                       'Admis G', 'Admis F', 'Admis T', 'Taux G (%)', 'Taux F (%)', 'Taux T (%)'])
        for examen in fin_annee['examens']:
            wb.add_row([examen['session'].type_examen, examen['session'].libelle, *gft(examen['inscrits']),
                        *gft(examen['presents']), *gft(examen['admis']), *gft(examen['taux'])])
    return wb.response(f"Statistiques_officielles_{annee.libelle}.xlsx".replace('/', '-').replace(' ', '_'))
