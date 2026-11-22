/* Kirish sahifalari foni: sekin suzuvchi nuqtalar va ularni bog'lovchi ingichka chiziqlar («neyron tarmoq»).
   Kutubxonasiz, telefon uchun yengil:
   - nuqtalar soni ekran maydoniga qarab (telefonda kamroq);
   - sahifa ko'rinmay qolganda (boshqa ilovaga o'tilganda) animatsiya to'xtaydi;
   - «harakatni kamaytirish» yoki trafikni tejash yoqilgan bo'lsa — faqat harakatsiz rasm chiziladi;
   - ranglar dizayn tizimidagi --ai-1/2/3 dan olinadi, yorug'/qorong'i mavzu almashsa yangilanadi. */
(function () {
  "use strict";
  var canvas = document.querySelector("canvas.auth-bg");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var saveData = !!(navigator.connection && navigator.connection.saveData);

  var W = 0, H = 0, dpr = 1, pts = [], colors = [], dark = false, linkDist = 110;
  var raf = 0, last = 0, running = false;

  function readColors() {
    var s = getComputedStyle(root);
    colors = ["--ai-1", "--ai-2", "--ai-3"].map(function (v) { return s.getPropertyValue(v).trim() || "#2563eb"; });
    dark = s.colorScheme === "dark" || root.dataset.theme === "dark" ||
      (!root.dataset.theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  function size() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    linkDist = W < 640 ? 120 : 140;
    // ~1 nuqta har 14 000 px² ga; telefonda ~22–30, katta ekranda 64 tagacha
    var n = Math.max(22, Math.min(64, Math.round(W * H / 14000)));
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
  // Mavzu tugmasi data-theme ni o'zgartiradi; tizim mavzusi ham kuzatiladi
  new MutationObserver(function () { readColors(); draw(); }).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  if (mq.addEventListener) mq.addEventListener("change", function () { readColors(); draw(); });
})();
