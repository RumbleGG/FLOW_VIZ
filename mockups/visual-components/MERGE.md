# Merging `visual-components` → `detail-slot-pr-helper` → `main`

**For the agent finishing 3.5.0 on `detail-slot-pr-helper`.** This branch restyles every drawing (boxes,
icons, connections, zones, badges, sequence view, drawer) after the ByteByteGo infographics the human shared.
It changes **no spec field, cap, icon name or grid size**, so your 3.5.0 features (detail slot, `status`
tags, cap tiers, PR helpers, figures) merge with it cleanly in substance. The goal of this guide: once both
are on `main`, **everything from both branches is still there**.

The guidance below comes from a **trial merge**: a snapshot of your uncommitted working tree (25 modified
files + 34 untracked, `VERSION` 3.5.0, taken 2026-10-18) committed in a throwaway worktree, with this branch
merged on top. With the resolutions below, all six deliverables built and **audited clean** with `--browser`:
`examples/checkout`, `examples/deploy`, `examples/pr/PR-418`, `PLAN`, `detail-pr/DETAIL_PR`, and this
folder's report. Your status tags, including a `removed` strike-through, render correctly in the new style.

What the branch holds:

| Commit | What |
|---|---|
| `f18a770` | the restyle: `template/icons.svg`, `template/draw.css`, `template/draw.js`, docs, this report |
| `099a64c` | each box's icon and label centred as one group |
| the two `Stamp…` commits | reference builds rebuilt with a clean sha |

The full picture of what changed, with every icon and two example diagrams, is the report beside this file:
`mockups/visual-components/VISUAL_COMPONENTS.html` (serve the folder with `bin/flowviz serve`).

---

## 1. Order of operations

- [ ] **Commit and push your 3.5.0 work on `detail-slot-pr-helper`.** The branch on GitHub was created from
      your local ref only, which still points at `main` (`cd77785`); none of your uncommitted work was pushed.
      Your next push is a plain fast-forward.
- [ ] **Merge this branch locally**, not in the GitHub editor: five of the conflicting files are built pages,
      which are rebuilt, never hand-merged.

  ```sh
  cd ~/Projects/FLOW_VIZ
  git fetch origin
  git merge --no-ff origin/visual-components
  ```

- [ ] Resolve the four source conflicts as in section 2, and take either side of the built pages (section 3).
- [ ] Set the version (section 4), rebuild and audit everything (section 5), run the retention check (section 6).
- [ ] Commit the merge, then a `Stamp the reference builds with the 3.6.0 commit` commit as usual, and push
      `detail-slot-pr-helper`. GitHub marks this PR merged on its own once its commits are in the base.
- [ ] Merge `detail-slot-pr-helper` into `main`, tag `v3.5.0` and `v3.6.0` as the history dictates, push the tags.

## 2. The four source conflicts

### `template/draw.js` · `drawNode()`: the one real code conflict

Your side draws the `removed` strike-through from a fixed `b.x + 55`. This branch no longer has a fixed label
position: the icon and label are one group `g.cnt`, centred in the box, and the group slides (CSS
`--sx`) to centre on the tech line when the Labels layer is on. **Keep this branch's lines, and add your
strike-through after the x positions are set, from the label's own x, inside `lg`** so it lifts and slides
with the label:

```js
      fit(t, LABEL_ROOM);
      var lw = textW(t), tw = 0, tt = null;
      if (n.tech) {
        tt = el('text', { class: 'tech', y: b.cy + 14 }, cg);
        tt.textContent = n.tech;
        fit(tt, LABEL_ROOM);
        tw = textW(tt);
      }
      var x0 = b.cx - (ICON + IGAP + lw) / 2, x1 = b.cx - (ICON + IGAP + Math.max(lw, tw)) / 2;
      ico.setAttribute('x', f(x0));
      t.setAttribute('x', f(x0 + ICON + IGAP));
      if (tt) tt.setAttribute('x', f(x0 + ICON + IGAP));
      if (x1 < x0 - 0.5) cg.style.setProperty('--sx', f(x1 - x0) + 'px');
      if (ns === 'removed') {
        var tx0 = x0 + ICON + IGAP, sx = t.getComputedTextLength() || lw;
        el('line', { class: 'strike', x1: f(tx0), y1: f(b.cy + 0.5), x2: f(tx0 + sx), y2: f(b.cy + 0.5) }, lg);
      }
```

Everything else in `draw.js` merged automatically and was checked: your `STATUS`, `TIER`, `statusOf()`,
the `.nstat` foot tag, the tiered `audit()` and the list-returning `shrunkLabels()` all sit beside this
branch's `textW()`, `zoneTag()`, `ICON`/`IGAP`, `PAINTS` and the drawer's `dr-ico illus` class without edits.

### `CLAUDE.md` · the *What lives where* table

Keep **this branch's** `template/icons.svg` row and **your** `template/report.src.html` row (the one that
mentions the detail slot).

### `AGENTS.md` · the spec bullet list

Keep **this branch's** `icon` bullet (65 icons listed by family) and **your** *Optional fields* bullet (the one
that adds `status`).

### `CHANGELOG.md`

Keep both entries. Rename this branch's heading

``## Unreleased — branch `visual-components` · one outlined, illustrated look for every drawing``

to `## 3.6.0 — <date> · one outlined, illustrated look for every drawing` and put it **above** your 3.5.0 entry.

## 3. Built pages: rebuild, never hand-merge

