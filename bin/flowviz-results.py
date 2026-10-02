#!/usr/bin/env python3
"""flowviz results — start the Results section once the human has run the playbook.

    flowviz results <report>.src.html [--archive-to DIR]

Reads what the human pasted (the sidecar beside the report), re-derives every verdict, and works out
the outcome: blocked if a command was rejected, failed if the target said no, passed if every step
passed, inconclusive otherwise. Then it inserts a Results section at the top of the source with the
outcome chip and counts filled in, a results drawing started from the spine drawing's boxes, and one
gated step that moves the finished folder into the archive. You write the claim, the summary, the
next actions, and mark on the drawing where it passed or failed. An existing Results section is never
overwritten.
"""
import argparse
import datetime
import html
import importlib.util
import json
import os
import re
import shlex
import sys

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'template')
F = '~/Projects/FLOW_VIZ/bin/flowviz'


def die(msg, code=1):
    print('flowviz results: ' + msg, file=sys.stderr)
    sys.exit(code)


def captures_module():
    spec = importlib.util.spec_from_file_location('fvcaptures', os.path.join(ROOT, 'bin', 'flowviz-captures.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tilde(path):
    home = os.path.expanduser('~')
    if path == home:
        return '~'
    if path.startswith(home + os.sep):
        return '~/' + shlex.quote(path[len(home) + 1:])
    return shlex.quote(path)


def main():
    ap = argparse.ArgumentParser(prog='flowviz results', description=__doc__.split('\n')[0])
    ap.add_argument('src', help='the report .src.html whose playbook the human has run')
    ap.add_argument('--archive-to', help='where finished work goes (default: ~/Archive, else ~/Archives)')
    a = ap.parse_args()

    src_path = os.path.abspath(a.src)
    if not os.path.exists(src_path):
        die('no such file: %s' % a.src)
    text = open(src_path, encoding='utf-8').read()
    if re.search(r'<section\b[^>]*class="[^"]*\bresults\b', text):
        die('%s already has a Results section. Edit it; this command never overwrites one.' % a.src)
    if 'name="flowviz-kind" content="drawing"' in text:
        die('Results belong to reports; a drawing page has no playbook to report on.')

    m = captures_module()
    root = m.parse_html(text)
    doc = m.find_doc_id(text, root)
    if not doc:
        die('no <meta name="flowviz-doc"> in the source — refusing to guess the sidecar.')
    folder = os.path.dirname(src_path)
    sidecar = os.path.join(folder, doc + '.flow.json')
    if not os.path.exists(sidecar):
        print(m.no_sidecar_message(sidecar, folder), file=sys.stderr)
        sys.exit(2)
    state = json.load(open(sidecar, encoding='utf-8')) or {}
    captures = state.get('captures') or {}

    # a rollback row's steps only run when something went wrong: "not run" there is not missing
    kind_of = {}
    for row in root.find(lambda e: e.tag == 'details' and e.has_class('row')):
        for li in row.find(lambda e: e.tag == 'li' and e.has_class('step')):
            kind_of[li.attrs.get('data-step')] = row.attrs.get('data-kind')
    steps = m.extract_steps(root)
    if not steps:
        die('this report has no checklist steps, so there is nothing to report results on.')
    rows = [(s, m.step_capture_record(s, captures)) for s in steps]
    count = {'pass': 0, 'fail': 0, 'error': 0, 'no match': 0, 'none': 0, 'skipped': 0}
    for s, r in rows:
        v = r['verdict']
        if v == 'none' and kind_of.get(s['id']) == 'rollback':
            v = 'skipped'
        count[v] = count.get(v, 0) + 1

    def first(verdict):
        return next(((s, r) for s, r in rows if r['verdict'] == verdict), None)
    def label(s):   # a step is named by its id (b4); an older report's ids fall back to its counter
        return s['id'] if re.match(r'^[a-z][0-9]+$', s['id'] or '') else 'step %s' % s['n']
    hit = first('error')
    if hit:
        outcome, chip, chip_text = 'blocked', 'warn', 'Blocked at %s' % label(hit[0])
    elif first('fail'):
        hit = first('fail')
        outcome, chip, chip_text = 'fail', 'bad', 'Failed at %s' % label(hit[0])
    elif count['pass'] and not count['no match'] and not count['none']:
        outcome, chip, chip_text = 'pass', 'ok', 'Passed %d of %d steps' % (count['pass'], count['pass'])
    else:
        hit = first('no match') or first('none')
        outcome, chip = 'inconclusive', 'warn'
        chip_text = ('No match at %s' % label(hit[0])) if hit and hit[1]['verdict'] == 'no match' \
            else '%d step%s not run' % (count['none'], '' if count['none'] == 1 else 's')
    words = {'pass': 'pass', 'fail': 'fail', 'error': 'error', 'no match': 'no match', 'none': 'not run',
             'skipped': 'rollback not needed'}
    counts = '%d steps: ' % len(rows) + ', '.join('%d %s' % (count[k], w) for k, w in words.items() if count[k])

    # the diagram starts from the spine drawing: same boxes, no flows, nothing marked yet
    tpl = open(os.path.join(TEMPLATE, 'results.src.html'), encoding='utf-8').read()
    spine = root.first(lambda e: e.has_class('spine'))
    fig = spine.first(lambda e: e.tag == 'figure' and e.has_class('fv-drawing')) if spine else None
    base = None
    if fig is not None:
        sc = fig.first(lambda e: e.tag == 'script')
        try:
            base = json.loads(sc.raw()) if sc is not None else None
        except json.JSONDecodeError:
            base = None
    placeholders = json.loads(re.search(r'<!-- results-spec\n(.*?)\n-->', tpl, re.S).group(1))
    if base:
        spec = {'id': 'results', 'name': base.get('name', 'Results'),
                'title': placeholders['title'], 'lede': placeholders['lede'],
                'grid': base.get('grid'), 'zones': base.get('zones', []),
                'nodes': [{k: v for k, v in n.items() if k != 'segment'} for n in base.get('nodes', [])],
                'edges': base.get('edges', []), 'flows': []}
    else:
        spec = placeholders['fallback']
    fmt = _loader_fmt()
    archive = os.path.abspath(os.path.expanduser(a.archive_to)) if a.archive_to else next(
        (p for p in (os.path.expanduser('~/Archive'), os.path.expanduser('~/Archives')) if os.path.isdir(p)),
        os.path.expanduser('~/Archive'))
    name = os.path.basename(folder)
    dest = os.path.join(archive, name)
    cmd = 'mv %s %s && ls -d %s' % (tilde(folder), tilde(dest), tilde(dest))
    tail = os.path.basename(archive) + '/' + name

    block = re.sub(r'<!-- results-spec\n.*?\n-->\n', '', tpl, count=1, flags=re.S)
    block = (block.replace('{{OUTCOME}}', outcome).replace('{{CHIP}}', chip)
                  .replace('{{CHIP_TEXT}}', html.escape(chip_text))
                  .replace('{{DATE}}', datetime.date.today().isoformat())
                  .replace('{{COUNTS}}', html.escape(counts))
                  .replace('{{RESULTS_SPEC}}', fmt(spec))
                  .replace('{{FOLDER}}', html.escape(tilde(folder)))
                  .replace('{{ARCHIVE}}', html.escape(tilde(archive)))
                  .replace('{{ARCHIVE_CMD}}', html.escape(cmd))
                  .replace('{{ARCHIVE_PASS}}', html.escape(r'\b' + re.escape(tail) + r'\b')))
    anchor = text.find('<!-- ══════════════ LAYER 1 — THE CARD')
    if anchor < 0:
        m2 = re.search(r'<body[^>]*>\n?', text)
        if not m2:
            die('no <body> in the source')
        anchor = m2.end()
    out = text[:anchor] + block + '\n' + text[anchor:]
    tmp = src_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(out)
    os.replace(tmp, src_path)

    print('results section added to %s' % a.src)
    print('  outcome  %s — %s (%s)' % (outcome, chip_text, counts))
    if hit:
        print('  at       %s  %s' % (label(hit[0]), hit[0]['sentence']))
    print('  archive  %s' % cmd)
    # what the human added in the page: the outcome above is the plan's, so say what it left out
    in_html = {x['id'] for x in steps}
    live = lambda d: {k: v for k, v in (d or {}).items() if isinstance(v, dict) and not v.get('gone')}
    unfolded = sorted(k for k in live(state.get('added')) if k not in in_html)
    if unfolded:
        print('  added    %s: added in the page, not in the outcome — flowviz fold first to count them'
              % ', '.join(unfolded))
    for k, t in sorted(live(state.get('todos')).items(), key=lambda kv: int(kv[0][1:]) if kv[0][1:].isdigit() else 0):
        if not t.get('done'):
            print('  to-do    %s %s: %s' % (k, '(do after: a Next item?)' if t.get('kind') == 'do'
                                              else '(add to write-up)', t.get('text') or ''))
    print('next: check the outcome, then write the claim, the summary and the next actions, and mark the')
    print('diagram — "result": "pass" | "fail" | "error" on the box or connection where it passed or failed.')
    print('  %s build %s && %s audit --browser %s' % (F, tilde(src_path), F, tilde(src_path[:-9] + '.html')))


def _loader_fmt():
    spec = importlib.util.spec_from_file_location('fvnew', os.path.join(ROOT, 'bin', 'flowviz-new.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.fmt


if __name__ == '__main__':
    main()
