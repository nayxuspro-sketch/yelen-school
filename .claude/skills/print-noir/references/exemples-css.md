# Bibliothèque CSS — Composants N&B prêts à l'emploi

Composants réutilisables pour tout document scolaire à imprimer en noir et blanc.

---

## 1. En-tête d'établissement

```html
<style>
.entete {
  border: 2px solid #000;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.entete .nom { font-size: 15px; font-weight: bold; }
.entete .infos { font-size: 11px; line-height: 1.4; }
.entete .annee { text-align: right; font-weight: bold; font-size: 13px; }
</style>

<div class="entete">
  <div>
    <div class="nom">NOM DE L'ÉTABLISSEMENT</div>
    <div class="infos">Adresse — Ville, Burkina Faso<br>Tél : XX XX XX XX</div>
  </div>
  <div class="annee">Année scolaire 2024–2025</div>
</div>
```

---

## 2. Tableau liste d'élèves (avec alternance)

```html
<style>
table.liste {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
table.liste th {
  background: #cccccc; border: 1.5px solid #000;
  padding: 5px 6px; text-align: left;
}
table.liste td {
  border: 1px solid #777; padding: 4px 6px;
}
table.liste tr:nth-child(even) td { background: #f0f0f0; }
</style>

<table class="liste">
  <thead>
    <tr><th>N°</th><th>Nom & Prénoms</th><th>Date naissance</th><th>Sexe</th><th>Statut</th></tr>
  </thead>
  <tbody>
    <tr><td>01</td><td>KABORÉ Aminata</td><td>12/03/2010</td><td>F</td><td>Régulier</td></tr>
    <tr><td>02</td><td>OUÉDRAOGO Issouf</td><td>05/07/2009</td><td>M</td><td>Régulier</td></tr>
  </tbody>
</table>
```

---

## 3. Fiche convocation / courrier

```html
<style>
.courrier { max-width: 170mm; margin: 0 auto; font-size: 13px; line-height: 1.6; }
.courrier .objet { font-weight: bold; text-decoration: underline; margin: 12px 0; }
.courrier .signature { margin-top: 40px; text-align: right; }
.courrier .cadre-reponse {
  border: 1px solid #000; padding: 8px 12px;
  margin-top: 15px; min-height: 60px;
}
</style>

<div class="courrier">
  <p style="text-align:right">Koudougou, le ___________</p>
  <p><strong>À l'attention de :</strong> M./Mme _________________</p>
  <p><strong>Élève :</strong> ___________________ — Classe : _______</p>
  <div class="objet">OBJET : Convocation</div>
  <p>Monsieur / Madame,</p>
  <p>Vous êtes prié(e) de bien vouloir vous présenter au bureau de la Direction le ___________
  à _________ heures pour [motif].</p>
  <p>Veuillez agréer, Monsieur/Madame, l'expression de nos salutations distinguées.</p>
  <div class="signature">
    Le Directeur<br><br><br>
    [Nom et signature]
  </div>
  <div class="cadre-reponse">
    <strong>Accusé de réception (à retourner signé) :</strong><br>
    Je soussigné(e) _____________ , parent/tuteur de l'élève _____________,
    ai bien reçu la présente convocation.<br><br>
    Date : _________ &nbsp;&nbsp; Signature : _________________
  </div>
</div>
```

---

## 4. Emploi du temps (grille 5 jours)

