#!/usr/bin/env python3
"""flowviz archive — move a finished deliverable, and everything that is its, into the archive.

    flowviz archive <NAME>.html [--to <dir>] [--dry-run]

The destination is decided here, so no agent has to choose one: <root>/<YYYY-MM-DD>-<project>-<doc>/,
where root is $FLOWVIZ_ARCHIVE, else ~/Archive (~/Archives if only that exists), the date is today's (local), project is the folder under
~/Projects the page lives in (else the page's own folder) and doc is the page's doc id. A name already
taken gets -2, -3. --to names the folder outright.

What moves: the page, its .src.html, its state (<doc>.flow.json), its pasted images (<doc>.assets/), its
build snapshots (.flowviz/history/<doc>/), its sends (<doc>.send.json, .flowviz/sent/<doc>/) and every
figure its source names. A figure another source in
the same folder also names is copied instead, so that page still builds. Relative paths are kept, so the
archived source rebuilds where it lands. Folders the move leaves empty are removed; the page's own
folder is not. Every built page shows this command, with its own path, behind **file** in the pill.
"""
import argparse
import datetime
import html
import importlib.util
import os
import re
import shutil
import sys
import urllib.parse

BIN = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser('~')


def die(msg):
    print('flowviz archive: ' + msg, file=sys.stderr)
    sys.exit(1)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-') or 'untitled'


def archive_root():
    """Where finished work goes: $FLOWVIZ_ARCHIVE, else ~/Archive, else ~/Archives when only that exists.
    Decided here once: the build stamps it into every page, and `flowviz results` writes it into the
    archive step, so no agent picks a place of its own."""
    env = os.environ.get('FLOWVIZ_ARCHIVE')
    if env:
        return os.path.abspath(os.path.expanduser(env))
    a, b = os.path.join(HOME, 'Archive'), os.path.join(HOME, 'Archives')
    return b if not os.path.isdir(a) and os.path.isdir(b) else a


def archive_stem(page_path, doc):
    """<project>-<doc>, the date-free part of the folder name. The build stamps it into each page,
    and the page puts today's date in front, so what it shows is what this script will do."""
    page_path = os.path.abspath(page_path)
    projects = os.path.join(HOME, 'Projects') + os.sep
    if page_path.startswith(projects):
        project = page_path[len(projects):].split(os.sep)[0]
    else:
        project = os.path.basename(os.path.dirname(page_path))
    p, d = slug(project), slug(doc)
    # a doc id that already names its project (flowviz-plan in FLOW_VIZ) is not prefixed twice
    return d if d.replace('-', '').startswith(p.replace('-', '')) else p + '-' + d


def in_archive(path):
    return os.path.abspath(path).startswith(archive_root() + os.sep)


