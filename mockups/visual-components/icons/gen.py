#!/usr/bin/env python3
"""Generate template/icons.svg: illustrated component icons (48 grid) + the unchanged UI glyphs.
Run: python3 mockups/visual-components/icons/gen.py template/icons.svg   (ui.svgfrag holds the UI glyphs)

Markup shorthand inside an icon:  fill="@b"  stroke="@y"  ->  style="fill:var(--i2)" etc.
Paints: a deep · b main · c light (all three follow the box's kind)
        w white · g signal green · y gold · r coral · m metal dark · n metal light · k ink
        l line: ink on light paper, light on dark paper — for strokes that stand alone, not around a fill
Ink outlines are currentColor, so the <use> element's `color` sets them.
"""
import math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAINT = {'a': 'var(--i1)', 'b': 'var(--i2)', 'c': 'var(--i3)', 'w': 'var(--iw)', 'g': 'var(--ion)',
         'y': 'var(--igold)', 'r': 'var(--ired)', 'm': 'var(--imetal)', 'n': 'var(--imetal2)', 'k': 'currentColor', 'l': 'var(--iline)'}


def f(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def poly(pts):
    return 'M' + 'L'.join('%s %s' % (f(x), f(y)) for x, y in pts) + 'Z'


def gear(cx, cy, ro, ri, n, top=0.36, root=0.62):
    step = 2 * math.pi / n
    pts = []
    for i in range(n):
        a = i * step - math.pi / 2
        for r, d in ((ri, -root), (ro, -top), (ro, top), (ri, root)):
            pts.append((cx + r * math.cos(a + d * step / 2), cy + r * math.sin(a + d * step / 2)))
    return poly(pts)


def cube(cx, cy, s, fills=('c', 'b', 'a')):
    k = 0.866 * s
    T, UR, LR, B, LL, UL, C = ((cx, cy - s), (cx + k, cy - s / 2), (cx + k, cy + s / 2), (cx, cy + s),
                               (cx - k, cy + s / 2), (cx - k, cy - s / 2), (cx, cy))
    return ('<path fill="@%s" d="%s"/><path fill="@%s" d="%s"/><path fill="@%s" d="%s"/>'
            % (fills[0], poly([T, UR, C, UL]), fills[1], poly([UL, C, B, LL]), fills[2], poly([C, UR, LR, B])))


def doc(x, y, w, h, fold=8, fill='w', foldfill='b'):
    """a page with a folded top-right corner"""
    r = 2
    body = ('M%s %sh%sl%s %sv%sa%s %s 0 0 1-%s %sH%sa%s %s 0 0 1-%s-%sV%sa%s %s 0 0 1 %s-%sz'
            % (f(x + r), f(y), f(w - r - fold), f(fold), f(fold), f(h - fold - r), r, r, r, r, f(x + r), r, r, r, r,
               f(y + r), r, r, r, r))
    fd = 'M%s %sv%sa2 2 0 0 0 2 2h%sz' % (f(x + w - fold), f(y), f(fold - 2), f(fold - 2))
    return '<path fill="@%s" d="%s"/><path fill="@%s" d="%s"/>' % (fill, body, foldfill, fd)


# the same cloud everywhere a cloud appears
CLOUD = 'M14 37a8.5 8.5 0 0 1-1.6-16.85A12 12 0 0 1 35.3 16.9 10 10 0 0 1 34 37z'

ICONS = {}

# ── clients ──────────────────────────────────────────────────────────────────
ICONS['user'] = '''
<path fill="@b" d="M7.5 43c0-9.6 7.4-15.5 16.5-15.5S40.5 33.4 40.5 43z"/>
<path stroke-width="2.2" d="M19 28.6l5 5.4 5-5.4"/>
<circle fill="@c" cx="24" cy="15.5" r="9"/>'''

ICONS['users'] = '''
<path fill="@c" d="M23 37c0-7.4 5-12 11.5-12S46 29.6 46 37z"/>
<circle fill="@c" cx="34.5" cy="15" r="6.8"/>
<path fill="@b" d="M2.5 43c0-9 6.4-14.5 14.5-14.5S31.5 34 31.5 43z"/>
<circle fill="@c" cx="17" cy="18.5" r="8"/>'''

ICONS['desktop'] = '''
<path fill="@m" d="M20 33.5h8l1.6 6.5H18.4z"/>
<rect fill="@m" x="12.5" y="39" width="23" height="4.5" rx="2.2" stroke-width="2.2"/>
<rect fill="@m" x="4" y="6" width="40" height="28" rx="3.5"/>
<rect fill="@b" x="8" y="10" width="32" height="20" rx="1.5" stroke-width="2"/>
<path stroke="@w" stroke-width="2.8" d="M13 15.5l4.5 4-4.5 4M21.5 24.5h6"/>'''

ICONS['laptop'] = '''
<rect fill="@m" x="8.5" y="8" width="31" height="23" rx="3"/>
<rect fill="@b" x="12" y="11.5" width="24" height="16" rx="1" stroke-width="2"/>
<path stroke="@w" stroke-width="2.6" d="M16 16h9M16 21h5"/>
<path fill="@n" d="M3.5 31h41v2.5a4.5 4.5 0 0 1-4.5 4.5H8a4.5 4.5 0 0 1-4.5-4.5z"/>
<path stroke-width="2" d="M19.5 31v1a1.5 1.5 0 0 0 1.5 1.5h6a1.5 1.5 0 0 0 1.5-1.5v-1"/>'''

ICONS['mobile'] = '''
<rect fill="@m" x="12.5" y="3.5" width="23" height="41" rx="5"/>
<rect fill="@b" x="16" y="9" width="16" height="27.5" rx="1.5" stroke-width="2"/>
<path stroke="@w" stroke-width="2.6" d="M19.5 15h9M19.5 20.5h5"/>
<path stroke="@n" stroke-width="2.6" d="M21.5 40.5h5"/>'''

ICONS['devices'] = '''
<rect fill="@m" x="4.5" y="8" width="28" height="20" rx="2.5"/>
<rect fill="@b" x="8" y="11.5" width="21" height="13" rx="1" stroke-width="2"/>
<path fill="@n" d="M1.5 28h34v1.5a3.5 3.5 0 0 1-3.5 3.5H5a3.5 3.5 0 0 1-3.5-3.5z"/>
<rect fill="@m" x="30.5" y="15.5" width="15" height="27" rx="3.5"/>
<rect fill="@c" x="33.5" y="19.5" width="9" height="16" rx="1" stroke-width="2"/>'''

ICONS['browser'] = '''
<rect fill="@w" x="4" y="7" width="40" height="34" rx="4"/>
<path fill="@b" d="M4 11a4 4 0 0 1 4-4h32a4 4 0 0 1 4 4v5H4z"/>
<circle fill="@w" cx="9.5" cy="11.5" r="1.6" stroke-width="1.6"/>
<circle fill="@w" cx="14.5" cy="11.5" r="1.6" stroke-width="1.6"/>
<rect fill="@c" x="9" y="21" width="12" height="14" rx="1.5" stroke-width="2"/>
<path stroke-width="2.6" d="M26 23h12M26 28.5h12M26 34h7"/>'''

ICONS['terminal'] = '''
<rect fill="@m" x="4" y="7" width="40" height="34" rx="4"/>
<path fill="@n" d="M4 11a4 4 0 0 1 4-4h32a4 4 0 0 1 4 4v4H4z"/>
<circle fill="@w" cx="9.5" cy="11" r="1.5" stroke-width="1.5"/>
<circle fill="@w" cx="14.5" cy="11" r="1.5" stroke-width="1.5"/>
<path stroke="@b" stroke-width="3.2" d="M11 22l5.5 4.5-5.5 4.5"/>
<path stroke="@w" stroke-width="3.2" d="M21 33.5h9"/>'''

ICONS['code'] = '''
<rect fill="@w" x="4" y="7" width="40" height="34" rx="4"/>
<path fill="@b" d="M4 11a4 4 0 0 1 4-4h32a4 4 0 0 1 4 4v4H4z"/>
<circle fill="@w" cx="9.5" cy="11" r="1.5" stroke-width="1.5"/>
<circle fill="@w" cx="14.5" cy="11" r="1.5" stroke-width="1.5"/>
<path stroke-width="3" d="M17.5 21.5l-6 6 6 6M30.5 21.5l6 6-6 6"/>
<path stroke="@a" stroke-width="3" d="M26.5 20l-5 15"/>'''

# ── edge, network ────────────────────────────────────────────────────────────
ICONS['gateway'] = '''
<rect fill="@b" x="7" y="13" width="8.5" height="29" rx="2"/>
<rect fill="@b" x="32.5" y="13" width="8.5" height="29" rx="2"/>
<rect fill="@a" x="3.5" y="6" width="41" height="8.5" rx="2.5"/>
<path fill="@c" d="M15.5 24.5h7.5V19l9.5 9-9.5 9v-5.5h-7.5z"/>'''

ICONS['lb'] = '''
<path stroke="@l" d="M14 24h21M14 24L35 10M14 24l21 14"/>
<circle fill="@b" cx="11" cy="24" r="7.5"/>
<circle fill="@w" cx="11" cy="24" r="2.6" stroke-width="2"/>
<circle fill="@c" cx="38.5" cy="9.5" r="5"/>
<circle fill="@c" cx="38.5" cy="24" r="5"/>
<circle fill="@c" cx="38.5" cy="38.5" r="5"/>'''

ICONS['cdn'] = '''
<path stroke="@l" stroke-width="2.4" d="M13 36v4.5M24 36v4.5M35 36v4.5"/>
<circle fill="@c" cx="13" cy="42" r="2.8" stroke-width="2"/>
<circle fill="@c" cx="24" cy="42" r="2.8" stroke-width="2"/>
<circle fill="@c" cx="35" cy="42" r="2.8" stroke-width="2"/>
<g transform="translate(0 -4)"><path fill="@b" d="%s"/><path stroke="@w" stroke-width="2.6" d="M16 27.5h16M19 32h10"/></g>''' % CLOUD

ICONS['cloud'] = '''
<g transform="translate(0 1)"><path fill="@c" d="%s"/>
<path fill="@b" stroke="none" d="M8.6 30.5a8.5 8.5 0 0 0 5.4 6.5h20a10 10 0 0 0 9.8-8z"/>
<path fill="none" d="%s"/>
<path stroke="@w" stroke-width="2.6" d="M17.5 19.5a7.5 7.5 0 0 1 5-3.4"/></g>''' % (CLOUD, CLOUD)

ICONS['globe'] = '''
<circle fill="@c" cx="24" cy="24" r="18.5"/>
<path fill="@b" d="M24 5.5c5 5 7.5 11.2 7.5 18.5S29 37.5 24 42.5c-5-5-7.5-11.2-7.5-18.5S19 10.5 24 5.5z"/>
<path stroke-width="2.2" d="M5.5 24h37M8.5 14.5h31M8.5 33.5h31"/>'''

ICONS['firewall'] = '''
<rect fill="@b" x="4" y="9" width="40" height="31" rx="3"/>
<path stroke-width="2.2" d="M4 19.3h40M4 29.6h40M17 9v10.3M31 9v10.3M10 19.3v10.3M24 19.3v10.3M38 19.3v10.3M17 29.6V40M31 29.6V40"/>
<path fill="@r" stroke-width="2.2" d="M34 3.5c4.5 3 6.5 6 6.5 9.2a5.5 5.5 0 0 1-11 0c0-1.6.8-3.2 2-4.2.2 1.5 1 2.4 2.2 2.6-.6-2.6-.4-5 .3-7.6z"/>'''

# ── compute ──────────────────────────────────────────────────────────────────
ICONS['server'] = '''
<rect fill="@b" x="7" y="4.5" width="34" height="11.5" rx="3"/>
<rect fill="@b" x="7" y="18.25" width="34" height="11.5" rx="3"/>
<rect fill="@b" x="7" y="32" width="34" height="11.5" rx="3"/>
<circle fill="@g" cx="13.5" cy="10.25" r="2.3" stroke-width="2"/>
<circle fill="@g" cx="13.5" cy="24" r="2.3" stroke-width="2"/>
<circle fill="@g" cx="13.5" cy="37.75" r="2.3" stroke-width="2"/>
<path stroke-width="2.7" d="M25.5 8.4v0M30 8.4v0M34.5 8.4v0M25.5 12.1v0M30 12.1v0M34.5 12.1v0M25.5 22.15v0M30 22.15v0M34.5 22.15v0M25.5 25.85v0M30 25.85v0M34.5 25.85v0M25.5 35.9v0M30 35.9v0M34.5 35.9v0M25.5 39.6v0M30 39.6v0M34.5 39.6v0"/>'''

ICONS['service'] = cube(24, 24, 19)

ICONS['function'] = '''
<rect fill="@b" x="5" y="5" width="38" height="38" rx="9"/>
<path stroke="@w" stroke-width="3.6" d="M15.5 13h3.6c1.5 0 2.4.7 3 2.1l7.3 19.4h3.1M23.5 23L16 35"/>'''

ICONS['worker'] = ('<path fill="@b" d="%s"/><circle fill="@w" cx="19" cy="19" r="5"/>'
                   '<path fill="@c" d="%s"/><circle fill="@w" cx="34.5" cy="34.5" r="3"/>'
                   % (gear(19, 19, 15.5, 11.5, 9), gear(34.5, 34.5, 10.5, 7.5, 7)))

ICONS['gear'] = ('<path fill="@b" d="%s"/><circle fill="@c" cx="24" cy="24" r="10"/><circle fill="@w" cx="24" cy="24" r="4.5"/>'
                 % gear(24, 24, 20, 15, 10))

ICONS['chip'] = '''
<path stroke="@l" stroke-width="2.6" d="M17 4v6M24 4v6M31 4v6M17 38v6M24 38v6M31 38v6M4 17h6M4 24h6M4 31h6M38 17h6M38 24h6M38 31h6"/>
<rect fill="@b" x="10" y="10" width="28" height="28" rx="4"/>
<rect fill="@c" x="16.5" y="16.5" width="15" height="15" rx="2"/>
<path stroke="@a" stroke-width="2.4" d="M21 21h6v6h-6z" stroke-linejoin="round"/>'''

ICONS['relay'] = '''
<path fill="@b" d="M5 11.5h24.5V5.5l13 9.5-13 9.5v-6H5z"/>
<path fill="@c" d="M43 29.5H18.5v-6l-13 9.5 13 9.5v-6H43z"/>'''

ICONS['api'] = ('<path stroke="@l" stroke-width="2.6" d="M9.5 9.5l7 7M38.5 9.5l-7 7M9.5 38.5l7-7M38.5 38.5l-7-7"/>'
                '<circle fill="@c" cx="8" cy="8" r="4"/><circle fill="@c" cx="40" cy="8" r="4"/>'
                '<circle fill="@c" cx="8" cy="40" r="4"/><circle fill="@c" cx="40" cy="40" r="4"/>'
                '<path fill="@b" d="%s"/><circle fill="@w" cx="24" cy="24" r="7.5"/>'
                '<path stroke-width="2.4" d="M22 21l-3 3 3 3M26 21l3 3-3 3"/>' % gear(24, 24, 16.5, 12.5, 9))

ICONS['agent'] = '''
<path stroke="@l" stroke-width="2.6" d="M24 11V7"/>
<circle fill="@y" cx="24" cy="5" r="2.6" stroke-width="2"/>
<rect fill="@c" x="4" y="18.5" width="5.5" height="11" rx="2"/>
<rect fill="@c" x="38.5" y="18.5" width="5.5" height="11" rx="2"/>
<path fill="@c" d="M13.5 44v-1.5a6 6 0 0 1 6-6h9a6 6 0 0 1 6 6V44z"/>
<rect fill="@b" x="9.5" y="10.5" width="29" height="25" rx="8"/>
<rect fill="@m" x="14" y="15.5" width="20" height="13" rx="5.5"/>
<circle fill="@c" stroke="none" cx="19.5" cy="22" r="2.6"/>
<circle fill="@c" stroke="none" cx="28.5" cy="22" r="2.6"/>'''

ICONS['llm'] = '''
<path fill="@b" d="M23.5 9.5C21.5 6.3 15.8 6.4 14.4 10.4 9.8 10.1 6.8 14.2 8.4 18.2 5.2 20.3 5.2 26 8.4 28 6.8 32.2 9.6 36.4 14 36.2c.9 4 6.4 5.6 9.5 2.5z"/>
<path fill="@c" d="M24.5 9.5c2-3.2 7.7-3.1 9.1.9 4.6-.3 7.6 3.8 6 7.8 3.2 2.1 3.2 7.8 0 9.8 1.6 4.2-1.2 8.4-5.6 8.2-.9 4-6.4 5.6-9.5 2.5z"/>
<path stroke-width="2.2" d="M14.4 10.4c.4 2.6 2.4 4.3 5.2 4.3M8.4 18.2c2.7-.5 5.4.6 6.3 3.3M8.4 28c2.6.4 5-.7 6-3.2M14 36.2c.4-3 2.4-4.7 5.2-4.7M33.6 10.4c-.4 2.6-2.4 4.3-5.2 4.3M39.6 18.2c-2.7-.5-5.4.6-6.3 3.3M39.6 28c-2.6.4-5-.7-6-3.2M34 36.2c-.4-3-2.4-4.7-5.2-4.7"/>'''

ICONS['spark'] = '''
<path fill="@b" d="M19 5c1.3 8.2 5 11.9 13.2 13.2C24 19.5 20.3 23.2 19 31.4 17.7 23.2 14 19.5 5.8 18.2 14 16.9 17.7 13.2 19 5z"/>
<path fill="@y" d="M35 25.5c.7 4.5 2.7 6.5 7.2 7.2-4.5.7-6.5 2.7-7.2 7.2-.7-4.5-2.7-6.5-7.2-7.2 4.5-.7 6.5-2.7 7.2-7.2z"/>
<path fill="@c" stroke-width="2" d="M36 5.5c.4 2.4 1.5 3.5 3.9 3.9-2.4.4-3.5 1.5-3.9 3.9-.4-2.4-1.5-3.5-3.9-3.9 2.4-.4 3.5-1.5 3.9-3.9z"/>'''

# ── data ─────────────────────────────────────────────────────────────────────
ICONS['db'] = '''
<path fill="@b" d="M9 11v26c0 2.8 6.7 5 15 5s15-2.2 15-5V11"/>
<path stroke="@c" stroke-width="3.2" d="M13.2 18.5v2.5M13.2 27v2.5M13.2 35.5v2"/>
<path d="M9 19.6c0 2.8 6.7 5 15 5s15-2.2 15-5M9 28.3c0 2.8 6.7 5 15 5s15-2.2 15-5"/>
<ellipse fill="@c" cx="24" cy="11" rx="15" ry="5"/>'''

ICONS['index'] = '''
<path fill="@b" d="M4.5 9v21c0 2.5 5.4 4.5 12 4.5s12-2 12-4.5V9"/>
<path d="M4.5 19.5c0 2.5 5.4 4.5 12 4.5s12-2 12-4.5"/>
<ellipse fill="@c" cx="16.5" cy="9" rx="12" ry="4.5"/>
<path stroke-width="8.5" d="M38 38l5 5"/><path stroke="@a" stroke-width="3.5" d="M38 38l5 5"/>
<circle fill="@w" cx="32" cy="32" r="9"/>
<path stroke="@c" stroke-width="2.6" d="M27.5 30.5a5 5 0 0 1 3-3.4"/>'''

ICONS['table'] = '''
<rect fill="@w" x="4.5" y="8" width="39" height="32" rx="4"/>
<path fill="@b" d="M4.5 12a4 4 0 0 1 4-4h31a4 4 0 0 1 4 4v5.5h-39z"/>
<path stroke-width="2.2" d="M4.5 17.5h39M4.5 25h39M4.5 32.5h39M17.5 17.5V40M30.5 17.5V40"/>'''

ICONS['cache'] = '''
<circle fill="@c" cx="24" cy="24" r="19.5"/>
<path fill="@b" d="M27.5 6.5L13 27h10l-3 14.5L35 21H25z"/>
<path stroke="@w" stroke-width="2.4" d="M24.5 13.5l-5 7"/>'''

ICONS['storage'] = '''
<path fill="@b" d="M7.5 12l3.6 27.3a4 4 0 0 0 4 3.5h17.8a4 4 0 0 0 4-3.5L40.5 12"/>
<path d="M9.3 25.5c3.7 1.9 8.8 2.9 14.7 2.9s11-1 14.7-2.9"/>
<ellipse fill="@c" cx="24" cy="12" rx="16.5" ry="5.5"/>'''

ICONS['search'] = '''
<path stroke-width="9" d="M30.5 30.5l10.5 10.5"/>
<path stroke="@b" stroke-width="4" d="M30.5 30.5l10.5 10.5"/>
<circle fill="@c" cx="20" cy="20" r="13.5"/>
<path stroke="@w" stroke-width="2.8" d="M12.5 17.5a8 8 0 0 1 5-5.5"/>'''

ICONS['queue'] = '''
<path fill="@b" d="M1.5 18.5h5V13l7 11-7 11v-5.5h-5z"/>
<path fill="@b" d="M35.5 18.5h4V13l7 11-7 11v-5.5h-4z"/>
<rect fill="@w" x="8.5" y="11" width="30" height="26" rx="6.5"/>
<rect fill="@b" x="12.5" y="15" width="4.4" height="18" rx="1.4" stroke-width="2"/>
<rect fill="@b" x="18.3" y="15" width="4.4" height="18" rx="1.4" stroke-width="2"/>
<rect fill="@b" x="24.1" y="15" width="4.4" height="18" rx="1.4" stroke-width="2"/>
<rect fill="@c" x="29.9" y="15" width="4.4" height="18" rx="1.4" stroke-width="2"/>'''

ICONS['box'] = (cube(24, 24, 19) + '<path fill="@w" stroke-width="2" d="%s"/><path fill="@w" stroke-width="2" d="%s"/>'
                % (poly([(13.2, 11.2), (17.6, 8.6), (34.5, 18.3), (30, 20.9)]),
                   poly([(30, 20.9), (34.5, 18.3), (34.5, 37.3), (30, 39.9)])))

ICONS['cubes'] = cube(15, 33.5, 10.5) + cube(33, 33.5, 10.5) + cube(24, 15.5, 10.5)

ICONS['vector'] = ('<path stroke="@l" stroke-width="2.4" d="M24 5.5v6M41 15l-5 3M41 33l-5-3M24 42.5v-6M7 33l5-3M7 15l5 3"/>' + cube(24, 24, 12.5)
                   + ''.join('<circle fill="@b" cx="%s" cy="%s" r="3" stroke-width="2"/>' % (f(x), f(y))
                             for x, y in ((24, 4), (42.5, 14), (42.5, 34), (24, 44), (5.5, 34), (5.5, 14))))

# ── messaging ────────────────────────────────────────────────────────────────
ICONS['bell'] = '''
<path stroke="@l" stroke-width="3" d="M24 5.5v3.5"/>
<path fill="@c" d="M19 39.5a5 5 0 0 0 10 0z"/>
<path fill="@b" d="M11.5 34V22.5a12.5 12.5 0 0 1 25 0V34l3.5 4.5H8z"/>
<path stroke="@w" stroke-width="2.6" d="M17 22a7.5 7.5 0 0 1 4-6.2"/>'''

ICONS['mail'] = '''
<rect fill="@w" x="4.5" y="10" width="39" height="28" rx="4"/>
<path stroke-width="2.2" d="M6 36.5l13.5-12M42 36.5l-13.5-12"/>
<path fill="@b" d="M8.5 10h31a3.5 3.5 0 0 1 2.4 1L24 26.5 6.1 11a3.5 3.5 0 0 1 2.4-1z"/>'''

ICONS['chat'] = '''
<path fill="@b" d="M10 6.5h28a5 5 0 0 1 5 5v16a5 5 0 0 1-5 5H22.5L13 40.5v-8h-3a5 5 0 0 1-5-5v-16a5 5 0 0 1 5-5z"/>
<path stroke="@w" stroke-width="4" d="M16 19.5v0M24 19.5v0M32 19.5v0"/>'''

# ── money ────────────────────────────────────────────────────────────────────
ICONS['card'] = '''
<rect fill="@b" x="4" y="9.5" width="40" height="29" rx="4"/>
<path fill="currentColor" d="M4 16h40v6H4z"/>
<rect fill="@y" x="9" y="27" width="8.5" height="6.5" rx="1.5" stroke-width="2"/>
<path stroke="@w" stroke-width="2.6" d="M23 30.5h15"/>'''

ICONS['bank'] = '''
<path fill="@c" d="M5 16.5L24 5.5l19 11z"/>
<rect fill="@w" x="9" y="20" width="5" height="15" rx="1"/>
<rect fill="@w" x="17" y="20" width="5" height="15" rx="1"/>
<rect fill="@w" x="26" y="20" width="5" height="15" rx="1"/>
<rect fill="@w" x="34" y="20" width="5" height="15" rx="1"/>
<rect fill="@b" x="5" y="16.5" width="38" height="4" rx="1.5"/>
<rect fill="@b" x="3.5" y="35" width="41" height="7" rx="2"/>'''

# ── security ─────────────────────────────────────────────────────────────────
ICONS['lock'] = '''
<path stroke-width="8.5" d="M15.5 21v-6a8.5 8.5 0 0 1 17 0v6"/>
<path stroke="@n" stroke-width="3.5" d="M15.5 21v-6a8.5 8.5 0 0 1 17 0v6"/>
<rect fill="@y" x="8.5" y="19.5" width="31" height="24" rx="4.5"/>
<circle fill="currentColor" stroke="none" cx="24" cy="29.5" r="3.4"/>
<path stroke-width="3.2" d="M24 31v5.5"/>'''

ICONS['key'] = '''
<path stroke-width="8.5" d="M21 27L40.5 7.5M35 13l4.5 4.5M29.5 18.5l3.5 3.5"/>
<path stroke="@y" stroke-width="3.5" d="M21 27L40.5 7.5M35 13l4.5 4.5M29.5 18.5l3.5 3.5"/>
<circle fill="@y" cx="15" cy="33" r="10.5"/>
<circle fill="@w" cx="12.5" cy="35.5" r="3.2"/>'''

ICONS['shield'] = '''
<path fill="@b" d="M24 4.5l16.5 6v11.5c0 10.5-7 18.2-16.5 22.2C14.5 40.2 7.5 32.5 7.5 22V10.5z"/>
<path fill="@c" stroke="none" d="M24 8.3l12.8 4.7v9c0 8.2-5.2 14.4-12.8 18z"/>
<path fill="@y" stroke-width="2.2" d="M26.5 12.5l-9 13h6.5l-2.5 10 9-13.5H24z"/>'''

ICONS['cert'] = (doc(6, 4, 28, 38, 8) + '<path stroke-width="2.6" d="M11 20h17M11 26h12"/>'
                 '<circle fill="@g" cx="34.5" cy="34.5" r="9.5"/><path stroke="@w" stroke-width="3" d="M30 34.5l3.2 3.2 5.6-5.8"/>')

ICONS['alert'] = '''
<path fill="@y" d="M21 7.2L4.4 36.4A3.5 3.5 0 0 0 7.4 41.5h33.2a3.5 3.5 0 0 0 3-5.1L27 7.2a3.4 3.4 0 0 0-6 0z"/>
<path stroke-width="3.4" d="M24 17v11"/><circle fill="currentColor" stroke="none" cx="24" cy="34.2" r="2.2"/>'''

# ── time ─────────────────────────────────────────────────────────────────────
ICONS['clock'] = '''
<circle fill="@b" cx="24" cy="24" r="19.5"/>
<circle fill="@w" cx="24" cy="24" r="14"/>
<path stroke-width="3" d="M24 15.5V24l6 3.8"/>
<circle fill="currentColor" stroke="none" cx="24" cy="24" r="2"/>'''

ICONS['hourglass'] = '''
<path fill="@w" d="M14 6h20v6.5c0 5-4 8.5-7 11.5 3 3 7 6.5 7 11.5V42H14v-6.5c0-5 4-8.5 7-11.5-3-3-7-6.5-7-11.5z"/>
<path fill="@b" stroke="none" d="M17.6 39.5c.8-3.6 3.6-5.8 6.4-7.4 2.8 1.6 5.6 3.8 6.4 7.4z"/>
<path fill="@b" stroke="none" d="M18.2 13.5h11.6c-.7 2.6-3 4.7-5.8 6.7-2.8-2-5.1-4.1-5.8-6.7z"/>
<rect fill="@n" x="10" y="2.5" width="28" height="5" rx="2" stroke-width="2.2"/><rect fill="@n" x="10" y="40.5" width="28" height="5" rx="2" stroke-width="2.2"/>'''

ICONS['calendar'] = '''
<rect fill="@w" x="5.5" y="9" width="37" height="33.5" rx="4"/>
<path fill="@b" d="M5.5 13a4 4 0 0 1 4-4h29a4 4 0 0 1 4 4v6h-37z"/>
<path stroke="@l" stroke-width="3" d="M15 5v8M33 5v8"/>
<rect fill="@c" x="27" y="30" width="8" height="7" rx="1.5" stroke-width="2"/>
<path stroke-width="3.2" d="M13 26v0M20 26v0M27 26v0M34 26v0M13 33.5v0M20 33.5v0"/>'''

# ── documents ────────────────────────────────────────────────────────────────
ICONS['file'] = doc(9, 4, 30, 40, 10) + '<path stroke-width="2.6" d="M15 22h18M15 28.5h18M15 35h11"/>'

ICONS['docs'] = (doc(15, 3, 26, 34, 8, 'c', 'c') + doc(7, 10, 26, 35, 8)
                 + '<path stroke-width="2.6" d="M12 27h15M12 33h15M12 39h9"/>')

ICONS['json'] = doc(9, 4, 30, 40, 10) + '<path stroke-width="2.6" d="M20 21.5c-2.4 0-3 1-3 2.6v2.3c0 1.2-.8 1.8-2 1.8 1.2 0 2 .6 2 1.8v2.3c0 1.6.6 2.6 3 2.6M28 21.5c2.4 0 3 1 3 2.6v2.3c0 1.2.8 1.8 2 1.8-1.2 0-2 .6-2 1.8v2.3c0 1.6-.6 2.6-3 2.6"/>'

ICONS['folder'] = '''
<path fill="@b" d="M4.5 12a3 3 0 0 1 3-3h10.2l4.3 4.5h18.5a3 3 0 0 1 3 3V38a3 3 0 0 1-3 3h-33a3 3 0 0 1-3-3z"/>
<path fill="@c" d="M4.5 20.5a3 3 0 0 1 3-3h33a3 3 0 0 1 3 3V38a3 3 0 0 1-3 3h-33a3 3 0 0 1-3-3z"/>'''

ICONS['book'] = '''
<path fill="@b" d="M2.5 14v29h18c1.6 1.7 5.4 1.7 7 0h18V14z"/>
<path fill="@w" d="M24 13c-5-4.2-11.5-5.3-18.5-3.6v27.8c7-1.7 13.5-.6 18.5 3.6z"/>
<path fill="@w" d="M24 13c5-4.2 11.5-5.3 18.5-3.6v27.8c-7-1.7-13.5-.6-18.5 3.6z"/>
<path stroke-width="2.2" d="M10 17c3.5-.4 7 .2 10 1.8M10 23.5c3.5-.4 7 .2 10 1.8M10 30c3.5-.4 7 .2 10 1.8M28 18.8c3-1.6 6.5-2.2 10-1.8M28 25.3c3-1.6 6.5-2.2 10-1.8M28 31.8c3-1.6 6.5-2.2 10-1.8"/>'''

ICONS['checklist'] = '''
<rect fill="@w" x="8" y="4.5" width="32" height="39" rx="4"/>
<path stroke="@b" stroke-width="3.6" d="M25 15h9M25 25h9M25 35h6"/>
<path stroke-width="2.6" d="M13.5 15l2.6 2.6 4.4-5M13.5 25l2.6 2.6 4.4-5M13.5 35l2.6 2.6 4.4-5"/>'''

ICONS['check'] = '''
<rect fill="@w" x="8.5" y="7" width="31" height="36.5" rx="4"/>
<path fill="@b" d="M16.5 4.5h15a1.5 1.5 0 0 1 1.5 1.5v4.5a2 2 0 0 1-2 2H17a2 2 0 0 1-2-2V6a1.5 1.5 0 0 1 1.5-1.5z"/>
<path stroke-width="3.4" d="M16 27l5.5 5.5L32.5 21"/>'''

# ── observe, build ───────────────────────────────────────────────────────────
ICONS['chart'] = '''
<rect fill="@w" x="4.5" y="6" width="39" height="36" rx="4"/>
<rect fill="@c" x="11" y="25" width="6" height="11" rx="1" stroke-width="2.2"/>
<rect fill="@b" x="21" y="17" width="6" height="19" rx="1" stroke-width="2.2"/>
<rect fill="@a" x="31" y="21" width="6" height="15" rx="1" stroke-width="2.2"/>
<path stroke-width="2.4" d="M10 13.5l7.5 3.5 7-5 9.5 2.5"/>'''

ICONS['pulse'] = '''
<path fill="@m" d="M20 33.5h8l1.6 6.5H18.4z"/>
<rect fill="@m" x="12.5" y="39" width="23" height="4.5" rx="2.2" stroke-width="2.2"/>
<rect fill="@w" x="4" y="6" width="40" height="28" rx="3.5"/>
<rect fill="@b" x="8" y="10" width="32" height="20" rx="1.5" stroke-width="2"/>
<path stroke="@w" stroke-width="2.8" d="M11 21h6l3-6 4.5 11 3.5-7 2 2h7"/>'''

ICONS['eye'] = '''
<path fill="@w" d="M3 24S10.5 11.5 24 11.5 45 24 45 24 37.5 36.5 24 36.5 3 24 3 24z"/>
<circle fill="@b" cx="24" cy="24" r="8"/>
<circle fill="currentColor" stroke="none" cx="24" cy="24" r="3.3"/>
<circle fill="@w" stroke="none" cx="26.6" cy="21.4" r="1.5"/>'''

ICONS['tool'] = '''
<g transform="matrix(1.75 0 0 1.75 3 3)" stroke-width="1.45"><path fill="@b" d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></g>'''

ICONS['plugin'] = '''
<path stroke-width="8" d="M18 5v8M30 5v8"/><path stroke="@n" stroke-width="3" d="M18 5v8M30 5v8"/>
<path stroke-width="8" d="M24 33v10"/><path stroke="@c" stroke-width="3" d="M24 33v10"/>
<path fill="@b" d="M11 13h26v7a13 13 0 0 1-26 0z"/>
<path stroke="@w" stroke-width="2.6" d="M16.5 20.5a8 8 0 0 0 3.5 6"/>'''

ICONS['workflow'] = '''
<path stroke="@l" d="M12 18v13.5M12 24h19"/>
<rect fill="@b" x="5" y="5" width="14" height="13" rx="3"/>
<rect fill="@c" x="29" y="17.5" width="14" height="13" rx="3"/>
<rect fill="@c" x="5" y="30" width="14" height="13" rx="3"/>'''

ICONS['git'] = '''
<path stroke="@l" stroke-width="3" d="M13 13v22M35 18c0 9-9 10.5-20 15"/>
<circle fill="@b" cx="13" cy="10" r="5.5"/>
<circle fill="@b" cx="13" cy="38" r="5.5"/>
<circle fill="@c" cx="35" cy="14" r="5.5"/>'''

ICONS['target'] = '''
<circle fill="@w" cx="21" cy="27" r="17"/>
<circle fill="@b" cx="21" cy="27" r="11"/>
<circle fill="@w" cx="21" cy="27" r="5.5"/>
<path stroke="@l" stroke-width="3" d="M21 27L38.5 9.5"/>
<path fill="@y" stroke-width="2.2" d="M36 5.5l1.5 5.5 5.5 1.5-4 4-5.5-1.5-1.5-5.5z"/>
<circle fill="currentColor" stroke="none" cx="21" cy="27" r="2"/>'''

ICONS['bulb'] = '''
<path fill="@y" d="M24 4a13.5 13.5 0 0 0-7.8 24.5c1.3 1 2.1 2.4 2.1 4V33.5h11.4V32.5c0-1.6.8-3 2.1-4A13.5 13.5 0 0 0 24 4z"/>
<path fill="@n" d="M18.3 33.5h11.4v4.5a3 3 0 0 1-3 3h-5.4a3 3 0 0 1-3-3z"/>
<path stroke-width="2.2" d="M18.5 37.3h11M20.5 22l3.5 3.5 3.5-3.5M24 25.5v8"/>
<path stroke="@w" stroke-width="2.6" d="M16.5 15.5a8 8 0 0 1 4.2-5"/>'''

ORDER = ['user', 'users', 'desktop', 'laptop', 'mobile', 'devices', 'browser', 'terminal', 'code',
         'gateway', 'lb', 'cdn', 'cloud', 'globe', 'firewall',
         'server', 'service', 'function', 'worker', 'gear', 'chip', 'relay', 'api',
         'agent', 'llm', 'spark',
         'db', 'index', 'table', 'cache', 'storage', 'search', 'queue', 'box', 'cubes', 'vector',
         'bell', 'mail', 'chat', 'card', 'bank',
         'lock', 'key', 'shield', 'cert', 'alert',
         'clock', 'hourglass', 'calendar',
         'file', 'docs', 'json', 'folder', 'book', 'checklist', 'check',
         'chart', 'pulse', 'eye', 'tool', 'plugin', 'workflow', 'git', 'target', 'bulb']
assert sorted(ORDER) == sorted(ICONS), set(ORDER) ^ set(ICONS)


def paint(markup):
    def tag(m):
        t = m.group(0)
        st = []
        for prop in ('fill', 'stroke'):
            mm = re.search(r'\s%s="@(\w)"' % prop, t)
            if mm:
                st.append('%s:%s' % (prop, PAINT[mm.group(1)]))
                t = t.replace(mm.group(0), '')
        if st:
            t = re.sub(r'(/?>)$', ' style="%s"\\1' % ';'.join(st), t)
        return t
    out = re.sub(r'<[a-z]+\b[^>]*>', tag, markup)
    return re.sub(r'\s*\n\s*', '', out)


def build():
    sym = []
    for name in ORDER:
        body = paint(ICONS[name])
        sym.append('<symbol id="i-%s" viewBox="0 0 48 48"><g fill="none" stroke="currentColor" stroke-width="2.5" '
                   'stroke-linecap="round" stroke-linejoin="round">%s</g></symbol>' % (name, body))
    ui = open(os.path.join(HERE, 'ui.svgfrag')).read().strip()
    head = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true" focusable="false">\n'
            '<!-- FLOW_VIZ icon sprite.\n'
            '     Components (node "icon"): drawn on a 48 grid, ink outlines on flat fills. The ink is currentColor;\n'
            '     the fills are paints the box sets: --i1 deep, --i2 main, --i3 light (from its kind), and the fixed\n'
            '     --iw white, --ion green, --igold gold, --ired coral, --imetal/--imetal2 hardware, and --iline for a stroke\n'
            '     that stands alone (ink on light paper, light on dark). draw.css owns them all. A new icon follows suit:\n'
            '     a 48 viewBox, one <g> carrying the ink stroke (2.5, round), fills as style="fill:var(--i2)" and the like.\n'
            '     ' + ' '.join(ORDER[:33]) + '\n'
            '     ' + ' '.join(ORDER[33:]) + '.\n'
            '     UI glyphs (24 grid, currentColor stroke): play pause replay left right back sun moon auto motion info copy x zoom. -->\n')
    return head + '\n'.join(sym) + '\n' + ui + '\n</svg>\n'


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'icons.svg')
    open(out, 'w').write(build())
    print('wrote', out, len(ORDER), 'components')
