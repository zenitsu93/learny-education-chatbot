/* Service worker Learny : l'interface reste disponible sans réseau. */
const CACHE = "learny-{{ version }}";
const FICHIERS = [{% for f in fichiers %}"{{ f|escapejs }}"{% if not forloop.last %},{% endif %}{% endfor %}];
const HORS_LIGNE = "{% url 'hors_ligne' %}";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FICHIERS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((cles) => Promise.all(cles.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // Fichiers statiques : cache d'abord (ils sont versionnés par le nom du cache).
  if (url.pathname.startsWith("{{ static_prefix }}") || FICHIERS.includes(url.pathname)) {
    e.respondWith(caches.match(req).then((r) => r || fetch(req).then((res) => {
      const copie = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copie));
      return res;
    })));
    return;
  }

  // Pages : réseau d'abord, dernière version connue sinon, page hors connexion en dernier recours.
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).then((res) => {
        const copie = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copie));
        return res;
      }).catch(() => caches.match(req).then((r) => r || caches.match(HORS_LIGNE)))
    );
  }
});
