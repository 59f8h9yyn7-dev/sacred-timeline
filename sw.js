// Sacred Timeline — offline cache. Cambiare VERSION a ogni aggiornamento dell'app.
const VERSION = 'v9';
const CORE = `core-${VERSION}`, RUN = 'run';
const PRE = ['./', 'index.html', 'manifest.webmanifest', 'vendor/three.module.min.js', 'data/map.json', 'data/chrono.json', 'data/cards.json', 'sky/sky.json', 'icons/icon-192.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CORE).then(c => Promise.all(PRE.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('core-') && k !== CORE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
const fresh = (req, ms) => new Promise((ok, no) => { const t = setTimeout(() => no('timeout'), ms); fetch(req).then(r => { clearTimeout(t); ok(r); }, e => { clearTimeout(t); no(e); }); });
self.addEventListener('fetch', e => {
  const r = e.request; if (r.method !== 'GET') return;
  const u = new URL(r.url); if (u.origin !== location.origin) return;
  const path = u.pathname, soft = /\/(data\/|index\.html$|sw\.js$)|\/$/.test(path);
  if (soft) {
    // pagina e dati: prima la rete (aggiornamenti subito), se lenta o assente la copia salvata
    e.respondWith(fresh(new Request(r.url, { cache: 'no-store', credentials: 'same-origin' }), 6000).then(res => { if (res.ok) { const cp = res.clone(); caches.open(CORE).then(c => c.put(r, cp)); } return res; }).catch(() => caches.match(r, { ignoreSearch: true }).then(m => m || fetch(r))));
  } else {
    // immagini, cielo, motore 3D: prima la copia salvata (le foto senza estensione ricevono il tipo giusto)
    const typed = res => !/\/_blob\/[0-9a-f]+$/.test(path) || !res.ok ? res : res.arrayBuffer().then(b => { const h = new Uint8Array(b.slice(0, 12)), t = h[0] === 0xFF && h[1] === 0xD8 ? 'image/jpeg' : h[0] === 0x89 && h[1] === 0x50 ? 'image/png' : h[8] === 0x57 && h[9] === 0x45 ? 'image/webp' : (h[4] === 0x66 && h[5] === 0x74 ? 'image/avif' : 'application/octet-stream'); return new Response(b, { status: 200, headers: { 'Content-Type': t } }); });
    e.respondWith(caches.match(r, { ignoreSearch: true }).then(m => m || fetch(r).then(typed).then(res => { if (res.ok && res.status === 200) { const cp = res.clone(); caches.open(RUN).then(c => c.put(r, cp)); } return res; })));
  }
});
