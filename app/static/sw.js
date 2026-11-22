/* raqamliMuallim — Service Worker (PWA, oflayn rejim).
   Strategiya: avval tarmoq, bo'lmasa kesh — yangilangan fayllar darhol ko'rinadi, internet yo'q bo'lsa keshdan.

   Nima keshlanadi:
   - STATIC: /static/ fayllari (CSS, JS, shrift, ikonkalar) — soni cheklangan, shuning uchun limitsiz;
   - PAGES: faqat o'qituvchi sahifalari (/app/, /test/) — oflayn ochish uchun. Eng ko'pi PAGE_LIMIT ta,
     eskisi o'chiriladi. Ekspert/admin panellari, kirish sahifalari va /api/ javoblari keshlanmaydi
     (shaxsiy yoki tez o'zgaradigan ma'lumot). Chiqishda (/chiqish) server Clear-Site-Data bilan hammasini tozalaydi. */
var VERSION = "rm-v5";
var STATIC = VERSION + "-static", PAGES = VERSION + "-pages", PAGE_LIMIT = 50;
var CORE = [
  "/static/css/app.css",
  "/static/css/utilities.css",
  "/static/js/core.js",
  "/static/js/learner.js",
  "/static/js/player.js",
  "/static/vendor/alpine-3.14.1.min.js",
  "/static/fonts/inter-latin-wght.woff2",
  "/static/icon.svg",
  "/static/icons/icon-192.png",
  "/static/icons/apple-touch-icon.png",
  "/static/manifest.webmanifest"
];
var OFFLINE = "/app/oflayn";

self.addEventListener("install", function (e) {
  e.waitUntil(Promise.all([
    caches.open(STATIC).then(function (c) { return c.addAll(CORE); }),
    caches.open(PAGES).then(function (c) { return c.add(OFFLINE); })
  ]).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== STATIC && k !== PAGES; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

// Sahifalar keshi PAGE_LIMIT dan oshsa — eng eski yozuvlar o'chiriladi (oflayn sahifa saqlanib qoladi)
function trim(cache) {
  return cache.keys().then(function (keys) {
    var extra = keys.filter(function (k) { return new URL(k.url).pathname !== OFFLINE; });
    return Promise.all(extra.slice(0, Math.max(0, extra.length - PAGE_LIMIT)).map(function (k) { return cache.delete(k); }));
  });
}

function bucket(req, url) {
  if (url.pathname.indexOf("/static/") === 0) return STATIC;
  if (req.mode === "navigate" && /^\/(app|test)\//.test(url.pathname)) return PAGES;
  return null;   // qolganlari (panel, kirish, /api/) — keshlanmaydi
}

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== location.origin || url.pathname.indexOf("/api/") === 0) return;
  var name = bucket(req, url);

  e.respondWith(
    fetch(req).then(function (res) {
      var noStore = /no-store/.test(res.headers.get("Cache-Control") || "");
      if (name && res.ok && res.type === "basic" && !noStore) {
        var copy = res.clone();
        caches.open(name).then(function (c) {
          return c.put(req, copy).then(function () { if (name === PAGES) return trim(c); });
        });
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        if (hit) return hit;
        if (req.mode === "navigate") return caches.match(OFFLINE);
        return Response.error();
      });
    })
  );
});
