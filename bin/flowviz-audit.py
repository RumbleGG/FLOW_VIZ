#!/usr/bin/env python3
"""flowviz audit — measure a report or a drawing against the standard. Exit 1 on any OVER or FAIL.

    flowviz audit <file>.html [--browser] [--json]

Every cap that can be read from the file is measured here, with no browser: the report caps from the
markup, the drawing caps from each spec. Then the author checks — unfilled slots (compared against the
templates' own words), paste safety of every command block, fragile verdict regexes, and the drawing
spec's ids, references, vocabulary and grid. Layout caps (screens at rest, crossings, labels shrunk to
fit) need a browser: --browser runs headless Chrome on ?audit=1 and reads the panel back.
"""
import argparse
import html
import html.parser
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'template')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source',
        'track', 'wbr'}

# ── a small DOM ──────────────────────────────────────────────────────────────


class El:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids = tag, dict(attrs), parent, []

    @property
    def cls(self):
        return (self.attrs.get('class') or '').split()

    def has(self, c):
        return c in self.cls

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
        parts = []

        def go(n):
            for k in n.kids:
                if isinstance(k, str):
                    parts.append(k)
                elif k.tag not in ('script', 'style', 'template'):
                    parts.append(' ')
                    go(k)
                    parts.append(' ')
        go(self)
        return ' '.join(''.join(parts).split())

    def raw(self):
        return ''.join(k if isinstance(k, str) else k.raw() for k in self.kids)

    def inside(self, pred):
        p = self.parent
        while p is not None:
            if pred(p):
                return True
            p = p.parent
        return False


class Tree(html.parser.HTMLParser):
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


def parse(text):
    t = Tree()
    t.feed(text)
    t.close()
    return t.root


def cls(*names):
    return lambda e: all(e.has(n) for n in names)


def words(s):
    return len((s or '').split())


def sentences_over_one(s):
    s = (s or '').strip()
    s = re.sub(r'[.!?]$', '', s)
    return bool(re.search(r'[.!?]\s', s))


# ── the verb heuristic ───────────────────────────────────────────────────────
VERBS = set('''
accept add allow answer apply arrive ask audit avoid become begin block break bring build call carry cause
change check choose clear close collect come commit compare complete confirm connect contain continue cost
create cut decide define delete deliver depend deploy describe draw drop enable end ensure explain expose fail
fall fetch fill find finish fit fix flow follow force get give go grow handle happen hit hold hide improve
include increase keep know land last lead leave let lift limit list live load lock lose make matter mean meet
merge miss move need open own pass pay place point prevent print prove publish pull push put reach read
receive reduce refuse release remove render repeat replace report require reset resolve respond rest restore
return reuse rewrite route run save say scale scaffold see send serve set settle show shrink sit skip slow sort
split stamp start stay stop store survive swap sync take talk tell test think throw time touch track travel
trigger trust try turn understand update use validate verify wait walk want warn win work wrap write
die hang crash stall leak lag spike reject deny cross succeed recover retry restart rotate expire rise
climb double halve beat cover ship roll speak drain queue land time-out break-even outgrow undo redo
stick drift slip overflow underflow corrupt duplicate deliver bounce
'''.split())
AUX = set('''
is are was were be been being am has have had do does did can could will would shall should may might must
isn't aren't wasn't weren't don't doesn't didn't can't won't cannot shouldn't wouldn't couldn't
'''.split())
IRREGULAR = set('''
ran went got took made found broke built sent held kept left lost met paid read said set shut sold spent
stood told thought won wrote came gave knew became began brought bought caught chose fell fought grew hit led
let rose saw shook shot shrank sat split spread stuck struck threw woke rebuilt overwrote undid
'''.split())


def has_verb(title):
    for raw in (title or '').split():
        w = raw.strip('.,:;!?()[]"\'`')
        # identifiers and acronyms are names, not verbs: FLOW_VIZ, STO, JWT, v0.6
        if not w or '_' in w or any(c.isdigit() for c in w) or (w.isupper() and len(w) > 1):
            continue
        w = w.lower()
        if not re.match(r"^[a-z][a-z'-]*$", w):
            continue
        if w in AUX or w in VERBS or w in IRREGULAR:
            return True
        stems = [w[:-1] if w.endswith('s') else None, w[:-2] if w.endswith('es') else None,
                 w[:-3] + 'y' if w.endswith('ies') else None, w[:-2] if w.endswith('ed') else None,
                 w[:-1] if w.endswith('ed') else None, w[:-3] if w.endswith('ing') else None,
                 w[:-3] + 'e' if w.endswith('ing') else None,
                 w[:-3] if re.search(r'(.)\1ed$', w) else None]
        if any(s in VERBS for s in stems if s):
            return True
    return False


# ── the report ───────────────────────────────────────────────────────────────
class Audit:
    def __init__(self):
        self.rows = []      # (section, label, actual, cap, status)

    def cap(self, section, label, actual, cap, ok):
        self.rows.append((section, label, str(actual), cap, 'ok' if ok else 'OVER'))

    def check(self, section, label, problems):
        self.rows.append((section, label, str(len(problems)), '0', 'ok' if not problems else 'FAIL'))
        for p in problems[:8]:
            self.rows.append((section, '  ' + p, '', '', 'why'))
        if len(problems) > 8:
            self.rows.append((section, '  … %d more' % (len(problems) - 8), '', '', 'why'))

    def unmeasured(self, section, label, how):
        self.rows.append((section, label, '', how, '--'))

    def note(self, section, label, detail):
        self.rows.append((section, label, detail, '', 'note'))

    def failed(self):
        return any(r[4] in ('OVER', 'FAIL') for r in self.rows)


