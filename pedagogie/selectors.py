"""Sélecteurs du module pédagogie (lecture seule, sans effet de bord).

Configuration des matières par portée : cycle entier, niveau, niveau + série du bac.
"""
import unicodedata

from parametres.models import Classe, Cycle

from .forms import MatiereCycleForm

# Ordre pédagogique des niveaux usuels (clé normalisée → rang) ; les niveaux inconnus
# viennent ensuite, par ordre alphabétique.
_RANGS = {}
for _rang, _alias in enumerate([
    ('ps', 'petitesection'), ('ms', 'moyennesection'), ('gs', 'grandesection'),
    ('cp1',), ('cp2',), ('ce1',), ('ce2',), ('cm1',), ('cm2',),
    ('6eme', '6e', 'sixieme'), ('5eme', '5e', 'cinquieme'), ('4eme', '4e', 'quatrieme'), ('3eme', '3e', 'troisieme'),
    ('2nde', '2de', 'seconde'), ('1ere', '1re', 'premiere'), ('tle', 'terminale', 'term'),
]):
    for _a in _alias:
        _RANGS[_a] = _rang

SERIES_BAC = dict(Classe._meta.get_field('serie_bac').choices)


def _normaliser(niveau):
    texte = unicodedata.normalize('NFKD', niveau or '').encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in texte if c.isalnum())


def rang_niveau(niveau):
    """Clé de tri d'un niveau : rang pédagogique connu, puis libellé."""
    return (_RANGS.get(_normaliser(niveau), len(_RANGS)), (niveau or '').lower())


def portees_cycle(cycle, matiere=None):
    """Portées (niveau, série) d'un cycle : niveaux des classes actives du cycle, plus les
    portées déjà configurées pour la matière (afin de rester visibles et supprimables)."""
    portees = {
        ((niveau or '').strip(), serie or '')
        for niveau, serie in Classe.objects.filter(cycle=cycle, actif=True).values_list('niveau', 'serie_bac')
    }
    if matiere is not None:
        portees |= set(matiere.configurations_cycle.filter(cycle=cycle).values_list('niveau', 'serie'))
    portees.discard(('', ''))
    return sorted(portees, key=lambda p: (rang_niveau(p[0]), p[1]))


def ligne_configuration(matiere, cycle, niveau='', serie='', configs=None, form=None):
    """Données d'une ligne de configuration pour le gabarit ``cycle_config_row.html``.

    ``base`` fournit les valeurs héritées (portée parente ou défauts de la matière) :
    niveau + série → niveau → tout le cycle → matière.
    """
    if configs is None:
        configs = {(c.niveau, c.serie): c for c in matiere.configurations_cycle.filter(cycle=cycle)}
    config = configs.get((niveau, serie))
    parents = [(niveau, '')] if serie else []
    parents.append(('', ''))
    base = next((configs[cle] for cle in parents if cle != (niveau, serie) and cle in configs), matiere)
    return {
        'niveau': niveau,
        'serie': serie,
        'serie_label': SERIES_BAC.get(serie, ''),
        'cle': f"{niveau}-{serie}" if serie else niveau,
        'config': config,
        'base': base,
        'valeurs': config or base,
        'form': form or MatiereCycleForm(instance=config),
    }


def configurations_matiere(matiere):
    """Cycles actifs avec, pour chacun, la ligne « tout le cycle » puis une ligne par portée."""
    resultat = []
    for cycle in Cycle.objects.filter(actif=True).order_by('ordre', 'nom'):
        configs = {(c.niveau, c.serie): c for c in matiere.configurations_cycle.filter(cycle=cycle)}
        lignes = [ligne_configuration(matiere, cycle, '', '', configs)]
        lignes += [ligne_configuration(matiere, cycle, n, s, configs) for n, s in portees_cycle(cycle, matiere)]
        resultat.append({'cycle': cycle, 'lignes': lignes, 'nb_portees': len(lignes) - 1})
    return resultat
