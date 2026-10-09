/*
 * Service worker for the installable app (F9.8.2).
 *
 * Only the app itself is cached: built assets, which are content-hashed and so never
 * change under one name, and an offline page. Pages are always fetched from the network
 * first, so a deploy reaches an installed copy on its next launch. API responses are
 * never touched — the API is on another origin, and receipts and figures are financial
 * data that must not linger on the device.
 */
const SHELL = "budget-shell-v1";
const ASSETS = "budget-assets";
const OFFLINE_URL = "/offline.html";
const MAX_ASSETS = 60;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL)
      .then((cache) => cache.addAll([OFFLINE_URL, "/icon.svg"]))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== SHELL && key !== ASSETS).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

async function trim(cache) {
  const keys = await cache.keys();
  await Promise.all(
    keys.slice(0, Math.max(keys.length - MAX_ASSETS, 0)).map((k) => cache.delete(k)),
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  if (url.pathname === OFFLINE_URL || url.pathname === "/icon.svg") {
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
    return;
  }

  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(
      caches.open(ASSETS).then(async (cache) => {
        const cached = await cache.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        if (response.ok) {
          await cache.put(request, response.clone());
          void trim(cache);
        }
        return response;
      }),
    );
  }
});