def report_caps(a, doc):
    S = 'report'
    card = doc.first(cls('card'))
    h1 = card.first(lambda e: e.tag == 'h1') if card else None
    title = h1.text() if h1 else ''
    a.cap(S, 'title chars', len(title), '≤ 70', 0 < len(title) <= 70)
    a.cap(S, 'title contains a verb', 'yes' if has_verb(title) else 'no', 'a claim', has_verb(title))

    def slot(name):
        e = doc.first(lambda e: e.attrs.get('data-slot') == name)
        return e.text() if e else ''
    a.cap(S, 'verdict words', words(slot('verdict')), '≤ 50', words(slot('verdict')) <= 50)
    a.cap(S, 'so-what words', words(slot('sowhat')), '≤ 30', words(slot('sowhat')) <= 30)
    vit = doc.first(cls('vitals'))
    tiles = [k for k in vit.kids if isinstance(k, El)] if vit else []
    a.cap(S, 'vital tiles', len(tiles), '≤ 5', len(tiles) <= 5)
    nxt = card.first(cls('next')) if card else None
    items = nxt.find(lambda e: e.tag == 'li') if nxt else []
    a.cap(S, 'next items', len(items), '≤ 4', len(items) <= 4)
    longest = max([words(i.text()) for i in items] or [0])
    a.cap(S, 'longest next item (words)', longest, '≤ 14', longest <= 14)
    untagged = [i for i in items if not i.first(cls('badge'))]
    a.cap(S, 'untagged next items', len(untagged), '0', not untagged)

    spine = doc.first(cls('spine'))
    dias = spine.find(lambda e: e.has('dia') or e.has('mermaid') or e.has('fv-drawing')) if spine else []
    a.cap(S, 'diagrams in the spine', len(dias), '= 1', len(dias) == 1)

    rows = doc.find(lambda e: e.tag == 'details' and e.has('row'))
    a.cap(S, 'rows', len(rows), '≤ 6', len(rows) <= 6)
    summ = [r.first(lambda e: e.tag == 'summary') for r in rows]
    cl = [s.first(cls('cl')) for s in summ if s]
    longest = max([words(c.text()) for c in cl if c] or [0])
    a.cap(S, 'longest row summary (words)', longest, '≤ 14', longest <= 14)
    opened = [r for r in rows if 'open' in r.attrs]
    a.cap(S, 'rows open at load', len(opened), '≤ 1', len(opened) <= 1)
    secs = doc.find(lambda e: e.tag == 'h2' and e.has('sec'))
    a.cap(S, 'section headers', len(secs), '≤ 3', len(secs) <= 3)
    longest = max([words(h.text()) for h in secs] or [0])
    a.cap(S, 'longest section header (words)', longest, '≤ 4', longest <= 4)
    order = {id(e): i for i, e in enumerate(doc.walk())}
    first = order[id(secs[0])] if secs else None
    before = [r for r in rows if first is None or order[id(r)] < first]
    a.cap(S, 'rows before the first header', len(before), '0', not before)
    nokind = [r for r in rows if r.attrs.get('data-kind') not in ROW_KINDS]
    a.cap(S, 'rows with no kind', len(nokind), '0', not nokind)

    steps = doc.find(lambda e: e.tag == 'li' and e.has('step'))
    ds = [s.first(cls('ds')) for s in steps]
    longest = max([words(d.text()) for d in ds if d] or [0])
    a.cap(S, 'longest step sentence (words)', longest, '≤ 20', longest <= 20)
    multi = [s.attrs.get('data-step') for s, d in zip(steps, ds) if d and sentences_over_one(d.text())]
    a.cap(S, 'multi-sentence steps', len(multi), '0', not multi)
    norisk = [s for s in steps if s.attrs.get('data-risk') not in ('ro', 'w')]
    a.cap(S, 'steps with no risk tag', len(norisk), '0', not norisk)
    nogate = [s for s in steps if s.attrs.get('data-risk') == 'w' and not s.first(cls('ack'))]
    a.cap(S, 'write steps with no gate', len(nogate), '0', not nogate)

    rest = (words(card.text() if card else '') + sum(words(s.text()) for s in summ if s)
            + sum(words(h.text()) for h in secs))
    a.cap(S, 'words at rest', rest, '≤ 350', rest <= 350)
    a.unmeasured(S, 'screens at rest', 'needs layout: --browser')



