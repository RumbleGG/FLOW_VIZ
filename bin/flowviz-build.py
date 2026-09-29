#!/usr/bin/env python3
"""flowviz build — turn a .src.html into one self-contained .html.

    flowviz build <name>.src.html [--out <name>.html]

Inlines template/flow.css + draw.css at <!-- flowviz:head --> (after a boot script that sets
the theme before first paint), the icon sprite + flow.js + draw.js at <!-- flowviz:js -->, and a
provenance footer at <!-- flowviz:foot -->. Every drawing spec is parsed first, so a broken spec
fails here rather than in the human's browser. The previous output, if any, is copied to
<dir>/.flowviz/history/<doc>/<UTC>.html before it is overwritten.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'template')
MARKERS = ('<!-- flowviz:head -->', '<!-- flowviz:foot -->', '<!-- flowviz:js -->')


def die(msg):
    print('flowviz build: ' + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def asset(name):
    path = os.path.join(TEMPLATE, name)
    if not os.path.exists(path):
        print('flowviz build: WARNING template/%s is missing — this build is incomplete' % name,
              file=sys.stderr)
        return ('<!-- template/%s missing at build time -->' if name.endswith('.svg')
                else '/* template/%s missing at build time */') % name
    text = read(path)
    if name.endswith('.js') and re.search(r'</script', text, re.I):
        die('template/%s contains "</script" and would end its own tag early' % name)
    return text


def meta(src, name):
    m = re.search(r'<meta\s+name="flowviz-%s"\s+content="([^"]*)"' % name, src)
    return m.group(1).strip() if m else None


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'untitled'


def git_sha():
    """The toolkit's commit, but only when FLOW_VIZ is its own repository —
    a parent repository's sha would name the wrong history."""
    def run(*args):
        return subprocess.run(['git', '-C', ROOT] + list(args), capture_output=True, text=True, timeout=5)
    try:
        top = run('rev-parse', '--show-toplevel')
        if top.returncode or os.path.realpath(top.stdout.strip()) != os.path.realpath(ROOT):
            return None
        sha = run('rev-parse', '--short', 'HEAD').stdout.strip()
        if not sha:
            return None
        dirty = run('status', '--porcelain', '--', 'template', 'bin', 'VERSION').stdout.strip()
        return sha + ('+dirty' if dirty else '')
    except (OSError, subprocess.SubprocessError):
        return None


def check_specs(src):
    """Every drawing's JSON must parse; report the line it is on if it does not."""
    count = 0
    for fig in re.finditer(r'<figure\b[^>]*class="[^"]*\bfv-drawing\b[^"]*"[^>]*>(.*?)</figure>', src, re.S):
        count += 1
        m = re.search(r'<script\s+type="application/json"\s*>(.*?)</script>', fig.group(1), re.S)
        line = src.count('\n', 0, fig.start()) + 1
        if not m:
            die('the drawing at line %d has no <script type="application/json"> spec' % line)
        try:
            spec = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            die('the drawing spec at line %d does not parse: %s (spec line %d, column %d)'
                % (line, e.msg, e.lineno, e.colno))
        if not isinstance(spec, dict) or not spec.get('id'):
            die('the drawing spec at line %d has no "id"' % line)
    return count


# ── the embed stylesheet: everything a drawing needs, scoped to .fvx ──────────
# A drawing copied into a wiki page carries this, so it looks right there and
# cannot restyle the page around it: token blocks move from :root onto .fvx,
# page-level rules are dropped, core components are prefixed with .fvx, and the
# drawing's own rules (already namespaced fv-) are kept as they are.
TOKEN_MAP = {':root': '.fvx', '[data-theme="dark"]': '.fvx[data-theme="dark"]',
             '[data-kind="drawing"]': '.fvx', '[data-kind="drawing"][data-theme="dark"]': '.fvx[data-theme="dark"]'}
CORE_OK = re.compile(r'^(p|ul|ol|li|b|strong|a|em|code|pre|table|thead|tbody|tr|th|td|h3|\.box|\.cmd|\.copy'
                     r'|\.expect|details\.more|\.c|\.k|\.badge)(?![\w-])')


