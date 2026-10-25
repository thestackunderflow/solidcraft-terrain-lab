"""terrain/sections.py: the data-to-slices step (PLAN rev 2.1 §6.2), proven on synthetic grids first.
- read_tiff reads an uncompressed float32 GeoTIFF (USGS 3DEP exportImage) exactly;
- slices(): one closed outline per grid row, north row first (largest y), x across, heights stretched;
- hand_volume(): the area of each outline (shoelace) integrated along y with the trapezoid rule (the proof's hand count);
- script(): the SolidCraft command file, sketches on XZ (as written: the trap), flip, or an explicit plane."""
import os
import struct
import sys
import tempfile

import numpy as np
import pytest

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, LAB)
from terrain import sections as S  # noqa: E402


def write_tiff(path, a):
    """A minimal uncompressed float32 single-strip TIFF (little-endian), for the reader's test only."""
    a = np.asarray(a, dtype='<f4')
    h, w = a.shape
    data = a.tobytes()
    tags = [(256, 3, 1, w), (257, 3, 1, h), (258, 3, 1, 32), (259, 3, 1, 1), (262, 3, 1, 1),
            (273, 4, 1, 0), (277, 3, 1, 1), (278, 3, 1, h), (279, 4, 1, len(data)), (339, 3, 1, 3)]
    ifd_off = 8
    ifd = 2 + 12 * len(tags) + 4
    data_off = ifd_off + ifd
    out = bytearray(b'II*\x00' + struct.pack('<I', ifd_off) + struct.pack('<H', len(tags)))
    for tag, typ, cnt, val in tags:
        if tag == 273:
            val = data_off
        out += struct.pack('<HHI', tag, typ, cnt) + (struct.pack('<HH', val, 0) if typ == 3 else struct.pack('<I', val))
    out += struct.pack('<I', 0) + data
    with open(path, 'wb') as f:
        f.write(bytes(out))


def test_read_tiff_exact():
    a = np.array([[1.5, 2.25, 3.0], [955.0, 2525.625, -1.0]], dtype='<f4')
    p = os.path.join(tempfile.mkdtemp(), 'a.tif')
    write_tiff(p, a)
    assert np.array_equal(S.read_tiff(p), a)


