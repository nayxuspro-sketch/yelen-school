/* YELEN SCHOOL — Saisie hors réseau, côté Service Worker (chargé par /app-sw.js via importScripts).
 *
 * Un formulaire de notes ou d'appel soumis alors que le serveur est injoignable est conservé dans
 * IndexedDB (une saisie par page : la plus récente remplace la précédente), puis rejoué à l'identique
 * quand une page de l'application le demande (message « saisies:synchroniser », envoyé par
 * saisies_hors_ligne.js au chargement et au retour du réseau). Le rejeu porte l'en-tête
 * X-Saisie-Differee : le serveur répond en JSON (core/hors_ligne.py).
 *
 * Le rejeu n'est jamais lancé sans page ouverte : la page fournit le jeton CSRF courant et l'identité
 * de l'utilisateur connecté, et seules ses propres saisies sont transmises.
 */
/* global self, caches, indexedDB, Response, URLSearchParams */
(function (global) {
  'use strict';

  const PAGES = [
    /^\/pedagogie\/evaluations\/[0-9a-f-]{36}\/saisie\/$/,
    /^\/presences\/appel\/[0-9a-f-]{36}\/saisie\/$/,
  ];
  const PAGE_FILE = '/hors-ligne/saisies/';
  const BASE = 'yelen-hors-ligne';
  const SAISIES = 'saisies';
  const TRANSMISSIONS = 'transmissions';
  const MAX_TRANSMISSIONS = 20;

  function concerne(chemin) {
    return PAGES.some(motif => motif.test(chemin));
  }

  // ── IndexedDB ──────────────────────────────────────────────────────────────
  function ouvrir() {
    return new Promise((resolve, reject) => {
      const demande = indexedDB.open(BASE, 1);
      demande.onupgradeneeded = () => {
        demande.result.createObjectStore(SAISIES, { keyPath: 'url' });
        demande.result.createObjectStore(TRANSMISSIONS, { autoIncrement: true });
      };
      demande.onsuccess = () => resolve(demande.result);
      demande.onerror = () => reject(demande.error);
    });
  }

  function transaction(magasin, mode, action) {
    return ouvrir().then(db => new Promise((resolve, reject) => {
      const tx = db.transaction(magasin, mode);
      const requete = action(tx.objectStore(magasin));
      tx.oncomplete = () => { db.close(); resolve(requete ? requete.result : undefined); };
      tx.onerror = () => { db.close(); reject(tx.error); };
    }));
  }

  const lireTout = magasin => transaction(magasin, 'readonly', s => s.getAll());
  const lire = url => transaction(SAISIES, 'readonly', s => s.get(url));
  const ecrire = saisie => transaction(SAISIES, 'readwrite', s => s.put(saisie));
  const retirer = url => transaction(SAISIES, 'readwrite', s => s.delete(url));

  function archiver(transmission) {
    return transaction(TRANSMISSIONS, 'readwrite', s => { s.add(transmission); return s.getAllKeys(); })
      .then(cles => {
        const excedent = cles.length - MAX_TRANSMISSIONS;
        if (excedent <= 0) return;
        return transaction(TRANSMISSIONS, 'readwrite', s => { cles.slice(0, excedent).forEach(c => s.delete(c)); });
      });
  }

  // ── Interception d'une soumission ──────────────────────────────────────────
  async function depuisLaPageEnCache(url) {
    const page = await caches.match(url, { ignoreVary: true });
    if (!page) return {};
    const html = await page.text();
    const titre = /<title>([^<]*)<\/title>/.exec(html);
    const utilisateur = /name="yelen-utilisateur" content="([^"]*)"/.exec(html);
    return {
      titre: titre ? titre[1].replace(/\s+/g, ' ').trim() : '',
      utilisateur: utilisateur ? utilisateur[1] : '',
    };
  }

  async function intercepter(request) {
    const type = request.headers.get('Content-Type') || '';
    if (!type.startsWith('application/x-www-form-urlencoded')) return fetch(request);
    const corps = await request.clone().text();
    try {
      return await fetch(request);
    } catch (_) {
      // Serveur injoignable : la saisie est conservée sur l'appareil.
    }
    const url = new URL(request.url).pathname;
    const page = await depuisLaPageEnCache(url);
    await ecrire({
      url, corps,
      titre: page.titre || url,
      utilisateur: page.utilisateur || '',
      enregistree_le: new Date().toISOString(),
      etat: 'attente',
      motif: '',
    });
    return Response.redirect(PAGE_FILE + '#enregistree', 303);
  }

  // ── Rejeu ──────────────────────────────────────────────────────────────────
  let rejeuEnCours = null;

  async function rejouer(contexte) {
    const bilan = { transmises: [], refusees: [], bloquee: '' };
    const saisies = (await lireTout(SAISIES))
      .filter(s => s.etat === 'attente')
      .sort((a, b) => (a.enregistree_le < b.enregistree_le ? -1 : 1));

    for (const saisie of saisies) {
      if (saisie.utilisateur && contexte.utilisateur && saisie.utilisateur !== contexte.utilisateur) continue;
      const corps = new URLSearchParams(saisie.corps);
      corps.delete('csrfmiddlewaretoken');          // remplacé par le jeton courant (en-tête)
      let reponse;
      try {
        reponse = await fetch(saisie.url, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': contexte.csrf || '',
            'X-Saisie-Differee': saisie.enregistree_le,
            'X-Saisie-Utilisateur': saisie.utilisateur || '',
          },
          body: corps.toString(),
        });
      } catch (_) {
        bilan.bloquee = 'reseau';
        break;
      }
      const json = (reponse.headers.get('Content-Type') || '').includes('application/json');
      if (reponse.status === 401) { bilan.bloquee = 'connexion'; break; }
      if (reponse.status === 403 && !json) { bilan.bloquee = 'jeton'; break; }   // jeton CSRF périmé
      if (!json || (!reponse.ok && reponse.status !== 403)) { bilan.bloquee = 'serveur'; break; }

      const retour = await reponse.json();
      if (retour.code === 'utilisateur') continue;               // saisie d'un autre compte : attend son auteur
      const messages = retour.messages || [];
      if (retour.ok) {
        await retirer(saisie.url);
        await archiver({ titre: saisie.titre, url: saisie.url, enregistree_le: saisie.enregistree_le,
                         transmise_le: new Date().toISOString(), messages });
        bilan.transmises.push({ titre: saisie.titre, messages });
      } else {
        saisie.etat = 'refusee';
        saisie.motif = messages.map(m => m.texte).join(' ') || 'Saisie refusée par le serveur.';
        await ecrire(saisie);
        bilan.refusees.push({ titre: saisie.titre, motif: saisie.motif });
      }
    }
    return bilan;
  }

  function synchroniser(contexte) {
    if (!rejeuEnCours) {
      rejeuEnCours = rejouer(contexte).finally(() => { rejeuEnCours = null; });
    }
    return rejeuEnCours;
  }

  // ── État communiqué aux pages ──────────────────────────────────────────────
  async function etat() {
    const saisies = (await lireTout(SAISIES)).map(s => ({
      url: s.url, titre: s.titre, utilisateur: s.utilisateur, enregistree_le: s.enregistree_le,
      etat: s.etat, motif: s.motif, cloture: new URLSearchParams(s.corps).has('clore'),
    }));
    return { type: 'saisies:etat', saisies, transmissions: (await lireTout(TRANSMISSIONS)).reverse() };
  }

  function diffuser(message) {
    return self.clients.matchAll({ type: 'window' }).then(clients => clients.forEach(c => c.postMessage(message)));
  }

  self.addEventListener('message', e => {
    const d = e.data || {};
    if (typeof d.type !== 'string' || !d.type.startsWith('saisies:')) return;
    const port = e.ports && e.ports[0];
    const repondre = r => { if (port) port.postMessage(r); };
    let travail;
    if (d.type === 'saisies:etat') {
      travail = etat().then(repondre);
    } else if (d.type === 'saisies:lire') {
      travail = lire(d.url).then(s => repondre(s || null));
    } else if (d.type === 'saisies:retirer') {
      travail = retirer(d.url).then(etat).then(r => { repondre(r); return diffuser(r); });
    } else if (d.type === 'saisies:reessayer') {
      travail = lire(d.url)
        .then(s => { if (s) { s.etat = 'attente'; s.motif = ''; return ecrire(s); } })
        .then(etat).then(r => { repondre(r); return diffuser(r); });
    } else if (d.type === 'saisies:synchroniser') {
      travail = synchroniser({ csrf: d.csrf, utilisateur: d.utilisateur })
        .then(bilan => etat().then(r => { repondre(Object.assign({ bilan }, r)); return diffuser(r); }));
    } else {
      return;
    }
    e.waitUntil(travail.catch(() => repondre(null)));
  });

  global.SAISIES = { concerne, intercepter };
})(self);
