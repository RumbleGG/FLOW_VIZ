# FLOW_VIZ — the brief for an agent working in another folder

You were pointed here because you are about to hand finished work back to one human as HTML: a
**report**, a **drawing** of a system, or a report with a drawing inside it. **Read only this file.** It
is self-contained. `SPEC.md` is the normative long form, needed only to change the standard;
`CLAUDE.md` is for agents maintaining this toolkit.

One rule underneath everything: **the main idea lands at a glance, and depth is exactly one gesture
away — never zero, never three.**

| You have… | Make | It gives the human |
|---|---|---|
| an answer, a root cause, a plan, commands to run | **report** | a card, the argument, evidence, and a checklist they run and paste output into |
| a system to explain: what talks to what, in what order, what breaks | **drawing** | boxes on a grid with motion, a peek on hover, depth on click, a step-by-step walkthrough |
| both | a **report** whose spine diagram is a drawing | the report template already has one in its spine |

## The commands

`bin/flowviz` is the only path worth remembering. Run it bare for the cheat sheet.

```sh
F=~/Projects/FLOW_VIZ/bin/flowviz

$F new report  "The 500 is partial trust, not a web.config bug" --dir ~/work/sto --rows 5 --steps 7
$F new drawing "Checkout confirms in 300 ms" --dir ~/work/shop --boxes 8 --flows 2
                                          # 1. scaffold into the folder the work is in
                                          # 2. write every slot (the long part)
$F build ~/work/sto/STO.src.html          # 3. one self-contained .html (rebuild freely: the previous
                                          #    output is kept in .flowviz/history/ beside it)
$F audit --browser ~/work/sto/STO.html    # 4. fix every OVER and FAIL
$F serve ~/work/sto --open                # 5. hand over, served
$F captures ~/work/sto/STO.html           # later: what they pasted, and every note they left
```

The deliverable lives in **the folder the work is in**; this repository is only the toolkit. Nothing is
installed, nothing is on `PATH`, no network, stdlib Python only. **Serve it** — opened from Finder, what
the human types stays in their browser and never reaches you.

---

## Reports

### The caps

Hard limits, not guidelines. `flowviz audit` measures all of them; screens at rest needs layout, which
`--browser` measures in headless Chrome.

| Slot | Cap |
|---|---|
| Title | ≤70 chars, **must contain a verb** — a claim, not a topic |
| Verdict | ≤50 words — the one thing you would say in a hallway |
| So what | ≤30 words — the consequence or the decision it forces, never a restatement |
| Vitals | ≤5 tiles, each a number + a label |
| Next | ≤4 items, ≤14 words each, imperative, **each tagged `read-only` or `write`** |
| Diagram | exactly 1 in the spine: a drawing (≤9 boxes) or a hand-written `div.dia` SVG |
| Rows | ≤6, each summary a claim with a verb in ≤14 words |
| Section headers | ≤3, ≤4 words each, saying what the rows below are for; no row before the first |
| Row kind | every row has `data-kind` (below) |
| Open at load | ≤1 row. Zero is the norm |
| Step sentence | ≤20 words, **exactly one sentence** |
| Words at rest | ≤350 — card text plus row summaries |
| Screens at rest | ≤3 |

**If you cannot fit, split the report.** Raising a cap is a major version bump of the standard and is not
yours to make. Nothing is ever deleted to fit — it moves down a layer:

| Layer | Budget | Holds |
|---|---|---|
| 1 · Card | one screen, never scrolls | chip, claim-title, verdict, so-what, vitals, next |
| 2 · Spine | 1 diagram + ≤6 collapsed rows | the shape, then one row per idea |
| 3 · Evidence | **unlimited** | logs, stack traces, tables, `file:line` citations — only inside rows |

### Every row says what it is for

Group the rows under section headers — `<h2 class="sec">Try it on this Mac</h2>` — and give every row a
`data-kind`. **You do not write the label**: the page draws it from the attribute, the same way in every
report, and the audit fails a label that does not match what the row holds.

