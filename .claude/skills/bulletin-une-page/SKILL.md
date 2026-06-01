---
name: bulletin-une-page
description: >
  Utilise ce skill OBLIGATOIREMENT dès que l'utilisateur veut que les bulletins de
  notes tiennent sur une seule page, ou qu'il parle de mise en page des bulletins PDF,
  de compresser/réduire un bulletin, de problème de saut de page dans les bulletins,
  de bulletin trop long ou trop court, ou de "page-break" dans les bulletins.
  Ce skill couvre le template HTML WeasyPrint, le CSS @page, la compression du contenu,
  et la configuration Django (vue, service, template) pour tous les cycles scolaires.
  Déclenche également si l'utilisateur dit "le bulletin dépasse une page",
  "le bulletin est trop grand", "ajuste la mise en page du bulletin", ou toute variante.
---

# Bulletin une page — Guide complet YELEN SCHOOL

## Objectif
Garantir que **chaque bulletin de notes s'imprime sur exactement une page A4**,
quel que soit le cycle (Préscolaire, Primaire, Post-primaire, Secondaire) et
quel que soit le nombre de matières.

---

## Étape 0 — Lire les fichiers de référence AVANT de coder

| Fichier                          | Pourquoi                                        |
|----------------------------------|-------------------------------------------------|
| `static/css/yelen.css`           | Classes CSS existantes — ne rien inventer       |
| `bulletins/templates/`           | Templates existants à modifier (pas recréer)    |
| `bulletins/services.py`          | Logique de génération PDF (WeasyPrint)          |
| `bulletins/views.py`             | Vue de prévisualisation et de téléchargement    |
| `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` | À mettre à jour après chaque modification |

---

## Étape 1 — Règles CSS @page pour WeasyPrint

Le fichier CSS dédié aux bulletins PDF est **séparé de `yelen.css`** car WeasyPrint
utilise des règles spéciales qui ne s'appliquent qu'à l'impression.

### Fichier : `bulletins/static/bulletins/css/bulletin_pdf.css`

