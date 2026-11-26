/* raqamliMuallim — oflayn paket: mavzu darslari, rasmlari va dars testlarini qurilmaga yuklash (serverda fayl saqlanmaydi).

   Sahifalar Cache Storage'dagi «rm-pack» keshiga yoziladi; internet yo'q paytda Service Worker avval shu keshga qaraydi.
   Ro'yxati — localStorage «rm-packs»: { <mavzu id>: { name, page, urls, bytes, tests, at, exp } }. Chiqishda hammasi tozalanadi.
   Dars testi oflayn topshirilsa, javoblar player.js navbatida turadi va internet tiklanganda serverda baholanadi. */
window.rmPacks = (function () {
  var CACHE = "rm-pack", KEY = "rm-packs";
  function all() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function save(p) { localStorage.setItem(KEY, JSON.stringify(p)); }
  function supported() { return "caches" in window && "serviceWorker" in navigator; }
  function token() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ""; }
  function post(url) {
    return fetch(url, { method: "POST", credentials: "same-origin", headers: { Accept: "application/json", "X-CSRFToken": token() } })
      .catch(function () { throw new Error(rmT("offlineShort")); })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok || !j.ok) throw new Error(j.error || rmT("badServer"));
          return j;
        });
      });
  }
  /* Faqat shu paketda bo'lgan manzillar o'chiriladi: rasm boshqa paketda ham bo'lishi mumkin */
  function drop(urls, exceptId) {
    var packs = all(), keep = {};
    Object.keys(packs).forEach(function (id) { if (id !== String(exceptId)) packs[id].urls.forEach(function (u) { keep[u] = 1; }); });
    return caches.open(CACHE).then(function (c) {
      return Promise.all(urls.filter(function (u) { return !keep[u]; }).map(function (u) { return c.delete(u); }));
    });
  }
  function download(id, onProgress) {
    var done = [], man, old = all()[id];
    if (!supported()) return Promise.reject(new Error(rmT("packUnsupported")));
    return post("/api/oflayn/" + id).then(function (m) {
      man = m;
      return caches.open(CACHE);
    }).then(function (c) {
      var bytes = 0;
      return man.urls.reduce(function (chain, u, i) {
        return chain.then(function () {
          return fetch(u, { credentials: "same-origin", cache: "no-store", headers: { "X-RM-Pack": "1" } })
            .catch(function () { throw new Error(rmT("offlineShort")); });
        }).then(function (r) {
          if (!r.ok || r.redirected) throw new Error(rmT("packFailed"));
          return r.clone().blob().then(function (b) {
            bytes += b.size;
            if (bytes > man.limit) throw new Error(rmT("packBig"));
            return c.put(u, r);
          });
        }).then(function () { done.push(u); onProgress(Math.round((i + 1) / man.urls.length * 100)); });
      }, Promise.resolve()).then(function () { return bytes; });
    }).then(function (bytes) {
      var packs = all();
      packs[id] = { name: man.name, page: man.page, urls: man.urls, bytes: bytes, tests: man.tests, lessons: man.lessons,
                    at: Date.now(), exp: Date.now() + man.days * 864e5 };
      save(packs);
      // Eski paketdagi, endi kerak bo'lmagan sahifalar (topshirilgan testlar)
      var gone = old ? old.urls.filter(function (u) { return man.urls.indexOf(u) === -1; }) : [];
      if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(function () {});
      return drop(gone, null).then(function () { return packs[id]; });
    }).catch(function (e) {
      // Yarim yuklangan paket qolmaydi; avvalgisi bo'lsa, u tegilmaydi
      var extra = done.filter(function (u) { return !old || old.urls.indexOf(u) === -1; });
      return drop(extra, old ? null : id).then(function () {
        throw e && e.name === "QuotaExceededError" ? new Error(rmT("packNoSpace")) : e;
      });
    });
  }
  function remove(id) {
    var packs = all(), p = packs[id];
    if (!p) return Promise.resolve();
    return drop(p.urls, id).then(function () {
      delete packs[id];
      save(packs);
      post("/api/oflayn/" + id + "/ochirish").catch(function () {});     // internet yo'q — server muddati o'tgach o'zi o'chiradi
    });
  }
  return { all: all, supported: supported, download: download, remove: remove,
           size: function (b) { return b < 1048576 ? Math.max(1, Math.round(b / 1024)) + " KB" : (b / 1048576).toFixed(1) + " MB"; },
           date: function (ms) { var d = new Date(ms), p = function (n) { return String(n).padStart(2, "0"); }; return p(d.getDate()) + "." + p(d.getMonth() + 1) + "." + d.getFullYear(); } };
})();

