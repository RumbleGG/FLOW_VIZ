#!/usr/bin/env python3
"""flowviz-serve — serve a FLOW_VIZ working folder on localhost so what the human
types in a report or drawing reaches disk (SPEC.md §6, §8). stdlib only, no network
beyond the local socket.

Usage: flowviz-serve.py <dir> [--port 8787] [--open [FILE]]
"""
import argparse
import http.server
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timezone

DOC_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
FLOW_MARKER = 'window.FLOW='
FLOW_BLOB_RE = re.compile(r'window\.FLOW\s*=\s*\{(.*?)\}', re.S)
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.S | re.I)
MAX_BODY = 4 * 1024 * 1024  # 4 MB
PUT_SUFFIX = '_flow/state/'


def field_from_blob(blob, name):
    """Loosely pull `name:'value'` or `"name": "value"` out of a window.FLOW{...} blob."""
    m = re.search(r'[\'"]?' + re.escape(name) + r'[\'"]?\s*:\s*[\'"]([^\'"]*)[\'"]', blob)
    return m.group(1) if m else None


def parse_flow_globals(text):
    """Returns (doc, kind) parsed loosely from a window.FLOW={...} literal, or (None, None)."""
    m = FLOW_BLOB_RE.search(text)
    if not m:
        return None, None
    blob = m.group(1)
    return field_from_blob(blob, 'doc'), field_from_blob(blob, 'kind')


def extract_title(text):
    m = TITLE_RE.search(text)
    if not m:
        return ''
    import html as html_mod
    return ' '.join(html_mod.unescape(m.group(1)).split())


def sidecar_stats(data):
    """(capture_count, done_count, note_count) from a parsed sidecar object."""
    captures = data.get('captures') or {}
    cap_n = sum(1 for c in captures.values() if isinstance(c, dict) and (c.get('text') or '').strip())
    steps = data.get('steps') or {}
    done_n = sum(1 for s in steps.values() if isinstance(s, dict) and s.get('done'))
    notes = data.get('notes') or {}
    return cap_n, done_n, len(notes)


def fmt_kb(nbytes):
    return '%.1f KB' % (nbytes / 1024.0)


