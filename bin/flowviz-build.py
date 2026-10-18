#!/usr/bin/env python3
"""flowviz build — turn a .src.html into one self-contained .html.

    flowviz build <name>.src.html [--out <name>.html]

Inlines template/flow.css + draw.css at <!-- flowviz:head --> (after a boot script that sets
the theme before first paint), the icon sprite + flow.js + draw.js at <!-- flowviz:js -->, and a
provenance footer at <!-- flowviz:foot -->. Every <img src> — a figure the author shows — is read from
beside the source and inlined as a data URI, so the page stays one file. Every drawing spec is parsed
first, so a broken spec fails here rather than in the human's browser. The previous output, if any, is
copied to <dir>/.flowviz/history/<doc>/<UTC>.html before it is overwritten.
"""
import argparse
import base64
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import urllib.parse

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
                     r'|\.expect|details\.more|\.c|\.k|\.badge|figure\.shot)(?![\w-])')


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


def check_emits(src):
    """A bad emit, or a {{step.NAME}} token that nothing emits, never ships: the same checks the
    audit runs, taken from it so the two can never disagree."""
    import importlib.util
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('fvaudit', os.path.join(ROOT, 'bin', 'flowviz-audit.py'))
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    bad, dangling, _, _ = audit.emit_checks(audit.parse(src))
    if bad or dangling:
        die('emits do not resolve — nothing was written:\n  ' + '\n  '.join(bad + dangling))


# ── figures: every <img src> becomes a data URI, so the page stays one file ──
# A figure (SPEC §1.3e) is <figure class="shot"><img src="shots/x.png"><figcaption>…</figcaption></figure>.
# The file is read here, relative to the source, and inlined with its type, size, sha256 and pixel
# size on the tag, so the page opens from Finder, prints and travels with nothing beside it. A remote
# image never ships (SPEC §4), and nothing over 10 MB is inlined: the audit fails a figure over 1 MB.
IMG_TAG = re.compile(r'<img\b[^>]*>', re.I)
ATTR = re.compile(r'''\s+([^\s"'=<>/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>`]+)))?''')
FIGURE = re.compile(r'<figure\b[^>]*\bclass="[^"]*\bshot\b[^"]*"[^>]*>(.*?)</figure>', re.S | re.I)
CAPTION = re.compile(r'<figcaption\b[^>]*>(.*?)</figcaption>', re.S | re.I)
IMG_MAX = 10 * 1024 * 1024
SOF = {0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf}


def image_info(data):
    """(mime, width, height) read from the first bytes of a PNG, JPEG, GIF or WebP; None for anything else."""
    if data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR':
        w, h = struct.unpack('>II', data[16:24])
        return 'image/png', w, h
    if data[:6] in (b'GIF87a', b'GIF89a'):
        w, h = struct.unpack('<HH', data[6:10])
        return 'image/gif', w, h
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        chunk = data[12:16]
        if chunk == b'VP8 ' and len(data) >= 30:
            w, h = struct.unpack('<HH', data[26:30])
            return 'image/webp', w & 0x3fff, h & 0x3fff
        if chunk == b'VP8L' and len(data) >= 25:
            n = data[21] | data[22] << 8 | data[23] << 16 | data[24] << 24
            return 'image/webp', (n & 0x3fff) + 1, ((n >> 14) & 0x3fff) + 1
        if chunk == b'VP8X' and len(data) >= 30:
            return ('image/webp', 1 + (data[24] | data[25] << 8 | data[26] << 16),
                    1 + (data[27] | data[28] << 8 | data[29] << 16))
        return 'image/webp', 0, 0
    if data[:3] == b'\xff\xd8\xff':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xff:
                i += 1
                continue
            marker = data[i + 1]
            if marker == 0xff:
                i += 1
                continue
            if marker in (0x01, 0xd8) or 0xd0 <= marker <= 0xd7:
                i += 2
                continue
            if marker in SOF:
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return 'image/jpeg', w, h
            i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
        return 'image/jpeg', 0, 0
    return None


