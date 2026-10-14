/* Service worker for 관리자 서식함. Generated into sw.js by build.py; edit this template. */
const VERSION = '2026.10.14-5';
const PREFIX = 'jangrye-app-';
const CACHE = PREFIX + VERSION;
const FONT_CACHE = 'seosik-fonts-v1';
const CORE = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/gukhwa-192.png",
  "./icons/gukhwa-512.png",
  "./icons/gukhwa-apple-180.png"
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(CORE.map((u) => new Request(u, { cache: 'reload' }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith(PREFIX) && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

const timeout = (ms) => new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms));

// App files: always try the network first so a new version shows up on the next open;
// fall back to the saved copy when offline or very slow (funeral-hall basements).
async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  const url = new URL(request.url);
  url.search = '';
  // each page keeps its own saved copy; the bare folder address is the main page
  const key = url.pathname.endsWith('/') ? new URL('index.html', url).href : url.href;
  try {
    const res = await Promise.race([fetch(url.href, { cache: 'no-cache', credentials: 'same-origin' }), timeout(4000)]);
    if (res && res.ok) cache.put(key, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(key);
    if (hit) return hit;
    if (request.mode === 'navigate') {
      const home = await cache.match(new URL('./index.html', self.registration.scope).href);
      if (home) return home;
    }
    return fetch(request);
  }
}

// Fonts: serve the saved copy immediately, refresh it in the background.
async function staleWhileRevalidate(request) {
  const cache = await caches.open(FONT_CACHE);
  const hit = await cache.match(request);
  const net = fetch(request)
    .then((res) => { if (res && (res.ok || res.type === 'opaque')) cache.put(request, res.clone()); return res; })
    .catch(() => null);
  return hit || (await net) || Response.error();
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === self.location.origin) {
    if (url.pathname.endsWith('/version.json')) return; // always live
    if (!url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
    event.respondWith(networkFirst(req));
  } else if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(staleWhileRevalidate(req));
  }
});