def build_module():
    spec = importlib.util.spec_from_file_location('flowviz_build', os.path.join(BIN, 'flowviz-build.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def doc_of(html_path, src_path, b):
    if src_path:
        d = b.meta(read(src_path), 'doc')
        if d:
            return d
    if html_path and os.path.exists(html_path):
        m = re.search(r'window\.FLOW\s*=\s*\{.*?"doc"\s*:\s*"([^"]+)"', read(html_path), re.S)
        if m:
            return m.group(1)
    base = os.path.basename(src_path or html_path)
    return b.slug(re.sub(r'(\.src)?\.html$', '', base))


def figures(src_path, b):
    """The relative paths of the files a source's <img> tags name, outside comments, inside its folder."""
    src, base = read(src_path), os.path.dirname(src_path)
    comments = [(m.start(), m.end()) for m in re.finditer(r'<!--.*?-->', src, re.S)]
    out = []
    for m in b.IMG_TAG.finditer(src):
        if any(s <= m.start() < e for s, e in comments):
            continue
        attrs = {am.group(1).lower(): next((v for v in am.group(2, 3, 4) if v is not None), None)
                 for am in b.ATTR.finditer(m.group(0)[4:].rstrip('>').rstrip('/'))}
        ref = html.unescape(attrs.get('src') or '')
        if not ref or re.match(r'^[a-z][a-z0-9+.-]*:', ref, re.I):
            continue
        p = os.path.abspath(os.path.join(base, os.path.expanduser(urllib.parse.unquote(ref))))
        if p.startswith(base + os.sep) and os.path.isfile(p):
            rel = os.path.relpath(p, base)
            if rel not in out:
                out.append(rel)
    return out


def main():
    ap = argparse.ArgumentParser(prog='flowviz archive', description=__doc__.split('\n')[0])
    ap.add_argument('page', help='the built <NAME>.html (or its <NAME>.src.html)')
    ap.add_argument('--to', help='the folder to move it into (default: the archive, dated)')
    ap.add_argument('--dry-run', action='store_true', help='say what would move, and move nothing')
    a = ap.parse_args()

    path = os.path.abspath(os.path.expanduser(a.page))
    if path.endswith('.src.html'):
        src_path, html_path = path, path[:-len('.src.html')] + '.html'
    elif path.endswith('.html'):
        html_path, src_path = path, path[:-len('.html')] + '.src.html'
    else:
        die('give the page: <NAME>.html or <NAME>.src.html')
    if not os.path.exists(html_path) and not os.path.exists(src_path):
        die('no such page: %s' % a.page)
    if not os.path.exists(src_path):
        src_path = None
    if in_archive(path) and not a.to:
        die('%s is already in the archive (%s)' % (a.page, archive_root()))

    b = build_module()
    base = os.path.dirname(path)
    doc = doc_of(html_path, src_path, b)

    if a.to:
        dest = os.path.abspath(os.path.expanduser(a.to))
    else:
        stem = os.path.join(archive_root(), datetime.date.today().isoformat() + '-' + archive_stem(path, doc))
        dest, n = stem, 2
        while os.path.exists(dest) and os.listdir(dest):
            dest, n = '%s-%d' % (stem, n), n + 1
    if dest == base or dest.startswith(os.path.join(base, doc + '.assets') + os.sep):
        die('refusing to archive a page into its own folder: %s' % dest)

    # (relative path, move or copy) — everything that belongs to this page
    moves = []
    for rel in (os.path.basename(html_path), src_path and os.path.basename(src_path),
                doc + '.flow.json', doc + '.assets', os.path.join('.flowviz', 'history', doc),
                doc + '.send.json', os.path.join('.flowviz', 'sent', doc)):
        if rel and os.path.exists(os.path.join(base, rel)):
            moves.append((rel, 'move'))
    if src_path:
        others = [os.path.join(base, f) for f in os.listdir(base)
                  if f.endswith('.src.html') and os.path.join(base, f) != src_path]
        shared = set()
        for o in others:
            shared.update(figures(o, b))
        for rel in figures(src_path, b):
            moves.append((rel, 'copy' if rel in shared else 'move'))

    for rel, how in moves:
        if os.path.exists(os.path.join(dest, rel)):
            die('%s already holds %s: pass --to <another folder>' % (dest, rel))

    shown = lambda p: p.replace(HOME, '~', 1)
    if a.dry_run:
        print('would %s %d item%s to %s/' % ('move' if all(h == 'move' for _, h in moves) else 'move or copy',
              len(moves), '' if len(moves) == 1 else 's', shown(dest)))
        for rel, how in moves:
            print('  %-4s %s' % (how, rel))
        return

    touched = set()
    for rel, how in moves:
        s, d = os.path.join(base, rel), os.path.join(dest, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if how == 'copy':
            shutil.copy2(s, d)
        else:
            shutil.move(s, d)
            touched.add(os.path.dirname(s))
    # leave no empty shots/ or .flowviz/history behind — but never remove the page's own folder
    for t in sorted(touched, key=len, reverse=True):
        while t.startswith(base + os.sep) and os.path.isdir(t) and not os.listdir(t):
            os.rmdir(t)
            t = os.path.dirname(t)

    page = os.path.join(dest, os.path.basename(html_path))
    print('archived %s -> %s/  (%d moved%s)' % (
        os.path.basename(html_path), shown(dest), sum(1 for _, h in moves if h == 'move'),
        ', %d copied: another page in the folder names them' % sum(1 for _, h in moves if h == 'copy')
        if any(h == 'copy' for _, h in moves) else ''))
    if os.path.exists(page):
        print('open it: open %s' % shown(page))


if __name__ == '__main__':
    main()
