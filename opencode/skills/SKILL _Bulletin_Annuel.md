---
name: yelen-school-bulletin-annuel
description: >
  Génère le bulletin annuel de notes pour YELEN SCHOOL. Utilise ce skill dès
  que la tâche implique : créer ou modifier le bulletin annuel, calculer la
  moyenne annuelle de passage, lister les moyennes par période d'évaluation,
  produire le PDF récapitulatif de fin d'année scolaire. Ce skill étend le
  skill principal `yelen-school` — ses règles s'appliquent intégralement ici.
---

# YELEN SCHOOL — Skill : Bulletin Annuel de Notes

> **Prérequis absolu** : lire et respecter intégralement le skill principal
> `yelen-school/SKILL.md` avant d'appliquer le présent skill.
> Toutes ses règles (stack, design, métier) sont en vigueur ici sans exception.

---

## 1. Définitions métier

| Terme | Définition |
|---|---|
| **Période d'évaluation** | Trimestre ou séquence noté(e) sur 20, défini(e) dans `PeriodeEvaluation` |
| **Moyenne de période** | Moyenne pondérée des notes de l'élève pour une période donnée |
| **Moyenne annuelle** | Moyenne arithmétique simple des moyennes de toutes les périodes |
| **Moyenne de passage** | Seuil ≥ 10/20 — *Passe en classe supérieure* si atteint, *Redouble la classe* sinon |
| **Coefficient** | Poids d'une matière dans le calcul de la moyenne de période |

**Règle fondamentale :** toutes les notes et moyennes sont **sur 20**, jamais sur 100 ni sur autre base.

**Ce document est unique :** le bulletin annuel est un document de synthèse de fin d'année scolaire, distinct et indépendant des bulletins trimestriels. Il ne les remplace pas et ne les duplique pas.

---

## 2. Modèles de données impliqués

### 2.1 Modèles existants à réutiliser (ne pas recréer)

```python
# eleves/models.py
class Eleve(BaseModel):
    matricule        # {CODE_ETAB}-AAAA-NN (élève) / {CODE_ETAB}-P-AAAA-NN (personnel) — auto, readonly
    nom, prenom, date_naissance
    classe           # FK → Classe

# notes/models.py
class PeriodeEvaluation(BaseModel):
    nom              # ex. "Trimestre 1", "Séquence 2"
    ordre            # entier — définit l'ordre d'affichage
    annee_scolaire   # FK → AnneeScolaire

class Note(BaseModel):
    eleve            # FK → Eleve
    matiere          # FK → Matiere
    periode          # FK → PeriodeEvaluation
    valeur           # DecimalField(max_digits=4, decimal_places=2) — entre 0 et 20
    coefficient      # PositiveSmallIntegerField — coefficient de la matière
```

### 2.2 Nouveau modèle à créer : `BulletinAnnuel`

```python
# bulletins/models.py
from django.db import models
from core.models import BaseModel

class BulletinAnnuel(BaseModel):
    """
    Snapshot calculé du bulletin annuel d'un élève.
    Ne jamais recalculer à la volée en vue — utiliser ce modèle.
    Document distinct des bulletins trimestriels.
    """
    eleve            = models.ForeignKey("eleves.Eleve",        on_delete=models.PROTECT)
    annee_scolaire   = models.ForeignKey("core.AnneeScolaire",  on_delete=models.PROTECT)
    donnees_json     = models.JSONField()   # voir §3 pour la structure
    moyenne_annuelle = models.DecimalField(max_digits=4, decimal_places=2)
    est_admis        = models.BooleanField(default=False)  # moyenne_annuelle >= 10
    genere_le        = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("eleve", "annee_scolaire")
        ordering = ["eleve__nom", "eleve__prenom"]

    def __str__(self):
        return f"Bulletin annuel {self.eleve} — {self.annee_scolaire}"

    @property
    def decision(self):
        return "Passe en classe supérieure" if self.est_admis else "Redouble la classe"
```

---

## 3. Structure du champ `donnees_json`

Le bulletin annuel ne contient que les **moyennes de période**, pas le détail
matière par matière (celui-ci appartient aux bulletins trimestriels).