def results_checks(a, doc):
    """A Results section, once the human has run the playbook: first on the page, an outcome,
    a claim, a summary, one drawing that marks where it passed or failed, next actions, and one
    gated step that archives the finished work."""
    res = doc.find(lambda e: e.tag == 'section' and e.has('results'))
    if not res:
        return
    S = 'results'
    if len(res) > 1:
        a.check(S, 'one Results section', ['this report has %d; keep one and edit it' % len(res)])
    r = res[0]
    order = {id(e): i for i, e in enumerate(doc.walk())}
    card = doc.first(cls('card'))
    ahead = card is None or order[id(r)] < order[id(card)]
    a.cap(S, 'results come before the card', 'yes' if ahead else 'no', 'first', ahead)
    outcome = r.attrs.get('data-outcome')
    a.cap(S, 'outcome', outcome or 'none', 'pass|fail|blocked|inconclusive', outcome in OUTCOMES)
    chip = r.first(cls('chip'))
    a.cap(S, 'outcome chip', 'yes' if chip else 'no', 'present', chip is not None)
    h2 = r.first(lambda e: e.tag == 'h2')
    title = h2.text() if h2 else ''
    a.cap(S, 'claim chars', len(title), '≤ 70', 0 < len(title) <= 70)
    a.cap(S, 'claim contains a verb', 'yes' if has_verb(title) else 'no', 'a claim', has_verb(title))
    summ = r.first(lambda e: e.attrs.get('data-slot') == 'summary')
    a.cap(S, 'summary words', words(summ.text() if summ else ''), '≤ 50', 0 < words(summ.text() if summ else '') <= 50)
    figs = r.find(lambda e: e.tag == 'figure' and e.has('fv-drawing'))
    a.cap(S, 'diagrams', len(figs), '= 1', len(figs) == 1)
    marks = []
    if figs:
        sc = figs[0].first(lambda e: e.tag == 'script' and e.attrs.get('type') == 'application/json')
        try:
            spec = json.loads(sc.raw() if sc else '')
            things = (spec.get('nodes') or []) + (spec.get('edges') or []) + \
                [st for f in spec.get('flows') or [] for st in f.get('steps') or []]
            marks = [x.get('result') for x in things if x.get('result') or x.get('fail')]
            marks = ['fail' if m is True else m for m in marks]
        except (json.JSONDecodeError, TypeError, AttributeError):
            marks = []
    a.cap(S, 'diagram marks a result', len(marks), '≥ 1', len(marks) >= 1)
    fits = {'pass': 'fail' not in marks and 'error' not in marks, 'fail': 'fail' in marks,
            'blocked': 'error' in marks, 'inconclusive': True}.get(outcome, True)
    a.cap(S, 'diagram agrees with the outcome', 'yes' if fits else 'no', 'yes', fits)
    nxt = r.first(cls('next'))
    items = nxt.find(lambda e: e.tag == 'li') if nxt else []
    a.cap(S, 'next items', len(items), '1 to 4', 1 <= len(items) <= 4)
    longest = max([words(i.text()) for i in items] or [0])
    a.cap(S, 'longest next item (words)', longest, '≤ 14', longest <= 14)
    untagged = [i for i in items if not i.first(cls('badge'))]
    a.cap(S, 'untagged next items', len(untagged), '0', not untagged)
    arch = r.find(lambda e: e.tag == 'li' and e.has('step') and 'data-archive' in e.attrs)
    gated = [x for x in arch if x.attrs.get('data-risk') == 'w' and x.first(cls('ack'))]
    a.cap(S, 'archive step, gated', len(gated), '= 1', len(arch) == 1 and len(gated) == 1)
    top = r.first(cls('top'))
    ds = [x.first(cls('ds')) for x in arch]
    rest = (words(top.text() if top else '') + words(title) + words(summ.text() if summ else '')
            + sum(words(i.text()) for i in items) + sum(words(d.text()) for d in ds if d))
    a.cap(S, 'words at rest', rest, '≤ 150', rest <= 150)
    a.unmeasured(S, 'results screens', 'needs layout: --browser')

# ── drawings ─────────────────────────────────────────────────────────────────
KINDS = {'client', 'edge', 'service', 'data', 'stream', 'external', 'threat'}
RESULTS = {'pass', 'fail', 'error'}
OUTCOMES = {'pass', 'fail', 'blocked', 'inconclusive'}
ROW_READ = {'context', 'finding', 'record'}
ROW_ACT = {'investigation', 'test', 'change', 'rollback'}
ROW_KINDS = ROW_READ | ROW_ACT | {'decision'}
MODES = {'sync', 'async'}
TONES = {'neutral', 'sync', 'async', 'ext', 'data', 'svc'}
TAGS = {'tl', 'tr', 'bl', 'br'}
ROUTES = {'h', 'v', 'hvh', 'vhv'}
ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
BOX_W, BOX_H = 0.36, 0.21        # half a box, in cells — the runtime's 172×56 on a 240×132 grid


def icon_names():
    path = os.path.join(TEMPLATE, 'icons.svg')
    if not os.path.exists(path):
        return None
    return set(re.findall(r'<symbol[^>]*\bid="i-([a-z0-9-]+)"', open(path, encoding='utf-8').read()))


def polyline(a, b, route):
    (ca, ra), (cb, rb) = a['at'], b['at']
    dc, dr = cb - ca, rb - ra
    kind = route or ('h' if dr == 0 else 'v' if dc == 0 else 'hvh' if abs(dc) >= abs(dr) else 'vhv')
    if kind in ('h', 'hvh'):
        s = 1 if dc > 0 else -1
        p0, p3 = (ca + s * BOX_W, ra), (cb - s * BOX_W, rb)
        if kind == 'h':
            return [p0, p3]
        mx = (p0[0] + p3[0]) / 2
        return [p0, (mx, ra), (mx, rb), p3]
    s = 1 if dr > 0 else -1
    p0, p3 = (ca, ra + s * BOX_H), (cb, rb - s * BOX_H)
    if kind == 'v':
        return [p0, p3]
    my = (p0[1] + p3[1]) / 2
    return [p0, (ca, my), (cb, my), p3]


def hits_box(pts, box):
    cx, cy = box['at']
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if abs(y1 - y2) < 1e-9 and cy - BOX_H < y1 < cy + BOX_H:
            if min(x1, x2) < cx + BOX_W and max(x1, x2) > cx - BOX_W:
                return True
        if abs(x1 - x2) < 1e-9 and cx - BOX_W < x1 < cx + BOX_W:
            if min(y1, y2) < cy + BOX_H and max(y1, y2) > cy - BOX_H:
                return True
    return False


