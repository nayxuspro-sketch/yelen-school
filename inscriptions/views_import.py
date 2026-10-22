"""
Assistant d'import des élèves depuis le fichier existant de l'école, en quatre
étapes : fichier → colonnes → vérification → résultat.

L'état de l'assistant (fichier enregistré, feuille, correspondance des
colonnes, résultat) vit dans la session ; le fichier est relu à chaque étape
et supprimé une fois l'import effectué.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.excel import ExcelExport
from core.importation import (
    ERREURS_MAX, ErreurImport, detecter_colonnes, enregistrer_fichier, lettre_colonne, lire_feuille, noms_feuilles,
    normaliser, supprimer_fichier, synonymes_de, texte,
)
from parametres.models import AnneeScolaire, Classe

from . import importation
from .importation import CHAMPS

CLE_SESSION = 'import_eleves'
ETAPES = ('Fichier', 'Colonnes', 'Vérification', 'Résultat')
APERCU_LIGNES = 5


def _etat(request):
    return request.session.get(CLE_SESSION) or {}


def _memoriser(request, etat):
    request.session[CLE_SESSION] = etat
    request.session.modified = True


def _abandonner(request, etat, erreur):
    """Fichier illisible ou disparu : on repart de l'étape 1 avec le motif."""
    supprimer_fichier(etat.get('fichier', ''))
    request.session.pop(CLE_SESSION, None)
    messages.error(request, str(erreur))
    return redirect('inscriptions:eleve_import')


def _etablissement(request):
    return getattr(request.user, 'etablissement', None)


def _annees(request):
    etab = _etablissement(request)
    return AnneeScolaire.objects.filter(etablissement=etab) if etab else AnneeScolaire.objects.all()


def _classes(request):
    etab = _etablissement(request)
    classes = Classe.objects.filter(etablissement=etab) if etab else Classe.objects.all()
    return classes.select_related('cycle').order_by('cycle__ordre', 'niveau', 'nom')


def _contexte(etape, **extra):
    return {'etapes': ETAPES, 'etape': etape, **extra}


def cle_classe(libelle) -> str:
    """Clé de rapprochement des libellés de classe : « 6ème A », « 6e A », « 6EME-A » → « 6ea »."""
    cle = normaliser(libelle)
    for long, court in (('terminale', 'tle'), ('seconde', '2de'), ('premiere', '1re'), ('sixieme', '6e'),
                        ('cinquieme', '5e'), ('quatrieme', '4e'), ('troisieme', '3e'), ('ieme', 'e'), ('eme', 'e'),
                        ('ere', 're'), ('nde', 'de')):
        cle = cle.replace(long, court)
    return cle.replace(' ', '')


# ── Étape 1 : fichier ────────────────────────────────────────────────────

@login_required
def eleve_import(request):
    annees = _annees(request)
    if request.method == 'POST':
        fichier = request.FILES.get('fichier')
        annee = annees.filter(pk=request.POST.get('annee')).first()
        if not fichier or annee is None:
            messages.error(request, "Choisissez un fichier et l'année scolaire d'inscription.")
            return redirect('inscriptions:eleve_import')
        try:
            nom = enregistrer_fichier(fichier)
        except ErreurImport as exc:
            messages.error(request, str(exc))
            return redirect('inscriptions:eleve_import')
        supprimer_fichier(_etat(request).get('fichier', ''))
        _memoriser(request, {'fichier': nom, 'nom_fichier': fichier.name, 'annee': str(annee.pk)})
        return redirect('inscriptions:eleve_import_correspondance')

    annee_courante = annees.filter(est_courante=True).first()
    return render(request, 'inscriptions/eleve_import.html', _contexte(
        1, annees=annees, annee_courante=annee_courante, champs=CHAMPS,
    ))


