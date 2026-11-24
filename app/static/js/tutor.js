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
      var params = new URLSearchParams(location.search), q = params.get("q"), ref = params.get("savol");
      if (q || ref) {
        if (ref) this.solve(ref); else this.ask(q);
        // URL'dan savolni olib tashlaymiz: sahifa yangilansa savol qayta qo'shilmasin
        params.delete("q"); params.delete("savol");
        history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params : ""));
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
    /* Test natijasidagi «Yechimini ko'rish»: savol va yechimi serverdan (shablonda tozalangan HTML) */
    solve: function (ref) {
      var self = this;
      this.typing = true;
      fetch("/app/tutor/yechim/" + encodeURIComponent(ref), { headers: { Accept: "application/json" } })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function (d) {
          self.typing = false;
          // Shu savol yechimi suhbatda bo'lsa, takrorlanmaydi (oxiriga ko'chadi)
          self.msgs = self.msgs.filter(function (m) { return m.ref !== ref; });
          self.msgs.push({ role: "user", html: d.ask, ref: ref }, { role: "ai", html: d.html, ref: ref });
          self.persist(); self.scroll();
        })
        .catch(function (e) {
          self.typing = false;
          rmToast(rmT(e === 404 ? "solveMissing" : "solveFailed"));
        });
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
