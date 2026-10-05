# FLOW_VIZ

A standard, and the toolkit that enforces it, for how agents hand finished work back to you: as one
self-contained HTML file whose main idea lands at a glance, with every bit of depth one gesture away.

It makes two things:

- **Reports** — a claim, the shape of the argument in six rows or fewer, evidence one click down, and a
  checklist playbook: every command you have to run is a step with a copy button, a blast-radius badge and
  a box to paste its output into. What you paste comes back to the agent, attributed to the step. Rows are
  lettered and steps numbered within them — `b1`, `b2` — so "look at b3" is never ambiguous, and a value
  one step prints can flow into a later step's command without being retyped.
- **Drawings** — a system, or one segment of it, on a grid. The selected flow moves (dashes for calls, dots
  for events) so you see where data goes; hover for a one-line peek, click for everything, press
  **Walk through** to watch a request travel step by step. Boxes can open into their own drawing.

Three ideas carry it:

1. **The budget is measured, not trusted.** "Readable in two minutes" became countable caps — title length,
   words at rest, boxes per canvas, one sentence per step — and `flowviz audit` exits 1 when one is broken.
2. **Depth moves down a layer; it is never deleted.** The card and the canvas are tight; rows and the drawer
   are unlimited.
3. **The page is an input device.** Ticks, pasted output and screenshots, verdicts the human set by hand,
   notes on boxes, steps they found missing and to-dos they remembered mid-run save beside the page when it
   is served (`<doc>.flow.json`, and images in `<doc>.assets/`), and
   `flowviz captures` reads them back for the agent; `flowviz fold` writes added steps into the source.

## Quick start

```sh
~/Projects/FLOW_VIZ/bin/flowviz                      # the whole workflow on one screen
open ~/Projects/FLOW_VIZ/PLAN.html                   # the toolkit's own plan, written to its standard
open ~/Projects/FLOW_VIZ/examples/checkout/checkout.html   # a drawing: three flows, a failure, a segment
open ~/Projects/FLOW_VIZ/examples/deploy/DEPLOY.html       # a report after its run: Results on top
~/Projects/FLOW_VIZ/bin/flowviz serve ~/Projects/FLOW_VIZ --open PLAN.html   # so your pastes reach disk
```

To point an agent at it, tell it: *read `~/Projects/FLOW_VIZ/AGENTS.md` and hand this back as a FLOW_VIZ
report* (or *drawing*).

## What is where

```
AGENTS.md       the only file an agent in another folder needs
SPEC.md         the standard: caps, motion grammar, schemas, versioning
CLAUDE.md       for agents changing the toolkit itself
VERSION         stamped into every deliverable's footer
CHANGELOG.md    why each version changed
PLAN.src.html   the toolkit's plan, as a report  →  PLAN.html
bin/            flowviz (cheat sheet + dispatcher), new, build, audit, serve, captures, fold, results, relabel
template/       flow.css flow.js (core, reports) · draw.css draw.js icons.svg (drawings) · scaffolds
examples/       checkout/: the approved drawing, with flows · deploy/: a report closed with Results
mockups/        approved mockups, kept for reference: the drawing look (checkout-system.html), and
                to-dos and added steps (todo-steps/: the proposal, and the prototype it was tried on)
```

Deliverables are written into the folder the work is in, never into this one. Stdlib Python 3 and a browser
are all it needs; nothing is installed and nothing touches the network.
