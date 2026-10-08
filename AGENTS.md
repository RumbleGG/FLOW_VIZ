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
$F captures ~/work/sto/STO.html           # later: what they pasted (text and images), every note and override, every step or to-do they added
$F fold ~/work/sto/STO.src.html           # the steps they added in the page, into the source, same ids
$F results ~/work/sto/STO.src.html        # once they have run it all: start the Results section
$F relabel ~/work/sto/STO.src.html        # an older report onto a, b, c and b1, b2: what was pasted moves too
```

The deliverable lives in **the folder the work is in**; this repository is only the toolkit. Nothing is
installed, nothing is on `PATH`, no network, stdlib Python only. **Serve it** — opened from Finder, what
the human types stays in their browser and never reaches you.

## Which agent does which step

One agent can do all of it. Shared out, each step goes to the **cheapest agent that gets it right the
first time**, and everything that decides what the deliverable *says* stays at the top. The tiers are
Claude's; a model of the same class serves the same role.

| Tier | Role | Does | Never |
|---|---|---|---|
| **Opus agent, or equivalent** | **Lead** | decides what to make and what it claims: title, verdict, so-what, vitals, next; the rows, their kinds and their order; every step's sentence, blast radius, pass and fail conditions and run order; a drawing's boxes, zones, segments, and whether it has flows. Reads what the human pasted, opens every image, judges a verdict set by hand, decides the Results | lets the audit decide for it: a split, a dropped row, a reworded claim is the Lead's call |
| **Sonnet agent, or equivalent** | **Builder** | turns the brief into a deliverable that audits clean: `flowviz new`, every slot written in the template's shape, regexes anchored, emits declared, boxes placed until nothing crosses, depth sections, `fold`, `relabel`; fixes every OVER and FAIL **whose fix leaves the meaning unchanged** | changes a claim, drops a row, splits a report, moves a step after handover, renames an id, or works around the runtime |
| **Haiku agent, or equivalent** | **Runner** | runs what it is given, exactly as written, and returns the output word for word: `build`, `audit --browser` (`--json` when asked), the parse checks, `serve`, `captures`, screenshots in light, dark and print, counts | decides, summarises, retries with a variation, edits a file, or runs a step of the human's playbook |

A brief going down carries the file paths, the exact commands and what to return. The Builder's brief
carries the Lead's decisions in the slots they belong in; the Builder returns the audit's result line and
whatever it could not fix without changing the meaning, which goes back up to the Lead. **If you are the
only agent, you are the Lead**: the table says where to spend thought, and what a cheaper agent could do
for you.

### When it stops behaving: the Supervisor

An **Opus agent, or equivalent**, with a different brief from the Lead's: troubleshoot the run, not the
argument. Hand over to one on the first of these, and stop changing the deliverable:

- a `flowviz` command tracebacks, exits 2, or prints something this file does not describe
- `--browser` cannot run, or measures a layout cap that no spec change moves
- the third rebuild still names the same OVER or FAIL
- `captures` shows `error` on more than one step: the playbook is failing, not the system
- the folder is served but the sidecar is missing or stale, `serve` answers 409, or something the human
  typed is gone
- the fix in front of you would rename an id after handover

The Supervisor is handed the audit output, the sidecar, the source and the last brief. It reproduces first
on the reference builds (`PLAN.html`, `examples/`) to tell a deliverable fault from a toolkit fault; fixes a
deliverable fault by naming the exact edit for the Builder; fixes a toolkit fault in `template/` or `bin/`
under `CLAUDE.md` and rebuilds the reference builds too; then returns what it found, what it changed and the
clean result line, and the Lead takes the handover from where it stopped. It never papers over a runtime
defect in a deliverable's markup, and never renames an id. Alone, do the same on the first trigger: stop
patching and troubleshoot as the Supervisor would.

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
`data-kind`. **You do not write the kind's label**: the page draws it from the attribute, the same way in
every report, and the audit fails a label that does not match what the row holds. **Rows are lettered a,
b, c… in the order they appear**: the letter is both the row's `data-row` and its `.ord`, and the
scaffold writes both.

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
<details class="row" data-row="d" data-kind="change">
<summary><span class="ord">d</span><span class="cl">Switching the app pool to full trust clears the 500</span><span class="rt">5 min</span></summary>
```

### Checklist steps — the playbook

A command the human must run is never a bare `<pre>`. It is a step: checkbox, id, one sentence,
blast-radius badge, copy button, verdict chip. The command, the expected result and the paste box sit
behind the disclosure, so a nine-step playbook reads as nine sentences.

