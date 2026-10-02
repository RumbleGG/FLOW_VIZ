#!/usr/bin/env python3
"""Inject the prototype layer into pages flowviz build just wrote. Prototype only.

    inject.py PAGE.html [PAGE.html ...]

Puts proto.css at the end of <head> and proto.js at the end of <body>, after flow.js and
draw.js, so it reaches the page only through window.FLOWVIZ, as draw.js does. A page whose
doc id is deploy-proto also gets the demo run (seed-deploy.json): as window.FVPROTO_SEED,
and, when opened from disk with nothing stored, written to localStorage before flow.js
reads it. Served, build.sh writes the same seed as the sidecar, once.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return f.read()


def main(paths):
    css, js = read('proto.css'), read('proto.js')
    seed = json.loads(read('seed-deploy.json'))
    for path in paths:
        with open(path, encoding='utf-8') as f:
            page = f.read()
        if 'id="fvProtoCss"' in page:
            sys.exit('inject.py: %s already has the prototype layer: rebuild it first' % path)
        doc = re.search(r'<meta name="flowviz-doc" content="([^"]+)"', page).group(1)
        head = '<style id="fvProtoCss">\n' + css + '\n</style>\n'
        if doc == seed['doc']:
            head += ('<script>\n/* PROTOTYPE: the demo run. From disk with nothing stored, it goes to localStorage\n'
                     '   before flow.js reads it; served, build.sh wrote it as the sidecar instead. */\n'
                     'window.FVPROTO_SEED = ' + json.dumps(seed, ensure_ascii=True) + ';\n'
                     '(function () { try {\n'
                     '  if (/^https?:$/.test(location.protocol)) return;\n'
                     '  var k = "flowviz:" + window.FVPROTO_SEED.doc;\n'
                     '  if (localStorage.getItem(k) == null) localStorage.setItem(k, JSON.stringify(window.FVPROTO_SEED));\n'
                     '} catch (e) {} })();\n</script>\n')
        page = page.replace('</head>', head + '</head>', 1)
        i = page.rindex('</body>')
        page = page[:i] + '<script id="fvProtoJs">\n' + js + '\n</script>\n' + page[i:]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(page)
        print('inject.py: prototype layer -> %s (%s%s)' % (os.path.basename(path), doc,
              ', demo run' if doc == seed['doc'] else ''))


if __name__ == '__main__':
    main(sys.argv[1:])
