---
name: print-noir
description: >
  Optimise tout document destiné à l'impression en noir et blanc (N&B) dans un contexte scolaire ou administratif sans imprimante couleur.
  UTILISE CE SKILL dès que l'utilisateur mentionne : impression, imprimer, imprimante, bulletin, fiche, liste, tableau, document à distribuer, PDF à imprimer, document pour les élèves ou les parents — même sans mentionner explicitement le noir et blanc.
  Ce skill couvre : la génération de documents HTML/PDF optimisés N&B, la conversion de documents existants (HTML, DOCX, tableaux), les conseils de mise en page, le choix des contrastes, et les règles typographiques pour une lisibilité maximale à l'impression N&B.
---

# Skill : Optimisation Impression Noir & Blanc

## Contexte d'utilisation

L'établissement ne dispose **pas d'imprimante couleur**. Tout document produit doit être parfaitement lisible en impression N&B, économiser l'encre, et rester professionnel.

---

## Règles fondamentales N&B

### 1. Couleurs → Remplacer systématiquement

| Usage couleur courant | Remplacement N&B |
|---|---|
| Fond coloré (en-tête, cellule) | Fond gris clair `#f0f0f0` ou `#e0e0e0` |
| Texte coloré (rouge, bleu…) | Texte **gras** ou souligné |
| Bordures colorées | Bordures noires `1px solid #000` ou `2px` |
| Icônes colorées | Icônes en contour noir ou supprimées |
| Graphiques multicolores | Hachures, textures, niveaux de gris distincts |
| Surlignage jaune | **Gras** ou encadré |

### 2. Contrastes — Règle des 3 niveaux

Pour distinguer visuellement les zones sans couleur, utiliser **3 niveaux de gris maximum** :

```
Blanc pur    #FFFFFF  →  zones de contenu principal
Gris clair   #EEEEEE  →  alternance de lignes, sous-titres
Gris moyen   #CCCCCC  →  en-têtes de colonnes, cadres importants
Noir/foncé   #000000  →  texte, bordures, titres
```

> ⚠️ Éviter les gris > `#BBBBBB` comme fond avec du texte noir : contraste insuffisant à l'impression.

### 3. Typographie

- Police **sans-serif** recommandée : Arial, Calibri, Helvetica (meilleure lisibilité imprimée)
- Taille minimale corps de texte : **11pt** (HTML : 11px équivaut à ~8pt, donc utiliser au moins `13px` / `0.85rem`)
- Taille minimale pour tableaux denses : **10pt**
- Titres : **gras + taille 14pt+**, jamais uniquement en couleur
- Éviter l'italique seul pour signaler quelque chose d'important (peu visible à l'impression)

### 4. Tableaux

```css
/* Tableau N&B optimal */
table { border-collapse: collapse; width: 100%; }
th {
  background: #cccccc;
  font-weight: bold;
  border: 1.5px solid #000;
  padding: 6px 8px;
}
td {
  border: 1px solid #555;
  padding: 5px 8px;
}
tr:nth-child(even) td { background: #f0f0f0; } /* alternance lisible */
```

### 5. Économie d'encre

- Réduire les fonds sombres (gris foncé, noir) aux **en-têtes seulement**
- Préférer les **bordures fines** aux fonds pleins pour délimiter les zones
- Supprimer les logos en couleur ou les remplacer par une version N&B
- Éviter les images de fond (watermarks, textures décoratives)
- Utiliser des **marges raisonnables** : 1,5 cm minimum (évite les coupures à l'impression)

---

## Workflow de production d'un document

### Étape 1 — Identifier le type de document

| Type | Approche |
|---|---|
| Bulletin de notes | Voir `references/bulletin.md` |
| Liste d'élèves / fiche classe | Tableau simple, alternance gris |
| Convocation / courrier | Texte structuré, cadre d'en-tête sobre |
| Emploi du temps | Grille CSS, hachures pour différencier |
| Fiche d'exercice / contrôle | Zones de réponse encadrées, numérotation claire |
| Reçu / attestation de paiement | Bloc signataire, encadré sobre |

### Étape 2 — Générer le HTML optimisé N&B

Toujours inclure ce bloc CSS de base dans `<style>` :

```css
@media print {
  body { font-family: Arial, sans-serif; color: #000; background: #fff; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .no-print { display: none; }
  @page { margin: 1.5cm; }
}

body {
  font-family: Arial, sans-serif;
  font-size: 13px;
  color: #000;
  background: #fff;
  max-width: 210mm; /* format A4 */
  margin: 0 auto;
  padding: 15px;
}
```

### Étape 3 — Vérifications avant livraison

Passer mentalement cette checklist avant de rendre le document :

- [ ] Aucune couleur ne porte seule une information (toujours doublon : gras, forme, texte)
- [ ] Tous les fonds colorés convertis en gris ≤ `#cccccc`
- [ ] Contrastes texte/fond suffisants (ratio ≥ 4:1)
- [ ] Taille de police ≥ 11pt partout
- [ ] Bordures de tableau visibles en N&B
- [ ] Marges ≥ 1,5 cm
- [ ] Pas d'élément décoratif qui gaspille l'encre
- [ ] Page ne dépasse pas le format A4 en largeur

---

## Produire le fichier final

### Format recommandé : HTML imprimable

Générer un fichier `.html` autonome (CSS inline ou dans `<style>`). L'utilisateur l'ouvre dans un navigateur et fait `Ctrl+P` → choisit "Noir et blanc" si disponible.

Toujours ajouter un bouton d'impression masqué à l'impression :

```html
<button class="no-print" onclick="window.print()" 
  style="margin:10px;padding:8px 16px;font-size:14px;cursor:pointer;">
  🖨️ Imprimer
</button>
```

### Format alternatif : DOCX ou PDF

Si l'utilisateur demande un fichier Word ou PDF, consulter d'abord :
- `/mnt/skills/public/docx/SKILL.md` pour DOCX
- `/mnt/skills/public/pdf/SKILL.md` pour PDF

Appliquer les mêmes règles N&B dans le code de génération.

---

## Références complémentaires

- `references/bulletin.md` — Modèle de bulletin de notes N&B pour établissement burkinabè
- `references/exemples-css.md` — Bibliothèque de composants CSS N&B prêts à l'emploi

Lire ces fichiers si la demande concerne spécifiquement ces cas.
