/* raqamliMuallim — AI tutor sahifasi */

/* AI tutor sahifasi: suhbatni tiklash, yangi savolni qo'shish va saqlash.
   msgs — [{ role: "user" | "ai", html }] (namunadagi boshlang'ich suhbat serverdan keladi). */
window.rmTutor = function () {
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  return {
    msgs: [], restored: false, typing: false, startedAt: null,
    init: function () {
      var self = this, saved = rmTutorStore.load();
      if (saved && saved.msgs.length) { this.msgs = saved.msgs; this.startedAt = saved.savedAt; this.restored = true; }
      else {
        // Namunaviy suhbat (faqat ishlab chiqishda, saqlanmaydi) — shablondagi elementlardan
        this.msgs = Array.prototype.map.call(this.$refs.seed.children, function (el) {
          return { role: el.dataset.role, html: el.innerHTML, seed: true };
        });
      }
      // 24 soat o'tdi yoki keyingi mavzuga o'tildi: ochiq turgan sahifadagi suhbat ham tozalanadi
      document.addEventListener("rm-tutor-cleared", function () { self.msgs = []; self.startedAt = null; self.restored = false; });
      var q = new URLSearchParams(location.search).get("q");
      if (q) {
        this.ask(q);
        // URL'dan savolni olib tashlaymiz: sahifa yangilansa savol qayta qo'shilmasin
        history.replaceState(null, "", location.pathname + location.search.replace(/([?&])q=[^&]*&?/, "$1").replace(/[?&]$/, ""));
      }
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
        if (self.startedAt === null) return;            // javob kutilayotganda suhbat tozalandi
        self.msgs.push({ role: "ai", html: "<p>" + esc(rmT("tutorDemo", { q: text.slice(0, 80) })) + "</p>" });
        self.persist(); self.scroll();
      }, 900);
    },
    send: function (ev) {
      var ta = ev.target.querySelector("textarea");
      this.ask(ta.value); ta.value = ""; ta.style.height = "auto";
    },
    reset: function () {
      rmTutorStore.clear();     // msgs "rm-tutor-cleared" hodisasida bo'shatiladi
    },
    persist: function () {
      var own = this.msgs.filter(function (m) { return !m.seed; });
      if (!own.length) return;
      if (this.startedAt === null) this.startedAt = Date.now();
      rmTutorStore.save(own, this.startedAt);
    },
    scroll: function () {
      this.$nextTick(function () { window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); });
    }
  };
};
