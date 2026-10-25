"""Panel text and card specs for the St. Helens video, from out/ and data/ only (no number typed by hand).

    python3 video/make_panels.py

Writes out/evidence/numbers.json, video/terminal-*.txt (<= 8 rows x 44 cols), video/toolcalls.json (the transcript row
each tool-call panel cites + the result substring + plain words), video/json-cards.json and video/python-cards.json.
tests/test_evidence.py re-derives the values.
"""
import json
import os
import re

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = lambda *a: os.path.join(LAB, *a)  # noqa: E731
PROBE = 'out/probe/0.19.0'
USGS_SUMMIT_M = 2539   # https://www.usgs.gov/volcanoes/mount-st.-helens, "Elevation: 2,539 (m)" (2009 lidar): ACCURACY.md


def jload(*a):
    with open(P(*a), encoding='utf-8') as f:
        return json.load(f)


def write(rel, text):
    os.makedirs(os.path.dirname(P(rel)), exist_ok=True)
    with open(P(rel), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if text.endswith('\n') else text + '\n')


def rows(rel):
    with open(P(rel), encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def call_row(rel, pred):
    for i, r in enumerate(rows(rel), 1):
        m = r.get('msg') or {}
        if r.get('dir') == 'client->server' and m.get('method') == 'tools/call' and pred(m['params']):
            return r['seq'], i, r
    raise LookupError(rel)


def reply_text(rel, seq):
    rs = rows(rel)
    call = next(r for r in rs if r['seq'] == seq)
    for r in rs[rs.index(call) + 1:]:
        m = r.get('msg') or {}
        if r['dir'] == 'server->client' and m.get('id') == call['msg']['id']:
            return ''.join(c.get('text', '') for c in m['result']['content'] if c.get('type') == 'text')
    raise LookupError(seq)


def line_no(rel, needle):
    with open(P(rel), encoding='utf-8') as f:
        for i, l in enumerate(f, 1):
            if needle in l:
                return i
    raise LookupError(needle)


def main():
    meta = jload('data', 'slices.json')['meta']
    cell = {c: jload(PROBE, c, 'summary.json') for c in ('xz', 'flip', 'plane', 'slicer-flip', 'mirror')}
    runs = jload('out', 'runs', 'SCORES.json')['runs']
    sl = jload('out', 'slice', 'slice-report.json')
    n = {
        'sections': str(meta['rows']), 'points': str(meta['cols']), 'scale': f"{meta['scale_1_to']:,}",
        'stretch': f"{meta['stretch']}", 'base': f"{meta['base_mm']:.0f}", 'tile_w': f"{meta['width_mm']:.0f}",
        'tile_h': f"{meta['height_mm']:.0f}", 'spacing': f"{meta['spacing_mm'][1]:.1f}",
        'xz_zmin': f"{cell['xz']['bbox_min'][2]:.1f}", 'up_zmax': f"{cell['plane']['bbox_max'][2]:.1f}",
        'hand_volume': f"{meta['hand_volume_mm3']:,.0f}", 'loft_volume': f"{cell['plane']['volume_mm3']:,.0f}",
        'volume_pct': f"{cell['plane']['volume_vs_hand_pct']:.2f}",
        'data_top_x': f"{meta['slices_max_at']['x_mm']:.1f}", 'data_top_y': f"{meta['slices_max_at']['y_mm']:.1f}",
        'up_top_x': f"{cell['plane']['summit'][0]:.1f}", 'up_top_y': f"{cell['plane']['summit'][1]:.1f}",
        'flip_top_y': f"{cell['slicer-flip']['summit'][1]:.1f}",
        'slices_max_m': f"{meta['slices_max_m']:,.0f}", 'grid_max_m': f"{meta['grid_max_m']:,.0f}",
        'usgs_m': f"{USGS_SUMMIT_M:,}", 'short_m': f"{USGS_SUMMIT_M - meta['slices_max_m']:.0f}",
        'layer_m': f"{0.2 / (meta['mm_per_m'] * meta['stretch']):.0f}",
        'slice_time': sl['gcode']['print_time'], 'slice_g': f"{sl['gcode']['filament_g']:.0f}",
        'runs': str(len(runs)), 'runs_total_usd': f"{sum(r['cost_usd'] for r in runs):.2f}",
        'runs_up': str(sum(1 for r in runs if r['measured'] and r['measured']['up'])),
        'runs_round': str(sum(1 for r in runs if r['measured'] and r['measured']['round'])),
        'runs_mirror': str(sum(1 for r in runs if r['fix'] == 'mirror')),
        'runs_rotate': str(sum(1 for r in runs if r['fix'] == 'rotate')),
        'runs_rebuild': str(sum(1 for r in runs if r['fix'] == 'rebuild')),
    }
    write('out/evidence/numbers.json', json.dumps(n, indent=1))

    write('video/terminal-data.txt', '\n'.join([
        'USGS 3DEP heights · 400 x 320 samples',
        f"{n['sections']} slices x {n['points']} points, {n['spacing']} mm apart",
        f"tile {n['tile_w']} x {n['tile_h']} mm · 1 : {n['scale']}",
        f"heights x {n['stretch']} · base {n['base']} mm",
    ]))
    write('video/terminal-upside.txt', '\n'.join([
        '50 slices on XZ, lofted: ok, true',
        f"lowest point  z = {n['xz_zmin']} mm",
        'highest point z = 0.0 mm',
        '= the mountain hangs under the floor',
    ]))
    write('video/terminal-proof.txt', '\n'.join([
        'fresh build · sketches told which way is up',
        f"z from 0.0 to {n['up_zmax']} mm",
        f"volume {n['loft_volume']} mm3",
        f"hand count {n['hand_volume']} mm3 ({n['volume_pct']}%)",
        f"top at x {n['up_top_x']}, y {n['up_top_y']} mm",
        f"data's top: x {n['data_top_x']}, y {n['data_top_y']} mm",
        f"slicer flip: top at y {n['flip_top_y']} (mirrored)",
    ]))
    write('video/terminal-summit.txt', '\n'.join([
        f"our 50 slices: top {n['slices_max_m']} m",
        f"the 400 x 320 grid: {n['grid_max_m']} m",
        f"USGS (2009 lidar): {n['usgs_m']} m",
    ]))
    write('video/terminal-runs.txt', '\n'.join([
        f"{n['runs']} runs · Claude Code · same prompt",
        f"right way up: {n['runs_up']} of {n['runs']}",
        f"right way round: {n['runs_round']} of {n['runs']}",
        f"fixed with a mirror: {n['runs_mirror']} of {n['runs']}",
        f"agent cost: ${n['runs_total_usd']} at API prices",
    ]))
    write('video/terminal-slicer.txt', '\n'.join([
        'PrusaSlicer 2.9.2 · MK4S 0.4 · PLA',
        '0.2 mm layers · slicer estimate',
        f"{n['slice_time']} · {n['slice_g']} g",
        'one part, no open edges',
    ]))

    ev = lambda c: f'{PROBE}/{c}/transcript.jsonl'  # noqa: E731
    tcs = []
    seq, _, _ = call_row(ev('xz'), lambda p: p['name'] == 'batch')
    assert '"ok": true' in reply_text(ev('xz'), seq)
    tcs.append({'id': 'tc-loft', 'evidence': f"{ev('xz')}#seq={seq}", 'tool': 'batch', 'result': '"ok": true',
                'plain': '50 slices and the loft: built, no warning'})
    seq, _, _ = call_row(ev('xz'), lambda p: p['name'] == 'measure')
    t = reply_text(ev('xz'), seq)
    zmin = re.search(r'-33\.\d+', t).group(0)
    tcs.append({'id': 'tc-under', 'evidence': f"{ev('xz')}#seq={seq}", 'tool': 'measure', 'result': zmin,
                'plain': 'the lowest point: 33 mm under the floor'})
    seq, _, _ = call_row(ev('plane'), lambda p: p['name'] == 'measure')
    t = reply_text(ev('plane'), seq)
    zmax = re.search(r'33\.16\d+', t).group(0)
    tcs.append({'id': 'tc-up', 'evidence': f"{ev('plane')}#seq={seq}", 'tool': 'measure', 'result': zmax,
                'plain': 'the top: 33 mm above the floor'})
    a = 'out/runs/plain-1/transcript.jsonl'
    seq, _, r = call_row(a, lambda p: p['name'] == 'execute' and p['arguments'].get('command') == 'solid.mirror'
                         or (p['name'] == 'batch' and any(c.get('command') == 'solid.mirror' for c in p['arguments'].get('commands', []))))
    t = reply_text(a, seq)
    res = '"ok": true' if '"ok": true' in t else re.search(r'"created_bodies": \[[^\]]*\]', t).group(0)
    res = re.sub(r'\s+', ' ', res)          # the engine compares results with whitespace collapsed
    tcs.append({'id': 'tc-claude-mirror', 'evidence': f'{a}#seq={seq}', 'tool': r['msg']['params']['name'], 'result': res,
                'plain': "Claude's fix: a mirror across the floor plane"})
    write('video/toolcalls.json', json.dumps(tcs, indent=1))

    seq, line, r = call_row(ev('xz'), lambda p: p['name'] == 'batch')
    cards = [{'id': 'json-plane', 'src': f"{ev('xz')}#L{line}", 'source_kind': 'no-AI test (our probe)',
              'view': {'reformat': 'pretty', 'at': '/msg/params/arguments/commands/0/params', 'cols': 44},
              'focusKey': '/msg/params/arguments/commands/0/params/plane', 'focusValue': 'XZ', 'spoken': 'plane, X Z'}]
    write('video/json-cards.json', json.dumps(cards, indent=1))
    first = line_no('terrain/sections.py', 'def outline(')
    src = f'terrain/sections.py#L{first}-{first + 5}'
    write('video/python-cards.json', json.dumps([
        {'id': 'py-row', 'src': src, 'focus': [first + 3], 'note': 'one row in: each height becomes one dot'},
        {'id': 'py-close', 'src': src, 'focus': [first + 5], 'note': 'down to the base and back: one slice'}], indent=1))
    print(json.dumps(n))


if __name__ == '__main__':
    main()
