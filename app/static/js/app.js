/* raqamliMuallim — kichik yordamchi skriptlar (Alpine.js bilan birga ishlaydi) */

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

/* AI tutor sahifasi: suhbatni tiklash, yangi savolni qo'shish va saqlash.
   msgs — [{ role: "user" | "ai", html }] (namunadagi boshlang'ich suhbat serverdan keladi). */
window.rmTutor = function (topic) {
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  return {
    msgs: [], restored: false, typing: false,
    init: function () {
      var self = this, saved = rmTutorStore.load(topic);
      if (saved && saved.msgs.length) { this.msgs = saved.msgs; this.restored = true; }
      else {
        // Boshlang'ich (namunaviy) suhbat — shablondagi elementlardan
        this.msgs = Array.prototype.map.call(this.$refs.seed.children, function (el) {
          return { role: el.dataset.role, html: el.innerHTML };
        });
      }
      var q = new URLSearchParams(location.search).get("q");
      if (q) {
        this.ask(q);
        // URL'dan savolni olib tashlaymiz: sahifa yangilansa savol qayta qo'shilmasin
        history.replaceState(null, "", location.pathname + location.search.replace(/([?&])q=[^&]*&?/, "$1").replace(/[?&]$/, ""));
      } else this.persist();
      this.$nextTick(function () { self.scroll(); });
    },
    ask: function (text) {
      var self = this;
      text = (text || "").trim();
      if (!text) return;
      this.msgs.push({ role: "user", html: esc(text) });
      this.persist(); this.typing = true; this.scroll();
      // Namunada AI javobi soxta; backendda /api/tutor oqim (stream) bilan javob qaytaradi
      setTimeout(function () {
        self.typing = false;
        self.msgs.push({ role: "ai", html: "<p>" + esc("Bu namunaviy javob. Backend ulanganda AI tutor «" + text.slice(0, 80) + "» savoliga darslik asosida javob beradi.") + "</p>" });
        self.persist(); self.scroll();
      }, 900);
    },
    send: function (ev) {
      var ta = ev.target.querySelector("textarea");
      this.ask(ta.value); ta.value = ""; ta.style.height = "auto";
    },
    reset: function () {
      rmTutorStore.clear();
      this.msgs = []; this.restored = false;
    },
    persist: function () { rmTutorStore.save(topic, this.msgs); },
    scroll: function () {
      this.$nextTick(function () { window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); });
    }
  };
};

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
      if (!e) { window.rmToast && window.rmToast("Brauzer menyusidan «Ilovani o‘rnatish»ni tanlang"); return; }
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

/* Mavzu testi savoli: javob avtomatik saqlanadi (RMPlayer), taymer tugash vaqtidan hisoblanadi.
   cfg: { id, kind (test turi), total, duration, pos, mode (yopiq|kop|moslash|ochiq), offline (namuna) } */
window.rmTestQuestion = function (cfg) {
  return {
    s: null, st: "idle", pending: 0, online: navigator.onLine, left: null, started: Date.now(),
    init: function () {
      var self = this, form = this.$el;
      if (cfg.offline) RMPlayer.setForceOffline(true);
      RMPlayer.on(function (p) { self.st = p.state; self.pending = p.pending; self.online = p.online && !cfg.offline; });
      RMPlayer.open({ id: cfg.id, kind: cfg.kind, total: cfg.total, duration: cfg.duration }).then(function (s) {
        self.s = s;
        var a = s.answers[cfg.pos];
        if (a) { RMPlayer.writeForm(form, cfg.mode, a.v); self.st = "synced"; window.dispatchEvent(new CustomEvent("rm-q-restored")); }
        s.setPos(cfg.pos);
        self.left = s.remaining();
        setInterval(function () { self.left = s.remaining(); }, 1000);
      });
    },
    save: function () {
      if (!this.s) return;
      var v = RMPlayer.readForm(this.$el, cfg.mode);
      this.s.answer(cfg.pos, v, Date.now() - this.started);
    },
    fmt: function (x) {
      if (x === null) return "--:--";
      var p = function (n) { return String(n).padStart(2, "0"); };
      return (x >= 3600 ? Math.floor(x / 3600) + ":" : "") + p(Math.floor(x % 3600 / 60)) + ":" + p(x % 60);
    },
    label: function () {
      if (this.st === "saving") return "Saqlanmoqda…";
      if (this.st === "local" || (this.st !== "idle" && !this.online)) return "Qurilmada saqlandi";
      if (this.st === "synced") return "Saqlandi";
      if (this.st === "error") return "Saqlanmadi";
      return "";
    }
  };
};