def placeholders():
    """Every string a template spec or template page carries, as matchers. A string that ends in a
    number ("Box 1") matches its whole family ("Box 7"); {{TOKENS}} match anything."""
    exact, fams, page = set(), [], []
    for name in ('report.src.html', 'drawing.src.html'):
        path = os.path.join(TEMPLATE, name)
        if not os.path.exists(path):
            continue
        text = open(path, encoding='utf-8').read()
        m = re.search(r'<script type="application/json">\n(.*?)\n</script>', text, re.S)
        if m:
            for s in spec_strings(json.loads(m.group(1))):
                if '{{' in s:
                    continue
                f = re.match(r'^(.*\D)\d+$', s)
                if f:
                    fams.append(re.compile('^' + re.escape(f.group(1)) + r'\d+$'))
                else:
                    exact.add(s)
        page.append(parse(text))
    rpath = os.path.join(TEMPLATE, 'results.src.html')
    if os.path.exists(rpath):
        rtext = open(rpath, encoding='utf-8').read()
        m = re.search(r'<!-- results-spec\n(.*?)\n-->', rtext, re.S)
        if m:
            ph = json.loads(m.group(1))
            exact.update([ph['title'], ph['lede']] + spec_strings(ph['fallback']))
        rdoc = parse(rtext)
        # the archive step ships filled in (real paths), so its words are not placeholders
        for e in rdoc.find(cls('archive')):
            e.kids = []
        page.append(rdoc)
    return exact, fams, page


def spec_strings(spec, paths=False):
    out = []

    def add(path, v):
        if isinstance(v, str) and v.strip():
            out.append((path, v) if paths else v)
    for k in ('name', 'title', 'lede'):
        add(k, spec.get(k))
    for z in spec.get('zones') or []:
        add('zone %s label' % z.get('id'), z.get('label'))
    for n in spec.get('nodes') or []:
        for k in ('label', 'tech', 'peek'):
            add('box %s %s' % (n.get('id'), k), n.get(k))
        for f in n.get('facts') or []:
            add('box %s fact' % n.get('id'), f)
    for e in spec.get('edges') or []:
        for k in ('label', 'ms', 'peek'):
            add('connection %s %s' % (e.get('id'), k), e.get(k))
    for fl in spec.get('flows') or []:
        for k in ('label', 'summary'):
            add('flow %s %s' % (fl.get('id'), k), fl.get(k))
        for st in fl.get('steps') or []:
            for k in ('msg', 'say'):
                add('step %s %s' % (st.get('id'), k), st.get(k))
    return out


