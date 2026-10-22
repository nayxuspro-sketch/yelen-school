"""
Assistant d'import des notes d'une classe depuis le fichier existant de l'école,
en quatre étapes : fichier et période → colonnes → vérification → résultat.
Même mécanique que l'import des élèves (``inscriptions.views_import``).
"""
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from core.excel import ExcelExport
from core.importation import (
    ERREURS_MAX, ErreurImport, detecter_colonnes, en_date, enregistrer_fichier, lettre_colonne, lire_feuille,
    noms_feuilles, supprimer_fichier, synonymes_de, texte,
)
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe

from .. import importation
from ..importation import CHAMPS_ELEVE
from ..models import Enseignement, Trimestre, TypeEvaluation

CLE_SESSION = 'import_notes'
ETAPES = ('Fichier et période', 'Colonnes', 'Vérification', 'Résultat')
APERCU_LIGNES = 5


def _etat(request):
    return request.session.get(CLE_SESSION) or {}


def _memoriser(request, etat):
    request.session[CLE_SESSION] = etat
    request.session.modified = True


def _abandonner(request, etat, erreur):
    supprimer_fichier(etat.get('fichier', ''))
    request.session.pop(CLE_SESSION, None)
    messages.error(request, str(erreur))
    return redirect('pedagogie:notes_import')


def _etablissement(request):
    return getattr(request.user, 'etablissement', None)


def _classes(request):
    etab = _etablissement(request)
    classes = Classe.objects.filter(etablissement=etab) if etab else Classe.objects.all()
    return classes.select_related('cycle').order_by('cycle__ordre', 'niveau', 'nom')


def _annee_courante(request):
    etab = _etablissement(request)
    annees = AnneeScolaire.objects.filter(etablissement=etab) if etab else AnneeScolaire.objects.all()
    return annees.filter(est_courante=True).first()


def _contexte(etape, **extra):
    return {'etapes': ETAPES, 'etape': etape, **extra}


def _parametres(request, etat):
    """Objets de l'étape 1 relus depuis la session (None si l'un d'eux a disparu)."""
    classe = _classes(request).filter(pk=etat.get('classe')).first()
    trimestre = Trimestre.objects.filter(pk=etat.get('trimestre')).select_related('annee_scolaire').first()
    type_evaluation = TypeEvaluation.objects.filter(pk=etat.get('type_evaluation')).first()
    if not (classe and trimestre and type_evaluation):
        return None
    return {
        'classe': classe, 'trimestre': trimestre, 'type_evaluation': type_evaluation, 'titre': etat['titre'],
        'bareme': Decimal(etat['bareme']), 'date_evaluation': date.fromisoformat(etat['date_evaluation']),
        'enseignements': Enseignement.objects.filter(
            classe=classe, annee_scolaire=trimestre.annee_scolaire, est_actif=True,
        ).select_related('matiere').order_by('matiere__nom'),
    }


# ── Étape 1 : fichier et période ─────────────────────────────────────────

@login_required
def notes_import(request):
    annee = _annee_courante(request)
    classes = _classes(request)
    trimestres = Trimestre.objects.filter(annee_scolaire=annee).order_by('numero') if annee else Trimestre.objects.none()
    types = TypeEvaluation.objects.order_by('ordre', 'code')

    if request.method == 'POST':
        fichier = request.FILES.get('fichier')
        classe = classes.filter(pk=request.POST.get('classe')).first()
        trimestre = trimestres.filter(pk=request.POST.get('trimestre')).first()
        type_evaluation = types.filter(pk=request.POST.get('type_evaluation')).first()
        titre = texte(request.POST.get('titre'))[:200]
        erreur = None
        try:
            bareme = Decimal(texte(request.POST.get('bareme', '20')).replace(',', '.'))
            if not 0 < bareme <= 999:
                raise InvalidOperation
        except InvalidOperation:
            bareme, erreur = None, "Barème invalide (par exemple 20 ou 10)."
        try:
            date_evaluation = en_date(request.POST.get('date_evaluation')) or timezone.localdate()
        except ValueError:
            date_evaluation, erreur = None, "Date d'évaluation invalide (jj/mm/aaaa)."
        if not (fichier and classe and trimestre and type_evaluation and titre):
            erreur = erreur or "Renseignez le fichier, la classe, le trimestre, le type d'évaluation et le titre."
        elif not Enseignement.objects.filter(classe=classe, annee_scolaire=trimestre.annee_scolaire,
                                             est_actif=True).exists():
            erreur = (f"Aucun enseignement n'est défini pour la classe {classe.nom} en "
                      f"{trimestre.annee_scolaire.libelle} (Pédagogie › Enseignements).")
        if erreur is None:
            try:
                nom = enregistrer_fichier(fichier)
            except ErreurImport as exc:
                erreur = str(exc)
        if erreur:
            messages.error(request, erreur)
            return redirect('pedagogie:notes_import')
        supprimer_fichier(_etat(request).get('fichier', ''))
        _memoriser(request, {
            'fichier': nom, 'nom_fichier': fichier.name, 'classe': str(classe.pk), 'trimestre': str(trimestre.pk),
            'type_evaluation': str(type_evaluation.pk), 'titre': titre, 'bareme': str(bareme),
            'date_evaluation': date_evaluation.isoformat(),
        })
        return redirect('pedagogie:notes_import_correspondance')

    return render(request, 'pedagogie/notes_import.html', _contexte(
        1, annee=annee, classes=classes, trimestres=trimestres, types=types, aujourd_hui=timezone.localdate(),
    ))


