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
          if (typeof window.bulkSelectAll === 'function') window.bulkSelectAll();
          break;
        case 'bulk-deselect-all':
          if (typeof window.bulkDeselectAll === 'function') window.bulkDeselectAll();
          break;
        case 'bulk-export':
          if (typeof window.exportSelected === 'function') window.exportSelected();
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
          var insertTarget = actionEl.dataset.insertTarget;
          var insertVar = actionEl.dataset.insertVar;
          if (insertTarget && insertVar && typeof window.insertVariable === 'function') {
            window.insertVariable(insertTarget, insertVar);
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

    // 10. data-csp-href="url" ou template
    var hrefEl = target.closest('[data-csp-href]');
    if (hrefEl && !hrefEl.closest('a')) {
      // Seulement si ce n'est pas déjà un lien
      e.preventDefault();
      var href = hrefEl.dataset.cspHref;
      if (href) window.location.href = href;
      return;
    }

    // 11. data-csp-href-template pour les cas avec {% url %}
    var hrefTpl = target.closest('[data-csp-href-template]');
    if (hrefTpl) {
      e.preventDefault();
      var tpl = hrefTpl.dataset.cspHrefTemplate;
      var inscrId = hrefTpl.dataset.inscrId;
      if (tpl === 'fiche_suivi_eleve' && inscrId) {
        window.location.href = '/viescolaire/fiche-suivi/' + inscrId + '/';
      } else if (tpl === 'fiche_suivi_eleve_sanctions' && inscrId) {
        window.location.href = '/viescolaire/fiche-suivi/' + inscrId + '/#sanctions';
      }
      return;
    }
  });

  // ── Delegation submit pour confirm ─────────────────────────────────
  document.addEventListener('submit', function(e) {
    var form = e.target;
    var confirmMsg = form.dataset.cspConfirmSubmit;
    if (confirmMsg) {
      if (!confirm(confirmMsg)) {
        e.preventDefault();
      }
    }
  });

  // ── Delegation change : data-csp-fill-target="id" ──────────────────
  // Sur un <select>, recopie le data-fill de l'option choisie dans le champ cible
  // (ex. montant d'une rubrique → champ Montant). Fonctionne pour le contenu injecté par HTMX.
  document.addEventListener('change', function(e) {
    var sel = e.target;
    if (!sel || !sel.dataset || !sel.dataset.cspFillTarget) return;
    var cible = document.getElementById(sel.dataset.cspFillTarget);
    var opt = sel.options ? sel.options[sel.selectedIndex] : null;
    if (!cible || !opt) return;
    var valeur = opt.dataset.fill;
    if (valeur) cible.value = valeur;
  });

  // ── Expose helpers globaux pour compatibilité ───────────────────────
  window.cspCloseModal = closeModalById;
  window.cspShowModal = showModalById;

})();
