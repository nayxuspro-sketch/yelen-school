"""
signataire_tags.py
==================
Tag de template autonome pour l'affichage automatique des signataires sur
tous les documents PDF de YELEN SCHOOL.

Usage dans n'importe quel template PDF :

    {% load signataire_tags %}
    {% signataire_auto "CERT_SCOL" %}

Le tag auto-détecte le cycle et l'année scolaire depuis le contexte du
template parent (inscription, classe, trimestre, annee_scolaire, etc.)
puis applique le repli progressif de SignataireDocument.objects.get_signataire().

Codes TypeDocument disponibles
────────────────────────────────
  CERT_SCOL         Certificat de Scolarité
  BULLETIN          Bulletin de Notes
  RECU_PAIEMENT     Reçu de Paiement
  ATTESTATION       Attestation de Non-Redevabilité
  LISTE_CLASSE      Liste Alphabétique de Classe
  LISTE_PERSONNEL   Liste du Personnel
  LISTE_REDEVABLES  Liste des Redevables
  CURSUS            Cursus Scolaire Complet
  CARTE_ID          Carte d'Identité Scolaire
  AUTORISATION      Autorisation d'Absence
"""

import html as html_escape_lib
from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone

register = template.Library()

# CSS commun — injecté une seule fois par document (WeasyPrint l'applique globalement)
_SIGNATAIRE_CSS = """
<style>
.msig-zone        { margin-top:28pt; page-break-inside:avoid; break-inside:avoid; }
.msig-date        { font-size:10pt; color:#222; text-align:center; margin-bottom:10pt; }
.msig-table       { width:100%; border-collapse:collapse; }
.msig-col         { vertical-align:top; text-align:center; padding:0 8pt; }
.msig-col:first-child { text-align:left; }
.msig-col:last-child  { text-align:right; }
.msig-fonction    { font-size:10pt; color:#1c3557; font-weight:bold; }
.msig-name        { font-size:11pt; font-weight:bold; color:#000; margin-top:1.6cm; line-height:1.3; }
.msig-honors      { font-size:8pt; font-style:italic; color:#555; margin-top:2pt; }
/* Compatibilité ancienne classe sig-zone (pour templates qui utilisent le partial) */
.sig-zone          { margin-top:32pt; text-align:right; page-break-inside:avoid; break-inside:avoid; }
.sig-date          { font-size:10pt; color:#222; }
.sig-fonction      { font-size:11pt; color:#111; margin-top:1cm; }
.sig-name          { font-size:11pt; font-weight:bold; color:#000; margin-top:2cm; line-height:1.3; }
.sig-honors        { font-size:8.5pt; font-style:italic; color:#333; margin-top:2px; }
</style>
"""


def _e(value):
    """Échappe une valeur pour insertion sécurisée dans du HTML."""
    return html_escape_lib.escape(str(value or ''))


def _detecter_cycle_et_annee(context):
    """
    Auto-détecte le Cycle et l'AnneeScolaire depuis le contexte du template.
    """
    cycle = None
    annee = None

    inscription = context.get('inscription')
    if inscription:
        classe = getattr(inscription, 'classe', None)
        if classe:
            cycle = getattr(classe, 'cycle', None)

    if cycle is None:
        classe = context.get('classe')
        if classe:
            cycle = getattr(classe, 'cycle', None)

    if cycle is None:
        cycle = context.get('cycle')

    if inscription:
        annee = getattr(inscription, 'annee_scolaire', None)

    if annee is None:
        annee = context.get('annee_scolaire')

    if annee is None:
        trimestre = context.get('trimestre')
        if trimestre:
            annee = getattr(trimestre, 'annee_scolaire', None)

    if annee is None:
        annee = context.get('annee_courante') or context.get('annee_selected')

    return cycle, annee


def _trouver_type_document(type_doc_code, cycle):
    """
    Recherche progressive du TypeDocument, cycle-aware.
    """
    from parametres.models import TypeDocument
    qs = TypeDocument.objects.filter(actif=True)

    td = qs.filter(code=type_doc_code).first()
    if td:
        return td

    td = qs.filter(code__iexact=type_doc_code).first()
    if td:
        return td

    if cycle:
        td = qs.filter(code__istartswith=type_doc_code, cycle=cycle).first()
        if td:
            return td

    td = qs.filter(code__istartswith=type_doc_code).first()
    if td:
        return td

    mots = [m for m in type_doc_code.lower().replace('-', '_').split('_') if len(m) > 3]
    if mots:
        qs_mots = qs
        for mot in mots:
            qs_mots = qs_mots.filter(code__icontains=mot)
        if cycle:
            td = qs_mots.filter(cycle=cycle).first()
            if td:
                return td
        td = qs_mots.first()
        if td:
            return td

    return None


