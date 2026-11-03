"""Application installable : manifeste, service worker, hors-ligne, icônes et certificat."""

from pathlib import Path
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import cache_control, never_cache
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse

from .portail import PORTAILS


def app_manifest(request):
    """Web App Manifest pour l'application principale YELEN SCHOOL (staff)."""
    manifest = {
        "name": "YELEN SCHOOL",
        "short_name": "YELEN",
        "description": "Système de gestion scolaire — Burkina Faso",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#0A1628",
        "theme_color": "#00A86B",
        "lang": "fr",
        "icons": [
            {"src": static('img/pwa/icon-192.png'), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static('img/pwa/icon-512.png'), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static('img/pwa/icon-maskable-512.png'), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "categories": ["education", "productivity"],
        "shortcuts": [
            {"name": "Mes cours — faire l'appel", "short_name": "Appel", "url": "/presences/mes-cours/"},
            {"name": "Saisir des notes", "short_name": "Notes", "url": "/pedagogie/evaluations/"},
        ],
    }
    return JsonResponse(manifest)


@never_cache
def app_service_worker(request):
    """Service Worker de l'application principale — cache les assets, page offline en fallback.

    Le nom du cache porte la version : chaque livraison change le script, le navigateur installe le
    nouveau worker qui purge l'ancien cache, puis les pages ouvertes se rechargent (base.html).
    """
    sw = """
const APP_CACHE = 'yelen-app-__VERSION__';
const PRECACHE = [
  '/offline/',
  '__PAGE_SAISIES__',
  '__CSS__',
  '__HTMX__',
  '__JS_SAISIES__',
];
const STATIC_ORIGIN = self.location.origin;
const BYPASS = ['/accounts/', '/admin/', '/api/', '/sw.js', '/app-sw.js', '/hors-ligne/contexte/'];

// Saisie hors réseau (notes, appels) : file d'attente des formulaires, rejouée au retour du réseau.
importScripts('__SW_SAISIES__');

// ── Install : pré-cache les assets critiques ──
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(APP_CACHE)
      .then(c => c.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

// ── Activate : purge les anciens caches ──
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== APP_CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ──
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== STATIC_ORIGIN) return;
  if (e.request.method === 'POST' && SAISIES.concerne(url.pathname)) {
    e.respondWith(SAISIES.intercepter(e.request));
    return;
  }
  if (e.request.method !== 'GET') return;
  if (BYPASS.some(p => url.pathname.startsWith(p))) return;

  // Copie mise en cache : clonée avant que le navigateur ne consomme la réponse (sinon clone() échoue
  // et rien n'est jamais mis en cache) ; waitUntil garde le worker en vie jusqu'à l'écriture.
  const memoriser = r => {
    const copie = r.clone();
    e.waitUntil(caches.open(APP_CACHE).then(c => c.put(e.request, copie)).catch(() => {}));
  };

  // Assets statiques et fichiers /media/ (servis après connexion) : Cache First.
  // Une réponse redirigée (session expirée → page de connexion) n'est jamais mise en cache.
  if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const network = fetch(e.request).then(r => {
          if (r.ok && !r.redirected) memoriser(r);
          return r;
        });
        return cached || network;
      })
    );
    return;
  }

  // Pages : Network First, fallback cache, fallback /offline/
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r.ok && !r.redirected) memoriser(r);
        return r;
      })
      .catch(() =>
        caches.match(e.request)
          .then(cached => cached || caches.match('/offline/'))
      )
  );
});

// ── Notifications push (core/push.py) : affichage, puis ouverture de la page concernée au toucher ──
self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { message: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.titre || 'YELEN SCHOOL', {
    body: d.message || '', icon: '__ICONE__', badge: '__ICONE__',
    tag: d.tag || 'yelen-app', renotify: true, data: { url: d.url || '__PAGE_NOTIFICATIONS__' }
  }));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '__PAGE_NOTIFICATIONS__';
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(liste => {
    const c = liste.find(w => new URL(w.url).origin === STATIC_ORIGIN);
    if (c) return c.navigate(url).then(() => c.focus()).catch(() => clients.openWindow(url));
    return clients.openWindow(url);
  }));
});
"""
    remplacements = {
        '__VERSION__': settings.YELEN_VERSION,
        '__PAGE_SAISIES__': reverse('core:saisies_hors_ligne'),
        '__CSS__': static('css/yelen.css'),
        '__HTMX__': static('js/htmx.min.js'),
        '__JS_SAISIES__': static('js/saisies_hors_ligne.js'),
        '__SW_SAISIES__': static('js/sw_saisies.js'),
        '__ICONE__': static('img/pwa/icon-192.png'),
        '__PAGE_NOTIFICATIONS__': reverse('core:notifications_list'),
    }
    script = sw.strip()
    for marqueur, valeur in remplacements.items():
        script = script.replace(marqueur, valeur)
    return HttpResponse(script, content_type='application/javascript')


def offline_page(request):
    """Page affichée par le Service Worker quand le serveur est inaccessible."""
    return render(request, 'core/offline.html')


def saisies_hors_ligne(request):
    """Saisies (notes, appels) conservées sur l'appareil faute de réseau : liste, transmission, retrait.
    Page sans donnée serveur (tout vient du navigateur), pré-cachée par le Service Worker, accessible
    hors connexion."""
    return render(request, 'core/saisies_hors_ligne.html')


@never_cache
def saisies_contexte(request):
    """Contexte frais demandé par le navigateur juste avant de transmettre ses saisies hors réseau :
    session encore valide ?, identité (seules les saisies de l'utilisateur connecté sont transmises)
    et jeton CSRF courant — une page servie depuis le cache porterait un jeton périmé."""
    authentifie = request.user.is_authenticated
    return JsonResponse({
        'authentifie': authentifie,
        'utilisateur': str(request.user.pk) if authentifie else '',
        'csrf': get_token(request),
    })


def pwa_manifest(request, role='PARENT'):
    """Web App Manifest du portail parent (``/manifest.json``) ou élève (``/manifest-eleve.json``)."""
    portail = PORTAILS[role]
    manifest = {
        "name": f"YELEN SCHOOL — {portail['titre']}",
        "short_name": portail['court'],
        "description": "Suivez la scolarité de vos enfants en temps réel" if role == 'PARENT' else "Votre scolarité en temps réel",
        "start_url": portail['prefixe'],
        "scope": portail['prefixe'],
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0A1628",
        "theme_color": "#00A86B",
        "lang": "fr",
        "icons": [
            {"src": static('img/pwa/icon-192.png'), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static('img/pwa/icon-512.png'), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static('img/pwa/icon-maskable-512.png'), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Mes bulletins", "short_name": "Bulletins", "url": portail['prefixe'] + 'bulletins/'},
            {"name": "Ma vie scolaire", "short_name": "Vie scol.", "url": portail['prefixe'] + 'vie-scolaire/'},
        ],
    }
    return JsonResponse(manifest)


def certificat_autorite(request):
    """Autorité de certification locale (clé publique, HTTPS local) à installer
    une fois sur les tablettes et téléphones ; 404 tant que le HTTPS n'est pas activé."""
    chemin = Path(settings.BASE_DIR) / 'certs' / 'yelen-ca.crt'
    if not chemin.is_file():
        raise Http404("HTTPS local non activé : aucune autorité à télécharger.")
    return FileResponse(chemin.open('rb'), content_type='application/x-x509-ca-cert',
                        as_attachment=True, filename='yelen-ca.crt')


@cache_control(max_age=86400, public=True)
def favicon(request):
    """`/favicon.ico` demandé d'office par les navigateurs : renvoie l'icône PNG de l'application
    (les gabarits principaux déclarent en plus l'icône SVG `img/favicon.svg`)."""
    return HttpResponseRedirect(static('img/pwa/icon-192.png'))


def pwa_icon(request, size):
    """Icône SVG de l'application PWA."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}">'
        f'<rect width="{size}" height="{size}" rx="{size // 5}" fill="#0A1628"/>'
        f'<text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" '
        f'font-family="Outfit,Arial,sans-serif" font-weight="700" '
        f'font-size="{size // 2}" fill="#00A86B">Y</text>'
        f'</svg>'
    )
    return HttpResponse(svg, content_type='image/svg+xml')


def pwa_service_worker(request, role='PARENT'):
    """Service Worker — cache le portail (parent : ``/sw.js`` ; élève : ``/sw-eleve.js``) pour un accès hors ligne."""
    portail = PORTAILS[role]
    racine = portail['prefixe']
    sw = (
        f"const CACHE='{portail['cache']}';\n"
        f"const PRECACHE=['{racine}','{racine}bulletins/','{racine}vie-scolaire/',"
        f"'{racine}cahier/','{racine}notifications/','/static/css/yelen.css','/static/js/pwa.js','/static/js/push.js'];\n"
        "self.addEventListener('install',e=>{"
        "e.waitUntil(caches.open(CACHE).then(c=>c.addAll(PRECACHE)).then(()=>self.skipWaiting()));});\n"
        "self.addEventListener('activate',e=>{"
        "e.waitUntil(caches.keys()"
        ".then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))"
        ".then(()=>self.clients.claim()));});\n"
        "self.addEventListener('fetch',e=>{"
        "if(e.request.method!=='GET')return;"
        "const u=new URL(e.request.url);"
        "if(u.pathname.startsWith('/accounts/')||u.pathname.startsWith('/api/'))return;"
        "e.respondWith(fetch(e.request).then(r=>{"
        "if(r.ok){const c=r.clone();caches.open(CACHE).then(ca=>ca.put(e.request,c));}"
        "return r;}).catch(()=>caches.match(e.request)"
        f".then(cached=>cached||caches.match('{racine}'))));}});\n"
        # Notifications push (core/push.py) : affichage, puis ouverture de la page du portail au toucher.
        "self.addEventListener('push',e=>{"
        "let d={};try{d=e.data?e.data.json():{};}catch(_){d={message:e.data?e.data.text():''};}"
        "e.waitUntil(self.registration.showNotification(d.titre||'YELEN SCHOOL',{"
        f"body:d.message||'',icon:'{static('img/pwa/icon-192.png')}',badge:'{static('img/pwa/icon-192.png')}',"
        f"tag:d.tag||'{portail['cache'].rsplit('-', 1)[0]}',renotify:true,data:{{url:d.url||'{racine}notifications/'}}}}));}});\n"
        "self.addEventListener('notificationclick',e=>{"
        "e.notification.close();"
        f"const url=(e.notification.data&&e.notification.data.url)||'{racine}';"
        "e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(liste=>{"
        f"const c=liste.find(w=>new URL(w.url).pathname.startsWith('{racine}'));"
        "if(c){return c.navigate(url).then(()=>c.focus()).catch(()=>clients.openWindow(url));}"
        "return clients.openWindow(url);}));});\n"
    )
    return HttpResponse(sw, content_type='application/javascript')