```json
{
  "periodes": [
    { "id": 1, "nom": "Trimestre 1", "ordre": 1, "moyenne_periode": 13.25 },
    { "id": 2, "nom": "Trimestre 2", "ordre": 2, "moyenne_periode": 11.68 },
    { "id": 3, "nom": "Trimestre 3", "ordre": 3, "moyenne_periode": 12.96 }
  ],
  "nombre_periodes": 3,
  "somme_moyennes_periodes": 37.89,
  "moyenne_annuelle": 12.63,
  "seuil_passage": 10.00,
  "est_admis": true,
  "decision": "Passe en classe supérieure"
}
```

**Règles de calcul :**

```
moyenne_periode  = Σ(note × coefficient) / Σ(coefficient)
moyenne_annuelle = Σ(moyenne_periode) / nombre_periodes
est_admis        = moyenne_annuelle >= 10.00
decision         = "Passe en classe supérieure" si est_admis, "Redouble la classe" sinon
```

---

## 4. Service de calcul

Toute logique métier réside dans un service dédié — **jamais dans la vue**.

```python
# bulletins/services.py
from decimal import Decimal, ROUND_HALF_UP
from notes.models import Note, PeriodeEvaluation
from .models import BulletinAnnuel


def calculer_bulletin_annuel(eleve, annee_scolaire) -> BulletinAnnuel:
    """
    Calcule (ou recalcule) le bulletin annuel d'un élève pour une année scolaire.
    Crée ou met à jour l'enregistrement BulletinAnnuel correspondant.
    N'affecte pas les bulletins trimestriels existants.
    """
    periodes = PeriodeEvaluation.objects.filter(
        annee_scolaire=annee_scolaire
    ).order_by("ordre")

    donnees_periodes = []
    somme_moyennes = Decimal("0.00")

    for periode in periodes:
        notes_qs = Note.objects.filter(
            eleve=eleve, periode=periode
        ).select_related("matiere")

        if not notes_qs.exists():
            continue

        total_coeff  = 0
        total_points = Decimal("0.00")

        for note in notes_qs:
            total_coeff  += note.coefficient
            total_points += note.valeur * note.coefficient

        moy = (total_points / total_coeff).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) if total_coeff else Decimal("0.00")

        somme_moyennes += moy
        donnees_periodes.append({
            "id":              periode.pk,
            "nom":             periode.nom,
            "ordre":           periode.ordre,
            "moyenne_periode": float(moy),
        })

    n = len(donnees_periodes)
    moy_annuelle = (somme_moyennes / n).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) if n else Decimal("0.00")

    est_admis = moy_annuelle >= Decimal("10.00")

    donnees_json = {
        "periodes":                donnees_periodes,
        "nombre_periodes":         n,
        "somme_moyennes_periodes": float(somme_moyennes),
        "moyenne_annuelle":        float(moy_annuelle),
        "seuil_passage":           10.00,
        "est_admis":               est_admis,
        "decision": "Passe en classe supérieure" if est_admis else "Redouble la classe",
    }

    bulletin, _ = BulletinAnnuel.objects.update_or_create(
        eleve=eleve,
        annee_scolaire=annee_scolaire,
        defaults={
            "donnees_json":    donnees_json,
            "moyenne_annuelle": moy_annuelle,
            "est_admis":       est_admis,
        },
    )
    return bulletin
```

---

## 5. Vue et URL

```python
# bulletins/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404, render
from eleves.models import Eleve
from core.models import AnneeScolaire
from .services import calculer_bulletin_annuel


class BulletinAnnuelView(LoginRequiredMixin, View):
    template_name = "bulletins/bulletin_annuel.html"

    def get(self, request, eleve_pk, annee_pk):
        eleve    = get_object_or_404(Eleve, pk=eleve_pk)
        annee    = get_object_or_404(AnneeScolaire, pk=annee_pk)
        bulletin = calculer_bulletin_annuel(eleve, annee)
        return render(request, self.template_name, {
            "eleve":   eleve,
            "annee":   annee,
            "bulletin": bulletin,
        })
```

```python
# bulletins/urls.py
from django.urls import path
from .views import BulletinAnnuelView, BulletinAnnuelPDFView

urlpatterns = [
    path(
        "eleve/<int:eleve_pk>/annee/<int:annee_pk>/bulletin-annuel/",
        BulletinAnnuelView.as_view(),
        name="bulletin_annuel",
    ),
    path(
        "eleve/<int:eleve_pk>/annee/<int:annee_pk>/bulletin-annuel/pdf/",
        BulletinAnnuelPDFView.as_view(),
        name="bulletin_annuel_pdf",
    ),
]
```

