#!/usr/bin/env bash
# Slice the right-way-up tile headlessly: PrusaSlicer 2.9.2 (image habs-slicer:0.2, from the lighthouse lab), profile P
# (Original Prusa MK4S 0.4 nozzle, Prusament PLA, PrusaSlicer's bundled presets, slicer/profile-P.ini) with ONE print
# override, --layer-height 0.2 (PLAN rev 2.1 §4.3). Writes out/slice/: info, log, G-code, report.
#   bash slicer/slice.sh
set -euo pipefail
cd "$(dirname "$0")/.."
EXP="$(pwd -W 2>/dev/null || pwd)"
OUT=out/slice; STL=out/probe/0.19.0/plane/terrain.stl
mkdir -p "$OUT"
MSYS_NO_PATHCONV=1 docker run --rm -v "$EXP:/w" -w /w habs-slicer:0.2 sh -c "
  set -e
  prusa-slicer --info '$STL' > '$OUT/info.txt' 2>&1
  prusa-slicer --load slicer/profile-P.ini --layer-height 0.2 --center 125,105 --binary-gcode=0 --export-gcode -o '$OUT/terrain.gcode' '$STL' > '$OUT/slice-log.txt' 2>&1
  python3 slicer/slice_report.py '$OUT/info.txt' '$OUT/terrain.gcode' '$OUT/slice-log.txt' > '$OUT/slice-report.json'
  dpkg -s prusa-slicer | grep ^Version >> '$OUT/slice-log.txt'
"
cat "$OUT/slice-report.json"
