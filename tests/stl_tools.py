"""STL checks with numpy only (no trimesh): read/write, watertight, body count, and the two measurements the lid video
uses: the material intervals along a line through a horizontal section (side gap, rim wall) and the gaps along a
vertical line (top gap). Proven on synthetic meshes in tests/test_stl_tools.py."""
import struct

import numpy as np

WELD = 1e-6


def read_stl(path):
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) >= 84:
        n = struct.unpack('<I', data[80:84])[0]
        if 84 + 50 * n == len(data):
            rec = np.frombuffer(data, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]),
                                count=n, offset=84)
            return rec['v'].astype(float)
    tris, cur = [], []
    for line in data.decode('ascii', 'replace').splitlines():
        w = line.split()
        if w and w[0] == 'vertex':
            cur.append([float(x) for x in w[1:4]])
            if len(cur) == 3:
                tris.append(cur)
                cur = []
    return np.array(tris, dtype=float).reshape(-1, 3, 3)


def write_stl(path, tris, binary=True):
    tris = np.asarray(tris, dtype=float).reshape(-1, 3, 3)
    if binary:
        with open(path, 'wb') as f:
            f.write(b'\0' * 80 + struct.pack('<I', len(tris)))
            for t in tris:
                nrm = np.cross(t[1] - t[0], t[2] - t[0])
                f.write(struct.pack('<12fH', *nrm, *t.reshape(-1), 0))
    else:
        with open(path, 'w', encoding='ascii') as f:
            f.write('solid m\n')
            for t in tris:
                f.write(' facet normal 0 0 0\n  outer loop\n')
                for v in t:
                    f.write(f'   vertex {v[0]!r} {v[1]!r} {v[2]!r}\n')
                f.write('  endloop\n endfacet\n')
            f.write('endsolid m\n')


def box_tris(lo, hi):
    """12 outward-facing triangles of an axis-aligned box."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], dtype=float)
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return np.array([[v[a], v[b], v[c]] for a, b, c in f])


def _weld(tris):
    pts = np.round(np.asarray(tris).reshape(-1, 3) / WELD).astype(np.int64)
    _, idx = np.unique(pts, axis=0, return_inverse=True)
    return idx.reshape(-1, 3)


def watertight(tris):
    if len(tris) == 0:
        return False
    f = _weld(tris)
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return bool(np.all(counts == 2))


def bodies(tris):
    """Connected pieces: triangles that share a (welded) vertex belong to one piece."""
    if len(tris) == 0:
        return 0
    f = _weld(tris)
    parent = list(range(int(f.max()) + 1))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, c in f:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    return len({find(int(v)) for v in np.unique(f)})


def _section_segments(tris, z):
    segs = []
    for t in np.asarray(tris):
        d = t[:, 2] - z
        pts = []
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            da, db = d[i], d[(i + 1) % 3]
            if (da > 0) != (db > 0):
                s = da / (da - db)
                pts.append(a + s * (b - a))
        if len(pts) == 2:
            segs.append((pts[0][:2], pts[1][:2]))
    return segs


def _pair(vals):
    u = []
    for v in sorted(vals):
        if not u or abs(v - u[-1]) > 1e-7:
            u.append(v)
    return [(u[i], u[i + 1]) for i in range(0, len(u) - 1, 2)]


def x_intervals(tris, z, y=0.0):
    """Material along the line y = const in the horizontal section at height z: [(x_in, x_out), ...]."""
    xs = []
    for p, q in _section_segments(tris, z):
        if (p[1] > y) != (q[1] > y):
            s = (y - p[1]) / (q[1] - p[1])
            xs.append(float(p[0] + s * (q[0] - p[0])))
    return _pair(xs)


def z_gaps(tris, x, y=0.0):
    """Empty stretches between material along the vertical line (x, y): [(z_top_of_lower, z_bottom_of_upper), ...]."""
    zs = []
    for t in np.asarray(tris):
        a, b, c = t
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den
        l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -1e-9:
            zs.append(float(l1 * a[2] + l2 * b[2] + l3 * c[2]))
    solid = _pair(zs)
    return [(solid[i][1], solid[i + 1][0]) for i in range(len(solid) - 1)]
