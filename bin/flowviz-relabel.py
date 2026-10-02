#!/usr/bin/env python3
"""flowviz relabel — put a report's rows and steps on the naming convention, and move the human's state with them.

    flowviz relabel <report>.src.html [--dry-run]

Rows are lettered a, b, c… in the order they appear; a step is its row's letter plus its number in that
row (b1, b2…); a Results section's steps are r1, r2…. Every reference moves with its id: in the source,
the step's capture box, exit code, counters, note, verdict chip, data-after gate, {{step.NAME}} tokens and
captures["id"] labels; in the sidecar beside it, the captures, ticks, emits and open rows. The sidecar is
backed up first. The page keeps the map, so a browser's own copy of the state moves the next time the page
opens, and a tab still showing the old ids is refused when it tries to save over the new ones.
"""
import argparse
import datetime
import html
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = '~/Projects/FLOW_VIZ/bin/flowviz'
# every attribute whose value is a step id (the scaffold's step shapes, plus the gate)
STEP_ATTRS = ('data-step', 'data-cap', 'data-ec', 'data-cnt', 'data-at', 'data-run', 'data-rr',
              'data-note', 'data-vd', 'data-after')
TAG = re.compile(r'<([a-zA-Z][\w-]*)((?:\s+[^\s=>/]+(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+))?)*)\s*/?>')
ATTR = re.compile(r'([^\s=>/]+)(?:\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+))?')
ORD = re.compile(r'<span\b[^>]*\bclass="[^"]*\bord\b[^"]*"[^>]*>([^<]*)</span>')
CAPTURES = re.compile(r'captures\[(["\'])([^"\'\]]+)\1\]')
TOKEN = re.compile(r'(?<!\$)\{\{([A-Za-z0-9][\w-]*)\.([A-Z][A-Z0-9_]*)\}\}')
META = re.compile(r'<meta\s+name="flowviz-relabel"\s+content=(?:\'([^\']*)\'|"([^"]*)")\s*/?>\n?')
INSERTED = re.compile(r'^[a-z][0-9]+[a-z]$')


def die(msg, code=1):
    print('flowviz relabel: ' + msg, file=sys.stderr)
    sys.exit(code)


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'bin', file))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mask(text):
    """The source with comments, scripts and styles blanked, so a scan never reads them and every
    offset still points at the same character of the original."""
    blank = lambda s: re.sub(r'[^\n]', ' ', s)
    text = re.sub(r'<!--.*?-->', lambda m: blank(m.group(0)), text, flags=re.S)
    return re.sub(r'(<(script|style)\b[^>]*>)(.*?)(</\2\s*>)',
                  lambda m: m.group(1) + blank(m.group(3)) + m.group(4), text, flags=re.S | re.I)


def plan(doc):
    """Where every row and step belongs: [(old row id, letter)] in order, {old step id: new}, strays."""
    is_step = lambda e: e.tag == 'li' and e.has('step')
    rows, steps, stray, placed, seen = [], {}, [], set(), set()
    def put(li, new):
        old = li.attrs.get('data-step')
        if not old:
            die('a step has no data-step, so nothing it captured could be moved. Give it one first.')
        if old in seen:
            die('two steps share the id "%s". Tell them apart first; relabel moves state by id.' % old)
        seen.add(old)
        placed.add(id(li))
        steps[old] = new
    for i, r in enumerate(doc.find(lambda e: e.tag == 'details' and e.has('row'))):
        letter = chr(ord('a') + i)
        rows.append((r.attrs.get('data-row'), letter))
        n, sub = 0, ''
        for li in r.find(is_step):
            # a step folded in from the page sits between two numbers and keeps that place: b3a
            if INSERTED.match(li.attrs.get('data-step') or ''):
                sub = chr(ord(sub) + 1) if sub else 'a'
                put(li, '%s%d%s' % (letter, n, sub))
                continue
            n, sub = n + 1, ''
            put(li, '%s%d' % (letter, n))
    for res in doc.find(lambda e: e.tag == 'section' and e.has('results')):
        for n, li in enumerate(res.find(is_step), 1):
            put(li, 'r%d' % n)
    for li in doc.find(is_step):
        if id(li) not in placed:
            stray.append(li.attrs.get('data-step') or '?')
    return rows, steps, stray


