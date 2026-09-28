#!/usr/bin/env python3
"""flowviz new — scaffold a report or a drawing into the folder the work is in.

    flowviz new report  "<claim with a verb>" --dir DIR [--name NAME] [--rows 4] [--steps 3] [--boxes 4]
    flowviz new drawing "<claim with a verb>" --dir DIR [--name NAME] [--boxes 6] [--flows 1] [--steps N]

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
F = '~/Projects/FLOW_VIZ/bin/flowviz'


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


def gen_spec(tpl, n, flows, steps, max_cols, spec_id, title=None):
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
        node.update(id='box%d' % (i + 1), label='Box %d' % (i + 1), at=at(i))
        nodes.append(node)
    edges = []
    for i in range(n - 1):
        e = dict(tpl['edges'][0])
        e.update(id='box%d-box%d' % (i + 1, i + 2), **{'from': 'box%d' % (i + 1)}, to='box%d' % (i + 2))
        edges.append(e)
    walks = []
    for f in range(flows):
        fl = dict(tpl['flows'][0])
        fl.update(id='flow%d' % (f + 1), label='Flow %d' % (f + 1), steps=[
            dict(tpl['flows'][0]['steps'][0], id='f%ds%d' % (f + 1, s + 1),
                 path=['box%d' % (s + 1), 'box%d' % (s + 2)])
            for s in range(min(steps, n - 1, 9))])
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
    row, pb = block(t, 'row'), block(t, 'pb')
    ro, w = block(t, 'step-ro'), block(t, 'step-w')

    steps = []
    for i in range(1, a.steps + 1):
        shape = w if (i == a.steps and a.steps >= 2) else ro
        after = ' data-after="s%d"' % (i - 1) if i > 1 else ''
        steps.append(shape.replace('{{STEP_ID}}', 's%d' % i).replace('{{AFTER}}', after))
    playbook = pb.replace('<!-- steps -->\n', ''.join(steps)) if steps else ''

    rows = []
    for i in range(1, a.rows + 1):
        r = row.replace('{{ROW_ID}}', 'r%d' % i).replace('{{ROW_N}}', str(i))
        r = r.replace('<!-- playbook -->\n', playbook if (i == a.rows) else '')
        rows.append(r)

    out = re.sub(r'<!-- row:begin -->\n.*?<!-- row:end -->\n', lambda _: ''.join(rows), t, flags=re.S)
    out = re.sub(r'\n<!-- ═+ PLAYBOOK SHAPES.*?<!-- step-w:end -->\n', '\n', out, flags=re.S)
    _, tpl = spec_of(out)
    out = put_spec(out, gen_spec(tpl, a.boxes, 1, a.boxes - 1, 4, 'spine'))
    return out


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
    ap.add_argument('--flows', type=int, default=1, help='drawing flows, 1-3 (default 1)')
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
    else:
        a.boxes = 6 if a.boxes is None else a.boxes
        if not 2 <= a.boxes <= 12:
            die('--boxes must be 2-12: a 13th box means a segment')
        if not 1 <= a.flows <= 3:
            die('--flows must be 1-3')
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

    what = ('%d row%s · %d step%s · spine drawing %d boxes' % (a.rows, '' if a.rows == 1 else 's', a.steps,
            '' if a.steps == 1 else 's', a.boxes) if a.kind == 'report'
            else '%d boxes · %d flow%s' % (a.boxes, a.flows, '' if a.flows == 1 else 's'))
    print('created %s  (%s · doc %s · %s)' % (src, a.kind, doc, what))
    if len(title) > 70:
        print('  note: the title is %d characters; the cap is 70.' % len(title))
    print('next: write every slot — the audit fails on any template words left — then')
    print('  %s build %s' % (F, src.replace(os.path.expanduser('~'), '~')))


if __name__ == '__main__':
    main()
