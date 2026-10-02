# Changelog

Semver for the standard. A cap change, or a change to the card's shape, is a **major** bump. Every
deliverable's footer names the version that built it.

## 3.1.0 — 2026-10-01 · steps and to-dos the human adds mid-run

**Added steps.** A playbook no longer has to be right the first time. Mid-run the human can add the step
that was missing: from a line on every seam between steps (on hover), **+ step after** at each step's foot,
the prompt under a `fail` or `error` chip (*Was a step missing before b4?*), or **+ Add a step** at the end of
a playbook. One composer serves all four: one sentence, read or write, an optional command, with the audit's
rules shown as meters while typing — 20 words, one sentence, ASCII, one line, and a **fix** for smart quotes —
and nothing refused. The step is drawn in place in violet, dashed, with a proofreader's caret where it went
in, and behaves as any step does: gate, copy, paste box, Done, re-run, dimming, progress, evidence. Its id is
the step it follows plus the next free letter — `b3a`, then `b3b`; `b0a` before a row's first step — so no
number moves and nothing pasted is orphaned. With no rule yet its chip reads `captured`, not `no match`.

**To-dos.** One section at the end of every report, one line at rest: *add to write-up* (the write-up is
missing something; **make it a step** turns it into one, closing the to-do as `→ b1a`) and *do after* (a
task once the run is over). `t` anywhere, or **+ to-do** in the pill with its open count, adds one tied to the
step you were last in, without the page moving. Rows and steps carry a small violet count at rest.

**Back to the agent.** State schema 5 adds `added` and `todos`; an added step's output uses the ordinary
`captures` and `steps` keys. Removing writes a tombstone (`gone`), because the load merge is a union and a
deleted key would come back from the other store. **Copy captures for agent** and **Save evidence** carry
both. `flowviz captures` prints an added step in place, marked `+`, a removed one apart, and the to-dos
after the playbooks; `--json` has them too. **`flowviz fold`** (new) writes added steps into the source
after the step they followed, under the same ids, chaining `data-after`, with the template's own words left
where only the agent can write — so the audit blocks until the pass and fail lines, the regexes and any gate
are written; `--todo t2` folds an *add to write-up* to-do the same way. `flowviz results` names unfolded
steps and open to-dos; `flowviz relabel` moves `added` and to-do anchors with the steps they hang off.

**Audited.** The naming check accepts a folded step's id (`b3a` between `b3` and `b4`), and the audit notes,
without failing, any added step or open to-do in the sidecar beside the page. What the human added is left
out of every cap: added steps, the counts on rows and steps, and the to-do section's height.

**Fixed: an older page could erase newer state.** `merge()` copied only the keys it knew, so a page built
before a key existed dropped it on its next save. It now keeps keys it does not know, and `flowviz serve`
carries over any top-level key a save leaves out; serve's index lists open to-dos per page.

Minor: no cap changed, and the audit fails nothing it passed. The design was approved from the prototype in
`mockups/todo-steps/`.

## 3.0.0 — 2026-09-29 · letters for rows, numbers for steps, and values that carry

**Names.** Rows are lettered a, b, c… in order, and a step's id is its row's letter and its number in that
row: `b1`, `b2` … `bn`; a Results section's steps are `r1`, `r2`…. The page shows the id where the counter
was, so "look at b3" names one step on screen, in the sidecar and in the agent's read-back. Mnemonic ids
(`push`, `bb`) are retired: **the audit now fails a report off the convention**, which is why this is a
major version. `flowviz new` and `flowviz results` write conforming ids.

**`flowviz relabel`** moves an existing report onto the convention without losing what was pasted. It
rewrites every reference in the source, backs the sidecar up and re-keys its captures, ticks, emits and open
rows, and records the move in a `flowviz-relabel` meta, so state a browser still holds is re-keyed the next
time the page opens. A tab left open from before the move is refused (`409`, pill *ids moved: reload*)
instead of writing the old ids back. PLAN and the deploy example were moved with it.

**Emits.** A value one step prints now reaches a later step's command without being retyped:
`data-emit="VER=VERSION ([0-9][0-9.]+)"` on the producing step's paste box, `{{b1.VER}}` in the later
command. The value is the capture group of the last match, re-derived on every paste and load and cached in
the sidecar under `emits` (schema 4). Until it exists the token shows as written and copy refuses — *b1 has
not run* — and a value that is not paste-safe is refused the same way, so nothing unresolved reaches a
console. The build and the audit fail a token that cannot resolve and a regex without exactly one capture
group; the audit warns when the producer is not on the consumer's `data-after` chain, and on any `PASTE_`
placeholder left in a command. `flowviz captures` prints each value beside its capture
(`b1 -> PREV=2.2.4`). A report with no `data-emit` renders, copies and saves as before. In the deploy
example, the rollback now pins the exact version `b1` printed instead of trusting `rollout undo`.

