/* Tableaux de liste sur téléphone — 5.47.0
   Sous 1040 px de large, chaque ligne d'un tableau de liste devient une carte étiquetée : les libellés de
   colonnes sont repris du <thead> (aucun gabarit n'est modifié). Les matrices et plannings portent
   data-cartes="non" et gardent leur défilement horizontal. Sans JavaScript, le tableau reste défilant :
   aucune régression possible. */
(function () {
  'use strict';

  var LIBELLE_TITRE = /^(él[èe]ve|nom|libellé|designation|désignation|intitulé|fournisseur|article|utilisateur|compte|enseignant|famille)\b/i;
  var LIBELLE_ACTIONS = /^(actions?|opérations?)\b/i;
  var COLONNES_MAX = 10;   // au-delà, c'est une matrice : elle reste défilante
  // Une cellule de titre contient une ligne de texte libre (nom), pas une étiquette courte, une date,
  // un montant ni une commande : c'est ce contenu qui décide, pas le seul libellé de colonne.
  var AFFICHAGE_COURT = /^(\d|[+\-]?\d[\d\s.,]*\s*(fcfa|f\s*cfa|f|%|ans?|jours?)?$|oui$|non$|actif$|inactif$|nouveau$|ancien$|aucun$)/i;
  var CODE = /^[A-Z0-9][A-Z0-9\-\/_.]{2,}$/;   // matricule, numéro de reçu, code

  function libelles(table) {
    var thead = table.tHead;
    if (!thead || !thead.rows.length) { return null; }
    var ligne = thead.rows[thead.rows.length - 1];
    var map = {}, index = 0;
    Array.prototype.forEach.call(ligne.cells, function (cellule) {
      map[index] = (cellule.textContent || '').trim();
      index += (cellule.colSpan || 1);
    });
    return { map: map, colonnes: index };
  }

  function estActionnable(cellule) {
    // Cellule d'actions : uniquement des boutons, des liens-boutons ou des cases à cocher.
    var contenu = Array.prototype.filter.call(cellule.childNodes, function (noeud) {
      if (noeud.nodeType === 3) { return noeud.textContent.trim() !== ''; }
      if (noeud.nodeType !== 1) { return false; }
      return !noeud.matches('a, button, form, input, select, svg, i, span.badge, span.btn-group, div.btn-group');
    });
    return contenu.length === 0 && cellule.querySelector('a, button, input[type="submit"], input[type="button"]') !== null;
  }

  function estTitre(cellule) {
    var texte = (cellule.textContent || '').trim().replace(/\s+/g, ' ');
    if (texte.length < 3 || texte.length > 60) { return false; }
    if (AFFICHAGE_COURT.test(texte)) { return false; }
    // Un code (matricule, n° de reçu) s'écrit d'un seul bloc, sans espace : « DEM026-0007 ».
    // « DIALLO BALKISSA » ou « ILBOUDO Adam » sont des noms, donc des titres.
    if (texte.indexOf(' ') === -1 && CODE.test(texte)) { return false; }
    return true;
  }

  function etiqueter(table) {
    if (table.getAttribute('data-cartes') === 'non') { return; }
    if (table.classList.contains('table-stats') || table.classList.contains('edt-table')) { return; }
    var entetes = libelles(table);
    if (!entetes || entetes.colonnes < 3 || entetes.colonnes > COLONNES_MAX) { return; }

    // Colonne de titre : déterminée une fois, puis appliquée à la même colonne de chaque ligne.
    var colonneTitre = -1;
    var lignes = [];
    Array.prototype.forEach.call(table.tBodies, function (corps) {
      Array.prototype.forEach.call(corps.rows, function (ligne) {
        var cellules = Array.prototype.slice.call(ligne.cells);
        if (cellules.length === 1 && (cellules[0].colSpan || 1) > 1) {
          ligne.setAttribute('data-pleine-largeur', '');
          return;
        }
        lignes.push({ ligne: ligne, cellules: cellules });
      });
    });

    lignes.forEach(function (item) {
      item.cellules.forEach(function (cellule) {
        cellule.setAttribute('data-label', entetes.map[cellule.cellIndex] || '');
      });
    });

    var candidate = lignes.filter(function (item) {
      return item.cellules.some(function (c) { return estTitre(c); });
    })[0];
    if (candidate) {
      var titres = candidate.cellules.filter(function (c) {
        return LIBELLE_TITRE.test(c.getAttribute('data-label')) && estTitre(c);
      });
      if (!titres.length) {
        titres = candidate.cellules.filter(function (c) {
          return !LIBELLE_ACTIONS.test(c.getAttribute('data-label')) && estTitre(c);
        });
      }
      if (titres.length) { colonneTitre = titres[0].cellIndex; }
    }

    lignes.forEach(function (item) {
      item.cellules.forEach(function (cellule) {
        if (!cellule.getAttribute('data-label')) { return; }
        if (cellule.cellIndex === colonneTitre) { cellule.setAttribute('data-titre', ''); return; }
        if (LIBELLE_ACTIONS.test(cellule.getAttribute('data-label')) || estActionnable(cellule)) {
          cellule.setAttribute('data-actions', '');
        }
      });
    });

    table.setAttribute('data-cartes', 'oui');
    var conteneur = table.closest('.table-scroll');
    if (conteneur) { conteneur.classList.add('table-cartes'); }
  }

  function parcourir(racine) {
    var tables = (racine || document).querySelectorAll('table.data-table, table.table');
    Array.prototype.forEach.call(tables, etiqueter);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { parcourir(document); });
  } else {
    parcourir(document);
  }
  // Contenus chargés en place (htmx, listes filtrées, pagination) : les nouveaux tableaux sont traités aussi.
  document.body && document.body.addEventListener('htmx:afterSwap', function (evenement) {
    parcourir(evenement.target || document);
  });
})();
