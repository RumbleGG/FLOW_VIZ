#!/usr/bin/env python3
"""flowviz fold — write the steps a human added in the page into the source, under the ids they already have.

    flowviz fold <report>.src.html [--todo t2 ...] [--dry-run]

A step the human typed into the page after handover lives in the sidecar (added.b3a) until it is folded.
This writes each one into the source after the step it was added after, as an ordinary step cut from the
template: the same id, so what was pasted into it re-attaches on the next build; the human's sentence and
command; data-after chained, so the step that followed now waits on it. What only the agent can write is
left in the template's own words, so the audit blocks until it is written: the pass and fail lines and
their regexes, and for a write step the gate. --todo folds an "add to write-up" to-do as a step too, after
the step it is tied to. The sidecar is backed up first, and each folded addition is stamped. No id moves.
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
TEMPLATE = os.path.join(ROOT, 'template', 'report.src.html')
F = '~/Projects/FLOW_VIZ/bin/flowviz'
# the template's own words for what fold cannot know; the audit's unfilled-slot check finds them
PH_SENTENCE = ('State in one sentence what this step establishes.', 'State in one sentence what this step changes.')
PH_COMMAND = ('echo replace-with-the-command-that-writes', 'echo replace-with-the-command')
PH_WHY = '<p>Traps, fallbacks and <code>file:line</code> citations, as long as it needs.</p>'


def die(msg, code=1):
    print('flowviz fold: ' + msg, file=sys.stderr)
    sys.exit(code)


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'bin', file))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mask(text):
    """The source with comments, scripts and styles blanked, offsets unchanged (as relabel does)."""
    blank = lambda s: re.sub(r'[^\n]', ' ', s)
    text = re.sub(r'<!--.*?-->', lambda m: blank(m.group(0)), text, flags=re.S)
    return re.sub(r'(<(script|style)\b[^>]*>)(.*?)(</\2\s*>)',
                  lambda m: m.group(1) + blank(m.group(3)) + m.group(4), text, flags=re.S | re.I)


def steps_in(text):
    """[(id, start, end)] for every li.step in document order; end is just past its own </li>."""
    masked, out = mask(text), []
    for m in re.finditer(r'<li\b[^>]*>', masked):
        if not re.search(r'\bclass="[^"]*\bstep\b', m.group(0)):
            continue
        sid = re.search(r'\bdata-step="([^"]+)"', m.group(0))
        depth, end = 0, None
        for t in re.finditer(r'<li\b|</li\s*>', masked[m.start():]):
            depth += 1 if t.group(0).startswith('<li') else -1
            if depth == 0:
                end = m.start() + t.end()
                break
        if sid and end:
            out.append((sid.group(1), m.start(), end))
    return out


def template_block(name):
    text = open(TEMPLATE, encoding='utf-8').read()
    m = re.search(r'<!-- %s:begin -->\n(.*?)<!-- %s:end -->\n' % (name, name), text, re.S)
    if not m:
        die('template/report.src.html has no %s block' % name)
    return m.group(1)


def reindent(block, indent):
    lines = block.rstrip('\n').split('\n')
    have = len(lines[0]) - len(lines[0].lstrip(' '))
    shift = lambda l: (' ' * max(0, len(l) - len(l.lstrip(' ')) - have + len(indent)) + l.lstrip(' ')) if l.strip() else l
    return '\n'.join(shift(l) for l in lines) + '\n'


def esc(s):
    return html.escape(s or '', quote=False)


def local_time(iso):
    try:
        dt = datetime.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone()
        return dt.strftime('%Y-%m-%d %H:%M %Z')
    except ValueError:
        return str(iso)


def markup(sid, after, risk, text, cmd, why, indent):
    """One step, cut from the template the scaffold uses, so a fold never drifts from what `new` writes."""
    blk = template_block('step-w' if risk == 'w' else 'step-ro')
    blk = blk.replace('{{STEP_ID}}', sid).replace('{{AFTER}}', ' data-after="%s"' % after if after else '')
    for ph in PH_SENTENCE:
        blk = blk.replace(ph, esc(text))
    if cmd:
        for ph in PH_COMMAND:                    # the write placeholder first: the other is its prefix
            blk = blk.replace(ph, esc(cmd))
    if why:
        blk = blk.replace(PH_WHY, '<p>%s</p>' % why)
    return reindent(blk, indent)


def shown(path):
    """A path as the human would type it: relative when it is under here, else from ~."""
    rel = os.path.relpath(path)
    if not rel.startswith('..'):
        return rel
    home = os.path.expanduser('~')
    return '~' + path[len(home):] if path.startswith(home + os.sep) else path


def main():
    ap = argparse.ArgumentParser(prog='flowviz fold', description=__doc__.split('\n')[0])
    ap.add_argument('src', help='the report .src.html the human worked from')
    ap.add_argument('--todo', action='append', default=[], metavar='ID',
                    help='also fold this "add to write-up" to-do as a step, after the step it is tied to')
    ap.add_argument('--dry-run', action='store_true', help='print what would be folded and write nothing')
    a = ap.parse_args()

    src_path = os.path.abspath(a.src)
    if not os.path.exists(src_path):
        die('no such file: %s' % a.src)
    if not src_path.endswith('.src.html'):
        die('fold into the source (<NAME>.src.html), then rebuild; the built page is regenerated from it.')
    text = open(src_path, encoding='utf-8').read()
    if 'name="flowviz-kind" content="drawing"' in text:
        die('a drawing page has no playbook to fold steps into.')
    cap = load('fvcaptures', 'flowviz-captures.py')
    doc = cap.find_doc_id(text, cap.parse_html(text))
    if not doc:
        die('no <meta name="flowviz-doc"> in the source — refusing to guess the sidecar.')
    folder = os.path.dirname(src_path)
    sidecar = os.path.join(folder, doc + '.flow.json')
    if not os.path.exists(sidecar):
        print(cap.no_sidecar_message(sidecar, folder), file=sys.stderr)
        sys.exit(2)
    try:
        data = json.load(open(sidecar, encoding='utf-8'))
    except ValueError as e:
        die('%s is not valid JSON (%s); nothing was written.' % (sidecar, e))
    added = data.get('added') if isinstance(data.get('added'), dict) else {}
    todos = data.get('todos') if isinstance(data.get('todos'), dict) else {}
    have = {sid for sid, _, _ in steps_in(text)}
    taken = set(have) | set(added)               # a tombstone's id is never handed out again

    # what to fold: every live added step the source lacks, then each --todo asked for
    work, skipped = [], []
    for aid in sorted(k for k, v in added.items() if isinstance(v, dict) and not v.get('gone') and k not in have):
        v = added[aid]
        base = str(v.get('after') or '')
        anchor = base[0] + '1' if re.match(r'^[a-z]0$', base) else base
        if anchor not in have:
            skipped.append('%s was added after %s, which the source no longer has: fold it by hand' % (aid, base))
            continue
        work.append({'id': aid, 'base': base, 'text': v.get('text') or '', 'cmd': v.get('cmd') or '',
                     'risk': 'w' if v.get('risk') == 'w' else 'ro', 'at': v.get('at'), 'todo': None,
                     'note': ((data.get('captures') or {}).get(aid) or {}).get('note') or ''})
    for tid in a.todo:
        t = todos.get(tid)
        if not isinstance(t, dict) or t.get('gone'):
            die('there is no to-do %s in %s' % (tid, os.path.basename(sidecar)))
        if t.get('kind') == 'do':
            die('%s is a "do after" to-do: it belongs in Next, not in the playbook' % tid)
        if t.get('became'):
            die('%s already became step %s' % (tid, t['became']))
        base = re.match(r'^[a-z][0-9]+', str(t.get('ref') or ''))
        if not base or (t.get('ref') not in have and t.get('ref') not in [w['id'] for w in work]):
            die('%s is not tied to a step in the source, so fold cannot tell where it goes; add it by hand' % tid)
        base = base.group(0)
        sid = next(base + chr(c) for c in range(97, 123) if base + chr(c) not in taken
                   and base + chr(c) not in [w['id'] for w in work])
        work.append({'id': sid, 'base': base, 'text': t.get('text') or '', 'cmd': '', 'risk': 'ro',
                     'at': t.get('at'), 'todo': tid, 'note': ''})
    if not work:
        opened = [k for k, v in todos.items() if isinstance(v, dict) and not v.get('gone') and not v.get('done')
                  and v.get('kind') != 'do' and v.get('ref')]
        print('nothing to fold: every step added in the page is already in %s.' % shown(src_path))
        for s in skipped:
            print('  skip   ' + s)
        if opened:
            print('open "add to write-up" to-dos you could fold as steps: %s (--todo ID)' % ', '.join(sorted(opened)))
        return

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    out, report = text, []
    for w in sorted(work, key=lambda x: x['id']):
        spans = steps_in(out)
        ids = [s for s, _, _ in spans]
        if re.match(r'^[a-z]0$', w['base']):
            group = [s for s in ids if re.match(r'^%s[a-z]$' % re.escape(w['base']), s) and s < w['id']]
            prev = group[-1] if group else None
            at = next(e for s, _, e in spans if s == prev) if prev else next(st for s, st, _ in spans if s == w['base'][0] + '1')
        else:
            group = [s for s in ids if s == w['base'] or (re.match(r'^%s[a-z]$' % re.escape(w['base']), s) and s < w['id'])]
            prev = group[-1]
            at = next(e for s, _, e in spans if s == prev)
        line_start = out.rfind('\n', 0, next(st for s, st, _ in spans if s == (prev or w['base'][0] + '1'))) + 1
        indent = re.match(r'[ \t]*', out[line_start:]).group(0)
        why = 'Added in the page %s%s, while the playbook ran%s. Folded in by <code>flowviz fold</code>.' % (
            local_time(w['at']) if w['at'] else 'after handover',
            ', after ' + prev if prev else ', before the first step',
            ', with the note: %s' % esc(w['note']) if w['note'] else '')
        block = markup(w['id'], prev, w['risk'], w['text'], w['cmd'], why, indent)
        if w['risk'] == 'w':                     # the write shape has no "why this step": say it in a comment
            block = '%s<!-- %s -->\n' % (indent, re.sub(r'<[^>]+>', '', why).replace('--', '-')) + block
        if prev:
            out = out[:at] + '\n\n' + block.rstrip('\n') + out[at:]
        else:
            out = out[:line_start] + block + '\n' + out[line_start:]
        # the step that came next now waits on the new one, if it waited on the one before
        nxt = None
        for s, st, _ in steps_in(out):
            if prev and s == prev:
                nxt = 'after-prev'
                continue
            if nxt == 'after-prev' and s != w['id']:
                nxt = (s, st)
                break
        moved = ''
        if isinstance(nxt, tuple):
            s, st = nxt
            tag_end = out.index('>', st)
            tag = out[st:tag_end]
            if prev and re.search(r'\bdata-after="%s"' % re.escape(prev), tag):
                out = out[:st] + re.sub(r'\bdata-after="%s"' % re.escape(prev), 'data-after="%s"' % w['id'], tag) + out[tag_end:]
                moved = '%s now waits on %s' % (s, w['id'])
        left = ['the pass and fail lines and their regexes']
        if not w['cmd']:
            left.insert(0, 'the command (or what to check by hand)')
        if w['todo']:
            left.insert(0, 'the sentence, as what the step establishes (it was written as a to-do)')
        if w['risk'] == 'w':
            left.append('the gate, naming exactly what it writes to')
        report.append((w, prev, moved, left))
        if w['todo']:
            t = todos[w['todo']]
            t.update(became=w['id'], done=True, doneAt=t.get('doneAt') or now, folded=now)
        else:
            added[w['id']]['folded'] = now

    rel = shown(src_path)
    print('%s%s' % ('dry run — nothing written · ' if a.dry_run else '', rel))
    for w, prev, moved, left in report:
        print('  fold   %-5s %s · %s · "%s"' % (w['id'],
              ('after %s' % prev) if prev else 'before %s1' % w['base'][0], 'WRITE' if w['risk'] == 'w' else 'read',
              w['text']) + ('   (from to-do %s)' % w['todo'] if w['todo'] else ''))
        if moved:
            print('         ' + moved)
        print('         left for you: ' + '; '.join(left))
    for s in skipped:
        print('  skip   ' + s)
    if a.dry_run:
        return

    data['savedAt'] = now
    tmp = src_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(out)
    os.replace(tmp, src_path)
    bdir = os.path.join(folder, '.flowviz', 'state-backup')
    os.makedirs(bdir, exist_ok=True)
    backup = os.path.join(bdir, '%s.%s.json' % (doc, datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    with open(sidecar, 'rb') as f_in, open(backup, 'wb') as f_out:
        f_out.write(f_in.read())
    tmp = sidecar + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    os.replace(tmp, sidecar)
    print('  state  %s: %s · backup %s' % (os.path.basename(sidecar), ', '.join(
        ('%s closed as %s' % (w['todo'], w['id'])) if w['todo'] else '%s stamped folded' % w['id'] for w, _, _, _ in report),
        shown(backup)))
    print('next: write what is left, then rebuild and audit; reload the page and each step reads as authored.')
    print('  %s build %s && %s audit --browser %s' % (F, rel, F, rel[:-9] + '.html'))


if __name__ == '__main__':
    main()
