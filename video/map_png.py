"""The data picture for the on-ramp: the USGS 3DEP grid (data/picture-grid.tif) as a shaded relief, north up, with
the slice lines drawn where make_slices.py cuts its 50 slices (every 5th one darker). Our drawing of the data, not a map.

    python3 video/map_png.py        -> video/frames/data-relief.png, data-slices.png, data-relief-mirrored.png
"""
import os
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
LINE, LINE5 = (59, 130, 246), (30, 64, 175)


def relief(z, scale=3):
    z = np.asarray(z, dtype=float)
    gy, gx = np.gradient(z)
    n = np.dstack([-gx, gy, np.full_like(z, 30.0)])          # rows run north to south, so +y is -row
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    light = np.array([-1.0, 1.0, 1.5]) / np.linalg.norm([-1.0, 1.0, 1.5])  # from the north-west
    shade = np.clip(n @ light, 0, 1)
    h = (z - z.min()) / (np.ptp(z) or 1)
    base = 200 + 40 * h                                     # light, higher is lighter
    g = np.clip(base * (0.55 + 0.45 * shade), 0, 255).astype(np.uint8)
    img = np.dstack([g, g, np.clip(g.astype(int) + 8, 0, 255).astype(np.uint8)])
    return np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)


def with_slices(img, rows=50, every=5):
    out = img.copy()
    h = out.shape[0]
    for k in range(rows):
        y = int(round(k * (h - 1) / (rows - 1)))
        out[y, :] = LINE5 if k % every == 0 else LINE
    return out


def write_png(path, rgb):
    h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[i].tobytes() for i in range(h))

    def chunk(t, b):
        return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    from terrain.sections import read_tiff
    z = read_tiff(os.path.join(HERE, '..', 'data', 'picture-grid.tif'))
    img = relief(z, 3)
    write_png(os.path.join(HERE, 'frames', 'data-relief.png'), img)
    write_png(os.path.join(HERE, 'frames', 'data-slices.png'), with_slices(img, 50, 5))
    # the turned-over tile's heights: the same grid mirrored north-south (the lab measures it: top at y 70.1, not 44.7)
    write_png(os.path.join(HERE, 'frames', 'data-relief-mirrored.png'), np.ascontiguousarray(img[::-1]))
    print('wrote data-relief.png, data-slices.png', img.shape)
