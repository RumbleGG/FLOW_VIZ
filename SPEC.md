# FLOW_VIZ — the standard

**Version 3.6.1** · normative. Where this document and a deliverable disagree, the deliverable is wrong.

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
| **2 — Spine** | one diagram (+ one detail drawing, §1.2c) + ≤6 collapsed rows under ≤3 headers | the shape of the thing, then one labelled row per idea |
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
| Detail | optional; exactly 1 drawing when present | Directly under the spine, on its own cap tier (§1.2c). |
| Rows | ≤6 | Seven ideas is two reports. |
| Row summary | a claim with a verb, ≤14 words | The collapsed spine reads as a six-line argument. |
| Open at load | ≤1 row | The cap most often broken; it is what makes a file feel like a wall. |
| Section headers | ≤3, ≤4 words each; no row before the first | They say what the rows below are for, so six claims are not six mysteries. |
| Row kind | every row has one (§1.2a) | The reader knows before opening a row whether to read it or act on it. |
| Step sentence | exactly one sentence, ≤20 words | A nine-step playbook reads as nine sentences. |
| Words at rest | ≤350 | Card text plus row summaries. The two-minute budget, made countable. |
| Screens at rest | ≤3 | Needs layout: measured by `?audit=1` or `flowviz audit --browser`. Compared unrounded and shown rounded up to two decimals, so `3.01` is over and nothing over ever reads `3.0`. |

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

### 1.2c The detail slot — the code inside the system

A spine draws a system at the scale of services. Some reports also need the scale below it — one box per
class, one connection per method call, the calls of one request in order — and that picture needs more
boxes and longer walkthroughs than a spine may have. It gets a place of its own instead of an exception.

| Part | Rule |
|---|---|
| Markup | `<div class="detail">` holding exactly one `figure.fv-drawing`, a child of `<body>` placed **directly after `div.spine`**, before the control bar. At most one per report. `flowviz new report … --detail [boxes]` scaffolds it; off by default. |
| Caps | **≤20 boxes, ≤4 zones, ≤2 flows, ≤20 steps per flow**. Title, lede, label, tech, peek, facts, words on canvas, crossings 0, labels shrunk 0, connections through boxes 0, zone labels crossed 0: as for every drawing. A segment of a detail drawing is an ordinary canvas (§2.2). |
| Audit | Its own section, `detail <id>`, in `flowviz audit` and on `?audit=1`; three structural rows where a detail exists: one slot, one drawing in it, directly under the spine. A report without one audits as before. |
| Status | A detail drawing usually marks what a change did to each class: `"status"` on a box (§2.4). |
| Budget | The page keeps ≤3 screens at rest and ≤350 words. A report with a detail usually needs a two-line title and a shorter verdict; when it still does not fit, it is two reports. |

The spine stays one drawing with its own caps, and further drawings still live inside rows.

### 1.3 Checklist steps

A playbook step is **a checkbox, its id, and one sentence.** That is all that is visible.

| Rule | Detail |
|---|---|
| Description | Exactly one sentence, ≤20 words, stating what the step *establishes* or *changes*. |
| Command | Behind the disclosure. The `⧉` on the collapsed row copies it without opening anything, prompts stripped. |
| Blast radius | `data-risk="ro"` or `data-risk="w"` on every step. A `w` step blurs its command until the acknowledgement is ticked, and `⧉` refuses to copy it — it opens the step and says *tick the gate*. |
| Id | `<row letter><n>` (§1.2b), shown where the counter was. |
| Prereqs | `data-after="<id>"` dims the step until that one is done or captured. It names a step above (§1.3d). |
| Carried value | `data-emit` on the producer's textarea, `{{<step>.<NAME>}}` in a later command (§1.3a). |
| Capture | Every step has a textarea, an exit-code field, a one-line note, and its sidecar key shown beside it. The textarea also takes images (§1.3c); only its text is matched against the rules. |
| Figure | A picture of what the human should see — a screenshot, a photo that exists — is a `figure.shot` inside the step (§1.3e), inlined by the build. |
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

