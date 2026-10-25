"""From a grid of heights (USGS 3DEP) to SolidCraft slices: one closed outline per grid row.

North row first, at the top of the tile (largest y); x runs east; heights are stretched by `stretch` and stand on a
`base_mm` floor. hand_volume() is the proof's hand count: each outline's area (shoelace), trapezoids along y.
"""
import struct

import numpy as np


def read_tiff(path):
    """An uncompressed float32 GeoTIFF (what the 3DEP exportImage returns) as a rows x cols array."""
    b = open(path, 'rb').read()
    end = '<' if b[:2] == b'II' else '>'
    ifd = struct.unpack(end + 'I', b[4:8])[0]
    n = struct.unpack(end + 'H', b[ifd:ifd + 2])[0]
    tags = {}
    for i in range(n):
        e = b[ifd + 2 + 12 * i: ifd + 14 + 12 * i]
        tag, typ, cnt = struct.unpack(end + 'HHI', e[:8])
        size = {3: 2, 4: 4}.get(typ, 4)
        if cnt * size <= 4:
            vals = struct.unpack(end + ('H' if typ == 3 else 'I') * cnt, e[8:8 + cnt * size])
        else:
            off = struct.unpack(end + 'I', e[8:12])[0]
            vals = struct.unpack(end + ('H' if typ == 3 else 'I') * cnt, b[off:off + cnt * size])
        tags[tag] = vals
    w, h = tags[256][0], tags[257][0]
    assert tags[259][0] == 1 and tags[258][0] == 32 and tags.get(339, (3,))[0] == 3, 'uncompressed float32 only'
    if 273 in tags:                                   # strips
        data = b''.join(b[o:o + c] for o, c in zip(tags[273], tags[279]))
        return np.frombuffer(data, dtype=end + 'f4', count=w * h).reshape(h, w).astype(float)
    tw, th = tags[322][0], tags[323][0]               # tiles, row by row, each padded to tw x th
    ntx = -(-w // tw)
    out = np.zeros((-(-h // th) * th, ntx * tw))
    for i, (o, c) in enumerate(zip(tags[324], tags[325])):
        ty, tx = divmod(i, ntx)
        out[ty * th:(ty + 1) * th, tx * tw:(tx + 1) * tw] = np.frombuffer(b[o:o + c], dtype=end + 'f4').reshape(th, tw)
    return out[:h, :w]


def pixel_scale(path):
    """GeoTIFF ModelPixelScale (tag 33550): degrees per pixel in x, y. The server forces square pixels, so a grid
    whose shape does not match the box's shape comes back covering a bigger box (found 22 Oct 2026)."""
    b = open(path, 'rb').read()
    ifd = struct.unpack('<I', b[4:8])[0]
    for i in range(struct.unpack('<H', b[ifd:ifd + 2])[0]):
        e = b[ifd + 2 + 12 * i: ifd + 14 + 12 * i]
        tag, typ, cnt = struct.unpack('<HHI', e[:8])
        if tag == 33550:
            off = struct.unpack('<I', e[8:12])[0]
            return struct.unpack('<' + 'd' * cnt, b[off:off + 8 * cnt])
    raise KeyError('no ModelPixelScale')


def sample_grid(z, rows, cols):
    """Bilinear samples on an even rows x cols grid from corner to corner of z (row 0 = north)."""
    z = np.asarray(z, dtype=float)
    r = np.linspace(0, z.shape[0] - 1, rows)
    c = np.linspace(0, z.shape[1] - 1, cols)
    r0, c0 = np.minimum(r.astype(int), z.shape[0] - 2), np.minimum(c.astype(int), z.shape[1] - 2)
    fr, fc = (r - r0)[:, None], (c - c0)[None, :]
    a, b = z[r0][:, c0], z[r0][:, c0 + 1]
    d, e = z[r0 + 1][:, c0], z[r0 + 1][:, c0 + 1]
    return (1 - fr) * ((1 - fc) * a + fc * b) + fr * ((1 - fc) * d + fc * e)


def outline(heights, step):
    # one row of heights -> one slice
    dots = [[i * step, z]
            for i, z in enumerate(heights)]
    # down to the base, back along the bottom
    return dots + [[dots[-1][0], 0], [0, 0]]


def slice_of(row, y_mm, width_mm, base_mm, lowest, mm_up):
    """outline() in millimetres, rounded to 4 decimals (floats, so the command files keep '0.0')."""
    heights = [base_mm + (h - lowest) * mm_up for h in row]
    pts = outline(heights, width_mm / (len(row) - 1))
    pts[-2][0] = width_mm                                  # the last x exactly, not n * step
    return {'y_mm': round(y_mm, 4), 'outline': [[round(float(x), 4), round(float(z), 4)] for x, z in pts]}


def slices(z, width_mm, height_mm, base_mm, stretch, mm_per_m):
    """Every row of the grid, north (row 0) at y = height_mm, south at y = 0."""
    z = np.asarray(z, dtype=float)
    lowest, rows = float(z.min()), len(z)
    mm_up = mm_per_m * stretch
    return [slice_of(z[r], height_mm * (1 - r / (rows - 1)), width_mm, base_mm, lowest, mm_up) for r in range(rows)]


def area(outline):
    p = np.asarray(outline, dtype=float)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def hand_volume(sl):
    s = sorted(sl, key=lambda d: d['y_mm'])
    return sum((s[i + 1]['y_mm'] - s[i]['y_mm']) * (area(s[i]['outline']) + area(s[i + 1]['outline'])) / 2
               for i in range(len(s) - 1))


def plane(mode, y):
    if mode == 'xz':
        return {'plane': 'XZ', 'offset': y}
    if mode == 'flip':
        return {'plane': 'XZ', 'offset': y, 'flip': True}
    return {'plane': {'origin': [0, y, 0], 'x_dir': [1, 0, 0], 'y_dir': [0, 0, 1]}}


def script(sl, mode, loft=True):
    """The SolidCraft command file (docs/scripts.md): one sketch per slice, then (optionally) the loft."""
    cmds = []
    for k, s in enumerate(sl):
        cmds += [{'command': 'sketch.create', 'params': {**plane(mode, s['y_mm']), 'name': f'Slice{k + 1:02d}'}},
                 {'command': 'sketch.line', 'params': {'points': s['outline'], 'closed': True}},
                 {'command': 'sketch.finish', 'params': {}}]
    if loft:
        cmds.append({'command': 'solid.loft', 'params': {'sections': [{'sketch': f'Slice{k + 1:02d}'} for k in range(len(sl))],
                                                          'body_name': 'Mountain'}})
    return {'commands': cmds}
