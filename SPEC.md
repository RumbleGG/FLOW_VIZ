# FLOW_VIZ — the standard

**Version 3.2.0** · normative. Where this document and a deliverable disagree, the deliverable is wrong.

Producing something? `AGENTS.md` is the self-contained short road and is enough on its own. Read this
file when you need the reasoning, the full schemas, or you are changing the standard.

FLOW_VIZ has **two deliverables and one toolkit**:

| Kind | What it is | The budget that defines it |
|---|---|---|
| **report** | a claim, the shape of the argument, evidence, and a checklist playbook the human runs and pastes into | the main idea lands in **two minutes** |
| **drawing** | a whole system, or one segment of it, with motion that shows where data goes | the system reads in **ten seconds**; the walkthrough takes one minute |

Both are one self-contained HTML file. Both put depth **exactly one gesture away** — never zero, never
three. Both are input devices: what the human types lands in a sidecar the agent reads back with a
command — output pasted into a step, a note on a box, a step they found missing, a to-do. A report may carry a drawing as its spine diagram; that is the same component, smaller.

---

## 1. Reports

### 1.1 Three layers

| Layer | Budget | Holds |
|---|---|---|
| **1 — Card** | one screen, never scrolls | status chip, claim-title, verdict, so-what, ≤5 vital tiles, ≤4 next actions |
| **2 — Spine** | one diagram + ≤6 collapsed rows under ≤3 headers | the shape of the thing, then one labelled row per idea |
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
| Section headers | ≤3, ≤4 words each; no row before the first | They say what the rows below are for, so six claims are not six mysteries. |
| Row kind | every row has one (§1.2a) | The reader knows before opening a row whether to read it or act on it. |
| Step sentence | exactly one sentence, ≤20 words | A nine-step playbook reads as nine sentences. |
| Words at rest | ≤350 | Card text plus row summaries. The two-minute budget, made countable. |
| Screens at rest | ≤3 | Needs layout: measured by `?audit=1` or `flowviz audit --browser`. |

Structural checks measured alongside the caps, all must be 0: multi-sentence steps, steps with no
risk tag, write steps with no gate, untagged next items.

### 1.2a What each row is for

Every row carries `data-kind`. The agent writes the attribute; `flow.js` draws the label at the start of
the summary, every label as wide as the widest so the claims start in one column. Headers are written by
the agent: `<h2 class="sec">Try it on this Mac</h2>` before the rows they introduce.

| `data-kind` | Label | Means | Must hold |
|---|---|---|---|
| `context` | context | background to read | no steps |
| `finding` | finding | what the evidence shows | no steps |
| `record` | record | what was done, and how to undo it | no steps |
| `investigation` | action · investigation | commands that gather facts and change nothing | a step or a checkbox |
| `test` | action · test | commands that check that something works | a step or a checkbox |
| `change` | action · change | commands that change a system | a step or a checkbox |
| `rollback` | action · rollback | commands that undo a change | a step or a checkbox |
| `decision` | decision | yours to approve or choose | anything |

The audit fails a label that does not match what the row holds, in either direction.

### 1.2b Names: letters for rows, numbers for steps

Rows are lettered **a, b, c…** in the order they appear; the letter is the row's `data-row` and the label
in its `.ord`. A step's id is **its row's letter and its number in that row** — `b1`, `b2` … `bn` — and a
Results section's steps are `r1`, `r2`…. Never a word (`push`), never two letters (`bb`, `bc`): a letter
names a row and a number names a step, so "look at b3" means one thing on screen, in the sidecar and in the
agent's read-back. The page shows a conforming id where the step's counter was; any other id keeps the
counter, so an older report still reads as it did. The audit fails a report off the convention, and
`flowviz relabel` moves one onto it (§6).

A step the human adds in the page (§1.3b) is named for the step it follows plus the next free letter:
after `b3` it is `b3a`, then `b3b`; before a row's first step its anchor is `b0`, so `b0a`. No number moves,
so every id the human has already typed against stays put. Once `flowviz fold` writes it into the source it
keeps that id, and the convention accepts it there: a row reads `b1 b2 b3 b3a b4`.

### 1.3 Checklist steps

A playbook step is **a checkbox, its id, and one sentence.** That is all that is visible.

