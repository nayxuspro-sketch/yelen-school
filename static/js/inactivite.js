/* Caisse : déconnexion automatique après inactivité de l'utilisateur.
 * Durée lue sur data-secondes (= expiration de session côté serveur). Un bandeau
 * prévient 60 s avant ; toute action (souris, clavier, toucher) remet le compteur à zéro.
 * Les requêtes HTMX périodiques ne comptent pas comme une activité. */
(function () {
  'use strict';
  var script = document.currentScript;
  var total = parseInt(script.getAttribute('data-secondes'), 10) || 900;
  var logoutUrl = script.getAttribute('data-logout');
  var PREAVIS = 60;
  var derniereActivite = Date.now();
  var bandeau = null;

  function activite() {
    derniereActivite = Date.now();
    if (bandeau) { bandeau.remove(); bandeau = null; }
  }
  ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'wheel'].forEach(function (evt) {
    document.addEventListener(evt, activite, { passive: true });
  });

  function deconnecter() {
    var form = document.querySelector('form[action="' + logoutUrl + '"]');
    if (form) { form.submit(); } else { window.location.assign(logoutUrl); }
  }

  function afficherBandeau(restant) {
    if (!bandeau) {
      bandeau = document.createElement('div');
      bandeau.setAttribute('role', 'alert');
      bandeau.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;background:#b91c1c;color:#fff;' +
        'text-align:center;padding:10px 16px;font-size:.95rem;font-weight:600;';
      document.body.appendChild(bandeau);
    }
    bandeau.textContent = 'Caisse inactive : déconnexion automatique dans ' + restant + ' s. Bougez la souris pour rester connecté.';
  }

  setInterval(function () {
    var inactif = Math.floor((Date.now() - derniereActivite) / 1000);
    if (inactif >= total) {
      deconnecter();
    } else if (inactif >= total - PREAVIS) {
      afficherBandeau(total - inactif);
    }
  }, 1000);
})();
