# FLOW_VIZ — for agents changing the toolkit

Only here to produce a report or a drawing for work in another folder? **Read `AGENTS.md` instead** — it
is self-contained, and it is the shorter read. This file is for changing the toolkit or the standard.

Every change made here is a change to **every** deliverable cut from this toolkit. When the human dislikes
a detail in one report or drawing, the fix lands in `template/` or `bin/` and reaches the others on a
plain rebuild. Never fix a single deliverable's markup for something the runtime should do.

That makes changing the toolkit work for an **Opus agent, or equivalent**: one edit reaches every deliverable,
and the invariants below span several files. The Supervisor that `AGENTS.md` sends in when a run stops
behaving lands here once it has shown the fault is the runtime's: reproduce on `PLAN.html` and `examples/`
first, fix in `template/` or `bin/`, rebuild and audit all three, and never patch the deliverable instead. A
Sonnet agent, or equivalent, may carry out an edit this file spells out and rebuild; a Haiku agent, or
equivalent, may run the test block at the end and relay it word for word.

## What lives where

| Path | Owns | Notes |
|---|---|---|
| `SPEC.md` | the standard: caps, vocabulary, schemas | a cap change is a **major** version bump |
| `AGENTS.md` | the entry doc for agents working elsewhere | self-contained; budget its length |
| `template/flow.css` | core tokens + every report component | journal light / traditional dark |
| `template/flow.js` | core runtime: state, sidecar sync, pill, theme, copy, print, `?audit=1`, report components | exposes `window.FLOWVIZ` |
| `template/draw.css` | the drawing component + the drawing-page neutrals | uses core token names |
| `template/draw.js` | the drawing runtime: layout, routing, motion, peek, drawer, walkthrough, sequence, segments, notes | mounts every `figure.fv-drawing` |
| `template/icons.svg` | the icon sprite (`<symbol id="i-<name>">`) | inlined at build; components on a 48 grid, painted by `draw.css` (its header says how) |
| `template/report.src.html` | report skeleton with scaffold markers, the detail slot between `detail:begin/end` | `flowviz new report` expands it; `--detail` keeps the slot |
| `template/drawing.src.html` | drawing skeleton | `flowviz new drawing` fills it |
| `template/pr.src.html` | a PR helper's blocks: vitals, rows, one file's disclosure | `flowviz pr` cuts from it; the audit reads its words |
| `bin/flowviz` | the one entry point; bare = cheat sheet, with paths computed from where it lives | pure passthroughs |
| `bin/flowviz-*.py` | new, build, audit, serve, captures, fold, results, relabel, shot, pr | stdlib Python 3 only; `shot` and `audit --browser` drive the Chrome on this Mac |
| `PLAN.src.html` → `PLAN.html` | the toolkit's own plan, written to the standard | must audit clean |
| `examples/` | reference deliverables: checkout (drawing), deploy (Results), pr (a PR helper, with its `pr/` inputs and `checkout/`) | rebuilt and audited with every change |

## The build contract

A `.src.html` is a full HTML document holding content only. It carries two metas and three markers:

```html
<meta name="flowviz-doc" content="checkout">      <!-- the doc id: sidecar name and state key. Never changes. -->
<meta name="flowviz-kind" content="drawing">      <!-- report | drawing -->
<meta name="flowviz-relabel" content='[…]'>       <!-- only after `flowviz relabel`: every id move, oldest first -->
<!-- flowviz:head -->   in <head>: build puts the boot script and the inlined flow.css + draw.css here
<!-- flowviz:foot -->   in <body>: build puts the provenance footer here
<!-- flowviz:js -->     before </body>: build puts the icon sprite, flow.js and draw.js here
```

The build also writes `<script type="text/plain" id="fvEmbedCss">`: flow.css and draw.css transformed into
one stylesheet scoped to `.fvx` (token blocks moved from `:root`, page-level rules dropped, core components
prefixed), which `draw.js` puts into every **Copy HTML** snippet. Keep draw.css's own rules namespaced
`fv-`: anything else is prefixed with `.fvx` by the transform, and a host page's classes must never collide.

The build also inlines **every `<img>` outside a comment** (`inline_images()`): the file is read relative to
the source, becomes a data URI, and the tag is stamped with `data-file`, `data-sha256`, `data-bytes`, `width`
and `height`; a `figure.shot`'s caption becomes its `alt` when none is written. A missing or remote file, a
non-image, or anything over 10 MB fails the build. The source keeps the path, so a rebuild re-reads the file.