**A step's id is its row's letter and its number in that row: `d1`, `d2` … `dn`.** Never a word
(`push`), never two letters (`bb`, `bc`): letters name rows, numbers name steps, so "look at d3" means one
thing on the screen, in the sidecar and in your read-back. A Results section's steps are `r1`, `r2`…. The
scaffold writes these ids and the page shows them where a bare number would be; the audit fails any
other. Ids are the join key for what the human pastes, so **never change one after handover** — to move
an older report onto this convention, `flowviz relabel` moves what was pasted along with the ids. A step
the human added after `d2` is `d2a` (then `d2b`), and keeps that id once you fold it in.

```html
<li class="step" data-step="d2" data-risk="ro" data-after="d1">
  <input type="checkbox" class="done">
  <details class="sd">
    <summary><span class="n"></span><span class="ds">One sentence, ≤20 words, what this establishes.</span></summary>
    <div class="in">
      <div class="cmd"><button class="copy">copy</button><pre><code>the command</code></pre></div>
      <p class="expect"><b>Pass:</b> what good looks like &nbsp;·&nbsp; <i>Fail:</i> what bad looks like</p>
      <div class="cap">
        <div class="cl">Paste output <span class="kp">captures["d2"]</span></div>
        <textarea data-cap="d2" data-pass="\bFull\b" data-fail="\bMedium\b|\bMinimal\b"
          placeholder="paste the terminal output here — it saves as you type"></textarea>
        <div class="ft">
          <span>exit <input class="ec" data-ec="d2" placeholder="0"></span>
          <span data-cnt="d2">empty</span><span data-at="d2"></span>
          <span class="rn" data-run="d2"></span>
          <button class="rr" data-rr="d2" title="keep this attempt and clear the box">re-run</button>
        </div>
        <input class="nt" data-note="d2" placeholder="note for the agent (optional)">
      </div>
      <details class="more"><summary>why this step</summary>
      <div class="in"><p>Traps, fallbacks, <code>file:line</code> citations — as long as it needs.</p></div></details>
    </div>
  </details>
  <span class="ctr"><span class="badge ro">read</span>
    <button class="copy">⧉</button><span class="vd" data-vd="d2">—</span></span>
</li>
```

Steps sit in a **playbook**, one per action row: `<div class="pb">` with a header `div.hd` — the title
`span.t` (what running it achieves), an optional target `span.tgt` holding a `data-var` input, and
`span.prog`, which the page counts — then `<ol class="steps">`. The scaffold puts every step in its last
row; to spread them across rows, copy the whole `div.pb` into each action row and number the steps from 1
in their new row, before anyone pastes.

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

### Order: they run it once, top to bottom

The human does each step as they reach it and never goes back. If *take a snapshot before deploying* turns
up after the deploy step, they must undo work already done, or carry on with no way back. **Write steps in
the order the work has to happen, not the order you thought of them.**

- **Everything a write needs goes above it.** That means the restore point (snapshot, backup, the current config exported,
  the installed version recorded), access and preconditions checked, the package staged and verified, and
  dependents stopped. Then comes the write, then the test that proves it, then the rollback.
- **A restore point goes above the first write it protects**, and the rollback restores from it by id.
  `examples/deploy/` records the running version in b1, writes in b2 and puts b1's version back in c1.
- **Rows run in letter order too**: look, prepare, change, test, undo.
- **`data-after` names a step above**, never one below.
- **A caveat goes in or above the step it governs**, never in a later row, which is read only after the command has run.
- **Before handover, read the step sentences top to bottom, as the human will.** At each one, ask whether
  it assumes something no step above has done. A sentence that says *before*, *first* or *make sure* names something
  that belongs above it. Reorder now: once they have pasted, ids are fixed and a step cannot move.

The audit notes, never fails, a restore point below a write, a *before X* below the step that already
does X, and a `data-after` that points down.

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
- **A value carried in from an earlier step obeys the same rules.** `{{d1.VER}}` (below) resolves only to
  1–120 printable ASCII characters with no quote, `$`, backslash, backtick, `;` `|` `&` `<` `>` or
  bracket; anything else, or no value yet, and copy refuses. Never write a `PASTE_…` placeholder for the
  human to overwrite — the audit warns on one.

