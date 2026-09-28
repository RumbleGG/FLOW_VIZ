# FLOW_VIZ — the standard

**Version 0.6.0** · normative. Where this document and a deliverable disagree, the deliverable is wrong.

Producing something? `AGENTS.md` is the self-contained short road and is enough on its own. Read this
file when you need the reasoning, the full schemas, or you are changing the standard.

FLOW_VIZ has **two deliverables and one toolkit**:

| Kind | What it is | The budget that defines it |
|---|---|---|
| **report** | a claim, the shape of the argument, evidence, and a checklist playbook the human runs and pastes into | the main idea lands in **two minutes** |
| **drawing** | a whole system, or one segment of it, with motion that shows where data goes | the system reads in **ten seconds**; the walkthrough takes one minute |

Both are one self-contained HTML file. Both put depth **exactly one gesture away** — never zero, never
three. Both are input devices: what the human types lands in a sidecar the agent reads back with a
command. A report may carry a drawing as its spine diagram; that is the same component, smaller.

---

## 1. Reports

### 1.1 Three layers

| Layer | Budget | Holds |
|---|---|---|
| **1 — Card** | one screen, never scrolls | status chip, claim-title, verdict, so-what, ≤5 vital tiles, ≤4 next actions |
| **2 — Spine** | one diagram + ≤6 collapsed rows | the shape of the thing, then one row per idea |
| **3 — Evidence** | unlimited | logs, stack traces, tables, transcripts, `file:line` citations — only inside rows |

Layer 3 is where verbosity is *welcome*. Nothing gets deleted to satisfy this standard; it moves down a layer.

### 1.2 Caps

Hard limits. An agent that cannot fit splits the report — it does not grow the budget.

| Slot | Cap | Why |
|---|---|---|
| Title | ≤70 chars, must contain a verb | `STO investigation` is a topic; `The 500 is confirmed partial trust` is a claim. |
| Verdict | ≤50 words | The one thing you would say in a hallway. |
| So what | ≤30 words | The consequence, or the decision it forces. Never a restatement. |
| Vitals | ≤5 tiles, number + label | Only measurements that carry the argument. |
| Next | ≤4 items, ≤14 words each | Each tagged `read-only` or `write`. No exceptions. |
| Diagram | exactly 1 in the spine | A drawing (`figure.fv-drawing`, ≤9 boxes), a hand-written `.dia` SVG, or `.mermaid`. Extra diagrams go inside rows. |
| Rows | ≤6 | Seven ideas is two reports. |
| Row summary | a claim with a verb, ≤14 words | The collapsed spine reads as a six-line argument. |
| Open at load | ≤1 row | The cap most often broken; it is what makes a file feel like a wall. |
| Step sentence | exactly one sentence, ≤20 words | A nine-step playbook reads as nine sentences. |
| Words at rest | ≤350 | Card text plus row summaries. The two-minute budget, made countable. |
| Screens at rest | ≤3 | Needs layout: measured by `?audit=1` or `flowviz audit --browser`. |

Structural checks measured alongside the caps, all must be 0: multi-sentence steps, steps with no
risk tag, write steps with no gate, untagged next items.

### 1.3 Checklist steps

A playbook step is **a checkbox, a number, and one sentence.** That is all that is visible.

| Rule | Detail |
|---|---|
| Description | Exactly one sentence, ≤20 words, stating what the step *establishes* or *changes*. |
| Command | Behind the disclosure. The `⧉` on the collapsed row copies it without opening anything, prompts stripped. |
| Blast radius | `data-risk="ro"` or `data-risk="w"` on every step. A `w` step blurs its command until the acknowledgement is ticked, and `⧉` refuses to copy it — it opens the step and says *tick the gate*. |
| Prereqs | `data-after="<id>"` dims the step until that one is done or captured. |
| Capture | Every step has a textarea, an exit-code field, a one-line note, and its sidecar key shown beside it. |
| Verdict | `data-pass` / `data-fail` regexes flip the chip on paste. Every literal is **word-anchored** (`\bFull\b`, never `Full`). |
| Re-run | Files the current capture into `runs[]` and clears the box. A second attempt never destroys the first. |
| Injected, never written | The `Done ☐` button at the foot of every step, the second verdict chip beside it, the status pill, and every displayed time. `flow.js` adds them, so a rebuild gives old reports new affordances. |

