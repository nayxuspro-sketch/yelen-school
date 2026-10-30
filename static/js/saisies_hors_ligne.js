/* YELEN SCHOOL — Saisie hors réseau, côté page (chargé par base.html et par /hors-ligne/saisies/).
 *
 * Dialogue avec le Service Worker (sw_saisies.js) :
 *  - pastille « N saisie(s) en attente » et transmission automatique au chargement et au retour du réseau ;
 *  - sur une page de saisie : indication « disponible hors réseau » et restauration des valeurs d'une
 *    saisie conservée ;
 *  - page « Saisies hors réseau » : liste, transmission manuelle, nouvel essai, retrait, historique,
 *    pages de saisie consultables sans réseau.
 */
(function () {
  'use strict';
  if (!('serviceWorker' in navigator)) return;

  var PAGES = [
    /^\/pedagogie\/evaluations\/[0-9a-f-]{36}\/saisie\/$/,
    /^\/presences\/appel\/[0-9a-f-]{36}\/saisie\/$/,
  ];
  var PAGE_FILE = '/hors-ligne/saisies/';
  var URL_CONTEXTE = '/hors-ligne/contexte/';
  var SUFFIXE_TITRE = / — YELEN SCHOOL$/;

  function meta(nom) {
    var m = document.querySelector('meta[name="' + nom + '"]');
    return m ? m.getAttribute('content') : '';
  }
  var contexte = { utilisateur: meta('yelen-utilisateur') };   // affiné par /hors-ligne/contexte/ avant chaque transmission
  var pastille = document.getElementById('saisies-attente');
  var pageFile = document.getElementById('saisies-liste');
  var worker = null;

  // ── Utilitaires ─────────────────────────────────────────────────────────────
  function demander(message) {
    return new Promise(function (resolve) {
      if (!worker) { resolve(null); return; }
      var canal = new MessageChannel();
      var minuteur = setTimeout(function () { resolve(null); }, 20000);
      canal.port1.onmessage = function (e) { clearTimeout(minuteur); resolve(e.data); };
      worker.postMessage(message, [canal.port2]);
    });
  }

  function texteTitre(titre) {
    var doc = new DOMParser().parseFromString(titre || '', 'text/html');
    return (doc.documentElement.textContent || '').replace(SUFFIXE_TITRE, '').trim();
  }

  function dateCourte(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return '';
    var deux = function (n) { return (n < 10 ? '0' : '') + n; };
    return deux(d.getDate()) + '/' + deux(d.getMonth() + 1) + '/' + d.getFullYear() + ' à ' + deux(d.getHours()) + ':' + deux(d.getMinutes());
  }

  function toast(message, type) {
    if (typeof window.showToast === 'function') { window.showToast(message, type); return; }
    var statut = document.getElementById('saisies-statut');
    if (statut) { statut.textContent = message; statut.className = 'hl-statut hl-statut-' + (type || 'info'); }
  }

  function element(balise, classe, texte) {
    var el = document.createElement(balise);
    if (classe) el.className = classe;
    if (texte !== undefined) el.textContent = texte;
    return el;
  }

  // ── Pastille et synchronisation ─────────────────────────────────────────────
  function afficherEtat(etat) {
    var saisies = etat.saisies || [];
    var attente = saisies.filter(function (s) { return s.etat === 'attente'; }).length;
    var refusees = saisies.length - attente;
    if (pastille) {
      pastille.hidden = saisies.length === 0;
      pastille.textContent = attente
        ? attente + ' saisie' + (attente > 1 ? 's' : '') + ' en attente de transmission'
        : refusees + ' saisie' + (refusees > 1 ? 's' : '') + ' refusée' + (refusees > 1 ? 's' : '');
    }
    if (pageFile) rendrePageFile(etat);
  }

  function connexionRequise() {
    toast('Des saisies hors réseau attendent : connectez-vous pour les transmettre.', 'warning');
    var statut = document.getElementById('saisies-statut');
    if (!statut) return;
    statut.textContent = 'Connexion requise pour transmettre vos saisies : ';
    var lien = element('a', 'hl-lien', 'se connecter');
    lien.href = '/accounts/login/?next=' + encodeURIComponent(PAGE_FILE);
    statut.appendChild(lien);
    statut.className = 'hl-statut hl-statut-warning';
  }

  function synchroniser() {
    if (!navigator.onLine) return Promise.resolve();
    // Contexte frais (session, identité, jeton CSRF) : une page servie depuis le cache serait périmée.
    return fetch(URL_CONTEXTE, { credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (ctx) {
        if (!ctx) return;                                  // serveur injoignable : on réessaiera
        if (!ctx.authentifie) { connexionRequise(); return; }
        contexte.utilisateur = ctx.utilisateur;
        return demander({ type: 'saisies:synchroniser', csrf: ctx.csrf, utilisateur: ctx.utilisateur })
          .then(function (etat) {
            if (!etat) return;
            afficherEtat(etat);
            var bilan = etat.bilan || {};
            (bilan.transmises || []).forEach(function (t) {
              var details = (t.messages || []).map(function (m) { return m.texte; }).join(' ');
              toast('Saisie transmise — ' + texteTitre(t.titre) + (details ? ' : ' + details : ''), 'success');
            });
            (bilan.refusees || []).forEach(function (t) {
              toast('Saisie refusée — ' + texteTitre(t.titre) + ' : ' + t.motif, 'error');
            });
            if (bilan.bloquee === 'connexion') {
              connexionRequise();
            } else if (bilan.bloquee === 'jeton' || bilan.bloquee === 'serveur') {
              toast('Transmission interrompue : réponse inattendue du serveur. Nouvel essai au prochain chargement.', 'warning');
            }
          });
      });
  }

  // ── Page de saisie : disponibilité hors réseau et restauration ──────────────
  function marquerDisponible(form) {
    if (!('caches' in window)) return;
    var verifier = function () {
      return caches.match(window.location.pathname, { ignoreVary: true }).then(function (r) { return !!r; });
    };
    verifier().then(function (ok) { return ok || new Promise(function (res) { setTimeout(function () { verifier().then(res); }, 1500); }); })
      .then(function (ok) {
        if (!ok) return;
        var pill = element('span', 'hl-pastille-dispo', 'Disponible hors réseau : une saisie faite sans serveur sera transmise automatiquement.');
        form.insertAdjacentElement('beforebegin', pill);
      }).catch(function () {});
  }

  function restaurer(form, saisie) {
    var params = new URLSearchParams(saisie.corps);
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.matches(':disabled') || el.name === 'csrfmiddlewaretoken') return;
      if (el.type === 'submit' || el.type === 'button' || el.type === 'hidden') return;
      var coche = el.type === 'checkbox' || el.type === 'radio';
      var avant = coche ? el.checked : el.value;
      if (el.type === 'checkbox') {
        el.checked = params.getAll(el.name).indexOf(el.value || 'on') !== -1;
      } else if (el.type === 'radio') {
        if (params.has(el.name)) el.checked = params.get(el.name) === el.value;
      } else if (params.has(el.name)) {
        el.value = params.getAll(el.name).filter(function (v) { return v !== ''; })[0] || '';
      }
      if ((coche ? el.checked : el.value) === avant) return;    // inchangé : aucun événement (effets de bord de la page)
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    var bandeau = element('div', 'hl-bandeau' + (saisie.etat === 'refusee' ? ' hl-bandeau-refus' : ''));
    bandeau.setAttribute('role', 'status');
    bandeau.textContent = saisie.etat === 'refusee'
      ? 'Saisie du ' + dateCourte(saisie.enregistree_le) + ' refusée par le serveur (' + saisie.motif + '). Vos valeurs ont été restaurées : corrigez puis enregistrez de nouveau.'
      : 'Saisie du ' + dateCourte(saisie.enregistree_le) + (params.has('clore') ? ' (avec clôture de la séance)' : '')
        + ' conservée sur cet appareil, en attente de transmission. Vos valeurs ont été restaurées ; enregistrer de nouveau la remplace.';
    var lien = element('a', 'hl-bandeau-lien', 'Voir les saisies en attente');
    lien.href = PAGE_FILE;
    bandeau.appendChild(document.createTextNode(' '));
    bandeau.appendChild(lien);
    form.insertAdjacentElement('beforebegin', bandeau);
  }

  function pageDeSaisie() {
    var form = document.querySelector('#main-content form[method="post"]:not([action])');   // le formulaire de saisie, pas la déconnexion
    if (!form || !PAGES.some(function (m) { return m.test(window.location.pathname); })) return;
    marquerDisponible(form);
    demander({ type: 'saisies:lire', url: window.location.pathname }).then(function (saisie) {
      if (saisie && saisie.corps) restaurer(form, saisie);
    });
  }

  // ── Page « Saisies hors réseau » ────────────────────────────────────────────
  function bouton(libelle, classe, action) {
    var b = element('button', classe, libelle);
    b.type = 'button';
    b.addEventListener('click', action);
    return b;
  }

  function rendrePageFile(etat) {
    var saisies = etat.saisies || [];
    pageFile.textContent = '';
    if (!saisies.length) {
      pageFile.appendChild(element('p', 'hl-vide', 'Aucune saisie en attente : tout a été transmis au serveur.'));
    }
    saisies.sort(function (a, b) { return a.enregistree_le < b.enregistree_le ? -1 : 1; }).forEach(function (s) {
      var carte = element('div', 'hl-carte' + (s.etat === 'refusee' ? ' hl-carte-refus' : ''));
      carte.appendChild(element('div', 'hl-carte-titre', texteTitre(s.titre)));
      carte.appendChild(element('div', 'hl-carte-detail',
        'Enregistrée le ' + dateCourte(s.enregistree_le) + (s.cloture ? ' · avec clôture de la séance' : '')
        + (s.utilisateur && contexte.utilisateur && s.utilisateur !== contexte.utilisateur ? ' · saisie d\u2019un autre compte' : '')));
      if (s.etat === 'refusee') carte.appendChild(element('div', 'hl-carte-motif', 'Refusée : ' + s.motif));
      var actions = element('div', 'hl-carte-actions');
      var ouvrir = element('a', 'btn-secondary', 'Ouvrir la page');
      ouvrir.href = s.url;
      actions.appendChild(ouvrir);
      if (s.etat === 'refusee') {
        actions.appendChild(bouton('Réessayer', 'btn-secondary', function () {
          demander({ type: 'saisies:reessayer', url: s.url }).then(function (r) { if (r) afficherEtat(r); });
        }));
      }
      actions.appendChild(bouton('Retirer', 'btn-secondary hl-btn-danger', function () {
        if (!window.confirm('Retirer définitivement cette saisie de l\u2019appareil ? Les valeurs non transmises seront perdues.')) return;
        demander({ type: 'saisies:retirer', url: s.url }).then(function (r) { if (r) afficherEtat(r); });
      }));
      carte.appendChild(actions);
      pageFile.appendChild(carte);
    });

    var historique = document.getElementById('saisies-historique');
    if (historique) {
      historique.textContent = '';
      var transmissions = etat.transmissions || [];
      if (!transmissions.length) historique.appendChild(element('p', 'hl-vide', 'Aucune transmission récente.'));
      transmissions.forEach(function (t) {
        var ligne = element('div', 'hl-ligne');
        ligne.appendChild(element('span', 'hl-ligne-titre', texteTitre(t.titre)));
        ligne.appendChild(element('span', 'hl-ligne-detail', 'saisie le ' + dateCourte(t.enregistree_le) + ', transmise le ' + dateCourte(t.transmise_le)));
        var details = (t.messages || []).map(function (m) { return m.texte; }).join(' ');
        if (details) ligne.appendChild(element('span', 'hl-ligne-detail', details));
        historique.appendChild(ligne);
      });
    }

    var transmettre = document.getElementById('saisies-transmettre');
    if (transmettre) transmettre.disabled = !navigator.onLine || !saisies.some(function (s) { return s.etat === 'attente'; });
  }

  function listerPagesEnCache() {
    var conteneur = document.getElementById('saisies-pages');
    if (!conteneur || !('caches' in window)) return;
    caches.keys().then(function (noms) {
      var nom = noms.filter(function (n) { return n.indexOf('yelen-app-') === 0; })[0];
      if (!nom) return [];
      return caches.open(nom).then(function (cache) {
        return cache.keys().then(function (requetes) {
          var pages = requetes.filter(function (r) { return PAGES.some(function (m) { return m.test(new URL(r.url).pathname); }); });
          return Promise.all(pages.map(function (r) {
            return cache.match(r).then(function (rep) { return rep.text(); }).then(function (html) {
              var t = /<title>([^<]*)<\/title>/.exec(html);
              return { url: new URL(r.url).pathname, titre: t ? t[1] : r.url };
            });
          }));
        });
      });
    }).then(function (pages) {
      conteneur.textContent = '';
      if (!pages.length) {
        conteneur.appendChild(element('p', 'hl-vide', 'Aucune page de saisie en cache. Ouvrez vos pages de notes et d\u2019appel pendant que le serveur est joignable : elles resteront consultables ici.'));
        return;
      }
      pages.forEach(function (p) {
        var lien = element('a', 'hl-ligne hl-lien', texteTitre(p.titre));
        lien.href = p.url;
        conteneur.appendChild(lien);
      });
    }).catch(function () {});
  }

  function initPageFile() {
    var statut = document.getElementById('saisies-statut');
    var majStatut = function () {
      if (!statut) return;
      statut.textContent = navigator.onLine
        ? 'Réseau disponible — les saisies en attente sont transmises automatiquement.'
        : 'Hors réseau — les saisies seront transmises dès que le serveur sera joignable.';
      statut.className = 'hl-statut hl-statut-' + (navigator.onLine ? 'success' : 'warning');
      var transmettre = document.getElementById('saisies-transmettre');
      if (transmettre && !navigator.onLine) transmettre.disabled = true;
    };
    majStatut();
    window.addEventListener('online', majStatut);
    window.addEventListener('offline', majStatut);
    var transmettre = document.getElementById('saisies-transmettre');
    if (transmettre) transmettre.addEventListener('click', function () { transmettre.disabled = true; synchroniser(); });
    var confirmation = document.getElementById('saisies-enregistree');
    if (confirmation && window.location.hash === '#enregistree') confirmation.hidden = false;
    listerPagesEnCache();
  }

  // ── Démarrage ───────────────────────────────────────────────────────────────
  navigator.serviceWorker.addEventListener('message', function (e) {
    if (e.data && e.data.type === 'saisies:etat') afficherEtat(e.data);
  });
  window.addEventListener('online', function () { setTimeout(synchroniser, 2000); });
  if (pageFile) initPageFile();

  navigator.serviceWorker.ready.then(function (reg) {
    worker = reg.active;
    return demander({ type: 'saisies:etat' });
  }).then(function (etat) {
    if (!etat) return;
    afficherEtat(etat);
    pageDeSaisie();
    if ((etat.saisies || []).some(function (s) { return s.etat === 'attente'; })) synchroniser();
  }).catch(function () {});
})();
