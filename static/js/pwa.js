/* YELEN SCHOOL — PWA Client (portails parent et élève : data-pwa-sw / data-pwa-scope sur <body>) */

// ── Service Worker Registration ───────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const cfg = document.body.dataset;
    navigator.serviceWorker.register(cfg.pwaSw || '/sw.js', { scope: cfg.pwaScope || '/portail/parent/' })
      .catch(() => {});
  });
}

// ── Install Prompt (A2HS) ─────────────────────────────────────────────────────
let _deferredPrompt = null;

window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  _deferredPrompt = e;
  const banner = document.getElementById('pwa-install-banner');
  if (banner && sessionStorage.getItem('pwa-dismissed') !== '1') {
    banner.classList.remove('pp-hidden');
  }
});

window.addEventListener('appinstalled', () => {
  const banner = document.getElementById('pwa-install-banner');
  if (banner) banner.classList.add('pp-hidden');
  _deferredPrompt = null;
});

function pwaTriggerInstall() {
  if (!_deferredPrompt) return;
  _deferredPrompt.prompt();
  _deferredPrompt.userChoice.finally(() => {
    _deferredPrompt = null;
    const banner = document.getElementById('pwa-install-banner');
    if (banner) banner.classList.add('pp-hidden');
  });
}

function pwaDismiss() {
  sessionStorage.setItem('pwa-dismissed', '1');
  const banner = document.getElementById('pwa-install-banner');
  if (banner) banner.classList.add('pp-hidden');
}

// ── Offline Indicator ─────────────────────────────────────────────────────────
function _updateOnlineStatus() {
  const el = document.getElementById('pwa-offline-banner');
  if (el) el.classList.toggle('pp-hidden', navigator.onLine);
}
window.addEventListener('online',  _updateOnlineStatus);
window.addEventListener('offline', _updateOnlineStatus);
_updateOnlineStatus();
