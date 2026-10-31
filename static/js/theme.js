/* YELEN SCHOOL — apparence « selon l'appareil » (Mon profil → Apparence = auto).
   Chargé dans <head> avant le rendu : remplace data-theme="auto" par le thème de l'appareil, et suit ses changements.
   Les thèmes « sombre » et « clair » sont rendus par le serveur (attribut data-theme de <html>), sans script. */
(function () {
  'use strict';
  var racine = document.documentElement;
  if (racine.getAttribute('data-theme') !== 'auto' || !window.matchMedia) return;
  var clair = window.matchMedia('(prefers-color-scheme: light)');
  var appliquer = function () { racine.setAttribute('data-theme', clair.matches ? 'clair' : 'sombre'); };
  appliquer();
  if (clair.addEventListener) clair.addEventListener('change', appliquer);
})();
