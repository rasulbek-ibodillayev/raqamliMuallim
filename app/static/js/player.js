/* raqamliMuallim — test pleyer yadrosi (vanilla JS, Alpine'ga bog'liq emas).

   Vazifasi:
   - Har bir urinish (sessiya) IndexedDB'da saqlanadi: javoblar, joriy savol, belgilangan savollar, taymer.
     Sahifa yangilansa yoki brauzer yopilsa ham test uzilgan joyidan davom etadi.
   - Taymer "qolgan soniya" emas, "tugash vaqti" (deadline) sifatida saqlanadi: yangilash vaqtni qaytarmaydi.
   - Har bir javob avval qurilmaga, keyin "outbox" navbatiga yoziladi. Navbat internet bo'lganda serverga
     yuboriladi (online hodisasi, sahifa ochilishi, har 15 soniya). Server javobni urinish UUID'i va savol
     tartibi bo'yicha qabul qiladi, shuning uchun qayta yuborish xavfsiz (idempotent).
   - IndexedDB yo'q bo'lsa (ba'zi maxfiy rejimlar) localStorage'ga, u ham bo'lmasa xotiraga tushadi.

   Ishlatish:
     const s = await RMPlayer.open({ id: "exam:asosiy", kind: "exam", total: 35, duration: 7200 });
     s.answer(3, 1, 4200);  s.setPos(4);  s.remaining();  await s.finish();
     RMPlayer.on(function (st) { ... st.state: "idle" | "saving" | "local" | "synced" | "error", st.pending });
*/
(function () {
  "use strict";

  var DB_NAME = "rm-player", DB_VER = 1, API = "/api/urinish/";
  var listeners = [], status = { state: "idle", pending: 0, online: navigator.onLine };
  var forceOffline = false, syncing = false, syncTimer = null, retryMs = 2000;

  /* ---------- saqlash qatlami ---------- */
  function idbStore() {
    var dbp = new Promise(function (res, rej) {
      var r = indexedDB.open(DB_NAME, DB_VER);
      r.onupgradeneeded = function () {
        var db = r.result;
        if (!db.objectStoreNames.contains("sessions")) db.createObjectStore("sessions", { keyPath: "id" });
        if (!db.objectStoreNames.contains("outbox")) db.createObjectStore("outbox", { keyPath: "key" });
      };
      r.onsuccess = function () { res(r.result); };
      r.onerror = function () { rej(r.error); };
    });
    function tx(store, mode, fn) {
      return dbp.then(function (db) {
        return new Promise(function (res, rej) {
          var t = db.transaction(store, mode), os = t.objectStore(store), out = fn(os);
          t.oncomplete = function () { res(out && "result" in out ? out.result : undefined); };
          t.onerror = function () { rej(t.error); };
        });
      });
    }
    return {
      get: function (s, k) { return tx(s, "readonly", function (os) { return os.get(k); }); },
      // JSON nusxa: Alpine Proxy obyektlarini IndexedDB saqlay olmaydi (DataCloneError)
      put: function (s, v) { var plain = JSON.parse(JSON.stringify(v)); return tx(s, "readwrite", function (os) { os.put(plain); }); },
      del: function (s, k) { return tx(s, "readwrite", function (os) { os.delete(k); }); },
      all: function (s) { return tx(s, "readonly", function (os) { return os.getAll(); }); },
      ready: dbp
    };
  }

  function kvStore(backend) {
    // localStorage yoki xotira: { "rm-p:<store>": { key: value } }
    var mem = {};
    function load(s) {
      if (!backend) return mem[s] || (mem[s] = {});
      try { return JSON.parse(backend.getItem("rm-p:" + s)) || {}; } catch (e) { return {}; }
    }
    function save(s, o) { if (backend) backend.setItem("rm-p:" + s, JSON.stringify(o)); else mem[s] = o; }
    function keyOf(s, v) { return s === "sessions" ? v.id : v.key; }
    return {
      get: function (s, k) { return Promise.resolve(load(s)[k]); },
      put: function (s, v) { var o = load(s); o[keyOf(s, v)] = v; save(s, o); return Promise.resolve(); },
      del: function (s, k) { var o = load(s); delete o[k]; save(s, o); return Promise.resolve(); },
      all: function (s) { var o = load(s); return Promise.resolve(Object.keys(o).map(function (k) { return o[k]; })); },
      ready: Promise.resolve()
    };
  }

  var store = (function () {
    try {
      if (window.indexedDB) { var s = idbStore(); s.ready.catch(function () {}); return s; }
    } catch (e) {}
    try { localStorage.setItem("rm-p:t", "1"); localStorage.removeItem("rm-p:t"); return kvStore(localStorage); } catch (e) {}
    return kvStore(null);
  })();
  // IndexedDB ochilmasa (masalan, Firefox maxfiy rejimi) — localStorage'ga o'tamiz
  store.ready.catch(function () {
    try { store = kvStore(localStorage); } catch (e) { store = kvStore(null); }
  });

  /* ---------- holat va hodisalar ---------- */
  function emit(patch) {
    for (var k in patch) status[k] = patch[k];
    listeners.forEach(function (fn) { try { fn(status); } catch (e) {} });
    document.dispatchEvent(new CustomEvent("rm-player", { detail: status }));
  }
  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0; return (c === "x" ? r : (r & 3 | 8)).toString(16);
    });
  }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ""; }

  /* ---------- sessiya ---------- */
  function Session(data) { this.d = data; }
  Session.prototype = {
    get uuid() { return this.d.uuid; },
    get answers() { return this.d.answers; },
    get pos() { return this.d.pos; },
    get flagged() { return this.d.flagged; },
    get paused() { return !!this.d.pausedAt; },
    get finished() { return this.d.status !== "in_progress"; },
    persist: function () { return store.put("sessions", this.d); },
    answer: function (pos, value, timeMs) {
      var empty = value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length);
      if (this.finished) return Promise.resolve();
      if (empty) delete this.d.answers[pos];
      else this.d.answers[pos] = { v: value, t: timeMs || 0, at: Date.now() };
      emit({ state: "saving" });
      var self = this;
      return this.persist().then(function () {
        return self.d.local ? null : store.put("outbox", {
          key: self.d.uuid + ":" + pos, uuid: self.d.uuid, kind: self.d.kind, op: "answer",
          pos: pos, v: empty ? null : value, t: timeMs || 0, at: Date.now()
        });
      }).then(function () { return refreshPending(); }).then(function () {
        emit({ state: status.pending ? "local" : "synced" });
        scheduleSync(300);
      }).catch(function () { emit({ state: "error" }); });
    },
    setPos: function (p) { this.d.pos = p; return this.persist(); },
    toggleFlag: function (p) {
      var i = this.d.flagged.indexOf(p);
      if (i === -1) this.d.flagged.push(p); else this.d.flagged.splice(i, 1);
      return this.persist();
    },
    remaining: function () {
      if (!this.d.deadline) return null;
      var now = this.d.pausedAt || Date.now();
      return Math.max(0, Math.round((this.d.deadline - now) / 1000));
    },
    pause: function () { if (!this.d.pausedAt) { this.d.pausedAt = Date.now(); return this.persist(); } return Promise.resolve(); },
    resume: function () {
      if (this.d.pausedAt) { this.d.deadline += Date.now() - this.d.pausedAt; this.d.pausedAt = null; return this.persist(); }
      return Promise.resolve();
    },
    /* Yakunlash: navbatga "finish" yoziladi va darhol yuborishga harakat qilinadi.
       Natija: { synced: true, result_url } yoki { synced: false } (internet yo'q — keyin yuboriladi) */
    finish: function () {
      var self = this;
      this.d.status = "submitted"; this.d.finishedAt = Date.now();
      return this.persist().then(function () {
        if (self.d.local) return { synced: true, result_url: null };
        return store.put("outbox", { key: self.d.uuid + ":finish", uuid: self.d.uuid, kind: self.d.kind, op: "finish", at: Date.now() })
          .then(function () { return RMPlayer.sync(); })
          .then(function () { return store.get("outbox", self.d.uuid + ":finish"); })
          .then(function (left) { return left ? { synced: false } : { synced: true, result_url: self.d.resultUrl || null }; });
      });
    },
    discard: function () { return store.del("sessions", this.d.id); }
  };

  /* ---------- sinxronlash ---------- */
  function refreshPending() {
    return store.all("outbox").then(function (items) { emit({ pending: items.length }); return items; });
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "Accept": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { return { status: r.status, body: j }; });
    });
  }

  function scheduleSync(ms) { clearTimeout(syncTimer); syncTimer = setTimeout(function () { RMPlayer.sync(); }, ms); }

  function syncOnce() {
    if (forceOffline || !navigator.onLine) { emit({ online: false }); return refreshPending(); }
    return refreshPending().then(function (items) {
      if (!items.length) return;
      // Urinishlar bo'yicha guruhlaymiz: avval javoblar, keyin yakunlash
      var by = {};
      items.forEach(function (it) { (by[it.uuid] = by[it.uuid] || { answers: [], finish: null, kind: it.kind }); });
      items.forEach(function (it) { if (it.op === "finish") by[it.uuid].finish = it; else by[it.uuid].answers.push(it); });
      var chain = Promise.resolve();
      Object.keys(by).forEach(function (u) {
        var g = by[u];
        chain = chain.then(function () {
          if (!g.answers.length) return;
          return post(API + u + "/javoblar", {
            kind: g.kind, answers: g.answers.map(function (a) { return { pos: a.pos, v: a.v, t: a.t, at: a.at }; })
          }).then(function (r) {
            // 409 — urinish serverda allaqachon yakunlangan: bu javoblarni qayta yuborishdan foyda yo'q
            if (r.status === 200 || r.status === 409) {
              return Promise.all(g.answers.map(function (a) {
                // Yuborilayotganda yangi javob yozilgan bo'lsa, uni o'chirmaymiz
                return store.get("outbox", a.key).then(function (cur) { if (cur && cur.at === a.at) return store.del("outbox", a.key); });
              }));
            }
            throw new Error("HTTP " + r.status);
          });
        }).then(function () {
          if (!g.finish) return;
          return post(API + u + "/yakunlash", { kind: g.kind }).then(function (r) {
            if (r.status !== 200 && r.status !== 409) throw new Error("HTTP " + r.status);
            return Promise.all([
              store.del("outbox", g.finish.key),
              store.all("sessions").then(function (ss) {
                var s = ss.filter(function (x) { return x.uuid === u; })[0];
                if (s) { s.resultUrl = r.body.result_url || null; s.syncedAt = Date.now(); return store.put("sessions", s); }
              })
            ]);
          });
        });
      });
      return chain;
    }).then(function () { retryMs = 2000; emit({ online: true }); return refreshPending(); })
      .then(function (left) { emit({ state: left.length ? "local" : (status.state === "idle" ? "idle" : "synced") }); });
  }

  var RMPlayer = {
    /* Sessiyani ochish: bor bo'lsa tiklanadi, yo'q bo'lsa yaratiladi.
       opts: id, kind, total, duration (soniya, ixtiyoriy), local (true — serverga yubormaslik, namunalar uchun),
             seed ({pos: value} — yangi sessiya uchun boshlang'ich javoblar), restart (true — eskisini o'chirish) */
    open: function (opts) {
      return store.ready.catch(function () {}).then(function () { return store.get("sessions", opts.id); }).then(function (d) {
        // Yakunlangan urinish qayta ochilmaydi: yangisi boshlanadi (eskisining navbatdagi javoblari baribir yuboriladi)
        if (d && (opts.restart || d.status !== "in_progress")) d = null;
        if (!d) {
          d = {
            id: opts.id, uuid: uuid(), kind: opts.kind, total: opts.total, status: "in_progress",
            startedAt: Date.now(), deadline: opts.duration ? Date.now() + opts.duration * 1000 : null,
            pausedAt: null, pos: 0, answers: {}, flagged: [], local: !!opts.local
          };
          if (opts.seed) Object.keys(opts.seed).forEach(function (k) { d.answers[k] = { v: opts.seed[k], t: 0, at: 0 }; });
          return store.put("sessions", d).then(function () { return new Session(d); });
        }
        return new Session(d);
      }).then(function (s) { refreshPending().then(function (it) { if (it.length) emit({ state: "local" }); }); return s; });
    },
    sync: function () {
      if (syncing) return Promise.resolve();
      syncing = true;
      return syncOnce().catch(function () {
        emit({ state: "local" });
        retryMs = Math.min(retryMs * 2, 60000);
        scheduleSync(retryMs);
      }).then(function () { syncing = false; });
    },
    on: function (fn) { listeners.push(fn); fn(status); return function () { listeners = listeners.filter(function (f) { return f !== fn; }); }; },
    status: function () { return status; },
    /* Namunaviy "oflayn" ekran uchun: tarmoqni yo'q deb hisoblash */
    setForceOffline: function (v) { forceOffline = !!v; emit({ online: !v && navigator.onLine }); if (!v) RMPlayer.sync(); },
    /* Forma qiymatini o'qish/yozish (savol turi bo'yicha) */
    readForm: function (form, kind) {
      if (kind === "yopiq") { var r = form.querySelector('input[type=radio]:checked'); return r ? +r.value : null; }
      if (kind === "kop") return [].map.call(form.querySelectorAll('input[type=checkbox]:checked'), function (c) { return +c.value; });
      if (kind === "moslash") {
        var sel = [].map.call(form.querySelectorAll("select"), function (s) { return s.value === "" ? null : +s.value; });
        return sel.every(function (x) { return x === null; }) ? null : sel;
      }
      if (kind === "ochiq") { var i = form.querySelector("input[data-answer]"); return i ? i.value.trim() : null; }
      return null;
    },
    writeForm: function (form, kind, v) {
      if (kind === "yopiq") [].forEach.call(form.querySelectorAll('input[type=radio]'), function (r) { r.checked = +r.value === v; });
      else if (kind === "kop") [].forEach.call(form.querySelectorAll('input[type=checkbox]'), function (c) { c.checked = (v || []).indexOf(+c.value) !== -1; });
      else if (kind === "moslash") [].forEach.call(form.querySelectorAll("select"), function (s, i) { s.value = v && v[i] !== null && v[i] !== undefined ? String(v[i]) : ""; });
      else if (kind === "ochiq") { var i = form.querySelector("input[data-answer]"); if (i) { i.value = v || ""; i.dispatchEvent(new Event("input")); } }
    }
  };

  window.RMPlayer = RMPlayer;
  window.addEventListener("online", function () { emit({ online: true }); RMPlayer.sync(); });
  window.addEventListener("offline", function () { emit({ online: false }); });
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible") RMPlayer.sync(); });
  setInterval(function () { if (status.pending) RMPlayer.sync(); }, 15000);
  // Istalgan sahifa ochilganda navbatda qolgan javoblar yuboriladi
  RMPlayer.sync();
})();
