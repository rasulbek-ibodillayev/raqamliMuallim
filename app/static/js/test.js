/* raqamliMuallim — test va attestatsiya sahifalari: savol, moslashtirish, to'liq ekran, sahifadan chiqish ogohlantirishi */

/* Test pleyeri: hamma savol sahifada ([data-q] bo'limlari), bittadan ko'rsatiladi. Javob avtomatik saqlanadi (RMPlayer),
   taymer tugash vaqtidan hisoblanadi; chiqib ketilsa to'xtaydi, qaytilganda davom etadi, tugasa test o'zi yakunlanadi.
   cfg: { id, uuid, kind, stage, questions: [{ pos, mode }], answers ({pos: {v, at}} — serverdagi), duration, sample, nextUrl, offline } */
window.rmTestPlayer = function (cfg) {
  return {
    cfg: cfg, s: null, cur: 0, st: "idle", pending: 0, online: navigator.onLine, left: null, shownAt: Date.now(), finishing: false,
    init: function () {
      var self = this;
      if (cfg.offline) RMPlayer.setForceOffline(true);
      RMPlayer.on(function (p) { self.st = p.state; self.pending = p.pending; self.online = p.online && !cfg.offline; });
      RMPlayer.open({ id: cfg.id, uuid: cfg.uuid, stage: cfg.stage, kind: cfg.kind, total: cfg.questions.length, duration: cfg.duration,
                      server: cfg.answers, local: cfg.sample, restart: cfg.sample }).then(function (s) {
        self.s = s;
        cfg.questions.forEach(function (q, i) {
          var a = s.answers[q.pos];
          if (a) RMPlayer.writeForm(self.section(i), q.mode, a.v);
        });
        window.dispatchEvent(new CustomEvent("rm-q-restored"));
        if (s.finished) { self.finish(); return; }        // avval yakunlangan, lekin hali yuborilmagan
        s.resume();
        self.cur = Math.min(s.pos || 0, cfg.questions.length - 1);
        self.left = s.remaining();
        setInterval(function () {
          self.left = s.remaining();
          if (self.left === 0 && !self.finishing && !s.finished) self.finish();
        }, 1000);
      });
      document.addEventListener("click", function (e) {
        if (e.target.closest("[data-safe-leave]") && self.s && !self.s.finished) self.s.pause();
      });
      window.addEventListener("rm-q-retry", function () { self.finish(); });
      window.addEventListener("online", function () { if (self.s && self.s.finished) self.finish(); });
    },
    section: function (i) { return this.$root.querySelector('[data-q="' + i + '"]'); },
    save: function () {
      if (!this.s || this.s.finished) return;
      var q = cfg.questions[this.cur], v = RMPlayer.readForm(this.section(this.cur), q.mode), old = this.s.answers[q.pos];
      if (JSON.stringify(old ? old.v : null) === JSON.stringify(v === "" || (Array.isArray(v) && !v.length) ? null : v)) return;
      return this.s.answer(q.pos, v, Date.now() - this.shownAt);
    },
    go: function (i) {
      if (i < 0 || i >= cfg.questions.length) return;
      this.save();
      this.cur = i; this.shownAt = Date.now();
      if (this.s) this.s.setPos(i);
      window.scrollTo({ top: 0 });
    },
    next: function () {
      if (this.cur < cfg.questions.length - 1) { this.go(this.cur + 1); return; }
      var saving = this.save(), s = this.s, self = this;
      if (!s || this.finishing) return;
      var empty = cfg.questions.filter(function (q) { return !s.answers[q.pos]; }).length;
      if (empty && !confirm(rmT("unanswered", { n: empty }))) return;
      Promise.resolve(saving).then(function () { self.finish(); });
    },
    finish: function () {
      var self = this;
      if (!this.s || this.finishing) return;
      this.finishing = true;
      this.s.finish().then(function (r) {
        if (r.synced) {
          var g = document.querySelector("[data-leave-guard]"); if (g) g.removeAttribute("data-leave-guard");
          // result_url yo'q: urinish serverda allaqachon yopilgan — sahifa uni o'zi to'g'ri joyga yo'naltiradi
          if (r.result_url || cfg.nextUrl) location.href = r.result_url || cfg.nextUrl;
          else location.reload();
        } else { self.finishing = false; window.dispatchEvent(new CustomEvent("rm-q-queued", { detail: true })); }
      }).catch(function () { self.finishing = false; window.dispatchEvent(new CustomEvent("rm-q-queued", { detail: true })); });
    },
    fmt: function (x) {
      if (x === null) return "--:--";
      var p = function (n) { return String(n).padStart(2, "0"); };
      return (x >= 3600 ? Math.floor(x / 3600) + ":" : "") + p(Math.floor(x % 3600 / 60)) + ":" + p(x % 60);
    },
    label: function () {
      if (this.st === "saving") return rmT("saving");
      if (this.st === "local" || (this.st !== "idle" && !this.online)) return rmT("savedLocal");
      if (this.st === "synced") return rmT("saved");
      if (this.st === "error") return rmT("notSaved");
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

(function () {
  "use strict";

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
      if (e.target.closest("[data-fs-toggle]")) { window.rmToggleFullscreen(); return; }
      if (e.target.closest("[data-safe-leave]") && document.fullscreenElement) document.exitFullscreen().catch(function () {});
    });
    if (!canFs()) document.querySelectorAll("[data-fs-toggle]").forEach(function (b) { b.hidden = true; });
  })();

  // Sahifadan chiqib ketishdan ogohlantirish (test va sinov sahifalari)
  var safeLeave = false;
  document.addEventListener("click", function (e) { if (e.target.closest("[data-safe-leave]")) safeLeave = true; });
  // Faqat haqiqiy (sahifani almashtiradigan) yuborish: fetch orqali yuborilgan formalar (@submit.prevent) himoyani o'chirmasin
  document.addEventListener("submit", function (e) { if (!e.defaultPrevented) safeLeave = true; });
  window.addEventListener("beforeunload", function (e) {
    if (safeLeave || !document.querySelector("[data-leave-guard]")) return;
    e.preventDefault();
    e.returnValue = "";
  });
})();