The audit enforces the first four and the anchoring rule. The rest need an interpreter per language,
which the toolkit refuses to install: **they are yours**, and so is a pass condition that the command's
real output can actually falsify. Something **shown, not run** — a JSON sample, a tree, a log — is
`<div class="cmd fig">`: dashed, no copy button, exempt. Never use it to smuggle a command past the audit.

### A value one step prints, used by a later command

When a later command needs something an earlier step printed — a version, an id, a path — don't make the
human carry it across. Declare it on the producing step's paste box and name it in the later command:

```html
<textarea data-cap="d1" data-emit="VER=VERSION ([0-9][0-9.]+)" data-pass="…" data-fail="…"></textarea>
…
<pre><code>gh workflow run deploy.yml -f build-version="{{d1.VER}}"</code></pre>
```

- `data-emit` is one or more `NAME=<regex>` pairs, `;`-separated. Each regex has **exactly one** capture
  group; the value is that group from the **last** match in what was pasted, trimmed. It is re-derived on
  every paste and every load, and stored in the sidecar under `emits` beside the capture.
- `{{d1.VER}}` works in any later command. Until `d1` is pasted it shows as written and **copy refuses**
  with *d1 has not run*; afterwards the value appears in place, titled *from step d1*, and copy sends the
  resolved command. `${{ … }}` is someone else's syntax and is left alone.
- The producing step must come first on the consumer's `data-after` chain (or be the step itself); the
  audit warns when it is not, and **fails** a token whose step does not exist or declares no such name.
- `data-var` is for what only the human knows (a host name). An emit is for what an earlier step printed.

### When they have run it: Results

Once the human has worked the playbook and you have read `flowviz captures`, close the report with a
**Results** section. It goes **above the card** — what happened is now the main idea — and the card stays
as the plan that was tested.

1. `$F results <report>.src.html` inserts it with the outcome worked out from the sidecar (`blocked` if a
   command was rejected, `fail` if the target said no, `pass` if every step passed, else `inconclusive`),
   the chip and counts filled in, a drawing started from your spine drawing, and the archive step written.
   Check the outcome; it is a first reading, not a verdict you must keep.
2. Write the **claim** (`h2`, ≤70 chars with a verb: what happened), the **summary** (≤50 words: what ran,
   what it proved, where it stopped) and **next** (1 to 4, tagged).
3. **Mark the diagram**: `"result": "pass"` on the boxes and connections the run proved, `"fail"` where the
   target said no, `"error"` where a command never ran. Green, a red ✕, an amber ⚠ — no flows needed, and
   the marks must agree with the outcome.
4. Keep the **archive step** (`r1`): one gated write step that moves the finished folder into the workspace's
   archive (`~/Archive` when it exists; `--archive-to` for another). Suggest it in your reply too; never
   move anything yourself.
5. Rebuild, `audit --browser`, hand it back. The worked example is `examples/deploy/`.

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
| Value from an earlier step | `data-emit="VER=VERSION ([0-9.]+)"` on the step's `textarea`, `{{d1.VER}}` in a later command |

---

## Drawings

A drawing shows a whole system, or one segment of it, with its connections moving in their direction.
The human **looks** (boxes, zones, motion), **hovers** (a one-sentence peek) and **clicks** (the drawer:
everything you know about that box, and a note box that reaches you). You write the **spec** and the
**depth**; the runtime lays out, routes, animates and wires the rest.

**Flows are off by default.** Leave `"flows": []` unless the human asked for a walkthrough of the order of
events; then add up to three, and the drawing gains flow chips, step numbers and **Walk through** (a packet
walks each flow, one caption per step), plus a Sequence view.

### The caps

