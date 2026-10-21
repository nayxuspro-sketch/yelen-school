/* Affiche l'heure du serveur en continu : décalage calculé une fois au chargement (data-ms),
 * puis horloge locale + décalage, formatée dans le fuseau du serveur (data-fuseau). */
(function () {
  'use strict';
  var script = document.currentScript;
  var cible = document.getElementById('heure-serveur');
  var decalage = parseInt(script.getAttribute('data-ms'), 10) - Date.now();
  var format = new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    timeZone: script.getAttribute('data-fuseau') || undefined
  });
  if (!cible || isNaN(decalage)) { return; }
  setInterval(function () {
    cible.textContent = format.format(new Date(Date.now() + decalage));
  }, 1000);
})();