def canvas_checks(a, S, spec, root, max_boxes, icons, unfilled, exact, fams):
    nodes, edges, flows, zones = (spec.get(k) or [] for k in ('nodes', 'edges', 'flows', 'zones'))
    grid = spec.get('grid') or {}
    cols, rows = grid.get('cols', 0), grid.get('rows', 0)
    title, lede = spec.get('title') or '', spec.get('lede') or ''
    a.cap(S, 'title chars', len(title), '≤ 70', 0 < len(title) <= 70)
    a.cap(S, 'title contains a verb', 'yes' if has_verb(title) else 'no', 'a claim', has_verb(title))
    a.cap(S, 'lede words', words(lede), '≤ 30', words(lede) <= 30)
    a.cap(S, 'boxes', len(nodes), '≤ %d' % max_boxes, len(nodes) <= max_boxes)
    a.cap(S, 'zones', len(zones), '≤ 4', len(zones) <= 4)
    a.cap(S, 'flows', len(flows), '0 to 3', len(flows) <= 3)
    most = max([len(f.get('steps') or []) for f in flows] or [0])
    a.cap(S, 'longest flow (steps)', most, '≤ 9', most <= 9)
    says = [s.get('say') or '' for f in flows for s in f.get('steps') or []]
    a.cap(S, 'longest step (words)', max([words(s) for s in says] or [0]), '≤ 20',
          all(words(s) <= 20 for s in says))
    multi = [s for s in says if sentences_over_one(s)]
    a.cap(S, 'multi-sentence steps', len(multi), '0', not multi)
    msgs = [s.get('msg') or '' for f in flows for s in f.get('steps') or []]
    a.cap(S, 'longest step msg (chars)', max([len(m) for m in msgs] or [0]), '≤ 24', all(len(m) <= 24 for m in msgs))
    labels = [n.get('label') or '' for n in nodes]
    a.cap(S, 'longest box label (chars)', max([len(l) for l in labels] or [0]), '≤ 16', all(len(l) <= 16 for l in labels))
    techs = [n.get('tech') or '' for n in nodes]
    a.cap(S, 'longest tech (chars)', max([len(t) for t in techs] or [0]), '≤ 24', all(len(t) <= 24 for t in techs))
    elab = [e.get('label') or '' for e in edges]
    a.cap(S, 'longest connection label (chars)', max([len(l) for l in elab] or [0]), '≤ 16', all(len(l) <= 16 for l in elab))
    ems = [e.get('ms') or '' for e in edges]
    a.cap(S, 'longest connection ms (chars)', max([len(m) for m in ems] or [0]), '≤ 20', all(len(m) <= 20 for m in ems))
    peeks = [x.get('peek') or '' for x in nodes + edges]
    a.cap(S, 'longest peek (words)', max([words(p) for p in peeks] or [0]), '≤ 25', all(words(p) <= 25 for p in peeks))
    facts = [n.get('facts') or [] for n in nodes]
    a.cap(S, 'most facts on a box', max([len(f) for f in facts] or [0]), '≤ 3', all(len(f) <= 3 for f in facts))
    longf = max([len(x) for f in facts for x in f] or [0])
    a.cap(S, 'longest fact (chars)', longf, '≤ 24', longf <= 24)
    zl = max([len(z.get('label') or '') for z in zones] or [0])
    a.cap(S, 'longest zone label (chars)', zl, '≤ 28', zl <= 28)
    canvas = sum(words(l) for l in labels) + sum(words(z.get('label')) for z in zones)
    a.cap(S, 'words on canvas at rest', canvas, '≤ 60', canvas <= 60)

    # author checks on the spec
    bad_ids, refs, vocab, gridp, through = [], [], [], [], []
    seen = {}
    for kind, items in (('box', nodes), ('connection', edges), ('flow', flows), ('zone', zones)):
        for x in items:
            i = x.get('id')
            if not isinstance(i, str) or not ID.match(i):
                bad_ids.append('%s id %r is not [a-z0-9-]' % (kind, i))
            elif (kind, i) in seen:
                bad_ids.append('duplicate %s id "%s"' % (kind, i))
            seen[(kind, i)] = 1
    step_ids = [s.get('id') for f in flows for s in f.get('steps') or []]
    for i in step_ids:
        if not isinstance(i, str) or not ID.match(i):
            bad_ids.append('step id %r is not [a-z0-9-]' % (i,))
    for i in set(x for x in step_ids if step_ids.count(x) > 1):
        bad_ids.append('duplicate step id "%s"' % i)

    byid = {n.get('id'): n for n in nodes}
    pairs = set()
    for e in edges:
        for end in ('from', 'to'):
            if e.get(end) not in byid:
                refs.append('connection %s: %s "%s" is not a box' % (e.get('id'), end, e.get(end)))
        pairs.add((e.get('from'), e.get('to')))
        if e.get('mode', 'sync') not in MODES:
            vocab.append('connection %s: mode "%s"' % (e.get('id'), e.get('mode')))
        if e.get('route') and e['route'] not in ROUTES:
            vocab.append('connection %s: route "%s"' % (e.get('id'), e.get('route')))
    for x in nodes + edges + [s for f in flows for s in f.get('steps') or []]:
        if x.get('result') is not None and x.get('result') not in RESULTS:
            vocab.append('%s: result "%s" is not pass, fail or error' % (x.get('id'), x.get('result')))
    walked = set()
    for f in flows:
        for s in f.get('steps') or []:
            path = s.get('path') or []
            if len(path) < 2:
                refs.append('step %s: a path needs two boxes or more' % s.get('id'))
            for x, y in zip(path, path[1:]):
                if x not in byid or y not in byid:
                    refs.append('step %s: "%s" is not a box' % (s.get('id'), x if x not in byid else y))
                elif (x, y) not in pairs and (y, x) not in pairs:
                    refs.append('step %s: no connection joins %s and %s' % (s.get('id'), x, y))
                walked.add((x, y))
                walked.add((y, x))
    for n in nodes:
        if n.get('kind') not in KINDS:
            vocab.append('box %s: kind "%s"' % (n.get('id'), n.get('kind')))
        if icons is not None and n.get('icon') not in icons:
            vocab.append('box %s: icon "%s" is not in template/icons.svg' % (n.get('id'), n.get('icon')))
        at = n.get('at')
        if not (isinstance(at, list) and len(at) == 2 and all(isinstance(v, int) for v in at)):
            gridp.append('box %s: "at" must be [col, row]' % n.get('id'))
            continue
        if not (0 <= at[0] < cols and 0 <= at[1] < rows):
            gridp.append('box %s at %s is outside the %d×%d grid' % (n.get('id'), at, cols, rows))
        if n.get('segment') and (not root or n['segment'] not in (root.get('segments') or {})):
            refs.append('box %s: segment "%s" does not exist' % (n.get('id'), n.get('segment')))
        if n.get('ghost'):
            if root is None or spec is root:
                refs.append('box %s: ghosts belong inside segments' % n.get('id'))
            elif n['ghost'] not in {m.get('id') for m in root.get('nodes') or []}:
                refs.append('box %s: ghost "%s" is not a box of the parent drawing' % (n.get('id'), n['ghost']))
    cells = {}
    for n in nodes:
        at = tuple(n.get('at') or ())
        if at in cells:
            gridp.append('boxes %s and %s share cell %s' % (cells[at], n.get('id'), list(at)))
        cells[at] = n.get('id')
    for z in zones:
        if z.get('tone', 'neutral') not in TONES:
            vocab.append('zone %s: tone "%s"' % (z.get('id'), z.get('tone')))
        if z.get('tag', 'tl') not in TAGS:
            vocab.append('zone %s: tag "%s"' % (z.get('id'), z.get('tag')))
        c, r = z.get('cols') or [0, -1], z.get('rows') or [0, -1]
        if not (0 <= c[0] <= c[1] < cols and 0 <= r[0] <= r[1] < rows):
            gridp.append('zone %s spans outside the grid' % z.get('id'))
    if not refs and not gridp:
        for e in edges:
            a_, b_ = byid[e['from']], byid[e['to']]
            pts = polyline(a_, b_, e.get('route'))
            for n in nodes:
                if n is not a_ and n is not b_ and hits_box(pts, n):
                    through.append('connection %s runs through box %s' % (e.get('id'), n.get('id')))
    a.check(S, 'spec: ids', bad_ids)
    a.check(S, 'spec: references', refs)
    a.check(S, 'spec: vocabulary', vocab)
    a.check(S, 'spec: grid', gridp)
    a.check(S, 'spec: through a box', through)
    a.unmeasured(S, 'crossings, boxes hit, labels shrunk or crossed', 'needs layout: --browser')
    unused = [e.get('id') for e in edges if (e.get('from'), e.get('to')) not in walked] if flows else []
    if unused:
        a.note(S, 'unused connection', ', '.join(unused) + ' — no flow walks it')
    for path, s in spec_strings(spec, paths=True):
        if s in exact or any(f.match(s) for f in fams):
            unfilled.append('%s: %s' % (S, path))


