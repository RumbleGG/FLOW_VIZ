/* ===========================================================================
   FLOW_VIZ — flow.js  (v0.6.0)
   One IIFE. No dependencies. Works from file:// and from http://localhost.

   A deliverable declares, before this script (the build writes it):
     window.FLOW = { doc:'api-500-rootcause', version:'0.6.0', kind:'report', built:'…' }

   State shape (also the on-disk sidecar <doc>.flow.json), schema 5:
     { schema:5, doc, flowviz, savedAt,
       ui:{theme:'auto'|'light'|'dark', motion, draw:{<drawingId>:{…}}},
       vars:{host:'app-vm-01'},          // data-var inputs
       checks:{'<id>':true},                 // label.chk checkboxes
       open:{'<rowid>':true},                // which rows were expanded
       steps:{'<id>':{done,acked}},
       captures:{'<id>':{text,exit,verdict,at,note,runs:[{text,exit,verdict,at}]}},
       notes:{'<drawingId>/[<segment>/]<node|edge|step>:<id>':{text,at}},
       emits:{'<stepId>':{'<NAME>':'<value>'}},        // derived, never typed
       added:{'b3a':{after,text,cmd,risk,at,folded?,gone?}},   // steps typed into the page
       todos:{'t1':{text,kind,ref,at,done,doneAt?,became?,gone?}},
       relabel:'<ISO time>' }    // the last flowviz relabel this state was moved through

   verdict is one of 'pass' | 'fail' | 'error' | 'saved' | null.
     error  the interpreter rejected the command — evidence about the playbook
     fail   the command ran and said no — evidence about the target
     saved  captured, matched neither regex (the chip reads "no match")

   schema 1–4 load unchanged: note, runs (2), notes (3), emits (4), added and
   todos (5) are additive and default empty. emits are re-derived from the
   captures on every load, so a stored value is a cache, never a source. A key
   this build does not know is kept, not dropped, so an older page never erases
   what a newer one saved.

   window.FLOWVIZ is the contract with draw.js (see CLAUDE.md): the live state,
   save(), onHydrate(fn), auditHooks, ptTime() and flash(). draw.js keeps its
   notes and view state in this same object, so one sidecar holds everything
   the human left, and one PUT lands it on disk.
   =========================================================================== */