**Time.** Stored as ISO-8601 UTC everywhere (sidecar, exports, snapshot names). Shown in
`America/Los_Angeles`, labelled `PDT`/`PST`, with the ISO value on `title`. No report hand-formats a time.

### 1.4 The verdict vocabulary

Tested in this order; the earlier a tier, the less it presumes.

| Verdict | Chip | Means | Who it indicts |
|---|---|---|---|
| `error` | `error`, `--warn` | the interpreter rejected the command — parse failure or unresolved name | **the playbook**; the target was never asked |
| `fail` | `fail`, `--bad` | the command ran and the target said no | the system under test |
| `pass` | `pass`, `--ok` | `data-pass` matched and nothing above did | nothing |
| `saved` | `no match`, `--dim` | captured, matched neither regex | the step's pass condition |
| `null` | `—` | nothing pasted yet | — |

The `error` tier is deliberately narrow — these signatures and nothing else:

```
\bParserError\b   \bUnexpected token\b   \bMissing (?:closing|expression|argument|statement)\b
\bstring (?:is )?missing the terminator\b   \bpositional parameter cannot be found\b
\bis not recognized as the name of\b   \bCommandNotFoundException\b   \bcommand not found\b
\bsyntax error near unexpected token\b   \bunexpected EOF while looking for matching\b
\b(?:SyntaxError|IndentationError|TabError):
```

It excludes `FullyQualifiedErrorId` and `CategoryInfo`, which an expected failure also prints. Verdicts
are stored, but **re-derived on every load** from the current rules, superseded runs included: the
sidecar owns the output, the report owns the rule. `flowviz captures` re-derives the same way.

### 1.5 Command blocks

A `div.cmd` is something the human **runs**, pasted into a live console that drops the first character,
mangles column-0 constructs, and reports syntax errors away from the real cause.

| Rule | Why | Checked by |
|---|---|---|
| No leading comment line | A dropped `#` turns prose into code. | audit |
| ASCII only | An em dash or smart quote is a parse error, comments included. | audit |
| Nothing spanning a line break | No here-strings, no backtick or backslash continuations. | audit |
| No blank lines | Some consoles treat one as submit. | audit |
| Name the interpreter | PowerShell 5.1 and 7 differ in ways that break error handling silently. | you |
| Echo every derived value | A block that pattern-matches its way to a path prints what it matched and how many. | you |
| Parse-check before handover | `bash -n`, `python3 -m py_compile`, `Parser::ParseFile`. | you |

A block that is **shown, not run** — a JSON sample, a tree, a log excerpt — is `div.cmd.fig`: dashed, no
copy button, exempt from all of the above. Never use it to smuggle a command past the audit.

### 1.6 Evidence and print

**Save evidence** writes one plain-text turnover record: every step in DOM order with id, blast radius,
verdict, sentence, command, capture, SHA-256 of the capture (secure context only), exit code, time,
note and superseded runs — and every note left on a drawing. **Print** is a mode of the one stylesheet:
`flow.js` forces light, opens every `<details>`, grows every textarea on `beforeprint`, and restores all
three after. Print CSS carries pagination only.

---

## 2. Drawings

### 2.1 Four gestures, four layers

| Gesture | Shows | Budget |
|---|---|---|
| **Look** | boxes, zones, the selected flow in motion, step numbers | ≤12 boxes, ≤60 words on the canvas |
| **Hover** | a peek: one sentence and up to three facts | ≤25 words |
| **Click** | the drawer: depth sections, the steps a box takes part in, a note for the agent | unlimited |
| **Play** | the flow step by step: a labelled packet and a one-sentence caption | ≤9 steps, ≤20 words each |

Touch has no hover, so a tap opens the drawer, which also carries the peek.

### 2.2 Caps

