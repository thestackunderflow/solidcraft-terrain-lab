"""video/map_png.py: the data picture (the USGS grid as a shaded relief, north up) with the slice lines drawn where the
50 slices are cut. Proven on a synthetic grid: size, slice-line colour on the right rows, background elsewhere."""
import os
import sys
import tempfile

import numpy as np

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(LAB, 'video'))
import map_png  # noqa: E402


def test_slice_lines_are_drawn_on_their_rows():
    z = np.fromfunction(lambda r, c: 1000 + r + c, (32, 40))
    img = map_png.relief(z, scale=3)
    out = map_png.with_slices(img, rows=5, every=5)
    assert out.shape == (96, 120, 3)
    ys = [int(round(k * (96 - 1) / 4)) for k in range(5)]
    assert tuple(out[ys[0], 60]) == map_png.LINE5                 # every 5th line darker (here: the first)
    for y in ys[1:]:
        assert tuple(out[y, 60]) == map_png.LINE
    assert tuple(out[10, 60]) != map_png.LINE
    p = os.path.join(tempfile.mkdtemp(), 'm.png')
    map_png.write_png(p, out)
    assert open(p, 'rb').read()[:8] == b'\x89PNG\r\n\x1a\n'
