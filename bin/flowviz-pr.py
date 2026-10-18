#!/usr/bin/env python3
"""flowviz pr — a report that explains one pull request to its reviewer (SPEC §1.8).

    flowviz pr                                    the inputs to save first, and the commands that save them
    flowviz pr new "<claim with a verb>" --dir DIR --pr DIR/pr/pr.json --diff DIR/pr/pr.diff --checkout PATH
                   [--name NAME] [--boxes 5] [--detail 12]
    flowviz pr fill <NAME>.src.html [--repin]

`new` scaffolds a read-only report pinned to the PR's head commit — card, spine, detail drawing, and rows in
three groups: what is new, shared changes, files and review — then fills it. `fill` expands every marker
from the saved inputs, so no code or diff a reviewer reads was typed by hand:

    <!-- pr:lines PATH A-B -->   lines A to B of PATH at the pinned head, numbered, from the checkout
    <!-- pr:hunk PATH N -->      the Nth hunk of PATH's diff, verbatim (@L instead of N: the hunk holding new line L)
    <!-- pr:diff PATH -->        every hunk of PATH's diff, verbatim
    <!-- pr:files -->            one disclosure per file in GitHub's order: name, +added −removed and one sentence
                                 at rest; notes, new test names and the file's diff one click down
    <!-- pr:commits -->          one row per commit: sha, date, what it did
    <!-- pr:reviews -->          each reviewer's latest review, and the commit it was left on
    <!-- pr:checks -->           the CI checks GitHub reports for the head

and the card's vitals marked data-pr="files|lines|commits|tests". Each expansion follows its marker and
ends at <!-- /pr -->; a re-fill replaces it. What you wrote stays: a file's sentence and its notes
(<!-- pr:notes --> … <!-- /pr:notes -->), and a commit's "what it did". Nothing is written unless every
marker resolves, and the source is copied to .flowviz/history/ first.
"""
import argparse
import codecs
import datetime
import html
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

BIN = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BIN)
TEMPLATE = os.path.join(ROOT, 'template')
F = os.path.join(BIN, 'flowviz').replace(os.path.expanduser('~'), '~', 1)

INPUTS = '''Save the inputs first, read-only, into <dir>/pr/ (the PR is <url>, number <n>, in <owner>/<repo>):

  mkdir -p <dir>/pr
  gh pr view <url> --json number,title,url,headRefOid,baseRefName,headRefName,additions,deletions,files,commits,reviews,comments,statusCheckRollup > <dir>/pr/pr.json
  gh pr diff <url> > <dir>/pr/pr.diff
  gh api repos/<owner>/<repo>/pulls/<n>/comments --paginate > <dir>/pr/review-comments.json
  git -C <repo> fetch origin pull/<n>/head && git -C <repo> worktree add --detach <checkout> "$(gh pr view <url> --json headRefOid -q .headRefOid)"

pr.json carries GitHub's file order and counts, the commits with their dates, the reviews and the CI checks;
pr.diff is every hunk; review-comments.json is the line comments, for you to read. The checkout sits at the
head commit, and every line number in the report is pinned to it. Then:

  {F} pr new "<claim with a verb>" --dir <dir> --pr <dir>/pr/pr.json --diff <dir>/pr/pr.diff --checkout <checkout>
'''.replace('{F}', F)

MARK = re.compile(r'<!-- pr:(lines|hunk|diff|files|commits|reviews|checks)\b([^>]*?)-->')
CLOSE = '<!-- /pr -->'
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
TEST_PATH = re.compile(r'(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.\w+$|[Tt]ests?\.\w+$|\.(spec|test)\.\w+$')
UNWRITTEN = {'PATH', 'A-B', 'N'}


def die(msg, code=1):
    print('flowviz pr: ' + msg, file=sys.stderr)
    sys.exit(code)


def esc(s):
    return html.escape(s, quote=False)


def attr(s):
    return html.escape(s, quote=True)


