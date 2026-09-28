# FLOW_VIZ

A standard, and the toolkit that enforces it, for how agents hand finished work back to you: as one
self-contained HTML file whose main idea lands at a glance, with every bit of depth one gesture away.

It makes two things:

- **Reports** — a claim, the shape of the argument in six rows or fewer, evidence one click down, and a
  checklist playbook: every command you have to run is a step with a copy button, a blast-radius badge and
  a box to paste its output into. What you paste comes back to the agent, attributed to the step.
- **Drawings** — a system, or one segment of it, on a grid. The selected flow moves (dashes for calls, dots
  for events) so you see where data goes; hover for a one-line peek, click for everything, press
  **Walk through** to watch a request travel step by step. Boxes can open into their own drawing.

Three ideas carry it:

1. **The budget is measured, not trusted.** "Readable in two minutes" became countable caps — title length,
   words at rest, boxes per canvas, one sentence per step — and `flowviz audit` exits 1 when one is broken.
2. **Depth moves down a layer; it is never deleted.** The card and the canvas are tight; rows and the drawer
   are unlimited.
3. **The page is an input device.** Ticks, pasted output and notes on boxes save to `<doc>.flow.json` beside
   the page when it is served, and `flowviz captures` reads them back for the agent.

## Quick start

```sh
~/Projects/FLOW_VIZ/bin/flowviz                      # the whole workflow on one screen
open ~/Projects/FLOW_VIZ/PLAN.html                   # the toolkit's own plan, written to its standard
open ~/Projects/FLOW_VIZ/examples/checkout/checkout.html   # a drawing: three flows, a failure, a segment
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
bin/            flowviz (cheat sheet + dispatcher), new, build, audit, serve, captures
template/       flow.css flow.js (core, reports) · draw.css draw.js icons.svg (drawings) · two scaffolds
examples/       checkout/: the approved drawing, rebuilt by the toolkit
mockups/        the first hand-made mockup of the drawing look, kept for reference
```

Deliverables are written into the folder the work is in, never into this one. Stdlib Python 3 and a browser
are all it needs; nothing is installed and nothing touches the network.