def rewrite(text, rows, steps):
    """Every reference to a row or step id, moved at once (so b1 -> b2 and b2 -> b3 never collide)."""
    masked, edits = mask(text), []
    def val(m, a):  # (start, end, value) of one attribute's value, quotes excluded
        s = m.start(2) + a.start(2)
        q = a.group(2)[0] in '"\''
        return (s + 1, s + len(a.group(2)) - 1) if q else (s, s + len(a.group(2)))
    row_tags, row_i = [], 0
    old_rows = {o: n for o, n in rows if o}
    for m in TAG.finditer(masked):
        tag = m.group(1).lower()
        attrs = {a.group(1).lower(): a for a in ATTR.finditer(m.group(2)) if a.group(2)}
        klass = (attrs['class'].group(2).strip('"\'') if 'class' in attrs else '').split()
        if tag == 'details' and 'row' in klass:
            if row_i >= len(rows):
                die('the markup holds more rows than the page shows — is a row inside a comment or a script?')
            letter = rows[row_i][1]
            row_i += 1
            row_tags.append(m)
            if 'data-row' in attrs:
                s, e = val(m, attrs['data-row'])
                edits.append((s, e, letter))
            else:
                edits.append((m.end(1), m.end(1), ' data-row="%s"' % letter))
        for name in STEP_ATTRS:
            if name in attrs:
                s, e = val(m, attrs[name])
                if text[s:e] in steps:
                    edits.append((s, e, steps[text[s:e]]))
        if 'data-pb' in attrs:
            s, e = val(m, attrs['data-pb'])
            if text[s:e] in old_rows:
                edits.append((s, e, old_rows[text[s:e]]))
    for i, m in enumerate(row_tags):
        end = row_tags[i + 1].start() if i + 1 < len(row_tags) else len(masked)
        o = ORD.search(masked, m.end(), end)
        if o:
            edits.append((o.start(1), o.end(1), rows[i][1]))
    for rx, grp in ((CAPTURES, 2), (TOKEN, 1)):
        for m in rx.finditer(masked):
            if m.group(grp) in steps:
                edits.append((m.start(grp), m.end(grp), steps[m.group(grp)]))
    edits.sort()
    for a, b in zip(edits, edits[1:]):
        if a[1] > b[0]:
            die('two rewrites overlap near offset %d — the markup is not what relabel expects.' % b[0])
    out, last, moved = [], 0, 0
    for s, e, new in edits:
        out.append(text[last:s])
        out.append(new)
        moved += text[s:e] != new
        last = e
    out.append(text[last:])
    return ''.join(out), moved


def mentions(text, changed):
    """Old ids still named in prose — <code>push</code>, "step push" — which only a person can judge."""
    masked, hits = mask(text), []
    for old in changed:
        rx = re.compile(r'<code>\s*%s\s*</code>|\bsteps?\s+%s\b|\b%s\.[A-Z][A-Z0-9_]*\b' % ((re.escape(old),) * 3))
        for m in rx.finditer(masked):
            hits.append((masked.count('\n', 0, m.start()) + 1, re.sub(r'\s+', ' ', text[m.start():m.end()])))
    return sorted(set(hits))


def remap(d, keymap, clashes, where):
    """d with its keys renamed at once. A key no step owns any more keeps its place, unless a moved key
    lands on it; then it is kept beside it rather than lost."""
    out, rest = {}, []
    for k, v in d.items():
        if k in keymap:
            out[keymap[k]] = v
        else:
            rest.append((k, v))
    for k, v in rest:
        if k in out:
            clashes.append('%s["%s"] belonged to no step; kept as "%s~before-relabel"' % (where, k, k))
            k += '~before-relabel'
        out[k] = v
    return out


