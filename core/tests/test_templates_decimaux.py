"""Garde-fou : un Decimal rendu brut dans un attribut numérique (value/min/max/step d'un
<input type="number">) est localisé en fr-fr (« 12,50 ») ; le navigateur rejette la valeur et le
champ apparaît vide. Les décimaux doivent passer par |floatformat:"-2u" (non localisé)."""
import re

from core.tests.test_csp_templates import RACINE, _gabarits

_INPUT = re.compile(r'<input\b[^>]*>', re.S)
_ATTRIBUT = re.compile(r'\b(?:value|min|max|step)="((?:\{\{.*?\}\}|[^"])*)"', re.S)
_VARIABLE = re.compile(r'\{\{\s*(.*?)\s*\}\}', re.S)
_NON_LOCALISE = re.compile(r'floatformat:["\']-?\d*u["\']|floatformat:0\b|\|unlocalize\b|\|stringformat:')

# Expressions entières (IntegerField, années, compteurs) ou DecimalField(decimal_places=0) : rendu sûr.
_SANS_DECIMALES = {
    'activite.capacite_max', 'annee_filtre', 'appr.ordre', 'bulletin.absences_justifiees',
    'bulletin.absences_non_justifiees', 'bulletin.retards', 'categorie.ordre', 'classe.capacite_max',
    'config.SMS_HTTP_TIMEOUT', 'config.points_depart', 'config.seuil_alerte', 'config.seuil_conseil',
    'config.seuil_exclusion', 'cycle.ordre', 'd.jours_avant', 'discipline.ordre',
    'instance.annee_acquisition', 'instance.annee_edition', 'instance.prix_remplacement', 'localisation.etage',
    'periode.numero', 'post_data.montant', 'presence.minutes_retard', 'rubrique.ordre', 'statut.ordre',
    'tarif.montant', 'type_eval.nb_meilleures_notes', 'type_eval.ordre',
}


def test_aucun_decimal_localise_dans_un_champ_numerique():
    fautifs = []
    for f in _gabarits():
        s = f.read_text(encoding='utf-8')
        for m in _INPUT.finditer(s):
            if not re.search(r'type=["\']number["\']', m.group(0)):
                continue
            for attribut in _ATTRIBUT.finditer(m.group(0)):
                for expression in _VARIABLE.findall(attribut.group(1)):
                    if _NON_LOCALISE.search(expression):
                        continue
                    if expression.split('|')[0].strip() in _SANS_DECIMALES:
                        continue
                    fautifs.append(f"{f.relative_to(RACINE)}:{s[:m.start()].count(chr(10)) + 1} {{{{ {expression} }}}}")
    assert fautifs == [], (
        'Decimal localisé dans un <input type="number"> : ajouter |floatformat:"-2u" '
        '(ou inscrire l’expression dans _SANS_DECIMALES si le champ est entier) : ' + ', '.join(fautifs)
    )