def drawing_checks(a, doc, kind, exact, fams, unfilled):
    icons = icon_names()
    figs = doc.find(lambda e: e.tag == 'figure' and e.has('fv-drawing'))
    ids = []
    for fig in figs:
        sc = fig.first(lambda e: e.tag == 'script' and e.attrs.get('type') == 'application/json')
        try:
            spec = json.loads(sc.raw() if sc else '')
        except (json.JSONDecodeError, TypeError) as err:
            a.check('drawing', 'spec: parses', ['a drawing spec does not parse: %s' % err])
            continue
        sid = spec.get('id', '?')
        ids.append(sid)
        S = 'drawing %s' % sid
        small = fig.inside(cls('spine')) or fig.inside(lambda p: p.tag == 'section' and p.has('results'))
        canvas_checks(a, S, spec, spec, 9 if small else 12, icons, unfilled, exact, fams)
        for key, seg in (spec.get('segments') or {}).items():
            T = '%s › %s' % (S, key)
            if seg.get('parent') not in {n.get('id') for n in spec.get('nodes') or []}:
                a.check(T, 'spec: parent', ['segment %s: parent "%s" is not a box' % (key, seg.get('parent'))])
            canvas_checks(a, T, seg, spec, 12, icons, unfilled, exact, fams)
        depth = fig.first(cls('fv-depth'))
        if depth:
            tpl_depth = 'Layer 3 for this box: tables, logs and file:line citations, as long as it needs.'
            for sec in depth.find(lambda e: e.tag == 'section'):
                if sec.text() == tpl_depth:
                    unfilled.append('%s: depth for "%s"' % (S, sec.attrs.get('data-for')))
    dup = sorted(set(i for i in ids if ids.count(i) > 1))
    if dup:
        a.check('drawing', 'spec: ids', ['two drawings on one page share the id "%s"' % d for d in dup])
    if kind == 'drawing' and not figs:
        a.check('drawing', 'drawing present', ['a drawing page has no figure.fv-drawing'])
    return figs


# ── author checks on the page ────────────────────────────────────────────────
BOILERPLATE = '''
Get-Item : Cannot find path 'C:\\ops\\x.ps1' because it does not exist.
At line:1 char:1
+ CategoryInfo          : ObjectNotFound: (C:\\ops\\x.ps1:String) [Get-Item], ItemNotFoundException
+ FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetItemCommand
The term 'Get-Foo' is not recognized as the name of a cmdlet, function, script file, or operable program.
ParserError: Unexpected token '}' in expression or statement.
Missing closing '}' in statement block or type definition.
The string is missing the terminator: '.
A positional parameter cannot be found that accepts argument 'x'.
+ CategoryInfo          : PermissionDenied: (:) [], UnauthorizedAccessException
+ FullyQualifiedErrorId : UnauthorizedAccess
Exception calling "Invoke" with "0" argument(s): "Access is denied."
InvalidOperation: You cannot call a method on a null-valued expression.
+ CategoryInfo          : InvalidArgument: (:) [Set-Item], ParameterBindingException
+ CategoryInfo          : NotSpecified: (:) [], RemoteException
File C:\\ops\\x.ps1 cannot be loaded because running scripts is disabled on this system.
bash: foo: command not found
zsh: command not found: foo
bash: syntax error near unexpected token `fi'
bash: line 3: unexpected EOF while looking for matching `"'
ls: cannot access '/x': No such file or directory
curl: (7) Failed to connect to localhost port 8787 after 0 ms: Connection refused
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
SyntaxError: invalid syntax
IndentationError: unexpected indent
ModuleNotFoundError: No module named 'foo'
NameError: name 'foo' is not defined
FileNotFoundError: [Errno 2] No such file or directory: 'x'
PermissionError: [Errno 13] Permission denied: 'x'
'''.strip().splitlines()


def alternatives(pattern):
    out, depth, cur, esc, cls_ = [], 0, '', False, False
    for ch in pattern:
        if esc:
            cur += ch
            esc = False
            continue
        if ch == '\\':
            cur += ch
            esc = True
            continue
        if cls_:
            cls_ = ch != ']'
        elif ch == '[':
            cls_ = True
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == '|' and depth == 0:
            out.append(cur)
            cur = ''
            continue
        cur += ch
    out.append(cur)
    return [x for x in out if x]


def fragile(pattern):
    """An alternative that can match inside a word of real error boilerplate: `Full` inside
    `FullyQualifiedErrorId`. That is the match that turns a crashed command into a pass."""
    hits = []
    for alt in alternatives(pattern):
        try:
            rx = re.compile(alt, re.I)
        except re.error:
            continue
        for line in BOILERPLATE:
            for m in rx.finditer(line):
                s, e = m.span()
                if s == e:
                    continue
                w = lambda i: 0 <= i < len(line) and (line[i].isalnum() or line[i] == '_')
                if (w(s - 1) and w(s)) or (w(e) and w(e - 1)):
                    word = re.search(r'[\w-]*%s[\w-]*' % re.escape(line[s:e]), line[max(0, s - 40):e + 40])
                    hits.append('"%s" matches inside "%s"' % (alt, word.group(0) if word else line.strip()))
                    break
            if hits and hits[-1].startswith('"%s"' % alt):
                break
    return hits


