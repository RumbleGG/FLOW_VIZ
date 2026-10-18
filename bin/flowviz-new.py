#!/usr/bin/env python3
"""flowviz new — scaffold a report or a drawing into the folder the work is in.

    flowviz new report  "<claim with a verb>" --dir DIR [--name NAME] [--rows 4] [--steps 3] [--boxes 4] [--flows 0]
                        [--detail [BOXES]]
    flowviz new drawing "<claim with a verb>" --dir DIR [--name NAME] [--boxes 6] [--flows 0] [--steps N]

Drawings start without flows: boxes and connections, no walkthrough. Add --flows N only when the human
asked for a step-by-step walkthrough of the order of events.

--detail adds the detail slot under the spine: one more drawing for the code inside the system — one box
per class, one connection per call, one "Call order" flow (default 6 boxes, at most 20).

Writes DIR/NAME.src.html (NAME defaults to the folder's name, upper-cased) and refuses to overwrite
anything. Every slot carries the template's own words, so `flowviz audit` fails a scaffold that was
built but never written — on that, and on nothing else.
"""
import argparse
import datetime
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'template')
F = os.path.join(ROOT, 'bin', 'flowviz').replace(os.path.expanduser('~'), '~', 1)


def die(msg):
    print('flowviz new: ' + msg, file=sys.stderr)
    sys.exit(1)


def read(name):
    with open(os.path.join(TEMPLATE, name), encoding='utf-8') as f:
        return f.read()


def block(text, name):
    m = re.search(r'<!-- %s:begin -->\n(.*?)<!-- %s:end -->\n' % (name, name), text, re.S)
    if not m:
        die('template is missing the %s block' % name)
    return m.group(1)


def spec_of(text):
    m = re.search(r'(<script type="application/json">\n)(.*?)(\n</script>)', text, re.S)
    return m, json.loads(m.group(2))


def fmt(o, ind=0):
    """JSON with one line per box, connection and step — easy to read, easy to diff."""
    pad = '  ' * ind
    flat = lambda v: not isinstance(v, (dict, list)) or (
        isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v))
    if isinstance(o, dict):
        one = json.dumps(o, ensure_ascii=False, separators=(', ', ': '))
        if all(flat(v) for v in o.values()) and len(one) < 400:
            return one
        return '{\n' + ',\n'.join('%s  %s: %s' % (pad, json.dumps(k), fmt(v, ind + 1))
                                  for k, v in o.items()) + '\n' + pad + '}'
    if isinstance(o, list):
        if all(not isinstance(x, (dict, list)) for x in o):
            return json.dumps(o, ensure_ascii=False, separators=(', ', ': '))
        return '[\n' + ',\n'.join(pad + '  ' + fmt(x, ind + 1) for x in o) + '\n' + pad + ']'
    return json.dumps(o, ensure_ascii=False)