# ── Étape 2 : colonnes ───────────────────────────────────────────────────

def _feuille(etat, nom_feuille=''):
    return lire_feuille(etat['fichier'], nom_feuille or etat.get('feuille', ''), synonymes_de(CHAMPS_ELEVE))


def _colonnes(feuille):
    colonnes = []
    for index, entete in enumerate(feuille.entetes):
        exemple = next((texte(l[index]) for l in feuille.lignes[:20] if texte(l[index])), '')
        colonnes.append({'index': index, 'lettre': lettre_colonne(index), 'entete': entete, 'exemple': exemple})
    return colonnes


@login_required
def notes_import_correspondance(request):
    etat = _etat(request)
    if 'fichier' not in etat:
        return redirect('pedagogie:notes_import')
    parametres = _parametres(request, etat)
    if parametres is None:
        return _abandonner(request, etat, "Classe, trimestre ou type d'évaluation introuvable : recommencez l'import.")
    try:
        feuilles = noms_feuilles(etat['fichier'])
        nom_feuille = request.POST.get('feuille') or request.GET.get('feuille') or etat.get('feuille') or feuilles[0]
        feuille = _feuille(etat, nom_feuille)
    except ErreurImport as exc:
        return _abandonner(request, etat, exc)

    enseignements = list(parametres['enseignements'])
    par_pk = {str(e.pk): e for e in enseignements}
    nb_colonnes = len(feuille.entetes)

    if request.method == 'POST':
        erreurs = []
        correspondance = {}
        for champ in CHAMPS_ELEVE:
            valeur = request.POST.get(f'col_{champ.code}', '')
            if valeur.isdigit() and int(valeur) < nb_colonnes:
                correspondance[champ.code] = int(valeur)
        matieres = {}
        for index in range(nb_colonnes):
            if index in correspondance.values():
                continue
            ens = par_pk.get(request.POST.get(f'mat_{index}', ''))
            if ens is None:
                continue
            if ens in matieres.values():
                erreurs.append(f"La matière {ens.matiere.nom} est attribuée à deux colonnes.")
                continue
            matieres[index] = ens
        erreurs += importation.verifier_correspondance(correspondance, matieres)
        if not erreurs:
            etat.update(feuille=feuille.nom, correspondance=correspondance,
                        matieres={str(i): str(e.pk) for i, e in matieres.items()})
            etat.pop('resultat', None)
            _memoriser(request, etat)
            return redirect('pedagogie:notes_import_verification')
        for erreur in erreurs:
            messages.error(request, erreur)
    elif etat.get('correspondance') is not None and etat.get('feuille') == feuille.nom:
        correspondance = {c: int(i) for c, i in etat['correspondance'].items()}
        matieres = {int(i): par_pk[p] for i, p in etat['matieres'].items() if p in par_pk}
    else:
        correspondance = detecter_colonnes(feuille.entetes, CHAMPS_ELEVE)
        matieres = importation.detecter_matieres(feuille.entetes, enseignements, set(correspondance.values()))

    colonnes = _colonnes(feuille)
    for colonne in colonnes:
        colonne['enseignement'] = matieres.get(colonne['index'])
        colonne['champ'] = next((c for c in CHAMPS_ELEVE if correspondance.get(c.code) == colonne['index']), None)
    champs = [{'champ': c, 'index': correspondance.get(c.code)} for c in CHAMPS_ELEVE]
    return render(request, 'pedagogie/notes_import_correspondance.html', _contexte(
        2, etat=etat, parametres=parametres, feuille=feuille, feuilles=feuilles, colonnes=colonnes, champs=champs,
        enseignements=enseignements, apercu=[[texte(v) for v in l] for l in feuille.lignes[:APERCU_LIGNES]],
        nb_matieres=len(matieres),
    ))


