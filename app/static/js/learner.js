/* raqamliMuallim — o'qituvchi qobig'i: menyu va qidiruv, ilovani o'rnatish, dam olish taymeri, joriy mavzu (layouts/app, focus, exam) */

/* AI tutor suhbati qurilmada (localStorage) saqlanadi.
   Tozalanadi: yangi mavzu boshlanganda (rm-current-topic o'zgarsa) yoki yozilganiga 24 soat bo'lganda. */
window.rmTutorStore = (function () {
  var KEY = "rm-tutor-chat", TTL = 24 * 3600 * 1000;
  function read() {
    try {
      var d = JSON.parse(localStorage.getItem(KEY) || "null");
      if (!d || !Array.isArray(d.msgs)) return null;
      if (Date.now() - d.savedAt > TTL) { localStorage.removeItem(KEY); return null; }   // 24 soat o'tdi
      return d;
    } catch (e) { return null; }
  }
  return {
    load: function (topic) {
      var d = read();
      if (d && topic && d.topic !== topic) { this.clear(); return null; }                   // boshqa mavzu
      return d;
    },
    save: function (topic, msgs) {
      // savedAt — birinchi yozilgan vaqt: 24 soat shundan hisoblanadi
      var d = read(), at = d && d.topic === topic ? d.savedAt : Date.now();
      try { localStorage.setItem(KEY, JSON.stringify({ topic: topic, savedAt: at, msgs: msgs })); } catch (e) {}
    },
    clear: function () { try { localStorage.removeItem(KEY); } catch (e) {} }
  };
})();

/* PWA o'rnatish taklifi.
   Android/desktop Chrome: brauzerning beforeinstallprompt hodisasi saqlanadi va tugma bosilganda ko'rsatiladi.
   iPhone/iPad Safari: bunday hodisa yo'q, shuning uchun «Ulashish → Bosh ekranga» yo'riqnomasi chiqadi.
   Namunada ?pwa=1 (tugma) yoki ?pwa=ios (yo'riqnoma) bilan majburan ko'rsatish mumkin. */
window.rmDeferredInstall = null;
window.addEventListener("beforeinstallprompt", function (e) {
  e.preventDefault();
  window.rmDeferredInstall = e;
  document.dispatchEvent(new CustomEvent("rm-installable"));
});
window.addEventListener("appinstalled", function () {
  window.rmDeferredInstall = null;
  document.dispatchEvent(new CustomEvent("rm-installed"));
});
window.rmInstall = function (opts) {
  opts = opts || {};
  var ua = navigator.userAgent || "";
  var force = new URLSearchParams(location.search).get("pwa");
  var isIOS = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  function dismissed() {
    try { return Number(localStorage.getItem("rm-install-later") || 0) > Date.now(); } catch (e) { return false; }
  }
  return {
    canPrompt: !!window.rmDeferredInstall || force === "1",
    ios: (isIOS && !standalone) || force === "ios",
    installed: standalone && !force,
    hidden: !force && !!opts.dismissible && dismissed(),
    steps: false,
    get visible() { return !this.installed && !this.hidden && (this.canPrompt || this.ios); },
    install: function () {
      var self = this, e = window.rmDeferredInstall;
      if (this.ios) { this.steps = !this.steps; return; }
      if (!e) { window.rmToast && window.rmToast(rmT("installHint")); return; }
      e.prompt();
      e.userChoice.then(function (r) { if (r.outcome === "accepted") self.installed = true; window.rmDeferredInstall = null; });
    },
    later: function () {
      this.hidden = true;
      // 14 kun davomida qayta ko'rsatmaymiz
      try { localStorage.setItem("rm-install-later", String(Date.now() + 14 * 864e5)); } catch (e) {}
    }
  };
};

