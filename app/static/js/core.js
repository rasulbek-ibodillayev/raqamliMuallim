/* raqamliMuallim — umumiy yordamchilar (har bir sahifada). Sahifaga xos qismlar: learner.js, lesson.js, tutor.js, test.js */

/* Tarjima: base.html dagi <script id="rm-i18n"> (server tanlangan tilda beradi). Topilmasa — o'zbekcha matn.
   rmT("kalit", { q: "…" }) — {q} o'rinbosarlari almashtiriladi. */
window.rmT = (function () {
  var UZ = {
    saving: "Saqlanmoqda…", savedLocal: "Qurilmada saqlandi", saved: "Saqlandi", notSaved: "Saqlanmadi",
    badServer: "Server javobini o‘qib bo‘lmadi", fixErrors: "Xatolarni tuzating",
    offline: "Internetga ulanib bo‘lmadi. Ulanishni tekshirib, qayta yuboring.", offlineShort: "Internetga ulanib bo‘lmadi",
    installHint: "Brauzer menyusidan «Ilovani o‘rnatish»ni tanlang",
    solveMissing: "Savol topilmadi",
    solveFailed: "Yechimni yuklab bo‘lmadi. Internetni tekshirib, qayta urinib ko‘ring",
    tutorDemo: "Bu namunaviy javob. Backend ulanganda AI tutor «{q}» savoliga darslik asosida javob beradi.",
    sections: "Bo‘limlar", notes: "Eslatmalar", copied: "Nusxalandi",
    resume: "So‘nggi o‘qigan joyingiz:", fromStart: "Boshidan",
    selection: "Belgilangan matn", toNote: "Eslatmaga saqlash", askAi: "AI’dan so‘rash",
    general: "Umumiy", today: "Bugun", noteSaved: "Eslatmalarga saqlandi",
    explain: "Tushuntirib bering: «{t}»", breakOver: "Tanaffus tugadi. Davom etamiz!",
    copyManually: "Nusxalab oling:", pauseOffline: "Internet yo‘q: vaqtni to‘xtatib bo‘lmadi", resumeOffline: "Internet yo‘q. Ulanish tiklangach davom ettiring",
    bigExcel: "Excel fayl 5 MB dan oshmasin", bigImage: "Rasm 2 MB dan oshmasin",
    packReady: "Oflayn paket tayyor", packFailed: "Yuklab bo‘lmadi. Qayta urinib ko‘ring", packBig: "Paket 30 MB dan katta",
    packNoSpace: "Qurilmada joy yetarli emas", packUnsupported: "Bu brauzer oflayn saqlashni qo‘llamaydi",
    packRemove: "Yuklab olingan darslar o‘chirilsinmi?", packInfo: "{size} · {lessons} ta dars · {tests} ta test · {date} gacha",
    logoutPending: "{n} ta javob hali serverga yuborilmagan. Chiqsangiz, ular yo‘qoladi. Baribir chiqasizmi?",
    unanswered: "{n} ta savolga javob berilmagan (0 ball hisoblanadi). Baribir yakunlaysizmi?"
  };
  var dict = null;
  return function (key, vars) {
    if (!dict) {
      dict = {};
      try { var el = document.getElementById("rm-i18n"); if (el) dict = JSON.parse(el.textContent) || {}; } catch (e) {}
    }
    var s = dict[key] || UZ[key] || key;
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  };
})();

/* Sahifalararo o'tish animatsiyasi (@view-transition) brauzer tomonidan bekor qilinsa (masalan, ilova fonga o'tganda
   yoki tez ketma-ket bosilganda) uning va'dalari rad etiladi — bu xato emas, konsolni to'ldirmasligi uchun ushlanadi. */
window.addEventListener("pagereveal", function (e) {
  var vt = e.viewTransition;
  if (vt) ["ready", "finished", "updateCallbackDone"].forEach(function (k) { if (vt[k]) vt[k].catch(function () {}); });
});
window.addEventListener("pageswap", function (e) {
  var vt = e.viewTransition;
  if (vt) ["ready", "finished", "updateCallbackDone"].forEach(function (k) { if (vt[k]) vt[k].catch(function () {}); });
});

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
      this.message = ""; this.ok = false;
      var body = new FormData(form), big = null;
      // Katta fayl serverga yuborilmaydi: server ulanishni uzadi va «internet yo'q» degandek ko'rinardi
      body.forEach(function (v, k) { if (v instanceof File && v.size > (/\.xlsx$/i.test(v.name) ? 5 : 2) * 1048576) big = [k, v]; });
      if (big) {
        this.errors = {}; this.errors[big[0]] = this.message = rmT(/\.xlsx$/i.test(big[1].name) ? "bigExcel" : "bigImage");
        return Promise.resolve({ ok: false, errors: this.errors, message: this.message });
      }
      this.busy = true;
      if (ev.submitter && ev.submitter.name) body.append(ev.submitter.name, ev.submitter.value);
      // Atributdan olinadi: .formAction atribut bo'lmasa joriy sahifa manzilini, .action esa name="action" maydonini qaytaradi
      return fetch((ev.submitter && ev.submitter.getAttribute("formaction")) || form.getAttribute("action") || location.href, {
        method: "POST", body: body, credentials: "same-origin",
        headers: { "Accept": "application/json", "X-CSRFToken": (document.querySelector('meta[name="csrf-token"]') || {}).content || "" }
      }).then(function (r) {
        return r.json().catch(function () { return { ok: false, message: rmT("badServer") + " (" + r.status + ")" }; });
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
        self.message = j.message || j.error || rmT("fixErrors");
        // Birinchi xato maydonga fokus
        var first = Object.keys(self.errors)[0];
        var el = first && form.querySelector('[name="' + first + '"]');
        if (el) el.focus();
        return j;
      }).catch(function () {
        self.busy = false;
        self.message = rmT("offline");
      });
    }
  };
  return window.rmMix(base, extra);
};