| `data-kind` | The reader sees | Use for | Must hold |
|---|---|---|---|
| `context` | context | background they need to follow the argument | no steps |
| `finding` | finding | what the evidence shows | no steps |
| `record` | record | what was done, and how to undo it | no steps |
| `investigation` | action · investigation | commands that gather facts and change nothing | steps |
| `test` | action · test | commands that check something works | steps |
| `change` | action · change | commands that change a system | steps, write-gated |
| `rollback` | action · rollback | commands that undo a change | steps |
| `decision` | decision | something they approve or choose | anything |

```html
<h2 class="sec">Fix it</h2>
<details class="row" data-row="fx" data-kind="change">
<summary><span class="ord">4</span><span class="cl">Switching the app pool to full trust clears the 500</span><span class="rt">5 min</span></summary>
```

### Checklist steps — the playbook

A command the human must run is never a bare `<pre>`. It is a step: checkbox, number, one sentence,
blast-radius badge, copy button, verdict chip. The command, the expected result and the paste box sit
behind the disclosure, so a nine-step playbook reads as nine sentences. The scaffold writes both shapes;
**rename its `s1…sN` to mnemonic ids now** (`p6`, `ev2`, `rb1`) — ids are the join key for what the human
pastes, and renaming one later silently orphans their output.

```html
<li class="step" data-step="p6" data-risk="ro" data-after="p5">
  <input type="checkbox" class="done">
  <details class="sd">
    <summary><span class="n"></span><span class="ds">One sentence, ≤20 words, what this establishes.</span></summary>
    <div class="in">
      <div class="cmd"><button class="copy">copy</button><pre><code>the command</code></pre></div>
      <p class="expect"><b>Pass:</b> what good looks like &nbsp;·&nbsp; <i>Fail:</i> what bad looks like</p>
      <div class="cap">
        <div class="cl">Paste output <span class="kp">captures["p6"]</span></div>
        <textarea data-cap="p6" data-pass="\bFull\b" data-fail="\bMedium\b|\bMinimal\b"
          placeholder="paste the terminal output here — it saves as you type"></textarea>
        <div class="ft">
          <span>exit <input class="ec" data-ec="p6" placeholder="0"></span>
          <span data-cnt="p6">empty</span><span data-at="p6"></span>
          <span class="rn" data-run="p6"></span>
          <button class="rr" data-rr="p6" title="keep this attempt and clear the box">re-run</button>
        </div>
        <input class="nt" data-note="p6" placeholder="note for the agent (optional)">
      </div>
      <details class="more"><summary>why this step</summary>
      <div class="in"><p>Traps, fallbacks, <code>file:line</code> citations — as long as it needs.</p></div></details>
    </div>
  </details>
  <span class="ctr"><span class="badge ro">read</span>
    <button class="copy">⧉</button><span class="vd" data-vd="p6">—</span></span>
</li>
```

A **write** step differs in three places: `data-risk="w"`, `<span class="badge w">write</span>`, and an
acknowledgement gate as the first child of `div.in` —
`<label class="gate"><input type="checkbox" class="ack"> I accept this writes to app-vm-01.</label>`.
Its command stays blurred and uncopyable until the gate is ticked. `data-after="<id>"` dims a step until
that one is done or captured. **If a report contains no write steps, say so in the card** — silence
reads as an omission.

`data-pass` / `data-fail` are regexes tested against the pasted text. The order is fixed: an
**interpreter error** is detected first and chips `error`, then `data-fail`, then `data-pass`, else
`no match`. **Anchor every literal** — `\bFull\b`, never `Full`, which also matches
`FullyQualifiedErrorId` and turns a crashed command into a green `pass`. The audit fails you for it.

**You do not write these** — `flow.js` injects them, so a rebuild gives every old report the newest:
the `Done ☐` button at the foot of each step (it ticks, then folds the step away), a second verdict chip
beside it, the status pill (save state, theme, motion), and every displayed time (Pacific, labelled;
stored as UTC).

