/* YELEN SCHOOL — PWA Client (Portail Parent) */

// ── Service Worker Registration ───────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/portail/parent/' })
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
    banner.classList.remove('pwa-hidden');
  }
});

window.addEventListener('appinstalled', () => {
  const banner = document.getElementById('pwa-install-banner');
  if (banner) banner.classList.add('pwa-hidden');
  _deferredPrompt = null;
});

function pwaTriggerInstall() {
  if (!_deferredPrompt) return;
  _deferredPrompt.prompt();
  _deferredPrompt.userChoice.finally(() => {
    _deferredPrompt = null;
    const banner = document.getElementById('pwa-install-banner');
    if (banner) banner.classList.add('pwa-hidden');
  });
}

function pwaDismiss() {
  sessionStorage.setItem('pwa-dismissed', '1');
  const banner = document.getElementById('pwa-install-banner');
  if (banner) banner.classList.add('pwa-hidden');
}

// ── Offline Indicator ─────────────────────────────────────────────────────────
function _updateOnlineStatus() {
  const el = document.getElementById('pwa-offline-banner');
  if (el) el.classList.toggle('pwa-hidden', navigator.onLine);
}
window.addEventListener('online',  _updateOnlineStatus);
window.addEventListener('offline', _updateOnlineStatus);
_updateOnlineStatus();