def load(name, modname):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(modname, os.path.join(BIN, name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── the saved diff ───────────────────────────────────────────────────────────
def unquote(p):
    """git quotes a path with special characters C-style, octal bytes included."""
    if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
        return codecs.escape_decode(p[1:-1].encode('latin-1', 'backslashreplace'))[0].decode('utf-8', 'replace')
    return p


def strip_ab(p):
    p = unquote(p.split('\t')[0])
    return p[2:] if p[:2] in ('a/', 'b/') else p


def git_paths(rest):
    """The two paths of a `diff --git a/X b/Y` line. Unquoted paths may hold spaces, so prefer the split
    where both sides agree; the ---/+++ and rename lines that follow correct a rename."""
    if rest.startswith('"'):
        m = re.match(r'^("(?:[^"\\]|\\.)*") (.*)$', rest)
        if m:
            return strip_ab(m.group(1)), strip_ab(m.group(2))
    for i in [k for k in range(len(rest)) if rest.startswith(' b/', k)]:
        a, b = rest[:i], rest[i + 1:]
        if a[2:] == b[2:]:
            return strip_ab(a), strip_ab(b)
    i = rest.find(' b/')
    return (strip_ab(rest[:i]), strip_ab(rest[i + 1:])) if i > 0 else (strip_ab(rest), strip_ab(rest))


def parse_diff(text):
    """[{path, old, kind, binary, add, del, hunks: [{header, new, nlen, lines}]}] in the diff's own order.
    A hunk's lines are kept byte for byte, its @@ header first; counts are read from the hunk headers, so
    a removed line that starts with "--" is never taken for a file header."""
    files, cur, hunk, ro, rn = [], None, None, 0, 0
    for raw in text.replace('\r\n', '\n').split('\n'):
        if hunk is not None and (ro > 0 or rn > 0):
            c = raw[:1]
            hunk['lines'].append(raw)
            if c == '+':
                rn -= 1
                cur['add'] += 1
            elif c == '-':
                ro -= 1
                cur['del'] += 1
            elif c != '\\':                     # context, or an empty line some tools leave for one
                ro -= 1
                rn -= 1
            continue
        if hunk is not None and raw.startswith('\\'):
            hunk['lines'].append(raw)           # \ No newline at end of file
            continue
        if raw.startswith('diff --git '):
            old, new = git_paths(raw[len('diff --git '):])
            cur = {'path': new, 'old': old, 'new': new, 'kind': 'modified', 'binary': False,
                   'add': 0, 'del': 0, 'hunks': []}
            files.append(cur)
            hunk = None
            continue
        if cur is None:
            continue
        m = HUNK.match(raw)
        if m:
            ro = int(m.group(2)) if m.group(2) is not None else 1
            rn = int(m.group(4)) if m.group(4) is not None else 1
            hunk = {'header': raw, 'old': int(m.group(1)), 'new': int(m.group(3)), 'nlen': rn, 'lines': [raw]}
            cur['hunks'].append(hunk)
            continue
        hunk = None
        if raw.startswith('new file mode'):
            cur['kind'] = 'added'
        elif raw.startswith('deleted file mode'):
            cur['kind'] = 'removed'
        elif raw.startswith('rename from '):
            cur['kind'], cur['old'] = 'renamed', unquote(raw[len('rename from '):])
        elif raw.startswith('rename to '):
            cur['new'] = unquote(raw[len('rename to '):])
        elif raw.startswith('Binary files ') or raw.startswith('GIT binary patch'):
            cur['binary'] = True
        elif raw.startswith('--- ') and raw[4:].strip() != '/dev/null':
            cur['old'] = strip_ab(raw[4:])
        elif raw.startswith('+++ ') and raw[4:].strip() != '/dev/null':
            cur['new'] = strip_ab(raw[4:])
    for f in files:
        f['path'] = f['old'] if f['kind'] == 'removed' else f['new']
    return files


def hunk_text(h):
    return '\n'.join(h['lines'])


# ── the saved PR ─────────────────────────────────────────────────────────────
def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def pr_files(pr):
    """GitHub's order and counts: the order `gh pr view --json files` returns, which is the order of the
    Files changed tab."""
    return [{'path': f.get('path'), 'add': f.get('additions', 0), 'del': f.get('deletions', 0)}
            for f in pr.get('files') or [] if f.get('path')]


def expected_files(pr, diff):
    """The per-file list as it must read: GitHub's order, the diff's hunks. Returns (rows, problems)."""
    byp = {f['path']: f for f in diff}
    rows, problems = [], []
    gh = pr_files(pr) if pr else []
    if not gh:
        return [dict(f) for f in diff], ['pr.json lists no files: the order is the diff\'s, not GitHub\'s']
    for g in gh:
        d = byp.get(g['path'])
        if d is None:
            problems.append('%s is in pr.json but not in the diff: save both at the same head' % g['path'])
            continue
        if (d['add'], d['del']) != (g['add'], g['del']) and not d['binary']:
            problems.append('%s is +%d −%d in pr.json and +%d −%d in the diff: save both at the same head'
                            % (g['path'], g['add'], g['del'], d['add'], d['del']))
        rows.append(dict(d))
    listed = {g['path'] for g in gh}
    for d in diff:
        if d['path'] not in listed:
            problems.append('%s is in the diff but not in pr.json%s' % (d['path'], ' (gh lists 100 files at most)'
                                                                        if len(gh) >= 100 else ''))
    return rows, problems


def new_tests(f):
    """The test methods a test file's diff adds, read from its + lines."""
    if not TEST_PATH.search(f['path']):
        return None
    names, armed = [], False
    for h in f['hunks']:
        for raw in h['lines'][1:]:
            if not raw.startswith('+'):
                if not raw.startswith('-'):
                    armed = False
                continue
            line = raw[1:]
            m = (re.match(r'\s*(?:async\s+)?def\s+(test\w*)\s*\(', line)              # Python
                 or re.match(r'\s*func\s+(Test\w+)\s*\(', line)                      # Go
                 or re.match(r'\s*(?:it|test)\s*\(\s*([\'"`])(.+?)\1', line))        # JS, TS
            if m:
                names.append(m.group(m.lastindex))
                armed = False
                continue
            if re.match(r'\s*(?:@(?:Test|ParameterizedTest|RepeatedTest|TestFactory)\b|\[(?:Fact|Theory|Test|TestMethod)\b)', line):
                armed = True
                continue
            if armed:
                m = re.match(r'\s*(?:(?:public|protected|private|internal|static|final|override|suspend|async)\s+)*'
                             r'(?:fun\s+(`[^`]+`|\w+)|[\w<>\[\],.? ]+?\s+(\w+))\s*\(', line)
                if m:
                    names.append((m.group(1) or m.group(2)).strip('`'))
                    armed = False
    return names


# ── the checkout, at the pinned head ─────────────────────────────────────────
_ROOTS = {}


def own_repo(checkout):
    """True when the checkout is a git repository's top level, not a folder inside some other repository."""
    if checkout not in _ROOTS:
        try:
            r = subprocess.run(['git', '-C', checkout, 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
            _ROOTS[checkout] = r.returncode == 0 and os.path.realpath(r.stdout.strip()) == os.path.realpath(checkout)
        except OSError:
            _ROOTS[checkout] = False
    return _ROOTS[checkout]


def file_at(checkout, head, path):
    """PATH as it is at the pinned head: `git show head:path`, so a checkout that has moved on still
    answers for the commit the report is pinned to. A checkout that is not a repository: its files."""
    if own_repo(checkout):
        r = subprocess.run(['git', '-C', checkout, 'show', '%s:%s' % (head, path)], capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode('utf-8', 'replace')
    p = os.path.join(checkout, path)
    if os.path.isfile(p):
        with open(p, encoding='utf-8', errors='replace') as f:
            return f.read()
    return None


def head_of(checkout):
    if not own_repo(checkout):
        return None
    r = subprocess.run(['git', '-C', checkout, 'rev-parse', 'HEAD'], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def cut_warning(path, lines, a, b):
    """A range that cuts a block in two, the off-by-one at a method boundary: braces that do not
    balance, or a next line indented deeper than the excerpt's first."""
    out = []
    body = '\n'.join(lines[a - 1:b])
    if os.path.splitext(path)[1] in ('.java', '.kt', '.kts', '.scala', '.cs', '.js', '.jsx', '.ts', '.tsx', '.go',
                                     '.c', '.h', '.cc', '.cpp', '.hpp', '.swift', '.rs', '.php', '.groovy', '.dart'):
        bare = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', '', body, flags=re.S)
        if bare.count('{') != bare.count('}'):
            out.append('%s:%d-%d opens %d braces and closes %d' % (path, a, b, bare.count('{'), bare.count('}')))
    first = next((l for l in lines[a - 1:b] if l.strip()), '')
    nxt = next((l for l in lines[b:] if l.strip()), None)
    ind = lambda l: len(l) - len(l.lstrip())
    if first and nxt is not None and ind(nxt) > ind(first):
        out.append('%s:%d-%d stops while the block goes on at line %d' % (path, a, b, b + 1 + lines[b:].index(nxt)))
    return out


# ── what each marker becomes ─────────────────────────────────────────────────
def diff_code(lines):
    """Diff lines, escaped, each coloured by its first character; the text itself is untouched."""
    out = []
    for l in lines:
        c = 'dh' if l.startswith('@@') else 'da' if l.startswith('+') else 'dd' if l.startswith('-') else ''
        out.append('<span class="%s">%s</span>' % (c, esc(l)) if c else esc(l))
    return '\n'.join(out)


def kind_word(f):
    return {'added': 'new file', 'removed': 'deleted', 'renamed': 'renamed from %s' % f['old']}.get(f['kind'], '')


def render_lines(path, a, b, lines, head):
    body = '\n'.join('<span class="ln">%d</span>%s' % (n, esc(l)) for n, l in zip(range(a, b + 1), lines[a - 1:b]))
    return ('<div class="cmd fig src" data-pr-src="%s" data-pr-lines="%d-%d"><p class="at"><code>%s</code> lines %d–%d '
            'at <code>%s</code></p><pre><code>%s</code></pre></div>' % (attr(path), a, b, esc(path), a, b, head[:7], body))


def render_hunk(f, k):
    h = f['hunks'][k - 1]
    end = h['new'] + max(h['nlen'], 1) - 1
    return ('<div class="cmd fig diff" data-pr-hunk="%s" data-pr-n="%d"><p class="at"><code>%s</code> hunk %d of %d · new '
            'lines %d–%d</p><pre><code>%s</code></pre></div>' % (attr(f['path']), k, esc(f['path']), k, len(f['hunks']),
                                                              h['new'], end, diff_code(h['lines'])))


def render_diff(f):
    if f['binary'] or not f['hunks']:
        what = 'a binary file' if f['binary'] else 'no lines changed'
        return '<p class="prf-bin"><code>%s</code>: %s%s.</p>' % (esc(f['path']), what,
                                                                ' (%s)' % kind_word(f) if kind_word(f) else '')
    lines = [l for h in f['hunks'] for l in h['lines']]
    return ('<div class="cmd fig diff" data-pr-diff="%s"><p class="at"><code>%s</code> · %d hunk%s · +%d −%d%s</p>'
            '<pre><code>%s</code></pre></div>' % (attr(f['path']), esc(f['path']), len(f['hunks']),
                                                 '' if len(f['hunks']) == 1 else 's', f['add'], f['del'],
                                                 ' · ' + kind_word(f) if kind_word(f) else '', diff_code(lines)))


def kept_files(old):
    """What the author wrote into an earlier per-file list: each file's sentence and its notes."""
    kept = {}
    for chunk in old.split('<details class="prf-file" ')[1:]:
        m = re.match(r'data-file="([^"]*)"', chunk)
        if not m:
            continue
        s = re.search(r'<span class="prf-s">(.*?)</span></summary>', chunk, re.S)
        n = re.search(r'<!-- pr:notes -->\n?(.*?)<!-- /pr:notes -->', chunk, re.S)
        kept[html.unescape(m.group(1))] = (s.group(1) if s else None, n.group(1) if n else None)
    return kept


def render_files(rows, old, shape):
    kept, out = kept_files(old), []
    tpl_s = re.search(r'<span class="prf-s">(.*?)</span></summary>', shape, re.S).group(1)
    tpl_n = re.search(r'<!-- pr:notes -->\n?(.*?)<!-- /pr:notes -->', shape, re.S).group(1)
    for f in rows:
        s, n = kept.get(f['path'], (None, None))
        tests = new_tests(f)
        tline = ('' if tests is None else '<p class="prf-tests">%s</p>\n' % (
            'New tests: ' + ', '.join('<code>%s</code>' % esc(t) for t in tests) if tests
            else 'No new test methods: existing tests changed.'))
        kw = kind_word(f)
        item = (shape.replace('<span class="prf-s">%s</span>' % tpl_s, '<span class="prf-s">%s</span>' % (s or tpl_s))
                     .replace('<!-- pr:notes -->\n%s<!-- /pr:notes -->' % tpl_n,
                              '<!-- pr:notes -->\n%s<!-- /pr:notes -->' % (n if n is not None else tpl_n))
                     .replace('{{FILE}}', esc(f['path']).replace('"', '&quot;'))
                     .replace('{{ADD}}', str(f['add'])).replace('{{DEL}}', str(f['del']))
                     .replace('{{KIND}}', ' · %s' % esc(kw) if kw else '')
                     .replace('{{TESTS}}', tline).replace('{{DIFF}}', render_diff(f)))
        out.append(item.rstrip('\n'))
    gone = sorted(set(kept) - {f['path'] for f in rows})
    return '<div class="prf" data-pr-files="%d">\n%s\n</div>' % (len(rows), '\n'.join(out)), gone


def pt(iso):
    """2026-10-01 10:02 PDT: stored UTC, shown Pacific and labelled, as every time on the page is."""
    try:
        d = datetime.datetime.fromisoformat((iso or '').replace('Z', '+00:00'))
    except ValueError:
        return esc(iso or '')
    try:
        import zoneinfo
        d = d.astimezone(zoneinfo.ZoneInfo('America/Los_Angeles'))
        return d.strftime('%Y-%m-%d %H:%M ') + d.tzname()
    except Exception:
        return d.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%MZ')


def render_commits(pr, old):
    kept = {m.group(1): m.group(2) for m in re.finditer(
        r'<tr data-sha="([0-9a-f]+)">(?:(?!</tr>).)*?<td class="what">(.*?)</td></tr>', old, re.S)}
    rows = []
    for c in pr.get('commits') or []:
        oid, when = c.get('oid') or '', c.get('committedDate') or c.get('authoredDate') or ''
        rows.append('<tr data-sha="%s"><td><code>%s</code></td><td><time datetime="%s">%s</time></td>'
                    '<td class="what">%s</td></tr>' % (oid, oid[:7], attr(when), pt(when),
                                                       kept.get(oid) or esc(c.get('messageHeadline') or '')))
    if not rows:
        return '<p>pr.json lists no commits.</p>'
    return ('<table class="prc"><thead><tr><th>Commit</th><th>When</th><th>What it did</th></tr></thead><tbody>\n'
            + '\n'.join(rows) + '\n</tbody></table>')


STATE = {'APPROVED': 'approved', 'CHANGES_REQUESTED': 'changes requested', 'COMMENTED': 'commented',
         'DISMISSED': 'dismissed', 'PENDING': 'pending'}


def render_reviews(pr, head):
    last = {}
    for r in sorted(pr.get('reviews') or [], key=lambda r: r.get('submittedAt') or ''):
        who = (r.get('author') or {}).get('login') or '?'
        if r.get('state') == 'COMMENTED' and who in last and last[who].get('state') != 'COMMENTED':
            continue                         # a comment after a verdict leaves the verdict standing
        last[who] = r
    if not last:
        return '<p class="prv">No reviews yet at <code>%s</code>.</p>' % head[:7]
    rows = []
    for who, r in sorted(last.items()):
        oid = ((r.get('commit') or {}).get('oid')) or ''
        on = 'the pinned head' if oid and oid == head else ('<code>%s</code>, before the head' % oid[:7] if oid else '—')
        rows.append('<tr><td>%s</td><td>%s</td><td>%s</td><td><time datetime="%s">%s</time></td></tr>'
                    % (esc(who), STATE.get(r.get('state'), esc((r.get('state') or '').lower())), on,
                       attr(r.get('submittedAt') or ''), pt(r.get('submittedAt'))))
    return ('<table class="prv"><thead><tr><th>Reviewer</th><th>Latest review</th><th>Left on</th><th>When</th></tr>'
            '</thead><tbody>\n' + '\n'.join(rows) + '\n</tbody></table>')


def render_checks(pr, head):
    runs = []
    for c in pr.get('statusCheckRollup') or []:
        name = c.get('name') or c.get('context') or '?'
        if c.get('workflowName'):
            name = '%s / %s' % (c['workflowName'], name)
        res = (c.get('conclusion') or c.get('state') or c.get('status') or 'pending').lower()
        runs.append((name, res))
    if not runs:
        return '<p class="prk">No CI checks reported at <code>%s</code>.</p>' % head[:7]
    good = {'success', 'neutral', 'skipped'}
    bad = [r for r in runs if r[1] not in good]
    count = {}
    for _, r in runs:
        count[r] = count.get(r, 0) + 1
    line = '<p class="prk">%d CI check%s at <code>%s</code>: %s.</p>' % (
        len(runs), '' if len(runs) == 1 else 's', head[:7], ', '.join('%d %s' % (v, k) for k, v in sorted(count.items())))
    if not bad:
        return line
    return line + ('\n<table class="prk"><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>\n'
                   + '\n'.join('<tr><td>%s</td><td>%s</td></tr>' % (esc(n), esc(r)) for n, r in bad) + '\n</tbody></table>')


# ── fill ─────────────────────────────────────────────────────────────────────
def pr_meta(src):
    m = re.search(r'<meta\s+name="flowviz-pr"\s+content=\'([^\']*)\'', src)
    if not m:
        return None
    return json.loads(html.unescape(m.group(1)))


def meta_tag(meta):
    """JSON in a single-quoted attribute: only &, ' and < need escaping, so the source stays readable."""
    j = json.dumps(meta, ensure_ascii=False).replace('&', '&amp;').replace("'", '&#39;').replace('<', '&lt;')
    return "<meta name=\"flowviz-pr\" content='%s'>" % j


def resolve(base, p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def inputs(src_path, meta):
    """(pr, diff files, checkout, problems) from the paths the report records, relative to it."""
    base = os.path.dirname(os.path.abspath(src_path))
    probs, pr, diff = [], None, None
    try:
        pr = read_json(resolve(base, meta['pr']))
    except (OSError, ValueError, KeyError) as e:
        probs.append('pr.json: %s' % e)
    try:
        with open(resolve(base, meta['diff']), encoding='utf-8', errors='replace') as f:
            diff = parse_diff(f.read())
    except (OSError, KeyError) as e:
        probs.append('the diff: %s' % e)
    checkout = resolve(base, meta['checkout']) if meta.get('checkout') else None
    return pr, diff, checkout, probs


def counts(rows, pr):
    tests = sum(len(new_tests(f) or []) for f in rows)
    return {'files': str(len(rows)), 'lines': '+%d −%d' % (sum(f['add'] for f in rows), sum(f['del'] for f in rows)),
            'commits': str(len(pr.get('commits') or [])), 'tests': str(tests)}


def fill(src_path, repin=False, quiet=False):
    with open(src_path, encoding='utf-8') as f:
        src = f.read()
    meta = pr_meta(src)
    if meta is None:
        die('%s has no <meta name="flowviz-pr">: scaffold a PR helper with `flowviz pr new`' % src_path)
    pr, diff, checkout, probs = inputs(src_path, meta)
    if probs:
        die('cannot read the inputs the report names:\n  ' + '\n  '.join(probs))
    head = meta.get('head') or ''
    now = pr.get('headRefOid') or ''
    if now and now != head:
        if not repin:
            die('pr.json is at %s but the report is pinned to %s. Every line number would move: re-read the PR, '
                'then `flowviz pr fill %s --repin` to pin the new head' % (now[:7], head[:7], src_path))
        src = src.replace('head <code>%s</code>' % head[:7], 'head <code>%s</code>' % now[:7])
        meta['head'] = head = now
        src = re.sub(r'<meta\s+name="flowviz-pr"\s+content=\'[^\']*\'>', lambda _: meta_tag(meta), src)
    if checkout and os.path.isdir(checkout):
        at = head_of(checkout)
        if at and at != head and not quiet:
            print('  note: the checkout is at %s, not the pinned head %s; lines are read from the head with git show'
                  % (at[:7], head[:7]))
    byp = {f['path']: f for f in diff}
    rows, order_probs = expected_files(pr, diff)
    errors, warnings, unwritten = list(order_probs), [], 0
    shape = read_template_block('prfile')
    out, i, cache = [], 0, {}

    def source(path):
        if path not in cache:
            cache[path] = file_at(checkout, head, path) if checkout else None
        return cache[path]

    for m in MARK.finditer(src):
        if m.start() < i:
            continue
        kind, args = m.group(1), shlex.split(html.unescape(m.group(2).strip()))
        nxt = MARK.search(src, m.end())
        close = src.find(CLOSE, m.end())
        has_old = close >= 0 and (nxt is None or close < nxt.start())
        old = src[m.end():close] if has_old else ''
        end = close + len(CLOSE) if has_old else m.end()
        out.append(src[i:m.end()])
        i = end
        if set(args) & UNWRITTEN:
            unwritten += 1
            out.append(src[m.end():end])
            continue
        gen = None
        if kind == 'lines':
            if len(args) != 2 or not re.match(r'^\d+-\d+$', args[1]):
                errors.append('pr:lines %s — write it as <!-- pr:lines PATH A-B -->' % ' '.join(args))
            else:
                path, (a, b) = args[0], map(int, args[1].split('-'))
                text = source(path)
                if text is None:
                    errors.append('pr:lines %s — not in the checkout at %s%s' % (path, head[:7], '' if checkout else
                                                                                 ' (the report names no checkout)'))
                else:
                    lines = text.split('\n')
                    if text.endswith('\n'):
                        lines.pop()
                    if not 1 <= a <= b <= len(lines):
                        errors.append('pr:lines %s %d-%d — the file has %d lines' % (path, a, b, len(lines)))
                    else:
                        gen = render_lines(path, a, b, lines, head)
                        warnings += cut_warning(path, lines, a, b)
        elif kind in ('hunk', 'diff'):
            path = args[0] if args else ''
            f = byp.get(path)
            if f is None:
                errors.append('pr:%s %s — not a file in the diff' % (kind, path))
            elif kind == 'diff':
                gen = render_diff(f)
            elif len(args) != 2 or not re.match(r'^@?\d+$', args[1]):
                errors.append('pr:hunk %s — write it as <!-- pr:hunk PATH N --> or @LINE' % ' '.join(args))
            else:
                k = int(args[1].lstrip('@'))
                if args[1].startswith('@'):
                    k = next((n for n, h in enumerate(f['hunks'], 1) if h['new'] <= k < h['new'] + max(h['nlen'], 1)), 0)
                    if not k:
                        errors.append('pr:hunk %s %s — no hunk holds new line %s' % (path, args[1], args[1][1:]))
                elif not 1 <= k <= len(f['hunks']):
                    errors.append('pr:hunk %s %d — the file has %d hunk%s' % (path, k, len(f['hunks']),
                                                                            '' if len(f['hunks']) == 1 else 's'))
                    k = 0
                if k:
                    gen = render_hunk(f, k)
        elif kind == 'files':
            gen, gone = render_files(rows, old, shape)
            for g in gone:
                warnings.append('%s is no longer in the diff: its sentence and notes were dropped (the old source '
                                'is in .flowviz/history/)' % g)
        elif kind == 'commits':
            gen = render_commits(pr, old)
        elif kind == 'reviews':
            gen = render_reviews(pr, head)
        elif kind == 'checks':
            gen = render_checks(pr, head)
        out.append('\n%s\n%s' % (gen, CLOSE) if gen is not None else src[m.end():end])
    out.append(src[i:])
    new = ''.join(out)
    # the card's vitals: counted, never typed
    for k, v in counts(rows, pr).items():
        new = re.sub(r'(<div class="n" data-pr="%s">)[^<]*(</div>)' % k, lambda m, v=v: m.group(1) + v + m.group(2), new)
    if errors:
        die('nothing was written — fix these and fill again:\n  ' + '\n  '.join(errors))
    if new != src:
        doc = (re.search(r'<meta\s+name="flowviz-doc"\s+content="([^"]*)"', src) or [None, 'pr'])[1]
        hist = os.path.join(os.path.dirname(os.path.abspath(src_path)), '.flowviz', 'history', doc)
        os.makedirs(hist, exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        shutil.copy2(src_path, os.path.join(hist, stamp + '.src.html'))
        tmp = src_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(new)
        os.replace(tmp, src_path)
    if not quiet:
        c = counts(rows, pr)
        print('filled %s  (pinned %s · %s files · %s lines · %s commits · %s new tests%s)'
              % (src_path.replace(os.path.expanduser('~'), '~', 1), head[:7], c['files'], c['lines'], c['commits'],
                 c['tests'], ' · %d marker%s still to write' % (unwritten, '' if unwritten == 1 else 's') if unwritten else ''))
        for w in warnings:
            print('  check: ' + w)
    return new


def read_template_block(name):
    with open(os.path.join(TEMPLATE, 'pr.src.html'), encoding='utf-8') as f:
        t = f.read()
    m = re.search(r'<!-- %s:begin -->\n(.*?)<!-- %s:end -->\n' % (name, name), t, re.S)
    if not m:
        die('template/pr.src.html is missing the %s block' % name)
    return m.group(1)


# ── new ──────────────────────────────────────────────────────────────────────
VITALS = [('files', 'files changed'), ('lines', 'lines added and removed'), ('commits', 'commits'),
          ('tests', 'new tests')]


def new(a):
    nm = load('flowviz-new.py', 'fvnew')
    title = ' '.join(a.claim.split())
    folder = os.path.abspath(os.path.expanduser(a.dir))
    for p in (a.pr, a.diff):
        if not os.path.exists(os.path.expanduser(p)):
            die('%s does not exist: save the inputs first (run `flowviz pr` for the commands)' % p)
    pr = read_json(os.path.expanduser(a.pr))
    num, url, head = pr.get('number'), pr.get('url') or '', pr.get('headRefOid') or ''
    if not head:
        die('pr.json has no headRefOid: save it with --json …,headRefOid,…')
    if not a.checkout or not os.path.isdir(os.path.expanduser(a.checkout)):
        die('--checkout must be a local checkout of the PR head (run `flowviz pr` for the commands)')
    name = a.name or ('PR-%s' % num if num else 'PR')
    doc = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    src = os.path.join(folder, name + '.src.html')
    for path in (src, src[:-len('.src.html')] + '.html'):
        if os.path.exists(path):
            die('%s already exists — not overwriting it. Pick another --name, or run `flowviz pr fill` on it.' % path)
    if not 2 <= a.boxes <= 9:
        die('--boxes must be 2-9 for a report spine')
    if not 2 <= a.detail <= 20:
        die('--detail must be 2-20 classes: a 21st means a segment, or a second report')

    t = nm.read('report.src.html')
    rows = read_template_block('pr-rows')
    out = re.sub(r'<!-- sec:begin -->\n.*?<!-- sec:end -->\n', '', t, flags=re.S)
    out = re.sub(r'<!-- row:begin -->\n.*?<!-- row:end -->\n', lambda _: rows, out, flags=re.S)
    out = re.sub(r'\n<!-- ═+ PLAYBOOK SHAPES.*?<!-- step-w:end -->\n', '\n', out, flags=re.S)
    _, tpl = nm.spec_of(out)
    out = nm.put_spec(out, nm.gen_spec(tpl, a.boxes, 2, a.boxes - 1, 4, 'spine'))
    out = nm.detail_slot(out, a.detail)

    def rel(p):
        p = os.path.abspath(os.path.expanduser(p))
        r = os.path.relpath(p, folder)
        return r if not r.startswith('..') else p.replace(os.path.expanduser('~'), '~', 1)
    meta = {'url': url, 'number': num, 'head': head, 'pr': rel(a.pr), 'diff': rel(a.diff), 'checkout': rel(a.checkout)}
    out = out.replace('<meta name="flowviz-kind" content="report">',
                      '<meta name="flowviz-kind" content="report">\n' + meta_tag(meta), 1)
    label = 'PR #%s' % num if num else 'The PR'
    link = '<a href="%s">%s</a>' % (attr(url), label) if url.startswith('https://') else label
    out = re.sub(r'<span class="meta">[^<]*</span>',
                 lambda _: '<span class="meta">%s · head <code>%s</code> · read-only: nothing to run</span>'
                 % (link, head[:7]), out, count=1)
    tiles = ''.join('    <div><div class="n" data-pr="%s">0</div><div class="l">%s</div></div>\n' % (k, l)
                    for k, l in VITALS) + read_template_block('pr-vitals')
    out = re.sub(r'(<div class="vitals">\n).*?(  </div>\n)', lambda m: m.group(1) + tiles + m.group(2), out,
                 count=1, flags=re.S)
    out = (out.replace('<title>{{TITLE}}</title>', '<title>%s</title>' % html.escape(title))
              .replace('{{TITLE}}', html.escape(title)).replace('{{DOC}}', doc)
              .replace('{{DATE}}', datetime.date.today().isoformat()))
    os.makedirs(folder, exist_ok=True)
    with open(src, 'w', encoding='utf-8') as f:
        f.write(out)
    print('created %s  (PR helper · doc %s · read-only · spine %d boxes, 2 flows · detail %d classes)'
          % (src.replace(os.path.expanduser('~'), '~', 1), doc, a.boxes, a.detail))
    fill(src, quiet=False)
    if len(title) > 70:
        print('  note: the title is %d characters; the cap is 70.' % len(title))
    short = src.replace(os.path.expanduser('~'), '~', 1)
    print('next: write every slot and every PATH marker (AGENTS.md, "Explaining a pull request"), then')
    print('  %s pr fill %s && %s build %s' % (F, short, F, short))


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print('\n'.join(__doc__.split('\n')[:6]) + '\n\n' + INPUTS, end='')
        return
    ap = argparse.ArgumentParser(prog='flowviz pr', description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    n = sub.add_parser('new', help='scaffold a PR helper from the saved inputs, then fill it')
    n.add_argument('claim', help='the title: a claim with a verb, 70 characters at most')
    n.add_argument('--dir', required=True, help='the folder the work is in')
    n.add_argument('--pr', required=True, help='gh pr view --json … saved to disk')
    n.add_argument('--diff', required=True, help='gh pr diff saved to disk')
    n.add_argument('--checkout', required=True, help='a local checkout of the PR head')
    n.add_argument('--name', help='file name without .src.html (default PR-<number>)')
    n.add_argument('--boxes', type=int, default=5, help='spine boxes, 2-9 (default 5)')
    n.add_argument('--detail', type=int, default=12, help='detail drawing classes, 2-20 (default 12)')
    f = sub.add_parser('fill', help='expand every pr: marker from the saved inputs')
    f.add_argument('src', help='the report source, <NAME>.src.html')
    f.add_argument('--repin', action='store_true', help='move the pin to the head pr.json now names')
    a = ap.parse_args(argv)
    if a.cmd == 'new':
        new(a)
    else:
        if not os.path.exists(a.src):
            die('no such file: %s' % a.src, 2)
        fill(a.src, repin=a.repin)


if __name__ == '__main__':
    main()