---

## 6. Template HTML (WeasyPrint-compatible)

> Rappel design : fond `#0A1628`, cartes `#111E35`, accent `#00A86B`,
> police Outfit, zéro CSS inline, classes `yelen.css` uniquement.

```html
{# templates/bulletins/bulletin_annuel.html #}
{% extends "base.html" %}
{% load static %}

{% block title %}Bulletin Annuel — {{ eleve.get_full_name }}{% endblock %}

{% block content %}
<div class="page-bulletin">

  {# En-tête établissement #}
  <header class="bulletin-header">
    <img src="{% static 'img/logo_yelen.png' %}" alt="Logo YELEN SCHOOL" class="bulletin-logo">
    <div class="bulletin-header__info">
      <h1 class="titre-ecole">YELEN SCHOOL</h1>
      <p class="sous-titre-bulletin">Bulletin Annuel de Notes — {{ annee.libelle }}</p>
    </div>
  </header>

  {# Identité élève #}
  <section class="carte carte--eleve">
    <div class="carte__ligne">
      <span class="carte__label">Élève</span>
      <span class="carte__valeur">{{ eleve.nom|upper }} {{ eleve.prenom }}</span>
    </div>
    <div class="carte__ligne">
      <span class="carte__label">Matricule</span>
      <span class="carte__valeur matricule">{{ eleve.matricule }}</span>
    </div>
    <div class="carte__ligne">
      <span class="carte__label">Classe</span>
      <span class="carte__valeur">{{ eleve.classe }}</span>
    </div>
    <div class="carte__ligne">
      <span class="carte__label">Année scolaire</span>
      <span class="carte__valeur">{{ annee.libelle }}</span>
    </div>
  </section>

  {# Récapitulatif des moyennes par période #}
  <section class="carte carte--recapitulatif">
    <h2 class="recapitulatif__titre">Moyennes par période</h2>
    <table class="tableau-recapitulatif">
      <thead>
        <tr>
          <th>Période d'évaluation</th>
          <th>Moyenne /20</th>
        </tr>
      </thead>
      <tbody>
        {% for periode in bulletin.donnees_json.periodes %}
        <tr>
          <td>{{ periode.nom }}</td>
          <td class="col-centre {% if periode.moyenne_periode >= 10 %}note--admis{% else %}note--echec{% endif %}">
            {{ periode.moyenne_periode|floatformat:2 }}
          </td>
        </tr>
        {% endfor %}
      </tbody>
      <tfoot>
        <tr class="tfoot-annuel">
          <td><strong>Moyenne annuelle de passage</strong></td>
          <td class="col-centre {% if bulletin.est_admis %}note--admis{% else %}note--echec{% endif %}">
            <strong>{{ bulletin.moyenne_annuelle|floatformat:2 }} /20</strong>
          </td>
        </tr>
      </tfoot>
    </table>

    <div class="decision {% if bulletin.est_admis %}decision--admis{% else %}decision--echec{% endif %}">
      {% if bulletin.est_admis %}
        ✓ PASSE EN CLASSE SUPÉRIEURE
      {% else %}
        ✗ REDOUBLE LA CLASSE
      {% endif %}
    </div>
  </section>

  {# Signature du directeur #}
  <footer class="bulletin-footer">
    <div class="signature-bloc">
      <p class="signature-titre">Le Directeur de l'établissement</p>
      <div class="signature-ligne"></div>
      <p class="signature-nom">{{ directeur.nom }}</p>
    </div>
  </footer>

</div>
{% endblock %}
```

---

## 7. Export PDF (WeasyPrint)

