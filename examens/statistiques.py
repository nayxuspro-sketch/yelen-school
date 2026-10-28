"""Statistiques ventilées d'une session d'examen : par classe d'origine, par sexe, par centre, par mention et par
tranche de moyenne — inscrits, présents, admis, ajournés, absents, exclus, taux de réussite."""
from decimal import Decimal

from .models import InscriptionExamen

STATUTS = ('INSCRIT', 'ADMIS', 'AJOURNE', 'ABSENT', 'EXCLU')
TRANCHES = (
    ('Moins de 8', Decimal('0'), Decimal('8')), ('8 à 9,99', Decimal('8'), Decimal('10')),
    ('10 à 11,99', Decimal('10'), Decimal('12')), ('12 à 13,99', Decimal('12'), Decimal('14')),
    ('14 à 15,99', Decimal('14'), Decimal('16')), ('16 et plus', Decimal('16'), Decimal('99')),
)
_ORDRE_MENTIONS = ('très bien', 'bien', 'assez bien', 'passable')


def _vide(libelle):
    return {'libelle': libelle, 'inscrits': 0, 'presents': 0, 'admis': 0, 'ajournes': 0, 'absents': 0, 'exclus': 0,
            'admis_g': 0, 'admis_f': 0, 'presents_g': 0, 'presents_f': 0, 'inscrits_g': 0, 'inscrits_f': 0,
            'somme_moyennes': Decimal('0'), 'nb_moyennes': 0}


def _taux(part, total):
    return round(float(part) * 100 / float(total), 1) if total else 0.0


def _ajouter(ligne, c):
    genre = (c.inscription.eleve.genre or '').upper()
    suffixe = '_g' if genre == 'M' else '_f' if genre == 'F' else None
    ligne['inscrits'] += 1
    if suffixe:
        ligne['inscrits' + suffixe] += 1
    if c.statut in ('ADMIS', 'AJOURNE', 'EXCLU'):
        ligne['presents'] += 1
        if suffixe:
            ligne['presents' + suffixe] += 1
    if c.statut == 'ADMIS':
        ligne['admis'] += 1
        if suffixe:
            ligne['admis' + suffixe] += 1
    elif c.statut == 'AJOURNE':
        ligne['ajournes'] += 1
    elif c.statut == 'ABSENT':
        ligne['absents'] += 1
    elif c.statut == 'EXCLU':
        ligne['exclus'] += 1
    if c.moyenne_examen is not None:
        ligne['somme_moyennes'] += c.moyenne_examen
        ligne['nb_moyennes'] += 1


def _finaliser(ligne):
    ligne['taux'] = _taux(ligne['admis'], ligne['presents'])
    ligne['taux_g'] = _taux(ligne['admis_g'], ligne['presents_g'])
    ligne['taux_f'] = _taux(ligne['admis_f'], ligne['presents_f'])
    ligne['moyenne'] = (ligne['somme_moyennes'] / ligne['nb_moyennes']).quantize(Decimal('0.01')) if ligne['nb_moyennes'] else None
    return ligne


def _ventiler(candidats, cle, libelle, ordre=None):
    lignes = {}
    for c in candidats:
        k = cle(c)
        if k not in lignes:
            lignes[k] = _vide(libelle(c))
        _ajouter(lignes[k], c)
    resultat = [_finaliser(l) for l in lignes.values()]
    return sorted(resultat, key=ordre) if ordre else sorted(resultat, key=lambda l: l['libelle'])


def _rang_mention(ligne):
    lib = ligne['libelle'].lower()
    return (_ORDRE_MENTIONS.index(lib) if lib in _ORDRE_MENTIONS else len(_ORDRE_MENTIONS), lib)


def statistiques_session(session):
    """Tableaux de la session : global (G/F/T), par classe d'origine, par centre, par mention, par tranche de
    moyenne, et les dix meilleures moyennes. Taux de réussite = admis / présents (absents exclus du dénominateur)."""
    candidats = list(
        InscriptionExamen.objects.filter(session=session)
        .select_related('inscription__eleve', 'inscription__classe', 'centre')
        .order_by('inscription__classe__nom', 'inscription__eleve__nom', 'inscription__eleve__prenom')
    )
    globale = _vide('Session')
    for c in candidats:
        _ajouter(globale, c)
    _finaliser(globale)
    admis_notes = [c for c in candidats if c.statut == 'ADMIS' and c.moyenne_examen is not None]
    tranches = []
    for libelle, borne_min, borne_max in TRANCHES:
        nb = sum(1 for c in candidats if c.moyenne_examen is not None and borne_min <= c.moyenne_examen < borne_max)
        tranches.append({'libelle': libelle, 'nb': nb, 'taux': _taux(nb, globale['nb_moyennes'])})
    par_classe = _ventiler(candidats, lambda c: c.inscription.classe_id, lambda c: c.inscription.classe.nom)
    par_centre = _ventiler(candidats, lambda c: c.centre_id, lambda c: c.centre.nom if c.centre else 'Sans centre')
    return {
        'candidats': candidats,
        'globale': globale,
        'par_classe': par_classe,
        'par_centre': par_centre,
        'tableaux': [("Par classe d'origine", par_classe), ('Par centre', par_centre)],
        'par_mention': _ventiler([c for c in candidats if c.statut == 'ADMIS'],
                                 lambda c: (c.mention or '').strip().lower() or 'sans mention',
                                 lambda c: (c.mention or '').strip() or 'Sans mention', ordre=_rang_mention),
        'tranches': tranches,
        'meilleurs': sorted(admis_notes, key=lambda c: -c.moyenne_examen)[:10],
        'non_notes': sum(1 for c in candidats if c.statut == 'INSCRIT'),
    }