def _bloc_signataire_html(fonction, membre, titres_honorifiques=None, titre_honorifique=''):
    """
    Retourne le HTML interne d'un seul signataire (fonction + nom + titres).
    Sans conteneur — à placer dans une cellule de table.
    """
    if not membre:
        return ''

    fonction_html = _e(fonction or 'Le Directeur')
    nom_html = f"{_e(membre.nom).upper()} {_e(membre.prenom)}"

    titres_html = ''
    if titres_honorifiques:
        lignes = '<br>'.join(_e(t) for t in titres_honorifiques)
        titres_html = f'<div class="msig-honors">{lignes}</div>'
    elif titre_honorifique:
        titres_html = f'<div class="msig-honors">{_e(titre_honorifique)}</div>'

    return (
        f'<div class="msig-fonction">{fonction_html}</div>'
        f'<div class="msig-name">{nom_html}</div>'
        f'{titres_html}'
    )


@register.simple_tag(takes_context=True)
def signataire_auto(context, type_doc_code):
    """
    Génère le bloc HTML de signature pour un document PDF.

    - 1 seul signataire  → aligné à droite (mise en page classique)
    - 2+ signataires     → tableau côte à côte (gauche ↔ droite)

    Les co-signataires sont définis via CoSignataire liés au SignataireDocument principal.
    """
    try:
        from parametres.models import SignataireDocument, CoSignataire

        cycle, annee = _detecter_cycle_et_annee(context)

        type_doc = _trouver_type_document(type_doc_code, cycle)
        if not type_doc:
            return mark_safe('')

        signataire = SignataireDocument.objects.get_signataire(
            cycle=cycle,
            type_document=type_doc,
            annee_scolaire=annee,
        )
        if not signataire:
            return mark_safe('')

        membre_principal = signataire.get_membre_personnel()
        if not membre_principal:
            return mark_safe('')

        # Date + lieu
        identite = context.get('identite')
        ville_prefix = ''
        if identite and getattr(identite, 'ville', None):
            ville_prefix = f"{_e(identite.ville)}, "

        try:
            from django.utils.formats import date_format
            date_str = date_format(timezone.now(), 'd F Y', use_l10n=True)
        except Exception:
            date_str = timezone.now().strftime('%d %B %Y')

        # Construire la liste ordonnée de tous les signataires
        # Principal en premier (ordre implicite 1), puis co-signataires triés par ordre
        co_signataires = list(
            CoSignataire.objects
            .filter(signataire_principal=signataire, actif=True)
            .order_by('ordre')
        )

        if not co_signataires:
            # ── Cas simple : un seul signataire, aligné à droite ──────────────
            fonction = _e(signataire.fonction or signataire.titre or 'Le Directeur')
            nom = f"{_e(membre_principal.nom).upper()} {_e(membre_principal.prenom)}"

            titres_html = ''
            if signataire.titres_honorifiques:
                lignes = '<br>'.join(_e(t) for t in signataire.titres_honorifiques)
                titres_html = f'<div class="msig-honors">{lignes}</div>'
            elif signataire.titre_honorifique:
                titres_html = f'<div class="msig-honors">{_e(signataire.titre_honorifique)}</div>'

            bloc = (
                f'{_SIGNATAIRE_CSS}'
                f'<div class="msig-zone" style="text-align:right;">'
                f'<div class="msig-date" style="text-align:right;">{ville_prefix}le {date_str}</div>'
                f'<div class="msig-fonction">{fonction}</div>'
                f'<div class="msig-name">{nom}</div>'
                f'{titres_html}'
                f'</div>'
            )
            return mark_safe(bloc)

        # ── Cas multi-signataires : tableau côte à côte ───────────────────────
        # Construire la liste : [principal] + [co_signataires]
        all_sigs = [
            {
                'membre': membre_principal,
                'fonction': signataire.fonction or signataire.titre or 'Le Directeur',
                'titres_honorifiques': signataire.titres_honorifiques,
                'titre_honorifique': signataire.titre_honorifique,
            }
        ]
        for co in co_signataires:
            m = co.get_membre_personnel()
            if m:
                all_sigs.append({
                    'membre': m,
                    'fonction': co.fonction or 'Co-signataire',
                    'titres_honorifiques': co.titres_honorifiques,
                    'titre_honorifique': '',
                })

        n = len(all_sigs)
        col_width = round(100 / n)

        # Alignements : premier à gauche, dernier à droite, milieux centrés
        def align(i):
            if i == 0:
                return 'left'
            if i == n - 1:
                return 'right'
            return 'center'

        cols_html = ''
        for i, sig_data in enumerate(all_sigs):
            inner = _bloc_signataire_html(
                sig_data['fonction'],
                sig_data['membre'],
                sig_data.get('titres_honorifiques'),
                sig_data.get('titre_honorifique', ''),
            )
            cols_html += (
                f'<td class="msig-col" style="width:{col_width}%; text-align:{align(i)};">'
                f'{inner}'
                f'</td>'
            )

        bloc = (
            f'{_SIGNATAIRE_CSS}'
            f'<div class="msig-zone">'
            f'<div class="msig-date">{ville_prefix}le {date_str}</div>'
            f'<table class="msig-table"><tr>{cols_html}</tr></table>'
            f'</div>'
        )
        return mark_safe(bloc)

    except Exception:
        return mark_safe('')