/* Moslashtirish savoli: bitta javob faqat bitta atamaga. Biror atamaga tanlangan ta'rif boshqa atamalarning
   ro'yxatidan olib tashlanadi (yashiriladi va o'chiriladi); tanlov bekor qilinsa yana paydo bo'ladi. */
window.rmMatch = function () {
  return {
    init: function () {
      var self = this;
      this.sync();
      window.addEventListener("rm-q-restored", function () { self.sync(); });
    },
    sync: function () {
      var sels = Array.prototype.slice.call(this.$el.querySelectorAll("select"));
      var taken = sels.map(function (s) { return s.value; });
      sels.forEach(function (s, i) {
        Array.prototype.forEach.call(s.options, function (o) {
          if (!o.value) return;
          var used = taken.some(function (v, j) { return j !== i && v === o.value; });
          o.hidden = used; o.disabled = used;
        });
      });
    }
  };
};

/* Forma: POST + CSRF, server tekshiruvi, xatolarni maydon yonida ko'rsatish.
   JS bo'lmasa forma oddiy POST bo'lib ishlaydi (server sahifani xatolar bilan qayta chizadi).
   extra — formaning o'z holati ({ show: false } kabi), onOk(json) — muvaffaqiyatdan keyin (ixtiyoriy). */
window.rmForm = function (extra, onOk) {
  var base = {
    busy: false, errors: {}, message: "", ok: false,
    initForm: function () {
      try { this.errors = JSON.parse(this.$el.dataset.errors || "{}"); } catch (e) { this.errors = {}; }
    },
    err: function (name) { return this.errors[name] || ""; },
    clear: function (name) { if (this.errors[name]) { var e = Object.assign({}, this.errors); delete e[name]; this.errors = e; } },
    submit: function (ev) {
      var self = this, form = ev.target.closest("form");
      if (this.busy) return;
      this.busy = true; this.message = ""; this.ok = false;
      var body = new FormData(form);
      if (ev.submitter && ev.submitter.name) body.append(ev.submitter.name, ev.submitter.value);
      return fetch(ev.submitter && ev.submitter.formAction ? ev.submitter.formAction : form.action, {
        method: "POST", body: body, credentials: "same-origin",
        headers: { "Accept": "application/json", "X-CSRFToken": (document.querySelector('meta[name="csrf-token"]') || {}).content || "" }
      }).then(function (r) {
        return r.json().catch(function () { return { ok: false, message: "Server javobini o‘qib bo‘lmadi (" + r.status + ")" }; });
      }).then(function (j) {
        self.busy = false;
        if (j.ok) {
          self.errors = {}; self.ok = true; self.message = j.message || "";
          if (onOk && onOk.call(self, j, form) === false) return j;
          if (j.redirect && !(form.dataset.stay)) { location.href = j.redirect; return j; }
          if (j.message && window.rmToast) window.rmToast(j.message);
          return j;
        }
        self.errors = j.errors || {};
        self.message = j.message || j.error || "Xatolarni tuzating";
        // Birinchi xato maydonga fokus
        var first = Object.keys(self.errors)[0];
        var el = first && form.querySelector('[name="' + first + '"]');
        if (el) el.focus();
        return j;
      }).catch(function () {
        self.busy = false;
        self.message = "Internetga ulanib bo‘lmadi. Ulanishni tekshirib, qayta yuboring.";
      });
    }
  };
  return window.rmMix(base, extra);
};

/* Telefon/email formatini brauzerda tekshirish (server bilan bir xil qoida: forms.py PHONE_RE, EMAIL_RE).
   «Kod yuborish» tugmasi faqat format to'g'ri bo'lganda faollashadi. only: "phone" | "email" | undefined (ikkalasi) */