def write_tiled_tiff(path, a, tile=4):
    """The same, but tiled (what exportImage actually returns: 128 x 128 tiles, padded)."""
    a = np.asarray(a, dtype='<f4')
    h, w = a.shape
    nty, ntx = -(-h // tile), -(-w // tile)
    pad = np.zeros((nty * tile, ntx * tile), dtype='<f4')
    pad[:h, :w] = a
    blobs = [pad[ty * tile:(ty + 1) * tile, tx * tile:(tx + 1) * tile].tobytes() for ty in range(nty) for tx in range(ntx)]
    n = len(blobs)
    tags = [(256, 3, 1, w), (257, 3, 1, h), (258, 3, 1, 32), (259, 3, 1, 1), (262, 3, 1, 1), (277, 3, 1, 1),
            (322, 3, 1, tile), (323, 3, 1, tile), (324, 4, n, None), (325, 4, n, None), (339, 3, 1, 3)]
    ifd = 2 + 12 * len(tags) + 4
    offs_at = 8 + ifd
    counts_at = offs_at + 4 * n
    data_at = counts_at + 4 * n
    offsets = [data_at + sum(len(x) for x in blobs[:i]) for i in range(n)]
    out = bytearray(b'II*\x00' + struct.pack('<I', 8) + struct.pack('<H', len(tags)))
    for tag, typ, cnt, val in tags:
        if tag in (324, 325):
            arr = offsets if tag == 324 else [len(x) for x in blobs]
            out += struct.pack('<HHI', tag, typ, cnt) + (struct.pack('<I', arr[0]) if n == 1 else
                                                         struct.pack('<I', offs_at if tag == 324 else counts_at))
        else:
            out += struct.pack('<HHI', tag, typ, cnt) + (struct.pack('<HH', val, 0) if typ == 3 else struct.pack('<I', val))
    out += struct.pack('<I', 0)
    if n > 1:
        out += struct.pack('<' + 'I' * n, *offsets) + struct.pack('<' + 'I' * n, *[len(x) for x in blobs])
    else:
        out += b'\0' * 8
    out += b''.join(blobs)
    with open(path, 'wb') as f:
        f.write(bytes(out))


@pytest.mark.parametrize('shape,tile', [((5, 7), 4), ((3, 3), 128)])
def test_read_tiled_tiff_exact(shape, tile):
    a = np.arange(shape[0] * shape[1], dtype='<f4').reshape(shape) * 1.5 + 900
    p = os.path.join(tempfile.mkdtemp(), 't.tif')
    write_tiled_tiff(p, a, tile)
    assert np.array_equal(S.read_tiff(p), a)


def test_sample_grid_is_exact_on_a_plane_and_keeps_the_corners():
    # z = 2 * col + 3 * row on a 320 x 400 grid: bilinear sampling reproduces a plane exactly
    rr, cc = np.mgrid[0:320, 0:400]
    z = 2.0 * cc + 3.0 * rr
    s = S.sample_grid(z, rows=50, cols=44)
    assert s.shape == (50, 44)
    assert s[0, 0] == pytest.approx(0.0) and s[-1, -1] == pytest.approx(2 * 399 + 3 * 319)
    r = 17 * 319 / 49
    c = 30 * 399 / 43
    assert s[17, 30] == pytest.approx(2 * c + 3 * r)


def test_pixel_scale_reads_the_geotiff_extent():
    assert S.pixel_scale(os.path.join(LAB, 'data', 'picture-grid.tif'))[:2] == pytest.approx((0.00025, 0.00025))


def test_slices_flat_grid_is_a_box():
    z = np.full((5, 4), 1000.0)
    sl = S.slices(z, width_mm=60, height_mm=40, base_mm=3, stretch=1.5, mm_per_m=0.01)
    assert len(sl) == 5
    assert sl[0]['y_mm'] == 40 and sl[-1]['y_mm'] == 0          # north row first, at the top of the tile
    assert sl[0]['outline'][0] == [0.0, 3.0] and sl[0]['outline'][3] == [60.0, 3.0]
    assert sl[0]['outline'][-2:] == [[60.0, 0.0], [0.0, 0.0]]   # down to the base, back along the bottom
    assert S.hand_volume(sl) == pytest.approx(60 * 40 * 3)


def test_slices_stretch_and_scale():
    z = np.array([[1000.0, 1100.0], [1000.0, 1100.0]])
    sl = S.slices(z, width_mm=10, height_mm=10, base_mm=2, stretch=2.0, mm_per_m=0.01)
    # lowest sample sits on the base; 100 m higher -> 100 * 0.01 * 2 = 2 mm above it
    assert sl[0]['outline'][:2] == [[0.0, 2.0], [10.0, 4.0]]
    # each outline: a trapezoid of area 10 * (2 + 4) / 2 = 30 mm2; 10 mm deep -> 300 mm3
    assert S.hand_volume(sl) == pytest.approx(300.0)


@pytest.mark.parametrize('mode', ['xz', 'flip', 'plane'])
def test_script_modes(mode):
    sl = S.slices(np.full((3, 3), 1.0), width_mm=10, height_mm=10, base_mm=1, stretch=1, mm_per_m=1)
    cmds = S.script(sl, mode)['commands']
    creates = [c['params'] for c in cmds if c['command'] == 'sketch.create']
    assert len(creates) == 3
    if mode == 'xz':
        assert all(p['plane'] == 'XZ' and 'flip' not in p for p in creates)
    elif mode == 'flip':
        assert all(p['plane'] == 'XZ' and p['flip'] is True for p in creates)
    else:
        assert all(p['plane'] == {'origin': [0, p['plane']['origin'][1], 0], 'x_dir': [1, 0, 0], 'y_dir': [0, 0, 1]}
                   for p in creates)
    loft = [c for c in cmds if c['command'] == 'solid.loft']
    assert len(loft) == 1 and len(loft[0]['params']['sections']) == 3
    assert [c['command'] for c in cmds].count('sketch.line') == 3


def test_script_without_loft_for_the_agent():
    sl = S.slices(np.full((3, 3), 1.0), width_mm=10, height_mm=10, base_mm=1, stretch=1, mm_per_m=1)
    assert 'solid.loft' not in [c['command'] for c in S.script(sl, 'xz', loft=False)['commands']]