### 1.3d Order — run once, top to bottom

The human runs a playbook in the order it is written, each step as they reach it. A step that belonged
earlier — *snapshot the VM before deploying*, found below the deploy — makes them back-pedal over a change
already made, or go on without a way back. Steps are written in the order the work must happen.

| Rule | Detail |
|---|---|
| Run order | Rows run in letter order, steps in number order. No step asks for something a step above should have done. |
| Before a write | Everything the write needs sits above it: the restore point (snapshot, backup, the current config exported, the installed version recorded), access and preconditions checked, the package staged and verified, dependents stopped. Then the write, the test that proves it, the rollback. |
| Restore point | Above the first write it protects. The rollback restores from that step by id (`examples/deploy/`: b1 records the version, c1 puts it back). |
| `data-after` | Names a step above it. |
| Caveats | A warning that changes whether or how to run a step sits in that step or above it, never in a later row. |
| Fixed at handover | Reorder before handover. Once the human has pasted, ids are join keys (§1.2b) and a step cannot move. |

The audit reports, without blocking, what it can read from the sentences (§3): a step that takes a restore
point, or says *before X*, below a write that already does X, and a `data-after` that points down. It reads
words, not intent, so a clean audit is not a correct order — the read-through is the author's.

### 1.3e Figures — what the human should see