```css
/* ============================================================
   BULLETIN PDF — YELEN SCHOOL
   WeasyPrint uniquement. Ne pas utiliser dans les templates web.
   ============================================================ */

@page {
    size: A4 portrait;
    margin: 10mm 12mm 10mm 12mm;  /* top right bottom left */

    @top-center {
        content: "";  /* Pas d'en-tête de page répété */
    }
    @bottom-center {
        content: "";  /* Pas de pied de page répété */
    }
}

/* Empêcher tout saut de page non voulu */
html, body {
    margin: 0;
    padding: 0;
    height: 100%;
}

/* Conteneur principal — s'adapte à la page */
.bulletin-page {
    width: 100%;
    height: 267mm;  /* A4 (297mm) - marges (10+10=20mm) - sécurité (10mm) */
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: 'Outfit', Arial, sans-serif;
    font-size: 8pt;
    color: #1a1a1a;
    background: #ffffff;
}

/* En-tête du bulletin */
.bulletin-header {
    flex-shrink: 0;
    margin-bottom: 3mm;
}

/* Tableau des notes — prend l'espace disponible */
.bulletin-notes {
    flex: 1;
    overflow: hidden;
}

/* Pied du bulletin */
.bulletin-footer {
    flex-shrink: 0;
    margin-top: 3mm;
}

/* ---- Tableau des matières ---- */
.bulletin-notes table {
    width: 100%;
    border-collapse: collapse;
    font-size: 7.5pt;
}

.bulletin-notes thead th {
    background-color: #00A86B;
    color: #ffffff;
    padding: 2mm 1.5mm;
    text-align: center;
    font-weight: 600;
    font-size: 7pt;
    border: 0.3mm solid #008a57;
}

.bulletin-notes tbody td {
    padding: 1.5mm 1.5mm;
    border: 0.3mm solid #cccccc;
    font-size: 7pt;
}

.bulletin-notes tbody tr:nth-child(even) {
    background-color: #f5faf7;
}

/* Ligne de totaux / moyennes */
.bulletin-notes tfoot td {
    background-color: #e8f5ef;
    font-weight: 700;
    padding: 2mm 1.5mm;
    border: 0.3mm solid #00A86B;
    font-size: 7.5pt;
}

/* ---- Sections latérales (appréciations, absences) ---- */
.bulletin-side-section {
    font-size: 7pt;
    border: 0.3mm solid #cccccc;
    padding: 2mm;
    margin-top: 2mm;
}

.bulletin-side-section h4 {
    font-size: 7.5pt;
    font-weight: 700;
    color: #00A86B;
    margin: 0 0 1mm 0;
    text-transform: uppercase;
}

/* ---- Signatures ---- */
.bulletin-signatures {
    display: flex;
    justify-content: space-between;
    margin-top: 3mm;
    font-size: 7pt;
}

.bulletin-signatures .signe-bloc {
    text-align: center;
    width: 30%;
}

.bulletin-signatures .signe-ligne {
    border-top: 0.3mm solid #555555;
    margin-top: 8mm;
    padding-top: 1mm;
}

/* ---- Ajustements par nombre de matières ---- */
/* Peu de matières (≤ 8) : agrandir légèrement */
.bulletin-page.peu-matieres .bulletin-notes table {
    font-size: 8.5pt;
}
.bulletin-page.peu-matieres .bulletin-notes td,
.bulletin-page.peu-matieres .bulletin-notes th {
    padding: 2.5mm 2mm;
}

/* Beaucoup de matières (≥ 15) : compresser */
.bulletin-page.beaucoup-matieres .bulletin-notes table {
    font-size: 6.5pt;
}
.bulletin-page.beaucoup-matieres .bulletin-notes td,
.bulletin-page.beaucoup-matieres .bulletin-notes th {
    padding: 1mm 1mm;
}

/* Interdire tout saut de page à l'intérieur du bulletin */
.bulletin-page {
    page-break-inside: avoid;
    page-break-after: avoid;
    page-break-before: avoid;
    break-inside: avoid;
}
```

---

## Étape 2 — Template HTML du bulletin

### Fichier : `bulletins/templates/bulletins/bulletin_pdf.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Bulletin — {{ eleve.nom_complet }}</title>
    <link rel="stylesheet" href="{{ bulletin_css_url }}">
</head>
<body>