def write(path, content):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(prog='flowviz relabel', description=__doc__.split('\n')[0])
    ap.add_argument('src', help='the report .src.html to relabel')
    ap.add_argument('--dry-run', action='store_true', help='print the moves and write nothing')
    a = ap.parse_args()

    src_path = os.path.abspath(a.src)
    if not os.path.exists(src_path):
        die('no such file: %s' % a.src)
    if not src_path.endswith('.src.html'):
        die('relabel the source (<NAME>.src.html), then rebuild; the built page is regenerated from it.')
    text = open(src_path, encoding='utf-8').read()
    if 'name="flowviz-kind" content="drawing"' in text:
        die('a drawing page has no rows or steps to relabel.')

    audit = load('fvaudit', 'flowviz-audit.py')
    rows, steps, stray = plan(audit.parse(text))
    if stray:
        die('these steps sit outside a lettered row and the Results section, so they have no letter: %s.\n'
            'Move each into the row it belongs to, then run relabel again.' % ', '.join(stray))
    row_moves = [(o, n) for o, n in rows if o != n]
    step_moves = [(o, n) for o, n in steps.items() if o != n]
    new_text, moved = rewrite(text, rows, steps)
    rel = os.path.relpath(src_path)
    if new_text == text:
        print('%s is already on the convention: rows %s, steps %s. Nothing written.'
              % (rel, ' '.join(n for _, n in rows) or '(none)', ' '.join(steps.values()) or '(none)'))
        return

    at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    entry = {'at': at}
    if row_moves:
        entry['rows'] = {o: n for o, n in row_moves if o}
    if step_moves:
        entry['steps'] = dict(step_moves)
    history = []
    m = META.search(new_text)
    if m:
        try:
            history = json.loads(html.unescape(m.group(1) if m.group(1) is not None else m.group(2)))
        except ValueError:
            die('the page\'s flowviz-relabel meta is not valid JSON; restore it from git before relabelling again.')
    history.append(entry)
    raw = json.dumps(history, separators=(',', ':'))
    meta = "<meta name=\"flowviz-relabel\" content='%s'>\n" % (
        raw.replace('&', '&amp;').replace('<', '&lt;').replace("'", '&#39;'))
    if m:
        new_text = new_text[:m.start()] + meta + new_text[m.end():]
    else:
        k = re.search(r'<meta name="flowviz-(?:kind|doc)"[^>]*>\n', new_text)
        if not k:
            die('no <meta name="flowviz-doc"> in the source — is this a FLOW_VIZ report?')
        new_text = new_text[:k.end()] + meta + new_text[k.end():]

    print('%s%s' % ('dry run — nothing written · ' if a.dry_run else '', rel))
    if row_moves:
        print('  rows   ' + ' · '.join('%s -> %s' % (o or '(no id)', n) for o, n in row_moves))
    if step_moves:
        print('  steps  ' + ' · '.join('%s -> %s' % (o, n) for o, n in step_moves))
    print('  source %d reference%s moved' % (moved, '' if moved == 1 else 's'))

    # the sidecar: what the human pasted and ticked moves with the ids. It is read and checked before
    # anything is written; then the source goes first, because if the sidecar write failed after it,
    # the page's map would still move the state the next time it opened.
    cap = load('fvcaptures', 'flowviz-captures.py')
    doc_id = cap.find_doc_id(text, cap.parse_html(text))
    folder = os.path.dirname(src_path)
    sidecar = os.path.join(folder, (doc_id or '') + '.flow.json')
    data, counts, clashes = None, [], []
    if doc_id and os.path.exists(sidecar):
        try:
            data = json.load(open(sidecar, encoding='utf-8'))
        except ValueError as e:
            die('%s is not valid JSON (%s); nothing was written.' % (sidecar, e))
        smap = dict(steps)
        # a step added in the page and not yet folded hangs off its anchor: b3a moves with b3
        for aid in (data.get('added') or {}):
            m = INSERTED.match(aid) and re.match(r'^([a-z][0-9]+)([a-z])$', aid)
            if m and m.group(1) in smap and aid not in smap:
                smap[aid] = smap[m.group(1)] + m.group(2)
        omap = {o: n for o, n in rows if o}
        omap.update({'step:' + o: 'step:' + n for o, n in smap.items()})
        for t in (data.get('todos') or {}).values():
            if isinstance(t, dict):
                for f in ('ref', 'became'):
                    if t.get(f) in smap:
                        t[f] = smap[t[f]]
        if isinstance(data.get('added'), dict):
            for a_ in data['added'].values():
                if isinstance(a_, dict) and a_.get('after') in steps:
                    a_['after'] = steps[a_['after']]
        for key, keymap in (('captures', smap), ('steps', smap), ('emits', smap), ('open', omap), ('added', smap)):
            d = data.get(key)
            if isinstance(d, dict) and d:
                n = sum(1 for k in d if k in keymap and keymap[k] != k)
                data[key] = remap(d, keymap, clashes, key)
                if n:
                    counts.append('%d %s' % (n, {'steps': 'ticks', 'open': 'open', 'added': 'added steps'}.get(key, key)))
        data['savedAt'] = at
        data['relabel'] = at

    backup = None
    if not a.dry_run:
        write(src_path, new_text)
        if data is not None:
            bdir = os.path.join(folder, '.flowviz', 'state-backup')
            os.makedirs(bdir, exist_ok=True)
            backup = os.path.join(bdir, '%s.%s.json' % (doc_id, datetime.datetime.now(
                datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
            with open(sidecar, 'rb') as f_in, open(backup, 'wb') as f_out:
                f_out.write(f_in.read())
            write(sidecar, json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    if data is not None:
        print('  state  %s: %s' % (os.path.basename(sidecar),
              ', '.join(counts) + ' moved' if counts else 'nothing keyed by a moved id'))
        if backup:
            print('         backup %s' % os.path.relpath(backup))
    elif doc_id:
        print('  state  no %s yet — nothing pasted to move' % os.path.basename(sidecar))
    for c in clashes:
        print('  kept   ' + c)

    hits = mentions(new_text, [o for o, _ in step_moves])
    if hits:
        print('check by hand — the old ids are still named in prose:')
        for line, s in hits:
            print('  %s:%d  %s' % (rel, line, s))
    if not a.dry_run:
        print('next: rebuild, and reload any open copy of the page — a tab from before this refuses to save.')
        print('  %s build %s && %s audit --browser %s' % (F, rel, F, rel[:-9] + '.html'))


if __name__ == '__main__':
    main()
