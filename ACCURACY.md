# ACCURACY (lab): every number the video says → the file it comes from

SolidCraft 0.19.0 (release tarball, SHA256SUMS checked: `Dockerfile`), Claude Code 2.1.303, claude-sonnet-5-5,
PrusaSlicer 2.9.2 (`slicer/`). Measured 22 Oct 2026 in Docker. Cards pinned at the commit in `video/panel-sources.json`.

| Said / shown | Value | Source |
|---|---|---|
| The data: USGS 3DEP, 400 x 320 samples, box -122.24, 46.16, -122.14, 46.24 | sha256 f6ff705a… | `data/SOURCE.json`, `data/picture-grid.tif` (pixel scale checked: 0.00025 deg both ways) |
| 50 slices x 44 points, 2.3 mm apart; tile 100 x 115 mm; 1 : 77,049; heights x 1.5; base 3 mm | | `data/slices.json` `meta` (`terrain/make_slices.py`) |
| Lofted as drawn on XZ: ok true, no warning | | `out/probe/0.19.0/xz/transcript.jsonl` seq 8 (batch reply), `summary.json` (`loft_warning: null`) |
| Hangs under the floor: z -33.2 to 0 mm | -33.165 | `out/probe/0.19.0/xz/summary.json` (`bbox_min`), measure reply seq 10 |
| Right way up: z 0 to 33.2 mm | 33.165 | `out/probe/0.19.0/plane/summary.json`, measure reply seq 10 (same for `flip`, `mirror`) |
| Volume 166,209 mm3 vs hand count 166,191 mm3 (+0.01%) | | `plane/summary.json` (`volume_mm3`, `volume_vs_hand_pct`); hand count = shoelace areas of the same 50 slices, trapezoids along y (`terrain/sections.py hand_volume`) |
| Highest point x 44.2, y 44.7 mm; the data's highest sample x 44.2, y 44.5 mm | | `plane/summary.json` (`summit`), `data/slices.json` (`slices_max_at`) |
| Slicer flip: highest point at y 70.1 mm (mirrored); crater opens south | | `out/probe/0.19.0/slicer-flip/summary.json`; renders `video/frames/tilt-*.png` |
| The crater opens north (Mount St. Helens' 1980 crater) | | the data picture `video/frames/data-relief.png` (our shaded relief of the USGS grid, north up) |
| Our slices top 2,505 m; the 400 x 320 grid 2,525 m; USGS 2,539 m (2009 lidar) | | `data/slices.json` (`slices_max_m`, `grid_max_m`); https://www.usgs.gov/volcanoes/mount-st.-helens ("Elevation: 2,539 (m)"; "a lidar survey done in 2009 found the maximum elevation to be 2539 m") |
| 3 runs: right way up 3/3, right way round 3/3, mirror 3/3; $1.22 | | `out/runs/SCORES.json` |
| Claude's mirror call | | `out/runs/plain-1/transcript.jsonl` seq 34 |
| Slicer estimate 2h 47m 24s, 77 g; one part, no open edges | | `out/slice/slice-report.json` |
| Every 0.2 mm layer ≈ 10 m of height | 0.2 / (0.012979 x 1.5) = 10.3 m | `data/slices.json` meta (README only, not in the VO) |
| Square pixels: a 44 x 50 request came back 0.00227 deg/px and covered 46.143-46.257 N | | found 22 Oct while building (`terrain/sections.py pixel_scale`); lab note, not in the VO |

Not claimed: nothing was printed; "true height" only at 1.0x; no claim of the mountain's official height from our samples.