| Rule | Detail |
|---|---|
| Description | Exactly one sentence, ≤20 words, stating what the step *establishes* or *changes*. |
| Command | Behind the disclosure. The `⧉` on the collapsed row copies it without opening anything, prompts stripped. |
| Blast radius | `data-risk="ro"` or `data-risk="w"` on every step. A `w` step blurs its command until the acknowledgement is ticked, and `⧉` refuses to copy it — it opens the step and says *tick the gate*. |
| Id | `<row letter><n>` (§1.2b), shown where the counter was. |
| Prereqs | `data-after="<id>"` dims the step until that one is done or captured. |
| Carried value | `data-emit` on the producer's textarea, `{{<step>.<NAME>}}` in a later command (§1.3a). |
| Capture | Every step has a textarea, an exit-code field, a one-line note, and its sidecar key shown beside it. The textarea also takes images (§1.3c); only its text is matched against the rules. |
| Verdict | `data-pass` / `data-fail` regexes flip the chip on paste. Every literal is **word-anchored** (`\bFull\b`, never `Full`). |
| Re-run | Files the current capture into `runs[]` and clears the box. A second attempt never destroys the first. |
| Injected, never written | The `Done ☐` button at the foot of every step, the second verdict chip beside it, the status pill, and every displayed time. `flow.js` adds them, so a rebuild gives old reports new affordances. |

### 1.3a Emits — a value one step prints, used by a later step's command

A later command often needs something an earlier step printed: a version, an id, a path. The human never
carries it across by hand, and no command holds a `PASTE_…` placeholder for them to overwrite.