/* Mavzu va dars sahifasidagi karta */
window.rmPack = function (id) {
  return {
    pack: null, busy: false, pct: 0, error: "", ok: rmPacks.supported(),
    init: function () { this.pack = rmPacks.all()[id] || null; },
    get expired() { return !!this.pack && this.pack.exp < Date.now(); },
    get info() {
      return this.pack ? rmT("packInfo", { size: rmPacks.size(this.pack.bytes), lessons: this.pack.lessons, tests: this.pack.tests,
                                           date: rmPacks.date(this.pack.exp) }) : "";
    },
    download: function () {
      var self = this;
      if (this.busy) return;
      this.busy = true; this.error = ""; this.pct = 0;
      rmPacks.download(id, function (p) { self.pct = p; }).then(function (p) { self.pack = p; rmToast(rmT("packReady")); })
        .catch(function (e) { self.error = e.message; })
        .finally(function () { self.busy = false; });
    },
    remove: function () {
      var self = this;
      if (!confirm(rmT("packRemove"))) return;
      rmPacks.remove(id).then(function () { self.pack = null; });
    }
  };
};

/* «Oflayn darslar» sahifasi */
window.rmPackList = function () {
  return {
    items: [], ok: rmPacks.supported(),
    init: function () { this.load(); },
    load: function () {
      var p = rmPacks.all();
      this.items = Object.keys(p).map(function (id) {
        return Object.assign({ id: id, expired: p[id].exp < Date.now() }, p[id],
          { info: rmT("packInfo", { size: rmPacks.size(p[id].bytes), lessons: p[id].lessons, tests: p[id].tests, date: rmPacks.date(p[id].exp) }) });
      }).sort(function (a, b) { return b.at - a.at; });
    },
    total: function () { return rmPacks.size(this.items.reduce(function (s, x) { return s + x.bytes; }, 0)); },
    remove: function (id) {
      var self = this;
      if (!confirm(rmT("packRemove"))) return;
      rmPacks.remove(id).then(function () { self.load(); });
    }
  };
};

/* Paketdagi dars sahifasi: keyingi dars shu qurilmada joriy dars testi yakunlangach ochiladi (natijani server keyin baholaydi) */
(function () {
  "use strict";
  function gate() {
    var parts = Array.prototype.slice.call(document.querySelectorAll("[data-off-part]"));
    if (!parts.length || !window.RMPlayer) return;
    Promise.all(parts.map(function (el) {
      return el.dataset.offOk || !el.dataset.offTest ? true : RMPlayer.finishedHere(el.dataset.offTest);
    })).then(function (fin) {
      var open = true, closed = 0;
      parts.forEach(function (el, i) {
        el.hidden = !open;
        var link = document.querySelector('[data-toc-link="' + el.id + '"]');
        if (link) link.parentElement.hidden = !open;
        if (!open) closed++;
        if (open && fin[i] && el.dataset.offTest && !el.dataset.offOk) {
          el.querySelectorAll("[data-off-start]").forEach(function (a) { a.hidden = true; });
          el.querySelectorAll("[data-off-sent]").forEach(function (s) { s.hidden = false; });
        }
        if (!fin[i]) open = false;
      });
      var note = document.querySelector("[data-off-locked]");
      if (note) { note.hidden = !closed; note.querySelector("[data-off-n]").textContent = closed; }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", gate); else gate();
  window.addEventListener("pageshow", gate);
})();