window.rmIsEmail = function (v) { return /^[^@\s]{1,64}@[^@\s]+\.[A-Za-z]{2,}$/.test((v || "").trim()); };
window.rmIsPhone = function (v) {
  if (/[^\d\s+()\-]/.test(v || "")) return false;
  var d = (v || "").replace(/\D/g, "");
  if (d.length === 9) d = "998" + d;
  return /^998\d{9}$/.test(d);
};
/* Bir nechta obyektni getter'larini saqlagan holda birlashtiradi (Object.assign getter'ni qiymatga aylantiradi) */
window.rmMix = function () {
  var out = {};
  Array.prototype.forEach.call(arguments, function (o) {
    if (o) Object.defineProperties(out, Object.getOwnPropertyDescriptors(o));
  });
  return out;
};
window.rmContact = function (initial, only) {
  return {
    contact: initial || "",
    get kind() {
      var v = this.contact.trim();
      if (only !== "phone" && v.indexOf("@") !== -1) return rmIsEmail(v) ? "email" : "";
      if (only !== "email" && rmIsPhone(v)) return "phone";
      return "";
    },
    get valid() { return !!this.kind; }
  };
};

/* Kod amal qilish muddati (masalan, 5 daqiqa): orqaga sanaydi, tugagach «Kodni qayta yuborish» ko'rinadi */
window.rmCodeTimer = function (seconds) {
  return {
    left: seconds, total: seconds, t: null,
    start: function () {
      var self = this;
      clearInterval(this.t); this.left = this.total;
      this.t = setInterval(function () { if (self.left > 0) self.left--; else clearInterval(self.t); }, 1000);
    },
    get expired() { return this.left <= 0; },
    get mmss() { return Math.floor(this.left / 60) + ":" + String(this.left % 60).padStart(2, "0"); },
    get pct() { return Math.round(this.left / this.total * 100); }
  };
};

/* Joriy parolni tasdiqlash "darvozasi" (rmForm bilan birga): parol serverda tekshiriladi, to'g'ri bo'lsa pwOk = true
   va asosiy tugma faollashadi. Har bir harfda emas, faqat «Tasdiqlash» / Enter / maydondan chiqishda tekshiriladi —
   aks holda chala yozilgan parol urinishlar limitini (5 ta) behuda sarflaydi. */
