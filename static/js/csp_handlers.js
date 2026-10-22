/**
 * csp_handlers.js — Gestionnaires CSP-compatibles pour remplacer les onclick/onsubmit inline
 * Bloqués par script-src-attr 'none'. Tous les handlers utilisent data-csp-* attributes.
 * Inclus avec nonce dans base.html et autres templates standalone.
 */
(function() {
  'use strict';

  // ── Helpers ──────────────────────────────────────────────────────────
  function closeModalById(id) {
    var el = document.getElementById(id);
    if (el) {
      // Gère à la fois style.display et class modal-open
      if (el.classList.contains('modal') || el.classList.contains('modal-open')) {
        el.classList.remove('modal-open');
      } else {
        el.style.display = 'none';
      }
      // Si c'est modal-container, vide aussi modal-content
      if (id === 'modal-container') {
        var content = document.getElementById('modal-content');
        if (content) content.innerHTML = '';
      }
    }
  }

  function showModalById(id, display) {
    var el = document.getElementById(id);
    if (el) {
      if (display) el.style.display = display;
      else el.style.display = 'flex';
    }
  }

  // Barre d'actions groupées (templates/partials/bulk_actions.html) :
  // les cases .bulk-checkbox avec value sont les éléments ; une case sans value
  // (en-tête de tableau) coche / décoche toutes celles de son tableau.
  function bulkItems(racine) {
    return (racine || document).querySelectorAll('.bulk-checkbox[value]');
  }

  function bulkRefresh() {
    var bar = document.getElementById('bulk-actions-bar');
    if (!bar) return;
    var n = document.querySelectorAll('.bulk-checkbox[value]:checked').length;
    var compteur = document.getElementById('bulk-count');
    if (compteur) compteur.textContent = n + ' élément(s) sélectionné(s)';
    bar.hidden = n === 0;
  }

  function bulkSetAll(racine, coche) {
    bulkItems(racine).forEach(function(cb) { cb.checked = coche; });
    document.querySelectorAll('.bulk-checkbox:not([value])').forEach(function(cb) {
      if (!racine || racine.contains(cb)) cb.checked = coche;
    });
    bulkRefresh();
  }

  // ── Delegation globale click ─────────────────────────────────────────
  document.addEventListener('click', function(e) {
    var target = e.target;

    // 1. data-csp-dismiss="id" → cache l'élément
    var dismiss = target.closest('[data-csp-dismiss]');
    if (dismiss) {
      e.preventDefault();
      closeModalById(dismiss.dataset.cspDismiss);
      return;
    }

    // 2. data-csp-show="id" → affiche l'élément
    var show = target.closest('[data-csp-show]');
    if (show) {
      e.preventDefault();
      showModalById(show.dataset.cspShow, show.dataset.cspShowDisplay || 'flex');
      return;
    }

    // 3. data-csp-remove="id" → supprime l'élément
    var remove = target.closest('[data-csp-remove]');
    if (remove) {
      e.preventDefault();
      var el = document.getElementById(remove.dataset.cspRemove);
      if (el) el.remove();
      return;
    }

    // 4. data-csp-trigger-click="id" → déclenche click sur un autre élément
    var trigger = target.closest('[data-csp-trigger-click]');
    if (trigger) {
      e.preventDefault();
      var el = document.getElementById(trigger.dataset.cspTriggerClick);
      if (el) el.click();
      return;
    }

    // 5. data-csp-confirm="message" → confirm avant action, si annulé empêche
    var confirmEl = target.closest('[data-csp-confirm]');
    if (confirmEl) {
      var msg = confirmEl.dataset.cspConfirm;
      if (!confirm(msg)) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
      // Si c'est un bouton dans un formulaire, laisse passer
      // Si c'est un lien, laisse passer
      return;
    }

    // 6. data-csp-action générique
    var actionEl = target.closest('[data-csp-action]');
    if (actionEl) {
      var action = actionEl.dataset.cspAction;

      switch (action) {
        case 'reload':
          e.preventDefault();
          window.location.reload();
          break;
        case 'print':
          e.preventDefault();
          window.print();
          break;
        case 'history-back':
          // Retour à la page précédente ; sans historique (nouvel onglet), suit le href de repli.
          e.preventDefault();
          if (window.history.length > 1) window.history.back();
          else window.location.href = actionEl.getAttribute('href') || '/';
          break;
        case 'close-modal':
          e.preventDefault();
          // Ferme le modal le plus proche ou modal-container
          var modal = actionEl.closest('.modal') || document.getElementById('modal-container') || document.getElementById('modal-overlay');
          if (modal) {
            if (modal.classList.contains('modal-open')) modal.classList.remove('modal-open');
            else {
              modal.style.display = 'none';
              if (modal.id === 'modal-container') {
                var mc = document.getElementById('modal-content');
                if (mc) mc.innerHTML = '';
              }
            }
          }
          break;
        case 'close-modal-container':
          e.preventDefault();
          closeModalById('modal-container');
          break;
        case 'modal-close-parent':
          e.preventDefault();
          if (actionEl.parentElement) actionEl.parentElement.classList.remove('modal-open');
          break;
        case 'modal-close-closest':
          e.preventDefault();
          var closestModal = actionEl.closest('.modal');
          if (closestModal) closestModal.classList.remove('modal-open');
          break;
        case 'modal-backdrop-dismiss':
          // Seulement si on clique sur le backdrop lui-même
          if (e.target === actionEl) {
            actionEl.style.display = 'none';
          }
          break;
        case 'clear-form':
          e.preventDefault();
          var formId = actionEl.dataset.formId;
          var formEl = document.getElementById(formId);
          if (formEl) formEl.innerHTML = '';
          break;
        case 'clear-edt-gen':
          e.preventDefault();
          var edt = document.getElementById('edt-gen-container');
          if (edt) edt.innerHTML = '';
          break;
        case 'toggle-cycle':
          // toggleCycle(this) — this = header
          var header = actionEl;
          var content = header.nextElementSibling;
          if (content) {
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
          }
          break;
        case 'stop-propagation':
          e.stopPropagation();
          break;
        case 'toggle-eleve':
          // toggleEleve(this)
          var card = actionEl.closest('.card') || actionEl.parentElement;
          if (card) {
            var body = card.querySelector('.card-body') || card.nextElementSibling;
            if (body) body.style.display = body.style.display === 'none' ? 'block' : 'none';
          }
          break;
        case 'mark-all-present':
          if (typeof window.markAllPresent === 'function') window.markAllPresent();
          break;
        case 'bulk-select-all':
          bulkSetAll(null, true);
          break;
        case 'bulk-deselect-all':
          bulkSetAll(null, false);
          break;
        case 'bulk-export':
          var ids = Array.prototype.map.call(document.querySelectorAll('.bulk-checkbox[value]:checked'),
            function(cb) { return cb.value; }).join(',');
          if (actionEl.dataset.exportUrl) window.location.href = actionEl.dataset.exportUrl + '?ids=' + ids;
          break;
        case 'copy-link':
          e.preventDefault();
          var copyTargetId = actionEl.dataset.copyTarget;
          var copyEl = document.getElementById(copyTargetId);
          if (copyEl) {
            var text = copyEl.textContent.trim();
            navigator.clipboard.writeText(text).then(function() {
              var original = actionEl.textContent;
              actionEl.textContent = 'Copié ✓';
              setTimeout(function() { actionEl.textContent = original; }, 1500);
            });
          }
          break;
        case 'copy-text':
          e.preventDefault();
          var textId = actionEl.dataset.copyTextId;
          var textEl = document.getElementById(textId);
          if (textEl) {
            var txt = textEl.textContent || textEl.value || '';
            navigator.clipboard.writeText(txt).then(function() {
              var orig = actionEl.textContent;
              actionEl.textContent = 'Copié ✓';
              setTimeout(function() { actionEl.textContent = orig; }, 1500);
            });
          }
          break;
        case 'copy-webhook':
          if (typeof window.copierWebhook === 'function') window.copierWebhook();
          break;
        case 'pwa-install':
          if (typeof window.pwaAppInstall === 'function') window.pwaAppInstall();
          break;
        case 'pwa-trigger-install':
          if (typeof window.pwaTriggerInstall === 'function') window.pwaTriggerInstall();
          break;
        case 'fill-question':
          var q = actionEl.dataset.q;
          if (q && typeof window.fillQuestion === 'function') window.fillQuestion(q);
          break;
        case 'insert-variable':
          // Insère la variable à la position du curseur du champ cible
          var champ = document.getElementById(actionEl.dataset.insertTarget || '');
          var variable = actionEl.dataset.insertVar;
          if (champ && variable) {
            var debut = champ.selectionStart == null ? champ.value.length : champ.selectionStart;
            var fin = champ.selectionEnd == null ? debut : champ.selectionEnd;
            champ.value = champ.value.substring(0, debut) + variable + champ.value.substring(fin);
            champ.selectionStart = champ.selectionEnd = debut + variable.length;
            champ.focus();
            champ.dispatchEvent(new Event('input', { bubbles: true }));  // met à jour le compteur
          }
          break;
        case 'show-tab':
          var tabId = actionEl.dataset.tabId;
          if (tabId && typeof window.afficherOnglet === 'function') window.afficherOnglet(tabId);
          break;
        case 'confirm-remboursement':
          var montantEl = document.getElementById('id_montant');
          var montant = montantEl ? montantEl.value : '';
          if (!confirm('Confirmer le remboursement de ' + montant + ' FCFA ?')) {
            e.preventDefault();
            e.stopPropagation();
          }
          break;
        case 'session-detail-action':
          // Cas générique pour session_detail multi-line - on évalue le contenu stocké
          // Pour sécurité, on ne fait rien par défaut, le template doit migrer vers un handler spécifique
          console.warn('CSP: session-detail-action non migré complètement', actionEl);
          break;
      }
    }

    // 7. data-csp-quick-email="email"
    var quick = target.closest('[data-csp-quick-email]');
    if (quick) {
      e.preventDefault();
      var email = quick.dataset.cspQuickEmail;
      if (typeof window.fillQuick === 'function') window.fillQuick(email);
      else {
        var userEl = document.getElementById('id_username');
        var passEl = document.getElementById('id_password');
        if (userEl) userEl.value = email;
        if (passEl) passEl.value = 'motdepasse123';
      }
      return;
    }

    // 8. data-csp-toggle-all="true/false"
    var toggleAll = target.closest('[data-csp-toggle-all]');
    if (toggleAll) {
      e.preventDefault();
      var val = toggleAll.dataset.cspToggleAll === 'true';
      if (typeof window.toggleAll === 'function') window.toggleAll(val);
      return;
    }

    // 9. data-csp-modal-open="id"
    var modalOpen = target.closest('[data-csp-modal-open]');
    if (modalOpen) {
      e.preventDefault();
      var modalId = modalOpen.dataset.cspModalOpen;
      var mEl = document.getElementById(modalId);
      if (mEl) mEl.classList.add('modal-open');
      return;
    }

    // 10. data-csp-href="url" (ligne cliquable) — l'URL vient du gabarit ({% url %}), jamais du JS.
    //     Un lien ou un bouton à l'intérieur de la ligne garde son propre comportement.
    var hrefEl = target.closest('[data-csp-href]');
    if (hrefEl && !target.closest('a, button')) {
      e.preventDefault();
      var href = hrefEl.dataset.cspHref;
      if (href) window.location.href = href;
      return;
    }
  });

  // ── Delegation submit pour confirm / prompt ────────────────────────
  // - data-csp-confirm-submit="message" : confirm avant soumission
  // - data-csp-prompt-submit="question" : demande un motif, le place dans le champ
  //   data-prompt-field (défaut « motif ») et bloque la soumission s'il est vide
  document.addEventListener('submit', function(e) {
    var form = e.target;
    var confirmMsg = form.dataset.cspConfirmSubmit;
    if (confirmMsg) {
      if (!confirm(confirmMsg)) {
        e.preventDefault();
        return;
      }
    }
    var promptMsg = form.dataset.cspPromptSubmit;
    if (promptMsg) {
      var reponse = prompt(promptMsg);
      if (reponse === null) {
        e.preventDefault();
        return;
      }
      if (!reponse.trim()) {
        alert('Le motif est obligatoire.');
        e.preventDefault();
        return;
      }
      var nomChamp = form.dataset.promptField || 'motif';
      var champ = form.querySelector('input[name="' + nomChamp + '"]');
      if (!champ) {
        champ = document.createElement('input');
        champ.type = 'hidden';
        champ.name = nomChamp;
        form.appendChild(champ);
      }
      champ.value = reponse.trim();
    }
  });

  // ── Delegation change ───────────────────────────────────────────────
  // - data-csp-submit-on-change : soumet le formulaire parent dès que le champ change
  //   (remplace onchange="this.form.submit()", bloqué par script-src-attr 'none')
  // - data-csp-fill-target="id" : sur un <select>, recopie le data-fill de l'option choisie
  //   dans le champ cible (ex. montant d'une rubrique → champ Montant).
  // - .bulk-checkbox : met à jour la barre d'actions groupées (case d'en-tête = tout cocher)
  // - data-csp-toggle-target="id" : sur une case à cocher, affiche (cochée) ou masque la cible
  // - data-csp-preview-image="id" : sur un <input type="file">, affiche le fichier choisi dans <img id> ;
  //   data-preview-reveal="id,…" éléments à afficher, data-preview-conceal="id,…" éléments à masquer
  // Fonctionne pour le contenu injecté par HTMX.
  function parIds(liste, fn) {
    (liste || '').split(',').forEach(function(id) {
      var el = id.trim() && document.getElementById(id.trim());
      if (el) fn(el);
    });
  }

  document.addEventListener('change', function(e) {
    var sel = e.target;
    if (!sel || !sel.dataset) return;
    if (sel.classList.contains('bulk-checkbox')) {
      if (sel.hasAttribute('value')) bulkRefresh();
      else bulkSetAll(sel.closest('table') || document, sel.checked);
      return;
    }
    if (sel.dataset.cspToggleTarget) {
      var cible = document.getElementById(sel.dataset.cspToggleTarget);
      if (cible) cible.style.display = sel.checked ? '' : 'none';
      return;
    }
    if (sel.dataset.cspPreviewImage) {
      if (!sel.files || !sel.files[0]) return;
      var lecteur = new FileReader();
      lecteur.onload = function(ev) {
        var img = document.getElementById(sel.dataset.cspPreviewImage);
        if (img) { img.src = ev.target.result; img.style.display = ''; }
        parIds(sel.dataset.previewReveal, function(el) { el.style.display = ''; });
        parIds(sel.dataset.previewConceal, function(el) { el.style.display = 'none'; });
      };
      lecteur.readAsDataURL(sel.files[0]);
      return;
    }
    if ('cspSubmitOnChange' in sel.dataset && sel.form) {
      if (typeof sel.form.requestSubmit === 'function') sel.form.requestSubmit();
      else sel.form.submit();
      return;
    }
    if (!sel.dataset.cspFillTarget) return;
    var cible = document.getElementById(sel.dataset.cspFillTarget);
    var opt = sel.options ? sel.options[sel.selectedIndex] : null;
    if (!cible || !opt) return;
    var valeur = opt.dataset.fill;
    if (valeur) cible.value = valeur;
  });

  // ── Delegation input : data-csp-sync-target / data-csp-count-target ─
  // - data-csp-sync-target="id"  : recopie la valeur saisie dans la cible
  //   (champ → .value, autre élément → textContent) ; ex. sélecteur de couleur ↔ champ texte
  // - data-csp-count-target="id" : affiche le nombre de caractères saisis dans la cible
  document.addEventListener('input', function(e) {
    var src = e.target;
    if (!src || !src.dataset) return;
    if (src.dataset.cspSyncTarget) {
      var cible = document.getElementById(src.dataset.cspSyncTarget);
      if (cible) {
        if (cible.tagName === 'INPUT' || cible.tagName === 'TEXTAREA' || cible.tagName === 'SELECT') {
          // Un <input type="color"> n'accepte qu'une couleur #rrggbb complète
          if (cible.type !== 'color' || /^#[0-9a-fA-F]{6}$/.test(src.value)) cible.value = src.value;
        } else {
          cible.textContent = src.value;
        }
      }
    }
    if (src.dataset.cspCountTarget) {
      var compteur = document.getElementById(src.dataset.cspCountTarget);
      if (compteur) compteur.textContent = src.value.length;
    }
  });

  // ── Expose helpers globaux pour compatibilité ───────────────────────
  window.cspCloseModal = closeModalById;
  window.cspShowModal = showModalById;

})();