def inline_images(src, base):
    """Every <img> whose src is a file: read it, inline it, and stamp the tag with what it was.
    Returns the new source, the count and the total bytes inlined."""
    figs = [(m.start(), m.end(), CAPTION.search(m.group(1))) for m in FIGURE.finditer(src)]
    # the scaffold's own comments show the shape, <img src="shots/ready.png"> included: not a figure
    comments = [(m.start(), m.end()) for m in re.finditer(r'<!--.*?-->', src, re.S)]

    def caption_at(pos):
        for s, e, c in figs:
            if s <= pos < e:
                return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', c.group(1)))).strip() if c else ''
        return None

    out, last, count, total = [], 0, 0, 0
    for m in IMG_TAG.finditer(src):
        if any(s <= m.start() < e for s, e in comments):
            continue
        tag = m.group(0)
        attrs = [[am.group(1), next((v for v in am.group(2, 3, 4) if v is not None), None)]
                 for am in ATTR.finditer(tag[4:].rstrip('>').rstrip('/'))]
        d = {k.lower(): v for k, v in attrs}
        ref = html.unescape(d.get('src') or '')
        line = src.count('\n', 0, m.start()) + 1
        if ref.startswith('data:'):
            continue
        if not ref:
            die('the <img> at line %d has no src' % line)
        if re.match(r'^[a-z][a-z0-9+.-]*:', ref, re.I):
            die('the image at line %d is remote (%s): a page renders offline, so a figure is a file beside '
                'the source, inlined here' % (line, ref[:70]))
        path = os.path.expanduser(urllib.parse.unquote(ref))
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        if not os.path.isfile(path):
            die('the image at line %d is missing: %s (looked for %s)' % (line, ref, path))
        with open(path, 'rb') as f:
            data = f.read()
        info = image_info(data)
        if not info:
            die('the image at line %d is not a PNG, JPEG, GIF or WebP: %s' % (line, ref))
        if len(data) > IMG_MAX:
            die('the image at line %d is %.1f MB and is not inlined; a figure may be 1 MB. Shrink it first: '
                'sips -Z 1600 %s --out %s' % (line, len(data) / 1048576, ref, ref))
        mime, w, h = info

        def put(name, val):
            for kv in attrs:
                if kv[0].lower() == name:
                    kv[1] = val
                    return
            attrs.append([name, val])
        caption = caption_at(m.start())
        if not (d.get('alt') or '').strip() and caption:
            put('alt', html.escape(caption, quote=True))
        put('src', 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode('ascii')))
        if w and h and 'width' not in d and 'height' not in d:
            put('width', str(w))
            put('height', str(h))
        put('data-file', d['src'])
        put('data-sha256', hashlib.sha256(data).hexdigest())
        put('data-bytes', str(len(data)))
        out.append(src[last:m.start()])
        out.append('<img' + ''.join(' %s="%s"' % (k, v) if v is not None else ' ' + k for k, v in attrs) + '>')
        last = m.end()
        count += 1
        total += len(data)
    out.append(src[last:])
    return ''.join(out), count, total


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
              '<code id="flowRb">git -C %s checkout v%s</code>'
              '<button class="copy" data-for="flowRb">copy</button></span></div>'
              % (html.escape(ROOT.replace(os.path.expanduser('~'), '~', 1)), version))
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
    check_emits(src)
    src, figures, fig_bytes = inline_images(src, os.path.dirname(src_path))

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
    figs = (' · %d figure%s, %s inlined' % (figures, '' if figures == 1 else 's',
            '%.1f MB' % (fig_bytes / 1048576) if fig_bytes >= 1048576 else '%d KB' % round(fig_bytes / 1024))
            if figures else '')
    print('built %s  (%s · %d drawing%s%s · %.0f KB%s)' % (shown, kind, drawings,
          '' if drawings == 1 else 's', figs, size, note))


if __name__ == '__main__':
    main()