(function () {
  'use strict';
  var FLOW = window.FLOW || {};
  var DOC = FLOW.doc || 'untitled';
  var VER = FLOW.version || '0.0.0';
  var KIND = FLOW.kind || 'report';
  var LSKEY = 'flowviz:' + DOC;
  var served = /^https?:$/.test(location.protocol);

  var st = {
    schema: 5, doc: DOC, flowviz: VER, savedAt: null,
    ui: { theme: 'auto' }, vars: {}, checks: {}, open: {}, steps: {}, captures: {}, notes: {},
    emits: {}, added: {}, todos: {}
  };
  var MERGED = ['ui', 'vars', 'checks', 'open', 'steps', 'captures', 'notes', 'emits', 'added', 'todos'];
  var RELABEL = relabels();
  if (RELABEL.length) st.relabel = RELABEL[RELABEL.length - 1].at;

  /* ── the contract with draw.js ─────────────────────────────────────────────
     Exported before anything can call a hook. `state` is the live object —
     merge() assigns into its sub-objects, so references stay valid.          */
  var hydrateHooks = [];
  window.FLOWVIZ = {
    doc: DOC, version: VER, kind: KIND,
    state: st,
    save: function () { save(); },
    onHydrate: function (fn) { if (typeof fn === 'function') hydrateHooks.push(fn); },
    auditHooks: [],
    ptTime: function (iso, withSeconds) { return ptTime(iso, withSeconds); },
    flash: function (b, t) { flash(b, t); }
  };
  if (!document.documentElement.hasAttribute('data-kind')) {
    document.documentElement.setAttribute('data-kind', KIND);
  }

  /* ── the pill — injected, so every deliverable has one and an old one gains
     a new control on rebuild. A report that still carries it in markup keeps it. */
  if (!document.getElementById('flowPill')) {
    var pd = document.createElement('div');
    pd.className = 'pill'; pd.id = 'flowPill';
    pd.innerHTML = '<span class="dot"></span><span id="flowPillTxt">local only</span>' +
      '<span class="sep"></span><button id="flowTheme">auto</button>' +
      '<span class="sep"></span><button id="flowDownload">state</button>';
    document.body.appendChild(pd);
  }

  /* ── theme ─────────────────────────────────────────────────────────────── */
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  /* ?theme=light|dark forces a theme for this load only — never persisted.
     It exists so a headless screenshot can reach both themes; clicking the
     theme button releases it. */
  var forcedTheme = (location.search.match(/[?&]theme=(light|dark)\b/) || [])[1] || null;
  function applyTheme() {
    var t = (st.ui && st.ui.theme) || 'auto';
    var dark = forcedTheme ? forcedTheme === 'dark'
      : (t === 'dark' || (t === 'auto' && mq.matches));
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    var b = document.getElementById('flowTheme');
    if (b) {
      if (forcedTheme) {
        b.textContent = forcedTheme + ' · url';
        b.title = 'theme forced by ?theme=' + forcedTheme + ' for this load — click to cycle and release it';
      } else {
        b.textContent = t === 'auto' ? (dark ? 'auto · dark' : 'auto · light') : t;
        b.title = 'theme: ' + t + ' — click to cycle auto → light → dark';
      }
    }
  }
  mq.addEventListener && mq.addEventListener('change', applyTheme);

  /* ── load ───────────────────────────────────────────────────────────────
     localStorage first, then the sidecar — but only if the sidecar is newer.
     The merge is a union at key level, so a sparse sidecar never deletes a
     capture you have locally. Whichever side wins, both are brought level.  */
  var loadedFrom = 'nothing';
  try {
    var raw = localStorage.getItem(LSKEY);
    if (raw) { merge(upgrade(JSON.parse(raw))); loadedFrom = 'localStorage'; }
  } catch (e) {}
  applyTheme();

  /* `flowviz relabel` moved this page's row and step ids and left each move in a
     meta, oldest first. State saved before a move (a browser's own copy) is
     re-keyed through every move it predates, in order. st carries the latest
     stamp, so the server can refuse a tab that still has the old ids.         */
  function relabels() {
    try {
      var m = document.querySelector('meta[name="flowviz-relabel"]');
      return (m && JSON.parse(m.content)) || [];
    } catch (e) { return []; }
  }
  function rekey(o, map) {
    var out = {}, rest = [], has = Object.prototype.hasOwnProperty;
    Object.keys(o).forEach(function (k) {
      if (has.call(map, k)) out[map[k]] = o[k]; else rest.push(k);
    });
    // a key no step owns keeps its place, unless a moved key landed on it
    rest.forEach(function (k) { out[has.call(out, k) ? k + '~before-relabel' : k] = o[k]; });
    return out;
  }
  function upgrade(d) {
    if (!d || typeof d !== 'object') return d;
    RELABEL.forEach(function (r) {
      if ((d.relabel || '') >= r.at) return;
      var sm = r.steps || {}, om = {}, am = {}, all = {};
      /* a step typed into the page hangs off its anchor, so b3a moves with b3;
         one already folded into the source is in the map by its own id */
      Object.keys((d.added && typeof d.added === 'object') ? d.added : {}).forEach(function (id) {
        var m = /^([a-z][0-9]+)([a-z])$/.exec(id);
        if (m && sm[m[1]] && !sm[id]) am[id] = sm[m[1]] + m[2];
      });
      Object.keys(sm).forEach(function (k) { all[k] = sm[k]; });
      Object.keys(am).forEach(function (k) { all[k] = am[k]; });
      Object.keys(r.rows || {}).forEach(function (k) { om[k] = r.rows[k]; });
      Object.keys(all).forEach(function (k) { om['step:' + k] = 'step:' + all[k]; });
      ['captures', 'steps', 'emits'].forEach(function (k) {
        if (d[k] && typeof d[k] === 'object') d[k] = rekey(d[k], all);
      });
      if (d.open && typeof d.open === 'object') d.open = rekey(d.open, om);
      if (d.added && typeof d.added === 'object') {
        d.added = rekey(d.added, all);
        Object.keys(d.added).forEach(function (k) {
          var a = d.added[k];
          if (a && sm[a.after]) a.after = sm[a.after];
        });
      }
      if (d.todos && typeof d.todos === 'object') Object.keys(d.todos).forEach(function (k) {
        var t = d.todos[k];
        if (t && all[t.ref]) t.ref = all[t.ref];
        if (t && all[t.became]) t.became = all[t.became];
      });
      d.relabel = r.at;
    });
    return d;
  }

  function merge(d) {
    if (!d) return;
    MERGED.forEach(function (k) {
      if (d[k] && typeof d[k] === 'object') st[k] = Object.assign(st[k] || {}, d[k]);
    });
    /* a key this build does not know came from a newer one: keep it, so the
       next save carries it back to disk instead of erasing it */
    Object.keys(d).forEach(function (k) {
      if (!Object.prototype.hasOwnProperty.call(st, k) && k !== 'relabel' && d[k] !== undefined) st[k] = d[k];
    });
    if (d.savedAt) st.savedAt = d.savedAt;
  }

  function noteText(n) { return typeof n === 'string' ? n : ((n && n.text) || ''); }
  function hasContent() {
    var any = Object.keys(st.captures).some(function (k) {
      return (st.captures[k].text || '').trim();
    });
    var notesAny = Object.keys(st.notes || {}).some(function (k) {
      return noteText(st.notes[k]).trim();
    });
    return any || notesAny || Object.keys(st.steps).length > 0 || Object.keys(st.checks).length > 0 ||
      Object.keys(st.added || {}).length > 0 || Object.keys(st.todos || {}).length > 0 ||
      Object.keys(st.vars).some(function (k) { return st.vars[k]; });
  }

  if (served) {
    fetch('./' + DOC + '.flow.json', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (d && (!st.savedAt || (d.savedAt || '') > st.savedAt)) {
          live = false; merge(upgrade(d)); renderAdditions(); hydrate(); applyTheme(); live = true;
          loadedFrom = 'sidecar';
          try { localStorage.setItem(LSKEY, JSON.stringify(st)); } catch (e) {}
          setPill('disk', 'loaded from disk');
        } else if (!d && hasContent()) {
          // nothing on disk but there is state here — land it so the agent can read it
          save();
        }
        console.log('[flowviz] ' + DOC + ' state loaded from ' + loadedFrom);
      })
      .catch(function () {});
  }

  /* ── save: localStorage always, disk when served ───────────────────────────
     The PUT URL is relative, so a page in a subfolder of the served root lands
     its sidecar beside itself; the server refuses anything outside its root. */
  var pill, pillTxt, timer = null;
  function setPill(cls, txt) {
    if (!pill) return;
    pill.className = 'pill ' + cls;
    pillTxt.textContent = txt;
  }
  function save() {
    clearTimeout(timer);
    timer = setTimeout(function () {
      st.savedAt = new Date().toISOString();
      try { localStorage.setItem(LSKEY, JSON.stringify(st)); } catch (e) {}
      if (!served) { setPill('', 'local only'); return; }
      fetch('_flow/state/' + DOC, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(st, null, 2)
      }).then(function (r) {
        setPill(r.ok ? 'disk' : 'err', r.ok ? 'saved ' + ptTime(st.savedAt)
          : r.status === 409 ? 'ids moved: reload' : 'save rejected');
        if (pill && r.ok) pill.title = 'last saved ' + st.savedAt + ' — stored as UTC, shown as Pacific';
      }).catch(function () { setPill('err', 'server down'); });
    }, 700);
  }

  /* ── small helpers ─────────────────────────────────────────────────────── */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function words(s) { return (s || '').trim().split(/\s+/).filter(Boolean).length; }
  /* Every timestamp is *stored* as ISO-8601 UTC — the sidecar, the agent export
     and the evidence record all stay unambiguous. Every timestamp *shown on the
     page* is Pacific, because that is the clock the human is reading it on, and
     it is labelled PDT/PST so nobody has to guess which one. */
  function ptTime(iso, withSeconds) {
    var d = iso ? new Date(iso) : new Date();
    if (isNaN(d.getTime())) return '';
    try {
      var o = { timeZone: 'America/Los_Angeles', hourCycle: 'h23',
                hour: '2-digit', minute: '2-digit', timeZoneName: 'short' };
      if (withSeconds) o.second = '2-digit';
      return d.toLocaleTimeString('en-US', o);
    } catch (e) {
      return String(iso).slice(11, withSeconds ? 19 : 16) + 'Z';   // no ICU: say UTC
    }
  }
  function pad(s, n) { s = String(s); return s + new Array(Math.max(1, n - s.length + 1)).join(' '); }
  function flash(b, t) {
    var o = b.dataset.o || b.textContent;
    b.dataset.o = o; b.textContent = t || 'copied';
    setTimeout(function () { b.textContent = o; }, 1400);
  }
  function cap(id) {
    var r = (st.captures[id] = st.captures[id] || {});
    if (!('text' in r)) r.text = '';
    if (!('exit' in r)) r.exit = '';
    if (!('verdict' in r)) r.verdict = null;
    if (!('at' in r)) r.at = null;
    if (!('note' in r)) r.note = '';
    if (!Array.isArray(r.runs)) r.runs = [];
    return r;
  }
  function step(id) {
    return (st.steps[id] = st.steps[id] || { done: false, acked: false });
  }
  function sha256(s) {
    if (!s || !(window.crypto && crypto.subtle)) return Promise.resolve(null);
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))
      .then(function (b) {
        return Array.prototype.map.call(new Uint8Array(b), function (x) {
          return ('0' + x.toString(16)).slice(-2);
        }).join('');
      }).catch(function () { return null; });
  }

  /* ── copy ──────────────────────────────────────────────────────────────── */
  // the element whose text a copy button sends: its data-for target, or the pre
  // of its block — the collapsed-row ⧉ reaches the step's pre the same way
  function copySource(btn) {
    if (btn.dataset.for) return document.getElementById(btn.dataset.for);
    var scope = btn.closest('.cmd') || btn.closest('li.step') || btn.parentElement;
    return (scope && scope.querySelector('pre')) || null;
  }
  /* innerText is '' for anything inside a closed <details> — which is exactly
     where the ⧉ on a collapsed step reaches — so fall back to textContent. In a
     <pre> the two agree: whitespace is literal, and a resolved {{step.NAME}}
     span holds its value either way. */
  function textOf(el) { return el ? (el.innerText || el.textContent || '') : ''; }
  function cmdTextFor(btn) { return textOf(copySource(btn)); }
  // strip leading prompts, drop pure-comment lines, keep continuations
  function cleanCmd(s) {
    return s.replace(/\r/g, '').split('\n')
      .map(function (l) { return l.replace(/^\s*(?:PS\s+[^>]*>|[$#>]\s)\s*/, ''); })
      .filter(function (l) { return !/^\s*(#|\/\/)/.test(l); })
      .join('\n').trim();
  }
  /* Two buttons copy the same command — `copy` inside the block, and `⧉` on the
     collapsed row. Unlabelled, ⧉ reads as "expand", so a human hand-selects the
     command instead and loses whatever the selection missed. Titled here rather
     than in every report's markup, so old reports gain it on the next build. */
  $$('.copy').forEach(function (b) {
    if (b.title) return;
    b.title = b.closest('.cmd')
      ? 'Copy this command to the clipboard'
      : 'Copy this step’s command without opening the step';
    b.setAttribute('aria-label', b.title);
  });
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.copy');
    if (!b) return;
    e.preventDefault();
    // a write step's command does not leave the page until the gate is ticked,
    // including via the ⧉ on the collapsed row — open the step and say so
    var li = b.closest('li.step');
    if (li && li.dataset.risk === 'w' && !li.classList.contains('acked')) {
      var sd = $('details.sd', li); if (sd) sd.open = true;
      flash(b, 'tick the gate'); return;
    }
    /* a command that names another step's value copies only once that value is
       real and paste-safe: a token must never reach a live console unresolved */
    var src = copySource(b);
    if (src) {
      var pend = $('.sub.pending', src), unsafe = $('.sub.bad', src);
      if (pend) { flash(b, subKey(pend).id + ' has not run'); return; }
      if (unsafe) { flash(b, subKey(unsafe).key + ' is not paste-safe'); return; }
    }
    var txt = cleanCmd(textOf(src));
    if (!txt) return;
    navigator.clipboard.writeText(txt).then(function () { flash(b); },
      function () { flash(b, 'blocked'); });
  });

  /* ── emits: a value one step prints, handed to a later step's command ──────
     Producer: <textarea data-cap="b1" data-emit="VER=VERSION ([0-9][0-9.]+)">.
     One or more NAME=<regex> pairs; each needs exactly one capture group, and
     the value is group 1 of the LAST match, trimmed. Derived from the current
     capture only — never runs[] — on every paste, on re-run, and on every load,
     so fixing a regex fixes the value, the same way reverdict() fixes a verdict.
     Consumer: {{b1.VER}} anywhere inside a .cmd pre, figures included. A bad
     pair is skipped with a warning here; the audit and the build refuse it. */
  var EMIT_SPLIT = /;\s*(?=[A-Z][A-Z0-9_]*=)/;
  var EMIT_NAME = /^[A-Z][A-Z0-9_]*$/;
  var emitRules = {};                    // step id -> [{name, re}], compiled once
  function rulesFor(ta) {
    var id = ta.dataset.cap;
    if (emitRules[id]) return emitRules[id];
    var out = [];
    String(ta.dataset.emit || '').split(EMIT_SPLIT).forEach(function (pair) {
      pair = pair.replace(/^\s+/, '');
      if (!pair) return;
      var eq = pair.indexOf('='), name = eq > 0 ? pair.slice(0, eq) : '', src = pair.slice(eq + 1);
      if (!EMIT_NAME.test(name)) {
        console.warn('[flowviz] data-emit on ' + id + ': "' + pair.slice(0, 40) + '" is not NAME=<regex> — skipped');
        return;
      }
      var re, groups;
      try {
        re = new RegExp(src, 'g');
        groups = new RegExp(src + '|').exec('').length - 1;
      } catch (e) {
        console.warn('[flowviz] data-emit on ' + id + ': ' + name + ' does not compile — skipped (' + e.message + ')');
        return;
      }
      if (groups !== 1) {
        console.warn('[flowviz] data-emit on ' + id + ': ' + name + ' has ' + groups +
          ' capture groups, needs exactly one — skipped');
        return;
      }
      out.push({ name: name, re: re });
    });
    return (emitRules[id] = out);
  }
  function sameMap(a, b) {
    var ka = Object.keys(a || {}), kb = Object.keys(b || {});
    return ka.length === kb.length && ka.every(function (k) {
      return Object.prototype.hasOwnProperty.call(b, k) && a[k] === b[k];
    });
  }
  // re-derive one step's values from its current capture; true if anything moved
  function deriveEmits(ta) {
    var id = ta.dataset.cap, text = (st.captures[id] || {}).text || '', next = {};
    if (text.trim()) rulesFor(ta).forEach(function (r) {
      var m, last = null;
      r.re.lastIndex = 0;
      while ((m = r.re.exec(text)) !== null) {
        last = m;
        if (m[0] === '') r.re.lastIndex++;          // an empty match must still advance
      }
      if (last && last[1] !== undefined) next[r.name] = String(last[1]).trim();
    });
    var moved = !sameMap(st.emits[id], next);
    if (Object.keys(next).length) st.emits[id] = next; else delete st.emits[id];
    return moved;
  }
  // every step, from the stored captures and the current rules; a step that no
  // longer declares an emit loses whatever an older build stored for it
  function rederiveEmits() {
    var moved = false, owned = {};
    $$('textarea[data-cap]').forEach(function (ta) {
      owned[ta.dataset.cap] = 1;
      if (deriveEmits(ta)) moved = true;
    });
    Object.keys(st.emits).forEach(function (id) {
      if (!owned[id]) { delete st.emits[id]; moved = true; }
    });
    return moved;
  }

  /* Tokens become spans once, at init — text nodes only, existing markup left
     alone. A token preceded by `$` is someone else's syntax (GitHub's ${{ … }})
     and is never touched. The span then shows the value when it is real and
     paste-safe, and the literal token otherwise, so what you read is what the
     copy button will send. */
  var TOKEN = /\{\{([A-Za-z0-9][\w-]*)\.([A-Z][A-Z0-9_]*)\}\}/g;
  function wrapTokens(pre) {
    var walk = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT, null), nodes = [], n;
    while ((n = walk.nextNode())) nodes.push(n);
    // plan every hit before splitting anything, so each `$` check reads the
    // original text, including the tail of the previous text node
    var plan = nodes.map(function (node, i) {
      var hits = [], text = node.data, m;
      if (node.parentNode && node.parentNode.closest && node.parentNode.closest('.sub')) return hits;
      TOKEN.lastIndex = 0;
      while ((m = TOKEN.exec(text)) !== null) {
        var prev = m.index > 0 ? text.charAt(m.index - 1) : (i > 0 ? nodes[i - 1].data.slice(-1) : '');
        if (prev !== '$') hits.push({ at: m.index, len: m[0].length, key: m[1] + '.' + m[2] });
      }
      return hits;
    });
    nodes.forEach(function (node, i) {
      for (var k = plan[i].length - 1; k >= 0; k--) {     // from the end: offsets stay valid
        var h = plan[i][k], tok = node.splitText(h.at);
        tok.splitText(h.len);
        var span = document.createElement('span');
        span.className = 'sub pending';
        span.setAttribute('data-sub', h.key);
        span.textContent = '{{' + h.key + '}}';
        tok.parentNode.replaceChild(span, tok);
      }
    });
  }
  function subKey(el) {
    var key = el.getAttribute('data-sub') || '', dot = key.indexOf('.');
    return { key: key, id: key.slice(0, dot), name: key.slice(dot + 1) };
  }
  /* Paste-safe: printable ASCII, 1–120 characters, and none of the characters a
     shell would act on. A value that fails stays a token and refuses to copy —
     a version string never needs a quote, a `$` or a parenthesis. */
  var SAFE = /^[\x20-\x7E]{1,120}$/, UNSAFE = /[`$"'\\;|&<>(){}]/;
  function pasteSafe(v) { return SAFE.test(v) && !UNSAFE.test(v); }
  function paintSubs() {
    $$('.cmd pre .sub[data-sub]').forEach(function (s) {
      var k = subKey(s), vals = st.emits[k.id] || {};
      var has = Object.prototype.hasOwnProperty.call(vals, k.name), v = has ? vals[k.name] : null;
      var token = '{{' + k.key + '}}';
      if (!has) {
        s.className = 'sub pending'; s.textContent = token; s.title = 'waiting for step ' + k.id;
      } else if (pasteSafe(v)) {
        s.className = 'sub ok'; s.textContent = v; s.title = 'from step ' + k.id;
      } else {
        s.className = 'sub bad'; s.textContent = token; s.title = k.key + ' is not paste-safe';
      }
    });
  }
  $$('.cmd pre').forEach(wrapTokens);

  /* ── labels: rows are lettered, steps are letter + number ─────────────────
     A row whose id is one letter shows that letter; a step whose id is a letter
     and a number (b1) shows its id instead of the counter, so "look at b3" means
     the same thing on screen, in the sidecar and in the agent's read-back.
     Other ids keep the counter, so an older report looks as it did. A step
     folded in from the page keeps the id it was given there: b3a.          */
  $$('details.row').forEach(function (d) {
    if (!/^[a-z]$/.test(d.dataset.row || '')) return;
    var o = $('summary .ord', d); if (o) o.textContent = d.dataset.row;
  });
  $$('li.step').forEach(function (li) {
    var id = li.dataset.step || '';
    if (!/^[a-z][0-9]+[a-z]?$/.test(id)) return;
    var n = $('.sd>summary .n', li);
    if (n) { n.textContent = id; li.classList.add('named'); }
  });
  // the label a human sees for each step: its id when named, else the counter
  // (which counts only unnamed steps, per playbook, exactly as the CSS does)
  function stepLabels() {
    var out = {};
    $$('ol.steps').forEach(function (ol) {
      var c = 0;
      $$('li.step', ol).forEach(function (li) {
        out[li.dataset.step] = li.classList.contains('named') ? li.dataset.step : String(++c);
      });
    });
    return out;
  }

  /* ── rows ──────────────────────────────────────────────────────────────── */
  $$('details.row').forEach(function (d) {
    d.addEventListener('toggle', function () { st.open[d.dataset.row] = d.open; save(); });
  });
  /* What each row is for. The agent writes one attribute, data-kind; the label is
     injected here, so every report says it in the same words, in the same place.
     Action kinds lead with "action ·", so a row you only read never looks like a
     row where you have to do something. */
  var ROW_KIND = {
    context: ['context', 'read', 'Background to read. Nothing to do here.'],
    finding: ['finding', 'read', 'What the evidence shows. Read it; nothing to run.'],
    record: ['record', 'read', 'What was done, and how to undo it.'],
    investigation: ['action · investigation', 'act', 'Commands that gather facts. They change nothing.'],
    test: ['action · test', 'act', 'Commands that check that something works.'],
    change: ['action · change', 'act', 'Commands that change a system. Each write is gated.'],
    rollback: ['action · rollback', 'act', 'Commands that undo a change.'],
    decision: ['decision', 'decide', 'Yours to approve or choose.']
  };
  $$('details.row').forEach(function (d) {
    var k = ROW_KIND[d.dataset.kind], s = $('summary', d), cl = s && $('.cl', s);
    if (!k || !cl || $('.rk', s)) return;
    var b = document.createElement('span');
    b.className = 'rk rk-' + d.dataset.kind;
    b.textContent = k[0];
    b.title = k[2];
    s.insertBefore(b, cl);
    var rt = $('.rt', s);
    if (rt && !rt.title) rt.title = 'about ' + rt.textContent.trim() + (k[1] === 'read' ? ' to read' : ' to work through');
  });
  // one column: every label as wide as the widest, so the claims start in line
  (function () {
    var ks = $$('details.row > summary > .rk');
    var w = Math.max.apply(null, [0].concat(ks.map(function (k) { return k.getBoundingClientRect().width; })));
    if (w) document.documentElement.style.setProperty('--rk-w', Math.ceil(w) + 'px');
  })();

  var xa = $('#flowExpand'), ca = $('#flowCollapse');
  if (xa) xa.addEventListener('click', function () { $$('details.row').forEach(function (d) { d.open = true; }); });
  if (ca) ca.addEventListener('click', function () { $$('details.row').forEach(function (d) { d.open = false; }); });

  /* ── plain checkboxes + text vars ──────────────────────────────────────── */
  $$('[data-ck]').forEach(function (c) {
    c.addEventListener('change', function () { st.checks[c.dataset.ck] = c.checked; save(); });
  });
  $$('[data-var]').forEach(function (i) {
    i.addEventListener('input', function () { st.vars[i.dataset.var] = i.value; save(); });
  });

  /* ── playbook steps ────────────────────────────────────────────────────── */
  /* An interpreter error is evidence about the playbook, not about the target:
     the command never ran, so data-pass and data-fail are both meaningless and
     whichever one happens to match the error text is a lie. Tested first.

     Deliberately narrow — parse failures and unresolved names only. It does NOT
     include the generic PowerShell footer (FullyQualifiedErrorId, CategoryInfo),
     because a legitimately expected failure prints that too: an access-denied
     probe is a `fail`, not an `error`. A command that ran and returned the wrong
     answer stays a `fail`.

     This list exists twice — here and in bin/flowviz-captures.py. Change both. */
  var CMD_ERR = [
    /\bParserError\b/,                              // PowerShell, parse
    /\bUnexpected token\b/i,
    /\bMissing (?:closing|expression|argument|statement)\b/i,
    /\bstring (?:is )?missing the terminator\b/i,    // unterminated quote / here-string
    /\bpositional parameter cannot be found\b/i,     // malformed invocation
    /\bis not recognized as the name of\b/i,         // PowerShell, name lookup
    /\bCommandNotFoundException\b/,
    /\bcommand not found\b/i,                        // sh / bash
    /\bsyntax error near unexpected token\b/i,
    /\bunexpected EOF while looking for matching\b/i,
    /\b(?:SyntaxError|IndentationError|TabError):/    // python
  ];
  function cmdError(v) {
    return CMD_ERR.some(function (re) { return re.test(v); });
  }
  // a malformed author regex must not take the paste handler down with it
  function hit(pat, v) {
    if (!pat) return false;
    try { return new RegExp(pat, 'i').test(v); } catch (e) { return false; }
  }
  function verdictOf(ta, v) {
    if (!v.trim()) return null;
    if (cmdError(v)) return 'error';
    if (hit(ta.dataset.fail, v)) return 'fail';
    if (hit(ta.dataset.pass, v)) return 'pass';
    return 'saved';
  }
  var VD_LABEL = { pass: 'pass', fail: 'fail', error: 'error', saved: 'no match' };
  /* The foot chip has room the row header's column does not: a glyph, so the
     verdict reads without reading, and a plainer empty state than a dash. */
  var VD_GLYPH = { pass: '✓', fail: '✕', error: '⚠', saved: '?' };
  var VD_HINT = {
    pass: 'matched this step\'s pass signal',
    fail: 'matched this step\'s fail signal — that is evidence about the target',
    error: 'the interpreter rejected this command — the target was never asked',
    saved: 'captured, but it matched neither the pass nor the fail signal'
  };
  /* Flashing the foot chip is feedback for a paste, not for a page load — so it
     stays off until the first hydrate has finished, and off again while a
     sidecar arriving from disk repaints every step at once. */
  var live = false;
  // read-only peek, so painting never creates an empty record in the sidecar
  function peek(id) {
    var r = st.captures[id] || {};
    return { text: r.text || '', exit: r.exit || '', verdict: r.verdict || null,
             at: r.at || null, note: r.note || '', runs: r.runs || [] };
  }
  function paintCapture(id) {
    var r = peek(id), ta = $('textarea[data-cap="' + id + '"]');
    /* Every chip keyed to this step, not just the first: there are two now — the
       one in the row header, and one at the foot of the step beside `Done`,
       because after a long paste the header is off the top of the screen and
       pass/fail is the one thing the human scrolled down for.               */
    /* a step with no data-pass and no data-fail — one typed into the page,
       until the agent folds it — has no rule to miss, so it reads `captured`,
       never `no match`, which would blame a pass condition that is not there */
    var norule = !!ta && !ta.dataset.pass && !ta.dataset.fail;
    $$('[data-vd="' + id + '"]').forEach(function (chip) {
      var foot = chip.classList.contains('vdf');
      var was = chip.dataset.v, now = r.verdict || '';
      var plain = now === 'saved' && norule;
      chip.className = 'vd' + (foot ? ' vdf' : '') + (now ? ' ' + now : '');
      chip.textContent = foot
        ? (now ? (plain ? '● captured' : VD_GLYPH[now] + ' ' + VD_LABEL[now]) : '· not captured')
        : (plain ? 'captured' : VD_LABEL[now] || '—');
      chip.title = (plain ? 'captured: this step has no pass rule yet, so there is nothing to match' : VD_HINT[now]) ||
        (foot ? 'paste the output above — this then reads pass, fail, error or no match' : '');
      chip.dataset.v = now;
      // a verdict that just changed under your cursor gets one pulse, once
      if (foot && live && was !== undefined && was !== now && now) {
        void chip.offsetWidth; chip.classList.add('fl');
      }
    });
    var cnt = $('[data-cnt="' + id + '"]');
    if (cnt && ta) {
      var v = ta.value;
      cnt.textContent = v.trim() ? v.split('\n').length + ' lines · ' + v.length + ' chars' : 'empty';
    }
    var at = $('[data-at="' + id + '"]');
    if (at) {
      at.textContent = r.at ? 'captured ' + ptTime(r.at, true) : '';
      at.title = r.at ? r.at + ' — stored as UTC, shown as Pacific' : '';
    }
    var rn = $('[data-run="' + id + '"]');
    if (rn) rn.textContent = r.runs.length ? 'run ' + (r.runs.length + 1) : '';
    var rr = $('[data-rr="' + id + '"]');
    if (rr) rr.disabled = !(r.text || '').trim();
  }
  function paintStep(li) {
    var id = li.dataset.step, s = step(id);
    li.classList.toggle('done', !!s.done);
    li.classList.toggle('acked', !!s.acked);
    paintFin(li);
    var after = li.dataset.after;
    if (after) {
      var blocked = !(st.steps[after] && st.steps[after].done) &&
                    !((st.captures[after] || {}).text || '').trim();
      li.classList.toggle('dim', blocked);
    }
  }
  function paintProgress(pb) {
    var lis = $$('li.step', pb);
    var done = 0, fail = 0, err = 0;
    lis.forEach(function (li) {
      if (step(li.dataset.step).done) done++;
      var v = (st.captures[li.dataset.step] || {}).verdict;
      if (v === 'fail') fail++;
      else if (v === 'error') err++;
    });
    var p = $('.prog', pb);
    if (p) p.innerHTML = done + ' / ' + lis.length + ' done' +
      (fail ? ' · <span class="f">' + fail + ' failed</span>' : '') +
      (err ? ' · <span class="e">' + err + ' errored</span>' : '');
  }
  function repaintAll() {
    $$('li.step').forEach(paintStep);
    $$('.pb').forEach(paintProgress);
    paintMissed();
  }

  /* Two controls finish one step. The checkbox in the row header stays, but the
     work ends at the bottom of the step, and scrolling back up past the capture
     box to tick a box is friction — so every step gets a `Done ☐` button at its
     foot. Pressing it ticks the tick in place (☐ → ✅, an animation you cannot
     miss), then folds the step away 300 ms later: the step is finished, so its
     depth stops competing with the next one. Injected here rather than in every
     report's markup, so old reports gain it on the next build. hydrate() paints
     it but never collapses or animates — persisted open state wins there.      */
  var BOX = '☐', TICK = '✅';   // an open box, then the green check
  var COLLAPSE_MS = 300;                 // long enough to see the tick land
  function collapseStep(li) {
    var sd = $('details.sd', li);
    if (sd && sd.open) {
      sd.open = false;                          // the toggle handler persists this
      li.scrollIntoView({ block: 'nearest' });  // the page just got shorter
    }
  }
  function paintFin(li, animate) {
    var b = $('.fin>button', li); if (!b) return;
    var on = !!step(li.dataset.step).done, bx = $('.bx', b);
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.title = on ? 'Marked done — press again if that was wrong'
                 : 'Mark this step done — it collapses, so the next step is where you are looking';
    if (!bx) return;
    bx.textContent = on ? TICK : BOX;
    bx.classList.remove('pop');
    if (animate && on) { void bx.offsetWidth; bx.classList.add('pop'); }  // restart it
  }
  function setDone(li, on, collapse) {
    step(li.dataset.step).done = on;
    var dn = $('input.done', li); if (dn) dn.checked = on;
    if (on && collapse) collapseStep(li);
    repaintAll(); save();
  }

  /* every step is bound here: authored ones at load, and each step typed into
     the page as it is drawn, so both behave alike in every respect */
  function bindStep(li) {
    var id = li.dataset.step;
    var sd = $('details.sd', li);
    var inb = $('.sd>.in', li);      // the step body, not the `why this step` .in
    if (inb && !$('.fin', inb)) {
      var fin = document.createElement('div');
      fin.className = 'fin';
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'fd';
      b.innerHTML = 'Done <span class="bx"></span>';
      /* the verdict, repeated where the work ends — same `data-vd` key, so one
         paint path feeds both chips and a step that captures nothing gets no
         chip at all rather than a permanent `not captured`. aria-live, because
         a paste changes it without anything moving focus.                    */
      if ($('textarea[data-cap="' + id + '"]', li)) {
        var vd = document.createElement('span');
        vd.className = 'vd vdf';
        vd.setAttribute('data-vd', id);
        vd.setAttribute('aria-live', 'polite');
        fin.appendChild(vd);
      }
      /* Done sits in the bottom-right corner with the verdict just before it:
         the eye reads "pass", then the hand ticks it off, in one place. */
      fin.appendChild(b);
      inb.appendChild(fin);
      b.addEventListener('click', function () {
        var on = !step(id).done;
        setDone(li, on, false);            // the collapse waits for the animation
        paintFin(li, on);
        if (on) setTimeout(function () { collapseStep(li); }, COLLAPSE_MS);
      });
    }
    var hdr = $('input.done', li);
    if (hdr) hdr.addEventListener('change', function () { setDone(li, hdr.checked, true); });
    var ak = $('input.ack', li);
    if (ak) ak.addEventListener('change', function () {
      step(id).acked = ak.checked; paintStep(li); save();
    });
    if (sd) sd.addEventListener('toggle', function () { st.open['step:' + id] = sd.open; save(); });
  }
  $$('li.step').forEach(bindStep);

  function bindCaptureIn(root) {
  $$('textarea[data-cap]', root).forEach(function (ta) {
    ta.addEventListener('input', function () {
      var id = ta.dataset.cap, r = cap(id);
      r.text = ta.value;
      r.at = ta.value.trim() ? new Date().toISOString() : null;
      r.verdict = verdictOf(ta, ta.value);
      deriveEmits(ta);
      paintCapture(id);
      paintSubs();
      /* repaint every step, not just this playbook's progress: a capture is what
         releases a `data-after` step, and it should light up on the paste */
      repaintAll();
      save();
    });
  });
  $$('input[data-ec]', root).forEach(function (i) {
    i.addEventListener('input', function () { cap(i.dataset.ec).exit = i.value; save(); });
  });
  $$('input[data-note]', root).forEach(function (i) {
    i.addEventListener('input', function () { cap(i.dataset.note).note = i.value; save(); });
  });

  /* ── re-run: keep the old attempt, clear the box for a fresh one ────────── */
  $$('[data-rr]', root).forEach(function (b) {
    b.addEventListener('click', function () {
      var id = b.dataset.rr, r = cap(id);
      if (!(r.text || '').trim()) return;
      r.runs.push({ text: r.text, exit: r.exit, verdict: r.verdict, at: r.at });
      r.text = ''; r.exit = ''; r.verdict = null; r.at = null;
      var ta = $('textarea[data-cap="' + id + '"]'); if (ta) { ta.value = ''; ta.focus(); }
      var ec = $('input[data-ec="' + id + '"]'); if (ec) ec.value = '';
      if (ta) deriveEmits(ta); else delete st.emits[id];
      var li = $('li.step[data-step="' + id + '"]');
      if (li) setDone(li, false, false); else { step(id).done = false; }
      paintCapture(id); paintSubs(); repaintAll(); save();
      flash(b, 'run ' + (r.runs.length + 1));
    });
  });
  }
  bindCaptureIn(document);

  /* ── export for the agent ──────────────────────────────────────────────── */
  function notesForExport() {
    var out = {};
    Object.keys(st.notes || {}).forEach(function (k) {
      var n = st.notes[k], t = noteText(n);
      if (t.trim()) out[k] = { text: t, at: (n && n.at) || null };
    });
    return out;
  }
  var ac = $('#flowAgentCopy');
  if (ac) ac.addEventListener('click', function () {
    var out = { doc: DOC, flowviz: VER, at: new Date().toISOString(),
                vars: st.vars, captures: {}, done: [] };
    var labels = stepLabels();
    Object.keys(st.captures).forEach(function (k) {
      var r = st.captures[k];
      if ((r.text || '').trim()) {
        out.captures[k] = { text: r.text, exit: r.exit, verdict: r.verdict, at: r.at };
        if (labels[k]) out.captures[k].step = labels[k];
        if (r.note) out.captures[k].note = r.note;
        if (r.runs && r.runs.length) out.captures[k].priorRuns = r.runs.length;
      }
    });
    Object.keys(st.steps).forEach(function (k) { if (st.steps[k].done) out.done.push(k); });
    var notes = notesForExport(), nn = Object.keys(notes).length;
    if (nn) out.notes = notes;
    var emits = {};
    Object.keys(st.emits || {}).forEach(function (k) {
      if (Object.keys(st.emits[k] || {}).length) emits[k] = st.emits[k];
    });
    if (Object.keys(emits).length) out.emits = emits;
    // what the human added to the page: steps (their output is under captures) and to-dos
    var added = {}, todos = {};
    liveKeys(st.added).forEach(function (k) {
      var a = st.added[k];
      added[k] = { after: a.after, text: a.text, cmd: a.cmd || '', risk: a.risk, at: a.at };
      if (a.folded) added[k].folded = a.folded;
    });
    liveKeys(st.todos).forEach(function (k) { todos[k] = st.todos[k]; });
    var na = Object.keys(added).length, nt = Object.keys(todos).length;
    if (na) out.added = added;
    if (nt) out.todos = todos;
    var n = Object.keys(out.captures).length;
    navigator.clipboard.writeText('```json\n' + JSON.stringify(out, null, 2) + '\n```')
      .then(function () {
        flash(ac, n + ' capture' + (n === 1 ? '' : 's') +
          (nn ? ' · ' + nn + ' note' + (nn === 1 ? '' : 's') : '') +
          (na ? ' · ' + na + ' added' : '') + (nt ? ' · ' + nt + ' to-do' + (nt === 1 ? '' : 's') : '') + ' copied');
      }, function () { flash(ac, 'clipboard blocked'); });
  });

  var dl = $('#flowDownload');
  if (dl) dl.addEventListener('click', function () {
    download(DOC + '.flow.json', JSON.stringify(st, null, 2), 'application/json');
  });

  function download(name, text, type) {
    var b = new Blob([text], { type: type || 'text/plain' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = name; a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }

  /* ── turnover evidence record ───────────────────────────────────────────
     A flat text file you can attach to a change record: every capture in
     document order, with its command, exit code, timestamp and SHA-256.
     Superseded runs are kept, because "we tried it twice" is itself
     evidence. sha256 needs a secure context; over 127.0.0.1 you have one.
     Notes left on drawings close the record, keyed as they are stored.    */
  var ev = $('#flowEvidence');
  if (ev) ev.addEventListener('click', function () {
    var now = new Date().toISOString();
    var L = [];
    var bar = new Array(75).join('─');
    L.push('FLOW_VIZ EVIDENCE RECORD');
    L.push('doc        ' + DOC);
    L.push('template   ' + KIND + '@' + VER);
    L.push('exported   ' + now);
    L.push('source     ' + location.href.split('?')[0]);
    var title = $('.card h1') || $('h1');
    if (title) L.push('report     ' + title.innerText.trim());
    var vk = Object.keys(st.vars).filter(function (k) { return st.vars[k]; });
    if (vk.length) L.push('variables  ' + vk.map(function (k) { return k + '=' + st.vars[k]; }).join('  '));
    L.push('');

    var jobs = [];             // texts to hash; a marker holds each one's place
    var MK = String.fromCharCode(0xE000), MKE = String.fromCharCode(0xE001);
    function line(s) { L.push(s); }
    function emitCapture(id, n, sentence, risk, cmd, how) {
      var r = peek(id);
      var vd = ((how && how.norule && r.verdict === 'saved' ? 'captured' : VD_LABEL[r.verdict]) || 'not captured').toUpperCase();
      line(bar);
      line('step ' + (n === id ? id : n + ' · ' + id) + ' · ' + (risk === 'w' ? 'WRITE' : 'read') + ' · ' + vd +
           (how && how.added ? ' · ADDED IN THE PAGE' : ''));
      line(bar);
      line(sentence);
      if (how && how.note) line(how.note);
      if (cmd) {
        var cl = cmd.split('\n');
        line('command    ' + cl[0]);
        cl.slice(1).forEach(function (x) { line('           ' + x); });
      }
      if ((r.text || '').trim()) {
        line('captured   ' + (r.at || '—') + '   exit ' + (r.exit === '' ? '—' : r.exit) +
             '   ' + r.text.split('\n').length + ' lines, ' + r.text.length + ' chars');
        var em = st.emits[id] || {}, en = Object.keys(em);
        if (en.length) line('emits      ' + en.map(function (k) { return k + '=' + em[k]; }).join('  '));
        L.push(MK + jobs.length + MKE);
        jobs.push(r.text);
        line('output');
        r.text.replace(/\r/g, '').split('\n').forEach(function (x) { line('  | ' + x); });
      } else {
        line('captured   —  (no output recorded)');
      }
      if (r.note) line('note       ' + r.note);
      r.runs.forEach(function (p, i) {
        line('');
        line('  superseded run ' + (i + 1) + '  ' + (p.at || '—') +
             '  exit ' + (p.exit === '' ? '—' : p.exit) +
             '  verdict ' + (p.verdict || '—'));
        (p.text || '').replace(/\r/g, '').split('\n').forEach(function (x) { line('    | ' + x); });
      });
      line('');
    }

    var seen = {}, labels = stepLabels();
    $$('.pb').forEach(function (pb) {
      var t = $('.hd .t', pb), p = $('.hd .prog', pb);
      line('PLAYBOOK   ' + (t ? t.innerText.trim() : '(untitled)') +
           '        ' + (p ? p.innerText.trim() : ''));
      line('');
      $$('li.step', pb).forEach(function (li, i) {
        var id = li.dataset.step; seen[id] = 1;
        var ds = $('.ds', li), pre = $('.cmd pre', li), ta = $('textarea[data-cap]', li);
        var ad = li.classList.contains('added') && st.added[id];
        emitCapture(id, labels[id] || String(i + 1), textOf(ds).trim(), li.dataset.risk,
                    textOf(pre).trim(), { added: !!ad, norule: !!ta && !ta.dataset.pass && !ta.dataset.fail,
                    note: ad ? 'added      ' + (ad.at || '—') + '   after ' + ad.after + '   not in the source yet' : '' });
      });
    });
    var loose = Object.keys(st.captures).filter(function (k) {
      return !seen[k] && (st.captures[k].text || '').trim();
    });
    if (loose.length) {
      line('OTHER CAPTURES'); line('');
      loose.forEach(function (id, i) { emitCapture(id, '·', '(outside a playbook)', 'ro', ''); });
    }
    var cks = Object.keys(st.checks).filter(function (k) { return st.checks[k]; });
    if (cks.length) { line('checked    ' + cks.join(', ')); line(''); }

    var notes = notesForExport(), nk = Object.keys(notes);
    if (nk.length) {
      line('NOTES ON DRAWINGS'); line('');
      nk.forEach(function (k) {
        line(k + '   ' + (notes[k].at || '—'));
        notes[k].text.replace(/\r/g, '').split('\n').forEach(function (x) { line('  | ' + x); });
        line('');
      });
    }

    var tds = liveKeys(st.todos).sort(todoOrder);
    if (tds.length) {
      var open = tds.filter(function (k) { return !st.todos[k].done; }).length;
      line('TO-DOS     ' + open + ' open · ' + (tds.length - open) + ' done'); line('');
      tds.forEach(function (k) {
        var t = st.todos[k];
        line((t.done ? '[x] ' : '[ ] ') + pad(k, 5) + pad(TODO_KINDS[t.kind === 'do' ? 'do' : 'add'][1], 17) +
             pad(t.ref ? 'after ' + t.ref : '', 11) + t.text);
        line('           ' + (t.at || '—') + (t.done ? '   done ' + (t.doneAt || '—') : '') +
             (t.became ? '   became step ' + t.became : ''));
      });
      line('');
    }

    Promise.all(jobs.map(sha256)).then(function (hs) {
      var text = L.join('\n').replace(new RegExp(MK + '(\\d+)' + MKE, 'g'), function (_, i) {
        return hs[+i] ? 'sha256     ' + hs[+i] : 'sha256     unavailable (insecure context)';
      });
      var name = DOC + '-evidence-' + now.replace(/[:.]/g, '').slice(0, 15) + 'Z.txt';
      download(name, text + '\n');
      flash(ev, 'evidence saved');
    });
  });

  /* A verdict is stored, not derived on paint, so a change to the rules — a new
     data-pass, or v0.4.0's interpreter-error tier — would never reach a capture
     pasted before it, and a false `pass` would stay green forever. So re-derive
     on every load, superseded runs included: the sidecar owns the output, the
     report owns the rule. Returns true if anything moved, so it gets saved.   */
  function reverdict(ta, r) {
    var moved = false;
    if ((r.text || '').trim()) {
      var v = verdictOf(ta, r.text);
      if (v !== r.verdict) { r.verdict = v; moved = true; }
    }
    (r.runs || []).forEach(function (p) {
      if (!(p.text || '').trim()) return;
      var pv = verdictOf(ta, p.text);
      if (pv !== p.verdict) { p.verdict = pv; moved = true; }
    });
    return moved;
  }

  /* ── hydrate ───────────────────────────────────────────────────────────── */
  function hydrate() {
    Object.keys(st.open).forEach(function (k) {
      var el = k.indexOf('step:') === 0
        ? $('li.step[data-step="' + k.slice(5) + '"] details.sd')
        : $('details.row[data-row="' + k + '"]');
      if (el) el.open = !!st.open[k];
    });
    Object.keys(st.checks).forEach(function (k) {
      var c = $('[data-ck="' + k + '"]'); if (c) c.checked = !!st.checks[k];
    });
    Object.keys(st.vars).forEach(function (k) {
      var i = $('[data-var="' + k + '"]'); if (i) i.value = st.vars[k];
    });
    $$('li.step').forEach(function (li) {
      var s = step(li.dataset.step);
      var dn = $('input.done', li); if (dn) dn.checked = !!s.done;
      var ak = $('input.ack', li); if (ak) ak.checked = !!s.acked;
    });
    var moved = 0;
    Object.keys(st.captures).forEach(function (k) {
      var r = cap(k);
      var ta = $('textarea[data-cap="' + k + '"]'); if (ta) ta.value = r.text || '';
      var ec = $('input[data-ec="' + k + '"]'); if (ec) ec.value = r.exit || '';
      var nt = $('input[data-note="' + k + '"]'); if (nt) nt.value = r.note || '';
      if (ta && reverdict(ta, r)) moved++;
      paintCapture(k);
    });
    if (rederiveEmits()) moved++;
    paintSubs();
    if (moved) save();
    $$('textarea[data-cap]').forEach(function (ta) { paintCapture(ta.dataset.cap); });
    repaintAll();
    // draw.js and anything else that reads state repaints from here
    hydrateHooks.forEach(function (fn) { try { fn(); } catch (e) { console.error('[flowviz] onHydrate', e); } });
  }

  /* ── what the human adds after handover: steps and to-dos ─────────────────
     Mid-run the human finds a step missing, or remembers something the write-up
     should say, or something to do once it is over. They write it down here,
     where it belongs, and it reaches the agent with everything else.
       added: { b3a: { after:'b3', text, cmd, risk:'ro'|'w', at, edited?, folded?, gone? } }
       todos: { t1:  { text, kind:'add'|'do', ref:'b4'|null, at, done, doneAt?, edited?, became?, gone? } }
     A step typed into the page uses the ordinary keys for what it captures
     (captures.b3a, steps.b3a), so it pastes, dims, counts and exports like any
     step; with no data-pass or data-fail, its chip says `captured`. Its id is its
     anchor plus the next free letter — b3a, then b3b — so b4 is never renamed,
     and `flowviz fold` writes it into the source under that same id, where its
     output re-attaches. Nothing is deleted: removing writes `gone`, because the
     load merge is a union and a missing key would come back from the other
     store. All of it is drawn from state, none of it is markup, and the audit
     leaves it out of the agent's caps.                                       */
  var ANCHOR = /^[a-z][0-9]+$/, INSERTED = /^[a-z][0-9]+[a-z]$/;
  var TODO_KINDS = { add: ['Add to the write-up', 'add to write-up'], 'do': ['Do after this run', 'do after'] };
  var lastStep = null, todoKind = 'add', comp = null, quick = null, quickRef = null, toastEl = null, toastT = null;
  function liveKeys(o) { return Object.keys(o || {}).filter(function (k) { return o[k] && !o[k].gone; }); }
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function stepEl(id) { return id ? $('li.step[data-step="' + id + '"]') : null; }
  function isAdded(li) { return !!li && li.classList.contains('added'); }
  function baseOf(id) { var m = /^[a-z][0-9]+/.exec(id || ''); return m ? m[0] : null; }
  function isZero(base) { return /^[a-z]0$/.test(base || ''); }
  function openTodos() { return liveKeys(st.todos).filter(function (k) { return !st.todos[k].done; }); }
  // a playbook a human may add to: lettered steps, outside the Results section
  function anchorsIn(ol) {
    if (ol.closest('section.results')) return [];
    return $$('li.step', ol).filter(function (li) { return ANCHOR.test(li.dataset.step || ''); });
  }
  // a base and what hangs off it — b3, b3a, b3b — as drawn, in order
  function groupOf(base) {
    return $$('li.step').map(function (li) { return li.dataset.step || ''; }).filter(function (id) {
      return id === base || (INSERTED.test(id) && id.slice(0, -1) === base);
    }).sort();
  }
  function lastOf(base) { var g = groupOf(base); return g.length ? g[g.length - 1] : base; }
  // the next letter never used after a base; a tombstone counts, so no id is handed out twice
  function nextAddedId(base) {
    for (var c = 97; c < 123; c++) {
      var id = base + String.fromCharCode(c);
      if (!st.added[id] && !stepEl(id)) return id;
    }
    return null;
  }
  // the anchor a missing step would hang off: one number back in the row, else the row's start, b0
  function prevBase(li) {
    var m = /^([a-z])([0-9]+)$/.exec(li.dataset.step || '');
    if (!m) return null;
    var p = m[1] + (+m[2] - 1);
    return +m[2] > 1 && stepEl(p) ? p : m[1] + '0';
  }
  function nextTodoId() {
    var n = 0;
    Object.keys(st.todos).forEach(function (k) { var m = /^t([0-9]+)$/.exec(k); if (m) n = Math.max(n, +m[1]); });
    return 't' + (n + 1);
  }
  function todoOrder(a, b) {
    var ta = st.todos[a], tb = st.todos[b];
    if (!!ta.done !== !!tb.done) return ta.done ? 1 : -1;
    return (+a.slice(1) || 0) - (+b.slice(1) || 0);
  }
  function toast(t) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'flow-toast';
      toastEl.setAttribute('aria-live', 'polite');
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = t;
    toastEl.classList.add('on');
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.classList.remove('on'); }, 2600);
  }
  function flashEl(n) { n.classList.remove('flashed'); void n.offsetWidth; n.classList.add('flashed'); }

  /* An added step is the template's step, drawn from state: the same checkbox,
     gate, command, paste box and Done, bound by bindStep() and bindCaptureIn()
     exactly as an authored one is. What differs is said once, in violet: a tag
     with when it went in, a line saying the agent will fold it, edit, remove. */
  function addedLi(id) {
    var a = st.added[id], w = a.risk === 'w';
    var li = document.createElement('li');
    li.className = 'step named added';
    li.setAttribute('data-step', id);
    li.setAttribute('data-risk', w ? 'w' : 'ro');
    li.innerHTML =
      '<input type="checkbox" class="done" aria-label="' + id + ' done">' +
      '<details class="sd"><summary><span class="n">' + id + '</span><span class="ds">' + escHtml(a.text) + '</span>' +
        '<span class="addtag" title="typed into the page after handover, ' + escHtml(a.at || '') +
        ': not in the source yet">added ' + escHtml(ptTime(a.at)) + '</span></summary>' +
      '<div class="in">' +
        (w ? '<label class="gate"><input type="checkbox" class="ack"> I accept this writes: ' + escHtml(a.text) + '</label>' : '') +
        (a.cmd ? '<div class="cmd"><button class="copy">copy</button><pre><code>' + escHtml(a.cmd) + '</code></pre></div>'
               : '<p class="byhand">No command: something done or checked by hand.</p>') +
        '<div class="cap"><div class="cl">Paste output <span class="kp">captures["' + id + '"]</span></div>' +
          '<textarea data-cap="' + id + '" placeholder="paste what it printed — it saves as you type"></textarea>' +
          '<div class="ft"><span>exit <input class="ec" data-ec="' + id + '" placeholder="0"></span>' +
            '<span data-cnt="' + id + '">empty</span><span data-at="' + id + '"></span>' +
            '<span class="rn" data-run="' + id + '"></span>' +
            '<button class="rr" data-rr="' + id + '" title="keep this attempt and clear the box">re-run</button></div>' +
          '<input class="nt" data-note="' + id + '" placeholder="note for the agent (optional)">' +
        '</div>' +
        '<div class="addown"><span>Added by you, ' + (isZero(a.after) ? 'before the first step' : 'after <b>' + a.after + '</b>') +
          '. The agent folds it into the source as <b>' + id + '</b>, so what you paste here stays attached.</span>' +
          '<span class="addacts"><button type="button" class="lnk" data-add="edit">edit</button>' +
          '<button type="button" class="lnk" data-add="remove">remove</button></span></div>' +
      '</div></details>' +
      '<span class="ctr"><span class="badge ' + (w ? 'w' : 'ro') + '">' + (w ? 'write' : 'read') + '</span>' +
        (a.cmd ? '<button class="copy">⧉</button>' : '') + '<span class="vd" data-vd="' + id + '">—</span></span>';
    $$('.copy', li).forEach(function (b) {
      b.title = b.closest('.cmd') ? 'Copy this command to the clipboard' : 'Copy this step’s command without opening the step';
      b.setAttribute('aria-label', b.title);
    });
    return li;
  }
  // a drawn step filled from state, as hydrate() fills the authored ones
  function fillStep(li) {
    var id = li.dataset.step, r = st.captures[id] || {}, s = st.steps[id] || {};
    var ta = $('textarea[data-cap]', li); if (ta) ta.value = r.text || '';
    var ec = $('input[data-ec]', li); if (ec) ec.value = r.exit || '';
    var nt = $('input[data-note]', li); if (nt) nt.value = r.note || '';
    var dn = $('input.done', li); if (dn) dn.checked = !!s.done;
    var ak = $('input.ack', li); if (ak) ak.checked = !!s.acked;
    var sd = $('details.sd', li);
    if (sd && sd.open !== !!st.open['step:' + id]) sd.open = !!st.open['step:' + id];
    paintCapture(id);
  }

  /* the playbook: added steps in place, and one more step at the end */
  function renderSteps() {
    $$('li.step.added, li.pb-end').forEach(function (n) { n.remove(); });
    $$('ol.steps').forEach(function (ol) {
      var anchors = anchorsIn(ol);
      if (!anchors.length) return;
      liveKeys(st.added).filter(function (id) {
        var a = st.added[id];
        if (stepEl(id) || !a.after) return false;             // folded: the source draws it now
        var at = stepEl(isZero(a.after) ? a.after.charAt(0) + '1' : a.after);
        return !!at && at.closest('ol.steps') === ol;
      }).sort().forEach(function (id) {
        var a = st.added[id], li = addedLi(id);
        var prev = groupOf(a.after).filter(function (g) { return g < id; }).pop();
        if (prev) { stepEl(prev).after(li); li.setAttribute('data-after', prev); }
        else ol.insertBefore(li, stepEl(a.after.charAt(0) + '1'));
        bindStep(li); bindCaptureIn(li); fillStep(li);
      });
      var base = anchors[anchors.length - 1].dataset.step, g = document.createElement('li');
      g.className = 'pb-end';
      g.innerHTML = '<button type="button" class="pb-add" data-add="insert" data-base="' + base + '">' +
        '+ Add a step to this playbook<i>→ ' + nextAddedId(base) + '</i></button>';
      ol.appendChild(g);
    });
  }

  /* ── the fork: one + at the foot of every step, between the verdict and Done.
     Pressed, the + turns into × and the ways to add fork out of it to the left,
     along the foot row, nearest first: + step after, + to-do. They take the
     verdict's place while open (the row's header still shows it), so they never
     cover the step above or move the page. One quiet control at rest instead of a
     row of buttons and a line on every seam; a new way to add joins the row. ── */
  function renderFork() {
    $$('li.step').forEach(function (li) {
      if (li.closest('section.results')) return;
      var fin = $('.sd>.in>.fin', li), done = fin && $('button.fd', fin);
      if (!done || $('.fork', fin)) return;
      var id = li.dataset.step || '', opts = [];
      if (/^[a-z][0-9]+[a-z]?$/.test(id)) opts.push(['after', '+ step after', 'Add a step after ' + id]);
      opts.push(['todo', '+ to-do', 'Add a to-do tied to ' + id + ' (t)']);
      var f = document.createElement('span');
      f.className = 'fork';
      f.innerHTML = '<button type="button" class="fork-btn" data-add="fork" aria-haspopup="menu" aria-expanded="false" ' +
        'aria-label="Add after ' + escHtml(id) + '" title="Add a step or a to-do after this one"><i></i></button>' +
        '<span class="fork-menu" role="menu" aria-label="Add after ' + escHtml(id) + '">' + opts.map(function (o, i) {
          // nearest the + goes first, so the options cascade outward from it
          return '<button type="button" class="fork-opt" role="menuitem" tabindex="-1" data-add="' + o[0] + '" ' +
            'title="' + escHtml(o[2]) + '" style="--i:' + (opts.length - 1 - i) + '">' + o[1] + '</button>';
        }).join('') + '</span>';
      fin.insertBefore(f, done);
    });
  }
  function setFork(f, open, instant) {
    f.classList.toggle('instant', !!instant);          // from the keyboard: no motion, ever
    f.classList.toggle('open', open);
    f.parentNode.classList.toggle('forked', open);     // the verdict steps aside while it is open
    $('.fork-btn', f).setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function closeForks(except) {
    $$('.fork.open').forEach(function (f) { if (f !== except) setFork(f, false, f.classList.contains('instant')); });
  }
  function toggleFork(f, byKey) {
    var open = !f.classList.contains('open');
    closeForks(f);
    setFork(f, open, byKey);
    if (open && byKey) { var first = $('.fork-opt', f); if (first) first.focus(); }
  }
  // a red or amber chip is often how a missing step is found: offer it there
  function paintMissed() {
    if (KIND === 'drawing' || !ANCHOR) return;
    $$('li.step').forEach(function (li) {
      if (isAdded(li) || li.closest('section.results') || !ANCHOR.test(li.dataset.step || '')) return;
      var inb = $('.sd>.in', li), id = li.dataset.step, v = (st.captures[id] || {}).verdict;
      if (!inb) return;
      var box = $('.missed', inb);
      if (v !== 'fail' && v !== 'error') { if (box) box.hidden = true; return; }
      if (!box) { box = document.createElement('div'); box.className = 'missed'; inb.insertBefore(box, $('.fin', inb)); }
      var prev = prevBase(li), at = isZero(prev) && !groupOf(prev).length ? 'before ' + id : 'after ' + lastOf(prev);
      box.hidden = false;
      box.innerHTML = '<span>' + (v === 'error' ? 'Rejected before it ran. Was a setup step missing before ' + id + '?'
        : 'Was a step missing before ' + id + '?') + '</span><button type="button" class="addbtn" data-add="insert" ' +
        'data-base="' + prev + '">+ add it ' + at + ' → ' + nextAddedId(prev) + '</button>';
    });
  }

  /* ── the composer: one sentence, read or write, an optional command. The
     meters are the audit's own rules shown while typing; nothing is refused,
     because the agent tidies a step when it folds it. ────────────────────── */
  function openComposer(base, o) {
    o = o || {};
    closeComposer();
    if (!base) return;
    var anchor, before = false;
    if (o.edit) anchor = stepEl(o.edit);
    else if (isZero(base) && !groupOf(base).length) { anchor = stepEl(base.charAt(0) + '1'); before = true; }
    else anchor = stepEl(lastOf(base));
    var id = o.edit || nextAddedId(base);
    if (!anchor || !id) return;
    var row = anchor.closest('details.row'); if (row && !row.open) row.open = true;
    var a = o.edit ? st.added[o.edit] : null;
    var li = document.createElement('li');
    li.className = 'composer';
    li.innerHTML =
      '<div class="cmp-h"><span class="car">‸</span>' + (o.edit ? 'Edit added step' :
        (before ? 'New step before ' : 'New step after ') + '<span class="lc">' + anchor.dataset.step + '</span>') +
        ' <span class="cmp-id">' + id + '</span><span class="hint">' + (o.todo ? 'from to-do ' + o.todo + ' · ' : '') +
        (o.edit ? 'its id and what it captured stay' : 'no other step is renamed') + '</span></div>' +
      '<input class="cmp-in" data-k="text" placeholder="One sentence: what this step establishes or changes.">' +
      '<div class="cmp-row"><span class="meter" data-m="words"></span><span class="meter" data-m="sent"></span>' +
        '<span class="seg" role="group" aria-label="blast radius"><button type="button" data-add="risk" data-risk="ro">read</button>' +
        '<button type="button" data-add="risk" data-risk="w" class="w">write</button></span>' +
        '<span class="hint" data-m="risk"></span></div>' +
      '<label class="cmp-lab">Command <span>optional: leave it empty for something done by hand</span></label>' +
      '<textarea class="cmp-in mono" data-k="cmd" rows="1" spellcheck="false" placeholder="the command, on one line"></textarea>' +
      '<div class="cmp-row" data-m="lint"></div>' +
      '<div class="cmp-btns"><button type="button" class="btn-p" data-add="csave">' + (o.edit ? 'Save ' : 'Add ') + id + '</button>' +
        '<button type="button" class="btn-g" data-add="ccancel">Cancel</button>' +
        (o.edit || o.todo ? '' : '<button type="button" class="lnk" data-add="ctodo">or keep it as a to-do</button>') +
        '<span class="hint">↵ add · esc cancel</span></div>';
    if (before) anchor.parentNode.insertBefore(li, anchor); else anchor.after(li);
    if (o.edit) anchor.hidden = true;
    comp = { li: li, base: base, id: id, edit: o.edit || null, todo: o.todo || null,
             risk: a ? a.risk : 'ro', hid: o.edit ? anchor : null };
    $('[data-k="text"]', li).value = a ? a.text : (o.text || '');
    $('[data-k="cmd"]', li).value = a ? (a.cmd || '') : '';
    paintComposer();
    var inp = $('[data-k="text"]', li);
    inp.focus({ preventScroll: true });
    inp.setSelectionRange(inp.value.length, inp.value.length);
    li.scrollIntoView({ block: 'nearest' });
  }
  function closeComposer() {
    if (!comp) return;
    if (comp.hid) comp.hid.hidden = false;
    comp.li.remove();
    comp = null;
  }
  function meter(n, ok, text) {
    n.className = 'meter ' + (ok ? 'ok' : 'warn');
    n.innerHTML = text;
    n.hidden = !text;
  }
  function paintComposer() {
    if (!comp) return;
    var li = comp.li, text = $('[data-k="text"]', li).value, cmd = $('[data-k="cmd"]', li).value;
    var n = words(text), multi = (text.trim().replace(/[.!?]$/, '').match(/[.!?]\s/g) || []).length > 0;
    meter($('[data-m="words"]', li), n <= 20, n ? n + ' / 20 words' : '');
    meter($('[data-m="sent"]', li), !multi, !text.trim() ? '' : multi ? 'two sentences: the agent will split it' : 'one sentence');
    $$('.seg button', li).forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.risk === comp.risk ? 'true' : 'false');
    });
    $('[data-m="risk"]', li).textContent = comp.risk === 'w' ? 'it writes, so it gets a gate like every write step'
      : 'it changes nothing';
    /* the paste-safety rules: a smart quote copied from chat or a doc is the one
       a human brings in most, and a console rejects it */
    var out = [];
    if (cmd.trim()) {
      var bad = /[^\x00-\x7E]/.exec(cmd);
      var lines = cmd.replace(/\r/g, '').split('\n').filter(function (l) { return l.trim(); }).length;
      out.push(bad ? '<span class="meter warn">non-ASCII ' + escHtml(bad[0]) + ' at ' + (bad.index + 1) +
        ': a console rejects it <button type="button" data-add="ascii">fix</button></span>'
        : '<span class="meter ok">ASCII</span>');
      out.push(lines > 1 ? '<span class="meter warn">' + lines + ' lines: keep it to one</span>' : '<span class="meter ok">one line</span>');
      if (/^\s*(#|\/\/|<#|rem\b)/i.test(cmd)) out.push('<span class="meter warn">starts with a comment: its first character gets dropped</span>');
    }
    $('[data-m="lint"]', li).innerHTML = out.join('');
    $('[data-add="csave"]', li).disabled = !text.trim();
  }
  function asciiFix(s) {
    return s.replace(/[‘’‚′]/g, "'").replace(/[“”„″]/g, '"')
      .replace(/[–—−]/g, '-').replace(/…/g, '...').replace(/[   ]/g, ' ');
  }
  function saveComposer() {
    if (!comp) return;
    var c = comp, li = c.li, id = c.id;
    var text = $('[data-k="text"]', li).value.trim().replace(/\s+/g, ' ');
    var cmd = $('[data-k="cmd"]', li).value.replace(/\r/g, '').trim();
    if (!text) return;
    if (c.edit) {
      var a = st.added[id];
      a.text = text; a.cmd = cmd; a.risk = c.risk; a.edited = new Date().toISOString();
    } else {
      st.added[id] = { after: c.base, text: text, cmd: cmd, risk: c.risk, at: new Date().toISOString() };
      st.open['step:' + id] = true;
    }
    if (c.todo && st.todos[c.todo]) {
      var t = st.todos[c.todo];
      t.became = id; t.done = true; t.doneAt = new Date().toISOString();
    }
    closeComposer();
    save(); renderAdditions();
    var nli = stepEl(id);
    if (nli) {
      flashEl(nli);
      var ta = !c.edit && $('textarea[data-cap]', nli);
      if (ta) ta.focus({ preventScroll: true });
    }
    toast((c.edit ? 'Saved ' : 'Added ') + id + (c.todo ? ' from ' + c.todo : '') + ': saved with the page, not yet in the source');
  }

  /* ── to-dos: one section at the end, one line at rest; two kinds, in the
     words used mid-run: something the write-up is missing (it can become a
     step), and something to do once the run is over (it can become Next). ── */
  function addTodo(text, kind, ref) {
    text = (text || '').trim().replace(/\s+/g, ' ');
    if (!text) return null;
    var id = nextTodoId();
    st.todos[id] = { text: text, kind: kind === 'do' ? 'do' : 'add', ref: ref || null,
                     at: new Date().toISOString(), done: false };
    save(); renderTodos(); renderMarkers(); renderPill();
    return id;
  }
  function setKind(k) { todoKind = k === 'do' ? 'do' : 'add'; st.ui.todoKind = todoKind; }
  function todoItem(id) {
    var t = st.todos[id];
    var anc = t.ref ? '<button type="button" class="todo-anc" data-add="go" data-go="' + t.ref + '" title="go to ' + t.ref + '">after ' + t.ref + '</button>' : '';
    var became = t.became ? '<button type="button" class="todo-became" data-add="go" data-go="' + t.became +
      '" title="this to-do became step ' + t.became + '">→ ' + t.became + '</button>' : '';
    var promote = !t.done && t.kind === 'add' && t.ref ? '<button type="button" class="lnk" data-add="promote">make it a step</button>' : '';
    var when = t.done ? 'done ' + ptTime(t.doneAt) : ptTime(t.at);
    return '<li class="todo-item' + (t.done ? ' done' : '') + '" data-tid="' + id + '">' +
      '<input type="checkbox" class="todo-ck"' + (t.done ? ' checked' : '') + ' aria-label="' + id + ' done">' +
      '<span class="todo-id">' + id + '</span><span class="todo-tx">' + escHtml(t.text) + '</span>' +
      '<span class="todo-meta">' + anc + became + '<span title="' + escHtml((t.done ? t.doneAt : t.at) || '') + '">' + escHtml(when) + '</span>' +
      '<span class="todo-acts">' + promote + '<button type="button" class="lnk" data-add="tedit">edit</button>' +
      '<button type="button" class="lnk" data-add="tdel">remove</button></span></span></li>';
  }
  function stepOptions(sel) {
    return '<option value="">no step</option>' + $$('li.step').filter(function (li) {
      return !li.closest('section.results');
    }).map(function (li) {
      var id = li.dataset.step;
      return '<option value="' + escHtml(id) + '"' + (id === sel ? ' selected' : '') + '>after ' + escHtml(id) + '</option>';
    }).join('');
  }
  function renderTodos() {
    var sec = $('section.todo');
    if (!sec) {
      sec = document.createElement('section');
      sec.className = 'todo';
      sec.innerHTML = '<details><summary><span class="todo-k">To do</span><span class="todo-cnt"></span>' +
        '<span class="todo-peek"></span><button type="button" class="todo-add" data-add="quick">+ to-do</button></summary>' +
        '<div class="todo-body"></div></details>';
      var foot = $('.foot');
      if (foot) foot.parentNode.insertBefore(sec, foot); else document.body.appendChild(sec);
      var d = $('details', sec);
      d.addEventListener('toggle', function () {
        if (!!st.open['todo:list'] !== d.open) { st.open['todo:list'] = d.open; save(); }
      });
    }
    var dd = $('details', sec);
    if (dd.open !== !!st.open['todo:list']) dd.open = !!st.open['todo:list'];
    var ids = liveKeys(st.todos), open = openTodos().sort(todoOrder);
    $('.todo-cnt', sec).innerHTML = ids.length ? '<b>' + open.length + ' open</b> · ' + (ids.length - open.length) + ' done'
      : 'nothing yet · press <b>t</b> anywhere';
    $('.todo-peek', sec).textContent = open.length ? open[0] + '  ' + st.todos[open[0]].text : '';
    var h = '';
    ['add', 'do'].forEach(function (k) {
      var list = ids.filter(function (id) { return (st.todos[id].kind === 'do' ? 'do' : 'add') === k; }).sort(todoOrder);
      if (!list.length) return;
      var n = list.filter(function (id) { return !st.todos[id].done; }).length;
      h += '<div class="todo-grp">' + TODO_KINDS[k][0] + ' <em>' + n + '</em></div><ul class="todo-list">' +
        list.map(todoItem).join('') + '</ul>';
    });
    if (!ids.length) h += '<p class="todo-empty">Something this write-up is missing, or something to do once the run is ' +
      'over. Press <b>t</b> anywhere, or <b>+ to-do</b> in the pill, and it lands here without moving the page.</p>';
    h += '<div class="todo-new"><input class="cmp-in" data-k="ttext" placeholder="Something to add to this write-up, or to do after the run">' +
      '<span class="seg" role="group" aria-label="kind"><button type="button" data-add="tkind" data-kind="add">add to write-up</button>' +
      '<button type="button" data-add="tkind" data-kind="do">do after</button></span>' +
      '<select data-k="tref" aria-label="tie it to a step">' + stepOptions(lastStep) + '</select>' +
      '<button type="button" class="btn-p" data-add="tadd">Add</button></div>';
    $('.todo-body', sec).innerHTML = h;
    paintKind();
  }
  function paintKind() {
    $$('[data-add="tkind"], [data-add="qkind"]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.kind === todoKind ? 'true' : 'false');
    });
  }
  // at rest the rows are shut: say on the row, and on the step, where the human added something
  function renderMarkers() {
    $$('.todo-mark, .row-mark').forEach(function (n) { n.remove(); });
    var byRef = {};
    openTodos().forEach(function (id) {
      var t = st.todos[id];
      if (t.ref) (byRef[t.ref] = byRef[t.ref] || []).push(id);
    });
    Object.keys(byRef).forEach(function (ref) {
      var ds = $('.sd>summary .ds', stepEl(ref) || document.createElement('i'));
      if (!ds) return;
      var c = document.createElement('span');
      c.className = 'todo-mark';
      c.setAttribute('data-add', 'gotodo');
      c.setAttribute('data-tid', byRef[ref][0]);
      c.textContent = byRef[ref].length + ' to-do';
      c.title = byRef[ref].map(function (id) { return id + ': ' + st.todos[id].text; }).join('\n');
      ds.after(c);
    });
    $$('details.row').forEach(function (row) {
      var ids = $$('li.step', row).map(function (li) { return li.dataset.step; });
      var nAdd = $$('li.step.added', row).length, nTodo = 0;
      openTodos().forEach(function (id) { if (ids.indexOf(st.todos[id].ref) >= 0) nTodo++; });
      if (!nAdd && !nTodo) return;
      var s = $('summary', row), m = document.createElement('span');
      m.className = 'row-mark';
      m.textContent = [nAdd ? '+' + nAdd + ' added' : '', nTodo ? nTodo + ' to-do' : ''].filter(Boolean).join(' · ');
      m.title = 'typed into the page after handover: the agent reads these back';
      s.insertBefore(m, $('.rt', s));
    });
  }
  function renderPill() {
    var txt = $('#flowPillTxt');
    if (!txt) return;
    var b = $('#flowTodo');
    if (!b) {
      b = document.createElement('button');
      b.id = 'flowTodo'; b.type = 'button';
      b.setAttribute('data-add', 'quick');
      b.title = 'Add a to-do without losing your place (t)';
      var sep = document.createElement('span');
      sep.className = 'sep';
      txt.parentNode.insertBefore(sep, txt.nextSibling);
      txt.parentNode.insertBefore(b, sep.nextSibling);
    }
    var n = openTodos().length;
    b.innerHTML = '+ to-do' + (n ? '<span class="todo-n">' + n + '</span>' : '');
  }

  /* ── quick capture: a to-do from anywhere, tied to the step you were on,
     without the page moving ───────────────────────────────────────────────── */
  function openQuick(ref) {
    if (!quick) {
      quick = document.createElement('div');
      quick.className = 'todo-quick';
      quick.setAttribute('role', 'dialog');
      quick.setAttribute('aria-label', 'New to-do');
      document.body.appendChild(quick);
    }
    quickRef = ref !== undefined ? ref : lastStep;
    var n = openTodos().length;
    quick.innerHTML = '<div class="tq-h"><span class="todo-k">New to-do · <span class="lc">' + nextTodoId() + '</span></span>' +
      (quickRef ? '<span class="tq-anc" title="tied to the step you were on">after ' + escHtml(quickRef) +
        '<button type="button" data-add="qnoref" title="not tied to a step">✕</button></span>' : '') +
      '<button type="button" class="lnk" data-add="qclose">esc</button></div>' +
      '<input class="cmp-in" data-k="qtext" placeholder="Add to the write-up, or do after the run">' +
      '<div class="tq-f"><span class="seg" role="group" aria-label="kind">' +
        '<button type="button" data-add="qkind" data-kind="add">add to write-up</button>' +
        '<button type="button" data-add="qkind" data-kind="do">do after</button></span>' +
        '<span class="hint">↵ save · <a href="#" data-add="qall">' + n + ' open, see all</a></span></div>';
    paintKind();
    quick.hidden = false;
    $('[data-k="qtext"]', quick).focus();
  }
  function closeQuick() { if (quick) quick.hidden = true; }
  function saveQuick() {
    var inp = quick && $('[data-k="qtext"]', quick);
    if (!inp || !inp.value.trim()) return;
    var id = addTodo(inp.value, todoKind, quickRef);
    closeQuick();
    var b = $('#flowTodo'); if (b) flashEl(b);
    toast(id + ' saved' + (quickRef ? ' · after ' + quickRef : '') + ' · it waits in To do at the bottom');
  }
  function goStep(id) {
    var li = stepEl(id);
    if (!li) return;
    var row = li.closest('details.row'); if (row && !row.open) row.open = true;
    li.scrollIntoView({ block: 'center', behavior: 'smooth' });
    flashEl(li);
  }
  function goTodo(tid) {
    var sec = $('section.todo'); if (!sec) return;
    var d = $('details', sec); if (d && !d.open) d.open = true;
    var li = (tid && $('li.todo-item[data-tid="' + tid + '"]', sec)) || sec;
    li.scrollIntoView({ block: 'center', behavior: 'smooth' });
    flashEl(li);
  }

  function renderAdditions() {
    if (KIND === 'drawing') return;
    if (st.ui && st.ui.todoKind) todoKind = st.ui.todoKind === 'do' ? 'do' : 'add';
    renderSteps(); renderFork(); renderTodos(); renderMarkers(); renderPill();
    repaintAll();
  }

  /* ── events: delegated, because everything here is drawn after load and
     drawn again whenever its structure changes ────────────────────────────── */
  if (KIND !== 'drawing') {
    document.addEventListener('input', function (e) {
      if (comp && comp.li.contains(e.target)) paintComposer();
    });
    document.addEventListener('change', function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      var ti = t.closest('li.todo-item');
      if (ti && t.matches('.todo-ck')) {
        var td = st.todos[ti.dataset.tid];
        td.done = t.checked;
        td.doneAt = t.checked ? new Date().toISOString() : null;
        save(); renderTodos(); renderMarkers(); renderPill();
      }
      if (t.matches('select[data-k="tref"]') && t.value) lastStep = t.value;
    });
    // the step you were last in is what a new to-do is tied to; toggle does not bubble
    document.addEventListener('toggle', function (e) {
      var d = e.target;
      if (d.matches && d.matches('details.sd') && d.open) {
        var li = d.closest('li.step');
        if (li && !li.closest('section.results')) lastStep = li.dataset.step;
      }
    }, true);
    document.addEventListener('focusin', function (e) {
      var li = e.target.closest && e.target.closest('li.step');
      if (li && !li.closest('section.results')) lastStep = li.dataset.step;
      if (e.target.closest && !e.target.closest('.fork.open')) closeForks();
    });
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      if (quick && !quick.hidden && !quick.contains(t) && !t.closest('#flowTodo, [data-add="todo"], [data-add="quick"]')) closeQuick();
      if (!t.closest('.fork-btn')) closeForks();           // a choice, or a click anywhere else, folds it back
      var b = t.closest('[data-add]');
      if (!b) return;
      var act = b.getAttribute('data-add'), li = b.closest('li.step'), ti = b.closest('li.todo-item');
      if (act === 'fork') { e.preventDefault(); toggleFork(b.closest('.fork'), e.detail === 0); }
      else if (act === 'insert') { e.preventDefault(); openComposer(b.dataset.base); }
      else if (act === 'after' && li) openComposer(baseOf(li.dataset.step));
      else if (act === 'todo' && li) openQuick(li.dataset.step);
      else if (act === 'risk' && comp) { comp.risk = b.dataset.risk; paintComposer(); }
      else if (act === 'ascii' && comp) { var ci = $('[data-k="cmd"]', comp.li); ci.value = asciiFix(ci.value); paintComposer(); }
      else if (act === 'csave') saveComposer();
      else if (act === 'ccancel') closeComposer();
      else if (act === 'ctodo' && comp) {
        var tx = $('[data-k="text"]', comp.li).value, ref = lastOf(comp.base);
        closeComposer();
        var nid = addTodo(tx, 'add', isZero(ref) ? null : ref);
        if (nid) toast(nid + ' saved as a to-do · make it a step whenever you like');
      }
      else if (act === 'edit' && li && st.added[li.dataset.step]) openComposer(st.added[li.dataset.step].after, { edit: li.dataset.step });
      else if (act === 'remove' && li && st.added[li.dataset.step]) {
        if (!b.classList.contains('sure')) {
          b.classList.add('sure'); b.textContent = 'remove ' + li.dataset.step + '?';
          setTimeout(function () { b.classList.remove('sure'); b.textContent = 'remove'; }, 3000);
          return;
        }
        var gone = li.dataset.step;
        st.added[gone].gone = new Date().toISOString();       // a tombstone, never a delete
        save(); renderAdditions();
        toast(gone + ' removed · its id is never reused, and what it captured is kept');
      }
      else if (act === 'go') { e.preventDefault(); goStep(b.dataset.go); }
      else if (act === 'gotodo') { e.preventDefault(); e.stopPropagation(); goTodo(b.dataset.tid); }
      else if (act === 'quick') { e.preventDefault(); if (quick && !quick.hidden) closeQuick(); else openQuick(); }
      else if (act === 'qclose') closeQuick();
      else if (act === 'qnoref') {
        quickRef = null;
        var qa = b.closest('.tq-anc'); if (qa) qa.remove();
        $('[data-k="qtext"]', quick).focus();
      }
      else if (act === 'qkind' || act === 'tkind') { setKind(b.dataset.kind); paintKind(); }
      else if (act === 'qall') { e.preventDefault(); closeQuick(); goTodo(''); }
      else if (act === 'tadd') {
        var sec = $('section.todo'), inp = $('[data-k="ttext"]', sec), sel = $('[data-k="tref"]', sec);
        var id2 = addTodo(inp.value, todoKind, sel.value || null);
        if (id2) { var again = $('[data-k="ttext"]', sec); if (again) again.focus(); toast(id2 + ' saved'); }
      }
      else if (act === 'promote' && ti) {
        var td = st.todos[ti.dataset.tid];
        openComposer(baseOf(td.ref), { todo: ti.dataset.tid, text: td.text });
      }
      else if (act === 'tedit' && ti) {
        var tx2 = $('.todo-tx', ti);
        tx2.innerHTML = '<input class="cmp-in" data-k="tedit" value="' + escHtml(st.todos[ti.dataset.tid].text) + '">';
        var ei = $('input', tx2); ei.focus(); ei.select();
      }
      else if (act === 'tdel' && ti) {
        if (!b.classList.contains('sure')) {
          b.classList.add('sure'); b.textContent = 'remove ' + ti.dataset.tid + '?';
          setTimeout(function () { b.classList.remove('sure'); b.textContent = 'remove'; }, 3000);
          return;
        }
        st.todos[ti.dataset.tid].gone = new Date().toISOString();
        save(); renderTodos(); renderMarkers(); renderPill();
      }
    });
    document.addEventListener('keydown', function (e) {
      var t = e.target || {};
      if (e.key === 'Escape') {
        var fk = $('.fork.open');
        if (fk) { closeForks(); $('.fork-btn', fk).focus(); e.preventDefault(); }
        else if (quick && !quick.hidden) { closeQuick(); e.preventDefault(); }
        else if (comp && comp.li.contains(t)) { closeComposer(); e.preventDefault(); }
        return;
      }
      // arrows move between the options a fork holds open
      if (/^Arrow(Up|Down|Left|Right)$/.test(e.key) && t.classList && t.classList.contains('fork-opt')) {
        var all = $$('.fork-opt', t.closest('.fork-menu')), k = all.indexOf(t);
        var step = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : -1;  // in reading order, wrapping
        all[(k + step + all.length) % all.length].focus();
        e.preventDefault();
        return;
      }
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        if (comp && comp.li.contains(t)) { e.preventDefault(); saveComposer(); return; }
        if (quick && quick.contains(t) && t.matches('[data-k="qtext"]')) { e.preventDefault(); saveQuick(); return; }
        if (t.matches && t.matches('[data-k="ttext"]')) { e.preventDefault(); var ad = $('[data-add="tadd"]'); if (ad) ad.click(); return; }
        if (t.matches && t.matches('[data-k="tedit"]')) {
          e.preventDefault();
          var tl = t.closest('li.todo-item'), v = t.value.trim();
          if (tl && v) { st.todos[tl.dataset.tid].text = v; st.todos[tl.dataset.tid].edited = new Date().toISOString(); save(); }
          renderTodos(); renderMarkers();
          return;
        }
      }
      // t, anywhere you are not typing: a to-do tied to the step you were on
      if (e.key === 't' && !e.metaKey && !e.ctrlKey && !e.altKey &&
          !(t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || ''))) {
        e.preventDefault();
        openQuick();
      }
    });
  }

  /* ── print ────────────────────────────────────────────────────────────────
     Force light, open every <details>, and grow the textareas so a capture is
     not clipped to three visible lines on paper. All three are restored after,
     so the print CSS carries pagination only — no palette of its own.       */
  var printed = null, printedTheme = null;
  window.addEventListener('beforeprint', function () {
    printedTheme = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', 'light');
    printed = $$('details').map(function (d) { return [d, d.open]; });
    printed.forEach(function (p) { p[0].open = true; });
    $$('textarea').forEach(function (t) {
      t.dataset.h = t.style.height;
      t.style.height = 'auto';
      t.style.height = (t.scrollHeight + 4) + 'px';
    });
    document.body.classList.add('printing');
  });
  window.addEventListener('afterprint', function () {
    if (printedTheme) document.documentElement.setAttribute('data-theme', printedTheme);
    else document.documentElement.removeAttribute('data-theme');
    printedTheme = null;
    if (printed) printed.forEach(function (p) { p[0].open = p[1]; });
    printed = null;
    $$('textarea').forEach(function (t) { t.style.height = t.dataset.h || ''; });
    document.body.classList.remove('printing');
  });

  /* ── pill wiring ───────────────────────────────────────────────────────── */
  pill = $('#flowPill'); pillTxt = $('#flowPillTxt');
  var tb = $('#flowTheme');
  if (tb) tb.addEventListener('click', function () {
    var order = ['auto', 'light', 'dark'];
    forcedTheme = null;                 // a click is a real choice: release ?theme=
    st.ui.theme = order[(order.indexOf(st.ui.theme || 'auto') + 1) % 3];
    applyTheme(); save();
  });
  renderAdditions();
  hydrate();
  live = true;          // from here on, a verdict changing means the human did it
  setPill(served ? 'disk' : '', served ? 'disk-backed' : 'local only');
  if (dl && served) dl.style.display = 'none';

  /* ── audit: enforce the SPEC caps. open with ?audit=1 ──────────────────────
     Built on window `load`, not inline: draw.js runs after this script, mounts
     its drawings and pushes its rows onto FLOWVIZ.auditHooks — the panel has to
     wait for both, or it measures a page without its drawings. Report rows only
     on a report; screens at rest on everything (3 for a report, 2 for a drawing
     page). Every row carries data-k and data-ok, which is what
     `flowviz audit --browser` reads back out of the dumped DOM.              */
  function buildAudit() {
    var CAP = { title: 70, verdict: 50, sowhat: 30, vitals: 5, next: 4, nextWords: 14,
                rows: 6, rowSummary: 14, openAtLoad: 1, stepWords: 20, atRest: 350,
                screens: KIND === 'drawing' ? 2 : 3 };
    var rowsEls = $$('details.row'), secs = $$('h2.sec');
    var wasOpen = rowsEls.map(function (d) { return d.open; });
    rowsEls.forEach(function (d) { d.open = false; });
    /* a Results section has its own budget (1.5 screens), so the report's
       three-screen budget is measured without it */
    var resEl = $('section.results');
    var resH = resEl ? resEl.getBoundingClientRect().height : 0;
    /* what the human added is theirs, not the agent's budget: the to-do section,
       the counts on the rows and the steps typed into the page are measured out */
    var tdEl = $('section.todo'), tdD = tdEl && $('details', tdEl), tdOpen = !!(tdD && tdD.open);
    if (tdD) tdD.open = false;
    var tdH = tdEl ? tdEl.getBoundingClientRect().height + (parseFloat(getComputedStyle(tdEl).marginTop) || 0) : 0;
    var screens = (document.documentElement.scrollHeight - resH - tdH) / window.innerHeight;
    if (tdD) tdD.open = tdOpen;
    var restWords = words(($('.card') ? $('.card').innerText : '') + ' ' +
      secs.map(function (h) { return h.textContent; }).join(' ') + ' ' +
      rowsEls.map(function (d) {
        var s = $('summary', d);
        return s ? Array.prototype.map.call(s.childNodes, function (n) {
          return n.classList && n.classList.contains('row-mark') ? '' : (n.textContent || '');
        }).join(' ') : '';
      }).join(' '));
    rowsEls.forEach(function (d, i) { d.open = wasOpen[i]; });

    var rows = [];
    function chk(label, actual, cap, unit) {
      rows.push([label, actual + (unit || ''), '≤ ' + cap + (unit || ''), actual <= cap]);
    }
    function must(label, actual, want) {
      rows.push([label, actual, String(want), actual === want]);
    }
    if (KIND !== 'drawing') {
      var h1 = $('.card h1');
      chk('title chars', h1 ? h1.innerText.trim().length : 0, CAP.title);
      chk('verdict words', words($('[data-slot="verdict"]') && $('[data-slot="verdict"]').innerText), CAP.verdict);
      chk('so-what words', words($('[data-slot="sowhat"]') && $('[data-slot="sowhat"]').innerText), CAP.sowhat);
      chk('vital tiles', $$('.vitals>div').length, CAP.vitals);
      chk('next items', $$('.next li').length, CAP.next);
      chk('longest next item', Math.max.apply(null, [0].concat($$('.next li').map(function (l) { return words(l.innerText); }))), CAP.nextWords);
      chk('rows', rowsEls.length, CAP.rows);
      chk('longest row summary', Math.max.apply(null, [0].concat(rowsEls.map(function (d) { var c = $('.cl', d); return words(c ? c.innerText : ''); }))), CAP.rowSummary);
      chk('open at load', wasOpen.filter(Boolean).length, CAP.openAtLoad);
      chk('section headers', secs.length, 3);
      chk('longest section header', Math.max.apply(null, [0].concat(secs.map(function (h) { return words(h.textContent); }))), 4);
      must('rows before the first header', rowsEls.filter(function (d) {
        return !secs.length || !!(secs[0].compareDocumentPosition(d) & Node.DOCUMENT_POSITION_PRECEDING);
      }).length, 0);
      must('rows with no kind', rowsEls.filter(function (d) { return !ROW_KIND[d.dataset.kind]; }).length, 0);
      must('diagrams in spine', $$('.spine .dia, .spine .mermaid, .spine .fv-drawing').length, 1);
      /* textContent, not innerText: the rows were just closed to measure the page
         at rest, and innerText is '' for anything inside a closed <details> — so
         every step sentence silently measured 0 and the cap always read ok. */
      chk('longest step sentence', Math.max.apply(null, [0].concat($$('li.step:not(.added) .ds').map(function (s) { return words(s.textContent); }))), CAP.stepWords);
      var multi = $$('li.step:not(.added) .ds').filter(function (s) {
        return (s.textContent.trim().replace(/[.!?]$/, '').match(/[.!?]\s/g) || []).length > 0;
      }).length;
      must('multi-sentence steps', multi, 0);
      must('steps with no risk tag', $$('li.step:not(.added):not([data-risk])').length, 0);
      must('write steps with no gate', $$('li.step:not(.added)[data-risk="w"]').filter(function (li) {
        return !$('input.ack', li);
      }).length, 0);
      must('untagged next items', $$('.next li').filter(function (l) { return !$('.badge', l); }).length, 0);
      chk('words at rest', restWords, CAP.atRest);
    }
    rows.push(['screens at rest', screens.toFixed(1), '≤ ' + CAP.screens, screens <= CAP.screens]);
    if (resEl) {
      var rs = resH / window.innerHeight;
      rows.push(['results screens', rs.toFixed(1), '≤ 1.5', rs <= 1.5]);
    }

    // drawings (and anything else that registered) add their own rows
    function add(label, actual, capText, ok) {
      rows.push([String(label), actual, String(capText), !!ok]);
    }
    (window.FLOWVIZ.auditHooks || []).forEach(function (fn) {
      try { fn(add); } catch (e) {
        rows.push(['audit hook failed', String(e && e.message || e), 'no error', false]);
      }
    });

    function esc(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
    var bad = rows.filter(function (r) { return !r[3]; }).length;
    var d = document.createElement('div');
    d.className = 'audit';
    d.id = 'flowAudit';
    d.setAttribute('data-violations', String(bad));
    d.innerHTML = '<button class="x">✕</button><h4>Spec audit — ' +
      (bad ? bad + ' violation' + (bad === 1 ? '' : 's') : 'clean') + '</h4><table><tbody>' +
      rows.map(function (r) {
        return '<tr data-k="' + esc(r[0]) + '" data-ok="' + (r[3] ? '1' : '0') + '"><td>' + esc(r[0]) +
          '</td><td style="text-align:right"><code>' + esc(r[1]) +
          '</code></td><td>' + esc(r[2]) + '</td><td class="' + (r[3] ? 'p' : 'f') + '">' +
          (r[3] ? 'ok' : 'over') + '</td></tr>';
      }).join('') + '</tbody></table>';
    document.body.appendChild(d);
    $('.x', d).addEventListener('click', function () { d.remove(); });
  }
  if (/[?&]audit=1/.test(location.search)) {
    if (document.readyState === 'complete') setTimeout(buildAudit, 0);
    else window.addEventListener('load', buildAudit);
  }
})();
