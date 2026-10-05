#!/usr/bin/env python3
"""flowviz-captures — read back what a human pasted into a report's steps and left
as notes on a drawing, straight from the sidecar (SPEC.md §1.3, §1.4, §2.4, §6).
Every verdict is re-derived from the current rules, never trusted from storage.
Steps the human added in the page print in place, marked +, and their to-dos
follow the playbooks (SPEC.md §1.3b). stdlib only.

Usage: flowviz-captures.py <deliverable>.html [--json] [--step ID] [--all]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

try:
    from zoneinfo import ZoneInfo
    try:
        _LA = ZoneInfo('America/Los_Angeles')
    except Exception:
        _LA = None
except ImportError:
    _LA = None


# ── a small DOM ───────────────────────────────────────────────────────────────
# html.parser already HTML-unescapes attribute values and normal text for us
# (it treats <script>/<style> as CDATA, so a JSON spec's raw text comes through
# byte-for-byte, exactly what json.loads() needs).

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
        'param', 'source', 'track', 'wbr'}


class El:
    __slots__ = ('tag', 'attrs', 'parent', 'kids')

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.kids = []

    def has_class(self, name):
        return name in (self.attrs.get('class') or '').split()

    def walk(self):
        for k in self.kids:
            if isinstance(k, El):
                yield k
                yield from k.walk()

    def find(self, pred):
        return [e for e in self.walk() if pred(e)]

    def first(self, pred):
        for e in self.walk():
            if pred(e):
                return e
        return None

    def text(self):
        """Direct + descendant text (skipping script/style), trimmed. No spaces are
        injected between children, matching innerText for the flat, single-line/
        single-sentence fields this tool reads (SPEC.md §1.3, §1.5)."""
        parts = []

        def go(n):
            for k in n.kids:
                if isinstance(k, str):
                    parts.append(k)
                elif k.tag not in ('script', 'style'):
                    go(k)
        go(self)
        return ''.join(parts).strip()

    def raw(self):
        """All descendant text verbatim, including script/style — for pulling a
        figure's JSON spec out intact."""
        return ''.join(k if isinstance(k, str) else k.raw() for k in self.kids)


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = El('#root', {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        el = El(tag, attrs, self.cur)
        self.cur.kids.append(el)
        if tag not in VOID:
            self.cur = el

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(El(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def parse_html(text):
    t = _Tree()
    t.feed(text)
    t.close()
    return t.root


def cls(*names):
    return lambda e: all(e.has_class(n) for n in names)


# ── doc id ──────────────────────────────────────────────────────────────────

_FLOW_BLOB_RE = re.compile(r'window\.FLOW\s*=\s*\{(.*?)\}', re.S)


def _field_from_blob(blob, name):
    m = re.search(r'[\'"]?' + re.escape(name) + r'[\'"]?\s*:\s*[\'"]([^\'"]*)[\'"]', blob)
    return m.group(1) if m else None


def doc_id_from_window_flow(raw_html):
    m = _FLOW_BLOB_RE.search(raw_html)
    return _field_from_blob(m.group(1), 'doc') if m else None


def find_doc_id(raw_html, root):
    doc = doc_id_from_window_flow(raw_html)
    if doc:
        return doc
    meta = root.first(lambda e: e.tag == 'meta' and (e.attrs.get('name') or '').lower() == 'flowviz-doc')
    return meta.attrs.get('content') if meta else None


# ── the verdict vocabulary (SPEC.md §1.4) ────────────────────────────────────
# This list must stay identical to CMD_ERR in template/flow.js. Change both.
_ERROR_PATTERNS = [
    (r'\bParserError\b', 0),
    (r'\bUnexpected token\b', re.I),
    (r'\bMissing (?:closing|expression|argument|statement)\b', re.I),
    (r'\bstring (?:is )?missing the terminator\b', re.I),
    (r'\bpositional parameter cannot be found\b', re.I),
    (r'\bis not recognized as the name of\b', re.I),
    (r'\bCommandNotFoundException\b', 0),
    (r'\bcommand not found\b', re.I),
    (r'\bsyntax error near unexpected token\b', re.I),
    (r'\bunexpected EOF while looking for matching\b', re.I),
    (r'\b(?:SyntaxError|IndentationError|TabError):', 0),
]
_ERROR_RES = [re.compile(p, f) for p, f in _ERROR_PATTERNS]


def is_cmd_error(text):
    return any(rx.search(text) for rx in _ERROR_RES)


def compile_rule(pattern):
    """(compiled|None, warning|None). Case-insensitive, matching flow.js's hit(),
    which always tries `new RegExp(pat, 'i')`. A pattern Python cannot compile is
    treated as never matching, with a warning — it never takes the tool down."""
    if not pattern:
        return None, None
    try:
        return re.compile(pattern, re.I), None
    except re.error as e:
        return None, 'data-pass/data-fail pattern %r is not valid Python re (%s) — treated as no match' % (
            pattern, e)


def derive_verdict(text, pass_rx, fail_rx):
    if not text or not text.strip():
        return 'none'
    if is_cmd_error(text):
        return 'error'
    if fail_rx and fail_rx.search(text):
        return 'fail'
    if pass_rx and pass_rx.search(text):
        return 'pass'
    return 'no match'


def normalize_stored_verdict(v):
    """The sidecar stores flow.js's internal tier names ('saved', or the field is
    simply absent for 'nothing pasted yet') — SPEC.md §1.4's chip words are 'no
    match' and 'none'. Translate so a stored/derived comparison is apples-to-apples
    and never falsely flags a mismatch that is only a vocabulary difference."""
    if not v:
        return 'none'
    if v == 'saved':
        return 'no match'
    return v


# ── time ──────────────────────────────────────────────────────────────────

def fmt_time(iso_str):
    """('14:05:09 PDT', '2026-09-28T21:05:09Z') from a stored UTC ISO string, or
    (None, None) if there's nothing to format. Falls back to UTC with 'Z' when
    the local zone can't be resolved."""
    if not iso_str:
        return None, None
    s = iso_str.strip()
    s2 = s[:-1] + '+00:00' if s.endswith('Z') else s
    try:
        dt = datetime.fromisoformat(s2)
    except ValueError:
        return iso_str, iso_str
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc = dt.astimezone(timezone.utc)
    iso_disp = utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    if _LA is not None:
        try:
            local = utc.astimezone(_LA)
            return '%s %s' % (local.strftime('%H:%M:%S'), local.tzname()), iso_disp
        except Exception:
            pass
    return '%s Z' % utc.strftime('%H:%M:%S'), iso_disp


# ── steps (SPEC.md §1.3) ──────────────────────────────────────────────────
# div.pb (playbook) > ol.steps > li.step[data-step][data-risk] ; sentence in .ds ;
# command in the pre inside the step's div.cmd that is NOT div.cmd.fig (a "shown,
# not run" block, SPEC §1.5) ; textarea[data-cap] carries data-pass/data-fail.
# Numbering restarts per playbook (matches flow.js's own evidence export, which
# does $$('li.step', pb).forEach((li, i) => ...) per div.pb).

def _is_step(e):
    return e.tag == 'li' and e.has_class('step') and 'data-step' in e.attrs


_EMIT_SPLIT = re.compile(r';\s*(?=[A-Z][A-Z0-9_]*=)')
_NAMED = re.compile(r'^[a-z][0-9]+$')


def parse_emits(attr):
    """{NAME: regex} from data-emit's NAME=<regex>[; NAME=<regex>…]; a bad pair is skipped (the audit fails it)."""
    out = {}
    for part in (_EMIT_SPLIT.split(attr.strip()) if attr and attr.strip() else []):
        name, sep, src = part.partition('=')
        try:
            rx = re.compile(src)
        except re.error:
            continue
        if sep and re.match(r'^[A-Z][A-Z0-9_]*$', name.strip()) and rx.groups == 1:
            out[name.strip()] = rx
    return out


def derive_emits(text, emit_rx):
    """The last match's group, per name — exactly what the page stores."""
    got = {}
    for name, rx in emit_rx.items():
        ms = list(rx.finditer(text or ''))
        if ms and ms[-1].group(1) is not None:
            got[name] = ms[-1].group(1).strip()
    return got


def build_step(li, n, playbook=None):
    sid = li.attrs.get('data-step')
    risk = li.attrs.get('data-risk')
    ds_el = li.first(cls('ds'))
    sentence = ds_el.text() if ds_el else ''
    cmd_el = li.first(lambda e: e.tag == 'div' and e.has_class('cmd') and not e.has_class('fig'))
    command = ''
    if cmd_el is not None:
        pre_el = cmd_el.first(lambda e: e.tag == 'pre')
        if pre_el is not None:
            command = pre_el.text()
    ta = li.first(lambda e: e.tag == 'textarea' and 'data-cap' in e.attrs)
    pass_pattern = ta.attrs.get('data-pass') if ta is not None else None
    fail_pattern = ta.attrs.get('data-fail') if ta is not None else None
    emit_rx = parse_emits(ta.attrs.get('data-emit') if ta is not None else '')
    pass_rx, pass_warn = compile_rule(pass_pattern)
    fail_rx, fail_warn = compile_rule(fail_pattern)
    warnings = ['step %s: %s' % (sid, w) for w in (pass_warn, fail_warn) if w]
    return {
        'id': sid, 'n': n, 'risk': risk, 'sentence': sentence, 'command': command, 'playbook': playbook,
        'emit_rx': emit_rx, 'pass_pattern': pass_pattern, 'fail_pattern': fail_pattern,
        'pass_rx': pass_rx, 'fail_rx': fail_rx, 'warnings': warnings,
    }


# ── what the human added in the page (SPEC.md §1.3b) ────────────────────────
# added: {b3a: {after, text, cmd, risk, at, folded?, gone?}} · todos: {t1: {text, kind, ref, at, done, …}}
# A step added after b3 is b3a, then b3b; before a row's first step its anchor is b0. Once `flowviz fold`
# has written it into the source, the HTML holds it and it prints as an ordinary step.

def _live(d):
    return {k: v for k, v in (d or {}).items() if isinstance(v, dict) and not v.get('gone')}


def place_added(steps, added, in_html):
    """The page's steps with every live added step not in the HTML put where the page draws it: after
    the last step sharing its anchor (b3, b3a…) that sorts before it, or before the row's first step."""
    out, warnings = list(steps), []
    for aid in sorted(k for k in _live(added) if k not in in_html):
        a = added[aid]
        base = str(a.get('after') or '')
        if re.match(r'^[a-z]0$', base):
            at = next((i for i, s in enumerate(out) if s['id'] == base[0] + '1'), None)
            pos, pb = (at, out[at]['playbook']) if at is not None else (None, None)
        else:
            idx = [i for i, s in enumerate(out) if s['id'] and (s['id'] == base or (
                re.match(r'^[a-z][0-9]+[a-z]$', s['id']) and s['id'][:-1] == base and s['id'] < aid))]
            pos, pb = (idx[-1] + 1, out[idx[-1]]['playbook']) if idx else (None, None)
        step = {'id': aid, 'n': None, 'risk': a.get('risk') or 'ro', 'sentence': a.get('text') or '',
                'command': a.get('cmd') or '', 'playbook': pb, 'emit_rx': {}, 'pass_pattern': None,
                'fail_pattern': None, 'pass_rx': None, 'fail_rx': None, 'warnings': [], 'added': a}
        if pos is None:
            warnings.append('%s was added after %s, which this file no longer has' % (aid, base or '(nothing)'))
            out.append(step)
        else:
            out.insert(pos, step)
    return out, warnings


def todo_rows(todos):
    live = _live(todos)
    key = lambda k: (1 if live[k].get('done') else 0, int(k[1:]) if k[1:].isdigit() else 0)
    return [dict(live[k], id=k) for k in sorted(live, key=key)]


def print_todos_block(todos, out):
    rows = todo_rows(todos)
    if not rows:
        return
    opened = sum(1 for t in rows if not t.get('done'))
    out.append('')
    out.append('to-dos  %d open · %d done' % (opened, len(rows) - opened))
    for t in rows:
        local, _ = fmt_time(t.get('doneAt') if t.get('done') else t.get('at'))
        out.append('  %-4s %s  %-4s %-10s %s%s%s' % (
            t['id'], '[x]' if t.get('done') else '[ ]', 'do' if t.get('kind') == 'do' else 'add',
            ('after ' + t['ref']) if t.get('ref') else '', t.get('text') or '',
            ('  -> became ' + t['became']) if t.get('became') else '',
            ('   ' + ('done ' if t.get('done') else '') + local) if local else ''))


def print_removed_block(removed, captures, out):
    if not removed:
        return
    out.append('')
    out.append('removed in the page (their ids are never reused)')
    for rid, a in removed:
        local, _ = fmt_time(a.get('gone'))
        text = ((captures.get(rid) or {}).get('text') or '').strip()
        out.append('  %-5s %s%s%s' % (rid, a.get('text') or '', ('   removed ' + local) if local else '',
                                      '   (its capture is kept: %d chars)' % len(text) if text else ''))


def extract_steps(root):
    steps = []
    counted = set()
    for pb in root.find(cls('pb')):
        local = [e for e in pb.walk() if _is_step(e)]
        head = pb.first(lambda e: e.has_class('t') and e.parent is not None and e.parent.has_class('hd'))
        title = head.text() if head is not None else None
        up = pb.parent
        while title is None and up is not None:     # the Results section's archive step has no header
            if up.tag == 'section' and up.has_class('results'):
                title = 'Results'
            up = up.parent
        for i, li in enumerate(local):
            steps.append(build_step(li, i + 1, title))
            counted.add(li.attrs.get('data-step'))
    # a li.step outside any div.pb is unusual, but don't silently drop its capture
    for li in root.walk():
        if _is_step(li) and li.attrs.get('data-step') not in counted:
            steps.append(build_step(li, None))
            counted.add(li.attrs.get('data-step'))
    return steps


def text_hash(s):
    """FNV-1a, 32-bit, over the UTF-8 bytes: the same as textHash() in flow.js. It is how an override knows
    the output changed after it was set; change detection, not evidence (the evidence hash is sha256)."""
    h = 0x811c9dc5
    for c in (s or '').encode('utf-8'):
        h = ((h ^ c) * 0x01000193) & 0xffffffff
    return '%08x' % h


def live_images(cap):
    return [i for i in (cap or {}).get('images') or [] if isinstance(i, dict) and not i.get('gone')]


def step_capture_record(step, captures, stored_emits=None):
    cap = captures.get(step['id']) if step['id'] else None
    has_capture = isinstance(cap, dict)
    if not has_capture:
        cap = {}
    # a step with no data-pass and no data-fail — one typed into the page, until it is folded — has
    # no rule to miss: what it holds is "captured", never "no match"
    norule = step['pass_rx'] is None and step['fail_rx'] is None and not step.get('pass_pattern') and not step.get('fail_pattern')
    plain = lambda v: 'captured' if norule and v == 'no match' else v
    text = cap.get('text') or ''
    images = live_images(cap)
    derived = plain(derive_verdict(text, step['pass_rx'], step['fail_rx']))
    if derived == 'none' and images:
        derived = 'captured'                     # an image alone: nothing a rule can match
    # a verdict set by hand stands beside the derived one, never in its place
    ov = cap.get('override') if isinstance(cap.get('override'), dict) else None
    if ov:
        ov = dict(ov, verdict=normalize_stored_verdict(ov.get('verdict')), was=normalize_stored_verdict(ov.get('was')),
                  stale=ov.get('textHash') != text_hash(text))
    runs_out = []
    for run in (cap.get('runs') or []):
        if not isinstance(run, dict):
            continue
        rtext = run.get('text') or ''
        runs_out.append({
            'text': rtext, 'exit': run.get('exit', ''), 'at': run.get('at'),
            'verdict_stored': plain(normalize_stored_verdict(run.get('verdict'))),
            'verdict': plain(derive_verdict(rtext, step['pass_rx'], step['fail_rx'])),
        })
    return {
        'text': text, 'exit': cap.get('exit', ''), 'at': cap.get('at'),
        'note': cap.get('note') or '', 'verdict_stored': plain(normalize_stored_verdict(cap.get('verdict'))),
        'verdict': derived,
        'runs': runs_out, 'has_capture': has_capture,
        'emits': derive_emits(text, step.get('emit_rx') or {}),
        'emits_stored': dict((stored_emits or {}).get(step['id']) or {}),
        'override': ov, 'effective': ov['verdict'] if ov else derived, 'images': images,
    }


# ── drawings (SPEC.md §2.4) ───────────────────────────────────────────────

def extract_drawing_specs(root):
    specs, warnings = {}, []
    for fig in root.find(lambda e: e.tag == 'figure' and e.has_class('fv-drawing')):
        script_el = fig.first(lambda e: e.tag == 'script' and (e.attrs.get('type') or '') == 'application/json')
        if script_el is None:
            continue
        raw = script_el.raw()
        try:
            spec = json.loads(raw)
        except ValueError as e:
            warnings.append('a figure.fv-drawing spec did not parse as JSON: %s' % e)
            continue
        did = spec.get('id') if isinstance(spec, dict) else None
        if did:
            specs[did] = spec
    return specs, warnings


def find_by_id(items, item_id):
    for it in items or []:
        if isinstance(it, dict) and it.get('id') == item_id:
            return it
    return None


# <drawingId>/[<segmentId>/]<node|edge|step>:<id>  (SPEC.md §6)
_NOTE_KEY_RE = re.compile(r'^([^/]+)/(?:([^/]+)/)?(node|edge|step):(.+)$')


def resolve_note(specs, key):
    m = _NOTE_KEY_RE.match(key)
    if not m:
        return None, None, None, None, None
    drawing_id, segment_id, kind, elem_id = m.groups()
    spec = specs.get(drawing_id)
    scope = spec
    if spec is not None and segment_id:
        scope = (spec.get('segments') or {}).get(segment_id)
    if not scope:
        return drawing_id, segment_id, kind, elem_id, None
    label = None
    if kind == 'node':
        node = find_by_id(scope.get('nodes'), elem_id)
        label = node.get('label') if node else None
    elif kind == 'edge':
        edge = find_by_id(scope.get('edges'), elem_id)
        if edge:
            fr = find_by_id(scope.get('nodes'), edge.get('from'))
            to = find_by_id(scope.get('nodes'), edge.get('to'))
            label = '%s → %s' % (fr.get('label') if fr else edge.get('from'),
                                      to.get('label') if to else edge.get('to'))
    elif kind == 'step':
        for flow in scope.get('flows') or []:
            st = find_by_id(flow.get('steps'), elem_id)
            if st:
                label = st.get('say')
                break
    return drawing_id, segment_id, kind, elem_id, label


def build_notes_list(sidecar_notes, specs):
    out = []
    for key, val in (sidecar_notes or {}).items():
        if not isinstance(val, dict):
            continue
        drawing, segment, kind, elem_id, label = resolve_note(specs, key)
        out.append({'key': key, 'drawing': drawing, 'segment': segment, 'type': kind,
                     'id': elem_id, 'label': label, 'text': val.get('text') or '', 'at': val.get('at')})
    return out


# ── summary ───────────────────────────────────────────────────────────────

def fmt_size(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return '?'
    return '%.1f MB' % (n / 1048576.0) if n >= 1048576 else '%d KB' % max(1, round(n / 1024.0))


def summarize(records):
    counts = {'pass': 0, 'fail': 0, 'error': 0, 'no match': 0, 'captured': 0}
    captured_n = 0
    any_error = False
    by_hand = images = 0
    for _step, rec in records:
        v = rec.get('effective', rec['verdict'])
        by_hand += 1 if rec.get('override') else 0
        images += len(rec.get('images') or [])
        if v != 'none':
            captured_n += 1
            if v in counts:
                counts[v] += 1
        if v == 'error':
            any_error = True
        if any(r['verdict'] == 'error' for r in rec['runs']):
            any_error = True
    summary = {'captured': captured_n, 'pass': counts['pass'], 'fail': counts['fail'],
               'error': counts['error'], 'no_match': counts['no match'], 'no_rule': counts['captured'],
               'notes': 0, 'added': 0, 'todos_open': 0, 'by_hand': by_hand, 'images': images}
    return summary, any_error


def summary_line(summary):
    line = ('%d captured · pass %d · fail %d · error %d · no match %d · %d note%s'
            % (summary['captured'], summary['pass'], summary['fail'], summary['error'],
               summary['no_match'], summary['notes'], '' if summary['notes'] == 1 else 's'))
    if summary.get('no_rule'):
        line = line.replace(' · %d note' % summary['notes'], ' · no rule %d · %d note' % (summary['no_rule'], summary['notes']), 1)
    if summary.get('by_hand'):
        line += ' · %d set by hand' % summary['by_hand']
    if summary.get('images'):
        line += ' · %d image%s' % (summary['images'], '' if summary['images'] == 1 else 's')
    if summary.get('added'):
        line += ' · %d added in the page' % summary['added']
    if summary.get('todos_open'):
        line += ' · %d open to-do%s' % (summary['todos_open'], '' if summary['todos_open'] == 1 else 's')
    return line


CONCLUDE_NOTHING = ('error = the interpreter rejected the command, so the target was never asked '
                     '— the defect is in the playbook, conclude nothing about the system.')


# ── text rendering ────────────────────────────────────────────────────────

def render_lines(text, limit, show_all, prefix):
    if not text:
        return []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if not show_all and len(lines) > limit:
        rest = len(lines) - limit
        return [prefix + l for l in lines[:limit]] + ['  … %d more lines' % rest]
    return [prefix + l for l in lines]


def print_step_block(step, rec, show_all, out, folded=None):
    risk_disp = 'WRITE' if step['risk'] == 'w' else 'read'
    eff = rec.get('effective', rec['verdict'])
    shown = {'none': '—', 'no match': 'NO MATCH'}.get(eff, str(eff).upper()) + (' ✎' if rec.get('override') else '')
    if step.get('added'):
        a = step['added']
        out.append('+    %-5s %-5s  %-8s  %s' % (step['id'], risk_disp, shown, step['sentence']))
        local, _ = fmt_time(a.get('at'))
        out.append('  added %s in the page, %s · not in the source yet' % (
            local or '—', 'before the first step' if re.match(r'^[a-z]0$', str(a.get('after') or '')) else 'after %s' % a.get('after')))
        if step['command']:
            out.append('  $ %s' % step['command'])
    elif _NAMED.match(step['id'] or '') or re.match(r'^[a-z][0-9]+[a-z]$', step['id'] or ''):
        out.append('step %-5s %-5s  %-8s  %s' % (step['id'], risk_disp, shown, step['sentence']))
        if folded:
            local, _ = fmt_time(folded.get('at'))
            out.append('  folded in from the page (added %s)' % (local or '—'))
    else:
        n_disp = step['n'] if step['n'] is not None else '·'
        out.append('step %s  %-4s %-5s  %-8s  %s' % (n_disp, step['id'], risk_disp, shown, step['sentence']))
    ov = rec.get('override')
    if ov:
        local, iso = fmt_time(ov.get('at'))
        out.append('  ✎ set by hand %s, derived %s: "%s"%s' % (
            local or '—', {'none': 'none', 'no match': 'NO MATCH'}.get(rec['verdict'], str(rec['verdict']).upper()),
            ov.get('reason') or '', '   (the output changed after it was set)' if ov.get('stale') else ''))
    has_text = bool((rec['text'] or '').strip())
    if has_text and rec['verdict_stored'] != rec['verdict']:
        # pasted before the fold gave the step a rule: it was captured then, not a miss
        was = 'captured' if folded and rec['verdict_stored'] == 'no match' else rec['verdict_stored']
        out.append('  stored %s → now %s' % (was, rec['verdict']))
    for w in step['warnings']:
        out.append('  warning: %s' % w)
    if rec['at'] or has_text:
        local, iso = fmt_time(rec['at'])
        exit_disp = rec['exit'] if rec['exit'] not in (None, '') else '—'
        if local:
            out.append('  exit %s · captured %s (%s)' % (exit_disp, local, iso))
        else:
            out.append('  exit %s · captured —' % exit_disp)
    for name, val in rec['emits'].items():
        was = rec['emits_stored'].get(name)
        out.append('  %s -> %s=%s%s' % (step['id'], name, val,
                   '' if was in (None, val) else '   (stored %s, re-derived from the capture)' % was))
    for name in rec['emits_stored']:
        if name not in rec['emits']:
            out.append('  %s -> %s no longer matches the capture (stored %s)' % (step['id'], name, rec['emits_stored'][name]))
    if rec['note']:
        out.append('  note: %s' % rec['note'])
    for k, im in enumerate(rec.get('images') or [], 1):
        where = im.get('path') or im.get('file') or '?'
        out.append('  image  %s·%d  %s  %sx%s  %s%s%s' % (
            step['id'], k, where, im.get('w', '?'), im.get('h', '?'), fmt_size(im.get('bytes')),
            '  "%s"' % im['caption'] if im.get('caption') else '',
            ('  compressed from %s' % fmt_size((im.get('src') or {}).get('bytes'))) if im.get('src') else ''))
        if im.get('local'):
            out.append('         only in the browser that took it: serve the folder and open the page to bring it to disk')
        elif im.get('path') and not os.path.isfile(im['path']):
            out.append('         not on disk at that path')
    out.extend(render_lines(rec['text'], 40, show_all, '  | '))
    for i, run in enumerate(rec['runs'], 1):
        rlocal, riso = fmt_time(run['at'])
        when = rlocal or riso or '—'
        out.append('  run %d  %s  %s' % (i, when, run['verdict']))
        rhas_text = bool((run['text'] or '').strip())
        if rhas_text and run['verdict_stored'] != run['verdict']:
            out.append('    stored %s → now %s' % (run['verdict_stored'], run['verdict']))
        for l in render_lines(run['text'], 5, show_all, '  | '):
            out.append('  ' + l)


def print_orphaned_block(orphan_ids, captures, show_all, out):
    if not orphan_ids:
        return
    out.append('')
    out.append("orphaned (in the sidecar, no matching step in this file — renamed or removed?)")
    for oid in orphan_ids:
        cap = captures.get(oid) or {}
        text = cap.get('text') or ''
        stored = normalize_stored_verdict(cap.get('verdict'))
        local, iso = fmt_time(cap.get('at'))
        when = ('%s (%s)' % (local, iso)) if local else (cap.get('at') or '—')
        out.append('orphan  %s  stored %s  captured %s' % (oid, stored, when))
        out.extend(render_lines(text, 40, show_all, '  | '))


def print_notes_block(notes_list, show_all, out):
    if not notes_list:
        return
    out.append('')
    out.append('notes')
    for n in notes_list:
        local, iso = fmt_time(n['at'])
        when = ('%s (%s)' % (local, iso)) if local else (n['at'] or '—')
        label = n['label'] if n['label'] else '(unresolved — drawing, segment or id not found)'
        out.append('note  %s  %s  %s' % (n['key'], label, when))
        out.extend(render_lines(n['text'], 40, show_all, '  | '))


# ── JSON assembly ─────────────────────────────────────────────────────────

def build_json(doc, sidecar_path, sidecar, records, orphan_ids, captures, notes_list, summary,
               todos=None, removed=None):
    steps_json = []
    for step, rec in records:
        capture_obj = None
        if rec['has_capture']:
            capture_obj = {'text': rec['text'], 'exit': rec['exit'], 'at': rec['at'],
                            'note': rec['note'], 'verdict_stored': rec['verdict_stored'],
                            'verdict': rec['verdict'], 'effective': rec.get('effective', rec['verdict'])}
            if rec.get('override'):
                capture_obj['override'] = rec['override']
            if rec.get('images'):
                capture_obj['images'] = rec['images']
        entry = {'id': step['id'], 'n': step['n'], 'risk': step['risk'],
                 'sentence': step['sentence'], 'command': step['command'],
                 'capture': capture_obj, 'runs': rec['runs']}
        if step.get('emit_rx') or rec['emits_stored']:     # only a step that emits says so
            entry.update(emits=rec['emits'], emits_stored=rec['emits_stored'])
        if step.get('added'):                               # typed into the page, not in the source yet
            entry['added'] = {'after': step['added'].get('after'), 'at': step['added'].get('at')}
        steps_json.append(entry)
    orphaned_json = []
    for oid in orphan_ids:
        cap = captures.get(oid) or {}
        runs = [{'text': r.get('text') or '', 'exit': r.get('exit', ''), 'at': r.get('at'),
                 'verdict_stored': normalize_stored_verdict(r.get('verdict')), 'verdict': None}
                for r in (cap.get('runs') or []) if isinstance(r, dict)]
        orphaned_json.append({
            'id': oid, 'hint': 'no step with this id in the HTML — was it renamed or removed?',
            'capture': {'text': cap.get('text') or '', 'exit': cap.get('exit', ''), 'at': cap.get('at'),
                        'note': cap.get('note') or '',
                        'verdict_stored': normalize_stored_verdict(cap.get('verdict')), 'verdict': None},
            'runs': runs,
        })
    return {'doc': doc, 'sidecar': sidecar_path, 'savedAt': sidecar.get('savedAt'),
            'steps': steps_json, 'orphaned': orphaned_json, 'notes': notes_list,
            'todos': todo_rows(todos or {}),
            'removed': [dict(a, id=rid) for rid, a in (removed or [])], 'summary': summary}


# ── no-sidecar guidance ───────────────────────────────────────────────────

def no_sidecar_message(sidecar_path, html_dir):
    return (
        'flowviz-captures: no sidecar at %s\n\n'
        "This deliverable was likely opened straight from Finder (file://), so whatever\n"
        "was typed into it only ever reached that browser tab's storage, never disk.\n\n"
        'Either serve the folder so saves reach disk:\n'
        '    ~/Projects/FLOW_VIZ/bin/flowviz serve %s --open\n'
        'or, on the open page, click "Copy captures for agent" and paste that block back.'
    ) % (sidecar_path, html_dir)


# ── main ──────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='flowviz-captures.py',
        description="Read back a FLOW_VIZ deliverable's captures and drawing notes from its sidecar.")
    ap.add_argument('deliverable', help='path to the built .html deliverable')
    ap.add_argument('--json', action='store_true', help='emit one JSON object instead of text')
    ap.add_argument('--step', metavar='ID', help='show only this step')
    ap.add_argument('--all', action='store_true', help="don't truncate long captures")
    args = ap.parse_args(argv)

    html_path = args.deliverable
    try:
        with open(html_path, encoding='utf-8', errors='replace') as f:
            raw = f.read()
    except OSError as e:
        print('flowviz-captures: cannot read %s (%s)' % (html_path, e), file=sys.stderr)
        return 1

    root = parse_html(raw)
    doc = find_doc_id(raw, root)
    if not doc:
        print('flowviz-captures: no doc id in %s (no window.FLOW and no '
              '<meta name="flowviz-doc">) — refusing to guess.' % html_path, file=sys.stderr)
        return 2

    html_dir = os.path.dirname(os.path.abspath(html_path))
    sidecar_path = os.path.join(html_dir, doc + '.flow.json')
    if not os.path.isfile(sidecar_path):
        print(no_sidecar_message(sidecar_path, html_dir), file=sys.stderr)
        return 2
    try:
        with open(sidecar_path, encoding='utf-8') as f:
            sidecar = json.load(f)
    except (OSError, ValueError) as e:
        print('flowviz-captures: %s exists but is not readable JSON (%s)' % (sidecar_path, e), file=sys.stderr)
        return 2
    if not isinstance(sidecar, dict):
        print('flowviz-captures: %s does not hold a JSON object' % sidecar_path, file=sys.stderr)
        return 2

    html_steps = extract_steps(root)
    captures = sidecar.get('captures') or {}
    in_html = {s['id'] for s in html_steps if s['id']}
    added = sidecar.get('added') if isinstance(sidecar.get('added'), dict) else {}
    todos = sidecar.get('todos') if isinstance(sidecar.get('todos'), dict) else {}
    steps, place_warnings = place_added(html_steps, added, in_html)
    step_ids = {s['id'] for s in steps if s['id']}
    removed = sorted((k, v) for k, v in added.items() if isinstance(v, dict) and v.get('gone') and k not in in_html)
    gone_ids = {k for k, _ in removed}
    orphan_ids = [k for k in captures.keys() if k not in step_ids and k not in gone_ids]
    specs, spec_warnings = extract_drawing_specs(root)
    notes_list = build_notes_list(sidecar.get('notes') or {}, specs)

    records = [(s, step_capture_record(s, captures, sidecar.get('emits') or {})) for s in steps]
    for _s, rec in records:                      # absolute paths, so the agent can open each image
        for im in rec.get('images') or []:
            if im.get('file'):
                im['path'] = os.path.join(html_dir, im['file'])
    summary, any_error = summarize(records)
    summary['notes'] = len(notes_list)
    summary['added'] = sum(1 for s in steps if s.get('added'))
    summary['todos_open'] = sum(1 for t in todo_rows(todos) if not t.get('done'))

    if args.step is not None:
        match = next(((s, r) for s, r in records if s['id'] == args.step), None)
        if match is None:
            print("flowviz-captures: no step '%s' in %s" % (args.step, html_path), file=sys.stderr)
            return 1
        records_to_show = [match]
    else:
        records_to_show = records

    if args.json:
        out_obj = build_json(doc, sidecar_path, sidecar, records_to_show, orphan_ids, captures,
                              notes_list, summary, todos, removed)
        print(json.dumps(out_obj, indent=2, ensure_ascii=False))
        return 0

    lines = []
    for w in spec_warnings + place_warnings:
        lines.append('warning: %s' % w)
    playbook = object()
    for step, rec in records_to_show:
        if step.get('playbook') != playbook:
            playbook = step.get('playbook')
            lines.append(('' if lines else '') + ('playbook  %s' % playbook if playbook else 'steps outside a playbook'))
        print_step_block(step, rec, args.all, lines, folded=added.get(step['id']) if step['id'] in in_html else None)
    if args.step is None:
        print_orphaned_block(orphan_ids, captures, args.all, lines)
        print_removed_block(removed, captures, lines)
        print_notes_block(notes_list, args.all, lines)
        print_todos_block(todos, lines)
        lines.append('')
        lines.append(summary_line(summary))
        if any_error:
            lines.append(CONCLUDE_NOTHING)
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
