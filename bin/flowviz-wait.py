#!/usr/bin/env python3
"""flowviz wait — block until the human presses **send to agent** on a served page, then print the captures.

    flowviz wait <NAME>.html [--timeout MIN]

Run it as a background command right after `flowviz serve`: it sits quietly until the human presses
**send to agent** in the page's pill, then prints when they sent it and the whole `flowviz captures`
readout, and exits 0. An agent harness that wakes its agent when a background command ends (Claude
Code does) hands that agent the captures at the moment the human is done. Run it again to wait for the
next send.

How it knows: the page POSTs its state to `flowviz serve`, which saves it and writes <doc>.send.json
beside the page. This command takes that file (it moves to .flowviz/sent/<doc>/), so a send made while
no agent was waiting is picked up by the next `flowviz wait` at once, and each send is read once. While
it runs it leaves its pid in .flowviz/wait/<doc>.pid, so the page can tell the human the agent has it.

Exit 0: sent, captures printed. Exit 3: --timeout passed with nothing sent. Exit 2: not a page.
"""
import argparse
import atexit
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import importlib.util

BIN = os.path.dirname(os.path.abspath(__file__))


def die(msg, code=2):
    print('flowviz wait: ' + msg, file=sys.stderr)
    sys.exit(code)


def captures_module():
    spec = importlib.util.spec_from_file_location('fvcaptures', os.path.join(BIN, 'flowviz-captures.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(prog='flowviz wait', description=__doc__.split('\n')[0])
    ap.add_argument('page', help='the built <NAME>.html the human has open, served')
    ap.add_argument('--timeout', type=float, metavar='MIN', help='give up after this many minutes (default: never)')
    a = ap.parse_args()

    html_path = os.path.abspath(os.path.expanduser(a.page))
    if not html_path.endswith('.html') or html_path.endswith('.src.html') or not os.path.isfile(html_path):
        die('give the built page: <NAME>.html')
    cm = captures_module()
    raw = open(html_path, encoding='utf-8', errors='replace').read()
    doc = cm.find_doc_id(raw, cm.parse_html(raw))
    if not doc:
        die('no doc id in %s' % a.page)
    base = os.path.dirname(html_path)
    send_path = os.path.join(base, doc + '.send.json')

    # say we are here, for as long as we are: serve reads this to tell the human the agent has it
    wdir = os.path.join(base, '.flowviz', 'wait')
    os.makedirs(wdir, exist_ok=True)
    pid_path = os.path.join(wdir, doc + '.pid')
    with open(pid_path, 'w') as f:
        f.write('%d\n' % os.getpid())

    def gone(*_):
        try:
            if open(pid_path).read().split()[0] == str(os.getpid()):
                os.unlink(pid_path)
        except (OSError, IndexError):
            pass
    atexit.register(gone)
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: sys.exit(130))

    shown = html_path.replace(os.path.expanduser('~'), '~', 1)
    if not os.path.exists(send_path):
        print('flowviz wait: watching %s for send to agent%s' % (
            shown, ' (up to %g min)' % a.timeout if a.timeout else ''), flush=True)
    deadline = time.time() + a.timeout * 60 if a.timeout else None
    try:
        while not os.path.exists(send_path):
            if deadline and time.time() > deadline:
                print('flowviz wait: nothing sent in %g min. Run it again to keep waiting, or read what is there '
                      'with flowviz captures %s' % (a.timeout, shown))
                return 3
            time.sleep(1)
    except KeyboardInterrupt:
        return 130

    # take the send, so it is read once: it moves to .flowviz/sent/<doc>/<UTC>.json
    try:
        rec = json.load(open(send_path, encoding='utf-8'))
    except (OSError, ValueError):
        rec = {}
    sent_dir = os.path.join(base, '.flowviz', 'sent', doc)
    os.makedirs(sent_dir, exist_ok=True)
    stamp = (rec.get('at') or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())).replace('-', '').replace(':', '')
    shutil.move(send_path, os.path.join(sent_dir, stamp + '.json'))
    gone()

    at = rec.get('at')
    when = cm.fmt_time(at)[0] if at else 'just now'
    print('The human pressed send to agent on %s at %s%s.' % (
        shown, when, ' (pressed %d times since the last wait; this is the latest)' % rec['n'] if rec.get('n', 1) > 1 else ''))
    print('Read every capture, note, added step and to-do below, then act on them.\n', flush=True)
    r = subprocess.run([sys.executable, os.path.join(BIN, 'flowviz-captures.py'), html_path])
    return 0 if r.returncode == 0 else r.returncode


if __name__ == '__main__':
    sys.exit(main())