Some steps end at a screen, not a console: a wizard page, a dashboard, a dialog with one line to read. A
picture of it says what no sentence can — *this* page, *that* line — and a photo that already exists (last
run's evidence, the rack as it was) belongs beside the row or step that argues from it. A figure is the
author's picture; the human's pictures are evidence (§1.3c), and the two never share a strip.

| Part | Rule |
|---|---|
| Markup | `<figure class="shot"><img src="shots/ready.png"><figcaption>…</figcaption></figure>`. The `src` is a file beside the source — by convention `<dir>/shots/` — never a URL (§4). |
| Where | Inside a row's body, a step, or a drawing's depth section: layer 3. Never on the card or the spine, and on a drawing page only in a depth section. A figure is read one gesture down, not at rest. |
| Caption | Required: one sentence, ≤20 words, saying what to look at. It is the `alt` when none is written. |
| Build | `flowviz build` inlines the file as a data URI and stamps the `img` with `data-file`, `data-sha256`, `data-bytes`, `width` and `height`, so the page stays one file. It refuses a missing file, a remote image, anything that is not PNG, JPEG, GIF or WebP, and anything over 10 MB. |
| At rest | A thumbnail 360 px wide with its caption; two sit side by side. Click, Enter or Space opens it full size in the evidence viewer with its file, pixels, size and hash; ← → walk the figures of the same step, row or depth section. On a drawing page the figure is cloned into the drawer with its depth section. Print shows every figure full width, with its file and sha256. |
| Caps | Each figure ≤1 MB; a page's figures ≤6 MB together; caption ≤20 words. A larger picture is shrunk first (`sips -Z 1200`, or a smaller `--size`); more pictures than fit are a second report. |
| Where it comes from | `flowviz shot <url \| file> --out <dir>/shots/<name>.png`: headless Chrome on anything with an address, a built page included (`?audit=1`, `--theme dark`). A picture that exists — a photo, a prior run's `<doc>.assets/<sha256>.png`, whose path `flowviz captures` prints — is copied into `shots/`. A window on the human's own screen is theirs to capture, with them at the keyboard. |

Words and screens at rest are unchanged: a figure sits below the layer they measure. The audit measures the
three caps and the four checks in §3 only where a figure exists, so a page without one audits as before.

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
| SQL is checked by running it | No parser here reads SQL: `bash -n` on `psql -c "…"` checks the quoting, not the statement. Run it read-only against the real database. | you |

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

### 1.8 PR helpers — one pull request, explained to its reviewer

A PR helper is a report with a fixed shape, made often, read by the person who approves the change. It is
read-only: no playbook steps, and the card says so. What a reviewer reads as code, diff or count is copied
by `flowviz pr fill` from saved inputs, never typed.

| Part | Rule |
|---|---|
| Inputs | Saved read-only beside the report, in `pr/`: `pr.json` (`gh pr view --json number,title,url,headRefOid,…,files,commits,reviews,comments,statusCheckRollup`), `pr.diff` (`gh pr diff`), `review-comments.json`; and a local checkout of the PR head. `<meta name="flowviz-pr" content='{"url","number","head","pr","diff","checkout"}'>` names them, relative to the report. |
| Pin | The head commit is in the meta and on the card's meta line; every line number is read at that commit (`git show <head>:<path>`). A moved PR is re-pinned on purpose: `flowviz pr fill --repin`. |
| Diagrams | Always two: the spine (the path through the system, a zone around what the PR touches, the happy path and the main rejection path as flows) and the detail (§1.2c: the class call graph for that path, one call-order flow, `status` on every class the PR adds or changes; an unchanged helper folded into its caller's box says so in that box's depth). |
| Rows | Three groups, under the headers *What is new* (the new path hop by hop, each hop a disclosure: one line visible, the excerpt inside), *Shared changes* (each change that also runs outside the stated feature, in a table with *who else runs it* and *risk*, each with a disclosure) and *Files and review* (the per-file list; a reviewer table — who asked what, fixed, disputed with evidence, or open at the pinned head — above the generated reviews and CI; the commit table). |
| Per-file list | **GitHub's order, strictly**: the order `pr.json` carries, which is the Files changed tab's; never alphabetized or regrouped. **One sentence visible, the exact diff behind one click**: name, `+added −removed` and the author's sentence at rest; inside, the author's bullets, the new test methods of a test file, then the file's hunks verbatim. |
| Card | Vitals: files changed, lines added and removed, commits, new tests (counted: `data-pr`), and the PR's own unit of change. A broader tracker report, when one exists, is linked both ways by row id. |

`flowviz pr fill` expands each marker after itself, up to `<!-- /pr -->`, and replaces that span on every
fill; it writes nothing unless every marker resolves, and keeps the previous source in `.flowviz/history/`:

| Marker | Becomes |
|---|---|
| `<!-- pr:lines PATH A-B -->` | `div.cmd.fig.src[data-pr-src][data-pr-lines]`: lines A–B of PATH at the head, numbered |
| `<!-- pr:hunk PATH N\|@L -->` | `div.cmd.fig.diff[data-pr-hunk][data-pr-n]`: that hunk, verbatim |
| `<!-- pr:diff PATH -->` | `div.cmd.fig.diff[data-pr-diff]`: every hunk of PATH, verbatim |
| `<!-- pr:files -->` | `div.prf` of `details.prf-file[data-file][data-add][data-del]`, in GitHub's order |
| `<!-- pr:commits -->` · `pr:reviews` · `pr:checks` | the commit table · each reviewer's latest review and the commit it was left on · the CI checks |

The author's words survive a fill: `span.prf-s`, whatever sits between `<!-- pr:notes -->` and
`<!-- /pr:notes -->`, and a commit's `td.what`. A range that cuts a block (braces that do not balance, or a
next line indented deeper than the first) is warned about. A diff is coloured line by line and never
altered; its `+` and `-` stay in the text. Caps are the report's; the per-file list, the excerpts and the
diffs are layer 3.

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
| Boxes | ≤12 per canvas; **≤9** when the drawing is a report's spine diagram; **≤20** when it is a report's detail (§1.2c). One more means a segment. |
| Zones | ≤4 |
| Flows | 0 to 3 per canvas (≤2 in a detail); 0 unless the human asked for a walkthrough |
| Steps | ≤9 per flow (≤20 in a detail) |
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
| Labels shrunk to fit | 0 — needs layout. Box labels: a box is a fixed width. A connection's label chip grows to fit and shows only with Labels or Timings on, so it is never shrunk and not measured |
| Zone labels crossed by a connection | 0 — needs layout |
| Peeks cut off | 0 — needs layout. Every box's and connection's peek must land whole inside the window, cut off by no ancestor |
| Clicks that open no drawer | 0 — needs layout. A click at a box's middle must reach the box and open its drawer, with nothing covering either |
| Screens at rest (drawing page) | ≤2 — needs layout |