### Command blocks must survive a keystroke paste

A console that pastes as keystrokes drops the first character, mangles column-0 constructs, and reports
syntax errors lines away from the cause.

- **Never start a block with a comment line.** Context ("run elevated, on the box") goes in a
  `<div class="box warn">` above the `.cmd`, where it is readable and cannot be pasted.
- **ASCII only** inside `<pre><code>` — no em dash, no smart quote, comments included.
- **Nothing spans a line break**: no here-strings, no backtick or backslash continuations. One long line
  beats an elegant wrapped one.
- **No blank lines** — some consoles treat one as submit.
- **Name the interpreter** when it matters; **echo every derived value** and how many matched.
- **Parse-check every block** before handover: `bash -n`, `python3 -m py_compile`,
  `[System.Management.Automation.Language.Parser]::ParseFile`.

The audit enforces the first four and the anchoring rule. The rest need an interpreter per language,
which the toolkit refuses to install: **they are yours**, and so is a pass condition that the command's
real output can actually falsify. Something **shown, not run** — a JSON sample, a tree, a log — is
`<div class="cmd fig">`: dashed, no copy button, exempt. Never use it to smuggle a command past the audit.

### Components

All exist in the stylesheet. Use the class; never write CSS.

| Want | Markup |
|---|---|
| Callout | `<div class="box key\|ok\|warn\|bad"><p>…</p></div>` |
| Command | `<div class="cmd"><button class="copy">copy</button><pre><code>…</code></pre></div>` |
| Figure, not a command | `<div class="cmd fig"><pre><code>…</code></pre></div>` |
| Nested disclosure | `<details class="more"><summary>label</summary><div class="in">…</div></details>` |
| Table | plain `<table><thead><tr><th>` |
| Plain checkbox | `<label class="chk"><input type="checkbox" data-ck="id"><span>…</span></label>` |
| Fill-in variable | `<input data-var="host" placeholder="app-vm-01">` — persists with the state |

---

## Drawings

A drawing shows a whole system, or one segment of it, in motion. The human **looks** (boxes, zones, the
selected flow moving), **hovers** (a one-sentence peek), **clicks** (the drawer: everything you know
about that box, and a note box that reaches you), and **plays** (a packet walks the flow, one caption per
step). You write the **spec** and the **depth**; the runtime lays out, routes, animates and wires the rest.

### The caps