`PLAN.html`, `examples/checkout/checkout.html`, `examples/deploy/DEPLOY.html`,
`mockups/todo-steps/DEPLOY-PROTO.html` and `mockups/todo-steps/TODO-STEPS.html` conflict because both sides
rebuilt them. Take either side, then rebuild all of them in section 5:

```sh
git checkout --theirs PLAN.html examples/checkout/checkout.html examples/deploy/DEPLOY.html mockups/todo-steps/DEPLOY-PROTO.html mockups/todo-steps/TODO-STEPS.html
```

`template/draw.css` and `SPEC.md` merge without conflict. Still run section 6: a merge that silently took one
side of `draw.css` would drop the whole restyle.

## 4. Version

`VERSION` does not conflict (this branch never changed it), so it stays at your 3.5.0. Set it to **3.6.0**:
a minor bump, because nothing here changes a cap or the card's shape. If 3.5.0 has not shipped yet, folding
both into one release is also fine, as long as both changelog entries survive word for word.

## 5. Rebuild and audit: every line must say `result: clean`

```sh
cd ~/Projects/FLOW_VIZ
for f in examples/checkout/checkout.src.html examples/deploy/DEPLOY.src.html examples/pr/PR-418.src.html PLAN.src.html mockups/visual-components/VISUAL_COMPONENTS.src.html; do bin/flowviz build "$f"; done
sh mockups/todo-steps/build.sh
for f in examples/checkout/checkout.html examples/deploy/DEPLOY.html examples/pr/PR-418.html PLAN.html mockups/visual-components/VISUAL_COMPONENTS.html; do bin/flowviz audit --browser "$f" | tail -1; done
```

`detail-pr/DETAIL_PR` was untracked in your tree; if it ends up in the repo, build and audit it too (it was
clean in the trial). Then look at one drawing in light, dark and print, as `CLAUDE.md` asks (`?theme=dark`).

## 6. Retention check: run after the merge, before you push

Every line must print `ok`. A `MISSING` means one side was dropped; restore it from that branch.

```sh
cd ~/Projects/FLOW_VIZ && python3 - <<'EOF'
import re
read = lambda p: open(p, encoding='utf-8').read()
js, css, svg = read('template/draw.js'), read('template/draw.css'), read('template/icons.svg')
checks = [
  ('65 component icons + 14 UI glyphs', len(re.findall(r'<symbol id="i-', svg)) == 79),
  ('icons are 48-grid illustrations', svg.count('viewBox="0 0 48 48"') == 65),
  ('kind icon paints (-p / -l)', '--client-p:' in css and '--threat-l:' in css),
  ('fixed icon paints and --iline', all(t in css for t in ('--i-ink:', '--iline:', '--igold:', '--imetal:'))),
  ('.k-* classes set --i1..--i3', '.k-client{--k:var(--client);--k-bg:var(--client-bg);--k-bd:var(--client-bd);--i1:' in css),
  ('box: 2px kind outline, no shadow', '.fv-drawing .node .shape{fill:var(--k-bg);stroke:var(--k);stroke-width:2;' in css),
  ('centred icon + label group slides', '.node .cnt{' in css and "class: 'cnt'" in js and 'function textW' in js),
  ('chevron arrowheads', '.edge .head{fill:none;stroke:' in css and 'an open chevron' in js),
  ('dotted zones with a pill tag', '.zone .zbox{' in css and '.zone .ztag{' in css and 'function zoneTag' in js),
  ('zone audit measures the pill', 'var w = t.getComputedTextLength() + 2 * ZPAD;' in js),
  ('step badges ringed in ink', 'stepno circle{fill:var(--flow);stroke:var(--i-ink)' in css),
  ('plain canvas, no dot grid', '.fv-grid{background:none}' in css),
  ('drawing title bar', 'h1.fv-title::before' in css),
  ('drawer shows the box icon on its kind', 'dr-ico illus k-' in js and '.dr-ico.illus{' in css),
  ('Copy HTML keeps icon paints', 'var PAINTS' in js),
  ('3.5.0 status tags kept', 'STATUS = {' in js and '.nstat rect' in css),
  ('3.5.0 cap tiers kept', 'TIER = {' in js),
  ('removed strike-through uses the label x', "var tx0 = x0 + ICON + IGAP" in js),
]
for name, ok in checks: print('%-8s %s' % ('ok' if ok else 'MISSING', name))
EOF
```

If `template/icons.svg` was damaged in a merge, regenerate it (byte-identical to this branch's):

```sh
python3 mockups/visual-components/icons/gen.py template/icons.svg
```

## 7. Easy to lose later

- **New code inside a box** goes relative to the label's x (`x0 + ICON + IGAP`), never `b.x + 55`, and inside
  `cg` when it should slide with the label. The label may use `LABEL_ROOM` = 110px.
- **`zoneTag()`** is the one geometry for a zone's pill: `drawZone()` draws it and `zoneLabelHits()` measures
  it. Change one, and the browser audit measures a label where it is not drawn.
- **A new `kind`** needs five colours in both theme blocks (`--x`, `-bg`, `-bd`, `-p`, `-l`) and a `.k-x` rule
  that sets `--i1/--i2/--i3`, or its icons fall back to blue.
- **A new icon** follows the sprite header: a 48 viewBox, ink stroke 2.5 on one `<g>`, fills as
  `style="fill:var(--i2)"` and the like; or add it to `icons/gen.py` and regenerate.
- **Never fix a look in a deliverable's markup**: it lands in `template/`, per `CLAUDE.md`.