@login_required
def eleve_import_template(request):
    """Modèle Excel vide : une colonne par champ reconnu, les indispensables marqués d'une étoile."""
    wb = ExcelExport("Import élèves")
    colonnes = [f"{c.libelle} *" if c.obligatoire else c.libelle for c in CHAMPS if c.code != 'nom_complet']
    wb.add_header(colonnes)
    exemple = ['', 'OUEDRAOGO', 'Abdoul Kader', 'M', '12/05/2012', 'Ouagadougou', '6ème A', 'Non', 'Burkinabè',
               '70123456', 'OUEDRAOGO Issa', 'Commerçant', 'SAWADOGO Awa', 'Ménagère']
    wb.add_row(exemple + [''] * (len(colonnes) - len(exemple)))
    return wb.response("modele_import_eleves.xlsx")


# ── Étape 2 : colonnes ───────────────────────────────────────────────────

def _feuille(etat, nom_feuille=''):
    return lire_feuille(etat['fichier'], nom_feuille or etat.get('feuille', ''), synonymes_de(CHAMPS))


def _colonnes(feuille):
    """Descriptif des colonnes du fichier pour les listes déroulantes : lettre, entête, premier exemple."""
    colonnes = []
    for index, entete in enumerate(feuille.entetes):
        exemple = next((texte(l[index]) for l in feuille.lignes[:20] if texte(l[index])), '')
        colonnes.append({'index': index, 'lettre': lettre_colonne(index), 'entete': entete, 'exemple': exemple})
    return colonnes


def _lire_correspondance(post, champs, nb_colonnes):
    """Sélections du formulaire → {code: index} ; refuse une colonne attribuée à deux champs."""
    correspondance, erreurs = {}, []
    for champ in champs:
        valeur = post.get(f'col_{champ.code}', '')
        if valeur == '':
            continue
        if not valeur.isdigit() or int(valeur) >= nb_colonnes:
            continue
        index = int(valeur)
        if index in correspondance.values():
            autre = next(c.libelle for c in champs if correspondance.get(c.code) == index)
            erreurs.append(f"La colonne {lettre_colonne(index)} est attribuée à la fois à « {autre} » "
                           f"et à « {champ.libelle} ».")
            continue
        correspondance[champ.code] = index
    return correspondance, erreurs


@login_required
def eleve_import_correspondance(request):
    etat = _etat(request)
    if 'fichier' not in etat:
        return redirect('inscriptions:eleve_import')
    try:
        feuilles = noms_feuilles(etat['fichier'])
        nom_feuille = request.POST.get('feuille') or request.GET.get('feuille') or etat.get('feuille') or feuilles[0]
        feuille = _feuille(etat, nom_feuille)
    except ErreurImport as exc:
        return _abandonner(request, etat, exc)

    classes = _classes(request)
    classe_defaut = ''
    if request.method == 'POST':
        correspondance, erreurs = _lire_correspondance(request.POST, CHAMPS, len(feuille.entetes))
        erreurs += importation.verifier_correspondance(correspondance)
        classe_defaut = request.POST.get('classe_defaut', '')
        if classe_defaut and not classes.filter(pk=classe_defaut).exists():
            classe_defaut = ''
        if not erreurs:
            etat.update(feuille=feuille.nom, correspondance=correspondance, classe_defaut=classe_defaut)
            etat.pop('resultat', None)
            _memoriser(request, etat)
            return redirect('inscriptions:eleve_import_verification')
        for erreur in erreurs:
            messages.error(request, erreur)
    elif etat.get('correspondance') and etat.get('feuille') == feuille.nom:
        correspondance = {c: int(i) for c, i in etat['correspondance'].items()}
        classe_defaut = etat.get('classe_defaut', '')
    else:
        correspondance = detecter_colonnes(feuille.entetes, CHAMPS)

    champs = [{'champ': c, 'index': correspondance.get(c.code)} for c in CHAMPS]
    return render(request, 'inscriptions/eleve_import_correspondance.html', _contexte(
        2, etat=etat, feuille=feuille, feuilles=feuilles, colonnes=_colonnes(feuille), champs=champs,
        apercu=[[texte(v) for v in l] for l in feuille.lignes[:APERCU_LIGNES]], classes=classes,
        classe_defaut=classe_defaut,
        nb_detectes=sum(1 for c in champs if c['index'] is not None),
    ))


# ── Étape 3 : vérification puis import ───────────────────────────────────

