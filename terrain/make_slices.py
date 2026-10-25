"""Heights -> 50 slices -> SolidCraft command files (PLAN rev 2.1 §6.2).

    python3 terrain/make_slices.py      (after get_data.py; in the lab image)

Tile 100 mm east-west, north-south in proportion (about 115 mm), 50 slices about 2.3 mm apart, 44 points per slice (the
same spacing across), heights stretched 1.5x on a 3 mm base. Writes:
  data/slices.json                  the slices + the numbers they were made with (scale, stretch, hand-count volume)
  steps/slices-xz.json              the 50 sketches only, drawn on XZ as a plain script would (the agent's start)
  steps/terrain-xz.json             + the loft: the mountain hangs under the floor (the hook)
  steps/terrain-flip.json           sketches with flip: true
  steps/terrain-plane.json          sketches on a plane that says which way is up: x along X, y along Z
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from terrain import sections as S  # noqa: E402
from terrain.get_data import BBOX  # noqa: E402

ROWS, COLS, WIDTH_MM, BASE_MM, STRETCH = 50, 44, 100.0, 3.0, 1.5
LAB = os.path.join(HERE, '..')


def main():
    z = S.read_tiff(os.path.join(LAB, 'data', 'picture-grid.tif'))
    lat = math.radians((BBOX[1] + BBOX[3]) / 2)
    w_m = (BBOX[2] - BBOX[0]) * 111320 * math.cos(lat)           # metres east-west (spherical, "about")
    h_m = (BBOX[3] - BBOX[1]) * 110574                            # metres north-south
    mm_per_m = WIDTH_MM / w_m
    height_mm = WIDTH_MM * h_m / w_m
    grid = S.sample_grid(z, ROWS, COLS)
    sl = S.slices(grid, WIDTH_MM, height_mm, BASE_MM, STRETCH, mm_per_m)
    r, c = divmod(int(grid.argmax()), COLS)
    meta = {'rows': ROWS, 'cols': COLS, 'width_mm': WIDTH_MM, 'height_mm': round(height_mm, 4), 'base_mm': BASE_MM,
            'stretch': STRETCH, 'mm_per_m': mm_per_m, 'scale_1_to': round(1000 / mm_per_m),
            'spacing_mm': [round(WIDTH_MM / (COLS - 1), 4), round(height_mm / (ROWS - 1), 4)],
            'grid_min_m': float(z.min()), 'grid_max_m': float(z.max()),
            'slices_min_m': float(grid.min()), 'slices_max_m': float(grid.max()),
            'slices_max_at': {'row': r, 'col': c, 'x_mm': sl[r]['outline'][c][0], 'y_mm': sl[r]['y_mm'],
                              'z_mm': sl[r]['outline'][c][1]},
            'hand_volume_mm3': S.hand_volume(sl)}
    with open(os.path.join(LAB, 'data', 'slices.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'meta': meta, 'slices': sl}, f)
    os.makedirs(os.path.join(LAB, 'steps'), exist_ok=True)
    for name, obj in (('slices-xz', S.script(sl, 'xz', loft=False)), ('terrain-xz', S.script(sl, 'xz')),
                      ('terrain-flip', S.script(sl, 'flip')), ('terrain-plane', S.script(sl, 'plane'))):
        with open(os.path.join(LAB, 'steps', name + '.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(obj, f)
    print(json.dumps(meta, indent=1))


if __name__ == '__main__':
    main()