def page_checks(a, doc, tpl_pages, unfilled):
    S = 'author checks'
    # unfilled slots: the same selectors on the templates and on the deliverable
    SEL = [
        ('status chip', lambda e: e.has('chip') and e.inside(cls('card'))),
        ('meta line', lambda e: e.has('meta') and e.inside(cls('card'))),
        ('verdict', lambda e: e.attrs.get('data-slot') == 'verdict'),
        ('results claim', lambda e: e.tag == 'h2' and e.inside(lambda p: p.tag == 'section' and p.has('results'))),
        ('results summary', lambda e: e.attrs.get('data-slot') == 'summary'),
        ('so what', lambda e: e.attrs.get('data-slot') == 'sowhat'),
        ('vital label', lambda e: e.has('l') and e.inside(cls('vitals'))),
        ('next item', lambda e: e.tag == 'li' and e.inside(cls('next'))),
        ('section header', lambda e: e.tag == 'h2' and e.has('sec')),
        ('row summary', lambda e: e.has('cl') and e.inside(lambda p: p.tag == 'details' and p.has('row'))),
        ('row body', lambda e: e.tag == 'p' and e.parent is not None and e.parent.has('in')
            and e.parent.parent is not None and e.parent.parent.tag == 'details' and e.parent.parent.has('row')),
        ('playbook title', lambda e: e.has('t') and e.inside(cls('hd'))),
        ('step sentence', lambda e: e.has('ds')),
        ('command', lambda e: e.tag == 'code' and e.inside(lambda p: p.has('cmd') and not p.has('fig'))),
        ('pass/fail line', lambda e: e.has('expect')),
        ('write gate', lambda e: e.has('gate')),
        ('why this step', lambda e: e.tag == 'p' and e.inside(cls('more'))),
    ]
    tpl = {}
    for p in tpl_pages:
        for name, pred in SEL:
            for e in p.find(pred):
                t = e.text()
                if t:
                    tpl.setdefault(name, set()).add(t)
        for e in p.find(lambda e: e.tag == 'textarea'):
            for k in ('data-pass', 'data-fail'):
                if e.attrs.get(k):
                    tpl.setdefault('verdict regex', set()).add(e.attrs[k])

    def matches(name, text):
        for t in tpl.get(name, ()):
            if '{{' in t:
                rx = '^' + re.sub(r'\\\{\\\{[A-Z_]+\\\}\\\}', '.+?', re.escape(t)) + '$'
                if re.match(rx, text):
                    return True
            elif t == text:
                return True
        return False
    for name, pred in SEL:
        for e in doc.find(pred):
            if matches(name, e.text()):
                where = e.inside(lambda p: p.tag == 'li' and p.has('step'))
                unfilled.append(name)
    for e in doc.find(lambda e: e.tag == 'textarea'):
        for k in ('data-pass', 'data-fail'):
            if e.attrs.get(k) and matches('verdict regex', e.attrs[k]):
                unfilled.append('%s of step %s' % (k, e.attrs.get('data-cap')))

    counted = {}
    for u in unfilled:
        u = re.sub(r'^(drawing [^:]+: )(box|connection|flow|step|zone) \S+ ', r'\1\2 ', u)
        counted[u] = counted.get(u, 0) + 1
    a.check(S, 'unfilled slots', ['%s%s' % (k, ' ×%d' % v if v > 1 else '') for k, v in counted.items()])

    mismatch = []
    for r in doc.find(lambda e: e.tag == 'details' and e.has('row')):
        k, rid = r.attrs.get('data-kind'), r.attrs.get('data-row')
        steps = r.find(lambda e: e.tag == 'li' and e.has('step'))
        if k is not None and k not in ROW_KINDS:
            mismatch.append('row %s: "%s" is not a row kind' % (rid, k))
        elif k in ROW_ACT and not steps and not r.find(lambda e: e.tag == 'label' and e.has('chk')):
            mismatch.append('row %s says "action · %s" but holds nothing to run or tick' % (rid, k))
        elif k in ROW_READ and steps:
            mismatch.append('row %s says "%s" but holds %d step%s — use an action kind'
                            % (rid, k, len(steps), '' if len(steps) == 1 else 's'))
    a.check(S, 'row kind matches its content', mismatch)

    cmds = doc.find(lambda e: e.has('cmd') and not e.has('fig'))
    lead, nonascii, span, blank = [], [], [], []
    for c in cmds:
        pre = c.first(lambda e: e.tag == 'pre')
        if not pre:
            continue
        where = c.first(lambda e: False)
        li = c
        while li is not None and not (li.tag == 'li' and li.has('step')):
            li = li.parent
        name = 'step %s' % li.attrs.get('data-step') if li is not None else 'a command block'
        code = pre.raw()
        code = html.unescape(re.sub(r'<[^>]+>', '', code)) if '<' in code else code
        lines = code.replace('\r', '').split('\n')
        body = [l for l in lines if l.strip()]
        if body and re.match(r'^\s*(#|//|<#|rem\b)', body[0], re.I):
            lead.append(name)
        bad = sorted(set(ch for ch in code if ord(ch) > 0x7F))
        if bad:
            nonascii.append('%s: %s' % (name, ' '.join('U+%04X %s' % (ord(ch), ch) for ch in bad[:4])))
        for l in lines:
            if re.search(r"@['\"]\s*$", l) or re.search(r'<<-?\s*[\'"]?\w+[\'"]?\s*$', l) or re.search(r'[`\\]\s*$', l):
                span.append('%s: %s' % (name, l.strip()[:60]))
                break
        first = next((i for i, l in enumerate(lines) if l.strip()), 0)
        last = max([i for i, l in enumerate(lines) if l.strip()] or [0])
        if any(not l.strip() for l in lines[first:last + 1]):
            blank.append(name)
    a.check(S, 'cmd: leading comment', lead)
    a.check(S, 'cmd: non-ASCII', nonascii)
    a.check(S, 'cmd: spans a line break', span)
    a.check(S, 'cmd: blank line', blank)
    frag = []
    for e in doc.find(lambda e: e.tag == 'textarea' and e.attrs.get('data-cap')):
        for k in ('data-pass', 'data-fail'):
            for h in fragile(e.attrs.get(k) or ''):
                frag.append('step %s %s: %s' % (e.attrs.get('data-cap'), k, h))
    a.check(S, 'cmd: fragile verdict regex', frag)