Fixed on the way: the collapsed row's ⧉ copied nothing, and the agent export dropped a closed step's
command and sentence, because Chrome reports no `innerText` inside a closed `<details>`. Both now read the
text directly.

## 2.1.0 — 2026-09-28 · Copy HTML

Every drawing gains a **Copy HTML** button for pasting it into a wiki page. The snippet carries its own
scoped styles (`.fvx`, generated by the build from flow.css and draw.css, so it cannot restyle the host
page), the icon sprite, the spec and depth, the runtime, and a still fallback: an SVG with every colour and
result mark inlined, plus a `<details>` per box. Where the wiki allows scripts it is fully interactive —
drawer, peeks, flows, segments, notes; where scripts are stripped the picture and details still show; it has
no blank lines, so markdown wikis keep it whole. Several snippets on one page share one runtime.

Known limit: the snippet's styles cannot leak out, but a host page that styles generic class names the
live drawing also uses (`.edge`, `.node`, `.row`) can reach in. The still fallback is immune — it carries no
classes. Mounting the live drawing in a shadow root would close this.

## 2.0.1 — 2026-09-28 · the drawer fits its content

The details drawer was a fixed 440px, and its body was a grid with no column limit: one wide code block or
table stretched the column past the panel's edge, cutting off everything to its right, and three-column
tables wrapped into fragments. Now the column is locked to the panel; the drawer starts at 520px and widens
to fit its widest code block or table, up to min(720px, 55vw); tables that still do not fit scroll inside
their own box, code wraps, and on a phone the sheet spans the full width.

## 2.0.0 — 2026-09-28 · results, and quieter drawings

**Results.** When the human has run a playbook, the agent closes the report with a `section.results` placed
above the card: the outcome (`pass`, `fail`, `blocked`, `inconclusive`) with its chip, a claim, a summary, one
drawing marking where the run passed or failed, next actions, and a gated step that moves the finished folder
into the archive. `flowviz results` starts it from the sidecar — outcome and counts worked out, the diagram
begun from the spine drawing, the archive step written — and never overwrites one. Audited: its own caps,
≤150 words and ≤1.5 screens, with the report's three screens measured without it. `examples/deploy/` is the
worked example, with its captures committed.

**Result marks on drawings.** `"result": "pass" | "fail" | "error"` on a box, connection or flow step: green
with a ✓, red with a ✕ at the stop, amber with a ⚠ near the source — the verdict vocabulary, drawn.

**Flows are off by default.** A drawing is boxes and connections with no flow chips, step badges or Walk
through unless the human asks for a walkthrough; its connections still move, in plain ink. `flowviz new`
scaffolds none; `--flows N` adds them.

**Done moved.** The `Done` button sits in the bottom-right corner of each step, beside the verdict chip.

Major, because the flows cap loosened from 1–3 to 0–3: the standard's rule counts any cap change as major,
so a looser drawing is a visible decision rather than a quiet one.

## 1.0.0 — 2026-09-28 · every row says what it is for

A report's six rows read as six claims with no sign of whether to read them or act on them. Now:
- **Row kinds.** Every row carries `data-kind` — `context`, `finding`, `record` (read), `investigation`,
  `test`, `change`, `rollback` (action), or `decision` — and `flow.js` draws the label at the start of the
  summary, all labels one width so the claims line up. The label is injected, never written.
- **Section headers.** `<h2 class="sec">` groups the rows: ≤3 per report, ≤4 words each, and no row
  before the first. Quiet micro-labels with a hairline, counted in words at rest.
- **Audited.** New caps (section headers, longest header, rows before the first header, rows with no
  kind) and an author check that fails a label that does not match what the row holds: an action with
  nothing to run, or a read-only row holding steps.

Major, because the spine's shape changed: a 0.6.0 report still renders, but fails the audit until its rows
have kinds and headers. `flowviz new report` scaffolds both.

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
- FLOW_VIZ is its own repository again (`github.com/RumbleGG/FLOW_VIZ`), so footers carry the sha
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