| Part | Rule |
|---|---|
| Produce | `data-emit="NAME=<regex>[; NAME=<regex>…]"` on the step's `textarea`. `NAME` is `[A-Z][A-Z0-9_]*`; each regex has **exactly one** capture group. |
| Value | group 1 of the **last** match in the current capture, trimmed. Derived on every paste, re-run and load — never from `runs[]` — and stored in the sidecar under `emits` as a cache: fixing a regex fixes the value, the way re-deriving fixes a verdict. |
| Consume | `{{<step>.<NAME>}}` anywhere in a `.cmd pre`. A token right after `$` (`${{ … }}`) is someone else's syntax and is never touched. |
| Render | `span.sub`: the value, titled *from step b1*, when it exists and is paste-safe; the literal token otherwise, so what you read is what copy sends. |
| Copy | both `copy` and `⧉` send the resolved command. While a token has no value the copy is refused with *b1 has not run*; while its value is not paste-safe, with *b1.VER is not paste-safe*. Nothing unresolved reaches a clipboard. |
| Paste-safe value | 1–120 printable ASCII characters, none of `` ` $ " ' \ ; \| & < > ( ) { } ``, so no newline and nothing long enough to wrap. |
| Order | the producer is the consuming step itself or on its `data-after` chain; otherwise the audit warns that the order is not guaranteed. |

`data-var` is for what only the human knows (a host name); an emit is for what an earlier step printed.
Both persist with the state; only an emit has a source step, so only an emit can be checked for being
wrong. Words and screens at rest are unchanged: commands sit behind the disclosure.

### 1.3b What the human adds: steps and to-dos

Mid-run the human finds a step missing, or remembers something the write-up should say, or something to
do once it is over. They write it into the page, where it belongs, and it reaches the agent with everything
else. Both are drawn by `flow.js` from state; neither is ever in a report's markup, and the agent writes
nothing to enable them.

| Part | Rule |
|---|---|
| Add a step | three ways in, one composer: the **+** at each step's foot, between its verdict and **Done** — pressed, it turns into × and forks out **+ step after** and **+ to-do** along the row, taking the verdict's place until it closes — the prompt under a `fail` or `error` chip (*Was a step missing before b4?*), and **+ Add a step** at the end of a playbook. Not in the Results section. |
| The composer | one sentence, read or write, an optional command. It shows the audit's rules as meters while typing — 20 words, one sentence, ASCII, one line, no leading comment, with a **fix** for smart quotes — and refuses nothing: the agent tidies the step when it folds it. |
| An added step | the template's step, drawn in place in violet (human ink) and dashed: checkbox, gate if it writes, command, paste box, Done. Its output, tick and note use the ordinary keys (`captures.b3a`, `steps.b3a`). With no `data-pass` or `data-fail` its chip reads `captured`, never `no match`. It can be edited, or removed. |
| To-dos | one section at the end, one line at rest. Two kinds in the words used mid-run: **add to write-up** (something the write-up is missing; **make it a step** opens the composer at its anchor and closes the to-do as `→ b1a`) and **do after** (a task once the run is over; a candidate for Next). Ids `t1`, `t2`…, each optionally tied to a step. |
| Capture without losing your place | `t` anywhere outside a text field, **+ to-do** in the pill (with the open count), or **+ to-do** from a step's **+**, opens a small form tied to that step; the page does not move. |
| At rest | a violet count on the row (`+1 added · 2 to-do`) and on the step a to-do is tied to. |
| Removing | writes a tombstone (`gone`), never a delete: the load merge is a union, so a deleted key would come back from the other store. A removed id is never handed out again. |
| Caps | none apply: this is the human's writing, not the agent's budget. The audit leaves added steps, the markers and the to-do section out of every measure. |

The agent reads both back with `flowviz captures` (an added step prints in place, marked `+`; to-dos follow
the playbooks), then decides what each becomes: a step folded into the source with `flowviz fold`, a
reworded step, or a next action. An open **do after** to-do is offered as Next by `flowviz results`.

**Time.** Stored as ISO-8601 UTC everywhere (sidecar, exports, snapshot names). Shown in
`America/Los_Angeles`, labelled `PDT`/`PST`, with the ISO value on `title`. No report hand-formats a time.

### 1.3c Evidence: images in a paste box, and verdicts set by hand

Text output is not always the evidence: a dashboard, a dialog, a page that rendered wrong. And a rule can be
wrong about one run while the human can see what happened. Both are captured where the step is.

| Part | Rule |
|---|---|
| Attach an image | paste one into the paste box (text on the clipboard still pastes as text), drop a file on the box, or **+ image** beside **re-run** (the way in on a phone). Images sit in a strip under the box, numbered `b4·1`, `b4·2`, each with a caption the human can edit; one opens full size with its hash. The text box itself is unchanged. |
| Where it lives | served: one file per image in `<doc>.assets/` beside the page, named by its sha256, sent before the state that refers to it; `flowviz serve` checks the type, the size and the hash, and writes each name once. The capture holds only the reference — pixels never go in the sidecar. Not yet on disk (opened from Finder, or the server was down): kept in this tab and, where the browser allows, its IndexedDB, under an amber *only in this browser* line, and sent the next time the page reaches its server. A page opened from Finder is a different origin from the served one, so, like its text, what it holds stays in that browser. |
| Over 10 MB | compressed in the page before it goes anywhere: re-encoded as WebP (JPEG where WebP is not available) at a high quality first, scaled down only if that is not enough. The original's type, size and pixels are recorded with it. A type the page does not keep (HEIC, BMP) is converted where the browser can read it; an animated GIF over the limit keeps its first frame. |
| Verdicts | images never change the derived verdict: rules match text. A capture that is only images reads `captured`. |
| Re-run · remove | re-run moves the images with the attempt into `runs[]`. Removing one keeps its record with `gone`, and the file stays on disk. |
| Set a verdict by hand | the verdict chip is a button. It opens a panel under the step's foot — it covers nothing — with **pass**, **fail** and **no match**, the derived one marked, and a one-line reason, which is required. The derived verdict is kept beside it and still re-derived on every load. |
| What shows it | a violet ✎ on the row's chip and a ✎ badge on the foot chip; one line under the foot with the time, the derived verdict, the reason and **back to derived**; the playbook's counter (`1 set by hand`). If the output changes afterwards, the line turns amber until it is set again or taken back. |
| What reads it | the effective verdict (the one set by hand, else the derived one) drives the chips, progress, the missing-step prompt and the outcome `flowviz results` works out; every surface that shows it — Copy captures for agent, `flowviz captures`, Save evidence, Results — shows the derived verdict and the reason beside it. |

Caps do not apply: the images and the panel live inside a step, below the layer the caps measure.

### 1.4 The verdict vocabulary

Tested in this order; the earlier a tier, the less it presumes.

| Verdict | Chip | Means | Who it indicts |
|---|---|---|---|
| `error` | `error`, `--warn` | the interpreter rejected the command — parse failure or unresolved name | **the playbook**; the target was never asked |
| `fail` | `fail`, `--bad` | the command ran and the target said no | the system under test |
| `pass` | `pass`, `--ok` | `data-pass` matched and nothing above did | nothing |
| `saved` | `no match`, `--dim` | captured, matched neither regex | the step's pass condition |
| `saved`, no rule | `captured` | captured by a step with no `data-pass` or `data-fail` — one added in the page, until it is folded — or only images | nothing: there is no rule to miss |
| any, set by hand | the verdict, with a violet ✎ | the operator decided it (§1.3c); the derived verdict is kept beside it | the operator's judgment: report it as theirs, with their reason |
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

### 1.6 Results — after the human has run the playbook

When the human has run the playbook and the agent has read the captures back, the agent adds a
**Results** section: `section.results`, placed **before the card**. What happened is now the main idea;
the card below stays as the plan that was tested. `flowviz results <report>.src.html` starts it from the
sidecar — outcome, chip and counts filled in, the diagram started from the spine drawing, the archive step
written — and never overwrites one that exists.

| Part | Cap |
|---|---|
| Outcome | `data-outcome`: `pass` (every step passed) · `fail` (a step failed: the target said no) · `blocked` (a command was rejected, so the target was never asked) · `inconclusive` (no match, or steps not run) — plus its chip |
| Claim (`h2`) | ≤70 chars with a verb: what happened, not "Results" |
| Summary | ≤50 words: what ran, what the output proved, where it stopped |
| Diagram | exactly 1 drawing, ≤9 boxes, marking the point: `"result": "pass" \| "fail" \| "error"` on a box, connection or flow step, agreeing with the outcome |
| Next | 1 to 4 items, ≤14 words, each tagged `read-only` or `write` |
| Archive | exactly 1 gated write step (`li.step[data-archive]`) that moves the finished folder into the archive |
| Words at rest | ≤150 |
| Height | ≤1.5 screens; the report's own ≤3 screens is measured without it |

A rollback step that was never needed counts as "not needed", not as missing.

### 1.7 Evidence and print

**Save evidence** writes one plain-text turnover record: every step in DOM order with id, blast radius,
verdict, sentence, command, capture, SHA-256 of the capture (secure context only), exit code, time,
note and superseded runs, a verdict set by hand with its reason and the derived verdict, every image with its
file, size, sha256 and caption — a step added in the page marked as such — then every note left on a drawing
and every to-do. **Print** is a mode of the one stylesheet:
`flow.js` forces light, opens every `<details>`, grows every textarea on `beforeprint`, and restores all
three after; each image prints full width under its step with its caption and hash, so print to PDF is a
complete evidence document. Print CSS carries pagination and that only.

---

## 2. Drawings

### 2.1 Four gestures, four layers

| Gesture | Shows | Budget |
|---|---|---|
| **Look** | boxes, zones, the selected flow in motion, step numbers | ≤12 boxes, ≤60 words on the canvas |
| **Hover** | a peek: one sentence and up to three facts | ≤25 words |
| **Click** | the drawer: depth sections, the steps a box takes part in, a note for the agent | unlimited |
| **Play** | the flow step by step: a labelled packet and a one-sentence caption | ≤9 steps, ≤20 words each |

**Flows are off by default.** A drawing without flows is boxes and connections, with no flow chips, no
step badges and no Walk through; every connection still moves gently in its own direction. Add flows only
when the human asks for a walkthrough of the order of events. Touch has no hover, so a tap opens the
drawer, which also carries the peek.

### 2.2 Caps

| Slot | Cap |
|---|---|
| Title | ≤70 chars, contains a verb: a claim about the system, not its name |
| Lede | ≤30 words |
| Boxes | ≤12 per canvas; **≤9** when the drawing is a report's spine diagram. A 13th box means a segment. |
| Zones | ≤4 |
| Flows | 0 to 3 per canvas; 0 unless the human asked for a walkthrough |
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
| Plain ink, moving | a connection in a drawing that has no flows |
| Dots, slower | an asynchronous message. Nobody waits on it. |
| Two parallel lanes | traffic in both directions (`"both": true`), one direction per lane. A sync edge implies its response and never needs a second lane. |
| Accent colour, moving | part of the selected flow |
| Grey and still | exists, but not part of the selected flow |
| Red, packet stops at ✕ | the call fails (`"fail": true` on the step; the last hop fails) |
| Numbered badge | the step that starts on that connection |
| ⤢ on a box | opens a segment: the inside of that box |
| Dashed box | a ghost: a box of the parent drawing, shown so a segment has edges |
| Green, ✓ badge | `"result": "pass"` — verified by a real run |
| Red, ✕ at the stop | `"result": "fail"` — the run failed here: the target said no |
| Amber, ⚠ near the source | `"result": "error"` — the command was rejected; the target was never asked |

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
| step `fail` | `true` makes the last hop fail (a designed failure path) |
| `result` | on a box, a connection or a flow step: `pass` · `fail` · `error` — what a real run proved (§1.6) |

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

### 2.7 Copy HTML — a drawing for a wiki page

Every drawing has a **Copy HTML** button. It copies one self-contained snippet to paste into a wiki page or
any page that accepts HTML, and the snippet works in three situations:

| The page… | The reader gets |
|---|---|
| allows scripts (Confluence's HTML macro, Wiki.js, a static site) | the live drawing: peek, drawer, flows and Walk through, segments, notes kept in that browser |
| strips scripts (Obsidian, GitHub, MediaWiki) | a still picture with its colours and result marks inlined, and a `<details>` per box with its peek, facts and depth |
| is markdown | either of the above: the snippet has no blank lines, so the HTML block is not cut short |

The snippet's styles are scoped to its wrapper (`.fvx`), so it cannot restyle the page around it. Several
snippets on one page, or one on a FLOW_VIZ page, share one runtime and never mount twice. The build
provides the scoped stylesheet as `script#fvEmbedCss`; the runtime assembles the rest.