The last six are measured by `?audit=1` or `flowviz audit --browser`, which names each offender — the
pair that crosses, the box and its label that shrank, the peek and what cut it off, the box and what
covered it; everything else is read from the spec without a browser. Peeks and clicks are the runtime's
own behaviour: a failure there is the toolkit's fault, never the author's, and goes to the toolkit. The tiers — every canvas, a report's spine (and Results drawing), a report's detail — live in
`TIER` in `draw.js` and `TIERS` in the audit.

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
| Solid ink tag NEW on a box's foot | `"status": "new"` — the change being explained adds this box |
| Outlined tag CHANGED | `"status": "changed"` — the change alters it |
| Dashed tag REMOVED, label struck through | `"status": "removed"` — the change takes it out |

A status tag has no hue, so it never reads as a kind (fill) or a result (border, corner glyph, green, red
or amber), and the three differ in grey print by fill and stroke. It appears in the Key when the drawing
uses it, in the peek and the drawer, in the still picture and the details of Copy HTML.

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
| node `icon` | one of the icon set listed in `AGENTS.md`: illustrations whose ink is fixed and whose fills come from the box's kind |
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
| node `status` | optional: `new` · `changed` · `removed` — what the change a drawing explains did to that box. Counted by the audit (*9 of 13 boxes: 4 new, 5 changed*) and on `?audit=1`. Replaces a marker typed into a label, with no id change |

Routing is deterministic: a connection leaves the side of its box that faces the target and bends only in
the gutter between cells. Straight connections own the centre of a side; bent ones fan out beside them.
**A straight connection may not pass through a box** — move a box, or add `route`.

### 2.5 Depth

`div.fv-depth > section[data-for="<key>"]` holds layer 3 for one element, as plain HTML (tables, code
blocks with `data-copy` buttons, lists, a `figure.shot` — §1.3e — for a picture). Keys: `<nodeId>`,
`edge:<edgeId>`, `step:<stepId>`, and inside a segment `<segmentId>/<key>`. A missing section is fine; the
drawer still shows the peek, facts, steps and the note box.

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
| spec: vocabulary | a `kind`, `icon`, `mode`, `tone`, `tag` or `status` outside the lists above |
| detail slot | where a `div.detail` exists: more than one, other than exactly one drawing in it, or not directly under the spine (§1.2c) |
| spec: grid | a box outside the grid, two boxes in one cell, or a zone outside the grid |
| spec: straight through a box | a straight connection that would pass through another box |
| row kind matches its content | an action kind with nothing to run or tick, a read kind that holds steps, or a kind outside §1.2a |
| section letters and step ids | a row not lettered in order or not showing its letter, a step not `<row letter><n>` in order (or, folded in from the page, the step before it plus the next letter), a Results step not `r<n>`, or a step outside every row and the Results section (§1.2b) |
| emit: regex | a `data-emit` pair that is not `NAME=<regex>`, declares a name twice, does not compile, or has other than one capture group |
| emit: dangling reference | a `{{<step>.<NAME>}}` whose step does not exist, or does not emit that name |
| figure: inlined | a built page holds an `<img>` whose `src` is not an inlined PNG, JPEG, GIF or WebP |
| figure: captioned | a `figure.shot` with no caption (§1.3e) |
| figure: image in a figure | an `<img>` outside `figure.shot`, or a `figure.shot` with no `img` |
| figure: placement | a figure on the card, the spine or the detail; on a drawing page, outside a depth section |
| pr: inputs · pinned · read-only · two diagrams · markers filled | a PR helper (§1.8) whose inputs are not beside it; whose head is not on the card or is not `pr.json`'s; that has a step or no detail drawing; or that holds a marker not yet filled or still reading `PATH` |
| pr: file rows match the diff | a changed file with no row, a row for a file not in the diff, a file twice, a row out of GitHub's order, or counts that differ from the diff's |
| pr: code and diffs verbatim · card counts | an excerpt that is not those lines at the head, a hunk that is not the saved diff's, or a `data-pr` vital that is not the count |