| Slot | Cap |
|---|---|
| Title | ≤70 chars, contains a verb: a claim about the system, not its name |
| Lede | ≤30 words |
| Boxes | ≤12 per canvas; **≤9** when the drawing is a report's spine diagram. A 13th box means a segment. |
| Zones | ≤4 |
| Flows | 1 to 3 per canvas |
| Steps | ≤9 per flow |
| Step `say` | exactly one sentence, ≤20 words |
| Step `msg` | ≤24 chars |
| Box `label` | ≤16 chars |
| Box `tech` | ≤24 chars |
| Connection `label` · `ms` | ≤16 chars · ≤20 chars |
| `peek` | ≤25 words, boxes and connections alike |
| `facts` | ≤3 per box, ≤24 chars each |
| Zone `label` | ≤28 chars |
| Words on canvas at rest | ≤60 — box labels plus zone labels |
| At load | no drawer open, no layer switched on, one flow moving |
| Crossings | 0 — needs layout |
| Labels shrunk to fit | 0 — needs layout |
| Zone labels crossed by a connection | 0 — needs layout |
| Screens at rest (drawing page) | ≤2 — needs layout |

The last four are measured by `?audit=1` or `flowviz audit --browser`; everything else is read from the
spec without a browser.

### 2.3 Motion grammar

Motion carries meaning or it does not move. These meanings are fixed; a drawing never redefines them.

| Mark | Means |
|---|---|
| Dashes | a synchronous call. They travel the way the request goes. |
| Dots, slower | an asynchronous message. Nobody waits on it. |
| Two parallel lanes | traffic in both directions (`"both": true`), one direction per lane. A sync edge implies its response and never needs a second lane. |
| Accent colour, moving | part of the selected flow |
| Grey and still | exists, but not part of the selected flow |
| Red, packet stops at ✕ | the call fails (`"fail": true` on the step; the last hop fails) |
| Numbered badge | the step that starts on that connection |
| ⤢ on a box | opens a segment: the inside of that box |
| Dashed box | a ghost: a box of the parent drawing, shown so a segment has edges |

`prefers-reduced-motion` and the **Motion** switch stop the drift and the packet travel; direction is
still carried by arrowheads, and every state stays reachable.

### 2.4 The spec

A drawing is a `figure.fv-drawing` holding one `<script type="application/json">` spec and one
`div.fv-depth` of HTML sections. The agent writes those two things and nothing else; layout, routing,
icons, motion, peeks, the drawer, the walkthrough, the sequence view and notes are the runtime's.

```json
{
  "id": "checkout",
  "name": "Checkout",
  "title": "Checkout confirms in 300 ms because payment settles off the hot path",
  "lede": "Three services and one transaction sit on the request path.",
  "grid": { "cols": 5, "rows": 4 },
  "zones": [ { "id": "hot", "label": "Hot path · p99 300 ms", "cols": [1, 3], "rows": [0, 1],
               "tone": "sync", "tag": "tl" } ],
  "nodes": [ { "id": "order", "label": "Order service", "kind": "service", "icon": "service",
               "at": [2, 1], "tech": "Go · 6 pods", "peek": "Owns the order lifecycle.",
               "facts": ["p99 200 ms"], "segment": "order-outbox" } ],
  "edges": [ { "id": "order-db", "from": "order", "to": "db", "mode": "sync", "label": "SQL",
               "ms": "p99 18 ms", "peek": "One transaction writes both rows." } ],
  "flows": [ { "id": "place", "label": "Place order", "summary": "8 steps; the id arrives at step 4.",
               "steps": [ { "id": "p3", "path": ["order", "db"], "msg": "COMMIT",
                            "say": "The order row and its outbox row commit in one transaction." } ] } ],
  "segments": { "order-outbox": { "name": "Order service", "parent": "order", "title": "…", "lede": "…",
                                   "grid": {}, "zones": [], "nodes": [], "edges": [], "flows": [] } }
}
```

| Field | Values |
|---|---|
| `id` | `[a-z0-9][a-z0-9-]*`, unique per page. Part of every note key: never rename it. |
| node `kind` | `client` `edge` `service` `data` `stream` `external` `threat` — sets the tint; agents never pick colours. `threat` is an adversary: red, with a broken edge |
| node `icon` | one of the icon set listed in `AGENTS.md` |
| node `at` | `[col, row]`, zero-based, inside `grid`, one box per cell |
| node `ghost` | inside a segment only: the id of the parent box it stands for. Drawn dashed; click goes back. |
| node `segment` | the key of a segment in `segments` |
| edge `mode` | `sync` or `async` |
| edge `both` | `true` for traffic in both directions |
| edge `route` | optional override: `h`, `v`, `hvh`, `vhv` |
| zone `cols` · `rows` | `[first, last]`, both inclusive |
| zone `tone` | `neutral` `sync` `async` `ext` `data` `svc` |
| zone `tag` | the corner the label sits in: `tl` (default) `tr` `bl` `br` |
| edge `ms` | optional; shown by the Timings layer. Omit it where nothing has a latency. |
| step `path` | two or more box ids; every consecutive pair must be joined by an edge, either direction |
| step `fail` | `true` makes the last hop fail |