def scan_deliverables(root):
    """Every *.html under root, up to 3 levels deep, skipping .flowviz dirs, whose
    text contains 'window.FLOW='. Returns a list of dicts sorted by relative path."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == os.curdir else rel.count(os.sep) + 1
        dirnames[:] = sorted(d for d in dirnames if d != '.flowviz')
        if depth >= 3:
            dirnames[:] = []
            continue
        for fn in sorted(filenames):
            if not fn.lower().endswith('.html'):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding='utf-8', errors='replace') as f:
                    text = f.read()
            except OSError:
                continue
            if FLOW_MARKER not in text:
                continue
            relpath = os.path.relpath(full, root).replace(os.sep, '/')
            doc, kind = parse_flow_globals(text)
            item = {
                'relpath': relpath,
                'title': extract_title(text) or relpath,
                'doc': doc,
                'kind': kind,
                'captures': None, 'done': None, 'notes': None, 'saved_at': None,
            }
            if doc:
                sidecar_path = os.path.join(dirpath, doc + '.flow.json')
                try:
                    with open(sidecar_path, encoding='utf-8') as f:
                        sdata = json.load(f)
                    if isinstance(sdata, dict):
                        cap_n, done_n, note_n = sidecar_stats(sdata)
                        item['captures'], item['done'], item['notes'] = cap_n, done_n, note_n
                        item['saved_at'] = sdata.get('savedAt')
                except (OSError, ValueError):
                    pass
            found.append(item)
        if depth == 2:
            dirnames[:] = []
    found.sort(key=lambda x: x['relpath'])
    return found


def dash(v):
    return '—' if v is None else str(v)


def render_index(root, items):
    import html as html_mod
    rows = []
    for it in items:
        href = '/' + urllib.parse.quote(it['relpath'])
        audit_href = href + '?audit=1'
        rows.append(
            '<tr>'
            '<td><a href="%s">%s</a></td>'
            '<td>%s</td>'
            '<td><code>%s</code></td>'
            '<td>%s</td>'
            '<td>%s</td>'
            '<td>%s</td>'
            '<td>%s</td>'
            '<td>%s</td>'
            '<td><a href="%s">audit</a></td>'
            '</tr>' % (
                href, html_mod.escape(it['relpath']),
                html_mod.escape(it['title']),
                html_mod.escape(it['doc'] or '—'),
                html_mod.escape(it['kind'] or '—'),
                dash(it['captures']), dash(it['done']), dash(it['notes']),
                html_mod.escape(it['saved_at'] or '—'),
                audit_href,
            )
        )
    body = ''.join(rows) if rows else (
        '<tr><td colspan="9" class="empty">No FLOW_VIZ deliverables found under this folder.</td></tr>'
    )
    page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>FLOW_VIZ — %s</title>
<style>
body{font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  margin:0;padding:2rem;background:#fbfbfa;color:#1a1a1a}
.wrap{max-width:980px;margin:0 auto}
h1{font-size:19px;margin:0 0 2px}
p.meta{color:#767676;font-size:12.5px;margin:0 0 20px}
table{border-collapse:collapse;width:100%%;background:#fff;border:1px solid #e3e3e0}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #ececea;vertical-align:top;
  font-size:13px}
th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#767676;
  background:#f4f4f2}
tr:last-child td{border-bottom:none}
tr:hover td{background:#f7f7f5}
code{background:#f0f0ee;padding:1px 5px;border-radius:4px;font-size:12px}
a{color:#0b57d0;text-decoration:none}
a:hover{text-decoration:underline}
.empty{color:#8a8a86;text-align:center;padding:26px 10px}
</style></head>
<body><div class="wrap">
<h1>FLOW_VIZ deliverables</h1>
<p class="meta">serving <code>%s</code> &middot; %d found</p>
<table>
<tr><th>File</th><th>Title</th><th>Doc</th><th>Kind</th><th>Captures</th><th>Done</th>
<th>Notes</th><th>Saved</th><th></th></tr>
%s
</table>
</div></body></html>''' % (html_mod.escape(root), html_mod.escape(root), len(items), body)
    return page.encode('utf-8')


class FlowVizServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, handler_cls, root):
        super().__init__(addr, handler_cls)
        self.fv_root = os.path.realpath(root)
        self.fv_lock = threading.Lock()
        self.fv_backed_up = set()  # {(target_dir, doc)} already given their one-time backup


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = 'flowviz-serve/0.6'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=kwargs.pop('directory', None), **kwargs)

    # ---- shared plumbing ------------------------------------------------

    def _json(self, status, obj):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):  # noqa: A003 - stdlib name
        # every error is JSON, never the default HTML error page
        self._json(code, {'error': message or ('HTTP %d' % code)})

    def end_headers(self):
        try:
            local_path = self.translate_path(self.path)
        except Exception:
            local_path = ''
        if local_path.endswith('.html') or local_path.endswith('.flow.json'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))

    # ---- GET / directory index ------------------------------------------

    def do_GET(self):
        local_path = self.translate_path(self.path)
        if os.path.isdir(local_path):
            items = scan_deliverables(self.server.fv_root)
            body = render_index(self.server.fv_root, items)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    # ---- PUT sidecar state -----------------------------------------------

    def do_PUT(self):
        raw_path = urllib.parse.unquote(self.path.split('?', 1)[0])
        if PUT_SUFFIX not in raw_path:
            self.send_error(404, 'not a sidecar save path')
            return
        prefix, _, doc = raw_path.rpartition(PUT_SUFFIX)
        dir_part = prefix.strip('/')

        if not DOC_RE.match(doc or ''):
            self.send_error(400, 'invalid doc id')
            return

        length_header = self.headers.get('Content-Length')
        if length_header is None:
            self.send_error(411, 'Content-Length required')
            return
        try:
            length = int(length_header)
        except ValueError:
            self.send_error(400, 'invalid Content-Length')
            return
        if length < 0:
            self.send_error(400, 'invalid Content-Length')
            return
        if length > MAX_BODY:
            self.send_error(413, 'body exceeds 4 MB')
            return
        body = self.rfile.read(length)

        try:
            data = json.loads(body.decode('utf-8'))
        except (UnicodeDecodeError, ValueError) as e:
            self.send_error(400, 'body is not valid JSON (%s)' % e)
            return
        if not isinstance(data, dict):
            self.send_error(400, 'body must be a JSON object')
            return
        if data.get('doc') != doc:
            self.send_error(400, "body 'doc' field does not match the URL")
            return

        root = self.server.fv_root
        target_dir = os.path.realpath(os.path.join(root, dir_part)) if dir_part else root
        if target_dir != root and not target_dir.startswith(root + os.sep):
            self.send_error(403, 'path escapes the served directory')
            return
        if not os.path.isdir(target_dir):
            self.send_error(404, 'no such directory: %s' % dir_part)
            return

        sidecar_path = os.path.join(target_dir, doc + '.flow.json')
        key = (target_dir, doc)
        with self.server.fv_lock:
            # a tab opened before `flowviz relabel` still holds the old ids: saving it would put them back
            if os.path.exists(sidecar_path):
                try:
                    moved_at = json.load(open(sidecar_path, encoding='utf-8')).get('relabel') or ''
                except (OSError, ValueError, AttributeError):
                    moved_at = ''
                if moved_at and str(data.get('relabel') or '') < moved_at:
                    print('PUT refused %s: this tab predates flowviz relabel %s; reload it'
                          % (os.path.relpath(sidecar_path, root).replace(os.sep, '/'), moved_at), flush=True)
                    self.send_error(409, 'the ids moved (flowviz relabel %s): reload the page' % moved_at)
                    return
            need_backup_check = key not in self.server.fv_backed_up
            if need_backup_check and os.path.exists(sidecar_path):
                backup_dir = os.path.join(target_dir, '.flowviz', 'state-backup')
                os.makedirs(backup_dir, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                backup_path = os.path.join(backup_dir, '%s.%s.json' % (doc, ts))
                shutil.copyfile(sidecar_path, backup_path)
                self.server.fv_backed_up.add(key)

            fd, tmp_path = tempfile.mkstemp(prefix='.%s.' % doc, suffix='.tmp', dir=target_dir)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(body)
                    f.flush()
                    os.fsync(f.fileno())
                os.chmod(tmp_path, 0o644)
                os.replace(tmp_path, sidecar_path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

        cap_n, done_n, note_n = sidecar_stats(data)
        rel_sidecar = os.path.relpath(sidecar_path, root).replace(os.sep, '/')
        plural = lambda n, w: '%d %s%s' % (n, w, '' if n == 1 else 's')
        print('PUT %s  %s · %d done · %s · %s'
              % (rel_sidecar, plural(cap_n, 'capture'), done_n, plural(note_n, 'note'), fmt_kb(len(body))), flush=True)

        self.send_response(204)
        self.send_header('Content-Length', '0')
        self.end_headers()

    # ---- everything else is 405 ------------------------------------------

    def _method_not_allowed(self):
        self.send_response(405)
        self.send_header('Allow', 'GET, HEAD, PUT')
        body = json.dumps({'error': 'method not allowed'}).encode('utf-8')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_POST = _method_not_allowed
    do_DELETE = _method_not_allowed
    do_PATCH = _method_not_allowed
    do_OPTIONS = _method_not_allowed


def main(argv=None):
    ap = argparse.ArgumentParser(prog='flowviz-serve.py',
                                  description='Serve a FLOW_VIZ folder on 127.0.0.1 so captures reach disk.')
    ap.add_argument('dir', help='folder to serve')
    ap.add_argument('--port', type=int, default=8787)
    ap.add_argument('--open', nargs='?', const='', default=None, metavar='FILE',
                     help='open the index (or FILE, relative to <dir>) in the default browser')
    args = ap.parse_args(argv)

    root = os.path.realpath(args.dir)
    if not os.path.isdir(root):
        print('flowviz-serve: no such directory: %s' % args.dir, file=sys.stderr)
        return 1

    def handler_factory(*a, **kw):
        return Handler(*a, directory=root, **kw)

    try:
        server = FlowVizServer(('127.0.0.1', args.port), handler_factory, root)
    except OSError as e:
        print('flowviz-serve: could not bind 127.0.0.1:%d (%s)' % (args.port, e), file=sys.stderr)
        return 1

    base_url = 'http://127.0.0.1:%d/' % args.port
    print('flowviz-serve: %s -> %s' % (root, base_url), flush=True)

    if args.open is not None:
        target = base_url if args.open == '' else base_url + urllib.parse.quote(args.open.lstrip('/'))
        webbrowser.open(target)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nflowviz-serve: stopped.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
