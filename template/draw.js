/* ===========================================================================
   FLOW_VIZ — draw.js
   Mounts every figure.fv-drawing: one JSON spec and one div.fv-depth of HTML
   sections. Everything else is drawn and wired here — grid layout, orthogonal
   routing, lanes, motion, peek, drawer, walkthrough, sequence, segments and
   notes — so a fix reaches every drawing on a plain rebuild.

   Layout is pure functions over a spec (window.FVDRAW.layout / crossings /
   throughBoxes), so the audit measures every canvas, segments included,
   without drawing any of them.

   State goes through window.FLOWVIZ (flow.js) when it is there:
     state.notes['<drawing>/[<segment>/]<node|edge|step>:<id>'] = {text, at}
     state.ui.draw[<drawing>] = {flow, view, labels, times, key}
     state.ui.motion === false   ->  <html class="still">
   Without flow.js the same shape lives in localStorage only.
   =========================================================================== */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  /* one grid for every drawing: agents place boxes in cells, never in pixels */
  var G = { cw: 240, ch: 132, nw: 172, nh: 56, px: 22, py: 18, r: 10, lane: 4.5 };
  var LABEL_ROOM = G.nw - 55 - 12;      // width a box label may use before it shrinks
  var KIND = { client: 'client', edge: 'edge', service: 'service', data: 'data', stream: 'stream', external: 'ext',
              threat: 'threat' };
  var KIND_NAME = { client: 'Client', edge: 'Edge', service: 'Service', data: 'Data', stream: 'Event stream', external: 'External',
                   threat: 'Threat' };
  var TONES = ['f1', 'f2', 'f3'];
  var reduce = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

  /* ── helpers ───────────────────────────────────────────────────────────── */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function el(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function h(tag, cls, html, parent) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    if (parent) parent.appendChild(n);
    return n;
  }
  function f(n) { return Math.round(n * 10) / 10; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function words(s) { return String(s || '').trim().split(/\s+/).filter(Boolean).length; }
  function ease(k) { return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; }
  function tone(i) { return TONES[i % TONES.length]; }
  function kindVar(k) { return 'var(--' + (KIND[k] || 'service') + ')'; }
  function icon(name) { return '<svg aria-hidden="true"><use href="#i-' + esc(name) + '"/></svg>'; }

  /* ── state bridge ──────────────────────────────────────────────────────── */
  var FV = window.FLOWVIZ || null;
  var LKEY = 'flowviz:' + ((window.FLOW && window.FLOW.doc) || 'drawing');
  var local = null, saveT = null;
  function state() {
    if (FV && FV.state) return FV.state;
    if (!local) {
      try { local = JSON.parse(localStorage.getItem(LKEY) || '{}') || {}; } catch (e) { local = {}; }
    }
    return local;
  }
  function save() {
    if (FV && FV.save) { FV.save(); return; }
    clearTimeout(saveT);
    saveT = setTimeout(function () {
      try { local.savedAt = new Date().toISOString(); localStorage.setItem(LKEY, JSON.stringify(local)); } catch (e) {}
    }, 400);
  }
  function uiAll() { var s = state(); if (!s.ui || typeof s.ui !== 'object') s.ui = {}; return s.ui; }
  function uiDraw(id) { var u = uiAll(); if (!u.draw || typeof u.draw !== 'object') u.draw = {}; return (u.draw[id] = u.draw[id] || {}); }
  function notes() { var s = state(); if (!s.notes || typeof s.notes !== 'object') s.notes = {}; return s.notes; }
  function noteText(n) { return n == null ? '' : typeof n === 'string' ? n : (n.text || ''); }
  function motionOn() { return uiAll().motion !== false; }
  function still() { return !motionOn() || reduce.matches; }
  function ptTime(iso) {
    if (FV && FV.ptTime) return FV.ptTime(iso);
    var d = new Date(iso);
    return isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  /* ── geometry: pure, over a spec ───────────────────────────────────────── */
  function cellBox(at) {
    var cx = G.px + at[0] * G.cw + G.cw / 2, cy = G.py + at[1] * G.ch + G.ch / 2;
    return { cx: cx, cy: cy, x: cx - G.nw / 2, y: cy - G.nh / 2, w: G.nw, h: G.nh };
  }
  function sidePoint(b, side, off) {
    if (side === 'r') return { x: b.x + b.w, y: b.cy + off };
    if (side === 'l') return { x: b.x, y: b.cy + off };
    if (side === 'b') return { x: b.cx + off, y: b.y + b.h };
    return { x: b.cx + off, y: b.y };
  }
  function zoneRect(z) {
    var c = z.cols || [0, 0], r = z.rows || [0, 0];
    return { x: G.px + c[0] * G.cw + 8, y: G.py + r[0] * G.ch + 6,
             w: (c[1] - c[0] + 1) * G.cw - 16, h: (r[1] - r[0] + 1) * G.ch - 12 };
  }
  /* a connection leaves the side that faces its target; bends live in the gutter */
  function plan(e, nodes) {
    var a = nodes[e.from], b = nodes[e.to];
    if (!a || !b || !a.at || !b.at) return null;
    var dc = b.at[0] - a.at[0], dr = b.at[1] - a.at[1];
    if (!dc && !dr) return null;
    var kind = e.route;
    if (kind === 'h' && dr) kind = 'hvh';
    if (kind === 'v' && dc) kind = 'vhv';
    if ((kind === 'hvh' || kind === 'vhv') && (!dc || !dr)) kind = null;
    if (kind !== 'h' && kind !== 'v' && kind !== 'hvh' && kind !== 'vhv') {
      kind = dr === 0 ? 'h' : dc === 0 ? 'v' : Math.abs(dc) >= Math.abs(dr) ? 'hvh' : 'vhv';
    }
    var horiz = kind === 'h' || kind === 'hvh';
    return {
      e: e, a: a, b: b, kind: kind,
      sa: horiz ? (dc > 0 ? 'r' : 'l') : (dr > 0 ? 'b' : 't'),
      sb: horiz ? (dc > 0 ? 'l' : 'r') : (dr > 0 ? 't' : 'b')
    };
  }
  function layout(spec) {
    var nodes = {}, boxes = {};
    (spec.nodes || []).forEach(function (n) {
      if (!n || !n.id) return;
      nodes[n.id] = n;
      if (Array.isArray(n.at)) boxes[n.id] = cellBox(n.at);
    });
    var grid = spec.grid || { cols: 1, rows: 1 };
    var plans = [], sides = {};
    (spec.edges || []).forEach(function (e) { var p = plan(e, nodes); if (p) plans.push(p); });
    plans.forEach(function (p) {
      (sides[p.e.from + ':' + p.sa] = sides[p.e.from + ':' + p.sa] || []).push({ p: p, end: 'a' });
      (sides[p.e.to + ':' + p.sb] = sides[p.e.to + ':' + p.sb] || []).push({ p: p, end: 'b' });
    });
    /* straight connections own the centre of a side; bent ones fan out beside them */
    Object.keys(sides).forEach(function (k) {
      var list = sides[k], side = k.slice(k.lastIndexOf(':') + 1), horiz = side === 'l' || side === 'r';
      var self = nodes[k.slice(0, k.lastIndexOf(':'))], selfKey = horiz ? self.at[1] : self.at[0];
      function key(it) { var o = it.end === 'a' ? it.p.b : it.p.a; return horiz ? o.at[1] : o.at[0]; }
      function isStraight(it) { return it.p.kind === 'h' || it.p.kind === 'v'; }
      var straight = list.filter(isStraight), bent = list.filter(function (it) { return !isStraight(it); });
      straight.forEach(function (it) { it.p['off' + it.end] = 0; });
      if (straight.length) {
        bent.filter(function (it) { return key(it) < selfKey; })
          .sort(function (m, n) { return key(n) - key(m); })
          .forEach(function (it, i) { it.p['off' + it.end] = -14 * (i + 1); });
        bent.filter(function (it) { return key(it) >= selfKey; })
          .sort(function (m, n) { return key(m) - key(n); })
          .forEach(function (it, i) { it.p['off' + it.end] = 14 * (i + 1); });
      } else {
        bent.sort(function (m, n) { return key(m) - key(n); })
          .forEach(function (it, i) { it.p['off' + it.end] = (i - (bent.length - 1) / 2) * 14; });
      }
    });
    plans.forEach(function (p) {
      var A = boxes[p.e.from], B = boxes[p.e.to];
      var P0 = sidePoint(A, p.sa, p.offa || 0), P3 = sidePoint(B, p.sb, p.offb || 0), pts;
      if (p.kind === 'h' || p.kind === 'v') pts = [P0, P3];
      else if (p.kind === 'hvh') {
        var mx = (P0.x + P3.x) / 2;
        pts = [P0, { x: mx, y: P0.y }, { x: mx, y: P3.y }, P3];
      } else {
        var my = (P0.y + P3.y) / 2;
        pts = [P0, { x: P0.x, y: my }, { x: P3.x, y: my }, P3];
      }
      p.pts = pts.filter(function (q, i) { return !i || Math.hypot(q.x - pts[i - 1].x, q.y - pts[i - 1].y) > 0.5; });
      p.lanes = p.e.both
        ? [{ dir: 1, pts: offsetPoly(p.pts, G.lane) }, { dir: -1, pts: offsetPoly(p.pts.slice().reverse(), G.lane) }]
        : [{ dir: 1, pts: p.pts }];
    });
    return {
      spec: spec, nodes: nodes, boxes: boxes, plans: plans,
      zones: (spec.zones || []).map(function (z) { return { z: z, r: zoneRect(z) }; }),
      W: G.px * 2 + (grid.cols || 1) * G.cw, H: G.py * 2 + (grid.rows || 1) * G.ch
    };
  }
  /* shift an orthogonal polyline sideways: two lanes for a two-way connection */
  function offsetPoly(pts, d) {
    if (pts.length < 2) return pts.slice();
    var segs = [];
    for (var i = 0; i < pts.length - 1; i++) {
      var p = pts[i], q = pts[i + 1], dx = q.x - p.x, dy = q.y - p.y, L = Math.hypot(dx, dy) || 1;
      var nx = -dy / L * d, ny = dx / L * d;
      segs.push([{ x: p.x + nx, y: p.y + ny }, { x: q.x + nx, y: q.y + ny }]);
    }
    var out = [segs[0][0]];
    for (var j = 1; j < segs.length; j++) {
      var s0 = segs[j - 1], s1 = segs[j], h0 = Math.abs(s0[0].y - s0[1].y) < 0.01;
      out.push(h0 ? { x: s1[0].x, y: s0[0].y } : { x: s0[0].x, y: s1[0].y });
    }
    out.push(segs[segs.length - 1][1]);
    return out;
  }
  function trimEnd(pts, d) {
    var out = pts.slice(), q = out[out.length - 1], p = out[out.length - 2];
    var L = Math.hypot(q.x - p.x, q.y - p.y) || 1, k = Math.max(0, (L - d) / L);
    out[out.length - 1] = { x: p.x + (q.x - p.x) * k, y: p.y + (q.y - p.y) * k };
    return out;
  }
  function roundPath(pts, r) {
    var d = 'M' + f(pts[0].x) + ' ' + f(pts[0].y);
    for (var i = 1; i < pts.length - 1; i++) {
      var p = pts[i - 1], c = pts[i], n = pts[i + 1];
      var l1 = Math.hypot(c.x - p.x, c.y - p.y) || 1, l2 = Math.hypot(n.x - c.x, n.y - c.y) || 1;
      var rr = Math.min(r, l1 / 2, l2 / 2);
      d += 'L' + f(c.x + (p.x - c.x) / l1 * rr) + ' ' + f(c.y + (p.y - c.y) / l1 * rr) +
           'Q' + f(c.x) + ' ' + f(c.y) + ' ' + f(c.x + (n.x - c.x) / l2 * rr) + ' ' + f(c.y + (n.y - c.y) / l2 * rr);
    }
    var e = pts[pts.length - 1];
    return d + 'L' + f(e.x) + ' ' + f(e.y);
  }
  /* a point part-way along a polyline, and whether that stretch is horizontal */
  function pointAt(pts, t) {
    var lens = [], total = 0;
    for (var i = 0; i < pts.length - 1; i++) {
      var l = Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y);
      lens.push(l); total += l;
    }
    var want = total * t;
    for (var j = 0; j < lens.length; j++) {
      if (want <= lens[j] || j === lens.length - 1) {
        var k = lens[j] ? Math.min(1, want / lens[j]) : 0, a = pts[j], b = pts[j + 1];
        return { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, horiz: Math.abs(b.y - a.y) < 0.5, len: total };
      }
      want -= lens[j];
    }
    return { x: pts[0].x, y: pts[0].y, horiz: true, len: total };
  }
  function segments(L) {
    var out = [];
    L.plans.forEach(function (p) {
      p.lanes.forEach(function (ln) {
        for (var i = 0; i < ln.pts.length - 1; i++) out.push({ id: p.e.id, a: ln.pts[i], b: ln.pts[i + 1] });
      });
    });
    return out;
  }
  function span(a, b) { return [Math.min(a, b), Math.max(a, b)]; }
  function segHit(p, q) {
    var E = 0.75, ph = Math.abs(p.a.y - p.b.y) < 0.5, qh = Math.abs(q.a.y - q.b.y) < 0.5;
    var px = span(p.a.x, p.b.x), py = span(p.a.y, p.b.y), qx = span(q.a.x, q.b.x), qy = span(q.a.y, q.b.y);
    if (ph && qh) return Math.abs(p.a.y - q.a.y) < 1 && Math.min(px[1], qx[1]) - Math.max(px[0], qx[0]) > 1;
    if (!ph && !qh) return Math.abs(p.a.x - q.a.x) < 1 && Math.min(py[1], qy[1]) - Math.max(py[0], qy[0]) > 1;
    var hs = ph ? { x: px, y: p.a.y } : { x: qx, y: q.a.y }, vs = ph ? { x: q.a.x, y: qy } : { x: p.a.x, y: py };
    return vs.x > hs.x[0] + E && vs.x < hs.x[1] - E && hs.y > vs.y[0] + E && hs.y < vs.y[1] - E;
  }
  /* pairs of connections that cross or run over each other */
  function crossings(L) {
    var s = segments(L), pairs = {};
    for (var i = 0; i < s.length; i++) {
      for (var j = i + 1; j < s.length; j++) {
        if (s[i].id !== s[j].id && segHit(s[i], s[j])) pairs[[s[i].id, s[j].id].sort().join(' × ')] = 1;
      }
    }
    return Object.keys(pairs);
  }
  /* connections whose route runs through a box that is not one of its ends */
  function throughBoxes(L) {
    var hits = {};
    L.plans.forEach(function (p) {
      for (var i = 0; i < p.pts.length - 1; i++) {
        var x = span(p.pts[i].x, p.pts[i + 1].x), y = span(p.pts[i].y, p.pts[i + 1].y);
        Object.keys(L.boxes).forEach(function (id) {
          if (id === p.e.from || id === p.e.to) return;
          var b = L.boxes[id];
          if (x[1] > b.x + 1 && x[0] < b.x + b.w - 1 && y[1] > b.y + 1 && y[0] < b.y + b.h - 1) hits[p.e.id + ' → ' + id] = 1;
        });
      }
    });
    return Object.keys(hits);
  }
  function restWords(spec) {
    var n = 0;
    (spec.nodes || []).forEach(function (x) { n += words(x.label); });
    (spec.zones || []).forEach(function (z) { n += words(z.label); });
    return n;
  }
  window.FVDRAW = { grid: G, layout: layout, crossings: crossings, throughBoxes: throughBoxes, restWords: restWords };

  /* ── page singletons: drawer, scrim, toast ─────────────────────────────── */
  var DR = null;
  function drawer() {
    if (DR) return DR;
    var scrim = h('div', 'fv-scrim', null, document.body);
    var d = h('aside', 'fv-drawer',
      '<div class="dr-hd"><div class="dr-ico"></div><div><p class="dr-kind"></p><h2 class="dr-title" id="fvDrawerTitle"></h2></div>' +
      '<button class="dr-x" type="button" aria-label="Close">' + icon('x') + '</button></div><div class="dr-body"></div>',
      document.body);
    d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'false');
    d.setAttribute('aria-labelledby', 'fvDrawerTitle'); d.setAttribute('aria-hidden', 'true');
    DR = { el: d, scrim: scrim, ico: $('.dr-ico', d), kind: $('.dr-kind', d), title: $('.dr-title', d),
           body: $('.dr-body', d), owner: null, what: null };
    $('.dr-x', d).addEventListener('click', closeDrawer);
    scrim.addEventListener('click', closeDrawer);
    return DR;
  }
  function closeDrawer() {
    if (!DR || !DR.owner) return;
    DR.el.classList.remove('on'); DR.el.setAttribute('aria-hidden', 'true');
    DR.scrim.classList.remove('on');
    var o = DR.owner;
    DR.owner = null; DR.what = null;
    o.select(null);
  }
  var toastEl = null, toastT = null;
  function toast(msg) {
    if (!toastEl) { toastEl = h('div', 'fv-toast', null, document.body); toastEl.setAttribute('role', 'status'); }
    toastEl.textContent = msg; toastEl.classList.add('on');
    clearTimeout(toastT); toastT = setTimeout(function () { toastEl.classList.remove('on'); }, 1600);
  }
  function copyText(text, btn, label) {
    function done(ok) {
      if (!ok) {             // no clipboard API here: fall back to a selection copy
        try {
          var ta = h('textarea', null, null, document.body);
          ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
          ta.select(); ok = document.execCommand('copy'); ta.remove();
        } catch (e) { ok = false; }
      }
      toast(ok ? (label || 'Copied') : 'Copy was blocked — select the text instead');
      if (btn && ok) {
        if (FV && FV.flash) FV.flash(btn, 'copied');
        else { var o = btn.innerHTML; btn.textContent = 'copied'; setTimeout(function () { btn.innerHTML = o; }, 1200); }
      }
    }
    try { navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); }); }
    catch (e) { done(false); }
  }

  /* ── instances, the keyboard, and the page-wide motion switch ──────────── */
  var INST = [], active = null;
  var PAGE_KIND = document.documentElement.getAttribute('data-kind') || (window.FLOW && window.FLOW.kind) || 'report';
  function keyTarget() { return active || (PAGE_KIND === 'drawing' ? INST[0] : null); }
  document.addEventListener('pointerdown', function (ev) {
    var fig = ev.target.closest && ev.target.closest('figure.fv-drawing');
    if (fig) { active = fig._fvd || active; return; }
    if (!(ev.target.closest && ev.target.closest('.fv-drawer'))) active = null;
  }, true);
  document.addEventListener('keydown', function (ev) {
    var t = ev.target;
    if (t && t.closest && t.closest('textarea, input, select, [contenteditable="true"]')) return;
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (ev.key === 'Escape' && DR && DR.owner) { closeDrawer(); return; }
    var d = keyTarget();
    if (!d) return;
    if (ev.key === 'Escape') { d.escape(); return; }
    if (d.view() === 'spec' || !d.hasFlows()) return;
    if (ev.key === 'ArrowRight') { ev.preventDefault(); d.stepBy(1); }
    else if (ev.key === 'ArrowLeft') { ev.preventDefault(); d.stepBy(-1); }
    else if (ev.key === ' ' && !(t && t.closest && t.closest('button, [role="button"], a, summary'))) {
      ev.preventDefault(); d.play();
    }
  });
  function paintMotion(b) {
    var on = motionOn();
    b.innerHTML = icon('motion') + (b.closest('.pill') ? (on ? 'motion' : 'still') : '<span>' + (on ? 'Motion' : 'Still') + '</span>');
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.title = on ? 'Motion is on — click to stop the drift and the packets' : 'Motion is off — click to let the flows move again';
  }
  function toggleMotion() {
    uiAll().motion = !motionOn();
    document.documentElement.classList.toggle('still', !motionOn());
    save();
    $$('.fv-motion').forEach(paintMotion);
    INST.forEach(function (d) { d.motionChanged(); });
  }
  function motionIntoPill() {
    var pill = document.getElementById('flowPill');
    if (!pill) return false;
    if (pill.querySelector('.fv-motion')) return true;
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'fv-motion';
    var dl = document.getElementById('flowDownload'), sep = h('span', 'sep');
    if (dl && dl.parentNode === pill) { pill.insertBefore(b, dl); pill.insertBefore(sep, dl); }
    else { pill.appendChild(sep); pill.appendChild(b); }
    paintMotion(b);
    b.addEventListener('click', toggleMotion);
    return true;
  }

  /* labels measured with the real CSS, off-screen, for every canvas */
  var scratch = null;
  function shrunkLabels(spec, host) {
    if (!scratch) {
      scratch = el('svg', { class: 'fv-map', 'aria-hidden': 'true', width: 10, height: 10,
        style: 'position:absolute;left:-9999px;top:0;width:10px;height:10px;min-width:0;visibility:hidden' });
    }
    if (scratch.parentNode !== host) host.appendChild(scratch);
    var g = el('g', { class: 'node' }, scratch), n = 0;
    (spec.nodes || []).forEach(function (x) {
      var t = el('text', { class: 'lbl' }, g);
      t.textContent = x.label || '';
      if (t.getComputedTextLength() > LABEL_ROOM + 1) n++;
    });
    g.remove();
    return n;
  }
  /* zone labels a connection runs through, measured where drawZone puts them */
  function zoneLabelHits(L, host) {
    shrunkLabels({ nodes: [] }, host);               // makes sure the scratch svg is mounted in host
    var g = el('g', { class: 'zone' }, scratch), hits = [], segs = segments(L);
    L.zones.forEach(function (zr) {
      var z = zr.z, r = zr.r, tag = z.tag || 'tl', right = tag[1] === 'r', bottom = tag[0] === 'b';
      var t = el('text', {}, g);
      t.textContent = z.label || '';
      var w = t.getComputedTextLength(), base = bottom ? r.y + r.h - 11 : r.y + 20;
      var x0 = (right ? r.x + r.w - 14 - w : r.x + 14) - 3, x1 = x0 + w + 6, y0 = base - 12, y1 = base + 4;
      segs.forEach(function (s) {
        var x = span(s.a.x, s.b.x), y = span(s.a.y, s.b.y);
        if (x[1] >= x0 && x[0] <= x1 && y[1] >= y0 && y[0] <= y1) hits.push('zone ' + z.id + ' label × ' + s.id);
      });
    });
    g.remove();
    return hits.filter(function (h, i) { return hits.indexOf(h) === i; });
  }

  /* ═════════════════════════ one drawing ═════════════════════════════════ */
  function Drawing(fig) {
    var script = null, DEPTH = null;
    Array.prototype.forEach.call(fig.children, function (c) {
      if (!script && c.tagName === 'SCRIPT' && /json/i.test(c.type)) script = c;
      if (!DEPTH && c.classList && c.classList.contains('fv-depth')) DEPTH = c;
    });
    if (!script) script = $('script[type="application/json"]', fig);
    if (!DEPTH) DEPTH = $('.fv-depth', fig);
    var ROOT;
    try { ROOT = JSON.parse(script ? script.textContent : ''); }
    catch (e) {
      h('p', 'fv-note', 'This drawing’s spec does not parse: ' + esc(e.message), fig);
      return null;
    }
    ROOT.nodes = ROOT.nodes || []; ROOT.edges = ROOT.edges || []; ROOT.flows = ROOT.flows || [];
    var ID = ROOT.id || ('drawing-' + (INST.length + 1));
    var PAGE = fig.getAttribute('data-mode') === 'page';
    var self = {};
    var S = {
      spec: ROOT, seg: null, flow: 0, step: -1, playing: false, run: 0, raf: null, timer: null,
      nodes: {}, edges: {}, nref: {}, eref: {}, lanes: [], seqRows: [], layer: {}, view: 'map', L: null
    };
    var R = {};
    var u0 = uiDraw(ID);
    S.flow = Math.min(Math.max(0, +u0.flow || 0), Math.max(0, ROOT.flows.length - 1));
    S.view = u0.view === 'seq' || u0.view === 'spec' ? u0.view : 'map';

    function flow() { return S.spec.flows[S.flow] || { label: '', summary: '', steps: [] }; }
    function scope(key) { return (S.seg ? S.seg + '/' : '') + key; }
    /* results: what a real run found — on a flow step, a connection or a box.
       pass = verified; fail = the target said no; error = the command was
       rejected, so the target was never asked. fail outranks error outranks pass. */
    var RES = {
      pass: { glyph: '✓', word: 'Passed', step: 'passed', tone: 'ok',
              note: 'The run verified this.' },
      fail: { glyph: '✕', word: 'Failed here', step: 'failed', tone: 'bad',
              note: 'The target said no here. That is evidence about the system.' },
      error: { glyph: '⚠\uFE0E', word: 'Rejected: the command never ran', step: 'rejected: the command never ran', tone: 'warn',
               note: 'The command was rejected before it reached the target, so this says nothing about the system. The defect is in the playbook.' }
    };
    var RANK = { pass: 1, error: 2, fail: 3 };
    function resultOf(x) { var r = x && x.result; return RES[r] ? r : null; }
    function stronger(a, b) { return !a ? b : !b ? a : (RANK[b] > RANK[a] ? b : a); }
    function hasFlows() { return (S.spec.flows || []).length > 0; }
    function flowOutcome(fl) {
      var steps = (fl && fl.steps) || [], rs = steps.map(resultOf).filter(Boolean);
      if (!rs.length) return null;
      if (rs.indexOf('fail') >= 0) return 'fail';
      if (rs.indexOf('error') >= 0) return 'error';
      return rs.length === steps.length ? 'pass' : null;
    }
    /* the flow's accent: green once every step passed, else its own tone */
    function flowAccent(i) { return flowOutcome(S.spec.flows[i]) === 'pass' ? 'var(--ok)' : 'var(--' + tone(i) + ')'; }
    /* the chip's dot says the outcome of a results flow at a glance */
    function chipColor(i) { var o = flowOutcome(S.spec.flows[i]); return o ? 'var(--' + RES[o].tone + ')' : 'var(--' + tone(i) + ')'; }
    function resBox(r) {
      return '<div class="box ' + RES[r].tone + ' fv-resbox"><p><b>' + RES[r].glyph + ' ' + esc(RES[r].word) + '.</b> ' + esc(RES[r].note) + '</p></div>';
    }
    function noteKey(key) { return ID + '/' + scope(key); }
    function ui() { return uiDraw(ID); }
    function persistUi(patch) { if (S.seg) return; var u = ui(); for (var k in patch) u[k] = patch[k]; save(); }

    /* ── the DOM the agent never writes ──────────────────────────────────── */
    function build() {
      fig.setAttribute('data-drawing', ID);
      if (PAGE) {
        R.head = h('header', 'fv-head',
          '<div class="fv-hd-top"><nav class="fv-crumbs" aria-label="Where you are in this drawing"></nav>' +
          '<div class="fv-tools"></div></div><h1 class="fv-title"></h1><p class="fv-lede"></p>');
      } else {
        R.head = h('figcaption', 'fv-fc',
          '<div class="fv-fc-top"><nav class="fv-crumbs" aria-label="Where you are in this drawing"></nav></div>' +
          '<div class="fv-fc-title"></div><p class="fv-fc-lede"></p>');
      }
      R.crumbs = $('.fv-crumbs', R.head);
      R.title = $('.fv-title, .fv-fc-title', R.head);
      R.lede = $('.fv-lede, .fv-fc-lede', R.head);
      R.tools = $('.fv-tools', R.head);

      R.strip = h('div', 'fv-strip');
      R.flows = h('div', 'fv-flows', null, R.strip);
      R.flows.setAttribute('role', 'radiogroup'); R.flows.setAttribute('aria-label', 'Flows');
      R.views = h('div', 'fv-views', null, R.strip);
      R.views.setAttribute('role', 'tablist'); R.views.setAttribute('aria-label', 'View');
      R.tabs = {};
      [['map', 'Map'], ['seq', 'Sequence'], ['spec', 'Spec']].forEach(function (v) {
        var b = h('button', null, v[1], R.views);
        b.type = 'button'; b.setAttribute('role', 'tab');
        b.addEventListener('click', function () { setView(v[0]); });
        R.tabs[v[0]] = b;
      });

      R.stage = h('section', 'fv-stage');
      R.stage.setAttribute('aria-label', 'System drawing');
      R.layers = h('div', 'fv-layers', null, R.strip);
      R.strip.insertBefore(R.layers, R.views);
      R.tg = {};
      [['labels', 'Labels', 'Protocols on every connection, technology under every box'],
       ['times', 'Timings', 'Latency on every connection'],
       ['key', 'Key', 'What the lines and badges mean']].forEach(function (t) {
        var b = h('button', null, '<span class="sw"></span>' + t[1], R.layers);
        b.type = 'button'; b.title = t[2];
        b.addEventListener('click', function () { var u = ui(); u[t[0]] = !u[t[0]]; save(); applyLayers(); });
        R.tg[t[0]] = b;
      });
      R.viewMap = h('div', 'fv-view fv-grid', '<div class="fv-scroll"><div class="fv-wrap"></div></div>', R.stage);
      R.wrap = $('.fv-wrap', R.viewMap);
      R.map = el('svg', { class: 'fv-map', role: 'img' }, R.wrap);
      R.viewSeq = h('div', 'fv-view fv-grid', '<div class="fv-scroll"></div>', R.stage);
      R.seq = el('svg', { class: 'fv-seq', role: 'img' }, $('.fv-scroll', R.viewSeq));
      R.viewSpec = h('div', 'fv-view',
        '<div class="fv-specwrap"><p class="fv-note">This is everything the agent wrote for this drawing: boxes on a grid, ' +
        'connections, flows and one sentence per step. The toolkit laid out, drew and animated the rest. Depth for the ' +
        'drawer lives in plain HTML sections beside it.</p><div class="fv-code"><button class="fv-btn" type="button">' +
        icon('copy') + 'copy</button><pre></pre></div></div>', R.stage);
      R.specPre = $('pre', R.viewSpec);
      $('.fv-btn', R.viewSpec).addEventListener('click', function (ev) {
        copyText(JSON.stringify(specSource(), null, 2), ev.currentTarget, 'Spec copied');
      });
      R.peek = h('div', 'fv-peek', null, R.stage); R.peek.hidden = true;
      R.key = h('div', 'fv-key', null, R.stage);
      R.key.hidden = true;
      R.rail = h('div', 'fv-rail', null, R.stage);
      R.play = h('button', 'fv-play', null, R.rail); R.play.type = 'button';
      R.dots = h('div', 'fv-dots', null, R.rail);
      R.cap = h('p', 'fv-cap', null, R.rail); R.cap.setAttribute('aria-live', 'polite');
      R.navs = h('div', 'fv-navs',
        '<button type="button" aria-label="Previous step">' + icon('left') + '</button>' +
        '<button type="button" aria-label="Next step">' + icon('right') + '</button>', R.rail);
      R.play.addEventListener('click', function () { play(); });
      $$('button', R.navs)[0].addEventListener('click', function () { stepBy(-1); });
      $$('button', R.navs)[1].addEventListener('click', function () { stepBy(1); });
      R.print = h('ol', 'fv-print');

      fig.appendChild(R.head); fig.appendChild(R.strip); fig.appendChild(R.stage); fig.appendChild(R.print);

      R.map.addEventListener('click', function () {
        if (DR && DR.owner === self) closeDrawer();
        else if (S.step >= 0 && !S.playing) rest();
      });
      fig.addEventListener('pointerenter', function () { active = self; });
      fig.addEventListener('focusin', function () { active = self; });
      /* on a report, leaving the drawing gives Space and the arrows back to the page */
      fig.addEventListener('pointerleave', function () {
        if (PAGE_KIND !== 'drawing' && active === self && !fig.contains(document.activeElement)) active = null;
      });
    }

    /* ── the map ─────────────────────────────────────────────────────────── */
    function renderMap() {
      var sp = S.spec, svg = R.map;
      svg.innerHTML = '';
      S.nodes = {}; S.edges = {}; S.nref = {}; S.eref = {}; S.lanes = [];
      (sp.nodes || []).forEach(function (n) { S.nodes[n.id] = n; });
      (sp.edges || []).forEach(function (e) { S.edges[e.id] = e; });
      var L = S.L = layout(sp);
      svg.setAttribute('viewBox', '0 0 ' + L.W + ' ' + L.H);
      svg.setAttribute('aria-label', (sp.title || sp.name || '') + '. ' + (sp.nodes || []).length + ' boxes; ' +
        (sp.flows || []).map(function (fl) { return fl.label; }).join(', ') + '.');
      svg.classList.remove('focus', 'stepping');
      S.layer = {
        zones: el('g', { class: 'zones' }, svg), edges: el('g', { class: 'edges' }, svg),
        nodes: el('g', { class: 'nodes' }, svg), badges: el('g', { class: 'badges' }, svg),
        marks: el('g', { class: 'marks' }, svg), fx: el('g', { class: 'fx' }, svg), seqfx: S.layer.seqfx
      };
      L.zones.forEach(drawZone);
      L.plans.forEach(drawEdge);
      (sp.nodes || []).forEach(function (n) { if (L.boxes[n.id]) drawNode(n, L.boxes[n.id]); });
    }
    function drawZone(zr) {
      var z = zr.z, r = zr.r;
      var g = el('g', { class: 'zone z-' + (z.tone || 'neutral') }, S.layer.zones);
      el('rect', { x: r.x, y: r.y, width: r.w, height: r.h, rx: 16 }, g);
      var tag = z.tag || 'tl', right = tag[1] === 'r', bottom = tag[0] === 'b';
      var t = el('text', { x: right ? r.x + r.w - 14 : r.x + 14, y: bottom ? r.y + r.h - 11 : r.y + 20,
        'text-anchor': right ? 'end' : 'start' }, g);
      t.textContent = z.label || '';
    }
    function head(pts, g) {
      var q = pts[pts.length - 1], p = pts[pts.length - 2];
      var dx = q.x - p.x, dy = q.y - p.y, L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L;
      var tx = q.x - ux * 1.5, ty = q.y - uy * 1.5, bx = tx - ux * 8.5, by = ty - uy * 8.5;
      el('path', { class: 'head', d: 'M' + f(tx) + ' ' + f(ty) + 'L' + f(bx - uy * 4.6) + ' ' + f(by + ux * 4.6) +
        'L' + f(bx + uy * 4.6) + ' ' + f(by - ux * 4.6) + 'Z' }, g);
    }
    function drawEdge(p) {
      var e = p.e, mode = e.mode === 'async' ? 'async' : 'sync';
      var set = el('g', { class: 'edgeset', 'data-edge': e.id }, S.layer.edges);
      p.lanes.forEach(function (ln) {
        var g = el('g', { class: 'edge m-' + mode, 'data-edge': e.id, 'data-dir': ln.dir }, set);
        var pts = trimEnd(ln.pts, 7);
        var path = el('path', { class: 'line', d: roundPath(pts, G.r) }, g);
        head(ln.pts, g);
        S.lanes.push({ edge: e, dir: ln.dir, g: g, path: path, pts: pts });
      });
      var hit = el('path', { class: 'hit', d: roundPath(p.pts, G.r) }, set);
      var cg = el('g', { class: 'chiplbl' }, set);
      S.eref[e.id] = { set: set, hit: hit, pts: p.pts, both: !!e.both,
        chip: { g: cg, rect: el('rect', { rx: 6, height: 18 }, cg), text: el('text', {}, cg) } };
      wireHover(hit, 'edge', e.id, set);
    }
    function zoomGlyph(cx, cy) {
      return 'M' + f(cx - 2.2) + ' ' + f(cy - 2.2) + 'h4.4v4.4M' + f(cx + 2.2) + ' ' + f(cy - 2.2) + 'l-4.6 4.6';
    }
    function fit(t, max) {
      var len = t.getComputedTextLength();
      if (!len || len <= max + 1) return;
      var fs = parseFloat(window.getComputedStyle(t).fontSize) || 13;
      t.style.fontSize = Math.max(9.5, fs * max / len * 0.97) + 'px';
      var s = t.textContent;
      while (s.length > 3 && t.getComputedTextLength() > max) { s = s.slice(0, -1); t.textContent = s + '…'; }
    }
    function drawNode(n, b) {
      var nr = resultOf(n);
      var g = el('g', {
        class: 'node k-' + (KIND[n.kind] ? n.kind : 'service') + (n.ghost ? ' ghost' : '') + (n.tech ? ' has-tech' : '') +
          (nr ? ' r-' + nr : ''),
        'data-node': n.id, tabindex: 0, role: 'button',
        'aria-label': (n.label || n.id) + (n.peek ? '. ' + n.peek : '')
      }, S.layer.nodes);
      el('rect', { class: 'shape', x: b.x, y: b.y, width: b.w, height: b.h, rx: 14 }, g);
      el('rect', { class: 'tile', x: b.x + 11, y: b.y + 11, width: 34, height: 34, rx: 10 }, g);
      el('use', { class: 'ico', href: '#i-' + (n.icon || 'service'), x: b.x + 18, y: b.y + 18, width: 20, height: 20 }, g);
      var lg = el('g', { class: 'lblg' }, g);
      var t = el('text', { class: 'lbl', x: b.x + 55, y: b.cy + 4.5 }, lg);
      t.textContent = n.label || n.id;
      fit(t, LABEL_ROOM);
      if (n.tech) {
        var tt = el('text', { class: 'tech', x: b.x + 55, y: b.cy + 14 }, g);
        tt.textContent = n.tech;
        fit(tt, b.w - 55 - 10);
      }
      if (n.segment && !n.ghost) {
        var sg = el('g', { class: 'seg', role: 'button', 'aria-label': 'Open the inside of ' + (n.label || n.id) }, g);
        el('circle', { cx: b.x + b.w - 3, cy: b.y + 3, r: 9.5 }, sg);
        el('path', { d: zoomGlyph(b.x + b.w - 3, b.y + 3) }, sg);
        var tl = el('title', {}, sg); tl.textContent = 'Open the inside of ' + (n.label || n.id);
        sg.addEventListener('click', function (ev) { ev.stopPropagation(); hoverOff(); openSegment(n.segment, n.id); });
      }
      if (nr) {
        var rb = el('g', { class: 'nres r-' + nr, transform: 'translate(' + f(b.x + 3) + ' ' + f(b.y + 3) + ')' }, g);
        resGlyph(rb, nr, 9.5);
        var rt = el('title', {}, rb); rt.textContent = RES[nr].word;
      }
      S.nref[n.id] = { g: g, b: b };
      wireHover(g, 'node', n.id, g);
    }
    /* ✓ ✕ ⚠ drawn, not typed, so they read the same in every font, theme and print */
    function resGlyph(g, r, rad) {
      if (r === 'error') {
        var k = rad / 9.5;
        el('path', { class: 'rbg', d: 'M0 ' + f(-9.8 * k) + 'L' + f(9.4 * k) + ' ' + f(7 * k) + 'H' + f(-9.4 * k) + 'Z' }, g);
        el('path', { class: 'rfg', d: 'M0 ' + f(-3.6 * k) + 'V' + f(1.6 * k) + 'M0 ' + f(4.4 * k) + 'v.1' }, g);
      } else {
        el('circle', { class: 'rbg', r: rad }, g);
        el('path', { class: 'rfg', d: r === 'pass'
          ? 'M' + f(-rad * 0.42) + ' 0.2l' + f(rad * 0.3) + ' ' + f(rad * 0.3) + 'l' + f(rad * 0.56) + ' ' + f(-rad * 0.6)
          : 'M' + f(-rad * 0.36) + ' ' + f(-rad * 0.36) + 'L' + f(rad * 0.36) + ' ' + f(rad * 0.36) + 'M' + f(rad * 0.36) + ' ' + f(-rad * 0.36) + 'L' + f(-rad * 0.36) + ' ' + f(rad * 0.36) }, g);
      }
      return g;
    }

    /* ── flows: which lanes a step walks, and which way ──────────────────── */
    function laneFor(a, b) {
      for (var i = 0; i < S.lanes.length; i++) {
        var L = S.lanes[i], e = L.edge;
        if (e.from === a && e.to === b && L.dir === 1) return { lane: L, back: false, edge: e };
        if (e.from === b && e.to === a) {
          if (e.both && L.dir === -1) return { lane: L, back: false, edge: e };
          if (!e.both && L.dir === 1) return { lane: L, back: true, edge: e };
        }
      }
      return { lane: null, back: false, edge: null };
    }
    function hops(st) {
      var out = [], path = st.path || [], res = resultOf(st), last = path.length - 2;
      for (var i = 0; i < path.length - 1; i++) {
        var hp = laneFor(path[i], path[i + 1]);
        hp.a = path[i]; hp.b = path[i + 1]; hp.i = i;
        hp.mode = (st.fail || res === 'fail') && i === last ? 'fail'
          : res === 'error' && i === 0 ? 'error'
          : hp.edge && hp.edge.mode === 'async' ? 'event'
          : hp.back ? 'response' : 'request';
        /* a failed step got as far as its last hop; a rejected one never left its first */
        hp.result = res === 'pass' ? 'pass' : res === 'fail' ? (i === last ? 'fail' : 'pass')
          : res === 'error' ? (i === 0 ? 'error' : null) : null;
        hp.walked = !(res === 'error' && i > 0);
        out.push(hp);
      }
      return out;
    }
    function applyFlow() {
      fig.style.setProperty('--flow', hasFlows() ? flowAccent(S.flow) : 'var(--dim)');
      R.map.classList.toggle('noflow', !hasFlows());
      S.lanes.forEach(function (L) { L.inFlow = L.fwd = L.back = false; L.res = resultOf(L.edge); });
      flow().steps.forEach(function (st) {
        hops(st).forEach(function (hp) {
          if (!hp.lane || !hp.walked) return;
          hp.lane.inFlow = true;
          if (hp.back) hp.lane.back = true; else hp.lane.fwd = true;
          hp.lane.res = stronger(hp.lane.res, hp.result);
        });
      });
      restLanes();
      renderBadges(); renderMarks(); renderDots(); caption(-1); renderSeq(); printSteps(); renderKey();
    }
    /* at rest a lane moves the way the flow mostly uses it; with no flows at all,
       every connection drifts in its own direction, in ink */
    function restLanes() {
      var none = !hasFlows();
      S.lanes.forEach(function (L) {
        L.g.classList.toggle('live', !!L.inFlow);
        L.g.classList.toggle('ink', none);
        L.g.classList.toggle('rev', !!(L.inFlow && !L.fwd && L.back));
        L.g.classList.remove('hot', 'failing', 'r-pass', 'r-fail', 'r-error');
        if (L.res) L.g.classList.add('r-' + L.res);
      });
    }
    /* the outcome is visible before anyone presses Walk through: a static ✕ where a
       call failed, a ⚠ where a command was rejected — for connections and steps alike */
    function markAt(pts, r) { return pointAt(pts, r === 'fail' ? 0.62 : 0.15); }
    function renderMarks() {
      var gm = S.layer.marks; gm.innerHTML = '';
      S.spec.edges.forEach(function (e) {
        var r = resultOf(e);
        if ((r !== 'fail' && r !== 'error') || !S.eref[e.id]) return;
        var pt = markAt(S.eref[e.id].pts, r);
        resGlyph(el('g', { class: 'rmark r-' + r, 'data-edge': e.id, transform: 'translate(' + f(pt.x) + ' ' + f(pt.y) + ')' }, gm), r, 8.5);
      });
      flow().steps.forEach(function (st, si) {
        var r = resultOf(st);
        if (r !== 'fail' && r !== 'error') return;
        var hs = hops(st), hp = r === 'fail' ? hs[hs.length - 1] : hs[0];
        if (!hp || !hp.lane) return;
        var pts = hp.back ? hp.lane.pts.slice().reverse() : hp.lane.pts, pt = markAt(pts, r);
        resGlyph(el('g', { class: 'rmark r-' + r, 'data-si': si, 'data-edge': hp.edge.id,
          transform: 'translate(' + f(pt.x) + ' ' + f(pt.y) + ')' }, gm), r, 8.5);
      });
    }
    function stopPoint(st, hp) {
      var pts = hp.back ? hp.lane.pts.slice().reverse() : hp.lane.pts;
      return markAt(pts, hp.mode === 'fail' ? 'fail' : 'error');
    }
    function renderKey() {
      var fl = hasFlows(), any = { pass: 0, fail: 0, error: 0 }, sp = S.spec;
      (sp.nodes || []).concat(sp.edges || []).forEach(function (x) { var r = resultOf(x); if (r) any[r] = 1; });
      (sp.flows || []).forEach(function (f0) { (f0.steps || []).forEach(function (st) { var r = resultOf(st); if (r) any[r] = 1; }); });
      var mv = fl ? 'live' : 'ink', rows = [
        '<svg viewBox="0 0 44 14"><g class="edge m-sync ' + mv + '"><path class="line" d="M2 7H42"/></g></svg><span>Synchronous call; the dashes travel with the request</span>',
        '<svg viewBox="0 0 44 14"><g class="edge m-async ' + mv + '"><path class="line" d="M2 7H42"/></g></svg><span>Asynchronous message; nobody waits on it</span>',
        '<svg viewBox="0 0 44 14"><g class="edge m-async ' + mv + '"><path class="line" d="M2 4H42"/><path class="line" d="M42 10H2"/></g></svg><span>Two lanes: traffic both ways</span>'];
      if (fl) rows.push(
        '<svg viewBox="0 0 44 14"><g class="edge m-sync"><path class="line" d="M2 7H42"/></g></svg><span>Exists, but not part of this flow</span>',
        '<svg viewBox="0 0 44 14"><g class="stepno"><circle cx="22" cy="7" r="7"/><text x="22" y="7">3</text></g></svg><span>Step number; press it to play that step</span>');
      if (any.pass) rows.push('<svg viewBox="0 0 44 14"><g class="edge m-sync r-pass ' + mv + '"><path class="line" d="M2 7H42"/></g></svg><span>Passed: verified by the run</span>');
      if (any.fail) rows.push('<svg viewBox="0 0 44 14"><g class="edge m-sync r-fail"><path class="line" d="M2 7H42"/></g><g class="rmark r-fail" transform="translate(27 7)"><circle class="rbg" r="6.5"/><path class="rfg" d="M-2.3 -2.3L2.3 2.3M2.3 -2.3L-2.3 2.3"/></g></svg><span>Failed here: the target said no</span>');
      if (any.error) rows.push('<svg viewBox="0 0 44 14"><g class="edge m-sync r-error"><path class="line" d="M2 7H42"/></g><g class="rmark r-error" transform="translate(9 7)"><path class="rbg" d="M0 -6.2L5.9 4.4H-5.9Z"/><path class="rfg" d="M0 -2.5V.8M0 2.6v.1"/></g></svg><span>Rejected: the command never ran</span>');
      rows.push('<svg viewBox="0 0 44 14"><g class="node k-service"><g class="seg"><circle cx="22" cy="7" r="6.5"/><path d="M19.8 4.8h4.4v4.4M24.2 4.8l-4.4 4.4"/></g></g></svg><span>Opens a segment: the inside of that box</span>');
      R.key.innerHTML = rows.join('');
    }
    function renderBadges() {
      var gb = S.layer.badges; gb.innerHTML = '';
      var perLane = [];
      flow().steps.forEach(function (st, si) {
        var hp = hops(st)[0];
        if (!hp || !hp.lane) return;
        var slot = perLane.filter(function (x) { return x.lane === hp.lane; })[0];
        if (!slot) perLane.push(slot = { lane: hp.lane, list: [] });
        slot.list.push({ st: st, si: si, back: hp.back, res: resultOf(st), single: hops(st).length === 1 });
      });
      perLane.forEach(function (slot) {
        var n = slot.list.length;
        slot.list.forEach(function (it, k) {
          /* one badge sits mid-lane (a response nearer its own start on a two-lane edge);
             several share the lane evenly, in step order, so none lands on another */
          var t = n === 1 ? (slot.lane.edge.both ? 0.3 : 0.5) : 0.3 + k * (0.4 / (n - 1));
          if (n === 1 && it.res === 'error') t = 0.62;                 // ⚠ sits at 15% of this lane
          else if (n === 1 && it.res === 'fail' && it.single) t = 0.3;  // ✕ sits at 62% of this lane
          if (it.back && n === 1) t = 1 - t;
          var pt = pointAt(slot.lane.pts, t);
          var g = el('g', { class: 'stepno' + (it.st.fail ? ' fail' : '') + (it.res ? ' r-' + it.res : ''), 'data-si': it.si,
            'data-edge': slot.lane.edge.id, tabindex: 0, role: 'button',
            'aria-label': 'Step ' + (it.si + 1) + (it.res ? ', ' + RES[it.res].step : '') + ': ' + (it.st.say || '') }, gb);
          el('circle', { cx: f(pt.x), cy: f(pt.y), r: 9.5 }, g);
          var tx = el('text', { x: f(pt.x), y: f(pt.y) + 0.5 }, g);
          tx.textContent = it.si + 1;
          g.addEventListener('click', function (ev) { ev.stopPropagation(); goStep(it.si); });
          g.addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); ev.stopPropagation(); goStep(it.si); }
          });
          g.addEventListener('pointerenter', function () { if (S.step < 0 && !S.playing) mark(it.si); });
          g.addEventListener('pointerleave', function () { if (S.step < 0 && !S.playing) clearStep(); });
        });
      });
    }
    /* the chip on a connection: its protocol, its timing, or both */
    function updateChips() {
      var u = ui();
      Object.keys(S.eref).forEach(function (id) {
        var e = S.edges[id], ref = S.eref[id], parts = [];
        if (u.labels || !u.times) parts.push(e.label);
        if (u.times && e.ms) parts.push(e.ms);
        var c = ref.chip, text = parts.filter(Boolean).join(' · ');
        c.text.textContent = text;
        if (!text) { c.g.setAttribute('visibility', 'hidden'); return; }
        c.g.removeAttribute('visibility');
        var w = (c.text.getComputedTextLength() || text.length * 6.3) + 14;
        var m = pointAt(ref.pts, 0.5), lift = ref.both ? G.lane + 13 : 14, cx, cy;
        if (m.horiz) { cx = m.x; cy = m.y - lift; } else { cx = m.x + (ref.both ? G.lane : 0) + 10 + w / 2; cy = m.y; }
        c.rect.setAttribute('x', f(cx - w / 2)); c.rect.setAttribute('y', f(cy - 9)); c.rect.setAttribute('width', f(w));
        c.text.setAttribute('x', f(cx)); c.text.setAttribute('y', f(cy + 0.5));
        c.text.setAttribute('text-anchor', 'middle'); c.text.setAttribute('dominant-baseline', 'central');
      });
    }

    /* ── the sequence: the same flow, laid out in time ───────────────────── */
    function renderSeq() {
      var svg = R.seq; svg.innerHTML = '';
      S.seqRows = [];
      var fl = flow(), parts = [], rows = [];
      fl.steps.forEach(function (st, si) {
        hops(st).forEach(function (hp) {
          if (!hp.walked) return;
          [hp.a, hp.b].forEach(function (id) { if (parts.indexOf(id) < 0) parts.push(id); });
          rows.push({ st: st, si: si, h: hp });
        });
      });
      var left = 24, top = 50, headH = 46, rowH = 44;   // top clears the layers pill
      var W = Math.max(1000, left * 2 + parts.length * 158), cw = (W - left * 2) / Math.max(1, parts.length);
      var H = top + headH + 26 + rows.length * rowH + 18;
      function X(id) { return left + cw * parts.indexOf(id) + cw / 2; }
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      svg.setAttribute('aria-label', (fl.label || '') + ' as a sequence: ' + fl.steps.map(function (st, i) {
        return (i + 1) + '. ' + (st.say || ''); }).join(' '));
      var gRows = el('g', {}, svg), gLife = el('g', {}, svg), gMsg = el('g', {}, svg);
      S.layer.seqfx = el('g', { class: 'fx' }, svg);
      var visible = !R.viewSeq.hidden;
      parts.forEach(function (id) {
        var n = S.nodes[id] || { id: id, label: id, kind: 'service', icon: 'service' }, x = X(id), w = Math.min(cw - 18, 156);
        el('line', { class: 'life', x1: x, y1: top + headH, x2: x, y2: H - 8 }, gLife);
        var g = el('g', { class: 'node k-' + (KIND[n.kind] ? n.kind : 'service') + (n.ghost ? ' ghost' : ''), 'data-node': id,
          tabindex: 0, role: 'button', 'aria-label': n.label || id }, gLife);
        el('rect', { class: 'shape', x: x - w / 2, y: top, width: w, height: headH - 6, rx: 11 }, g);
        el('rect', { class: 'tile', x: x - w / 2 + 7, y: top + 7, width: 26, height: 26, rx: 8 }, g);
        el('use', { class: 'ico', href: '#i-' + (n.icon || 'service'), x: x - w / 2 + 12, y: top + 12, width: 16, height: 16 }, g);
        var t = el('text', { class: 'lbl', x: x - w / 2 + 41, y: top + 24.5 }, g);
        t.textContent = n.label || id;
        if (visible) fit(t, w - 50);
        wireHover(g, 'node', id, g);
      });
      rows.forEach(function (r, k) {
        var y = top + headH + 34 + k * rowH, x1 = X(r.h.a), x2 = X(r.h.b), dir = x2 > x1 ? 1 : -1;
        var band = el('rect', { class: 'band', x: 6, y: f(y - rowH / 2 + 3), width: W - 12, height: rowH - 6, rx: 9 }, gRows);
        var g = el('g', { class: 'msg ' + r.h.mode + (r.h.result ? ' r-' + r.h.result : '') }, gMsg);
        var xs = x1 + dir * 12;
        var xe = r.h.mode === 'fail' ? x1 + (x2 - x1) * 0.62 : r.h.mode === 'error' ? x1 + dir * 46 : x2 - dir * 9;
        var p = el('path', { class: 'line', d: 'M' + f(xs) + ' ' + y + 'H' + f(xe) }, g);
        if (r.h.mode === 'fail') {
          var xg = el('g', { transform: 'translate(' + f(xe) + ' ' + y + ')' }, g), xm = el('g', { class: 'xmark' }, xg);
          el('circle', { r: 8 }, xm); el('path', { d: 'M-3.2 -3.2L3.2 3.2M3.2 -3.2L-3.2 3.2' }, xm);
        } else if (r.h.mode === 'error') {
          resGlyph(el('g', { class: 'rmark r-error', transform: 'translate(' + f(xe) + ' ' + y + ')' }, g), 'error', 8.5);
        } else el('path', { class: 'head', d: 'M' + f(x2 - dir * 1.5) + ' ' + y + 'l' + (-dir * 9) + ' -4.8v9.6z' }, g);
        var tx = el('text', { x: f(r.h.mode === 'error' ? (xs + xe) / 2 : (x1 + x2) / 2), y: y - 8 }, g);
        tx.textContent = r.st.msg || '';
        if (r.h.i === 0) {
          var rr = resultOf(r.st);
          var bg = el('g', { class: 'stepno' + (r.st.fail ? ' fail' : '') + (rr ? ' r-' + rr : ''), 'data-si': r.si }, gMsg);
          el('circle', { cx: x1, cy: y, r: 9.5 }, bg);
          var bt = el('text', { x: x1, y: y + 0.5 }, bg); bt.textContent = r.si + 1;
          bg.addEventListener('click', function () { goStep(r.si); });
        }
        S.seqRows.push({ si: r.si, band: band, g: g, path: p, mode: r.h.mode });
      });
    }

    /* ── chrome: header, flows, views, layers, spec ──────────────────────── */
    function renderHeader() {
      var sp = S.spec, isSeg = !!S.seg || ROOT.kind === 'segment';
      R.crumbs.innerHTML = '<span class="fv-chip' + (isSeg ? ' seg' : '') + '">' + (isSeg ? 'Segment' : 'System') + '</span>';
      if (S.seg) {
        var b = h('button', null, icon('back') + ' ' + esc(ROOT.name || ROOT.title || 'Back'), R.crumbs);
        b.type = 'button'; b.title = 'Back to the whole system (Esc)';
        b.addEventListener('click', function () { leaveSegment(); });
        R.crumbs.insertAdjacentHTML('beforeend', '<span class="sep">›</span><span>' + esc(sp.name || '') + '</span>');
      } else if (sp.name) R.crumbs.insertAdjacentHTML('beforeend', '<span>' + esc(sp.name) + '</span>');
      R.title.textContent = sp.title || '';
      R.lede.textContent = sp.lede || '';
      R.lede.hidden = !sp.lede;
    }
    function renderFlows() {
      R.flows.innerHTML = '';
      S.spec.flows.forEach(function (fl, i) {
        var b = h('button', 'fv-flow', '<span class="fd"></span>' + esc(fl.label || 'Flow ' + (i + 1)) +
          '<span class="n">' + (fl.steps || []).length + '</span>', R.flows);
        b.type = 'button';
        b.setAttribute('role', 'radio');
        b.setAttribute('aria-checked', String(i === S.flow));
        b.style.setProperty('--fc', chipColor(i));
        var o = flowOutcome(fl);
        if (o) b.title = o === 'pass' ? 'Every step passed' : o === 'fail' ? 'A step failed' : 'A command was rejected';
        b.addEventListener('click', function () { setFlow(i); });
      });
      R.flows.hidden = S.spec.flows.length < 2;
    }
    function setFlow(i) {
      if (i === S.flow) return;
      rest(); hoverOff();
      S.flow = i;
      persistUi({ flow: i });
      renderFlows(); applyFlow();
      if (DR && DR.owner === self && DR.what) {
        if (DR.what.type === 'step') closeDrawer(); else openDrawer(DR.what.type, DR.what.id);
      }
    }
    function setView(v, init) {
      if (v === 'seq' && !hasFlows()) v = 'map';
      if (S.view !== v) { pause(); cancelRun(); }
      S.view = v;
      if (!init) persistUi({ view: v });
      R.tabs.seq.hidden = !hasFlows();
      R.viewMap.hidden = v !== 'map'; R.viewSeq.hidden = v !== 'seq'; R.viewSpec.hidden = v !== 'spec';
      Object.keys(R.tabs).forEach(function (k) { R.tabs[k].setAttribute('aria-selected', String(k === v)); });
      R.layers.hidden = v === 'spec';
      R.tg.labels.hidden = R.tg.times.hidden = v !== 'map';
      R.rail.hidden = v === 'spec' || !hasFlows();
      R.key.hidden = !ui().key || v === 'spec';
      hoverOff();
      if (v === 'seq') renderSeq();
      if (v === 'map') updateChips();
      if (v !== 'spec' && S.step >= 0) mark(S.step);
      setPlay();
    }
    function applyLayers() {
      var u = ui();
      R.map.classList.toggle('show-labels', !!u.labels);
      R.map.classList.toggle('show-times', !!u.times);
      ['labels', 'times', 'key'].forEach(function (k) { R.tg[k].setAttribute('aria-pressed', String(!!u[k])); });
      R.key.hidden = !u.key || S.view === 'spec';
      updateChips();
    }
    function specSource() { return S.seg ? ROOT.segments[S.seg] : ROOT; }
    function hl(json) {
      return esc(json).replace(/(&quot;(?:[^&]|&(?!quot;))*?&quot;)(\s*:)?|(-?\b\d+(?:\.\d+)?\b)|([{}\[\],])/g,
        function (m, s, colon, num, p) {
          if (s) return '<span class="' + (colon ? 'j-k' : 'j-s') + '">' + s + '</span>' + (colon || '');
          if (num) return '<span class="j-n">' + num + '</span>';
          return '<span class="j-p">' + p + '</span>';
        });
    }
    function renderSpec() { R.specPre.innerHTML = hl(JSON.stringify(specSource(), null, 2)); }
    function printSteps() {
      R.print.innerHTML = flow().steps.map(function (st) {
        var rr = resultOf(st);
        return '<li>' + (rr ? '<b class="fv-res r-' + rr + '">' + RES[rr].glyph + ' ' + esc(RES[rr].step) + '</b> — ' : '') + esc(st.say || '') + '</li>';
      }).join('');
      R.print.hidden = !hasFlows();
    }
    function renderAll() {
      /* the first paint is the resting state itself, never a transition into it —
         a screenshot, a print or an audit taken at once sees the real outcome */
      R.map.classList.add('fv-instant');
      renderHeader(); renderMap(); renderFlows(); applyFlow(); applyLayers(); renderSpec();
      requestAnimationFrame(function () { requestAnimationFrame(function () { R.map.classList.remove('fv-instant'); }); });
    }

    /* ── walking a flow: highlight, then send a packet down each hop ─────── */
    function cancelRun() {
      S.run++;
      if (S.raf) cancelAnimationFrame(S.raf);
      clearTimeout(S.timer);
      [S.layer.fx, S.layer.seqfx].forEach(function (g) { if (g) g.innerHTML = ''; });
    }
    function clearStep() {
      R.map.classList.remove('stepping');
      restLanes();
      $$('.hot, .now', R.map).forEach(function (x) { x.classList.remove('hot', 'now'); });
      S.seqRows.forEach(function (r) { r.band.classList.remove('now'); r.g.classList.remove('now'); });
      paintDots(-1);
      caption(-1);
    }
    function mark(si) {
      var st = flow().steps[si];
      if (!st) return;
      R.map.classList.remove('focus');
      restLanes();
      $$('.hot, .now', R.map).forEach(function (x) { x.classList.remove('hot', 'now'); });
      R.map.classList.add('stepping');
      hops(st).forEach(function (hp) {
        if (!hp.lane || !hp.walked) return;
        hp.lane.g.classList.add('hot');
        hp.lane.g.classList.toggle('rev', hp.back);
        if (hp.result || resultOf(st)) {
          hp.lane.g.classList.remove('r-pass', 'r-fail', 'r-error');
          if (hp.result) hp.lane.g.classList.add('r-' + hp.result);
        }
        if (hp.mode === 'fail') hp.lane.g.classList.add('failing');
        S.eref[hp.edge.id].set.classList.add('hot');
        [hp.a, hp.b].forEach(function (id) { if (S.nref[id]) S.nref[id].g.classList.add('hot'); });
      });
      $$('.stepno', R.map).forEach(function (b) {
        var on = +b.getAttribute('data-si') === si;
        b.classList.toggle('hot', on); b.classList.toggle('now', on);
      });
      $$('.rmark[data-si]', R.map).forEach(function (m) { m.classList.toggle('hot', +m.getAttribute('data-si') === si); });
      S.seqRows.forEach(function (r) {
        var on = r.si === si; r.band.classList.toggle('now', on); r.g.classList.toggle('now', on);
      });
      paintDots(si);
      caption(si);
    }
    function land(id) {
      if (!id || !S.nref[id]) return;
      var g = S.nref[id].g;
      g.classList.add('land');
      setTimeout(function () { g.classList.remove('land'); }, 380);
    }
    function fly(path, back, mode, msg, layer, cb, token, landId, stop, res, endAt) {
      var len = path.getTotalLength();
      var pk = el('g', { class: 'pkt' + (mode === 'fail' ? ' fail' : mode === 'error' ? ' error' : res === 'pass' ? ' pass' : '') }, layer);
      el('circle', { class: 'halo', r: 10 }, pk);
      el('circle', { class: 'core', r: 5 }, pk);
      var tag = null;
      if (msg) {
        tag = el('g', { class: 'ptag' }, layer);
        var r = el('rect', { rx: 9, height: 18, y: -9 }, tag), t = el('text', {}, tag);
        t.textContent = msg;
        var w = (t.getComputedTextLength() || msg.length * 6.4) + 16;
        r.setAttribute('x', f(-w / 2)); r.setAttribute('width', f(w));
      }
      var speed = mode === 'event' ? 150 : 240;
      var dur = still() ? 0 : Math.max(450, len * stop / speed * 1000), t0 = performance.now();
      function place(k) {
        var e = ease(k) * stop, p = path.getPointAtLength(len * (back ? 1 - e : e));
        pk.setAttribute('transform', 'translate(' + f(p.x) + ' ' + f(p.y) + ')');
        if (tag) tag.setAttribute('transform', 'translate(' + f(p.x) + ' ' + f(p.y - 21) + ')');
        return p;
      }
      function frame(now) {
        if (token !== S.run) return;
        var k = dur ? Math.min(1, (now - t0) / dur) : 1, p = place(k);
        if (k < 1) { S.raf = requestAnimationFrame(frame); return; }
        if (mode === 'fail' || mode === 'error') {
          var q = endAt || p;                              // land exactly on the resting ✕ or ⚠
          var at = el('g', { transform: 'translate(' + f(q.x) + ' ' + f(q.y) + ')' }, layer);
          el('circle', { class: 'burst' + (mode === 'error' ? ' warn' : ''), r: 7 }, at);
          if (mode === 'fail') {
            var xm = el('g', { class: 'xmark' }, at);
            el('circle', { r: 8.5 }, xm);
            el('path', { d: 'M-3.4 -3.4L3.4 3.4M3.4 -3.4L-3.4 3.4' }, xm);
          } else resGlyph(el('g', { class: 'rmark r-error pop' }, at), 'error', 8.5);
          pk.remove();
        } else {
          land(landId);
          setTimeout(function () { if (pk.parentNode) pk.remove(); }, 160);
        }
        if (tag) setTimeout(function () { if (tag.parentNode) tag.remove(); }, mode === 'fail' || mode === 'error' ? 1200 : 160);
        cb();
      }
      place(0);
      S.raf = requestAnimationFrame(frame);
    }
    function playStep(si, done) {
      cancelRun();
      var token = S.run, st = flow().steps[si];
      if (!st) return;
      var hs = hops(st), i = 0;
      S.step = si;
      mark(si);
      var rows = S.seqRows.filter(function (r) { return r.si === si; });
      hs = hs.filter(function (hp) { return hp.walked; });
      (function next() {
        if (token !== S.run) return;
        if (i >= hs.length) { if (done) done(token); return; }
        var hp = hs[i], row = rows[i];
        i++;
        var stop = hp.mode === 'fail' ? 0.62 : hp.mode === 'error' ? 0.15 : 1;
        if (S.view === 'seq' && row) fly(row.path, false, hp.mode, st.msg, S.layer.seqfx, next, token, null, 1, hp.result);
        else if (S.view === 'map' && hp.lane) {
          fly(hp.lane.path, hp.back, hp.mode, st.msg, S.layer.fx, next, token, hp.b, stop, hp.result,
            stop < 1 && resultOf(st) ? stopPoint(st, hp) : null);
        } else next();
      })();
    }
    function setPlay(ended) {
      var ic = S.playing ? 'pause' : ended ? 'replay' : 'play';
      var label = S.playing ? 'Pause' : ended ? 'Replay' : S.step >= 0 ? 'Continue' : 'Walk through';
      R.play.innerHTML = icon(ic) + '<span>' + label + '</span>';
    }
    function play() {
      if (S.playing) { pause(); return; }
      var n = flow().steps.length;
      if (!n) return;
      S.playing = true; setPlay();
      (function go(si) {
        if (!S.playing) return;
        playStep(si, function (token) {
          if (!S.playing || token !== S.run) return;
          var dwell = Math.max(1100, words(flow().steps[si].say) * 150);
          if (si + 1 < n) S.timer = setTimeout(function () { if (S.playing && token === S.run) go(si + 1); }, dwell);
          else { S.playing = false; setPlay(true); }
        });
      })(S.step < 0 || S.step >= n - 1 ? 0 : S.step + 1);
    }
    function pause() { S.playing = false; clearTimeout(S.timer); setPlay(); }
    function goStep(si) { active = self; pause(); playStep(si); setPlay(); }
    function stepBy(d) {
      var n = flow().steps.length;
      if (!n) return;
      goStep(S.step < 0 ? (d > 0 ? 0 : n - 1) : Math.min(n - 1, Math.max(0, S.step + d)));
    }
    function rest() { pause(); cancelRun(); S.step = -1; clearStep(); setPlay(); }

    function renderDots() {
      R.dots.innerHTML = '';
      flow().steps.forEach(function (st, si) {
        var rr = resultOf(st);
        var b = h('button', 'fv-dot' + (st.fail ? ' fail' : '') + (rr ? ' r-' + rr : ''), String(si + 1), R.dots);
        b.type = 'button';
        b.setAttribute('aria-label', 'Step ' + (si + 1) + (rr ? ', ' + RES[rr].step : '') + ': ' + (st.say || ''));
        b.addEventListener('click', function () { goStep(si); });
        b.addEventListener('mouseenter', function () { if (S.step < 0 && !S.playing) mark(si); });
        b.addEventListener('mouseleave', function () { if (S.step < 0 && !S.playing) clearStep(); });
      });
      setPlay();
    }
    function paintDots(si) {
      $$('.fv-dot', R.dots).forEach(function (b, i) {
        b.classList.toggle('now', i === si);
        b.classList.toggle('seen', si >= 0 && i < si);
      });
    }
    function caption(si) {
      var fl = flow();
      if (si < 0) { R.cap.textContent = fl.summary || ''; return; }
      var st = fl.steps[si], rr = resultOf(st);
      R.cap.innerHTML = '<b>' + (si + 1) + '.</b> ' +
        (rr ? '<span class="fv-res r-' + rr + '">' + RES[rr].glyph + ' ' + esc(RES[rr].step) + '</span> — ' : '') +
        esc(st.say || '') + ' <button class="fv-more" type="button">Details</button>';
      $('.fv-more', R.cap).addEventListener('click', function () { openDrawer('step', si); });
    }

    /* ── hover: dim what a box does not touch, and peek ──────────────────── */
    var hovT, peekT, warmT, warm = false;
    function wireHover(target, type, id, g) {
      target.addEventListener('pointerenter', function (ev) { if (ev.pointerType !== 'touch') hoverOn(type, id, g); });
      target.addEventListener('pointerleave', hoverOff);
      target.addEventListener('click', function (ev) { ev.stopPropagation(); hoverOff(); activate(type, id); });
      if (type === 'node') {
        g.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); ev.stopPropagation(); activate(type, id); }
        });
        g.addEventListener('focus', function () { if (g.matches(':focus-visible')) hoverOn(type, id, g); });
        g.addEventListener('blur', hoverOff);
      }
    }
    function activate(type, id) {
      active = self;
      var n = type === 'node' && S.nodes[id];
      if (n && n.ghost && S.seg) { leaveSegment(n.ghost); return; }
      openDrawer(type, id);
    }
    function hoverOn(type, id, g) {
      clearTimeout(hovT);
      var svg = g.ownerSVGElement;
      hovT = setTimeout(function () {
        if (svg !== R.map || svg.classList.contains('stepping')) return;
        $$('.near, .hov', svg).forEach(function (x) { x.classList.remove('near', 'hov'); });
        svg.classList.add('focus');
        var near = {}, ids = [];
        if (type === 'node') {
          near[id] = 1;
          S.spec.edges.forEach(function (e) {
            if ((e.from === id || e.to === id) && S.eref[e.id]) { ids.push(e.id); near[e.from] = near[e.to] = 1; }
          });
        } else {
          var e = S.edges[id];
          ids.push(id); near[e.from] = near[e.to] = 1;
          S.eref[id].set.classList.add('hov');
        }
        Object.keys(near).forEach(function (n) { if (S.nref[n]) S.nref[n].g.classList.add('near'); });
        ids.forEach(function (eid) {
          S.eref[eid].set.classList.add('near');
          $$('.edge[data-edge="' + eid + '"], .stepno[data-edge="' + eid + '"], .rmark[data-edge="' + eid + '"]', svg)
            .forEach(function (x) { x.classList.add('near'); });
        });
      }, 60);
      showPeek(type, id, g);
    }
    function hoverOff() {
      clearTimeout(hovT);
      R.map.classList.remove('focus');
      $$('.near, .hov', R.map).forEach(function (x) { x.classList.remove('near', 'hov'); });
      hidePeek();
    }
    function factsHtml(list) {
      return list && list.length ? '<div class="facts">' + list.slice(0, 3).map(function (x) {
        return '<span>' + esc(x) + '</span>'; }).join('') + '</div>' : '';
    }
    function svgToScreen(svg, x, y) {
      var m = svg.getScreenCTM();
      return { x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f };
    }
    function showPeek(type, id, anchor) {
      clearTimeout(peekT); clearTimeout(warmT);
      peekT = setTimeout(function () {
        var pk = R.peek, html, k, r;
        if (type === 'node') {
          var n = S.nodes[id]; if (!n) return;
          k = n.ghost ? 'var(--dim2)' : kindVar(n.kind);
          html = '<div class="pk">' + esc(n.ghost ? 'In the whole system' : (KIND_NAME[n.kind] || 'Box')) +
            (n.tech ? ' · ' + esc(n.tech) : '') + '</div><h4>' + esc(n.label || id) + '</h4>' +
            (resultOf(n) ? '<div class="res r-' + resultOf(n) + '">' + RES[resultOf(n)].glyph + ' ' + esc(RES[resultOf(n)].word) + '</div>' : '') +
            '<p>' + esc(n.peek || '') + '</p>' +
            factsHtml(n.facts) + '<div class="hint">' + (n.ghost && S.seg ? '<span>Click to go back to it</span>'
              : '<span>Click for everything</span>' + (n.segment && !n.ghost ? '<span>⤢ opens its inside</span>' : '')) + '</div>';
          r = anchor.getBoundingClientRect();
        } else {
          var e = S.edges[id]; if (!e) return;
          k = e.mode === 'async' ? 'var(--stream)' : 'var(--f1)';
          html = '<div class="pk">' + (e.mode === 'async' ? 'Message' : 'Call') + (e.both ? ' · both ways' : '') +
            (e.label ? ' · ' + esc(e.label) : '') + '</div><h4>' + esc((S.nodes[e.from] || {}).label || e.from) +
            (e.both ? ' ⇄ ' : ' → ') + esc((S.nodes[e.to] || {}).label || e.to) + '</h4>' +
            (resultOf(e) ? '<div class="res r-' + resultOf(e) + '">' + RES[resultOf(e)].glyph + ' ' + esc(RES[resultOf(e)].word) + '</div>' : '') +
            '<p>' + esc(e.peek || '') + '</p>' +
            factsHtml(e.ms ? [e.ms] : []) + '<div class="hint"><span>Click for everything</span></div>';
          var m = pointAt(S.eref[id].pts, 0.5), s = svgToScreen(R.map, m.x, m.y);
          r = { left: s.x, top: s.y, bottom: s.y, width: 0, height: 0 };
        }
        pk.innerHTML = html;
        pk.style.setProperty('--k', k);
        pk.hidden = false;
        pk.classList.remove('on', 'below');
        var stage = R.stage.getBoundingClientRect(), w = pk.offsetWidth, hh = pk.offsetHeight;
        var left = Math.min(Math.max(8, r.left + r.width / 2 - stage.left - w / 2), stage.width - w - 8);
        var top = r.top - stage.top - hh - 12;
        if (top < 8) { top = r.bottom - stage.top + 12; pk.classList.add('below'); }
        pk.style.left = left + 'px'; pk.style.top = top + 'px';
        requestAnimationFrame(function () { pk.classList.add('on'); });
        warm = true;
      }, warm ? 0 : 150);
    }
    function hidePeek() {
      clearTimeout(peekT);
      var pk = R.peek;
      pk.classList.remove('on');
      clearTimeout(warmT);
      warmT = setTimeout(function () { warm = false; if (!pk.classList.contains('on')) pk.hidden = true; }, 380);
    }

    /* ── the drawer: layer 3 ─────────────────────────────────────────────── */
    function add(parent, html) { return h('div', null, html, parent); }
    function depth(key) {
      if (!DEPTH) return null;
      var s = null;
      $$('section[data-for]', DEPTH).some(function (x) { if (x.getAttribute('data-for') === key) { s = x; return true; } return false; });
      if (!s) return null;
      var c = s.cloneNode(true);
      c.removeAttribute('data-for');
      return c;
    }
    function openDrawer(type, id) {
      var D = drawer();
      if (DR.owner && DR.owner !== self) DR.owner.select(null);
      D.body.innerHTML = ''; D.ico.innerHTML = ''; D.ico.style.removeProperty('--k'); D.kind.style.removeProperty('--k');
      D.el.style.setProperty('--flow', 'var(--' + tone(S.flow) + ')');
      select(type, id);
      if (type === 'node') nodeDrawer(S.nodes[id], D);
      else if (type === 'edge') edgeDrawer(S.edges[id], D);
      else stepDrawer(id, D);
      D.el.classList.add('on'); D.el.setAttribute('aria-hidden', 'false');
      D.scrim.classList.add('on');
      D.body.scrollTop = 0;
      D.owner = self; D.what = { type: type, id: id };
    }
    function select(type, id) {
      $$('.sel', R.map).forEach(function (x) { x.classList.remove('sel'); });
      if (type === 'node' && S.nref[id]) S.nref[id].g.classList.add('sel');
      if (type === 'edge' && S.eref[id]) S.eref[id].set.classList.add('sel');
    }
    function stepsTouching(pred, body) {
      var fl = flow(), items = [];
      fl.steps.forEach(function (st, si) { if (pred(st)) items.push({ st: st, si: si }); });
      if (items.length) {
        var wrap = add(body, '<h3>In “' + esc(fl.label || 'this flow') + '”</h3><ol class="steplist"></ol>');
        wrap.style.setProperty('--fc', 'var(--' + tone(S.flow) + ')');
        items.forEach(function (it) {
          var li = h('li', null, '<button type="button"><span class="num' + (it.st.fail ? ' fail' : '') +
            (resultOf(it.st) ? ' r-' + resultOf(it.st) : '') + '">' + (it.si + 1) +
            '</span><span>' + esc(it.st.say || '') + '</span></button>', $('ol', wrap));
          $('button', li).addEventListener('click', function () {
            if (window.innerWidth < 760) closeDrawer();
            goStep(it.si);
          });
        });
      }
      var others = [];
      S.spec.flows.forEach(function (o, i) { if (i !== S.flow && (o.steps || []).some(pred)) others.push(i); });
      if (others.length) {
        var p = add(body, '<p class="alsoin">' + (items.length ? 'Also in' : 'Not in this flow. It appears in') + ' ' +
          others.map(function (i) { return '<button type="button" data-flow="' + i + '">' + esc(S.spec.flows[i].label) + '</button>'; }).join(' · ') + '</p>');
        $$('[data-flow]', p).forEach(function (b) {
          b.addEventListener('click', function () { setFlow(+b.getAttribute('data-flow')); });
        });
      }
    }
    function nodeDrawer(n, D) {
      var kv = n.ghost ? 'var(--dim2)' : kindVar(n.kind);
      D.ico.style.setProperty('--k', kv); D.kind.style.setProperty('--k', kv);
      D.ico.innerHTML = icon(n.icon || 'service');
      D.kind.textContent = (n.ghost ? 'In the whole system' : (KIND_NAME[n.kind] || 'Box')) + (n.tech ? ' · ' + n.tech : '');
      D.title.textContent = n.label || n.id;
      add(D.body, '<p class="lead">' + esc(n.peek || '') + '</p>');
      if (resultOf(n)) add(D.body, resBox(resultOf(n)));
      if (n.facts && n.facts.length) add(D.body, '<div class="facts-grid">' + n.facts.map(function (x) {
        return '<div>' + esc(x) + '</div>'; }).join('') + '</div>');
      stepsTouching(function (st) { return (st.path || []).indexOf(n.id) >= 0; }, D.body);
      var dp = depth(scope(n.id)); if (dp) D.body.appendChild(dp);
      if (n.segment && !n.ghost && ROOT.segments && ROOT.segments[n.segment]) {
        var b = add(D.body, '<button class="segbtn" type="button">' + icon('zoom') + '<span>Open the inside of ' + esc(n.label || n.id) +
          '<small>' + esc(ROOT.segments[n.segment].title || '') + '</small></span></button>');
        $('button', b).addEventListener('click', function () { openSegment(n.segment, n.id); });
      }
      D.body.appendChild(noteBox('node:' + n.id));
    }
    function edgeDrawer(e, D) {
      var kv = e.mode === 'async' ? 'var(--stream)' : 'var(--f1)';
      D.ico.style.setProperty('--k', kv); D.kind.style.setProperty('--k', kv);
      D.ico.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="' +
        (e.mode === 'async' ? '.1 4.2' : '4 3') + '"/><path d="M15 7l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      D.kind.textContent = (e.mode === 'async' ? 'Asynchronous message' : 'Synchronous call') + (e.both ? ' · both ways' : '');
      D.title.textContent = ((S.nodes[e.from] || {}).label || e.from) + (e.both ? ' ⇄ ' : ' → ') + ((S.nodes[e.to] || {}).label || e.to);
      add(D.body, '<p class="lead">' + esc(e.peek || '') + '</p>');
      if (resultOf(e)) add(D.body, resBox(resultOf(e)));
      var facts = [e.label, e.ms].filter(Boolean);
      if (facts.length) add(D.body, '<div class="facts-grid">' + facts.map(function (x) { return '<div>' + esc(x) + '</div>'; }).join('') + '</div>');
      stepsTouching(function (st) { return hops(st).some(function (hp) { return hp.edge === e && hp.walked; }); }, D.body);
      var dp = depth(scope('edge:' + e.id)); if (dp) D.body.appendChild(dp);
      D.body.appendChild(noteBox('edge:' + e.id));
    }
    function stepDrawer(si, D) {
      var fl = flow(), st = fl.steps[si];
      if (!st) return;
      var rr = resultOf(st);
      var kv = rr ? 'var(--' + RES[rr].tone + ')' : st.fail ? 'var(--bad)' : 'var(--' + tone(S.flow) + ')';
      D.ico.style.setProperty('--k', kv); D.kind.style.setProperty('--k', kv);
      D.ico.innerHTML = '<b>' + (si + 1) + '</b>';
      D.kind.textContent = 'Step ' + (si + 1) + ' of ' + fl.steps.length + ' · ' + (rr ? RES[rr].step.split(':')[0] : (fl.label || ''));
      D.title.textContent = st.msg || 'Step ' + (si + 1);
      add(D.body, '<p class="lead">' + esc(st.say || '') + '</p>');
      if (rr) add(D.body, resBox(rr));
      add(D.body, '<h3>Route</h3><p class="route">' + (st.path || []).map(function (id) {
        return esc(S.nodes[id] ? S.nodes[id].label : id); }).join(' <span class="arr">→</span> ') + '</p>');
      var dp = depth(scope('step:' + st.id)); if (dp) D.body.appendChild(dp);
      var nav = add(D.body, '<div class="stepnav"><button class="fv-btn" type="button" data-go="-1"' + (si ? '' : ' disabled') +
        '>‹ Previous step</button><button class="fv-btn" type="button" data-go="1"' + (si < fl.steps.length - 1 ? '' : ' disabled') +
        '>Next step ›</button></div>');
      $$('[data-go]', nav).forEach(function (b) {
        b.addEventListener('click', function () {
          var to = si + (+b.getAttribute('data-go'));
          if (to >= 0 && to < fl.steps.length) { goStep(to); openDrawer('step', to); }
        });
      });
      D.body.appendChild(noteBox('step:' + st.id));
    }
    /* the drawing is an input device too: a note per element, keyed by its id */
    function noteBox(key) {
      var full = noteKey(key), wrap = h('div', 'notebox');
      wrap.innerHTML = '<h3>Note for the agent</h3><textarea id="fvnote-' + full.replace(/[^\w-]/g, '_') +
        '" placeholder="Wrong, missing or unclear? Say so here."></textarea><div class="row"><span>' + esc(full) +
        '</span><button class="fv-btn" type="button">copy all notes</button></div>';
      var ta = $('textarea', wrap);
      ta.value = noteText(notes()[full]);
      ta.addEventListener('input', function () {
        if (ta.value.trim()) notes()[full] = { text: ta.value, at: new Date().toISOString() };
        else delete notes()[full];
        save();
      });
      $('.fv-btn', wrap).addEventListener('click', function (ev) {
        var all = {}, ns = notes();
        Object.keys(ns).forEach(function (k) { var t = noteText(ns[k]); if (t.trim()) all[k] = { text: t, at: ns[k].at || null }; });
        var n = Object.keys(all).length;
        copyText('```json\n' + JSON.stringify({ doc: (window.FLOW && window.FLOW.doc) || ID,
          flowviz: (window.FLOW && window.FLOW.version) || '', at: new Date().toISOString(), notes: all }, null, 2) + '\n```',
          ev.currentTarget, n + ' note' + (n === 1 ? '' : 's') + ' copied for the agent');
      });
      return wrap;
    }

    /* ── segments: a box opens into its own drawing ──────────────────────── */
    function zoom(nodeId, dir, swap) {
      var wrap = R.wrap;
      if (still() || S.view !== 'map') { swap(); return; }
      var wr = wrap.getBoundingClientRect();
      if (nodeId && S.nref[nodeId]) {
        var r = S.nref[nodeId].g.getBoundingClientRect();
        wrap.style.transformOrigin = f(r.left + r.width / 2 - wr.left) + 'px ' + f(r.top + r.height / 2 - wr.top) + 'px';
      } else wrap.style.transformOrigin = '50% 50%';
      wrap.classList.add(dir === 'in' ? 'zoom-out' : 'zoom-back');
      setTimeout(function () {
        swap();
        wrap.classList.remove('zoom-out', 'zoom-back');
        wrap.style.transformOrigin = '50% 50%';
        wrap.classList.add(dir === 'in' ? 'zoom-in-start' : 'zoom-from-big');
        void wrap.offsetWidth;
        wrap.classList.remove('zoom-in-start', 'zoom-from-big');
      }, 280);
    }
    function openSegment(segId, fromId) {
      if (!ROOT.segments || !ROOT.segments[segId]) return;
      if (DR && DR.owner === self) closeDrawer();
      hoverOff(); rest();
      if (S.view === 'spec') setView('map');
      zoom(fromId, 'in', function () {
        var sp = ROOT.segments[segId];
        sp.nodes = sp.nodes || []; sp.edges = sp.edges || []; sp.flows = sp.flows || [];
        S.spec = sp; S.seg = segId; S.flow = 0; S.step = -1;
        renderAll();
      });
    }
    function leaveSegment(focusId) {
      if (!S.seg) return;
      var parent = S.spec.parent;
      if (DR && DR.owner === self) closeDrawer();
      hoverOff(); rest();
      zoom(null, 'out', function () {
        S.spec = ROOT; S.seg = null; S.step = -1;
        S.flow = Math.min(Math.max(0, +ui().flow || 0), Math.max(0, ROOT.flows.length - 1));
        renderAll();
        var id = typeof focusId === 'string' ? focusId : parent;
        if (S.nref[id]) {
          var g = S.nref[id].g;
          g.classList.add('sel');
          setTimeout(function () { if (!(DR && DR.owner === self)) g.classList.remove('sel'); }, 1600);
        }
      });
    }

    /* ── the audit: every canvas, measured from the routing itself ───────── */
    function audit(add) {
      var inSpine = !!fig.closest('.spine, .results'), cap = inSpine ? 9 : 12, pre = 'drawing ' + ID + ': ';
      var canvases = [{ name: 'root', spec: ROOT }];
      Object.keys(ROOT.segments || {}).forEach(function (k) { canvases.push({ name: k, spec: ROOT.segments[k] }); });
      var segMax = 0, zones = 0, flowsOk = true, flowsMax = 0, longest = 0, cross = [], thru = [], shrunk = 0, zl = [];
      canvases.forEach(function (c, i) {
        var sp = c.spec, n = (sp.nodes || []).length, fl = (sp.flows || []).length;
        if (i) segMax = Math.max(segMax, n);
        zones = Math.max(zones, (sp.zones || []).length);
        flowsMax = Math.max(flowsMax, fl);
        if (fl > 3) flowsOk = false;
        (sp.flows || []).forEach(function (x) { longest = Math.max(longest, (x.steps || []).length); });
        var L = layout(sp);
        crossings(L).forEach(function (x) { cross.push(c.name + ': ' + x); });
        throughBoxes(L).forEach(function (x) { thru.push(c.name + ': ' + x); });
        shrunk += shrunkLabels(sp, fig);
        zoneLabelHits(L, fig).forEach(function (x) { zl.push(c.name + ': ' + x); });
      });
      var nRoot = ROOT.nodes.length;
      add(pre + 'boxes', nRoot, '≤ ' + cap, nRoot <= cap);
      if (canvases.length > 1) add(pre + 'boxes in the largest segment', segMax, '≤ 12', segMax <= 12);
      add(pre + 'zones', zones, '≤ 4', zones <= 4);
      add(pre + 'flows', flowsMax, '0 – 3', flowsOk);
      add(pre + 'longest flow', longest, '≤ 9', longest <= 9);
      var w = restWords(ROOT);
      add(pre + 'words on canvas at rest', w, '≤ 60', w <= 60);
      add(pre + 'crossings', cross.length ? cross.length + ' (' + cross.join('; ') + ')' : 0, '0', !cross.length);
      add(pre + 'connections through boxes', thru.length ? thru.length + ' (' + thru.join('; ') + ')' : 0, '0', !thru.length);
      add(pre + 'labels shrunk to fit', shrunk, '0', shrunk === 0);
      add(pre + 'zone labels crossed', zl.length ? zl.length + ' (' + zl.join('; ') + ')' : 0, '0', !zl.length);
    }

    /* ── the instance API: what the page-level code may call ─────────────── */
    self.id = ID;
    self.select = select;
    self.view = function () { return S.view; };
    self.hasFlows = hasFlows;
    self.stepBy = stepBy;
    self.play = play;
    self.escape = function () {
      if (S.step >= 0 || S.playing) rest();
      else if (S.seg) leaveSegment();
    };
    self.motionChanged = function () { if (still() && S.playing) { /* packets now jump; the walk goes on */ } setPlay(); };
    self.audit = audit;
    self.refreshNotes = function () {
      if (!(DR && DR.owner === self)) return;
      $$('.notebox textarea', DR.body).forEach(function (ta) {
        if (document.activeElement === ta) return;
        var k = ta.id.replace(/^fvnote-/, '');
        Object.keys(notes()).forEach(function (full) {
          if (full.replace(/[^\w-]/g, '_') === k) ta.value = noteText(notes()[full]);
        });
      });
    };

    build();
    renderAll();
    setView(S.view, true);
    fig._fvd = self;
    return self;
  }

  /* ═════════════════════════ mount ═══════════════════════════════════════ */
  function mount() {
    $$('figure.fv-drawing').forEach(function (fig) {
      if (fig._fvd) return;
      var d = Drawing(fig);
      if (d) INST.push(d);
    });
    if (!INST.length) return;
    if (!motionIntoPill()) {
      window.addEventListener('load', function () {
        if (motionIntoPill()) return;
        /* no pill on this page: the switch goes into the first drawing's own chrome */
        var host = $('.fv-drawing .fv-tools') || $('.fv-drawing .fv-layers');
        if (!host || $('.fv-motion', host)) return;
        var b = h('button', host.classList.contains('fv-tools') ? 'fv-tbtn fv-motion' : 'fv-motion', null, host);
        b.type = 'button'; paintMotion(b); b.addEventListener('click', toggleMotion);
      });
    }
    if (FV && FV.onHydrate) FV.onHydrate(function () {
      document.documentElement.classList.toggle('still', !motionOn());
      $$('.fv-motion').forEach(paintMotion);
      INST.forEach(function (d) { d.refreshNotes(); });
    });
    if (FV && Array.isArray(FV.auditHooks)) {
      FV.auditHooks.push(function (add) { INST.forEach(function (d) { d.audit(add); }); });
    }
  }
  document.documentElement.classList.toggle('still', !motionOn());
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
