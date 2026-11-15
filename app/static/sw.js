/* raqamliMuallim — Service Worker (PWA, oflayn rejim).
   Strategiya: avval tarmoq, bo'lmasa kesh. Shu sababli yangilangan fayllar darhol ko'rinadi,
   internet yo'q bo'lganda esa oxirgi ochilgan sahifalar va asosiy fayllar keshdan beriladi. */
var VERSION = "rm-v1";
var CORE = [
  "/static/css/app.css",
  "/static/js/app.js",
  "/static/vendor/alpine-3.14.1.min.js",
  "/static/fonts/inter-latin-wght.woff2",
  "/static/icon.svg",
  "/static/manifest.webmanifest",
  "/app/oflayn"
];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) { return c.addAll(CORE); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== VERSION; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return; // tashqi manbalarga (Google Fonts) tegmaymiz

  e.respondWith(
    fetch(req).then(function (res) {
      if (res.ok) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        if (hit) return hit;
        if (req.mode === "navigate") return caches.match("/app/oflayn");
        return Response.error();
      });
    })
  );
});
