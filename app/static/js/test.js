/* raqamliMuallim — test va attestatsiya sahifalari: savol, moslashtirish, to'liq ekran, sahifadan chiqish ogohlantirishi */

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
