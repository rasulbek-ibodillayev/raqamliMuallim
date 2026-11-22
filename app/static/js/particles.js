/* AI foni: sekin suzuvchi nuqtalar va ularni bog'lovchi ingichka chiziqlar («neyron tarmoq»).
   Kirish sahifalarida (canvas.auth-bg) to'liq, ilova va panellarda (canvas.ai-bg) yengilroq: data-density — zichlik.
   Kutubxonasiz, telefon uchun yengil:
   - nuqtalar soni ekran maydoniga qarab (telefonda kamroq);
   - sahifa ko'rinmay qolganda (boshqa ilovaga o'tilganda) animatsiya to'xtaydi;
   - «harakatni kamaytirish» yoki trafikni tejash yoqilgan bo'lsa — faqat harakatsiz rasm chiziladi;
   - ranglar --pt-1/2/3 dan olinadi (odatda AI ranglari). Dam olish rad etilib fon sarg'ish/qizg'ish tusga
     o'tganda (html[data-strain]) ular ham shu fonga mos iliq tuslarga sekin (fon bilan birga) o'tadi;
     yorug'/qorong'i mavzu almashsa ham yangilanadi. */
(function () {
  "use strict";
  var canvas = document.querySelector("canvas.auth-bg, canvas.ai-bg");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var saveData = !!(navigator.connection && navigator.connection.saveData);

  var density = parseFloat(canvas.dataset.density) || 1;
  var W = 0, H = 0, dpr = 1, pts = [], colors = [], dark = false, linkDist = 110;
  var raf = 0, last = 0, running = false;
  // Rang almashinuvi: from → to, FADE ms davomida (fon rangining .8s o'tishi bilan bir xil)
  var FADE = 800, fromRgb = null, toRgb = null, fadeStart = 0, fading = 0;

  // Har qanday CSS rangini [r, g, b] ga aylantiradi (canvas o'zi normallashtiradi)
  function rgb(c) {
    ctx.fillStyle = "#000"; ctx.fillStyle = c;
    var v = ctx.fillStyle;
    if (v.charAt(0) === "#") return [1, 3, 5].map(function (i) { return parseInt(v.substr(i, 2), 16); });
    var m = v.match(/[\d.]+/g) || [0, 0, 0];
    return [+m[0], +m[1], +m[2]];
  }
  function css(a) { return "rgb(" + a.map(Math.round).join(",") + ")"; }

  function readColors(animate) {
    var s = getComputedStyle(root);
    var next = ["--pt-1", "--pt-2", "--pt-3"].map(function (v, i) {
      return rgb(s.getPropertyValue(v).trim() || s.getPropertyValue("--ai-" + (i + 1)).trim() || "#2563eb");
    });
    dark = s.colorScheme === "dark" || root.dataset.theme === "dark" ||
      (!root.dataset.theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (animate && toRgb && animated()) { fromRgb = current(); toRgb = next; fadeStart = performance.now(); fading = 1; }
    else { fromRgb = toRgb = next; fading = 0; }
    colors = toRgb.map(css);
  }
  function current() {
    if (!fading) return toRgb;
    var k = Math.min(1, (performance.now() - fadeStart) / FADE);
    return toRgb.map(function (c, i) { return c.map(function (v, j) { return fromRgb[i][j] + (v - fromRgb[i][j]) * k; }); });
  }
  function blend() {
    if (!fading) return;
    var cur = current();
    colors = cur.map(css);
    if (performance.now() - fadeStart >= FADE) fading = 0;
  }

  function size() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    linkDist = W < 640 ? 120 : 140;
    // ~1 nuqta har 14 000 px² ga; telefonda ~22–30, katta ekranda 64 tagacha
    var n = Math.round(Math.max(22, Math.min(64, Math.round(W * H / 14000))) * density);
    while (pts.length < n) pts.push(make());
    pts.length = n;
    pts.forEach(function (p) { p.x = Math.min(p.x, W); p.y = Math.min(p.y, H); });
  }

  function make() {
    var a = Math.random() * Math.PI * 2, v = 6 + Math.random() * 10; // px/soniya — juda sekin
    return { x: Math.random() * W, y: Math.random() * H, vx: Math.cos(a) * v, vy: Math.sin(a) * v,
      r: 1.2 + Math.random() * 1.6, c: Math.floor(Math.random() * 3) };
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    var dotA = dark ? 0.7 : 0.55, lineA = dark ? 0.32 : 0.22;
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      for (var j = i + 1; j < pts.length; j++) {
        var q = pts[j], dx = p.x - q.x, dy = p.y - q.y, d2 = dx * dx + dy * dy;
        if (d2 < linkDist * linkDist) {
          ctx.globalAlpha = lineA * (1 - Math.sqrt(d2) / linkDist);
          ctx.strokeStyle = colors[p.c];
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        }
      }
    }
    for (var k = 0; k < pts.length; k++) {
      var o = pts[k];
      ctx.globalAlpha = dotA;
      ctx.fillStyle = colors[o.c];
      ctx.beginPath(); ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function step(t) {
    var dt = Math.min((t - (last || t)) / 1000, 0.05); // fon tabdan qaytganda nuqtalar «sakramasin»
    last = t;
    blend();
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      p.x += p.vx * dt; p.y += p.vy * dt;
      if (p.x < -10) p.x = W + 10; else if (p.x > W + 10) p.x = -10;
      if (p.y < -10) p.y = H + 10; else if (p.y > H + 10) p.y = -10;
    }
    draw();
    raf = requestAnimationFrame(step);
  }

  function animated() { return !reduce.matches && !saveData && !document.hidden; }
  function start() { if (running || !animated()) return; running = true; last = 0; raf = requestAnimationFrame(step); }
  function stop() { running = false; cancelAnimationFrame(raf); }
  function refresh() { stop(); draw(); start(); }

  readColors(); size(); draw(); start();

  var rt;
  window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { size(); draw(); }, 150); });
  document.addEventListener("visibilitychange", function () { document.hidden ? stop() : start(); });
  if (reduce.addEventListener) reduce.addEventListener("change", refresh);
  // Mavzu tugmasi data-theme ni, dam olish moduli (learner.js) data-strain ni o'zgartiradi; tizim mavzusi ham kuzatiladi
  new MutationObserver(function () { readColors(true); if (!running) draw(); })
    .observe(root, { attributes: true, attributeFilter: ["data-theme", "data-strain"] });
  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  if (mq.addEventListener) mq.addEventListener("change", function () { readColors(); draw(); });
})();
