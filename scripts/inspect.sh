#!/bin/bash
# Inspect one image and print a JSON verdict.
#
# Usage:  ./inspect.sh <image> ["custom inspection instruction"]
#
# With no instruction it looks for general manufacturing defects. Pass your own to
# retarget it: the model needs no retraining, only a different sentence.
set -euo pipefail

LLAMA="${LLAMA_CPP:-$HOME/llama.cpp}"
MODEL="${MODEL:-$HOME/models/muse-glimmer-30B-kquant-17gb.gguf}"
MMPROJ="${MMPROJ:-$HOME/models/mmproj-kquant.gguf}"

IMAGE="${1:?usage: inspect.sh <image> [instruction]}"
DEFAULT_SPEC='Inspect this circuit board for manufacturing defects. Reply with ONLY a JSON object and nothing else: {"pass": true|false, "defect": "...", "location": "...", "severity": "low|medium|high", "reason": "..."}'
SPEC="${2:-$DEFAULT_SPEC}"

# --jinja is required, or the CLI aborts on this model's chat template.
# "Reasoning strength" belongs in the system message; the --reasoning* flags do not
# stop this model from thinking.
exec "$LLAMA/build/bin/llama-mtmd-cli" \
  -m "$MODEL" --mmproj "$MMPROJ" --jinja \
  -t 8 -c 8192 -n 500 \
  -sys "You are an automated PCB inspection system.

Reasoning strength: low." \
  --image "$IMAGE" \
  -p "$SPEC"