### 2.8 Views

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
| row kind matches its content | an action kind with nothing to run or tick, a read kind that holds steps, or a kind outside §1.2a |
| section letters and step ids | a row not lettered in order or not showing its letter, a step not `<row letter><n>` in order (or, folded in from the page, the step before it plus the next letter), a Results step not `r<n>`, or a step outside every row and the Results section (§1.2b) |
| emit: regex | a `data-emit` pair that is not `NAME=<regex>`, declares a name twice, does not compile, or has other than one capture group |
| emit: dangling reference | a `{{<step>.<NAME>}}` whose step does not exist, or does not emit that name |

`flowviz build` refuses the two emit failures too, so a token that can never resolve never ships.

Reported, not blocking: **unused connection** — an edge no flow walks (it is still drawn; walk it in a flow
or delete it); **emit: ordering** — a token whose producer is neither the step itself nor on its
`data-after` chain; **PASTE_ placeholder** — a `PASTE_…` word in a command, which the human would have
to overwrite: use an emit from the producing step instead; **steps added in the page** and **open to-dos**
— read from the sidecar beside the page, when there is one: fold, reword or carry them (§1.3b).

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
  "schema": 6, "doc": "checkout", "flowviz": "3.2.0", "savedAt": "2026-09-28T21:14:08Z",
  "ui": { "theme": "auto", "motion": true,
          "draw": { "checkout": { "flow": 0, "view": "map", "labels": false, "times": false, "key": false } } },
  "vars": { "host": "app-vm-01" },
  "checks": { "p1a": true },
  "open": { "b": true, "step:b3": true },
  "steps": { "b3": { "done": true, "acked": false } },
  "captures": { "b3": { "text": "Hash : 4F2C…", "exit": "0", "verdict": "pass",
                          "at": "2026-09-28T21:13:57Z", "note": "share needed remapping first",
                          "runs": [ { "text": "Unexpected token '}'", "exit": "", "verdict": "error",
                                      "at": "2026-09-28T21:09:02Z" } ] },
                "b4": { "text": "{\"status\":\"failed\", …}", "exit": "0", "verdict": "fail", "at": "…",
                          "override": { "verdict": "pass", "was": "fail", "at": "…", "textHash": "9c1e44a0",
                                        "reason": "the provider's log shows m-8812 delivered" },
                          "images": [ { "sha256": "5e0c…a91b", "file": "checkout.assets/5e0c…a91b.png",
                                        "type": "image/png", "w": 960, "h": 330, "bytes": 29006,
                                        "caption": "provider delivery log", "at": "…" } ] } },
  "notes": { "checkout/node:order": { "text": "the cache is write-through, not cache-aside",
                                      "at": "2026-09-28T21:15:40Z" },
             "checkout/order-outbox/node:relay": { "text": "…", "at": "…" } },
  "emits": { "b1": { "VER": "12.149.3747.21500" } },
  "added": { "b3a": { "after": "b3", "text": "Check the allowlist includes the new egress range.",
                      "cmd": "curl -s https://provider.example.test/v1/allowlist", "risk": "ro",
                      "at": "2026-09-28T21:12:02Z", "folded": "2026-09-28T22:02:11Z" },
             "b2a": { "after": "b2", "text": "…", "at": "…", "gone": "2026-09-28T21:11:30Z" } },
  "todos": { "t1": { "text": "Ask the provider to allowlist the new range", "kind": "do", "ref": "b4",
                     "at": "2026-09-28T21:13:15Z", "done": false },
             "t2": { "text": "Check the kube context before b2", "kind": "add", "ref": "b1",
                     "at": "…", "done": true, "doneAt": "…", "became": "b1a" } },
  "relabel": "2026-09-29T17:32:04.988Z"
}
```

A capture's `images` and `override` arrived in schema 6 (`textHash` is FNV-1a of the output, for change
detection only; the evidence hash is sha256), `added` and `todos` in 5, `emits` in 4, `notes` in 3, `note` and
`runs` in 2. Every addition
defaults empty, so an older sidecar loads unchanged. A build keeps any key it does not know rather than
dropping it, and `flowviz serve` carries over any top-level key a save leaves out, so a page built before a
key existed can never erase it from disk. A removed step or to-do keeps its key with `gone` set: the merge
is a union, and only a tombstone survives it. Note
keys are `<drawingId>/[<segmentId>/]<node|edge|step>:<id>`. `emits` is a cache, re-derived from the
captures on every load; `relabel` is present only once `flowviz relabel` has moved the ids.

| Tier | When | Pill |
|---|---|---|
| `localStorage` | always, debounced 700 ms | — |
| Sidecar on disk | served over localhost: `PUT <page dir>/_flow/state/<doc>` | green, `saved 21:14 PDT` |
| Manual export | opened via `file://` | amber `local only` + a state button |

