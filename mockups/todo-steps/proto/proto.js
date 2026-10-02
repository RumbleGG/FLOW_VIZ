/* ===========================================================================
   FLOW_VIZ — proto.js · PROTOTYPE LAYER for to-dos and added steps
   Not part of template/. build.sh injects it after flow.js and draw.js, and it
   reaches the page only through window.FLOWVIZ (state, save, onHydrate,
   ptTime), the same contract draw.js uses.

   What it adds to the state (schema 5 in the proposal):
     added: { b3a: { after:'b3', text, cmd, risk:'ro'|'w', at, edited?, gone? } }
     todos: { t1:  { text, kind:'add'|'do', ref:'b4'|null, at, done, doneAt?, became?, gone? } }
   An added step's output, tick and note use the ordinary keys (captures.b3a,
   steps.b3a), so evidence, progress and dimming treat it like any other step.

   Ids are join keys, so an added step takes its anchor's id plus the next free
   letter (b3a, b3b) and b4 is never renumbered; a to-do takes the next t<n>.
   Nothing is deleted: removing writes a tombstone (gone), because the load
   merge is a union and a missing key would come back from the other store.
   =========================================================================== */
(function () {
  'use strict';
  var FV = window.FLOWVIZ;
  /* 3.1.0 shipped this natively (state schema 5): the prototype stands down, and only proto.css stays,
     for the static mockups in TODO-STEPS */
  if (!FV || FV.kind === 'drawing' || (FV.state && FV.state.schema >= 5)) return;
  var st = FV.state, DOC = FV.doc, LSKEY = 'flowviz:' + DOC;
  var served = /^https?:$/.test(location.protocol);
  var POSE = (location.search.match(/[?&]pose=([a-z]+)/) || [])[1] || '';
  var SRC = (location.pathname.split('/').pop() || 'REPORT.html').replace(/\.html$/, '.src.html');

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function iso() { return new Date().toISOString(); }
  function words(s) { return (s || '').trim().split(/\s+/).filter(Boolean).length; }
  function pt(t, s) { return t ? FV.ptTime(t, s) : ''; }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function live(o) { return Object.keys(o || {}).filter(function (k) { return o[k] && !o[k].gone; }); }
  function save() { FV.save(); }

  /* ── recover our keys ────────────────────────────────────────────────────
     flow.js's merge() copies only the keys it knows, so `added` and `todos`
     reach localStorage and the sidecar but are dropped again on load, and an
     older build's next save would erase them from disk. The prototype takes
     them back itself; the real build fixes merge() and makes serve keep the
     keys a PUT lacks (the proposal, row d). */
  var localAt = st.savedAt || '';
  function adopt(d) {
    if (!d || typeof d !== 'object') return false;
    var any = false;
    ['added', 'todos'].forEach(function (k) {
      if (d[k] && typeof d[k] === 'object') { st[k] = Object.assign(st[k] || {}, d[k]); any = true; }
    });
    return any;
  }
  try { adopt(JSON.parse(localStorage.getItem(LSKEY) || 'null')); } catch (e) {}
  if (!st.added || typeof st.added !== 'object') st.added = {};
  if (!st.todos || typeof st.todos !== 'object') st.todos = {};
  if (!st.open || typeof st.open !== 'object') st.open = {};
  if (served) {
    fetch('./' + DOC + '.flow.json', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (d && (!localAt || (d.savedAt || '') > localAt) && adopt(d)) renderAll();
      })
      .catch(function () {});
  }

  /* ── ids ───────────────────────────────────────────────────────────────── */
  var BASE = /^([a-z])([0-9]+)$/;
  function isAdded(li) { return li.classList.contains('fv-added'); }
  function authoredIn(ol) {
    return $$('li.step', ol).filter(function (li) { return !isAdded(li) && BASE.test(li.dataset.step || ''); });
  }
  // the added steps hanging off one authored step, in letter order
  function groupOf(base) {
    return live(st.added).filter(function (id) { return st.added[id].after === base; }).sort();
  }
  // a new step after `base` is the base plus the next letter never used; a
  // tombstone counts as used, so a removed b3a is never handed out twice
  function nextAddedId(base) {
    for (var c = 97; c < 123; c++) {
      var id = base + String.fromCharCode(c);
      if (!st.added[id] && !$('li.step[data-step="' + id + '"]')) return id;
    }
    return null;
  }
  function baseOf(id) { var m = /^([a-z][0-9]+)/.exec(id || ''); return m ? m[1] : null; }
  function lastOf(base) { var g = groupOf(base); return g.length ? g[g.length - 1] : base; }
  function isZero(base) { return /^[a-z]0$/.test(base); }
  function nextTodoId() {
    var n = 0;
    Object.keys(st.todos).forEach(function (k) { var m = /^t([0-9]+)$/.exec(k); if (m) n = Math.max(n, +m[1]); });
    return 't' + (n + 1);
  }

  /* ── verdict for a step with no rule ─────────────────────────────────────
     An added step has no data-pass or data-fail until the agent folds it, so
     it reads `captured`, never `no match`: there is no pass condition to blame.
     The interpreter-error tier still applies — a rejected command is evidence
     about the step, whoever wrote it. Copied from flow.js for the prototype;
     the real build calls flow.js's own verdictOf(). */
  var CMD_ERR = [/\bParserError\b/, /\bUnexpected token\b/i, /\bMissing (?:closing|expression|argument|statement)\b/i,
    /\bstring (?:is )?missing the terminator\b/i, /\bpositional parameter cannot be found\b/i,
    /\bis not recognized as the name of\b/i, /\bCommandNotFoundException\b/, /\bcommand not found\b/i,
    /\bsyntax error near unexpected token\b/i, /\bunexpected EOF while looking for matching\b/i,
    /\b(?:SyntaxError|IndentationError|TabError):/];
  function verdictOf(v) {
    if (!v.trim()) return null;
    return CMD_ERR.some(function (re) { return re.test(v); }) ? 'error' : 'saved';
  }
  var VD = { pass: 'pass', fail: 'fail', error: 'error', saved: 'captured' };
  var GLYPH = { pass: '✓', fail: '✕', error: '⚠', saved: '●' };
  function cap(id) {
    var r = (st.captures[id] = st.captures[id] || {});
    ['text', 'exit', 'note'].forEach(function (k) { if (!(k in r)) r[k] = ''; });
    if (!('verdict' in r)) r.verdict = null;
    if (!('at' in r)) r.at = null;
    if (!Array.isArray(r.runs)) r.runs = [];
    return r;
  }
  function stepRec(id) { return (st.steps[id] = st.steps[id] || { done: false, acked: false }); }

  /* ── an added step, drawn ────────────────────────────────────────────────
     The same markup as an authored step, so flow.js's own repaint (done,
     acked, dim, the Done box) and its Save evidence reach it unchanged. */
  function addedLi(id) {
    var a = st.added[id], w = a.risk === 'w';
    var li = el('li', 'step named fv-added');
    li.setAttribute('data-step', id);
    li.setAttribute('data-risk', w ? 'w' : 'ro');
    if (!isZero(a.after)) li.setAttribute('data-after', a.after);
    li.innerHTML =
      '<input type="checkbox" class="done" aria-label="done">' +
      '<details class="sd"><summary><span class="n">' + id + '</span><span class="ds">' + esc(a.text) + '</span>' +
        '<span class="fv-tag" title="typed into the page at ' + esc(a.at) + ', after handover: not in the source yet">added ' +
        esc(pt(a.at)) + '</span></summary>' +
      '<div class="in">' +
        (w ? '<label class="gate"><input type="checkbox" class="ack"> I accept this writes: ' + esc(a.text) + '</label>' : '') +
        (a.cmd ? '<div class="cmd"><button class="copy">copy</button><pre><code>' + esc(a.cmd) + '</code></pre></div>'
               : '<p class="fv-nocmd">No command: something done or checked by hand.</p>') +
        '<div class="cap"><div class="cl">Paste output <span class="kp">captures["' + id + '"]</span></div>' +
          '<textarea data-cap="' + id + '" placeholder="paste what it printed — it saves as you type"></textarea>' +
          '<div class="ft"><span>exit <input class="ec" data-ec="' + id + '" placeholder="0"></span>' +
            '<span data-cnt="' + id + '">empty</span><span data-at="' + id + '"></span></div>' +
          '<input class="nt" data-note="' + id + '" placeholder="note for the agent (optional)">' +
        '</div>' +
        '<div class="fv-own"><span>Added by you, after <b>' + (isZero(a.after) ? 'the start' : a.after) +
          '</b>. The agent folds it into the source as <b>' + id + '</b>, so this output stays attached.</span>' +
          '<span class="fv-acts2"><button type="button" class="fv-lnk" data-fv="edit">edit</button>' +
          '<button type="button" class="fv-lnk" data-fv="remove">remove</button></span></div>' +
        '<div class="fin"><span class="vd vdf" data-fvvd="' + id + '" aria-live="polite"></span>' +
          '<button type="button" class="fd">Done <span class="bx"></span></button></div>' +
      '</div></details>' +
      '<span class="ctr"><span class="badge ' + (w ? 'w' : 'ro') + '">' + (w ? 'write' : 'read') + '</span>' +
        (a.cmd ? '<button class="copy" title="Copy this step’s command without opening the step">⧉</button>' : '') +
        '<span class="vd" data-fvvd="' + id + '">—</span></span>';
    var r = st.captures[id] || {}, s = st.steps[id] || {};
    $('textarea', li).value = r.text || '';
    $('input.ec', li).value = r.exit || '';
    $('input.nt', li).value = r.note || '';
    $('input.done', li).checked = !!s.done;
    var ak = $('input.ack', li); if (ak) ak.checked = !!s.acked;
    $('details.sd', li).open = !!st.open['step:' + id];
    paintAdded(li);
    return li;
  }
  function paintAdded(li) {
    var id = li.dataset.step, s = st.steps[id] || {}, r = st.captures[id] || {}, v = r.verdict || '';
    li.classList.toggle('done', !!s.done);
    li.classList.toggle('acked', !!s.acked);
    var after = li.dataset.after;
    if (after) li.classList.toggle('dim', !(st.steps[after] && st.steps[after].done) &&
                                           !((st.captures[after] || {}).text || '').trim());
    var b = $('.fin>button.fd', li), bx = b && $('.bx', b);
    if (b) { b.classList.toggle('on', !!s.done); b.setAttribute('aria-pressed', s.done ? 'true' : 'false'); }
    if (bx) bx.textContent = s.done ? '✅' : '☐';
    $$('[data-fvvd]', li).forEach(function (c) {
      var foot = c.classList.contains('vdf');
      c.className = 'vd' + (foot ? ' vdf' : '') + (v ? ' ' + v : '');
      c.textContent = foot ? (v ? GLYPH[v] + ' ' + VD[v] : '· not captured') : (VD[v] || '—');
      c.title = v === 'saved' ? 'captured: an added step has no pass rule yet; the agent writes one when it folds the step'
        : v === 'error' ? 'the interpreter rejected this command: the target was never asked' : '';
    });
    var ta = $('textarea', li), cnt = $('[data-cnt]', li), at = $('[data-at]', li);
    if (cnt && ta) cnt.textContent = ta.value.trim() ? ta.value.split('\n').length + ' lines · ' + ta.value.length + ' chars' : 'empty';
    if (at) { at.textContent = r.at ? 'captured ' + pt(r.at, true) : ''; at.title = r.at || ''; }
  }
  // flow.js repaints a playbook's counter only on its own events, so ours does it too, the same way
  function paintProgress(pb) {
    if (!pb) return;
    var lis = $$('li.step', pb), done = 0, fail = 0, err = 0;
    lis.forEach(function (li) {
      var id = li.dataset.step, v = (st.captures[id] || {}).verdict;
      if ((st.steps[id] || {}).done) done++;
      if (v === 'fail') fail++; else if (v === 'error') err++;
    });
    var p = $('.prog', pb);
    if (p) p.innerHTML = done + ' / ' + lis.length + ' done' + (fail ? ' · <span class="f">' + fail + ' failed</span>' : '') +
      (err ? ' · <span class="e">' + err + ' errored</span>' : '');
  }

  /* ── the playbook: added steps in place, an insert line on every seam ───── */
  function renderSteps() {
    $$('li.fv-added, li.fv-gap, li.fv-end').forEach(function (n) { n.remove(); });
    $$('ol.steps').forEach(function (ol) {
      var steps = authoredIn(ol);
      if (!steps.length) return;
      var letter = steps[0].dataset.step.charAt(0);
      groupOf(letter + '0').forEach(function (id) { ol.insertBefore(addedLi(id), steps[0]); });
      steps.forEach(function (li, i) {
        var base = li.dataset.step, last = li;
        groupOf(base).forEach(function (id) { var a = addedLi(id); last.after(a); last = a; });
        if (i === steps.length - 1) return;           // the end row covers the last seam
        var g = el('li', 'fv-gap'), nid = nextAddedId(base);
        g.innerHTML = '<button type="button" class="fv-ins" data-fv="ins" data-base="' + base + '" ' +
          'title="Add a step here. It becomes ' + nid + ', and no other step is renamed.">' +
          '<span>+ add a step after ' + last.dataset.step + '<i>→ ' + nid + '</i></span></button>';
        last.after(g);
      });
      var tb = steps[steps.length - 1].dataset.step;
      ol.appendChild(el('li', 'fv-end', '<button type="button" class="fv-endbtn" data-fv="ins" data-base="' + tb + '">' +
        '+ Add a step to this playbook<i>→ ' + nextAddedId(tb) + '</i></button>'));
    });
    $$('.pb').forEach(paintProgress);
  }
  // every step's foot gains + step after and + to-do, left of the verdict and Done
  function renderFoot() {
    $$('li.step').forEach(function (li) {
      var fin = $('.sd>.in>.fin', li);
      if (!fin || $('.fv-foot', fin)) return;
      fin.insertBefore(el('span', 'fv-foot',
        '<button type="button" class="fv-fb" data-fv="footstep" title="Add a step after this one">+ step after</button>' +
        '<button type="button" class="fv-fb" data-fv="foottodo" title="Add a to-do tied to this step (t)">+ to-do</button>'), fin.firstChild);
    });
  }
  // a red or amber chip is often how you learn a step was missing: offer it there
  function prevBase(li) {
    var ol = li.closest('ol.steps'), steps = authoredIn(ol), i = steps.indexOf(li);
    return i > 0 ? steps[i - 1].dataset.step : li.dataset.step.charAt(0) + '0';
  }
  function paintMiss() {
    $$('li.step').forEach(function (li) {
      if (isAdded(li) || !BASE.test(li.dataset.step || '')) return;
      var inb = $('.sd>.in', li); if (!inb) return;
      var box = $('.fv-miss', inb), id = li.dataset.step, v = (st.captures[id] || {}).verdict;
      if (!box) { box = el('div', 'fv-miss'); inb.insertBefore(box, $('.fin', inb)); }
      box.hidden = !(v === 'fail' || v === 'error');
      if (box.hidden) return;
      var prev = prevBase(li), at = isZero(prev) ? 'before ' + id : 'after ' + lastOf(prev);
      box.innerHTML = '<span>' + (v === 'error' ? 'Rejected before it ran. Was a setup step missing before ' + id + '?'
        : 'Was a step missing before ' + id + '?') + '</span>' +
        '<button type="button" class="fv-fb" data-fv="ins" data-base="' + prev + '">+ add it ' + at +
        ' → ' + nextAddedId(prev) + '</button>';
    });
  }

  /* ── the composer: one sentence, read or write, an optional command ────── */
  var comp = null;
  function anchorFor(base) {
    if (!isZero(base)) return { li: $('li.step[data-step="' + lastOf(base) + '"]'), before: false };
    var g = groupOf(base);
    if (g.length) return { li: $('li.step[data-step="' + g[g.length - 1] + '"]'), before: false };
    var first = $$('li.step').filter(function (li) {
      return !isAdded(li) && (li.dataset.step || '').charAt(0) === base.charAt(0);
    })[0];
    return { li: first, before: true };
  }
  function openComposer(base, o) {
    o = o || {};
    closeComposer();
    if (!base) return;
    var an = o.edit ? { li: $('li.step[data-step="' + o.edit + '"]'), before: false } : anchorFor(base);
    if (!an.li) return;
    var row = an.li.closest('details.row'); if (row && !row.open) row.open = true;
    var a = o.edit ? st.added[o.edit] : null, id = o.edit || nextAddedId(base);
    var where = o.edit ? 'Edit added step' : (an.before ? 'New step before ' : 'New step after ') +
      '<span class="fv-lc">' + an.li.dataset.step + '</span>';
    var li = el('li', 'fv-compose');
    li.innerHTML =
      '<div class="fv-ch"><span class="fv-car">‸</span>' + where + ' <span class="fv-nid">' + id + '</span>' +
        (o.edit ? '' : '<span class="fv-hint">no other step is renamed</span>') +
        (o.todo ? '<span class="fv-hint">from to-do ' + o.todo + '</span>' : '') +
      '</div>' +
      '<input class="fv-in" data-k="text" placeholder="One sentence: what this step establishes or changes.">' +
      '<div class="fv-row"><span class="fv-m" data-m="words"></span><span class="fv-m" data-m="sent"></span>' +
        '<span class="fv-seg" role="group" aria-label="blast radius"><button type="button" data-fv="risk" data-risk="ro">read</button>' +
        '<button type="button" data-fv="risk" data-risk="w" class="w">write</button></span>' +
        '<span class="fv-hint" data-m="riskhint"></span></div>' +
      '<label class="fv-lab">Command <span>' +
        'optional: leave it empty for something done by hand</span></label>' +
      '<textarea class="fv-in mono" data-k="cmd" rows="1" spellcheck="false" placeholder="the command, on one line"></textarea>' +
      '<div class="fv-row" data-m="lint"></div>' +
      '<div class="fv-btns"><button type="button" class="fv-bp" data-fv="csave">' + (o.edit ? 'Save ' : 'Add ') + id + '</button>' +
        '<button type="button" class="fv-bg" data-fv="ccancel">Cancel</button>' +
        (o.edit || o.todo ? '' : '<button type="button" class="fv-lnk" data-fv="ctodo">or keep it as a to-do</button>') +
        '<span class="fv-hint">↵ add · esc cancel</span></div>';
    if (an.before) an.li.parentNode.insertBefore(li, an.li); else an.li.after(li);
    if (o.edit) an.li.hidden = true;
    comp = { li: li, base: base, id: id, edit: o.edit || null, todo: o.todo || null, risk: a ? a.risk : 'ro', hid: o.edit ? an.li : null };
    $('[data-k="text"]', li).value = a ? a.text : (o.text || '');
    $('[data-k="cmd"]', li).value = a ? (a.cmd || '') : (o.cmd || '');
    paintComposer();
    var inp = $('[data-k="text"]', li);
    if (!POSE) { inp.focus({ preventScroll: true }); inp.setSelectionRange(inp.value.length, inp.value.length); }
    li.scrollIntoView({ block: 'nearest' });
  }
  function closeComposer() {
    if (!comp) return;
    if (comp.hid) comp.hid.hidden = false;
    comp.li.remove(); comp = null;
  }
  function meter(n, cls, text) {
    if (!n) return;
    n.className = 'fv-m' + (cls ? ' ' + cls : '');
    n.innerHTML = text; n.hidden = !text;
  }
  function paintComposer() {
    if (!comp) return;
    var li = comp.li, text = $('[data-k="text"]', li).value, cmd = $('[data-k="cmd"]', li).value;
    var n = words(text), multi = (text.trim().replace(/[.!?]$/, '').match(/[.!?]\s/g) || []).length > 0;
    meter($('[data-m="words"]', li), n <= 20 ? 'ok' : 'warn', n ? n + ' / 20 words' : '');
    meter($('[data-m="sent"]', li), multi ? 'warn' : 'ok',
      !text.trim() ? '' : multi ? 'two sentences: the agent will split it' : 'one sentence');
    $$('.fv-seg button', li).forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.risk === comp.risk ? 'true' : 'false');
    });
    $('[data-m="riskhint"]', li).textContent = comp.risk === 'w' ? 'it writes, so it gets a gate like every write step'
      : 'it changes nothing';
    /* the audit's paste-safety rules, shown while typing: a smart quote from
       chat or a doc is the one a human pastes in most, and a console rejects it */
    var out = [];
    if (cmd.trim()) {
      var bad = /[^\x00-\x7E]/.exec(cmd);
      var lines = cmd.replace(/\r/g, '').split('\n').filter(function (l) { return l.trim(); }).length;
      out.push(bad ? '<span class="fv-m warn">non-ASCII ' + esc(bad[0]) + ' at ' + (bad.index + 1) +
        ': a console rejects it <button type="button" data-fv="ascii">fix</button></span>'
        : '<span class="fv-m ok">ASCII</span>');
      out.push(lines > 1 ? '<span class="fv-m warn">' + lines + ' lines: keep it to one</span>' : '<span class="fv-m ok">one line</span>');
      if (/^\s*(#|\/\/|<#|rem\b)/i.test(cmd)) out.push('<span class="fv-m warn">starts with a comment: its first character gets dropped</span>');
    }
    $('[data-m="lint"]', li).innerHTML = out.join('');
    $('[data-fv="csave"]', li).disabled = !text.trim();
  }
  function asciiFix(s) {
    return s.replace(/[‘’‚′]/g, "'").replace(/[“”„″]/g, '"')
      .replace(/[–—−]/g, '-').replace(/…/g, '...').replace(/[   ]/g, ' ');
  }
  function saveComposer() {
    if (!comp) return;
    var li = comp.li;
    var text = $('[data-k="text"]', li).value.trim().replace(/\s+/g, ' ');
    var cmd = $('[data-k="cmd"]', li).value.replace(/\r/g, '').trim();
    if (!text) return;
    var c = comp, id = c.id;
    if (c.edit) {
      var a = st.added[id]; a.text = text; a.cmd = cmd; a.risk = c.risk; a.edited = iso();
    } else {
      st.added[id] = { after: c.base, text: text, cmd: cmd, risk: c.risk, at: iso() };
      st.open['step:' + id] = true;
    }
    if (c.todo && st.todos[c.todo]) {
      var t = st.todos[c.todo]; t.became = id; t.done = true; t.doneAt = iso();
    }
    closeComposer();
    save(); renderAll();
    var nli = $('li.step[data-step="' + id + '"]');
    if (nli) {
      flashEl(nli);
      var ta = !c.edit && $('textarea', nli);
      if (ta) ta.focus({ preventScroll: true });
    }
    toast((c.edit ? 'Saved ' : 'Added ') + id + (c.todo ? ' from ' + c.todo : '') + ': in the sidecar, not yet in the source');
  }

  /* ── to-dos ──────────────────────────────────────────────────────────────
     Two kinds, in the words a human uses mid-run: something the write-up is
     missing (it can become a step), and something to do once the run is over. */
  var KIND = { add: ['Add to the write-up', 'add to write-up'], do: ['Do after this run', 'do after'] };
  var lastStep = null, newKind = (st.ui && st.ui.fvKind) || 'add', rbOpen = false;
  function setKind(k) { newKind = k === 'do' ? 'do' : 'add'; st.ui = st.ui || {}; st.ui.fvKind = newKind; }
  function addTodo(text, kind, ref) {
    text = (text || '').trim().replace(/\s+/g, ' ');
    if (!text) return null;
    var id = nextTodoId();
    st.todos[id] = { text: text, kind: kind === 'do' ? 'do' : 'add', ref: ref || null, at: iso(), done: false };
    save(); renderTodos(); renderMarkers(); renderPill();
    return id;
  }
  function byOrder(a, b) {
    var ta = st.todos[a], tb = st.todos[b];
    if (!!ta.done !== !!tb.done) return ta.done ? 1 : -1;
    return (+a.slice(1) || 0) - (+b.slice(1) || 0);
  }
  function todoLi(id) {
    var t = st.todos[id];
    var anc = t.ref ? '<button type="button" class="fv-anc" data-fv="go" data-go="' + t.ref + '" title="go to ' + t.ref + '">after ' + t.ref + '</button>' : '';
    var became = t.became ? '<button type="button" class="fv-became" data-fv="go" data-go="' + t.became +
      '" title="this to-do became step ' + t.became + '">→ ' + t.became + '</button>' : '';
    var promote = !t.done && t.kind === 'add' && t.ref ? '<button type="button" class="fv-lnk" data-fv="promote">make it a step</button>' : '';
    var when = t.done ? 'done ' + pt(t.doneAt) : pt(t.at);
    return '<li class="fv-ti' + (t.done ? ' done' : '') + '" data-tid="' + id + '">' +
      '<input type="checkbox" class="fv-tck"' + (t.done ? ' checked' : '') + ' aria-label="' + id + ' done">' +
      '<span class="fv-id">' + id + '</span><span class="fv-tx">' + esc(t.text) + '</span>' +
      '<span class="fv-meta">' + anc + became + '<span title="' + esc(t.done ? t.doneAt : t.at) + '">' + esc(when) + '</span>' +
      '<span class="fv-acts">' + promote + '<button type="button" class="fv-lnk" data-fv="tedit">edit</button>' +
      '<button type="button" class="fv-lnk" data-fv="tdel">remove</button></span></span></li>';
  }
  function stepOptions(sel) {
    return '<option value="">no step</option>' + $$('li.step').map(function (li) {
      var id = li.dataset.step;
      return '<option value="' + id + '"' + (id === sel ? ' selected' : '') + '>after ' + id + '</option>';
    }).join('');
  }
  function renderTodos() {
    var sec = $('#fvTodo');
    if (!sec) {
      sec = el('section', 'fv-todo');
      sec.id = 'fvTodo';
      sec.setAttribute('data-fv-live', '');
      sec.innerHTML = '<details><summary><span class="fv-k">To do</span><span class="fv-cnt"></span>' +
        '<span class="fv-peek"></span><button type="button" class="fv-add" data-fv="tnew">+ to-do</button></summary>' +
        '<div class="fv-body"></div></details>';
      var foot = $('.foot');
      if (foot) foot.parentNode.insertBefore(sec, foot); else document.body.appendChild(sec);
      var d = $('details', sec);
      d.open = !!st.open['fv:todo'];
      d.addEventListener('toggle', function () { st.open['fv:todo'] = d.open; save(); });
    }
    var ids = live(st.todos), open = ids.filter(function (id) { return !st.todos[id].done; }).sort(byOrder);
    $('.fv-cnt', sec).innerHTML = ids.length ? '<b>' + open.length + ' open</b> · ' + (ids.length - open.length) + ' done'
      : 'nothing yet · press <b>t</b> anywhere';
    $('.fv-peek', sec).textContent = open.length ? open[0] + '  ' + st.todos[open[0]].text : '';
    var h = '';
    ['add', 'do'].forEach(function (k) {
      var list = ids.filter(function (id) { return st.todos[id].kind === k; }).sort(byOrder);
      if (!list.length) return;
      var n = list.filter(function (id) { return !st.todos[id].done; }).length;
      h += '<div class="fv-grp">' + KIND[k][0] + ' <em>' + n + '</em></div><ul class="fv-tl">' + list.map(todoLi).join('') + '</ul>';
    });
    if (!ids.length) h += '<div class="fv-empty">Something this write-up is missing, or something to do once the run is over. ' +
      'Press <b>t</b> anywhere, or <b>+ to-do</b> in the pill, and it lands here without moving the page.</div>';
    h += '<div class="fv-new"><input class="fv-in" data-k="ttext" placeholder="Something to add to this write-up, or to do after the run">' +
      '<span class="fv-seg" role="group" aria-label="kind">' +
        '<button type="button" data-fv="tkind" data-kind="add">add to write-up</button>' +
        '<button type="button" data-fv="tkind" data-kind="do">do after</button></span>' +
      '<select data-k="tref" aria-label="tie it to a step">' + stepOptions(lastStep) + '</select>' +
      '<button type="button" class="fv-bp" data-fv="tadd">Add</button></div>';
    h += '<details class="more fv-rb"' + (rbOpen ? ' open' : '') + '><summary>what the agent reads back</summary><div class="in">' +
      '<div class="cmd fig"><pre><code data-fv-rb></code></pre></div>' +
      '<div class="fv-btns"><button type="button" class="fv-bg" data-fv="copyagent">Copy additions for agent</button>' +
      '<span class="fv-hint">in 3.1.0 this rides along in Copy captures for agent</span></div></div></details>';
    $('.fv-body', sec).innerHTML = h;
    $$('[data-fv="tkind"]', sec).forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.kind === newKind ? 'true' : 'false'); });
    var rb = $('.fv-rb', sec);
    rb.addEventListener('toggle', function () { rbOpen = rb.open; });
    renderReadBack();
  }
  function renderMarkers() {
    $$('.fv-tdm, .fv-rm').forEach(function (n) { n.remove(); });
    var byRef = {};
    live(st.todos).forEach(function (id) {
      var t = st.todos[id];
      if (!t.done && t.ref) (byRef[t.ref] = byRef[t.ref] || []).push(id);
    });
    Object.keys(byRef).forEach(function (ref) {
      var ds = $('li.step[data-step="' + ref + '"] .sd>summary .ds');
      if (!ds) return;
      var c = el('span', 'fv-tdm');
      c.setAttribute('data-fv', 'gotodo');
      c.setAttribute('data-tid', byRef[ref][0]);
      c.textContent = byRef[ref].length + ' to-do';
      c.title = byRef[ref].map(function (id) { return id + ': ' + st.todos[id].text; }).join('\n');
      ds.after(c);
    });
    // at rest the rows are shut: say on the row where the human added something
    $$('details.row').forEach(function (row) {
      var ids = $$('li.step', row).map(function (li) { return li.dataset.step; });
      var nAdd = $$('li.fv-added', row).length, nTodo = 0;
      live(st.todos).forEach(function (id) {
        var t = st.todos[id];
        if (!t.done && t.ref && ids.indexOf(t.ref) >= 0) nTodo++;
      });
      if (!nAdd && !nTodo) return;
      var s = $('summary', row);
      var m = el('span', 'fv-rm');
      m.textContent = [nAdd ? '+' + nAdd + ' added' : '', nTodo ? nTodo + ' to-do' : ''].filter(Boolean).join(' · ');
      m.title = 'typed into the page after handover: the agent reads these back';
      s.insertBefore(m, $('.rt', s));
    });
  }
  function renderPill() {
    var txt = $('#flowPillTxt');
    if (!txt) return;
    var b = $('#fvTodoBtn');
    if (!b) {
      b = el('button');
      b.id = 'fvTodoBtn'; b.type = 'button';
      b.setAttribute('data-fv', 'quick');
      b.title = 'Add a to-do without losing your place (t)';
      txt.after(el('span', 'sep'), b);
    }
    var n = live(st.todos).filter(function (id) { return !st.todos[id].done; }).length;
    b.innerHTML = '+ to-do' + (n ? '<span class="fv-pc">' + n + '</span>' : '');
  }

  /* ── what the agent reads back: a mock of flowviz captures in 3.1.0 ─────── */
  function trunc(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
  function pad(s, n) { s = String(s); return s + new Array(Math.max(1, n - s.length + 1)).join(' '); }
  function readBackText() {
    var L = [], adds = live(st.added);
    L.push('$ flowviz captures ' + SRC.replace('.src.html', '.html') + '        # as 3.1.0 would print it');
    $$('.pb').forEach(function (pb) {
      if (!$('li.fv-added', pb)) return;
      var t = $('.hd .t', pb);
      L.push('playbook  ' + (t ? t.textContent.trim() : '(untitled)'));
      $$('li.step', pb).forEach(function (li) {
        var id = li.dataset.step, r = st.captures[id] || {}, v = (r.verdict || '');
        var vd = v === 'saved' ? (isAdded(li) ? 'CAPTURED' : 'NO MATCH') : v ? v.toUpperCase() : '-';
        var risk = li.dataset.risk === 'w' ? 'WRITE' : 'read';
        var ds = $('.ds', li), sentence = ds ? ds.textContent : '';
        if (!isAdded(li)) { L.push('step ' + pad(id, 6) + pad(risk, 7) + pad(vd, 10) + trunc(sentence.trim(), 64)); return; }
        var a = st.added[id];
        L.push('+    ' + pad(id, 6) + pad(risk, 7) + pad(vd, 10) + a.text);
        L.push('  added ' + pt(a.at) + ' in the page, after ' + (isZero(a.after) ? 'the start' : a.after) + ' · not in the source yet');
        if (a.cmd) L.push('  $ ' + a.cmd);
        if ((r.text || '').trim()) {
          L.push('  exit ' + (r.exit === '' || r.exit == null ? '-' : r.exit) + ' · captured ' + pt(r.at) + (r.note ? ' · note: ' + r.note : ''));
          r.text.split('\n').slice(0, 4).forEach(function (x) { L.push('  | ' + x); });
        }
      });
    });
    var ids = live(st.todos).sort(byOrder), open = ids.filter(function (id) { return !st.todos[id].done; }).length;
    if (ids.length) {
      L.push('');
      L.push('to-dos  ' + open + ' open · ' + (ids.length - open) + ' done');
      ids.forEach(function (id) {
        var t = st.todos[id];
        L.push('  ' + pad(id, 4) + (t.done ? '[x]  ' : '[ ]  ') + pad(t.kind, 5) + pad(t.ref ? 'after ' + t.ref : '', 10) + t.text +
          (t.became ? '  -> became ' + t.became : ''));
      });
    }
    if (adds.length) {
      L.push('');
      L.push('fold with: flowviz fold ' + SRC + '   (' + adds.join(', ') + ' keep their ids)');
    }
    if (L.length === 1) L.push('(nothing added yet)');
    return L.join('\n');
  }
  function renderReadBack() {
    var c = $('[data-fv-rb]');
    if (c) c.textContent = readBackText();
  }
  function agentJson() {
    var added = {};
    live(st.added).forEach(function (id) {
      var a = st.added[id], r = st.captures[id] || {};
      added[id] = { after: a.after, text: a.text, cmd: a.cmd || '', risk: a.risk, at: a.at,
                    done: !!(st.steps[id] || {}).done };
      if ((r.text || '').trim()) added[id].capture = { text: r.text, exit: r.exit, verdict: r.verdict, at: r.at, note: r.note || '' };
    });
    var todos = {};
    live(st.todos).forEach(function (id) { todos[id] = st.todos[id]; });
    return '```json\n' + JSON.stringify({ doc: DOC, flowviz: FV.version + '+proto', at: iso(), added: added, todos: todos }, null, 2) + '\n```';
  }

  /* ── quick capture: a to-do from anywhere, without losing your place ───── */
  var quick = null, qref = null;
  function openQuick(ref) {
    if (!quick) {
      quick = el('div', 'fv-quick');
      quick.id = 'fvQuick';
      quick.setAttribute('data-fv-live', '');
      quick.setAttribute('role', 'dialog');
      quick.setAttribute('aria-label', 'New to-do');
      document.body.appendChild(quick);
    }
    qref = ref !== undefined ? ref : lastStep;
    var open = live(st.todos).filter(function (id) { return !st.todos[id].done; }).length;
    quick.innerHTML = '<div class="fv-qh"><span class="fv-k">New to-do · <span class="fv-lc">' + nextTodoId() + '</span></span>' +
      (qref ? '<span class="fv-qa" title="tied to the step you were on">after ' + qref +
        '<button type="button" data-fv="qnoref" title="not tied to a step">✕</button></span>' : '') +
      '<button type="button" class="fv-lnk" data-fv="qclose">esc</button></div>' +
      '<input class="fv-in" data-k="qtext" placeholder="Add to the write-up, or do after the run">' +
      '<div class="fv-qf"><span class="fv-seg" role="group" aria-label="kind">' +
        '<button type="button" data-fv="qkind" data-kind="add">add to write-up</button>' +
        '<button type="button" data-fv="qkind" data-kind="do">do after</button></span>' +
        '<span class="fv-hint">↵ save · <a href="#fvTodo" data-fv="qall">' + open + ' open, see all</a></span></div>';
    $$('[data-fv="qkind"]', quick).forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.kind === newKind ? 'true' : 'false'); });
    quick.hidden = false;
    if (!POSE) $('[data-k="qtext"]', quick).focus();
  }
  function closeQuick() { if (quick) quick.hidden = true; }
  function saveQuick() {
    var inp = quick && $('[data-k="qtext"]', quick);
    if (!inp || !inp.value.trim()) return;
    var id = addTodo(inp.value, newKind, qref);
    closeQuick();
    var b = $('#fvTodoBtn'); if (b) flashEl(b);
    toast(id + ' saved' + (qref ? ' · after ' + qref : '') + ' · it waits in To do at the bottom');
  }

  /* ── small things ──────────────────────────────────────────────────────── */
  var toastEl = null, toastT = null;
  function toast(t) {
    if (!toastEl) { toastEl = el('div', 'fv-toast'); toastEl.setAttribute('aria-live', 'polite'); document.body.appendChild(toastEl); }
    toastEl.textContent = t; toastEl.classList.add('on');
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.classList.remove('on'); }, 2600);
  }
  function flashEl(n) { n.classList.remove('fv-flash'); void n.offsetWidth; n.classList.add('fv-flash'); }
  function goStep(id) {
    var li = $('li.step[data-step="' + id + '"]');
    if (!li) return;
    var row = li.closest('details.row'); if (row && !row.open) row.open = true;
    li.scrollIntoView({ block: 'center', behavior: 'smooth' });
    flashEl(li);
  }
  function goTodo(tid) {
    var sec = $('#fvTodo'); if (!sec) return;
    var d = $('details', sec); if (d && !d.open) d.open = true;
    var li = $('li.fv-ti[data-tid="' + tid + '"]', sec) || sec;
    li.scrollIntoView({ block: 'center', behavior: 'smooth' });
    flashEl(li);
  }
  function copy(text, btn, label) {
    navigator.clipboard.writeText(text).then(function () { FV.flash(btn, label); }, function () { FV.flash(btn, 'clipboard blocked'); });
  }
  function renderProtoTag() {
    if ($('#fvProto')) return;
    var p = el('div', 'fv-proto');
    p.id = 'fvProto';
    p.innerHTML = '<b>prototype</b><span>to-dos and added steps · not in template/</span>' +
      (window.FVPROTO_SEED ? '<button type="button" data-fv="reset" title="clear everything typed into this page">start empty</button>' +
        '<button type="button" data-fv="demo" title="put the demo run back">demo run</button>' : '');
    document.body.appendChild(p);
  }
  function replaceState(src) {
    ['vars', 'checks', 'open', 'steps', 'captures', 'notes', 'emits', 'added', 'todos'].forEach(function (k) {
      st[k] = JSON.parse(JSON.stringify((src && src[k]) || {}));
    });
    save();
    toast('reloading…');
    setTimeout(function () { location.reload(); }, 1300);
  }

  function renderAll() {
    renderSteps(); renderFoot(); paintMiss(); renderTodos(); renderMarkers(); renderPill();
  }

  /* ── events: delegated, because every element here is drawn after flow.js
     bound its own handlers, and is redrawn whenever the structure changes ── */
  document.addEventListener('input', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    if (comp && comp.li.contains(t)) { paintComposer(); return; }
    var li = t.closest('li.fv-added');
    if (li) {
      var id = li.dataset.step;
      if (t.matches('textarea[data-cap]')) {
        var r = cap(id);
        r.text = t.value; r.at = t.value.trim() ? iso() : null; r.verdict = verdictOf(t.value);
        paintAdded(li); paintProgress(li.closest('.pb'));
      } else if (t.matches('input[data-ec]')) cap(id).exit = t.value;
      else if (t.matches('input[data-note]')) cap(id).note = t.value;
      save(); renderReadBack();
      return;
    }
    // an authored step's paste can turn its chip red: offer the missing step there
    if (t.matches('textarea[data-cap]')) { paintMiss(); renderReadBack(); }
  });
  document.addEventListener('change', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var li = t.closest('li.fv-added');
    if (li && t.matches('input.done')) { setDone(li, t.checked, true); return; }
    if (li && t.matches('input.ack')) { stepRec(li.dataset.step).acked = t.checked; paintAdded(li); save(); return; }
    var ti = t.closest('li.fv-ti');
    if (ti && t.matches('.fv-tck') && ti.closest('[data-fv-live]')) {
      var td = st.todos[ti.dataset.tid];
      td.done = t.checked; td.doneAt = t.checked ? iso() : null;
      save(); renderTodos(); renderMarkers(); renderPill();
    }
    if (t.matches('select[data-k="tref"]')) lastStep = t.value || lastStep;
  });
  function setDone(li, on, collapse) {
    stepRec(li.dataset.step).done = on;
    var dn = $('input.done', li); if (dn) dn.checked = on;
    paintAdded(li); paintProgress(li.closest('.pb')); save(); renderReadBack();
    if (on && collapse) { var sd = $('details.sd', li); if (sd && sd.open) sd.open = false; }
  }
  // toggle does not bubble: listen in the capture phase
  document.addEventListener('toggle', function (e) {
    var d = e.target;
    if (!d.matches || !d.matches('details.sd')) return;
    var li = d.closest('li.step'); if (!li) return;
    if (d.open) lastStep = li.dataset.step;
    if (isAdded(li)) { st.open['step:' + li.dataset.step] = d.open; save(); }
  }, true);
  document.addEventListener('focusin', function (e) {
    var li = e.target.closest && e.target.closest('li.step');
    if (li) lastStep = li.dataset.step;
  });

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    if (quick && !quick.hidden && !quick.contains(t) && !t.closest('#fvTodoBtn')) closeQuick();
    var li = t.closest('li.fv-added'), done = t.closest('.fin>button.fd');
    if (li && done) {
      var on = !(st.steps[li.dataset.step] || {}).done;
      setDone(li, on, false);
      var bx = $('.bx', done);
      if (on && bx) { bx.classList.remove('pop'); void bx.offsetWidth; bx.classList.add('pop'); }
      if (on) setTimeout(function () { var sd = $('details.sd', li); if (sd) sd.open = false; }, 300);
      return;
    }
    var b = t.closest('[data-fv]');
    if (!b || b.closest('.fvm')) return;                 // the proposal's static mockups never act
    var act = b.getAttribute('data-fv'), stepLi = b.closest('li.step'), ti = b.closest('li.fv-ti');
    if (act === 'ins') { e.preventDefault(); openComposer(b.dataset.base); }
    else if (act === 'footstep') openComposer(baseOf(stepLi.dataset.step));
    else if (act === 'foottodo') openQuick(stepLi.dataset.step);
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
    else if (act === 'edit' && stepLi) openComposer(st.added[stepLi.dataset.step].after, { edit: stepLi.dataset.step });
    else if (act === 'remove' && stepLi) {
      if (!b.classList.contains('fv-sure')) {
        b.classList.add('fv-sure'); b.textContent = 'remove ' + stepLi.dataset.step + '?';
        setTimeout(function () { b.classList.remove('fv-sure'); b.textContent = 'remove'; }, 3000);
        return;
      }
      st.added[stepLi.dataset.step].gone = iso();         // a tombstone, never a delete
      save(); renderAll(); toast(stepLi.dataset.step + ' removed · its id is never reused');
    }
    else if (act === 'go') { e.preventDefault(); goStep(b.dataset.go); }
    else if (act === 'gotodo') { e.preventDefault(); e.stopPropagation(); goTodo(b.dataset.tid); }
    else if (act === 'tnew') { e.preventDefault(); openQuick(); }
    else if (act === 'quick') { if (quick && !quick.hidden) closeQuick(); else openQuick(); }
    else if (act === 'qclose') closeQuick();
    else if (act === 'qnoref') { qref = null; var qa = b.closest('.fv-qa'); if (qa) qa.remove(); $('[data-k="qtext"]', quick).focus(); }
    else if (act === 'qkind' || act === 'tkind') {
      setKind(b.dataset.kind);
      $$('[data-fv="' + act + '"]').forEach(function (x) { x.setAttribute('aria-pressed', x.dataset.kind === newKind ? 'true' : 'false'); });
    }
    else if (act === 'qall') { e.preventDefault(); closeQuick(); goTodo(''); }
    else if (act === 'tadd') {
      var sec = $('#fvTodo'), inp = $('[data-k="ttext"]', sec), sel = $('[data-k="tref"]', sec);
      var id2 = addTodo(inp.value, newKind, sel.value || null);
      if (id2) { var again = $('[data-k="ttext"]', sec); if (again) again.focus(); toast(id2 + ' saved'); }
    }
    else if (act === 'promote' && ti) {
      var td = st.todos[ti.dataset.tid];
      openComposer(baseOf(td.ref), { todo: ti.dataset.tid, text: td.text });
    }
    else if (act === 'tedit' && ti) {
      var tx2 = $('.fv-tx', ti), tid = ti.dataset.tid;
      tx2.innerHTML = '<input class="fv-in fv-edit" data-k="tedit" value="' + esc(st.todos[tid].text) + '">';
      var ei = $('input', tx2); ei.focus(); ei.select();
    }
    else if (act === 'tdel' && ti) {
      if (!b.classList.contains('fv-sure')) {
        b.classList.add('fv-sure'); b.textContent = 'remove ' + ti.dataset.tid + '?';
        setTimeout(function () { b.classList.remove('fv-sure'); b.textContent = 'remove'; }, 3000);
        return;
      }
      st.todos[ti.dataset.tid].gone = iso();
      save(); renderTodos(); renderMarkers(); renderPill();
    }
    else if (act === 'copyagent') copy(agentJson(), b, 'copied for the agent');
    else if (act === 'reset') replaceState(null);
    else if (act === 'demo') replaceState(window.FVPROTO_SEED);
  });
  document.addEventListener('keydown', function (e) {
    var t = e.target || {};
    if (e.key === 'Escape') {
      if (quick && !quick.hidden) { closeQuick(); e.preventDefault(); }
      else if (comp) { closeComposer(); e.preventDefault(); }
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      if (comp && comp.li.contains(t)) { e.preventDefault(); saveComposer(); return; }
      if (quick && quick.contains(t) && t.matches('[data-k="qtext"]')) { e.preventDefault(); saveQuick(); return; }
      if (t.matches && t.matches('[data-k="ttext"]')) { e.preventDefault(); var ad = $('[data-fv="tadd"]'); if (ad) ad.click(); return; }
      if (t.matches && t.matches('[data-k="tedit"]')) {
        e.preventDefault();
        var tl = t.closest('li.fv-ti'), v = t.value.trim();
        if (tl && v) { st.todos[tl.dataset.tid].text = v; st.todos[tl.dataset.tid].edited = iso(); save(); }
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
  FV.onHydrate(function () { renderAll(); });

  /* ── poses: fixed views for screenshots, prototype only ─────────────────── */
  function pose() {
    if (!POSE) return;
    /* headless screenshots cannot scroll, so a pose hides what sits above the
       part it shows instead (html.fv-posing, in proto.css) */
    document.documentElement.classList.add('fv-posing');
    var row = $('details.row[data-row="b"]');
    if (POSE === 'steps' || POSE === 'compose') {
      if (row) { row.open = true; row.classList.add('fv-keep'); }
      if (POSE === 'steps') {
        ['b3a', 'b4'].forEach(function (id) { var d = $('li.step[data-step="' + id + '"] details.sd'); if (d) d.open = true; });
        var ins = $('.fv-ins[data-base="b2"]'); if (ins) ins.classList.add('fv-pose');
      } else {
        openComposer('b1', { todo: 't2' });
        $('[data-k="text"]', comp.li).value = 'Confirm kubectl points at the staging context before the rollout.';
        $('[data-k="cmd"]', comp.li).value = 'kubectl config current-context | grep -c \u2019staging\u2019';
        paintComposer();
      }
    } else if (/^row[a-z]$/.test(POSE)) {
      var pr = $('details.row[data-row="' + POSE.slice(3) + '"]');
      if (pr) { pr.open = true; pr.classList.add('fv-keep'); }
    } else if (POSE === 'todo') {
      var d2 = $('#fvTodo details'); if (d2) d2.open = true;
      setKind('do');
      openQuick('b4');
      $('[data-k="qtext"]', quick).value = 'Re-run b4 once the provider confirms the allowlist change';
    }
  }

  renderAll();
  renderProtoTag();
  pose();
})();