```python
# bulletins/views.py  (ajout de la vue PDF)
from django.http import HttpResponse
from weasyprint import HTML
from django.template.loader import render_to_string
from personnel.models import PersonnelDirection


class BulletinAnnuelPDFView(LoginRequiredMixin, View):
    def get(self, request, eleve_pk, annee_pk):
        eleve     = get_object_or_404(Eleve, pk=eleve_pk)
        annee     = get_object_or_404(AnneeScolaire, pk=annee_pk)
        bulletin  = calculer_bulletin_annuel(eleve, annee)
        directeur = PersonnelDirection.objects.filter(role="directeur").first()

        html_string = render_to_string("bulletins/bulletin_annuel.html", {
            "eleve":     eleve,
            "annee":     annee,
            "bulletin":  bulletin,
            "directeur": directeur,
        })
        pdf_file = HTML(
            string=html_string,
            base_url=request.build_absolute_uri()
        ).write_pdf()

        filename = f"bulletin_annuel_{eleve.matricule}_{annee.libelle}.pdf"
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
```

---

## 8. Classes CSS à ajouter dans `yelen.css`

```css
/* ── Bulletin Annuel ─────────────────────────────────────── */
.page-bulletin            { padding: 2rem; font-family: 'Outfit', sans-serif; }

/* En-tête */
.bulletin-header          { display: flex; align-items: center; gap: 1.5rem; margin-bottom: 2rem; }
.bulletin-logo            { height: 72px; }
.titre-ecole              { font-family: 'Playfair Display', serif; color: #00A86B; font-size: 1.8rem; margin: 0; }
.sous-titre-bulletin      { color: #cdd9f0; font-size: 1rem; margin: 0.25rem 0 0; }

/* Cartes */
.carte                    { background: #111E35; border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }
.carte__ligne             { display: flex; gap: 1rem; padding: 0.3rem 0; }
.carte__label             { color: #7a90b3; min-width: 140px; }
.carte__valeur            { color: #e8f0fe; font-weight: 600; }
.matricule                { font-family: 'DejaVu Sans Mono', monospace; color: #00A86B; font-size: .9rem; }

/* Titre de section */
.recapitulatif__titre     { color: #00A86B; font-size: 1.1rem; margin: 0 0 1rem; }

/* Tableau */
.tableau-recapitulatif    { width: 100%; border-collapse: collapse; }
.tableau-recapitulatif th { background: #0d1a2d; color: #7a90b3; font-weight: 600;
                            padding: .5rem .75rem; text-align: left; }
.tableau-recapitulatif td { padding: .5rem .75rem; border-bottom: 1px solid #1e2f4a; color: #e8f0fe; }
.col-centre               { text-align: center; }

/* Notes colorées */
.note--admis              { color: #00A86B; font-weight: 700; }
.note--echec              { color: #e74c3c; font-weight: 700; }

/* Pied de tableau */
.tfoot-annuel td          { background: #0d1a2d; color: #cdd9f0; font-weight: 600; padding: .6rem .75rem; }

/* Décision finale */
.decision                 { margin-top: 1.25rem; padding: .75rem 1.25rem; border-radius: 6px;
                            font-weight: 700; font-size: 1.05rem; text-align: center; }
.decision--admis          { background: rgba(0,168,107,.15); color: #00A86B; border: 1px solid #00A86B; }
.decision--echec          { background: rgba(231,76,60,.12); color: #e74c3c; border: 1px solid #e74c3c; }

/* Signature directeur */
.bulletin-footer          { margin-top: 3rem; display: flex; justify-content: center; }
.signature-bloc           { text-align: center; min-width: 220px; }
.signature-titre          { color: #7a90b3; font-size: .85rem; margin-bottom: 2.5rem; }
.signature-ligne          { border-top: 1px solid #2a3f5f; width: 80%; margin: 0 auto; }
.signature-nom            { color: #cdd9f0; font-size: .9rem; margin-top: .4rem; }
```

---

## 9. Tests requis (pytest + model_bakery)

