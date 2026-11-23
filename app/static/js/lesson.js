/* raqamliMuallim — dars sahifasi: mundarija, o'qilgan joydan davom ettirish, belgilangan matn menyusi */

(function () {
  "use strict";

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
        window.rmToast(rmT("resume") + " " + name, rmT("fromStart"), function () {
          window.scrollTo({ top: 0, behavior: "smooth" });
          try { localStorage.removeItem(key); } catch (e) {}
        });
      }, 150);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", lessonNav); else lessonNav();

  // «Mavzu testini boshlash» — mavzu birinchi marta oxirigacha ko'rib chiqilgach paydo bo'ladi.
  // Bir marta ko'rilgani qurilmada eslab qolinadi (keyingi kirishda tugma darhol ko'rinadi).
  function endGate() {
    var foot = document.querySelector("[data-end-gate]");
    var end = document.querySelector("[data-lesson-end]");
    var art = document.querySelector("[data-resume]");
    if (!foot || !end || !art) return;
    var key = "lesson-end:" + art.dataset.resume;
    var seen = false;
    try { seen = localStorage.getItem(key) === "1"; } catch (e) {}
    if (seen || !("IntersectionObserver" in window)) return;
    foot.classList.add("is-gated");
    var io = new IntersectionObserver(function (entries) {
      if (!entries.some(function (en) { return en.isIntersecting; })) return;
      foot.classList.remove("is-gated");
      try { localStorage.setItem(key, "1"); } catch (e) {}
      io.disconnect();
    });
    io.observe(end);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", endGate); else endGate();

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
    selMenu.className = "sel-menu"; selMenu.setAttribute("role", "toolbar"); selMenu.setAttribute("aria-label", rmT("selection"));
    selMenu.style.left = (r.left + r.width / 2 + window.scrollX) + "px";
    selMenu.style.top = (r.top + window.scrollY) + "px";
    selMenu.innerHTML =
      '<button type="button" data-act="note"><svg class="ico ico-sm" aria-hidden="true"><use href="#i-bookmark"/></svg></button>' +
      '<button type="button" data-act="ai"><svg class="ico ico-sm" aria-hidden="true"><use href="#i-sparkle"/></svg></button>';
    selMenu.querySelector('[data-act="note"]').appendChild(document.createTextNode(rmT("toNote")));
    selMenu.querySelector('[data-act="ai"]').appendChild(document.createTextNode(rmT("askAi")));
    selMenu.addEventListener("mousedown", function (e) { e.preventDefault(); });
    selMenu.addEventListener("click", function (e) {
      var act = e.target.closest("button") && e.target.closest("button").dataset.act;
      if (act === "note") {
        try {
          var inbox = JSON.parse(localStorage.getItem("rm-notes-inbox") || "[]");
          inbox.push({ id: Date.now(), topic: box.dataset.topic || rmT("general"), title: "", text: text, code: "", when: rmT("today") });
          localStorage.setItem("rm-notes-inbox", JSON.stringify(inbox));
        } catch (err) {}
        window.rmToast(rmT("noteSaved"));
      } else if (act === "ai") {
        location.href = box.dataset.tutorUrl + "?q=" + encodeURIComponent(rmT("explain", { t: text.slice(0, 300) }));
      }
      hideSel(); s.removeAllRanges();
    });
    document.body.appendChild(selMenu);
  }
  document.addEventListener("mouseup", function (e) { if (!(e.target.closest && e.target.closest(".sel-menu"))) setTimeout(showSel, 0); });
  document.addEventListener("touchend", function () { setTimeout(showSel, 250); });
  document.addEventListener("keyup", function (e) { if (e.shiftKey) showSel(); if (e.key === "Escape") hideSel(); });
  window.addEventListener("scroll", hideSel, { passive: true });
})();
