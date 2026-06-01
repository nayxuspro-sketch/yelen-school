# Modèle Bulletin de Notes — N&B

## Structure HTML complète

Ce modèle est adapté aux bulletins scolaires burkinabè (trimestre / semestre).  
Utilise uniquement du noir, blanc et gris. Lisible en impression économie d'encre.

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Bulletin de Notes</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  @page { margin: 1.5cm; size: A4; }
  @media print {
    .no-print { display: none !important; }
    * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }

  body {
    font-family: Arial, sans-serif;
    font-size: 12px;
    color: #000;
    background: #fff;
    max-width: 210mm;
    margin: 0 auto;
    padding: 10px;
  }

  /* En-tête établissement */
  .header {
    border: 2px solid #000;
    padding: 8px 12px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header .etablissement { font-size: 14px; font-weight: bold; }
  .header .sous-titre { font-size: 11px; }
  .header .annee { font-size: 13px; font-weight: bold; text-align: right; }

  /* Informations élève */
  .info-eleve {
    border: 1px solid #000;
    padding: 6px 10px;
    margin-bottom: 8px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    font-size: 12px;
  }
  .info-eleve .label { font-weight: bold; }

  /* Titre bulletin */
  .titre-bulletin {
    text-align: center;
    font-size: 15px;
    font-weight: bold;
    border: 2px solid #000;
    padding: 5px;
    margin-bottom: 8px;
    background: #e0e0e0;
  }

  /* Tableau de notes */
  table.notes {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 8px;
    font-size: 11px;
  }
  table.notes th {
    background: #cccccc;
    border: 1.5px solid #000;
    padding: 5px 4px;
    text-align: center;
    font-weight: bold;
    font-size: 11px;
  }
  table.notes td {
    border: 1px solid #555;
    padding: 4px 5px;
    text-align: center;
  }
  table.notes td.matiere {
    text-align: left;
    font-weight: bold;
  }
  table.notes tr:nth-child(even) td { background: #f5f5f5; }
  table.notes .groupe th {
    background: #888;
    color: #fff;
    font-size: 11px;
  }
  table.notes .total td {
    background: #ddd;
    font-weight: bold;
    border-top: 2px solid #000;
  }
  table.notes .moyenne-gen td {
    background: #bbb;
    font-weight: bold;
    font-size: 13px;
    border-top: 2px solid #000;
  }

  /* Appréciation */
  .appreciation {
    border: 1px solid #000;
    padding: 6px 10px;
    margin-bottom: 8px;
    min-height: 40px;
  }
  .appreciation .label { font-weight: bold; font-size: 11px; }

  /* Absences */
  .absences {
    border: 1px solid #000;
    padding: 5px 10px;
    margin-bottom: 8px;
    font-size: 11px;
    display: flex;
    gap: 20px;
  }

  /* Signatures */
  .signatures {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
    margin-top: 10px;
    font-size: 11px;
  }
  .signatures .bloc {
    border: 1px solid #000;
    padding: 5px 8px;
    min-height: 60px;
    text-align: center;
  }
  .signatures .bloc .titre { font-weight: bold; margin-bottom: 30px; }

  /* Bouton impression */
  .btn-print {
    display: block;
    margin: 10px auto;
    padding: 8px 20px;
    font-size: 14px;
    cursor: pointer;
    background: #f0f0f0;
    border: 1px solid #000;
  }
</style>
</head>
<body>

<button class="no-print btn-print" onclick="window.print()">🖨️ Imprimer ce bulletin</button>

<!-- EN-TÊTE -->
<div class="header">
  <div>
    <div class="etablissement">LYCÉE [NOM DE L'ÉTABLISSEMENT]</div>
    <div class="sous-titre">BP [Adresse] — [Ville], Burkina Faso</div>
    <div class="sous-titre">Tél : [Numéro]</div>
  </div>
  <div class="annee">
    Année scolaire : 2024–2025<br>
    <span style="font-size:11px">Trimestre / Semestre : <strong>1er</strong></span>
  </div>
</div>

<!-- TITRE -->
<div class="titre-bulletin">BULLETIN DE NOTES — 1er TRIMESTRE</div>

<!-- INFOS ÉLÈVE -->
<div class="info-eleve">
  <div><span class="label">Nom & Prénoms :</span> KABORÉ Aminata</div>
  <div><span class="label">Classe :</span> 3ème A</div>
  <div><span class="label">Date de naissance :</span> 12/03/2010</div>
  <div><span class="label">Effectif de la classe :</span> 45 élèves</div>
</div>

<!-- TABLEAU DE NOTES -->
<table class="notes">
  <thead>
    <tr>
      <th style="width:30%">Matière</th>
      <th>Coeff.</th>
      <th>Note /20</th>
      <th>Moy. classe</th>
      <th>Rang</th>
      <th>Appréciation du prof.</th>
    </tr>
  </thead>
  <tbody>
    <!-- Groupe -->
    <tr class="groupe"><th colspan="6">LETTRES ET SCIENCES HUMAINES</th></tr>
    <tr>
      <td class="matiere">Français</td>
      <td>3</td><td>14,00</td><td>11,50</td><td>5e</td><td>Bien</td>
    </tr>
    <tr>
      <td class="matiere">Histoire-Géographie</td>
      <td>2</td><td>12,50</td><td>10,00</td><td>8e</td><td>Assez bien</td>
    </tr>

    <tr class="groupe"><th colspan="6">SCIENCES ET MATHÉMATIQUES</th></tr>
    <tr>
      <td class="matiere">Mathématiques</td>
      <td>4</td><td>16,00</td><td>12,00</td><td>2e</td><td>Très bien</td>
    </tr>
    <tr>
      <td class="matiere">Sciences de la Vie et de la Terre</td>
      <td>2</td><td>13,00</td><td>11,00</td><td>6e</td><td>Bien</td>
    </tr>
    <tr>
      <td class="matiere">Physique-Chimie</td>
      <td>3</td><td>15,00</td><td>10,50</td><td>3e</td><td>Très bien</td>
    </tr>

    <tr class="groupe"><th colspan="6">LANGUES VIVANTES</th></tr>
    <tr>
      <td class="matiere">Anglais</td>
      <td>2</td><td>11,00</td><td>10,00</td><td>15e</td><td>Passable</td>
    </tr>

    <!-- Ligne moyenne générale -->
    <tr class="total">
      <td class="matiere" colspan="2">TOTAL POINTS</td>
      <td>228,5</td><td>—</td><td>—</td><td>—</td>
    </tr>
    <tr class="moyenne-gen">
      <td class="matiere" colspan="2">MOYENNE GÉNÉRALE</td>
      <td><strong>14,28 / 20</strong></td>
      <td>10,83</td>
      <td><strong>4e / 45</strong></td>
      <td>—</td>
    </tr>
  </tbody>
</table>

<!-- ABSENCES -->
<div class="absences">
  <div><span class="label">Absences justifiées :</span> 02 h</div>
  <div><span class="label">Absences non justifiées :</span> 00 h</div>
  <div><span class="label">Retards :</span> 01</div>
</div>

<!-- APPRÉCIATION DU CONSEIL DE CLASSE -->
<div class="appreciation">
  <div class="label">Appréciation du Conseil de classe :</div>
  <div style="margin-top:6px">Élève sérieuse et appliquée. Bons résultats dans l'ensemble. Peut viser l'excellence. Continuez ainsi !</div>
</div>

<!-- SIGNATURES -->
<div class="signatures">
  <div class="bloc">
    <div class="titre">Le Directeur / La Directrice</div>
    <div>Signature & cachet</div>
  </div>
  <div class="bloc">
    <div class="titre">Le Professeur Principal</div>
    <div>Signature</div>
  </div>
  <div class="bloc">
    <div class="titre">Parent / Tuteur</div>
    <div>Lu et approuvé — Signature</div>
  </div>
</div>

</body>
</html>
```

## Notes d'adaptation

- Remplacer les données fictives par les vraies données (nom élève, notes, classe…)
- Ajouter ou supprimer des groupes de matières selon le niveau (primaire, collège, lycée)
- Pour plusieurs élèves : dupliquer le `<body>` avec `<div style="page-break-after: always">` entre chaque bulletin
- Le gris `#888` sur les en-têtes de groupe imprime en gris foncé lisible même en mode économie d'encre