# ── Étape 3 : vérification puis import ───────────────────────────────────

def _analyse(request, etat, parametres):
    feuille = _feuille(etat)
    par_pk = {str(e.pk): e for e in parametres['enseignements']}
    matieres = {int(i): par_pk[p] for i, p in etat['matieres'].items() if p in par_pk}
    inscriptions = Inscription.objects.filter(
        classe=parametres['classe'], annee_scolaire=parametres['trimestre'].annee_scolaire,
    ).exclude(statut='ABANDON').select_related('eleve')
    analyse = importation.analyser(
        feuille, {c: int(i) for c, i in etat['correspondance'].items()}, matieres, inscriptions,
        parametres['bareme'], parametres['trimestre'], parametres['type_evaluation'], parametres['titre'],
    )
    return feuille, matieres, analyse


@login_required
def notes_import_verification(request):
    etat = _etat(request)
    if 'matieres' not in etat:
        return redirect('pedagogie:notes_import_correspondance' if 'fichier' in etat else 'pedagogie:notes_import')
    parametres = _parametres(request, etat)
    if parametres is None:
        return _abandonner(request, etat, "Classe, trimestre ou type d'évaluation introuvable : recommencez l'import.")
    try:
        feuille, matieres, analyse = _analyse(request, etat, parametres)
    except ErreurImport as exc:
        return _abandonner(request, etat, exc)

    if request.method == 'POST' and not analyse.bloquants and analyse.lignes:
        resultat = importation.importer(
            analyse, matieres, parametres['trimestre'], parametres['type_evaluation'], parametres['titre'],
            parametres['bareme'], parametres['date_evaluation'],
        )
        supprimer_fichier(etat['fichier'])
        _memoriser(request, {
            'nom_fichier': etat['nom_fichier'], 'classe': etat['classe'], 'trimestre': etat['trimestre'],
            'titre': etat['titre'],
            'resultat': {'evaluations_creees': resultat.evaluations_creees, 'notes_creees': resultat.notes_creees,
                         'notes_remplacees': resultat.notes_remplacees, 'nb_eleves': analyse.nb_eleves,
                         'nb_matieres': len(matieres), 'nb_erreurs': len(analyse.erreurs)},
            'erreurs': [list(e) for e in analyse.erreurs[:ERREURS_MAX]],
        })
        return redirect('pedagogie:notes_import_resultat')

    return render(request, 'pedagogie/notes_import_verification.html', _contexte(
        3, etat=etat, parametres=parametres, feuille=feuille, analyse=analyse, erreurs=analyse.erreurs[:100],
        matieres=sorted(matieres.values(), key=lambda e: e.matiere.nom), apercu=analyse.lignes[:APERCU_LIGNES],
    ))


# ── Étape 4 : résultat ───────────────────────────────────────────────────

@login_required
def notes_import_resultat(request):
    etat = _etat(request)
    if 'resultat' not in etat:
        return redirect('pedagogie:notes_import')
    classe = _classes(request).filter(pk=etat['classe']).first()
    trimestre = Trimestre.objects.filter(pk=etat['trimestre']).first()
    return render(request, 'pedagogie/notes_import_resultat.html', _contexte(
        4, etat=etat, classe=classe, trimestre=trimestre, resultat=etat['resultat'], erreurs=etat.get('erreurs', []),
    ))


@login_required
def notes_import_rapport(request):
    etat = _etat(request)
    if 'resultat' not in etat:
        return redirect('pedagogie:notes_import')
    wb = ExcelExport("Notes non importées")
    wb.add_title("Import de notes — cellules non importées", etat.get('nom_fichier', ''))
    wb.add_header(['Ligne du fichier', 'Élève', 'Motif'])
    for numero, identite, motif in etat.get('erreurs', []):
        wb.add_row([numero, identite, motif])
    return wb.response("import_notes_erreurs.xlsx")
