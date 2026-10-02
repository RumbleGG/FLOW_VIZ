#!/bin/sh
# Builds the two pages of the to-dos and added-steps proposal, then injects the prototype layer
# (proto/). Approved and shipped in 3.1.0: the runtime now does this itself, so proto.js stands down on
# a 3.1.0 build and only proto.css is still used, by the static mockups in TODO-STEPS.
#   TODO-STEPS.html    the proposal, a FLOW_VIZ report
#   DEPLOY-PROTO.html  examples/deploy mid-run, with the demo run loaded
set -e
D=$(cd "$(dirname "$0")" && pwd)
F="$D/../../bin/flowviz"
for n in TODO-STEPS DEPLOY-PROTO; do
  [ -f "$D/$n.src.html" ] && "$F" build "$D/$n.src.html"
done
python3 "$D/proto/inject.py" $(for n in TODO-STEPS DEPLOY-PROTO; do [ -f "$D/$n.html" ] && echo "$D/$n.html"; done)
# served, the demo run arrives as the sidecar: written once, never over what you typed
[ -f "$D/deploy-proto.flow.json" ] || cp "$D/proto/seed-deploy.json" "$D/deploy-proto.flow.json"
