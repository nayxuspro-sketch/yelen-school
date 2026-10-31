/* YELEN SCHOOL — notifications push (core/push.py), portail parent et application du personnel.
   Pilote la carte [data-push-cle] : état de l'appareil, activation (permission + abonnement envoyé au serveur),
   test, désactivation. Un abonnement déjà présent est resynchronisé avec le serveur à chaque ouverture.
   data-push-sw / data-push-scope désignent le service worker qui reçoit les notifications (/sw.js du portail,
   /app-sw.js de l'application) ; data-push-texte-actif, le texte affiché une fois les notifications activées. */
(function () {
  'use strict';
  var carte = document.querySelector('[data-push-cle]');
  if (!carte) return;

  var cle = carte.getAttribute('data-push-cle');
  var urls = {
    abonner: carte.getAttribute('data-push-abonner'),
    desabonner: carte.getAttribute('data-push-desabonner'),
    tester: carte.getAttribute('data-push-test')
  };
  var worker = {
    script: carte.getAttribute('data-push-sw') || '/sw.js',
    scope: carte.getAttribute('data-push-scope') || '/portail/parent/'
  };
  var texteActif = carte.getAttribute('data-push-texte-actif') || 'Activées sur cet appareil.';
  var invitation = carte.getAttribute('data-push-mode') === 'invitation';
  var texte = carte.querySelector('[data-push-texte]');
  var boutons = {};
  carte.querySelectorAll('[data-push-action]').forEach(function (b) { boutons[b.getAttribute('data-push-action')] = b; });

  var supporte = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  var ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var installee = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

  function csrf() {
    var champ = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return champ ? champ.value : '';
  }

  function cleBinaire(base64url) {
    var base64 = (base64url + '='.repeat((4 - base64url.length % 4) % 4)).replace(/-/g, '+').replace(/_/g, '/');
    var brut = atob(base64);
    var tableau = new Uint8Array(brut.length);
    for (var i = 0; i < brut.length; i++) tableau[i] = brut.charCodeAt(i);
    return tableau;
  }

  function appeler(url, corps) {
    return fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify(corps)
    }).then(function (r) { return r.json().catch(function () { return { ok: false, message: 'Réponse illisible du serveur.' }; }); });
  }

  function afficher(message, actions) {
    if (message) texte.textContent = message;
    Object.keys(boutons).forEach(function (nom) { boutons[nom].classList.toggle('pp-hidden', actions.indexOf(nom) < 0); });
    carte.classList.remove('pp-hidden');
  }

  function montrerEtat(abonnement) {
    if (!supporte) {
      if (ios && !installee) {
        if (invitation) return;
        return afficher("Sur iPhone et iPad, installez d'abord l'application : Partager → Sur l'écran d'accueil, puis ouvrez-la.", []);
      }
      if (invitation) return;
      return afficher("Ce navigateur ne prend pas en charge les notifications.", []);
    }
    if (Notification.permission === 'denied') {
      if (invitation) return;
      return afficher("Les notifications sont bloquées pour ce site dans les réglages du navigateur.", []);
    }
    if (abonnement) {
      if (invitation) return carte.classList.add('pp-hidden');
      return afficher(texteActif, ['tester', 'desactiver']);
    }
    afficher(null, ['activer']);
  }

  function enregistrement() {
    return navigator.serviceWorker.register(worker.script, { scope: worker.scope })
      .then(function () { return navigator.serviceWorker.ready; });
  }

  function activer() {
    boutons.activer.disabled = true;
    Notification.requestPermission().then(function (permission) {
      if (permission !== 'granted') { boutons.activer.disabled = false; return montrerEtat(null); }
      return enregistrement()
        .then(function (reg) { return reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: cleBinaire(cle) }); })
        .then(function (abonnement) {
          return appeler(urls.abonner, abonnement.toJSON()).then(function (reponse) {
            if (!reponse.ok) throw new Error(reponse.message);
            invitation = false;
            montrerEtat(abonnement);
          });
        });
    }).catch(function (erreur) {
      afficher("Activation impossible : " + (erreur && erreur.message ? erreur.message : erreur), ['activer']);
    }).then(function () { boutons.activer.disabled = false; });
  }

  function abonnementCourant() {
    return navigator.serviceWorker.getRegistration(worker.scope)
      .then(function (reg) { return reg ? reg.pushManager.getSubscription() : null; });
  }

  function desactiver() {
    abonnementCourant().then(function (abonnement) {
      if (!abonnement) return montrerEtat(null);
      return appeler(urls.desabonner, { endpoint: abonnement.endpoint })
        .then(function () { return abonnement.unsubscribe(); })
        .then(function () { afficher("Notifications désactivées sur cet appareil.", ['activer']); });
    }).catch(function () { afficher("Désactivation impossible pour le moment.", ['desactiver']); });
  }

  function tester() {
    boutons.tester.disabled = true;
    abonnementCourant().then(function (abonnement) {
      if (!abonnement) return montrerEtat(null);
      return appeler(urls.tester, { endpoint: abonnement.endpoint })
        .then(function (reponse) { afficher(reponse.message, ['tester', 'desactiver']); });
    }).catch(function () { afficher("Test impossible pour le moment.", ['tester', 'desactiver']); })
      .then(function () { boutons.tester.disabled = false; });
  }

  carte.addEventListener('click', function (e) {
    var bouton = e.target.closest('[data-push-action]');
    if (!bouton) return;
    ({ activer: activer, desactiver: desactiver, tester: tester })[bouton.getAttribute('data-push-action')]();
  });

  if (!supporte) return montrerEtat(null);
  abonnementCourant().then(function (abonnement) {
    montrerEtat(abonnement);
    if (abonnement) appeler(urls.abonner, abonnement.toJSON()).catch(function () {});   // resynchronisation silencieuse
  }).catch(function () { montrerEtat(null); });
})();