The figure caps — largest figure ≤1 MB, figure bytes ≤6 MB, caption ≤20 words — are measured beside these,
only where a figure exists. `flowviz build` refuses the two emit failures too, so a token that can never
resolve never ships, and refuses a missing, remote, oversize or non-image figure file.

Reported, not blocking: **unused connection** — an edge no flow walks (it is still drawn; walk it in a flow
or delete it); **emit: ordering** — a token whose producer is neither the step itself nor on its
`data-after` chain; **PASTE_ placeholder** — a `PASTE_…` word in a command, which the human would have
to overwrite: use an emit from the producing step instead; **order: prepares after a write** — outside a rollback row, a
step below a write that takes a restore point (snapshot, backup, checkpoint, the current state saved), or
says *before X* where a write above already does X (§1.3d); **order: data-after points down** — a step
that waits on one below it; **figure: file outside the folder** — a figure named by an absolute, `~` or
`..` path, which a rebuild elsewhere will not find (copy it into `shots/`); **figure: over 1 MB** — with
the command that shrinks it; **boxes with a status** — *N of M boxes: …*, per canvas; **marker typed into
a label** — a `✱`, `*`, `(new)` and the like at a label's edge: set `status` instead; **pr: excerpts not
re-read** — the checkout a PR helper names is not on this machine; **steps added in the page** and **open to-dos**
— read from the sidecar beside the page, when there is one: fold, reword or carry them (§1.3b).

---

## 4. Banned

- Numbered `§1–§12` outlines. Numbering invites completeness; completeness fights the budget.
- More than one `<details open>` in a report; any drawer or layer open at load in a drawing.
- Prose above the verdict. The card is always the first thing on a report.
- A command the reader must edit before running, unless its one sentence says so.
- CDN `<script src>`, web fonts, remote images. Deliverables render offline, locked down, and in print. A
  picture is a file beside the source that the build inlines (§1.3e).
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
| **drawing page** | *canvas*: cool white `#F5F7FB` ground, plain white canvas, boxes in a pale tint inside a 2px outline of their kind, illustrated icons, dotted zones with a solid tag, navy ink | *night*: deep navy `#0A0F1D`, dark tints inside luminous outlines, the same icons, the same grammar |

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
| minor | new component, caps unchanged (0.6.0 added drawings; 2.1.0 added Copy HTML; emits arrived in 3.0.0 beside a major change; 3.1.0 added steps and to-dos the human writes into the page; 3.2.0 added images and verdicts set by hand; 3.3.0 put playbooks in run order; 3.4.0 added figures the author shows, with their own caps, and `flowviz shot`; 3.5.0 added the detail slot with its own cap tier, a box's `status`, and PR helpers with `flowviz pr`; 3.6.0 gave every drawing one outlined, illustrated look) |
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
$F shot https://grafana.example.test/d/x --out ~/work/sto/shots/latency.png   # a figure's picture, by headless Chrome
$F new report "Refunds reuse the payment path" --dir ~/work/pr --detail 14     # a report with the detail slot
$F pr                                  # the inputs a PR helper needs, and the commands that save them
$F pr new "<claim>" --dir ~/work/pr --pr ~/work/pr/pr/pr.json --diff ~/work/pr/pr/pr.diff --checkout ~/src/shop-418
$F pr fill ~/work/pr/PR-418.src.html   # every marker from the saved inputs; --repin when the PR moved
```

Authors edit `.src.html`. The built `.html` is one file: no asset paths, no network, every figure inlined.
Deliverables are generated into the folder the work is in; this repository is the toolkit they are cut from.
