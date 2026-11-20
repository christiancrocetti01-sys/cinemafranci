// Service worker: fa funzionare l'app anche offline (con gli ultimi orari scaricati).
const VERSIONE = "cf-v1";
const GUSCIO = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "icons/icon.svg", "icons/icon-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSIONE).then((c) => c.addAll(GUSCIO)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((chiavi) => Promise.all(chiavi.filter((k) => k !== VERSIONE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const locale = url.origin === location.origin;

  // Dati e pagine dell'app: prima la rete (orari freschi), se offline la copia salvata.
  if (locale && (url.pathname.endsWith(".json") || req.mode === "navigate" || /\.(js|css|html)$/.test(url.pathname))) {
    e.respondWith(fetch(req).then((r) => {
      if (r.ok) { const copia = r.clone(); caches.open(VERSIONE).then((c) => c.put(req, copia)); }
      return r;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then((r) => r || caches.match("index.html"))));
    return;
  }

  // Locandine, font, icone: prima la cache, poi la rete.
  if (locale || /comingsoon\.it|fonts\.(googleapis|gstatic)\.com|teatrocinemaitalia\.it|ilgirone\.it/.test(url.hostname)) {
    e.respondWith(caches.match(req).then((c) => c || fetch(req).then((r) => {
      if (r.ok || r.type === "opaque") { const copia = r.clone(); caches.open(VERSIONE).then((cc) => cc.put(req, copia)); }
      return r;
    })));
  }
});
