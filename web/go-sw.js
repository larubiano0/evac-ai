// Service worker for the resident "Go" view (/go). Keeps the page, Leaflet, the map tiles around you and the
// flood overlay in the browser cache so /go still opens and shows your last route when the network drops.
// API answers (POST) cannot go in the Cache API; go.html keeps the last one in localStorage instead.
const SHELL = "go-shell-v1", TILES = "go-tiles-v1", MAX_TILES = 600;
const LEAFLET = ["https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => Promise.all([
    c.add("/go"),
    ...LEAFLET.map(u => fetch(u, { mode: "cors" }).then(r => c.put(u, r))),
  ])).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith("go-") && k !== SHELL && k !== TILES)
    .map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// network first, falling back to the cache (with a time limit, so a dead network doesn't hang the page)
async function networkFirst(req, key, cacheName, ms) {
  const c = await caches.open(cacheName);
  try {
    const r = await Promise.race([fetch(req), new Promise((_, no) => setTimeout(() => no(new Error("slow")), ms))]);
    if (r.ok) c.put(key, r.clone());
    return r;
  } catch (err) {
    const hit = await c.match(key, { ignoreSearch: key === "/go" });
    if (hit) return hit;
    throw err;
  }
}
async function cacheFirst(req, cacheName) {
  const c = await caches.open(cacheName);
  const hit = await c.match(req.url);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok || r.type === "opaque") {
    c.put(req.url, r.clone());
    if (cacheName === TILES) c.keys().then(ks => ks.length > MAX_TILES && Promise.all(ks.slice(0, ks.length - MAX_TILES).map(k => c.delete(k))));
  }
  return r;
}

self.addEventListener("fetch", e => {
  const req = e.request, u = new URL(req.url);
  if (req.method !== "GET") return;                                     // API POSTs go straight to the network
  if (req.mode === "navigate" && u.pathname === "/go") e.respondWith(networkFirst(req, "/go", SHELL, 4000));
  else if (u.hostname === "tile.openstreetmap.org") e.respondWith(cacheFirst(req, TILES));
  else if (u.hostname === "unpkg.com") e.respondWith(cacheFirst(req, SHELL));
  else if (u.pathname === "/api/predict/p.png") e.respondWith(networkFirst(req, req.url, SHELL, 8000));
  else if (u.pathname === "/api/predict/options") e.respondWith(networkFirst(req, req.url, SHELL, 4000));
});