Routing is deterministic: a connection leaves the side of its box that faces the target and bends only in
the gutter between cells. Straight connections own the centre of a side; bent ones fan out beside them.
**A straight connection may not pass through a box** — move a box, or add `route`.

### 2.5 Depth

`div.fv-depth > section[data-for="<key>"]` holds layer 3 for one element, as plain HTML (tables, code
blocks with `data-copy` buttons, lists). Keys: `<nodeId>`, `edge:<edgeId>`, `step:<stepId>`, and inside a
segment `<segmentId>/<key>`. A missing section is fine; the drawer still shows the peek, facts, steps and
the note box.

### 2.6 Segments

A drawing is a whole system or one segment of it. A box with `segment` opens its own canvas with its own
title, lede, grid and flows; the boxes it talks to come along as **ghosts** (`"ghost": "<parent box id>"`)
that lead back. When a system will not fit in 12 boxes, split it into segments instead of raising the cap.
A standalone drawing may itself be a segment (`"kind": "segment"`) of a system drawn elsewhere.

### 2.7 Views

One spec, three views: **Map** (the drawing), **Sequence** (the selected flow laid out in time: one
lifeline per box it touches, one arrow per hop, the same step numbers), and **Spec** (the JSON, with a
copy button). The walkthrough drives whichever of Map and Sequence is showing.

---

## 3. Author checks

Not caps — they measure the author, not the layout — and they block handover exactly like a cap.

| Check | Fails when |
|---|---|
| unfilled slots | a slot or spec string still carries the template's own words |
| cmd: leading comment | a `div.cmd` opens with `#`, `//`, `<#` or `rem` |
| cmd: non-ASCII | a byte above 0x7F inside `<pre><code>` |
| cmd: spans a line break | a here-string opener or a backtick/backslash continuation |
| cmd: blank line | a blank line inside a command |
| cmd: fragile verdict regex | a `data-pass`/`data-fail` literal matches inside a word of real shell error boilerplate |
| spec: parses | a drawing's JSON does not parse |
| spec: ids | a missing, malformed or duplicate id |
| spec: references | an edge endpoint, step hop, segment, ghost or parent that does not resolve |
| spec: vocabulary | a `kind`, `icon`, `mode`, `tone` or `tag` outside the lists above |
| spec: grid | a box outside the grid, two boxes in one cell, or a zone outside the grid |
| spec: straight through a box | a straight connection that would pass through another box |

One more is reported but does not block: **unused connection** — an edge no flow walks. It is still
drawn; if it matters, walk it in a flow, and if it does not, delete it.

---

## 4. Banned

- Numbered `§1–§12` outlines. Numbering invites completeness; completeness fights the budget.
- More than one `<details open>` in a report; any drawer or layer open at load in a drawing.
- Prose above the verdict. The card is always the first thing on a report.
- A command the reader must edit before running, unless its one sentence says so.
- CDN `<script src>`, web fonts, remote images. Deliverables render offline, locked down, and in print.
- A colour, font stack or radius written anywhere outside the token layer.
- Hand-written layout coordinates in a drawing. Boxes go on the grid; the runtime draws.

---

## 5. Themes

Tokens only. `data-theme` is set on `<html>` before first paint by the build's head script; the pill
cycles `auto → light → dark` and the choice persists in the sidecar. `data-kind` (`report`|`drawing`)
selects the neutral family.

| | Light | Dark |
|---|---|---|
| **report** | *journal*: warm paper `#f4efe4`, serif prose, hairlines, no vertical table borders, vermillion margin rule, 4px radii | *traditional*: cool slate `#0f1115`, system sans, full grid, 9px radii |
| **drawing page** | *canvas*: cool white `#F5F7FB` ground, white canvas with a faint dot grid, pastel component tints, navy ink | *night*: deep navy `#0A0F1D`, luminous tints, the same grammar |