# ── the browser ──────────────────────────────────────────────────────────────
def chrome():
    for p in ('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
              '/Applications/Chromium.app/Contents/MacOS/Chromium'):
        if os.path.exists(p):
            return p
    return shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')


def browser_rows(a, path):
    S = 'measured in the browser'
    exe = chrome()
    if not exe:
        a.unmeasured(S, 'layout caps', 'no Chrome found: open the file with ?audit=1 and read the panel')
        return
    prof = tempfile.mkdtemp(prefix='flowviz-chrome-')
    url = 'file://' + os.path.abspath(path) + '?audit=1'
    cmd = [exe, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
           '--user-data-dir=' + prof, '--window-size=1440,900', '--virtual-time-budget=6000', '--dump-dom', url]
    # --dump-dom prints the page and then often never exits: read until </html>, then stop Chrome
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    os.set_blocking(proc.stdout.fileno(), False)
    out, deadline = b'', time.time() + 90
    try:
        while time.time() < deadline:
            chunk = proc.stdout.read(1 << 16)
            if chunk:
                out += chunk
                if b'</html>' in out[-4096:]:
                    break
            elif proc.poll() is not None:
                break
            else:
                time.sleep(0.05)
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        proc.wait()
        shutil.rmtree(prof, ignore_errors=True)
    dom = parse(out.decode('utf-8', 'replace'))
    panel = dom.first(lambda e: e.attrs.get('id') == 'flowAudit')
    if not panel:
        a.check(S, 'the ?audit=1 panel rendered', ['Chrome loaded the page but no #flowAudit panel appeared'])
        return
    layout = re.compile(r'screens|cross|through box|shrunk', re.I)
    for tr in panel.find(lambda e: e.tag == 'tr' and 'data-k' in e.attrs):
        label = tr.attrs['data-k']
        if not layout.search(label):
            continue
        cells = [c.text() for c in tr.kids if isinstance(c, El) and c.tag == 'td']
        ok = tr.attrs.get('data-ok') == '1'
        a.cap(S, label, cells[1] if len(cells) > 1 else '', cells[2] if len(cells) > 2 else '', ok)


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(prog='flowviz audit', description=__doc__.split('\n')[0])
    ap.add_argument('file', help='the built .html (a .src.html works for the static checks)')
    ap.add_argument('--browser', action='store_true', help='also measure the layout caps in headless Chrome')
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    o = ap.parse_args()
    if not os.path.exists(o.file):
        print('flowviz audit: no such file: %s' % o.file, file=sys.stderr)
        sys.exit(2)
    text = open(o.file, encoding='utf-8').read()
    doc = parse(text)
    km = re.search(r'<meta\s+name="flowviz-kind"\s+content="(\w+)"', text)
    kind = km.group(1) if km else 'report'
    version = open(os.path.join(ROOT, 'VERSION')).read().strip()

    a = Audit()
    exact, fams, tpl_pages = placeholders()
    unfilled = []
    if kind == 'report':
        report_caps(a, doc)
        results_checks(a, doc)
    drawing_checks(a, doc, kind, exact, fams, unfilled)
    if kind == 'drawing':
        a.unmeasured('page', 'screens at rest', 'needs layout: --browser')
    page_checks(a, doc, tpl_pages, unfilled)
    if o.browser:
        a.rows = [r for r in a.rows if r[4] != '--']
        browser_rows(a, o.file)

    code = 1 if a.failed() else 0
    if o.json:
        print(json.dumps({'file': o.file, 'kind': kind, 'flowviz': version, 'exit': code,
                          'rows': [dict(zip(('section', 'label', 'actual', 'cap', 'status'), r)) for r in a.rows]},
                         indent=2, ensure_ascii=False))
        sys.exit(code)
    print('flowviz audit  %s  (%s · standard %s)' % (o.file, kind, version))
    section = None
    for sec, label, actual, capt, status in a.rows:
        if sec != section:
            print('\n' + sec)
            section = sec
        if status == 'why':
            print('        %s' % label)
        elif status == 'note':
            print('  note  %-44s %s' % (label, actual))
        elif status == '--':
            print('  --    %-44s %s' % (label, capt))
        else:
            print('  %-5s %-44s %8s  %s' % (status, label, actual, capt))
    over = sum(1 for r in a.rows if r[4] == 'OVER')
    fail = sum(1 for r in a.rows if r[4] == 'FAIL')
    todo = sum(1 for r in a.rows if r[4] == '--')
    print('\nresult: %s' % ('clean' if not code else '%d over, %d failing check%s' % (over, fail, '' if fail == 1 else 's'))
          + (' · %d unmeasured (run with --browser)' % todo if todo else '')
          + (' → exit 1' if code else ''))
    sys.exit(code)


if __name__ == '__main__':
    main()