On load both are read; the newer `savedAt` wins, then both are brought level. The merge is a union at
key level, so a sparse sidecar never deletes something held locally. The server copies the previous
sidecar to `.flowviz/state-backup/<doc>.<ts>.json` the first time each doc is overwritten in a run.

Every input is keyed by a **stable id** — the doc id, row and step ids, drawing ids, box, edge and step
ids — so an agent may regenerate the HTML freely and the human's input re-attaches. Ids are part of the
contract: **never renumber or rename one** once a human may have typed against it.

The one sanctioned move is **`flowviz relabel <report>.src.html`**, which puts a report on §1.2b. It
rewrites every reference in the source (the step's capture, exit, counter, note and chip attributes,
`data-after`, `captures["id"]` labels and `{{step.NAME}}` tokens), backs the sidecar up to
`.flowviz/state-backup/`, and moves its `captures`, `steps`, `emits`, `open` and `added` keys — a step added
in the page moves with the step it hangs off (`b3a` with `b3`) — and every to-do's `ref` and `became`. It also appends the
move to `<meta name="flowviz-relabel">` in the source, so state a browser still holds from before is
re-keyed the next time the page opens, and stamps `relabel` on the sidecar and on every later save: the
server answers `409` to a tab still carrying the old ids instead of letting it write them back.
`--dry-run` prints the moves and writes nothing.

---

## 7. Versioning

`VERSION` holds semver for the standard. Every built deliverable footers its provenance.

| Bump | Means |
|---|---|
| patch | CSS, wording, bug fix |
| minor | new component, caps unchanged (0.6.0 added drawings; 2.1.0 added Copy HTML; emits arrived in 3.0.0 beside a major change; 3.1.0 added steps and to-dos the human writes into the page; 3.2.0 added images and verdicts set by hand) |
| major | a cap changes, or the card or spine shape changes, or the audit starts failing reports it passed (1.0.0 labelled every row; 2.0.0 made flows optional; 3.0.0 named rows and steps by letter and number) |

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
$F captures ~/work/sto/STO.html         # read back captures, notes, added steps and to-dos
$F fold ~/work/sto/STO.src.html         # steps the human added, into the source under the same ids
$F results ~/work/sto/STO.src.html      # once it has run: start the Results section
$F relabel ~/work/sto/STO.src.html      # an older report onto a, b, c and b1, b2, state included
```

Authors edit `.src.html`. The built `.html` is one file: no asset paths, no network. Deliverables are
generated into the folder the work is in; this repository is the toolkit they are cut from.