The boot script build writes is, in order: `window.FLOW={doc,version,kind,built}`; then, from
`localStorage['flowviz:'+doc]`, set `data-theme` (`light`/`dark`, resolving `auto` with
`matchMedia`), set `data-kind` from `FLOW.kind`, and add class `still` to `<html>` when
`ui.motion === false`. Every report and drawing gets all four assets, always — a report can gain a
drawing without a template change, and a fix to any asset reaches everything on rebuild.

## The runtime contract

`flow.js` runs first and exposes:

```js
window.FLOWVIZ = {
  doc, version, kind,          // from window.FLOW
  state,                       // the live state object, schema 6 (SPEC §6). Mutate, then save().
  save(),                      // debounced 700 ms: localStorage always, PUT to the sidecar when served
  onHydrate(fn),               // fn() after a sidecar load merged newer state into `state`
  auditHooks: [],              // push fn(add); add(label, actual, capText, ok) adds a ?audit=1 row
  ptTime(iso, withSeconds),    // "14:05 PDT"
  flash(button, text)          // brief label swap on a button
};
```

- The sidecar PUT goes to the **relative** URL `_flow/state/<doc>`, so a page in a subfolder writes the
  sidecar beside itself. The server resolves that path under its root and refuses anything outside it.
- `flow.js` injects the pill (`#flowPill`) when the markup has none. `draw.js` adds its **Motion**
  button to the pill, before the state button.
- The `?audit=1` panel is built on `window` `load`, after `draw.js` has mounted and registered hooks. Report
  rows appear only when `kind !== 'drawing'`. Screens at rest is always measured: cap 3 for a report, 2
  for a drawing page. The panel is `div.audit#flowAudit[data-violations]`; every row is
  `<tr data-k="<label>" data-ok="1|0">` with cells label, actual, cap, verdict. `flowviz audit --browser`
  parses exactly that.
- **Copy captures for agent** and **Save evidence** include `state.notes`.
- `flow.js` owns every `.copy` button (a document-level handler). `draw.js` never uses the `.copy` class
  for its own buttons; it uses `.fv-btn`. Code inside a drawing's depth uses the core components:
  `div.cmd` for something to run, `div.cmd.fig` for something to read.

`draw.js` mounts every `figure.fv-drawing`: one JSON spec (`script[type="application/json"]`), one
`div.fv-depth`. `data-mode="page"` renders the page header (chip, crumbs, `h1` title, lede); any other
figure renders a compact `figcaption` (title, lede). Instances share one drawer, one scrim and one toast.
Keyboard (`← → Space Esc`) goes to the most recently touched instance, else the first. Per-drawing view
state lives in `state.ui.draw[<id>]`; motion is page-wide in `state.ui.motion`. Notes live in
`state.notes['<id>/[<segment>/]<node|edge|step>:<elementId>'] = {text, at}`. Without `window.FLOWVIZ` the
runtime still works, keeping state in `localStorage` only.

The runtime's audit hook adds, per drawing: boxes, zones, flows, longest flow, words on canvas at rest,
crossings, connections through boxes, and labels shrunk to fit — crossings and boxes-hit computed for the
root canvas **and every segment** from the routing itself, labels measured in a hidden scratch SVG. Then
`gestures()` tries the two gestures for real on the root canvas: every peek shown and placed by the
runtime's own code (**peeks cut off**: by the window or a clipping ancestor), every box clicked at its
middle through `elementFromPoint` (**clicks that open no drawer**), then again wherever the open drawer
leaves it reachable (**second clicks that keep it open**: `toggleDrawer()` closes the drawer when `shows()`
says it already holds that element). Then `chipsCovered()` turns on Labels, Timings and both, in every flow,
and reads every connection's chip the same way (**labels covered or covering**: something drawn over it, or
it on a box, step, mark, zone tag or chip). It puts back the scroll, view, layers, flow, Key and any
`<details>` it opened.

## Tokens

`flow.css` defines the core tokens (`--bg --paper --panel --panel2 --sunk --line --line2 --rule --fg
--dim --dim2 --acc --ok --warn --bad --mag` and their `…bg` tints, `--f-body --f-ui --f-mono --r --r2
--sh --grid`) for journal light on `:root` and traditional dark on `[data-theme="dark"]`.

`draw.css` adds component tokens — kind tints `--client --edge --service --data --stream --ext` each with
`-bg` and `-bd`, flow accents `--f1 --f2 --f3`, `--on-tint` — for light on `:root` and dark on
`[data-theme="dark"]`. On `[data-kind="drawing"]` (and its dark variant) it **overrides the core
neutrals** with the canvas/night palette, so a drawing page's pill, footer and drawer match its canvas.
Inside a report, a drawing uses the report's neutrals unchanged. Components read core names: canvas is
`--paper`, ink is `--fg`, secondary `--dim`, tertiary `--dim2`. The current flow's accent is the
instance variable `--flow`, set on the figure — never `--acc`, which is the page accent.

