/* raqamliMuallim — ekspert: «Mavzular va darslar» muharriri (templates/expert/topics.html).
   Daraxt har amaldan keyin serverdan yangilanadi; dars butunlay saqlanadi (rev — bir vaqtda tahrirlashdan himoya). */
window.rmContentEditor = function (cfg) {
  var T = cfg.t;
  function token() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ""; }
  function call(url, body, form) {
    var h = { Accept: "application/json", "X-CSRFToken": token() };
    if (body && !form) h["Content-Type"] = "application/json";
    return fetch(url, { method: body ? "POST" : "GET", headers: h, body: body ? (form ? body : JSON.stringify(body)) : undefined })
      .catch(function () { throw new Error(rmT("offlineShort")); })
      .then(function (r) {
        return r.json().catch(function () { throw new Error(rmT("badServer")); }).then(function (j) {
          if (!r.ok || !j.ok) throw new Error(j.error || rmT("notSaved"));
          return j;
        });
      });
  }
  return {
    topics: cfg.tree, sel: null, lesson: null, q: "", kinds: cfg.kinds, templates: cfg.templates,
    mode: "", value: "", target: null, err: "", busy: false, clean: "", lessonErr: "",
    init: function () {
      var self = this, p = new URLSearchParams(location.search), l = Number(p.get("dars"));
      var hit = this.topics.find(function (t) { return t.lessons.some(function (x) { return x.id === l; }); });
      this.sel = hit ? hit.id : (this.topics[0] && this.topics[0].id);
      if (hit) this.openLesson(l);
      window.addEventListener("beforeunload", function (e) { if (self.dirty()) { e.preventDefault(); e.returnValue = ""; } });
    },
    filtered: function () {
      var q = this.q.toLowerCase();
      return this.topics.filter(function (t) { return !q || (t.name + " " + t.lessons.map(function (l) { return l.name; }).join(" ")).toLowerCase().indexOf(q) !== -1; });
    },
    topic: function () { var id = this.sel; return this.topics.find(function (t) { return t.id === id; }); },
    body: function () {
      var l = this.lesson;
      return { rev: l.rev, name: l.name, minutes: Number(l.minutes) || null, published: !!l.published, subs: l.subs.map(function (s) {
        return { id: s.id, name: s.name, weight: Number(s.weight), generators: s.generators,
                 blocks: s.blocks.map(function (b) { return { id: b.id, kind: b.kind, data: b.data }; }) };
      }) };
    },
    dirty: function () { return !!this.lesson && JSON.stringify(this.body()) !== this.clean; },
    leave: function () { return !this.dirty() || confirm(T.unsaved); },
    setLesson: function (l) {
      var n = 0;
      l.subs.forEach(function (s) { s.key = ++n; s.open = l.subs.length < 4; s.blocks.forEach(function (b) { b.key = ++n; }); });
      this.nextKey = n; this.lesson = l; this.lessonErr = ""; this.clean = JSON.stringify(this.body());
    },
    key: function () { return ++this.nextKey; },
    pick: function (id) { if (!this.leave()) return; this.sel = id; this.lesson = null; this.close(); },
    closeLesson: function () { if (this.leave()) this.lesson = null; },
    openLesson: function (id) {
      var self = this;
      call(cfg.urls.lesson.replace("/0", "/" + id)).then(function (j) { self.setLesson(j.lesson); self.close(); window.scrollTo({ top: 0 }); })
        .catch(function (e) { rmToast(e.message); });
    },
    /* Ichki kartalar: topic-new | topic-edit | topic-delete | lesson-new | lesson-delete */
    open: function (mode, arg) {
      var self = this, ref = { "topic-new": "newTopic", "topic-edit": "editTopic", "lesson-new": "newLesson" }[mode];
      this.mode = mode; this.err = ""; this.target = mode === "lesson-delete" ? arg : null;
      this.value = mode === "topic-edit" ? arg : "";
      if (ref) this.$nextTick(function () { self.$refs[ref] && self.$refs[ref].focus(); });
    },
    close: function () { this.mode = ""; this.value = ""; this.err = ""; this.target = null; },
    op: function (data, msg) {
      var self = this;
      if (this.busy) return Promise.resolve(null);
      this.busy = true;
      return call(cfg.urls.api, data).then(function (j) { self.topics = j.tree; self.close(); if (msg) rmToast(msg); return j; })
        .catch(function (e) { self.err = e.message; if (!self.mode) rmToast(e.message); return null; })
        .finally(function () { self.busy = false; });
    },
    saveTopic: function () {
      var self = this, editing = this.mode === "topic-edit";
      this.op({ op: "section_save", id: editing ? this.sel : null, name: this.value }, T.savedTopic)
        .then(function (j) { if (j && !editing) { self.sel = j.id; self.lesson = null; } });
    },
    deleteTopic: function () {
      var self = this;
      this.op({ op: "section_delete", id: this.sel }, T.deleted)
        .then(function (j) { if (j) { self.sel = self.topics[0] && self.topics[0].id; self.lesson = null; } });
    },
    addLesson: function () {
      var self = this;
      this.op({ op: "lesson_add", section_id: this.sel, name: this.value }, T.savedLesson).then(function (j) { if (j) self.openLesson(j.id); });
    },
    deleteLesson: function (l) { this.op({ op: "lesson_delete", id: l.id }, T.deleted); },
    move: function (kind, id, step) { this.op({ op: "move", kind: kind, id: id, step: step }); },

    /* ---- Dars ---- */
    save: function () {
      var self = this;
      if (this.busy) return;
      this.busy = true; this.lessonErr = "";
      call(cfg.urls.lesson.replace("/0", "/" + this.lesson.id), this.body()).then(function (j) {
        var opened = {}; self.lesson.subs.forEach(function (s) { opened[s.name.trim()] = s.open; });
        self.setLesson(j.lesson); self.topics = j.tree;
        self.lesson.subs.forEach(function (s) { if (s.name in opened) s.open = opened[s.name]; });
        rmToast(T.saved);
      }).catch(function (e) { self.lessonErr = e.message; })
        .finally(function () { self.busy = false; });
    },
    addSub: function () { this.lesson.subs.push({ id: null, key: this.key(), name: "", weight: 1, generators: [], questions: 0, blocks: [], open: true }); },
    removeSub: function (i) {
      var s = this.lesson.subs[i];
      if (s.questions) { rmToast(T.hasQuestions); return; }
      if (!s.blocks.length || confirm(T.confirmSub)) this.lesson.subs.splice(i, 1);
    },
    swap: function (list, i, d) { if (list[i + d]) list.splice(i + d, 0, list.splice(i, 1)[0]); },
    addBlock: function (s, kind) {
      var empty = { text: { title: "", body: "" }, code: { title: "", code: "", lang: "" }, image: { src: "", alt: "", caption: "" },
                    table: { title: "", body: "", head: true }, mermaid: { title: "", code: "", alt: "" }, formula: { title: "", tex: "" },
                    video: { title: "", url: "" }, callout: { title: "", body: "" }, links: { links: [{ title: "", url: "" }] } };
      s.blocks.push({ id: null, key: this.key(), kind: kind, data: JSON.parse(JSON.stringify(empty[kind])) });
    },
    known: function (k) { return this.kinds.some(function (x) { return x[0] === k; }); },
    icon: function (k) { var x = this.kinds.find(function (y) { return y[0] === k; }); return x ? x[1] : "note"; },
    label: function (k) { var x = this.kinds.find(function (y) { return y[0] === k; }); return x ? x[2] : k; },
    rows: function (body) { return (body || "").split("\n").filter(function (r) { return r.trim(); }).map(function (r) { return r.split("|").map(function (c) { return c.trim(); }); }); },
    upload: function (b, ev) {
      var f = ev.target.files[0], form = new FormData();
      if (!f) return;
      form.append("image", f);
      call(cfg.urls.image, form, true).then(function (j) { b.data.src = j.src; }).catch(function (e) { rmToast(e.message); ev.target.value = ""; });
    },
    src: function (s) { return cfg.urls.static + s; }
  };
};
