"""Read one layer of a PrusaSlicer text G-code: the extruding moves (E increases), how many lines cross a short line
across a thin wall, and an SVG of that window (the "slicer preview" evidence, made from the G-code itself).

    python3 slicer/gcode_layer.py <file.gcode> <z> <y> <x_min> <x_max> <out.svg> <out.json>
"""
import json
import re
import sys


def layer_segments(text, z, tol=1e-3):
    segs, cur_z, x, y, e, layer = [], None, None, None, 0.0, None
    for raw in text.splitlines():
        line = raw.split(';', 1)[0].strip()
        if raw.startswith(';Z:'):
            layer = float(raw[3:])
            continue
        if not line:
            continue
        w = line.split()
        if w[0] == 'G92':
            for t in w[1:]:
                if t[0] == 'E':
                    e = float(t[1:])
            continue
        if w[0] not in ('G0', 'G1'):
            continue
        v = {t[0]: float(t[1:]) for t in w[1:] if t[0] in 'XYZE' and re.match(r'^[XYZE]-?[\d.]+$', t)}
        nx, ny = v.get('X', x), v.get('Y', y)
        ne = v.get('E', e)
        if 'Z' in v:
            cur_z = v['Z']
        here = layer if layer is not None else cur_z
        if here is not None and abs(here - z) < tol and x is not None and nx is not None and ne > e + 1e-9 \
                and (nx, ny) != (x, y):
            segs.append(((x, y), (nx, ny)))
        x, y, e = nx, ny, ne
    return segs


def lines_across(segs, y, x_min, x_max, merge=0.05):
    xs = []
    for (x0, y0), (x1, y1) in segs:
        if (y0 > y) != (y1 > y):
            xc = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x_min <= xc <= x_max:
                xs.append(round(xc, 4))
    out = []
    for v in sorted(xs):
        if not out or v - out[-1] > merge:
            out.append(v)
    return out


def layer_svg(segs, box, width_mm=0.45, marks=(), y=None, px_per_mm=60):
    x0, y0, x1, y1 = box
    W, H = (x1 - x0) * px_per_mm, (y1 - y0) * px_per_mm
    sx = lambda v: (v - x0) * px_per_mm  # noqa: E731
    sy = lambda v: (y1 - v) * px_per_mm  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']
    for (a, b), (c, d) in segs:
        if max(a, c) < x0 or min(a, c) > x1 or max(b, d) < y0 or min(b, d) > y1:
            continue
        out.append(f'<line x1="{sx(a):.1f}" y1="{sy(b):.1f}" x2="{sx(c):.1f}" y2="{sy(d):.1f}" stroke="#e07a1f" '
                   f'stroke-width="{width_mm * px_per_mm:.1f}" stroke-linecap="round" opacity="0.85"/>')
    if y is not None:
        out.append(f'<line x1="0" y1="{sy(y):.1f}" x2="{W:.0f}" y2="{sy(y):.1f}" stroke="#1f2937" stroke-width="2" '
                   f'stroke-dasharray="8 6"/>')
    for m in marks:
        out.append(f'<circle cx="{sx(m):.1f}" cy="{sy(y):.1f}" r="6" fill="#1f2937"/>')
    out.append('</svg>')
    return '\n'.join(out)


if __name__ == '__main__':
    path, z, y, xa, xb, svg_out, json_out = sys.argv[1:8]
    z, y, xa, xb = float(z), float(y), float(xa), float(xb)
    text = open(path, encoding='utf-8', errors='replace').read()
    segs = layer_segments(text, z)
    xs = lines_across(segs, y, xa, xb)
    with open(svg_out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(layer_svg(segs, (xa - 2, y - 2, xb + 2, y + 2), marks=xs, y=y))
    with open(json_out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'gcode': path.replace('\\', '/').split('/')[-1], 'z': z, 'y': y, 'band_x': [xa, xb],
                   'segments_in_layer': len(segs), 'lines_across': xs, 'count': len(xs)}, f, indent=1)
    print(json.dumps({'z': z, 'lines_across': xs, 'count': len(xs)}))
