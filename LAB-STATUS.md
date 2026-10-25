# LAB-STATUS (22 Oct 2026)

**State: video done (PUBLISH/59, release Fri 6 Nov by default); lab stays local, no remote, until the video ships.** Plan: `Refream-Canvas/inputs/video-plans/2026-10-22-solidcraft-open-data/`
(PLAN rev 2.1 §6.2). Cards pinned at the commit in `video/panel-sources.json`.

- Data: USGS 3DEP 400 x 320 (square pixels checked), 50 slices x 44 points, 1.5x, base 3 mm (`data/`).
- Probe (no AI, $0): xz hangs under the floor; flip / plane / mirror right way up and round; slicer-flip mirrored;
  volume +0.01% vs the hand count.
- Slicer: PrusaSlicer 2.9.2, MK4S 0.4, PLA, 0.2 mm: 2h 47m 24s, 77 g, one part, no open edges (estimate).
- Agent runs: 3 plain, $1.22 (ledger shared by the four labs); 3 of 3 noticed and mirrored; up and round 3 of 3.
- Tests: 46 passed (`out/green-phase-all.log`); red logs `out/red-phase-*.log` (the scorer and the map picture were
  written in the same step as their tests).
- Frames: SolidCraft product renders (`video/make_frames.py`), the data picture (`video/map_png.py`), stills
  (`video/make_hook.sh`): hook-landscape, twist, hook-vertical (the Short: 1x vs 2x).
- Video: script gate applied (4 reviewers), regression gate 478 identical; render 5:19, -14.0 LUFS / -1.0 dBTP, QA no
  problems; Short 25.4 s, -14.4 / -1.5, QA no problems. Kit in `Refream-Canvas/inputs/mcp-usecases/solidcraft-terrain/`.