```html
<style>
table.edt {
  width: 100%; border-collapse: collapse; font-size: 10px; table-layout: fixed;
}
table.edt th {
  background: #aaaaaa; color: #000; border: 1.5px solid #000;
  padding: 4px; text-align: center; font-weight: bold;
}
table.edt td {
  border: 1px solid #777; padding: 4px 3px;
  text-align: center; height: 32px; vertical-align: middle;
}
table.edt .heure { background: #e0e0e0; font-weight: bold; }
table.edt .pause { background: #cccccc; font-style: italic; }
table.edt .vide { background: #f8f8f8; }
</style>

<table class="edt">
  <thead>
    <tr>
      <th style="width:12%">Heure</th>
      <th>Lundi</th><th>Mardi</th><th>Mercredi</th><th>Jeudi</th><th>Vendredi</th>
    </tr>
  </thead>
  <tbody>
    <tr><td class="heure">07h30–08h30</td><td>Maths</td><td>Français</td><td>SVT</td><td>Anglais</td><td>Hist-Géo</td></tr>
    <tr><td class="heure">08h30–09h30</td><td>Physique</td><td>Maths</td><td>Français</td><td>Maths</td><td>SVT</td></tr>
    <tr><td class="pause" colspan="6">RÉCRÉATION — 09h30 à 09h45</td></tr>
    <tr><td class="heure">09h45–10h45</td><td>Hist-Géo</td><td>Physique</td><td class="vide">—</td><td>Français</td><td>Maths</td></tr>
    <tr><td class="heure">10h45–11h45</td><td>Anglais</td><td>SVT</td><td class="vide">—</td><td>Physique</td><td>Anglais</td></tr>
    <tr><td class="pause" colspan="6">PAUSE DÉJEUNER — 11h45 à 14h00</td></tr>
    <tr><td class="heure">14h00–15h00</td><td>SVT</td><td>Hist-Géo</td><td class="vide">—</td><td>Maths</td><td class="vide">—</td></tr>
    <tr><td class="heure">15h00–16h00</td><td>Français</td><td>Anglais</td><td class="vide">—</td><td>Physique</td><td class="vide">—</td></tr>
  </tbody>
</table>
```

---

## 5. Reçu de paiement / scolarité

```html
<style>
.recu {
  border: 2px solid #000; padding: 12px 16px;
  max-width: 140mm; font-size: 13px;
}
.recu .titre { text-align: center; font-size: 16px; font-weight: bold; margin-bottom: 8px; }
.recu .ligne { border-bottom: 1px dotted #000; padding: 4px 0; display: flex; justify-content: space-between; }
.recu .montant { font-size: 15px; font-weight: bold; }
.recu .sig { margin-top: 20px; display: flex; justify-content: space-between; }
</style>

<div class="recu">
  <div class="titre">REÇU DE PAIEMENT N° ______</div>
  <div class="ligne"><span>Élève :</span><span>____________________________</span></div>
  <div class="ligne"><span>Classe :</span><span>____________</span></div>
  <div class="ligne"><span>Motif :</span><span>Frais de scolarité — Trimestre ___</span></div>
  <div class="ligne"><span>Date de paiement :</span><span>_______________</span></div>
  <div class="ligne montant"><span>Montant reçu :</span><span>___________ FCFA</span></div>
  <div class="sig">
    <div>Le payeur<br><br><br>Signature</div>
    <div style="text-align:right">Le caissier<br><br><br>Signature & cachet</div>
  </div>
</div>
```

---

## 6. Fiche d'exercice / contrôle

```html
<style>
.controle header {
  display: flex; justify-content: space-between;
  border-bottom: 2px solid #000; padding-bottom: 6px; margin-bottom: 10px;
}
.controle .consigne { font-weight: bold; margin: 8px 0 4px; }
.controle .zone-reponse {
  border: 1px solid #000; min-height: 50px;
  padding: 5px; margin-bottom: 8px;
}
.controle .note-zone {
  float: right; border: 2px solid #000;
  padding: 4px 12px; text-align: center; font-weight: bold;
}
</style>

<div class="controle">
  <header>
    <div><strong>Nom :</strong> ______________________<br><strong>Classe :</strong> _______</div>
    <div><strong>Date :</strong> ___________<br><strong>Durée :</strong> 1h00</div>
    <div class="note-zone">Note<br><br>_____ / 20</div>
  </header>
  <h3 style="text-align:center; text-decoration:underline">CONTRÔLE DE MATHÉMATIQUES</h3>
  <p class="consigne">Exercice 1 — (8 points)</p>
  <p>Résoudre l'équation suivante : 3x + 7 = 22</p>
  <div class="zone-reponse"></div>
</div>
```

---

## Palette de gris recommandée (résumé rapide)

| Variable | Valeur | Usage |
|---|---|---|
| Fond page | `#FFFFFF` | Corps du document |
| Alternance tableau | `#F0F0F0` | Lignes paires |
| En-tête colonne | `#CCCCCC` | Thead de tableaux |
| En-tête groupe | `#AAAAAA` | Sous-sections sombres |
| Encadrés importants | `#E0E0E0` | Titres, blocs info |
| Texte principal | `#000000` | Tout le texte |
| Bordures légères | `#555555` | Lignes de tableau |
| Bordures fortes | `#000000` | Cadres, délimitations |