/* Telefon/email formatini brauzerda tekshirish (server bilan bir xil qoida: forms.py PHONE_RE, EMAIL_RE).
   «Kod yuborish» tugmasi faqat format to'g'ri bo'lganda faollashadi. only: "phone" | "email" | undefined (ikkalasi) */
window.rmIsEmail = function (v) { return /^[A-Za-z0-9._%+-]{1,64}@(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24}$/.test((v || "").trim()) && v.trim().length <= 254; };
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
      }).catch(function () { self.pwChecking = false; last = null; self.errors = Object.assign({}, self.errors, { pw: rmT("offlineShort") }); });
    }
  };
};

(function () {
  "use strict";

  // HTML ichidagi onclick/onchange o'rniga (Content-Security-Policy inline hodisalarni taqiqlaydi):
  // data-print — chop etish, data-reload — sahifani yangilash, data-back — orqaga, data-autosubmit — tanlanganda yuborish
  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest("[data-print], [data-reload], [data-back]");
    if (!t) return;
    if (t.hasAttribute("data-print")) window.print();
    else if (t.hasAttribute("data-reload")) location.reload();
    else history.back();
  });
  document.addEventListener("change", function (e) {
    if (e.target.matches && e.target.matches("[data-autosubmit]") && e.target.form) e.target.form.submit();
  });

  // Matnni nusxalash: data-copy-text="…" (masalan, taklif havolasi)
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-copy-text]");
    if (!b) return;
    var text = b.getAttribute("data-copy-text");
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(function () {
      window.rmToast(rmT("copied"));
    }).catch(function () { window.prompt(rmT("copyManually"), text); });
  });

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
    if (!b || b.dataset.copied) return;   // ketma-ket bosilsa «Nusxalandi» matni asl tugma o'rniga saqlanib qolmasin
    var pre = b.closest(".code").querySelector("pre");
    if (navigator.clipboard) navigator.clipboard.writeText(pre.innerText).catch(function () {});
    var old = b.innerHTML;
    b.dataset.copied = "1";
    b.textContent = rmT("copied");
    setTimeout(function () { b.innerHTML = old; delete b.dataset.copied; }, 1400);
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
    if (t.tagName !== "INPUT" || !t.closest(".otp")) return;
    t.value = t.value.replace(/\D/g, "").slice(0, 1);
    if (t.value && t.nextElementSibling) t.nextElementSibling.focus();
  });
  document.addEventListener("keydown", function (e) {
    var t = e.target;
    if (t.closest && t.closest(".otp") && e.key === "Backspace" && !t.value && t.previousElementSibling) {
      t.previousElementSibling.focus();
    }
  });
  // OTP: butun kodni (masalan, Telegram'dan nusxalangan «123456») qo'yganda kataklarga taqsimlanadi
  document.addEventListener("paste", function (e) {
    var t = e.target, box = t.closest && t.closest(".otp");
    if (!box) return;
    var digits = ((e.clipboardData || window.clipboardData).getData("text") || "").replace(/\D/g, "");
    if (digits.length < 2) return;
    e.preventDefault();
    var cells = Array.prototype.slice.call(box.querySelectorAll("input"));
    var start = Math.max(0, cells.indexOf(t));
    cells.slice(start).forEach(function (c, i) { if (digits[i] !== undefined) c.value = digits[i]; });
    var last = cells[Math.min(start + digits.length, cells.length) - 1];
    if (last) last.focus();
    box.dispatchEvent(new Event("input", { bubbles: true }));
  });

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

  // Serverdan kelgan flash xabarlar (JS'siz yuborilgan formalar) → toast
  document.querySelectorAll("[data-flash]").forEach(function (el) {
    try { JSON.parse(el.dataset.flash).forEach(function (m, i) { setTimeout(function () { window.rmToast(m); }, i * 2600); }); } catch (e) {}
  });

  // O'rnatilgan ilova (PWA) ekani — faqat umumiy statistika uchun (services/activity.py)
  if (window.matchMedia("(display-mode: standalone)").matches || navigator.standalone) document.cookie = "rm_pwa=1; path=/; max-age=31536000; samesite=lax";

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
})();