window.rmPwGate = function (url) {
  var last = null;
  return {
    pwOk: false, pwChecking: false,
    pwInput: function () { this.pwOk = false; last = null; this.clear("pw"); },
    checkPw: function () {
      var self = this, input = this.$root.querySelector('input[name="pw"]'), v = input ? input.value : "";
      if (!v || v === last || this.pwChecking) return;
      last = v; this.pwChecking = true;
      var body = new FormData(); body.append("pw", v);
      return fetch(url, { method: "POST", body: body, credentials: "same-origin",
        headers: { "Accept": "application/json", "X-CSRFToken": (document.querySelector('meta[name="csrf-token"]') || {}).content || "" }
      }).then(function (r) { return r.json(); }).then(function (j) {
        self.pwChecking = false; self.pwOk = !!j.ok;
        if (!j.ok) { self.errors = Object.assign({}, self.errors, j.errors || { pw: j.error }); }
      }).catch(function () { self.pwChecking = false; last = null; self.errors = Object.assign({}, self.errors, { pw: "Internetga ulanib bo‘lmadi" }); });
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
          items.push({ g: "Eslatmalar", t: n.title || n.text.slice(0, 70), s: n.topic, u: "/app/eslatmalar", i: "note" });
        });
      } catch (e) {}
      return items;
    },
    results: function () {
      var q = norm(this.q), all = this.index(), out;
      if (!q) out = all.filter(function (r) { return r.g === "Bo‘limlar"; }).slice(0, 8);
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

  // Yorug'/qorong'i mavzu
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-theme-toggle]");
    if (!t) return;
    var root = document.documentElement;
    var dark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (err) {}
  });

  // Kodni nusxalash
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-copy]");
    if (!b) return;
    var pre = b.closest(".code").querySelector("pre");
    if (navigator.clipboard) navigator.clipboard.writeText(pre.innerText).catch(function () {});
    var old = b.innerHTML;
    b.textContent = "Nusxalandi";
    setTimeout(function () { b.innerHTML = old; }, 1400);
  });

  // Matn maydoni balandligini avtomatik moslash; Enter — yuborish, Shift+Enter — yangi qator
  document.addEventListener("input", function (e) {
    var t = e.target;
    if (!t.matches("[data-autosize]")) return;
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 200) + "px";
  });
  document.addEventListener("keydown", function (e) {
    var t = e.target;
    if (t.matches && t.matches(".composer textarea") && e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (t.value.trim()) t.form.requestSubmit();
    }
  });

  // OTP: keyingi katakka avtomatik o'tish
  document.addEventListener("input", function (e) {
    var t = e.target;
    if (!t.closest || !t.closest(".otp")) return;
    t.value = t.value.replace(/\D/g, "").slice(0, 1);
    if (t.value && t.nextElementSibling) t.nextElementSibling.focus();
  });
  document.addEventListener("keydown", function (e) {
    var t = e.target;
    if (t.closest && t.closest(".otp") && e.key === "Backspace" && !t.value && t.previousElementSibling) {
      t.previousElementSibling.focus();
    }
  });

  // Python kodini sodda ranglash
  var KW = /\b(if|elif|else|for|while|in|def|return|import|from|as|and|or|not|True|False|None|class|try|except|with|lambda|break|continue|pass)\b/g;
  function highlight(src) {
    var esc = src.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return esc
      .replace(/(#.*)$/gm, "\u0001c$1\u0002")
      .replace(/("[^"\n]*"|'[^'\n]*')/g, "\u0001s$1\u0002")
      .replace(KW, "\u0001k$1\u0002")
      .replace(/\b(print|range|len|input|int|str|float|list)\b(?=\()/g, "\u0001f$1\u0002")
      .replace(/\b(\d+(?:\.\d+)?)\b/g, "\u0001n$1\u0002")
      .replace(/\u0001([cskfn])/g, '<span class="tok-$1">')
      .replace(/\u0002/g, "</span>");
  }
  function run() {
    document.querySelectorAll('pre[data-lang="python"] code').forEach(function (c) {
      if (c.dataset.hl) return;
      c.innerHTML = highlight(c.textContent);
      c.dataset.hl = "1";
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();

  // Scroll paytida kartalar va bo'limlarni silliq ko'rsatish
  var REVEAL = [
    ".page .card", ".page .ai-card", ".page .alert", ".page .table-wrap", ".page .chips",
    ".page .timeline > li", ".page .page-head", ".page .composer", ".page .empty",
    ".focus-body .card", ".focus-body .code", ".focus-body .prose", ".focus-body figure", ".focus-body .ai-card",
    ".cert-page", "[data-reveal]"
  ].join(",");
  function reveal() {
    if (!("IntersectionObserver" in window)) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var els = Array.prototype.filter.call(document.querySelectorAll(REVEAL), function (el) {
      // ichma-ich animatsiya bo'lmasin; modal oynalar ichidagilarga tegmaymiz
      return !el.parentElement.closest(".reveal") && !el.closest(".sheet-backdrop, .sidebar, [x-cloak]");
    });
    var fired = false;
    // Zaxira: kuzatuvchi umuman ishlamasa (masalan, sahifa fon rejimida), kontent yashirin qolmasin
    setTimeout(function () {
      if (fired) return;
      els.forEach(function (el) { el.classList.remove("reveal"); });
      io.disconnect();
    }, 1500);
    var io = new IntersectionObserver(function (entries) {
      fired = true;
      var i = 0;
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.style.setProperty("--rd", Math.min(i++ * 60, 300) + "ms");
        en.target.classList.add("in");
        io.unobserve(en.target);
        // animatsiya tugagach transform'ni olib tashlaymiz (fixed elementlar to'g'ri ishlashi uchun)
        var el = en.target;
        el.addEventListener("transitionend", function done(e) {
          if (e.target !== el || e.propertyName !== "transform") return;
          el.removeEventListener("transitionend", done);
          el.classList.remove("reveal", "in");
          el.style.removeProperty("--rd");
        });
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    els.forEach(function (el) { el.classList.add("reveal"); io.observe(el); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", reveal); else reveal();

  // Kichik bildirishnoma (toast)
  // rmToast(matn, [tugma matni, tugma bosilganda])
  window.rmToast = function (text, actionLabel, onAction) {
    var t = document.createElement("div");
    t.className = "toast"; t.setAttribute("role", "status");
    t.innerHTML = '<svg class="ico ico-sm" aria-hidden="true"><use href="#i-check"/></svg>';
    t.appendChild(document.createTextNode(text));
    if (actionLabel) {
      var b = document.createElement("button");
      b.type = "button"; b.textContent = actionLabel;
      b.addEventListener("click", function () { t.remove(); onAction(); });
      t.appendChild(b);
    }
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, actionLabel ? 6000 : 2400);
  };

  // Dars: mundarijada joriy bo'limni belgilash va so'nggi o'qilgan joydan davom ettirish
  function lessonNav() {
    var art = document.querySelector("[data-resume]");
    if (!art) return;
    var key = "resume:" + art.dataset.resume;
    var sections = Array.prototype.slice.call(art.querySelectorAll("[data-toc-section]"));
    var links = {};
    document.querySelectorAll("[data-toc-link]").forEach(function (a) { links[a.dataset.tocLink] = a; });
    var restoring = false;
    function setActive(id) {
      if (restoring) return;
      Object.keys(links).forEach(function (k) { links[k].classList.toggle("is-active", k === id); });
      if (links[id]) { links[id].setAttribute("aria-current", "true"); links[id].scrollIntoView({ block: "nearest", inline: "nearest" }); }
      try { if (id !== sections[0].id) localStorage.setItem(key, id); else localStorage.removeItem(key); } catch (e) {}
    }
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) setActive(en.target.id); });
      }, { rootMargin: "-30% 0px -60% 0px" });
      sections.forEach(function (s) { io.observe(s); });
    }
    var saved = null;
    try { saved = localStorage.getItem(key); } catch (e) {}
    var target = saved && document.getElementById(saved);
    if (target && !location.hash && saved !== sections[0].id) {
      restoring = true; // tiklash tugaguncha birinchi bo'lim «faol» deb yozilib qolmasin
      setTimeout(function () {
        target.scrollIntoView({ behavior: "instant", block: "start" });
        setTimeout(function () { restoring = false; setActive(saved); }, 400);
        var name = links[saved] ? links[saved].textContent.trim().replace(/^\d+/, "") : "";
        window.rmToast("So‘nggi o‘qigan joyingiz: " + name, "Boshidan", function () {
          window.scrollTo({ top: 0, behavior: "smooth" });
          try { localStorage.removeItem(key); } catch (e) {}
        });
      }, 150);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", lessonNav); else lessonNav();

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

  // Darsda matnni belgilaganda: «Eslatmaga saqlash» va «AI’dan so‘rash»
  // Eslatmalar hozircha brauzer xotirasiga (rm-notes-inbox) yoziladi, «Eslatmalar» sahifasi uni o'qib oladi.
  var selMenu = null;
  function hideSel() { if (selMenu) { selMenu.remove(); selMenu = null; } }
  function showSel() {
    var s = window.getSelection();
    var text = s ? s.toString().trim() : "";
    var box = s && s.rangeCount ? s.anchorNode && (s.anchorNode.nodeType === 1 ? s.anchorNode : s.anchorNode.parentElement).closest("[data-select-menu]") : null;
    hideSel();
    if (!box || text.length < 3) return;
    var r = s.getRangeAt(0).getBoundingClientRect();
    selMenu = document.createElement("div");
    selMenu.className = "sel-menu"; selMenu.setAttribute("role", "toolbar"); selMenu.setAttribute("aria-label", "Belgilangan matn");
    selMenu.style.left = (r.left + r.width / 2 + window.scrollX) + "px";
    selMenu.style.top = (r.top + window.scrollY) + "px";
    selMenu.innerHTML =
      '<button type="button" data-act="note"><svg class="ico ico-sm"><use href="#i-bookmark"/></svg>Eslatmaga saqlash</button>' +
      '<button type="button" data-act="ai"><svg class="ico ico-sm"><use href="#i-sparkle"/></svg>AI’dan so‘rash</button>';
    selMenu.addEventListener("mousedown", function (e) { e.preventDefault(); });
    selMenu.addEventListener("click", function (e) {
      var act = e.target.closest("button") && e.target.closest("button").dataset.act;
      if (act === "note") {
        try {
          var inbox = JSON.parse(localStorage.getItem("rm-notes-inbox") || "[]");
          inbox.push({ id: Date.now(), topic: box.dataset.topic || "Umumiy", title: "", text: text, code: "", when: "Bugun" });
          localStorage.setItem("rm-notes-inbox", JSON.stringify(inbox));
        } catch (err) {}
        window.rmToast("Eslatmalarga saqlandi");
      } else if (act === "ai") {
        location.href = box.dataset.tutorUrl + "?q=" + encodeURIComponent("Tushuntirib bering: «" + text.slice(0, 300) + "»");
      }
      hideSel(); s.removeAllRanges();
    });
    document.body.appendChild(selMenu);
  }
  document.addEventListener("mouseup", function (e) { if (!(e.target.closest && e.target.closest(".sel-menu"))) setTimeout(showSel, 0); });
  document.addEventListener("touchend", function () { setTimeout(showSel, 250); });
  document.addEventListener("keyup", function (e) { if (e.shiftKey) showSel(); if (e.key === "Escape") hideSel(); });
  window.addEventListener("scroll", hideSel, { passive: true });

  // Test rejimi: test sahifasida ([data-leave-guard]) ekranda faqat test qolsin — to'liq ekran.
  // Brauzer to'liq ekranni faqat foydalanuvchi harakatidan keyin ruxsat beradi, shuning uchun birinchi
  // bosishda yoqiladi. Test to'xtatilsa yoki yakunlansa (data-safe-leave / sahifadan chiqish) o'chadi.
  // Foydalanuvchi o'zi o'chirsa (Esc yoki tugma), shu test davomida qayta yoqilmaydi.
  (function () {
    if (!document.querySelector("[data-leave-guard]")) return;
    var root = document.documentElement, optedOut = false;
    document.body.classList.add("test-mode");
    function canFs() { return root.requestFullscreen && document.fullscreenEnabled; }
    function enter() {
      if (optedOut || !canFs() || document.fullscreenElement) return;
      root.requestFullscreen({ navigationUI: "hide" }).catch(function () {});
    }
    window.rmToggleFullscreen = function () {
      if (document.fullscreenElement) { optedOut = true; document.exitFullscreen().catch(function () {}); }
      else { optedOut = false; enter(); }
    };
    document.addEventListener("pointerdown", function once(e) {
      if (e.target.closest("[data-safe-leave], [data-fs-toggle]")) return;
      enter(); document.removeEventListener("pointerdown", once, true);
    }, true);
    document.addEventListener("fullscreenchange", function () {
      document.body.classList.toggle("is-fullscreen", !!document.fullscreenElement);
    });
    document.addEventListener("click", function (e) {
      if (e.target.closest("[data-safe-leave]") && document.fullscreenElement) document.exitFullscreen().catch(function () {});
    });
    if (!canFs()) document.querySelectorAll("[data-fs-toggle]").forEach(function (b) { b.hidden = true; });
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
        if (window.rmToast) window.rmToast("Tanaffus tugadi. Davom etamiz!");
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

  // Serverdan kelgan flash xabarlar (JS'siz yuborilgan formalar) → toast
  document.querySelectorAll("[data-flash]").forEach(function (el) {
    try { JSON.parse(el.dataset.flash).forEach(function (m, i) { setTimeout(function () { window.rmToast(m); }, i * 2600); }); } catch (e) {}
  });

  // PWA: Service Worker (oflayn rejim)
  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  }

  // Matn o'lchami: data-fs = md (standart) | lg | xl
  window.rmSetFontSize = function (v) {
    var d = document.documentElement;
    if (v === "md") delete d.dataset.fs; else d.dataset.fs = v;
    try { if (v === "md") localStorage.removeItem("fs"); else localStorage.setItem("fs", v); } catch (e) {}
    document.dispatchEvent(new CustomEvent("rm-fs", { detail: v }));
  };
  window.rmFontSize = function () { return document.documentElement.dataset.fs || "md"; };
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-fs-cycle]");
    if (!b) return;
    var order = ["md", "lg", "xl"], cur = window.rmFontSize();
    window.rmSetFontSize(order[(order.indexOf(cur) + 1) % order.length]);
  });

  // Sahifadan chiqib ketishdan ogohlantirish (test va sinov sahifalari)
  var safeLeave = false;
  document.addEventListener("click", function (e) { if (e.target.closest("[data-safe-leave]")) safeLeave = true; });
  document.addEventListener("submit", function () { safeLeave = true; });
  window.addEventListener("beforeunload", function (e) {
    if (safeLeave || !document.querySelector("[data-leave-guard]")) return;
    e.preventDefault();
    e.returnValue = "";
  });

  // Taymer: data-countdown="soniyalar"
  function pad(n) { return String(n).padStart(2, "0"); }
  function fmt(s) {
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
    return (h ? h + ":" + pad(m) : pad(m)) + ":" + pad(x);
  }
  function timers() {
    document.querySelectorAll("[data-countdown]").forEach(function (el) {
      var s = parseInt(el.dataset.countdown, 10);
      el.textContent = fmt(s);
      setInterval(function () { if (s > 0) { s--; el.textContent = fmt(s); } }, 1000);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", timers); else timers();
})();
