# FLOW_VIZ — for agents changing the toolkit

Only here to produce a report or a drawing for work in another folder? **Read `AGENTS.md` instead** — it
is self-contained, and it is the shorter read. This file is for changing the toolkit or the standard.

Every change made here is a change to **every** deliverable cut from this toolkit. When the human dislikes
a detail in one report or drawing, the fix lands in `template/` or `bin/` and reaches the others on a
plain rebuild. Never fix a single deliverable's markup for something the runtime should do.

## What lives where

| Path | Owns | Notes |
|---|---|---|
| `SPEC.md` | the standard: caps, vocabulary, schemas | a cap change is a **major** version bump |
| `AGENTS.md` | the entry doc for agents working elsewhere | self-contained; budget its length |
| `template/flow.css` | core tokens + every report component | journal light / traditional dark |
| `template/flow.js` | core runtime: state, sidecar sync, pill, theme, copy, print, `?audit=1`, report components | exposes `window.FLOWVIZ` |
| `template/draw.css` | the drawing component + the drawing-page neutrals | uses core token names |
| `template/draw.js` | the drawing runtime: layout, routing, motion, peek, drawer, walkthrough, sequence, segments, notes | mounts every `figure.fv-drawing` |
| `template/icons.svg` | the icon sprite (`<symbol id="i-<name>">`) | inlined at build |
| `template/report.src.html` | report skeleton with scaffold markers | `flowviz new report` expands it |
| `template/drawing.src.html` | drawing skeleton | `flowviz new drawing` fills it |
| `bin/flowviz` | the one entry point; bare = cheat sheet | pure passthroughs |
| `bin/flowviz-*.py` | new, build, audit, serve, captures, fold, results, relabel | stdlib Python 3 only |
| `PLAN.src.html` → `PLAN.html` | the toolkit's own plan, written to the standard | must audit clean |
| `examples/` | reference deliverables | rebuilt and audited with every change |

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
root canvas **and every segment** from the routing itself, labels measured in a hidden scratch SVG.

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
- **An added step's id (`b3a`) is read in four places** — `flow.js` (where it is drawn, and the label),
  `naming_checks()` in the audit, `plan()` in relabel, and `flowviz fold` (with `place_added()` in
  captures). Change them together. Fold cuts its markup from the template's `step-ro`/`step-w` blocks and
  replaces only the placeholders it can fill, so the unfilled-slot check still catches the rest.
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
```

Look at every change in light, dark and print before calling it done. Headless Chrome reaches all three:
`--screenshot --window-size=1440,1000` on `…html?theme=dark` (the boot script and `flow.js` honour a
`?theme=light|dark` query flag for exactly this), and `--print-to-pdf` for print. This Mac has no
`timeout` command: run Chrome in the background and kill it on a timer.
