#!/usr/bin/env python3
"""flowviz shot — a screenshot for a figure, taken by the same headless Chrome the audit uses.

    flowviz shot <url | file.html[?audit=1]> --out <dir>/shots/<name>.png [--size 1440x900] [--wait 2500] [--theme light|dark]

Anything with an address can be shot: a dashboard, an admin page, a built FLOW_VIZ page (add ?audit=1 for
the panel, --theme dark for the dark theme). The picture is a PNG of one viewport, --size wide and tall;
a taller --size shows more of a long page. It lands where --out says, which is where the figure's
<img src> will point: `<figure class="shot"><img src="shots/<name>.png"><figcaption>…</figcaption></figure>`,
inlined by `flowviz build`. A picture that already exists — a photo, a prior run's <doc>.assets/<sha>.png —
needs no shot: copy it into <dir>/shots/ and point at it.
"""
import argparse
import importlib.util
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_MAX = 1 << 20          # a figure's cap (SPEC §1.3e): the audit fails a larger one


def die(msg):
    print('flowviz shot: ' + msg, file=sys.stderr)
    sys.exit(1)


def chrome():
    """The audit's Chrome finder, imported so the two can never disagree about which browser runs."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('fvaudit', os.path.join(ROOT, 'bin', 'flowviz-audit.py'))
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    return audit.chrome()


def target(arg, theme):
    """A URL as given; a file as file://<absolute path>, its ?query kept. --theme adds theme=<t>,
    which a FLOW_VIZ page honours and any other page ignores."""
    if re.match(r'^https?://', arg, re.I):
        url = arg
    else:
        path, _, query = arg.partition('?')
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            die('no such file: %s' % path)
        url = 'file://' + urllib.parse.quote(path) + ('?' + query if query else '')
    if theme:
        url += ('&' if '?' in url else '?') + 'theme=' + theme
    return url


def png_size(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', head[16:24])


def kb(n):
    return '%.1f MB' % (n / 1048576) if n >= 1048576 else '%d KB' % max(1, round(n / 1024))


def main():
    ap = argparse.ArgumentParser(prog='flowviz shot', description=__doc__.split('\n')[0])
    ap.add_argument('what', help='a URL, or a file (a built .html, with ?audit=1 or any query it understands)')
    ap.add_argument('--out', required=True, help='the PNG to write, e.g. <dir>/shots/ready-page.png')
    ap.add_argument('--size', default='1440x900', help='viewport WIDTHxHEIGHT (default 1440x900)')
    ap.add_argument('--wait', type=int, default=2500, help='virtual time to let the page settle, ms (default 2500)')
    ap.add_argument('--theme', choices=('light', 'dark'), help='theme=<t> on the address, for a FLOW_VIZ page')
    a = ap.parse_args()

    m = re.match(r'^(\d{3,4})x(\d{3,4})$', a.size)
    if not m:
        die('--size is WIDTHxHEIGHT, like 1440x900')
    out = os.path.abspath(os.path.expanduser(a.out))
    if not out.lower().endswith('.png'):
        die('--out must end in .png: Chrome writes a PNG whatever the name says')
    url = target(a.what, a.theme)
    exe = chrome()
    if not exe:
        die('no Chrome or Chromium found; take the screenshot by hand and copy the file into <dir>/shots/')

    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    existed = os.path.exists(out)
    prof = tempfile.mkdtemp(prefix='flowviz-chrome-')
    tmp = out + '.tmp.png'
    cmd = [exe, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--user-data-dir=' + prof,
           '--window-size=%s,%s' % (m.group(1), m.group(2)), '--virtual-time-budget=%d' % a.wait,
           '--screenshot=' + tmp, url]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    # Chrome writes the PNG and then often never exits (the audit sees the same with --dump-dom):
    # once the file ends in PNG's IEND chunk and has stopped growing, the picture is done and Chrome is stopped
    deadline, seen = time.time() + 90, (None, 0)
    try:
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
            try:
                size = os.path.getsize(tmp)
                with open(tmp, 'rb') as f:
                    f.seek(max(0, size - 8))
                    done = f.read().endswith(b'IEND\xaeB`\x82')
            except OSError:
                continue
            if done and size == seen[0] and seen[1] >= 2:
                break
            seen = (size, seen[1] + 1 if size == seen[0] else 0)
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        proc.wait()
        shutil.rmtree(prof, ignore_errors=True)
    if not os.path.exists(tmp):
        die('Chrome wrote nothing for %s — does the address open in a browser?' % url)
    size = png_size(tmp)
    if not size:
        os.remove(tmp)
        die('Chrome wrote something that is not a PNG')
    os.replace(tmp, out)

    byts = os.path.getsize(out)
    shown = out.replace(os.path.expanduser('~'), '~', 1)
    print('shot %s  (%dx%d · %s%s)' % (shown, size[0], size[1], kb(byts), ' · replaced' if existed else ''))
    if byts > FIG_MAX:
        print('  note: over 1 MB, the cap on one figure. Shoot a smaller --size, or shrink it:'
              '\n        sips -Z 1200 %s --out %s' % (shown, shown))
    rel = os.path.relpath(out)                      # as the figure's src will read, from the source's folder
    if rel.startswith('..'):
        rel = os.path.join(os.path.basename(os.path.dirname(out)), os.path.basename(out))
    print('  figure: <figure class="shot"><img src="%s"><figcaption>One sentence: what to look at.</figcaption></figure>' % rel)


if __name__ == '__main__':
    main()