## Rules that are easy to break

- **Never rename an id** that a human may have typed against: doc ids, row and step ids, drawing ids, box,
  edge and flow-step ids. Renaming silently orphans their captures and notes. `flowviz relabel` is the one
  sanctioned move, and it is three pieces that must stay in step: the script rewrites the source and the
  sidecar, `upgrade()` in `flow.js` re-keys state a browser still holds, and `flowviz serve` answers `409`
  to a tab older than the sidecar's `relabel` stamp.
- **An emit is parsed three times** — `rulesFor()` in `flow.js`, `parse_emits()` in `bin/flowviz-audit.py`
  (which the build imports) and in `bin/flowviz-captures.py` — and the `{{step.NAME}}` token regex twice
  (`flow.js`, the audit). Change them together.
- **Row letters and step ids** (SPEC §1.2b) are checked by `naming_checks()` in the audit, written by
  `flowviz new` and `flowviz results`, and displayed by `flow.js` only for ids of that shape, so an older
  report keeps its counters until it is relabelled.
- **The error tier exists twice** — `CMD_ERR` in `flow.js` and in `bin/flowviz-captures.py`. Change both.
- **The figure caps exist twice** — `figure_checks()` in the audit and `buildAudit()` in `flow.js` (1 MB a
  figure, 6 MB a page). Change both. The audit's other figure checks read the built page, so an `<img>` the
  build did not inline is a failure there, never a broken picture in the human's browser.
- **The cap tiers exist twice** — `TIER` in `draw.js` and `TIERS` in the audit: every canvas, a spine (and
  a Results drawing), a detail. Change both, and the caps tables in SPEC §2.2 and AGENTS.md.
- **The detail slot is `body > div.detail`, found in three places** — `is_detail()` in the audit, `buildAudit()`
  in `flow.js` and `audit()` in `draw.js` — and written by `detail_slot()` in `flowviz new`, which `flowviz pr`
  reuses. A `div.detail` anywhere else is an ordinary div, so an older report that used the class audits as before.
- **`status` exists twice** — `STATUS` in `draw.js` (tag, Key, peek, drawer, Copy HTML) and `STATUSES` in the
  audit (vocabulary, the count). Change both. A status is ink only: never give it a hue a kind or a result uses.
- **A PR helper's inputs are parsed once.** `parse_diff()`, `expected_files()`, `file_at()`, `counts()` and the
  marker regex live in `flowviz-pr.py`; the audit imports that file (`pr_module()`), so fill and audit cannot
  disagree. The order is `pr.json`'s, never the diff's: that is GitHub's.
- **`template/pr.src.html` is read two ways.** `flowviz pr` cuts its `pr-vitals`, `pr-rows` and `prfile` blocks;
  the audit reads its words as placeholders, except the three section headers (`skip`), which are the recipe's
  own. Keep fixed words out of its rows and cells, or every PR helper fails on them; the four counted vitals
  are written by `pr.py` for that reason.
- **Screens at rest are compared unrounded** and shown rounded up to two decimals (`up2()` in `flow.js`), so a
  failing figure never reads as one that fits. The audit relays the page's own figure.
- **`CORE_OK` in the build decides which core components reach a wiki page** through Copy HTML. A report
  component that may sit inside a depth section (`figure.shot` is one) must be in it, or it arrives unstyled.
- **One viewer for two kinds of picture.** Evidence images (`openViewer`, `viewAt = {id, k}`) and figures
  (`openShot`, `viewAt = {shots, k}`) share `.ci-view`; its click and key handlers are bound on every page
  kind, in capture phase before the drawing's, because a figure in a depth section opens from inside the
  drawer and the viewer must own ← → and Esc while it is up.
- **Chrome often does not exit** after `--screenshot`, `--print-to-pdf` or `--dump-dom`. `shot` stops it once
  the PNG ends in its IEND chunk and has stopped growing; the audit stops it once `</html>` has arrived. A new
  Chrome call needs the same treatment, or it waits for a process that never ends.
- **An added step's id (`b3a`) is read in four places** — `flow.js` (where it is drawn, and the label),
  `naming_checks()` in the audit, `plan()` in relabel, and `flowviz fold` (with `place_added()` in
  captures). Change them together. Fold cuts its markup from the template's `step-ro`/`step-w` blocks and
  replaces only the placeholders it can fill, so the unfilled-slot check still catches the rest.
- **The peek lives on `<body>`, fixed to the window**, one per drawing, placed by `placePeek()`. Never put it
  back inside the stage: the stage's `overflow:hidden` cut off 8 of 9 peeks on a three-row spine. The
  audit's **peeks cut off** row catches exactly that. `browser_rows()` relays it, **clicks that open no
  drawer** and **labels covered or covering** only because its regex names `peek|click|covered`; a new
  gesture row needs its word there too.