def split_css(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    items, i, n = [], 0, len(css)
    while i < n:
        j = css.find('{', i)
        if j < 0:
            break
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {'{': 1, '}': -1}.get(css[k], 0)
            k += 1
        items.append((css[i:j].strip(), css[j + 1:k - 1]))
        i = k
    return items


def scope_rules(items, core):
    out = []
    for prelude, body in items:
        if prelude.startswith(('@media', '@supports')):
            inner = scope_rules(split_css(body), core)
            if inner:
                out.append(prelude + '{' + inner + '}')
            continue
        if prelude.startswith('@'):
            if not core:
                out.append(prelude + '{' + body + '}')
            continue
        sels = [x.strip() for x in prelude.split(',')]
        if len(sels) == 1 and sels[0] in TOKEN_MAP:
            out.append(TOKEN_MAP[sels[0]] + '{' + body + '}')
            continue
        if any(x.startswith('[data-kind="drawing"]') for x in sels):
            continue
        if core:
            if all(CORE_OK.match(x) for x in sels):
                out.append(','.join('.fvx ' + x for x in sels) + '{' + body + '}')
            continue
        out.append(','.join('.fvx ' + x if re.match(r'^\.(k|j)-', x) else x for x in sels) + '{' + body + '}')
    return '\n'.join(out)


def embed_css(flow_css, draw_css):
    # the wrapper gets spacing; everything carrying .fvx (the drawer, toast and peek too) gets type and ink
    head = ('.fvx[data-fvx]{display:block;margin:12px 0}\n'
            '.fvx{font:14px/1.55 var(--f-body);color:var(--fg)}\n'
            '.fvx,.fvx *{box-sizing:border-box}')
    css = head + '\n' + scope_rules(split_css(flow_css), True) + '\n' + scope_rules(split_css(draw_css), False)
    if re.search(r'</script', css, re.I):
        die('the embed stylesheet contains "</script"')
    return css


def boot(doc, version, kind, built):
    flow = json.dumps({'doc': doc, 'version': version, 'kind': kind, 'built': built})
    return ('<script>window.FLOW=%s;\n'
            '(function(){var h=document.documentElement;h.setAttribute("data-kind",FLOW.kind);'
            'try{var q=(location.search.match(/[?&]theme=(light|dark)/)||[])[1];'
            'var s=JSON.parse(localStorage.getItem("flowviz:"+FLOW.doc)||"{}"),u=s.ui||{};'
            'var t=q||u.theme||"auto";'
            'var d=t==="dark"||(t==="auto"&&matchMedia("(prefers-color-scheme: dark)").matches);'
            'h.setAttribute("data-theme",d?"dark":"light");if(u.motion===false)h.classList.add("still");}'
            'catch(e){h.setAttribute("data-theme","light");}})();</script>' % flow)


def footer(doc, kind, version, built, sha):
    stamp = ('<span class="v">FLOW-VIZ v%s</span> · doc <code>%s</code> · template <code>%s@%s</code> · '
             'built %s · sha <code>%s</code> · state <code>%s.flow.json</code>'
             % (version, doc, kind, version, built[:10], sha or 'untracked', doc))
    if sha:
        rb = ('<div class="rb">Roll back the standard to this version: <span class="inl">'
              '<code id="flowRb">git -C ~/Projects/FLOW_VIZ checkout v%s</code>'
              '<button class="copy" data-for="flowRb">copy</button></span></div>' % version)
    else:
        rb = '<div class="rb">No rollback handle yet: FLOW_VIZ is not its own git repository.</div>'
    return '<div class="foot">\n%s\n%s\n</div>' % (stamp, rb)


def main():
    ap = argparse.ArgumentParser(prog='flowviz build', description=__doc__.split('\n')[0])
    ap.add_argument('src', help='the .src.html to build')
    ap.add_argument('--out', help='output path (default: <name>.html beside the source)')
    a = ap.parse_args()

    src_path = os.path.abspath(a.src)
    if not os.path.exists(src_path):
        die('no such file: %s' % a.src)
    if a.out:
        out_path = os.path.abspath(a.out)
    elif src_path.endswith('.src.html'):
        out_path = src_path[:-len('.src.html')] + '.html'
    else:
        die('the source should end in .src.html, or pass --out')
    if out_path == src_path:
        die('refusing to overwrite the source with the build')

    src = read(src_path)
    for marker in MARKERS:
        n = src.count(marker)
        if n != 1:
            die('%s must appear exactly once in %s (found %d)' % (marker, os.path.basename(src_path), n))

    version = read(os.path.join(ROOT, 'VERSION')).strip()
    kind = meta(src, 'kind') or 'report'
    if kind not in ('report', 'drawing'):
        die('flowviz-kind must be "report" or "drawing", not "%s"' % kind)
    doc = meta(src, 'doc') or slug(os.path.basename(src_path).replace('.src.html', ''))
    if not re.match(r'^[A-Za-z0-9][A-Za-z0-9._-]*$', doc):
        die('the doc id "%s" must match [A-Za-z0-9][A-Za-z0-9._-]*' % doc)
    drawings = check_specs(src)

    built = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    sha = git_sha()
    head = boot(doc, version, kind, built) + '\n<style>\n' + asset('flow.css') + '\n' + asset('draw.css') + '\n</style>'
    fcss, dcss = asset('flow.css'), asset('draw.css')
    js = (asset('icons.svg') + '\n<script type="text/plain" id="fvEmbedCss">\n' + embed_css(fcss, dcss)
          + '\n</script>\n<script>\n' + asset('flow.js') + '\n</script>\n<script>\n' + asset('draw.js') + '\n</script>')
    out = (src.replace(MARKERS[0], head)
              .replace(MARKERS[1], footer(doc, kind, version, built, sha))
              .replace(MARKERS[2], js))

    snapshot = None
    if os.path.exists(out_path):
        hist = os.path.join(os.path.dirname(out_path), '.flowviz', 'history', doc)
        os.makedirs(hist, exist_ok=True)
        snapshot = os.path.join(hist, built.replace('-', '').replace(':', '') + '.html')
        shutil.copy2(out_path, snapshot)
    tmp = out_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(out)
    os.replace(tmp, out_path)

    size = len(out.encode('utf-8')) / 1024
    shown = os.path.relpath(out_path)
    if shown.startswith('..'):
        shown = out_path.replace(os.path.expanduser('~'), '~', 1)
    note = ' · snapshot %s' % os.path.relpath(snapshot, os.path.dirname(out_path)) if snapshot else ''
    print('built %s  (%s · %d drawing%s · %.0f KB%s)' % (shown, kind, drawings,
          '' if drawings == 1 else 's', size, note))


if __name__ == '__main__':
    main()