/* Ilova qobig'i: chap menyu, tezkor qidiruv (Ctrl+K) va bildirishnomalar */
window.rmShell = function () {
  function norm(s) { return (s || "").toLowerCase().replace(/[‘’ʻʼ'`]/g, "").trim(); }
  return {
    menu: false, search: false, notif: false, seen: false, q: "", pos: 0,
    openSearch: function () {
      var self = this;
      this.menu = false; this.notif = false; this.search = true; this.q = ""; this.pos = 0;
      // x-show animatsiyasi elementni ko'rsatgandan keyin fokus beramiz
      setTimeout(function () { self.$refs.q.focus(); }, 60);
    },
    index: function () {
      var items = (window.RM_SEARCH || []).slice();
      try {
        (JSON.parse(localStorage.getItem("rm-notes")) || []).forEach(function (n) {
          items.push({ g: rmT("notes"), t: n.title || String(n.text || "").slice(0, 70), s: n.topic, u: "/app/eslatmalar", i: "note" });
        });
      } catch (e) {}
      return items;
    },
    results: function () {
      var q = norm(this.q), all = this.index(), out;
      if (!q) out = all.filter(function (r) { return r.g === rmT("sections"); }).slice(0, 8);
      else out = all.filter(function (r) { return norm(r.t + " " + (r.s || "")).indexOf(q) !== -1; }).slice(0, 12);
      // h — guruh sarlavhasini ko'rsatish kerakmi (guruhdagi birinchi element)
      return out.map(function (r, i) { return Object.assign({}, r, { h: i === 0 || out[i - 1].g !== r.g }); });
    },
    move: function (d) { var n = this.results().length; if (n) this.pos = (this.pos + d + n) % n; },
    open: function () { var r = this.results()[this.pos]; if (r) location.href = r.u; },
    keys: function (e) {
      var typing = /input|textarea|select/i.test(e.target.tagName) || e.target.isContentEditable;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); this.openSearch(); }
      else if (e.key === "/" && !typing) { e.preventDefault(); this.openSearch(); }
      else if (e.key === "Escape") { this.search = false; this.menu = false; this.notif = false; }
    }
  };
};

(function () {
  "use strict";

  // Dars yoki mavzu sahifasi ochilganda shu mavzu «hozir o'rganilayotgan» deb eslab qolinadi
  // (yangi eslatma shu mavzuga saqlanadi). Yangi mavzu boshlansa — AI tutor suhbati tozalanadi.
  (function () {
    var el = document.querySelector("[data-current-topic]");
    if (!el) return;
    var topic = el.dataset.currentTopic;
    try {
      var prev = localStorage.getItem("rm-current-topic");
      localStorage.setItem("rm-current-topic", topic);
      if (prev && prev !== topic && window.rmTutorStore) window.rmTutorStore.clear();
    } catch (e) {}
  })();

  // ---------- Dam olish: 45 daqiqadan keyin ko'z uchun tanaffus (partials/rest.html) ----------
  (function () {
    var root = document.getElementById("rm-rest");
    if (!root) return;
    var MIN = 60 * 1000, LIMIT = 45 * MIN, BREAK = 5 * MIN, AWAY = 5 * MIN, REASK = 10 * MIN, TICK = 5000, KEY = "rm-rest";
    var html = document.documentElement;
    var inTest = !!document.querySelector("[data-leave-guard]");   // test paytida tavsiya chiqmaydi
    var $ = function (s) { return root.querySelector(s); };
    var prompt = $("[data-rest-prompt]"), brk = $("[data-rest-break]"), clock = $("[data-rest-clock]"), warn = $("[data-rest-warn]");
    var t = {}; try { t = JSON.parse(document.getElementById("rm-rest-i18n").textContent); } catch (e) {}

    function fresh() { return { acc: 0, last: Date.now(), declines: 0, nextAt: LIMIT, breakUntil: 0, forced: false }; }
    function load() { try { return Object.assign(fresh(), JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) { return fresh(); } }
    function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
    function level(s) { return s.declines >= 3 ? 2 : (s.declines >= 1 ? 1 : 0); }
    function paint(s) { var l = level(s); if (l) html.dataset.strain = l; else delete html.dataset.strain; }

    var s = load(), now = Date.now();
    // 5 daqiqadan uzoq tizimdan chiqib qaytgan bo'lsa — hisob va rang asl holiga qaytadi
    if (!s.breakUntil && now - s.last > AWAY) s = fresh();
    var demo = new URLSearchParams(location.search).get("dam");
    if (demo && !inTest) { s.acc = LIMIT; s.nextAt = LIMIT; s.breakUntil = 0; if (demo === "majburiy") s.declines = 4; }
    s.last = now; save(s); paint(s);

    function show(el) { root.hidden = false; prompt.hidden = el !== prompt; brk.hidden = el !== brk; document.body.classList.add("rest-open"); }
    function hide() { root.hidden = true; prompt.hidden = brk.hidden = true; document.body.classList.remove("rest-open"); }

    function startBreak(forced) {
      s = load(); s.breakUntil = Date.now() + BREAK; s.forced = !!forced; save(s);
      runBreak();
    }
    function runBreak() {
      $("[data-rest-forced]").hidden = !s.forced;
      show(brk);
      (function step() {
        var left = Math.max(0, load().breakUntil - Date.now());
        clock.textContent = Math.floor(left / MIN) + ":" + String(Math.floor(left % MIN / 1000)).padStart(2, "0");
        if (left > 0) return setTimeout(step, 500);
        // Tanaffus tugadi: rang va hisob asl holatga
        s = fresh(); save(s); paint(s); hide();
        if (window.rmToast) window.rmToast(rmT("breakOver"));
      })();
    }
    function ask() {
      if (s.declines >= 4) return startBreak(true);   // 5-safar — majburiy
      warn.hidden = !s.declines;
      if (s.declines) warn.textContent = (t.warn1 || "").replace("{n}", s.declines) + (s.declines === 3 ? " " + (t.warnLast || "") : "");
      show(prompt);
      $("[data-rest-accept]").focus();
    }
    $("[data-rest-accept]").addEventListener("click", function () { startBreak(false); });
    $("[data-rest-decline]").addEventListener("click", function () {
      s = load(); s.declines += 1; s.nextAt = s.acc + REASK; save(s); paint(s); hide();
    });

    function tick() {
      var cur = load(), n = Date.now();
      if (cur.breakUntil) {            // tanaffus davom etmoqda (boshqa oynada boshlangan bo'lishi ham mumkin)
        s = cur;
        if (brk.hidden && !inTest) runBreak();   // test paytida tanaffus oynasi chiqmaydi
        return;
      }
      var gap = n - cur.last;
      if (gap > AWAY) cur = fresh();   // uzoq tanaffus — hammasi qaytadan
      else cur.acc += gap;
      cur.last = n; s = cur; save(s); paint(s);
      if (!inTest && root.hidden && s.acc >= s.nextAt) ask();
    }
    if (s.breakUntil && s.breakUntil > now) { if (!inTest) runBreak(); }
    else if (s.breakUntil) { s = fresh(); save(s); paint(s); }
    else if (!inTest && s.acc >= s.nextAt) ask();   // masalan, test tugagach hisob 45 daqiqadan oshgan bo'lsa
    setInterval(tick, TICK);
    // Tanaffus paytida Esc va Tab bilan chiqib ketib bo'lmaydi
    document.addEventListener("keydown", function (e) { if (!brk.hidden && (e.key === "Escape" || e.key === "Tab")) e.preventDefault(); }, true);
  })();
})();