{# Classe dynamique selon le nombre de matières #}
{% with nb=notes|length %}
<div class="bulletin-page{% if nb <= 8 %} peu-matieres{% elif nb >= 15 %} beaucoup-matieres{% endif %}">

    {# ── EN-TÊTE ── #}
    <div class="bulletin-header">
        <table style="width:100%; border:none;">
            <tr>
                <td style="width:20%; text-align:center; vertical-align:middle;">
                    {% if etablissement.logo %}
                    <img src="{{ etablissement.logo_url }}"
                         style="max-height:18mm; max-width:30mm;">
                    {% endif %}
                </td>
                <td style="text-align:center; vertical-align:middle;">
                    <div style="font-size:10pt; font-weight:700; color:#00A86B; text-transform:uppercase;">
                        {{ etablissement.nom }}
                    </div>
                    <div style="font-size:8pt; color:#555;">
                        {{ etablissement.adresse }} — Tél : {{ etablissement.telephone }}
                    </div>
                    <div style="font-size:9pt; font-weight:600; margin-top:2mm;">
                        BULLETIN DE NOTES — {{ periode.libelle|upper }}
                    </div>
                    <div style="font-size:8pt;">
                        Année scolaire : {{ annee_scolaire.libelle }}
                    </div>
                </td>
                <td style="width:20%; text-align:center;">
                    {# Cachet de l'établissement si disponible #}
                </td>
            </tr>
        </table>

        {# Informations élève #}
        <table style="width:100%; border:0.3mm solid #cccccc; margin-top:2mm;
                      border-collapse:collapse; font-size:7.5pt;">
            <tr>
                <td style="padding:1.5mm 2mm; border-right:0.3mm solid #ccc; width:25%;">
                    <strong>Nom :</strong> {{ eleve.nom|upper }}
                </td>
                <td style="padding:1.5mm 2mm; border-right:0.3mm solid #ccc; width:25%;">
                    <strong>Prénom :</strong> {{ eleve.prenom }}
                </td>
                <td style="padding:1.5mm 2mm; border-right:0.3mm solid #ccc; width:20%;">
                    <strong>Classe :</strong> {{ classe.libelle }}
                </td>
                <td style="padding:1.5mm 2mm; border-right:0.3mm solid #ccc; width:15%;">
                    <strong>Matricule :</strong><br>
                    <span style="font-family:'DejaVu Sans Mono'; color:#00A86B; font-size:7pt;">
                        {{ eleve.matricule }}
                    </span>
                </td>
                <td style="padding:1.5mm 2mm; width:15%;">
                    <strong>Effectif :</strong> {{ effectif_classe }}
                </td>
            </tr>
        </table>
    </div>

    {# ── TABLEAU DES NOTES ── #}
    <div class="bulletin-notes">
        <table>
            <thead>
                <tr>
                    <th style="text-align:left; width:28%;">Matière</th>
                    <th>Coeff.</th>
                    {% for evaluation in types_evaluations %}
                    <th>{{ evaluation.code }}</th>
                    {% endfor %}
                    <th>Moy./20</th>
                    <th>Moy. Cl.</th>
                    <th>Min Cl.</th>
                    <th>Max Cl.</th>
                    <th style="text-align:left; width:22%;">Appréciation</th>
                </tr>
            </thead>
            <tbody>
                {% for note in notes %}
                <tr>
                    <td style="text-align:left; font-weight:{% if note.est_groupe %}600{% else %}400{% endif %};">
                        {% if not note.est_groupe %}&nbsp;&nbsp;{% endif %}
                        {{ note.matiere.libelle }}
                    </td>
                    <td style="text-align:center;">{{ note.coefficient }}</td>
                    {% for v in note.valeurs %}
                    <td style="text-align:center;">
                        {% if v is not None %}{{ v|floatformat:1 }}{% else %}—{% endif %}
                    </td>
                    {% endfor %}
                    <td style="text-align:center; font-weight:600;
                        color:{% if note.moyenne >= 10 %}#007a4d{% else %}#c0392b{% endif %};">
                        {{ note.moyenne|floatformat:2 }}
                    </td>
                    <td style="text-align:center;">{{ note.moyenne_classe|floatformat:2 }}</td>
                    <td style="text-align:center;">{{ note.min_classe|floatformat:2 }}</td>
                    <td style="text-align:center;">{{ note.max_classe|floatformat:2 }}</td>
                    <td style="text-align:left; font-style:italic; font-size:6.5pt;">
                        {{ note.appreciation }}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="{% if types_evaluations %}{{ types_evaluations|length|add:1 }}{% else %}2{% endif %}"
                        style="text-align:right; font-weight:700;">
                        MOYENNE GÉNÉRALE :
                    </td>
                    <td style="text-align:center; color:#00A86B; font-weight:700;">
                        {{ bulletin.moyenne_generale|floatformat:2 }}/20
                    </td>
                    <td style="text-align:center;">{{ bulletin.moyenne_classe|floatformat:2 }}</td>
                    <td style="text-align:center;">{{ bulletin.min_classe|floatformat:2 }}</td>
                    <td style="text-align:center;">{{ bulletin.max_classe|floatformat:2 }}</td>
                    <td style="text-align:left; font-style:italic; font-size:6.5pt;">
                        {{ bulletin.appreciation_generale }}
                    </td>
                </tr>
            </tfoot>
        </table>
    </div>

    {# ── PIED DE BULLETIN ── #}
    <div class="bulletin-footer">
        <table style="width:100%; border-collapse:collapse;">
            <tr>
                <td style="width:60%; vertical-align:top;">
                    <div class="bulletin-side-section">
                        <h4>Absences &amp; Retards</h4>
                        <table style="width:100%; font-size:7pt; border-collapse:collapse;">
                            <tr>
                                <td>Absences justifiées :</td>
                                <td style="font-weight:600;">{{ bulletin.absences_justifiees }}h</td>
                                <td>Absences injustifiées :</td>
                                <td style="font-weight:600;">{{ bulletin.absences_injustifiees }}h</td>
                                <td>Retards :</td>
                                <td style="font-weight:600;">{{ bulletin.retards }}</td>
                            </tr>
                        </table>
                    </div>
                    {% if bulletin.observation_conseil %}
                    <div class="bulletin-side-section" style="margin-top:1.5mm;">
                        <h4>Observation du Conseil de Classe</h4>
                        <p style="margin:0; font-size:7pt;">{{ bulletin.observation_conseil }}</p>
                    </div>
                    {% endif %}
                </td>
                <td style="width:5%;"></td>
                <td style="width:35%; vertical-align:top;">
                    <div class="bulletin-side-section">
                        <h4>Résultats</h4>
                        <table style="width:100%; font-size:7pt; border-collapse:collapse;">
                            <tr>
                                <td>Rang :</td>
                                <td style="font-weight:700; color:#00A86B;">
                                    {{ bulletin.rang }}/{{ effectif_classe }}
                                </td>
                            </tr>
                            <tr>
                                <td>Décision :</td>
                                <td style="font-weight:700;">{{ bulletin.decision }}</td>
                            </tr>
                        </table>
                    </div>
                </td>
            </tr>
        </table>

        {# Signatures #}
        <div class="bulletin-signatures">
            {% for signataire in signataires %}
            <div class="signe-bloc">
                <div>{{ signataire.titre }}</div>
                {% if signataire.nom %}
                <div class="signe-ligne">{{ signataire.nom }}</div>
                {% else %}
                <div class="signe-ligne">&nbsp;</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

</div>
{% endwith %}

</body>
</html>
```

> ⚠️ **Interdit** : pas de CSS inline `style="..."` dans le template web. Dans le
> template `bulletin_pdf.html`, le CSS inline **est toléré uniquement** car WeasyPrint
> ne supporte pas toutes les propriétés CSS via feuille externe. Signaler si besoin.

---

## Étape 3 — Service de génération PDF

### Fichier : `bulletins/services.py` — méthode `generer_pdf`

```python
import os
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML, CSS

def generer_bulletin_pdf(bulletin, request=None):
    """
    Génère un bulletin PDF tenant sur exactement une page A4.
    Retourne les bytes du PDF.
    """
    notes = _preparer_notes(bulletin)
    signataires = _get_signataires(bulletin.classe.cycle, type_document='bulletin')

    context = {
        'bulletin': bulletin,
        'eleve': bulletin.eleve,
        'classe': bulletin.classe,
        'periode': bulletin.periode,
        'annee_scolaire': bulletin.annee_scolaire,
        'etablissement': bulletin.classe.etablissement,
        'notes': notes,
        'types_evaluations': _get_types_evaluations(bulletin),
        'effectif_classe': _get_effectif(bulletin.classe, bulletin.periode),
        'signataires': signataires,
        # URL absolue pour le CSS (WeasyPrint en a besoin)
        'bulletin_css_url': _get_css_url(request),
    }

    html_string = render_to_string('bulletins/bulletin_pdf.html', context)

    css_path = os.path.join(
        settings.BASE_DIR,
        'bulletins', 'static', 'bulletins', 'css', 'bulletin_pdf.css'
    )

    pdf_bytes = HTML(
        string=html_string,
        base_url=settings.MEDIA_ROOT,
    ).write_pdf(
        stylesheets=[CSS(filename=css_path)],
        presentational_hints=True,   # Respecte width/height HTML
        optimize_images=True,
    )

    return pdf_bytes


def _preparer_notes(bulletin):
    """
    Retourne les notes ordonnées avec statistiques de classe.
    Chaque élément : {matiere, coefficient, valeurs, moyenne,
                      moyenne_classe, min_classe, max_classe, appreciation}
    """
    # Implémenter selon la structure existante des modèles de notes
    raise NotImplementedError("À adapter à la structure des modèles Note/Matiere du projet")


def _get_signataires(cycle, type_document):
    """
    Récupère les signataires configurables par cycle et type de document.
    Règle métier YELEN : signataires configurables.
    """
    from bulletins.models import ConfigurationSignataire
    return ConfigurationSignataire.objects.filter(
        cycle=cycle,
        type_document=type_document,
        actif=True,
    ).order_by('ordre')


def _get_css_url(request):
    """URL absolue du CSS pour WeasyPrint (nécessaire pour @font-face)."""
    if request:
        return request.build_absolute_uri(
            '/static/bulletins/css/bulletin_pdf.css'
        )
    return f"{settings.STATIC_ROOT}/bulletins/css/bulletin_pdf.css"
```

---

## Étape 4 — Vue Django

### Fichier : `bulletins/views.py`

```python
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Bulletin
from .services import generer_bulletin_pdf

@login_required
def telecharger_bulletin_pdf(request, bulletin_id):
    """Génère et télécharge le bulletin PDF d'un élève."""
    bulletin = get_object_or_404(Bulletin, pk=bulletin_id)

    # Contrôle d'accès à ajouter selon les règles métier

    pdf_bytes = generer_bulletin_pdf(bulletin, request=request)

    nom_fichier = (
        f"bulletin_{bulletin.eleve.matricule}"
        f"_{bulletin.periode.code}"
        f"_{bulletin.annee_scolaire.code}.pdf"
    )

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    return response
```

---

## Étape 5 — Checklist de vérification une-page

Après avoir généré un bulletin de test, vérifier chaque point :

- [ ] Le PDF fait exactement 1 page (vérifier avec un lecteur PDF)
- [ ] Les marges sont ≥ 8mm sur tous les côtés (impression sans coupure)
- [ ] Le tableau des notes n'est pas tronqué (toutes les matières visibles)
- [ ] La police minimum est ≥ 6pt (lisibilité acceptable)
- [ ] Les signatures apparaissent au bas de la page
- [ ] Le logo de l'établissement est affiché si configuré
- [ ] Le matricule est en `DejaVu Sans Mono` couleur `#00A86B`
- [ ] Tester avec le cycle ayant le plus de matières (cas le plus critique)
- [ ] Tester l'impression réelle (pas seulement l'aperçu PDF)

---

## Étape 6 — Dépannage bulletin > 1 page

Si le bulletin dépasse encore une page après ces modifications :

| Symptôme                      | Solution                                             |
|-------------------------------|------------------------------------------------------|
| Tableau déborde               | Réduire `font-size` de `0.5pt` dans `.bulletin-notes table` |
| En-tête trop haut             | Réduire `max-height` du logo (passer de 18mm à 14mm) |
| Appréciations très longues    | Limiter à 60 caractères côté service (`appreciation[:60]`) |
| Signatures prennent trop      | Réduire `margin-top` de `.signe-ligne` (8mm → 5mm)  |
| Logo haute résolution lent    | Ajouter `optimize_images=True` dans `write_pdf()`    |
| Marges incorrectes            | Vérifier `@page { margin: … }` — WeasyPrint prioritaire sur tout |

---

## Règles YELEN à ne jamais enfreindre dans ce contexte

- **WeasyPrint** est le seul moteur PDF — jamais reportlab, xhtml2pdf ou autre
- La police du bulletin reste **Outfit** (corps) + **DejaVu Sans Mono** (matricules)
- Les montants/notes restent sur **20** — jamais sur 100
- Les **signataires sont configurables** par cycle et type de document (modèle `ConfigurationSignataire`)
- Mettre à jour `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` après toute modification
- Terminer la réponse par `📘 Guide mis à jour — Section Bulletins PDF`