| Slot | Cap |
|---|---|
| Title | ≤70 chars with a verb: what the system guarantees, not its name |
| Lede | ≤30 words |
| Boxes | ≤12 per canvas (≤9 as a report's spine). A 13th box means a segment. |
| Zones | ≤4 |
| Flows | 1 to 3; ≤9 steps each |
| Step `say` | exactly one sentence, ≤20 words; `msg` ≤24 chars |
| Box `label` | ≤16 chars; `tech` ≤24 chars |
| Connection `label` · `ms` | ≤16 chars · ≤20 chars |
| `peek` | ≤25 words, on boxes and connections |
| `facts` | ≤3 per box, ≤24 chars each |
| Zone `label` | ≤28 chars |
| Words on canvas at rest | ≤60 |
| Crossings, connections through boxes, labels shrunk to fit, zone labels crossed | 0 (measured by `--browser`) |
| Screens at rest | ≤2 for a drawing page |

### The spec

```html
<figure class="fv-drawing" data-mode="page">          <!-- data-mode="page" only on a drawing page -->
<script type="application/json">
{
  "id": "checkout",                                     // part of every note key: never rename
  "name": "Checkout",
  "title": "Checkout confirms in 300 ms because payment settles off the hot path",
  "lede": "Three services and one transaction sit on the request path.",
  "grid": { "cols": 5, "rows": 4 },
  "zones": [ { "id": "hot", "label": "Hot path · p99 300 ms", "cols": [1, 3], "rows": [0, 1], "tone": "sync" } ],
  "nodes": [
    { "id": "order", "label": "Order service", "kind": "service", "icon": "service", "at": [2, 1],
      "tech": "Go · 6 pods", "peek": "Owns the order lifecycle; answers 202 once the order commits.",
      "facts": ["p99 200 ms", "6 pods"], "segment": "order-outbox" } ],
  "edges": [
    { "id": "order-db", "from": "order", "to": "db", "mode": "sync", "label": "SQL", "ms": "p99 18 ms",
      "peek": "One transaction writes the order row and the outbox row." },
    { "id": "order-bus", "from": "order", "to": "bus", "mode": "async", "both": true, "label": "events" } ],
  "flows": [
    { "id": "place", "label": "Place order", "summary": "8 steps; the customer has an id after step 4.",
      "steps": [
        { "id": "p3", "path": ["order", "db"], "msg": "COMMIT", "say": "The order and its outbox row commit together." },
        { "id": "p4", "path": ["order", "gw", "web"], "msg": "202 Accepted", "say": "The customer gets an order id." },
        { "id": "d2", "path": ["pay", "psp"], "msg": "Charge", "fail": true, "say": "The processor declines the card." } ] } ]
}
</script>
<div class="fv-depth" hidden>
  <section data-for="order"> …tables, lists, div.cmd / div.cmd.fig… </section>
  <section data-for="step:p3"> … </section>
</div>
</figure>
```

(JSON has no comments; the `//` above is only for this page.)

- **`kind`** sets the tint — never pick colours: `client` `edge` `service` `data` `stream` `external`,
  and `threat` for an adversary (red, with a broken edge) so an attacker never looks like a partner.
- **`icon`**: `user devices browser mobile gateway lb cdn cloud globe server service function worker relay
  api check box db table cache storage search queue bell mail card bank lock key alert clock file json
  folder terminal agent chart gear git`.
- **Optional fields**: `tech`, `facts`, `peek`, `segment` on a box; `label`, `ms`, `peek`, `both`, `route`
  on a connection; `msg`, `fail` on a step. `ms` feeds the **Timings** layer — leave it out where there is
  no real latency (a user clicking, a redirect the human follows).
- **`mode`**: `sync` draws dashes, `async` draws slower dots. **`"both": true`** draws two lanes for
  traffic both ways — use it for publish + consume; a sync call implies its response and needs no lane.
- **Zones** are rectangles of cells: `"cols": [first, last], "rows": [first, last]`, **both inclusive**, so
  `"cols": [1, 3]` covers columns 1, 2 and 3 of the grid. Each has a `tone` (`neutral` `sync` `async` `ext`
  `data` `svc`) and a `tag` naming the corner its label sits in (`tl` `tr` `bl` `br`; on a one-column zone
  `tl`/`tr` only change the alignment). Pick a corner no connection runs through; `--browser` fails a label
  that one does, and names it.
- **Steps** walk connections: `path` lists two or more boxes, each consecutive pair joined by an edge in
  either direction. A path that walks back (`["order","gw","web"]`) is the response. `"fail": true` makes
  the last hop fail: the line turns red and the packet stops at a ✕.

### Placing boxes

The grid is the layout; you never write coordinates. `at: [col, row]`, zero-based, one box per cell.

- Read left to right, top to bottom: the client on the left, the request path on one row, stores and
  asynchronous work on the rows below. Group what shares a boundary into a zone.
- A connection between boxes on the same row or column is straight, and **may not pass through another
  box** — neighbours only, or move one to another row.
- A connection between different rows and columns bends in the gutter: it leaves the side facing its
  target. Keep those between **adjacent** columns or rows; a bend across two columns runs through the
  middle one. `"route": "h" | "v" | "hvh" | "vhv"` overrides the choice.
- Every edge should be walked by a flow; the audit notes the ones that are not.

### Recipes

| You want to show | Do this |
|---|---|
| **A whole system** | ≤12 boxes; zones for the boundaries that matter (trust, latency, ownership); up to three flows: the happy path, the read path, the failure path. |
| **The inside of one box** | Give the box `"segment": "<key>"` and add `segments.<key>`: `parent`, its own `title`, `lede`, `grid`, `nodes`, `edges`, `flows`. Its neighbours come along as ghosts: `"ghost": "<parent box id>"`, same kind and icon. The box shows ⤢; the human zooms in and back. |
| **One request, in order** | One flow, ≤9 steps, one hop or a short path each, the response as a path that walks back. The **Sequence** view lays it out in time with no extra work. |
| **What fails, and what then** | A flow whose breaking step has `"fail": true`, followed by the steps that compensate. |
| **Two options** | Two flows on one canvas, `Today` and `Proposed`. Boxes only one option needs go in a zone named for it. The connections only one flow walks are the difference — the human switches flows and watches them light up. |
| **A system as part of a report** | The report scaffold's spine already holds a drawing (≤9 boxes, no `data-mode`). Extra drawings go inside rows. |
| **A system too big for 12 boxes** | Split it into segments. A standalone drawing may itself be a segment (`"kind": "segment"`) of one drawn elsewhere. |

### Depth

`div.fv-depth > section[data-for="<key>"]` is layer 3 for one element, plain HTML with the report
components: tables, `div.cmd` for anything to run (paste rules apply), `div.cmd.fig` for code to read,
`div.box`. Keys: the box id, `edge:<id>`, `step:<id>`, and `<segment>/<key>` inside a segment. No
section is required; the drawer always shows the peek, facts, the steps a box takes part in, and a note.

---

## Reading what the human left

When they say "I ran it", "look at step 4" or "I left notes", run `flowviz captures <file>.html`. It reads
the sidecar `<doc>.flow.json` — **never the HTML, which holds no state** — and prints each capture joined
to its step sentence and blast radius, verdicts **re-derived from the current rules**, superseded runs
oldest first (a step showing `pass` may have failed twice first, and the earlier text is usually the
diagnosis), then every note left on a drawing, keyed `<drawing>/[<segment>/]node|edge|step:<id>`.

**`error` is not `fail`.** `fail` means the command ran and the target said no — evidence about the
system. `error` means the interpreter rejected the command, so the target was never asked — evidence
about your playbook; conclude nothing about the system. `no match` means the pass condition is probably
wrong about what the command prints.

No sidecar means they opened the file from Finder. Don't guess: ask them to `flowviz serve` the folder,
or to press **Copy captures for agent** and paste the block to you.

## Nine things not to do

1. **Don't hand-roll the page.** Scaffold with `flowviz new`; fill slots, don't invent structure.
2. **Don't paste CSS or JS into a deliverable**, and don't write layout coordinates in a drawing. Inlining
   is `build`'s job; drawing is the runtime's.
3. **Don't hard-code a colour, font or radius.** Tokens only; box colours come from `kind`. Check light
   **and** dark — both are designed.
4. **Don't open anything at load**: at most one report row, no drawer, no layer.
5. **Don't rename an id** after handover — doc, step, drawing, box, connection or flow step. It orphans
   what the human typed.
6. **Don't write a second sentence** into a step, a `say` or a peek. It goes one layer down.
7. **Don't use a CDN, web font or remote image.** Deliverables render offline and in print.
8. **Don't skip the audit**, and don't raise a cap to pass it. Split the report; make a segment.
9. **Don't overwrite a document your deliverable replaces** — an older write-up, a verbose page. Give yours
   another name beside it, so the two can be read together. Rebuilding your own deliverable in place is
   fine: `build` keeps each previous output in `.flowviz/history/`.

## Worked examples

```
~/Projects/FLOW_VIZ/PLAN.html                         a report with a drawing spine and a live checklist
~/Projects/FLOW_VIZ/examples/checkout/checkout.html   a drawing: 10 boxes, 3 flows, a failure path, one segment
```

Open each with `?audit=1` to see the caps measured on the page itself.