A drawing embedded in a report takes the report's neutrals (paper, ink, hairlines) and keeps its own
component tints and flow accents — a coloured plate printed in the notebook.

---

## 6. State

Nothing a human types is stored in the HTML. It goes to `<doc>.flow.json` beside it.

```json
{
  "schema": 3, "doc": "checkout", "flowviz": "0.6.0", "savedAt": "2026-09-28T21:14:08Z",
  "ui": { "theme": "auto", "motion": true,
          "draw": { "checkout": { "flow": 0, "view": "map", "labels": false, "times": false, "key": false } } },
  "vars": { "host": "app-vm-01" },
  "checks": { "p1a": true },
  "open": { "r2": true, "step:ps-3": true },
  "steps": { "ps-3": { "done": true, "acked": false } },
  "captures": { "ps-3": { "text": "Hash : 4F2C…", "exit": "0", "verdict": "pass",
                          "at": "2026-09-28T21:13:57Z", "note": "share needed remapping first",
                          "runs": [ { "text": "Unexpected token '}'", "exit": "", "verdict": "error",
                                      "at": "2026-09-28T21:09:02Z" } ] } },
  "notes": { "checkout/node:order": { "text": "the cache is write-through, not cache-aside",
                                      "at": "2026-09-28T21:15:40Z" },
             "checkout/order-outbox/node:relay": { "text": "…", "at": "…" } }
}
```

`notes` arrived in schema 3; `note` and `runs` in schema 2. Every addition defaults empty, so an older
sidecar loads unchanged. Note keys are `<drawingId>/[<segmentId>/]<node|edge|step>:<id>`.

| Tier | When | Pill |
|---|---|---|
| `localStorage` | always, debounced 700 ms | — |
| Sidecar on disk | served over localhost: `PUT <page dir>/_flow/state/<doc>` | green, `saved 21:14 PDT` |
| Manual export | opened via `file://` | amber `local only` + a state button |

On load both are read; the newer `savedAt` wins, then both are brought level. The merge is a union at
key level, so a sparse sidecar never deletes something held locally. The server copies the previous
sidecar to `.flowviz/state-backup/<doc>.<ts>.json` the first time each doc is overwritten in a run.

Every input is keyed by a **stable id** — the doc id, step ids, drawing ids, box, edge and step ids — so
an agent may regenerate the HTML freely and the human's input re-attaches. Ids are part of the contract:
**never renumber or rename one** once a human may have typed against it.

---

## 7. Versioning

`VERSION` holds semver for the standard. Every built deliverable footers its provenance.

| Bump | Means |
|---|---|
| patch | CSS, wording, bug fix |
| minor | new component, caps unchanged (0.6.0 added drawings) |
| major | a cap changes, or the card shape changes |

Two things roll back independently: **the standard** (`git -C ~/Projects/FLOW_VIZ checkout v<ver>`, then
rebuild — once FLOW_VIZ is its own repository) and **a deliverable's content**
(`<dir>/.flowviz/history/<doc>/<UTC>.html`, written before any rebuild overwrites a file). Sidecar state
survives both.

---

## 8. Building

`bin/flowviz` is the single entry point. Run it bare for the cheat sheet.

```sh
F=~/Projects/FLOW_VIZ/bin/flowviz
$F new report  "The 500 is partial trust" --dir ~/work/sto --rows 5 --steps 7
$F new drawing "Checkout confirms in 300 ms" --dir ~/work/shop --boxes 8
$F build ~/work/sto/STO.src.html        # inline css + js + icons, stamp, snapshot
$F audit ~/work/sto/STO.html            # every static cap + author checks; exit 1 on any OVER/FAIL
$F audit --browser ~/work/sto/STO.html  # also the layout caps, via headless Chrome
$F serve ~/work/sto --open              # so what the human types reaches disk
$F captures ~/work/sto/STO.html         # read back captures and notes
```

Authors edit `.src.html`. The built `.html` is one file: no asset paths, no network. Deliverables are
generated into the folder the work is in; this repository is the toolkit they are cut from.
