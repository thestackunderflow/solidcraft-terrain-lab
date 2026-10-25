# SolidCraft terrain lab: Mount St. Helens from USGS elevation data, lofted

The lab behind "SolidCraft + Claude: Mount St. Helens from USGS Data" (SolidCraft for Beginners #5, The Stack
Underflow). USGS 3DEP heights become 50 slices; SolidCraft's loft turns the slices into a solid tile you can print.
Everything runs in Docker on SolidCraft 0.19.0.

What it found (22 Oct 2026):
- 50 slices drawn on SolidCraft's XZ plane and lofted: `ok: true`, no warning, and the mountain hangs UNDER the floor
  (z from -33.2 to 0 mm). On XZ a sketch's "up" points down in the world.
- Fix 1, told which way is up (`flip: true`, or a plane with x along X and y along Z): right way up, volume within 0.01%
  of the hand count, the highest point where the data's is.
- "Just flip it in the slicer" (turn it 180 degrees) puts it right way up but MIRRORED: the crater opens south instead of
  north, the highest point moves from y 44.5 to y 70.1 mm. A mirror across the floor plane is the one-step fix.
- Claude Code, same prompt, 3 runs: it noticed the upside-down loft each time and fixed it with a mirror: right way up
  and the right way round 3 of 3 ($1.22 in all).
- The data trap we hit: ask the USGS service for a grid whose shape differs from your box's shape and it returns square
  pixels covering a bigger box (`terrain/get_data.py` asks for 400 x 320 for a 0.10 x 0.08 degree box, and checks it).
Every number and its file: `ACCURACY.md`. Nothing here was printed; times and weights are the slicer's estimate.
Every 0.2 mm print layer is about 10 m of height at this scale and stretch. Known: the maker reviewer found 11 faces
wound backwards in SolidCraft's STL export; PrusaSlicer 2.9.2 still reports it manifold with 0 open edges (to clean up later).

## Your place: change one line
`terrain/get_data.py`: `BBOX = (west, south, east, north)` in degrees. Three limits: it must be inside the US (USGS 3DEP
covers the US); the box must keep the same 5 : 4 shape in degrees as ours, or the script stops (it checks that the grid
covers exactly your box: change the 400 x 320 grid size to match a different shape); and a low hill needs more stretch
than 1.5x (`STRETCH` in `terrain/make_slices.py`). Then run the steps below.

## Follow along: three ways
1. **Just print it.** `out/probe/0.19.0/plane/terrain.stl`: 100 x 115 x 33 mm, heights stretched 1.5x on a 3 mm base.
   Slicer estimate on an MK4S profile, 0.2 mm layers: about 2 h 47 min, 77 g.
2. **Build it with no AI.** `solidcraft-cli run steps/terrain-plane.json --out mountain.stl` (SolidCraft 0.19.0; the
   CLI is in the release download). `steps/terrain-xz.json` is the same, drawn on XZ: try it and see where it lands.
3. **Ask Claude.** Make the slices (`python3 terrain/get_data.py`, `python3 terrain/make_slices.py`), save them as a
   design (`solidcraft-cli run steps/slices-xz.json --save slices.solidcraft`), then give Claude the prompt in
   `claude-run/run.sh`. We ran Claude Code in a terminal with only SolidCraft's tools.

## Run the lab
```
docker build -t solidcraft-terrain-lab:0.19.0 .
docker run --rm -v "$PWD:/work" -w /work solidcraft-terrain-lab:0.19.0 python3 -m pytest -q tests/
docker run --rm -v "$PWD:/work" -v "$PWD/out/probe/0.19.0:/lab/out" -w /work solidcraft-terrain-lab:0.19.0 python3 probe/probe.py 0.19.0
```
Data credit: Map services and data available from U.S. Geological Survey, National Geospatial Program.
Licence: Apache-2.0 (code). Narration of the video: AI-generated voice.
