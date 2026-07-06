// Minimal service worker: enables PWA installability and offline-tolerant
// navigation with a network-first, same-origin cache. It never touches the API
// origin (cross-origin requests pass straight through), so auth/media are
// unaffected.
const CACHE = "playhub-v1";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // leave API/media alone

  event.respondWith(
    fetch(req)
      .then((res) => {
        // Only cache clean, successful responses (not errors/redirects/opaque).
        if (res.ok && res.type === "basic") {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("/"))),
  );
});