| Slot | Cap |
|---|---|
| Title | ≤70 chars with a verb: what the system guarantees, not its name |
| Lede | ≤30 words |
| Boxes | ≤12 per canvas (≤9 as a report's spine). A 13th box means a segment. |
| Zones | ≤4 |
| Flows | 0 by default; up to 3 when a walkthrough is asked for, ≤9 steps each |
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
| **One request, in order** *(when asked for)* | One flow, ≤9 steps, one hop or a short path each, the response as a path that walks back. The **Sequence** view lays it out in time with no extra work. |
| **What fails, and what then** *(when asked for)* | A flow whose breaking step has `"fail": true`, followed by the steps that compensate. |
| **Where a real run passed or failed** | No flows: `"result"` on the boxes and connections — see Results above. |
| **Two options** | Two flows on one canvas, `Today` and `Proposed`. Boxes only one option needs go in a zone named for it. The connections only one flow walks are the difference — the human switches flows and watches them light up. |
| **A system as part of a report** | The report scaffold's spine already holds a drawing (≤9 boxes, no `data-mode`). Extra drawings go inside rows. |
| **A system too big for 12 boxes** | Split it into segments. A standalone drawing may itself be a segment (`"kind": "segment"`) of one drawn elsewhere. |

### Copy HTML

Every drawing has a **Copy HTML** button the human uses to paste the drawing into a wiki page. You write
nothing for it: the copied snippet carries its own scoped styles, runtime and a still fallback, so it is fully
interactive where the wiki allows scripts and still shows the picture and every box's details where it does
not. Write depth sections knowing they may be read there too.

### Depth

`div.fv-depth > section[data-for="<key>"]` is layer 3 for one element, plain HTML with the report
components: tables, `div.cmd` for anything to run (paste rules apply), `div.cmd.fig` for code to read,
`div.box`. Keys: the box id, `edge:<id>`, `step:<id>`, and `<segment>/<key>` inside a segment. No
section is required; the drawer always shows the peek, facts, the steps a box takes part in, and a note.

---

## Reading what the human left

When they say "I ran it", "look at b4" or "I left notes", run `flowviz captures <file>.html`. It reads
the sidecar `<doc>.flow.json` — **never the HTML, which holds no state** — and prints each capture joined
to its step sentence and blast radius, verdicts **re-derived from the current rules**, every value it
emitted (`d1 -> VER=12.149.3747.21500`), superseded runs
oldest first (a step showing `pass` may have failed twice first, and the earlier text is usually the
diagnosis), then every note left on a drawing, keyed `<drawing>/[<segment>/]node|edge|step:<id>`.

**`error` is not `fail`.** `fail` means the command ran and the target said no — evidence about the
system. `error` means the interpreter rejected the command, so the target was never asked — evidence
about your playbook; conclude nothing about the system. `no match` means the pass condition is probably
wrong about what the command prints.

**What they added.** Mid-run the human can add a step where one was missing and keep to-dos; the page
does this itself and you write nothing for it. `captures` prints an added step in place — `+    b3a  read
CAPTURED …`, captured because it has no rule yet — and the to-dos after the playbooks: *add to write-up*
(the write-up is missing something) or *do after* (a task once the run is over). Decide what each becomes:

- **A step that belongs**: `$F fold <NAME>.src.html` writes it into the source after the step it followed,
  under the same id, so its output re-attaches; the next step's `data-after` follows. Then write what fold
  leaves in the template's words — pass and fail, their regexes, and the gate if it writes — and rebuild.
  `--todo t2` folds an *add to write-up* to-do the same way, after the step it is tied to.
- **A step in the wrong words**: fold it, then reword the sentence. Never renumber the steps around it.
- **A do after**: a Next item when you write Results; `flowviz results` lists the open ones.

**What they showed you.** A capture can hold images as well as text: `captures` prints each one as
`image  b4·1  <absolute path>  960x330  "caption"`. **Open every image before you conclude** — it is evidence,
like pasted output, and its caption is their description of it, not a substitute for looking. One marked
*only in the browser that took it* has not reached disk: ask them to serve the folder and open the page.

**What they decided.** A verdict with a ✎ was set by hand: `captures` prints it with the derived verdict and
their reason (`✎ set by hand 13:52 PDT, derived FAIL: "…"`). Report it as theirs, with that reason, and say so
when the evidence does not support it. Never change a rule just so it agrees with an override without saying
why; *the output changed after it was set* means they have not looked again.

No sidecar means they opened the file from Finder. Don't guess: ask them to `flowviz serve` the folder,
or to press **Copy captures for agent** and paste the block to you.

## Nine things not to do

1. **Don't hand-roll the page.** Scaffold with `flowviz new`; fill slots, don't invent structure.
2. **Don't paste CSS or JS into a deliverable**, and don't write layout coordinates in a drawing. Inlining
   is `build`'s job; drawing is the runtime's.
3. **Don't hard-code a colour, font or radius.** Tokens only; box colours come from `kind`. Check light
   **and** dark — both are designed.
4. **Don't open anything at load**: at most one report row, no drawer, no layer.
5. **Don't rename an id** after handover — doc, row, step, drawing, box, connection or flow step. It
   orphans what the human typed. (`flowviz relabel` is the one safe move: it takes the state with it.)
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
~/Projects/FLOW_VIZ/examples/deploy/DEPLOY.html       a report after its run: Results on top, a value b1 printed used by c1
```

Open each with `?audit=1` to see the caps measured on the page itself.
