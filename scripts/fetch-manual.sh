#!/bin/bash
# Build the document used in the "hold a manual in its head" section.
#
# Qualcomm's documentation is theirs, so this repository ships the recipe rather than
# the text. The docs site serves a Markdown version of every page, which is what we pull.
#
# Usage:  ./fetch-manual.sh [output-file]
set -euo pipefail

OUT="${1:-iq9075-manual.txt}"
BASE="https://dragonwingdocs.qualcomm.com"

PAGES=(
  "Linux/devices/iq9075-evk/device-overview"
  "System/Interfaces/dragonwing-iq-9075-interface-overview"
  "Linux/devices/iq9075-evk/peripherals-interfaces/Camera"
  "Linux/devices/iq9075-evk/peripherals-interfaces/Audio"
  "Linux/devices/iq9075-evk/peripherals-interfaces/USB"
  "Linux/devices/iq9075-evk/peripherals-interfaces/PCIe"
  "Linux/devices/iq9075-evk/peripherals-interfaces/Ethernet"
  "Linux/devices/iq9075-evk/peripherals-interfaces/WiFi-BT"
  "Linux/devices/iq9075-evk/peripherals-interfaces/Sensors"
  "System/Power/power-addendum-iq9075"
  "Technologies/Display/display-specs-iq9075"
)

: > "$OUT"
for p in "${PAGES[@]}"; do
  echo "===== $p =====" >> "$OUT"
  curl -sfL "$BASE/$p.md" >> "$OUT" || echo "  (fetch failed: $p)" >&2
  echo >> "$OUT"
done

echo "wrote $OUT: $(wc -c < "$OUT") bytes, $(wc -w < "$OUT") words"
echo "(the run in the guide used 96,951 characters, about 24,000 tokens)"