- **A connection's chip lives in `S.layer.chips`, over everything but the packets in flight**, and
  `updateChips()` places it where it covers nothing, from `chipSpots()`. What it may never cover is collected
  as it is drawn: `S.obs` (boxes, their corner marks and status tags, zone tags, arrowheads), `S.bobs` (step
  discs) and `S.mobs` (result marks). Anything new drawn on the canvas must join one of them, and a new flow
  must place the chips again (`applyFlow()` does). The chip carries its connection's `hov sel near hot`
  through `edgeOn()`, never through the edge set it used to sit in.
- **What the human adds is never the agent's budget.** `buildAudit()` in `flow.js` leaves out
  `li.step.added`, `.row-mark` and `section.todo`; anything new the page draws from state must be left
  out the same way, or a busy run pushes a clean report over its caps.
- **A verdict has two values once a human sets one.** `verdict` is derived from the rules and re-derived on
  every load; `override.verdict` is the human's. Everything that judges a step reads the effective one
  (`effective()` in `flow.js`, `effective` from `step_capture_record()` in captures, which results uses), and
  everything that shows it shows both. `textHash` is FNV-1a over UTF-8, in `flow.js` and in captures: change both.
- **Pixels never go in the sidecar.** Images go to `PUT _flow/asset/<doc>/<sha256>.<ext>` and live in
  `<doc>.assets/`, named by hash, so no id names a file and nothing has to move when an id does. The page
  compresses anything over 10 MB before sending it; serve refuses anything over 10 MB, mislabelled or misnamed.
- **State keys are additive and never dropped.** `merge()` keeps keys it does not know, and serve carries
  over top-level keys a PUT leaves out. A removal is a tombstone (`gone`), because the merge is a union.
- **The unfilled-slot check compares against the templates.** Change a template's placeholder words and
  the audit follows automatically; keep every placeholder inside every cap, or a fresh scaffold fails on
  more than "unfilled slots".
- **No network, no install.** Stdlib Python, no CDN, no web fonts, icons inline.
- **A cap change is a major version bump**, recorded in `CHANGELOG.md` with its reason.

## Testing a change

```sh
cd ~/Projects/FLOW_VIZ
bin/flowviz build examples/checkout/checkout.src.html && bin/flowviz audit --browser examples/checkout/checkout.html
bin/flowviz build PLAN.src.html && bin/flowviz audit --browser PLAN.html
bin/flowviz new report "The toolkit scaffolds a report" --dir /tmp/fvt --rows 3 --steps 3
bin/flowviz build /tmp/fvt/FVT.src.html; bin/flowviz audit /tmp/fvt/FVT.html   # must fail on unfilled slots only
bin/flowviz shot "PLAN.html?audit=1" --out /tmp/fvt/shots/panel.png             # a PNG in seconds, Chrome stopped
bin/flowviz new report "The toolkit scaffolds a detail" --dir /tmp/fvd --detail 15
bin/flowviz build /tmp/fvd/FVD.src.html; bin/flowviz audit /tmp/fvd/FVD.html   # unfilled slots only, no OVER
bin/flowviz pr fill examples/pr/PR-418.src.html && bin/flowviz build examples/pr/PR-418.src.html
bin/flowviz audit --browser examples/pr/PR-418.html                              # clean; the source must not change
```

Every drawing's audit tries both gestures. To check that the check still bites, break a copy of a built
page beside it and audit the copy: put the peek back in `R.stage`, drop `openDrawer` from `toggleDrawer()`, lay a
transparent `::after` over `.fv-stage`, or hide `.fv-drawer`. Each must fail with its boxes named. For the
second click: make `toggleDrawer()` always open; it must fail **second clicks that keep it open**. For the
chips: put them back in the edge set, pass `chipSpots()` an empty `fixed`, or drop `updateChips()` from
`applyFlow()`; each must fail **labels covered or covering** with the chips named.

`PLAN.html` carries two figures (`shots/`): a build that drops one, or an audit that fails or stops measuring
them, is a regression. `examples/pr/` is the PR helper: a fill that changes its source, or an audit that stops
naming a dropped, reordered or miscounted file row, is a regression — mutate a copy beside it to check. The scaffold's row comment names `shots/ready.png`; a build that tries to inline it is
reading comments.

Look at every change in light, dark and print before calling it done. Headless Chrome reaches all three:
`--screenshot --window-size=1440,1000` on `…html?theme=dark` (the boot script and `flow.js` honour a
`?theme=light|dark` query flag for exactly this), and `--print-to-pdf` for print. This Mac has no
`timeout` command: run Chrome in the background and kill it on a timer.