def gen_spec(tpl, n, flows, steps, max_cols, spec_id, title=None, max_steps=9, noun='box', flow_ids=None):
    """n boxes on a snaking grid, joined in a chain, walked by `flows` flows.
    Every string comes from the template, so every string still reads as unfilled."""
    first, mid, last = tpl['nodes'][0], tpl['nodes'][1], tpl['nodes'][-1]
    cols = min(n, max_cols)
    rows = -(-n // cols)

    def at(i):
        r, c = divmod(i, cols)
        return [cols - 1 - c if r % 2 else c, r]

    nodes = []
    for i in range(n):
        node = dict(first if i == 0 else last if i == n - 1 else mid)
        node.update(id='%s%d' % (noun, i + 1), label='%s %d' % (noun.title(), i + 1), at=at(i))
        nodes.append(node)
    edges = []
    for i in range(n - 1):
        e = dict(tpl['edges'][0])
        e.update(id='%s%d-%s%d' % (noun, i + 1, noun, i + 2), **{'from': '%s%d' % (noun, i + 1)}, to='%s%d' % (noun, i + 2))
        edges.append(e)
    walks = []
    for f in range(flows):
        fl = dict(tpl['flows'][0])
        fid, prefix = flow_ids[f] if flow_ids else ('flow%d' % (f + 1), 'f%ds' % (f + 1))
        fl.update(id=fid, steps=[
            dict(tpl['flows'][0]['steps'][0], id='%s%d' % (prefix, s + 1),
                 path=['%s%d' % (noun, s + 1), '%s%d' % (noun, s + 2)])
            for s in range(min(steps, n - 1, max_steps))])
        if not flow_ids:
            fl['label'] = 'Flow %d' % (f + 1)
        walks.append(fl)
    zones = []
    if n >= 3:
        zones.append(dict(tpl['zones'][0], cols=[1, cols - 1], rows=[0, rows - 1]))
    return {'id': spec_id, 'name': tpl['name'], 'title': title or tpl['title'], 'lede': tpl['lede'],
            'grid': {'cols': cols, 'rows': rows}, 'zones': zones, 'nodes': nodes, 'edges': edges,
            'flows': walks}


def put_spec(text, spec):
    m, _ = spec_of(text)
    return text[:m.start(2)] + fmt(spec) + text[m.end(2):]


def report(a, title, doc):
    t = read('report.src.html')
    row, pb, sec = block(t, 'row'), block(t, 'pb'), block(t, 'sec')
    ro, w = block(t, 'step-ro'), block(t, 'step-w')

    # rows are lettered a, b, c…; a step is its row's letter plus its number (the playbook is the last row)
    letter = chr(ord('a') + a.rows - 1)
    steps = []
    for i in range(1, a.steps + 1):
        shape = w if (i == a.steps and a.steps >= 2) else ro
        after = ' data-after="%s%d"' % (letter, i - 1) if i > 1 else ''
        steps.append(shape.replace('{{STEP_ID}}', '%s%d' % (letter, i)).replace('{{AFTER}}', after))
    playbook = pb.replace('<!-- steps -->\n', ''.join(steps)) if steps else ''

    rows = []
    for i in range(1, a.rows + 1):
        runs = bool(steps) and i == a.rows
        r = row.replace('{{ROW_ID}}', chr(ord('a') + i - 1)).replace('{{ROW_N}}', chr(ord('a') + i - 1))
        r = r.replace('{{ROW_KIND}}', 'test' if runs else 'context')
        r = r.replace('<!-- playbook -->\n', playbook if runs else '')
        # a header opens the rows, and another opens the playbook when it has company
        if i == 1 or (runs and a.rows > 1):
            r = sec + r
        rows.append(r)

    out = re.sub(r'<!-- sec:begin -->\n.*?<!-- sec:end -->\n', '', t, flags=re.S)
    out = re.sub(r'<!-- row:begin -->\n.*?<!-- row:end -->\n', lambda _: ''.join(rows), out, flags=re.S)
    out = re.sub(r'\n<!-- ═+ PLAYBOOK SHAPES.*?<!-- step-w:end -->\n', '\n', out, flags=re.S)
    _, tpl = spec_of(out)
    out = put_spec(out, gen_spec(tpl, a.boxes, a.flows, a.boxes - 1, 4, 'spine'))
    return detail_slot(out, a.detail)


def detail_slot(out, n):
    """The detail slot: one more drawing under the spine, on its own cap tier (≤20 boxes, one "Call
    order" flow of ≤20 steps) — n classes in a chain, or no slot at all when n is 0."""
    m = re.search(r'<!-- detail:begin -->\n(.*?)<!-- detail:end -->\n\n?', out, re.S)
    if not n:
        return out[:m.start()] + out[m.end():]
    part = m.group(1)
    dm, dtpl = spec_of(part)
    spec = gen_spec(dtpl, n, 1, n - 1, 5, dtpl['id'], max_steps=20, noun='class',
                    flow_ids=[(dtpl['flows'][0]['id'], 'c')])
    return out[:m.start()] + part[:dm.start(2)] + fmt(spec) + part[dm.end(2):] + '\n' + out[m.end():]


def drawing(a, title, doc):
    t = read('drawing.src.html')
    _, tpl = spec_of(t)
    steps = a.steps if a.steps is not None else a.boxes - 1
    return put_spec(t, gen_spec(tpl, a.boxes, a.flows, steps, 5, doc, title))


def main():
    argv = sys.argv[1:]
    if argv and argv[0] not in ('report', 'drawing', '-h', '--help'):
        argv = ['report'] + argv          # the pre-0.6 form: flowviz new "<claim>" --dir …
    ap = argparse.ArgumentParser(prog='flowviz new', description=__doc__.split('\n')[0])
    ap.add_argument('kind', choices=('report', 'drawing'))
    ap.add_argument('claim', help='the title: a claim with a verb, 70 characters at most')
    ap.add_argument('--dir', required=True, help='the folder the work is in')
    ap.add_argument('--name', help='file name without .src.html (default: the folder name, upper-cased)')
    ap.add_argument('--rows', type=int, default=4, help='report rows, 1-6 (default 4)')
    ap.add_argument('--steps', type=int, default=None,
                    help='report: playbook steps (default 3); drawing: steps per flow (default boxes-1, max 9)')
    ap.add_argument('--boxes', type=int, default=None, help='drawing boxes (default 6, max 12); report spine (default 4, max 9)')
    ap.add_argument('--flows', type=int, default=0,
                    help='flows, 0-3 (default 0: no walkthrough unless the human asked for one)')
    ap.add_argument('--detail', type=int, nargs='?', const=6, default=0, metavar='BOXES',
                    help='report: add the detail drawing under the spine, for the code inside the system '
                         '(default 6 boxes, 2-20)')
    a = ap.parse_args(argv)

    title = ' '.join(a.claim.split())
    if a.kind == 'report':
        a.steps = 3 if a.steps is None else a.steps
        a.boxes = 4 if a.boxes is None else a.boxes
        if not 1 <= a.rows <= 6:
            die('--rows must be 1-6: seven ideas is two reports')
        if not 2 <= a.boxes <= 9:
            die('--boxes must be 2-9 for a report spine')
        if not 0 <= a.steps <= 30:
            die('--steps must be 0-30')
        if not 0 <= a.flows <= 3:
            die('--flows must be 0-3')
        if a.detail and not 2 <= a.detail <= 20:
            die('--detail must be 2-20 boxes: a 21st class means a segment, or a second report')
    else:
        if a.detail:
            die('--detail is a report slot; a drawing page is one drawing')
        a.boxes = 6 if a.boxes is None else a.boxes
        if not 2 <= a.boxes <= 12:
            die('--boxes must be 2-12: a 13th box means a segment')
        if not 0 <= a.flows <= 3:
            die('--flows must be 0-3')
        if a.steps is not None and not 1 <= a.steps <= 9:
            die('--steps must be 1-9 per flow')

    folder = os.path.abspath(os.path.expanduser(a.dir))
    name = a.name or re.sub(r'[^A-Za-z0-9]+', '_', os.path.basename(folder)).strip('_').upper() or 'REPORT'
    doc = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    src = os.path.join(folder, name + '.src.html')
    for path in (src, src[:-len('.src.html')] + '.html'):
        if os.path.exists(path):
            die('%s already exists — not overwriting it. Pick another --name, or edit that file.' % path)
    os.makedirs(folder, exist_ok=True)

    body = report(a, title, doc) if a.kind == 'report' else drawing(a, title, doc)
    body = (body.replace('<title>{{TITLE}}</title>', '<title>%s</title>' % html.escape(title))
                .replace('{{TITLE}}', html.escape(title))
                .replace('{{DOC}}', doc)
                .replace('{{DATE}}', datetime.date.today().isoformat()))
    with open(src, 'w', encoding='utf-8') as f:
        f.write(body)

    what = ('%d row%s · %d step%s · spine drawing %d boxes%s' % (a.rows, '' if a.rows == 1 else 's', a.steps,
            '' if a.steps == 1 else 's', a.boxes, ' · detail drawing %d boxes' % a.detail if a.detail else '')
            if a.kind == 'report'
            else '%d boxes · %s' % (a.boxes, '%d flow%s' % (a.flows, '' if a.flows == 1 else 's') if a.flows else 'no flows'))
    print('created %s  (%s · doc %s · %s)' % (src, a.kind, doc, what))
    if len(title) > 70:
        print('  note: the title is %d characters; the cap is 70.' % len(title))
    print('next: write every slot — the audit fails on any template words left — then')
    print('  %s build %s' % (F, src.replace(os.path.expanduser('~'), '~')))


if __name__ == '__main__':
    main()