```python
# tests/bulletins/test_bulletin_annuel.py
import pytest
from decimal import Decimal
from model_bakery import baker
from bulletins.services import calculer_bulletin_annuel


@pytest.mark.django_db
class TestBulletinAnnuel:

    def setup_method(self):
        self.annee    = baker.make("core.AnneeScolaire")
        self.eleve    = baker.make("eleves.Eleve")
        self.matiere  = baker.make("notes.Matiere", nom="Mathématiques")
        self.periode1 = baker.make("notes.PeriodeEvaluation", annee_scolaire=self.annee, ordre=1)
        self.periode2 = baker.make("notes.PeriodeEvaluation", annee_scolaire=self.annee, ordre=2)
        self.periode3 = baker.make("notes.PeriodeEvaluation", annee_scolaire=self.annee, ordre=3)

    def _note(self, periode, valeur, coeff=2):
        return baker.make(
            "notes.Note",
            eleve=self.eleve, periode=periode, matiere=self.matiere,
            valeur=Decimal(str(valeur)), coefficient=coeff,
        )

    def test_moyenne_periode_ponderee(self):
        m2 = baker.make("notes.Matiere", nom="Français")
        baker.make("notes.Note", eleve=self.eleve, periode=self.periode1,
                   matiere=self.matiere, valeur=Decimal("15"), coefficient=3)
        baker.make("notes.Note", eleve=self.eleve, periode=self.periode1,
                   matiere=m2, valeur=Decimal("9"), coefficient=1)
        # moy = (15×3 + 9×1) / 4 = 13.50
        b = calculer_bulletin_annuel(self.eleve, self.annee)
        assert b.donnees_json["periodes"][0]["moyenne_periode"] == pytest.approx(13.50, 0.01)

    def test_moyenne_annuelle_est_moyenne_des_periodes(self):
        self._note(self.periode1, 16)
        self._note(self.periode2, 12)
        self._note(self.periode3, 14)
        b = calculer_bulletin_annuel(self.eleve, self.annee)
        # (16+12+14)/3 = 14.00
        assert b.moyenne_annuelle == Decimal("14.00")

    def test_passe_en_classe_superieure_si_moyenne_egale_a_10(self):
        self._note(self.periode1, 10)
        b = calculer_bulletin_annuel(self.eleve, self.annee)
        assert b.est_admis is True
        assert b.decision == "Passe en classe supérieure"

    def test_redouble_si_moyenne_inferieure_a_10(self):
        self._note(self.periode1, 9)
        b = calculer_bulletin_annuel(self.eleve, self.annee)
        assert b.est_admis is False
        assert b.decision == "Redouble la classe"

    def test_idempotence_recalcul(self):
        self._note(self.periode1, 14)
        b1 = calculer_bulletin_annuel(self.eleve, self.annee)
        b2 = calculer_bulletin_annuel(self.eleve, self.annee)
        assert b1.pk == b2.pk  # update_or_create, jamais de doublon

    def test_json_ne_contient_pas_de_detail_matiere(self):
        self._note(self.periode1, 12)
        b = calculer_bulletin_annuel(self.eleve, self.annee)
        for periode in b.donnees_json["periodes"]:
            assert "matieres" not in periode  # le détail appartient aux bulletins trimestriels
```

---

## 10. Checklist spécifique à ce skill

Avant de soumettre toute implémentation liée au bulletin annuel :

- [ ] Modèle `BulletinAnnuel` hérite de `BaseModel` avec `unique_together = ("eleve", "annee_scolaire")`
- [ ] Calcul dans `bulletins/services.py` exclusivement — aucune logique dans la vue
- [ ] Moyennes **sur 20**, arrondies à 2 décimales (`ROUND_HALF_UP`)
- [ ] `moyenne_annuelle = Σ(moyennes_périodes) / nombre_périodes` — pas une repasse sur les notes brutes
- [ ] `est_admis = True` si et seulement si `moyenne_annuelle >= 10.00`
- [ ] Décision : `"Passe en classe supérieure"` ou `"Redouble la classe"` — pas d'autre formulation
- [ ] Le `donnees_json` ne contient **pas** le détail matière par matière (celui-ci appartient aux bulletins trimestriels)
- [ ] Une seule signature : **le Directeur de l'établissement**
- [ ] PDF généré via **WeasyPrint** uniquement (jamais reportlab, fpdf ou autre)
- [ ] Zéro CSS inline — toutes les classes dans `yelen.css`
- [ ] Fond cartes `#111E35`, accent `#00A86B`, police `Outfit`, matricule `DejaVu Sans Mono`
- [ ] Tests pytest couvrant : pondération période, moyenne annuelle, passage, redoublement, idempotence, absence de détail matière dans le JSON
- [ ] `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` mis à jour — Section **Bulletin Annuel**
- [ ] Réponse terminée par `📘 Guide mis à jour — Section Bulletin Annuel`
