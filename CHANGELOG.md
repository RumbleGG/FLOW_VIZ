# Changelog

Semver for the standard. A cap change, or a change to the card's shape, is a **major** bump. Every
deliverable's footer names the version that built it.

## 0.6.0 — 2026-09-28 · drawings

Rebuilt on a new machine from the 0.5.1 brief, `AGENTS.md`, `SPEC.md` and `PLAN.html`, and extended with a
second deliverable. Report caps are unchanged, which is why this is a minor bump.

**Added — drawings.** A system, or a segment of one, written as a JSON spec (boxes on a grid, connections,
up to three flows of one-sentence steps) plus HTML depth, and drawn by a shared runtime:
- the look approved in `mockups/checkout-system.html`: pastel component tints by `kind`, icons, zones,
  numbered step badges, a dot-grid canvas, and a night theme designed alongside it;
- a fixed motion grammar — dashes for sync calls, slower dots for async messages, two lanes for two-way
  traffic, red with a ✕ for a failing call, grey and still for connections outside the selected flow;
- four gestures as four layers: look, hover (peek ≤25 words), click (drawer, unlimited, with a note for the
  agent), play (a labelled packet walks the flow);
- Map, Sequence and Spec views from one spec; segments with ghost boxes and a zoom transition;
- drawing caps: ≤12 boxes (≤9 as a report spine), ≤4 zones, 1–3 flows of ≤9 steps, one-sentence steps,
  ≤60 words on the canvas, 0 crossings, 0 labels shrunk to fit, 0 zone labels crossed.

**Added — toolkit.** `flowviz new drawing`; `flowviz audit` reads every drawing spec (caps, ids, references,
vocabulary, grid, straight-through-a-box) and `--browser` measures the layout caps in headless Chrome;
`flowviz captures` reads back drawing notes alongside step captures and re-derives verdicts from the
current rules; `examples/checkout/`.

**Changed.**
- State schema 3 adds `notes`; schema 1 and 2 sidecars load unchanged.
- The sidecar PUT is relative to the page, so a report in a subfolder saves beside itself.
- `flow.js` now injects the status pill rather than every report carrying it in markup.
- `flow.js` exposes `window.FLOWVIZ`, the state API drawings use.
- The report spine defaults to a drawing, and `.spine .fv-drawing` counts as the one diagram.
- FLOW_VIZ is its own repository again (private, `github.com/RumbleGG/FLOW_VIZ`), so footers carry the sha
  that built them and a working rollback command.
- Mermaid is no longer vendored. Sequence views come from drawing specs; state diagrams are not supported
  yet.

**Fixed.**
- Vitals used `.vitals div`, which also boxed the number and label inside each tile.
- Pasting a capture did not un-dim a step waiting on it with `data-after`.

**Found by testing the entry doc.** A fresh agent given only `AGENTS.md` produced a clean OAuth drawing in
two rounds, and reported what the doc left it to guess. From that: zone `cols`/`rows` are documented as
inclusive; a `threat` kind (red, broken edge) and an `alert` icon let an attacker look like one; the browser
audit fails a zone label that a connection runs through; connection `label` ≤16 and `ms` ≤20 chars are
capped; `ms` is documented as optional; and rule 9 now separates replacing someone's document (don't)
from rebuilding your own (fine — `build` keeps history).

**Found by the first audit.** The approved mockup broke a cap it had never been measured against: a fact of
26 characters against a cap of 24. The drawing changed; the cap did not.

## 0.1.0 – 0.5.1 · reports (previous machine)

Built on the previous machine; the history lives there. In order: the three layers and the caps, both themes
and the build step (0.1); the served round trip into a sidecar (0.2); notes, re-runs, hashed evidence and
print (0.3); an interpreter-error tier so a crashed command can no longer read as `pass`, verdicts
re-derived on load, and the paste-safety author checks (0.4); the `Done` button, the twin verdict chip,
Pacific display times and headless measurement of screens at rest (0.5).