def _correspondance_classes(analyse, classes, post=None):
    """Libellés de classe du fichier → classe choisie (rapprochement automatique, puis choix de l'utilisateur)."""
    par_cle = {}
    for classe in classes:
        par_cle.setdefault(cle_classe(classe.nom), classe)
    lignes = []
    for position, (libelle, nb) in enumerate(sorted(analyse.classes.items())):
        if post is not None:
            valeur = post.get(f'classe_{position}', '')
            classe = classes.filter(pk=valeur).first() if valeur else None
        else:
            classe = par_cle.get(cle_classe(libelle))
        lignes.append({'position': position, 'libelle': libelle, 'nb': nb, 'classe': classe})
    return lignes


@login_required
def eleve_import_verification(request):
    etat = _etat(request)
    if 'correspondance' not in etat:
        return redirect('inscriptions:eleve_import_correspondance' if 'fichier' in etat else 'inscriptions:eleve_import')
    annee = get_object_or_404(_annees(request), pk=etat['annee'])
    etab = _etablissement(request)
    try:
        feuille = _feuille(etat)
    except ErreurImport as exc:
        return _abandonner(request, etat, exc)
    correspondance = {c: int(i) for c, i in etat['correspondance'].items()}
    analyse = importation.analyser(feuille, correspondance, etab)
    classes = _classes(request)
    classe_defaut = classes.filter(pk=etat['classe_defaut']).first() if etat.get('classe_defaut') else None

    if request.method == 'POST':
        lignes_classes = _correspondance_classes(analyse, classes, request.POST)
        resultat = importation.importer(
            analyse, annee, {l['libelle']: l['classe'] for l in lignes_classes}, classe_defaut,
            etab.code if etab else '',
        )
        supprimer_fichier(etat['fichier'])
        _memoriser(request, {
            'nom_fichier': etat['nom_fichier'], 'annee': etat['annee'],
            'resultat': {'crees': resultat.crees, 'inscrits': resultat.inscrits, 'existants': resultat.existants,
                         'deja_inscrits': resultat.deja_inscrits, 'sans_classe': resultat.sans_classe,
                         'nb_erreurs': len(analyse.erreurs)},
            'erreurs': [list(e) for e in analyse.erreurs[:ERREURS_MAX]],
        })
        return redirect('inscriptions:eleve_import_resultat')

    lignes_classes = _correspondance_classes(analyse, classes)
    sans_classe = sum(l['nb'] for l in lignes_classes if l['classe'] is None)
    return render(request, 'inscriptions/eleve_import_verification.html', _contexte(
        3, etat=etat, annee=annee, feuille=feuille, analyse=analyse, erreurs=analyse.erreurs[:100],
        lignes_classes=lignes_classes, classes=classes, classe_defaut=classe_defaut,
        nb_sans_libelle=sum(1 for l in analyse.lignes if not l.classe_libelle),
        nb_libelles_sans_classe=sans_classe, apercu=analyse.lignes[:APERCU_LIGNES],
    ))


# ── Étape 4 : résultat ───────────────────────────────────────────────────

@login_required
def eleve_import_resultat(request):
    etat = _etat(request)
    if 'resultat' not in etat:
        return redirect('inscriptions:eleve_import')
    annee = _annees(request).filter(pk=etat['annee']).first()
    return render(request, 'inscriptions/eleve_import_resultat.html', _contexte(
        4, etat=etat, annee=annee, resultat=etat['resultat'], erreurs=etat.get('erreurs', []),
    ))


@login_required
def eleve_import_rapport(request):
    """Rapport Excel des lignes non importées : numéro de ligne, élève, motif — à corriger puis réimporter."""
    etat = _etat(request)
    if 'resultat' not in etat:
        return redirect('inscriptions:eleve_import')
    wb = ExcelExport("Lignes non importées")
    wb.add_title("Import d'élèves — lignes non importées", etat.get('nom_fichier', ''))
    wb.add_header(['Ligne du fichier', 'Élève', 'Motif'])
    for numero, identite, motif in etat.get('erreurs', []):
        wb.add_row([numero, identite, motif])
    return wb.response("import_eleves_erreurs.xlsx")
