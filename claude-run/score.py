"""Score every agent run in out/runs/<arm>-<n>/: cost, turns, tool calls, failed calls, the fix Claude used for the
orientation (mirror / rotate / rebuild = re-drawn sketches / none), and the lab's checks of the exported terrain.stl
against data/slices.json: right way up (lowest point at z 0 and the top above it), the right way round (the highest
point within one slice spacing of the data's highest sample), volume vs the hand count. Writes out/runs/SCORES.json.

    python3 claude-run/score.py
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(LAB, 'tests'))
from stl_tools import bodies, read_stl, watertight  # noqa: E402

META = json.load(open(os.path.join(LAB, 'data', 'slices.json'), encoding='utf-8'))['meta']


def _rows(p):
    with open(p, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def _commands(name, args):
    if name == 'batch':
        return [c for c in args.get('commands', []) if isinstance(c, dict)]
    if name == 'execute':
        return [{'command': args.get('command'), 'params': args.get('params') or {}}]
    return [{'command': name, 'params': args}]


def classify(cmds):
    names = [c.get('command') for c in cmds]
    if 'solid.mirror' in names:
        return 'mirror'
    if any(c.get('command') == 'solid.move' and (c.get('params') or {}).get('angle') for c in cmds):
        return 'rotate'
    if any(c.get('command') == 'sketch.create' for c in cmds):
        return 'rebuild'
    return 'none'


def measure(d):
    p = os.path.join(d, 'terrain.stl')
    if not os.path.exists(p):
        return None
    t = read_stl(p)
    v = t.reshape(-1, 3)
    top = v[int(np.argmax(v[:, 2]))]
    lo = v.min(axis=0)
    # follow the tile, not the origin: the data's x, y are measured from the tile's south-west corner
    x, y = float(top[0] - lo[0]), float(top[1] - lo[1])
    want = META['slices_max_at']
    vol = float(abs(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum()) / 6.0)
    up = bool(abs(lo[2]) < 0.05 and v[:, 2].max() > 1)
    return {'up': up, 'round': bool(up and abs(x - want['x_mm']) <= 2.35 and abs(y - want['y_mm']) <= 2.35),
            'summit_xy_mm': [round(x, 3), round(y, 3)], 'summit_z_mm': round(float(top[2]), 3),
            'bbox_min': [round(float(a), 3) for a in lo], 'bbox_max': [round(float(a), 3) for a in v.max(axis=0)],
            'volume_mm3': round(vol, 1), 'volume_vs_hand_pct': round(100 * (vol / META['hand_volume_mm3'] - 1), 3),
            'watertight': watertight(t), 'pieces': bodies(t)}


def score_run(d):
    rows = _rows(os.path.join(d, 'transcript.jsonl'))
    calls, replies = {}, {}
    for r in rows:
        m = r.get('msg') or {}
        if r.get('dir') == 'client->server' and m.get('method') == 'tools/call':
            calls[m['id']] = m['params']
        elif r.get('dir') == 'server->client' and 'id' in m and 'result' in m:
            replies[m['id']] = m['result']
    cmds, failed, errors = [], 0, []
    for i, p in calls.items():
        cmds += _commands(p['name'], p.get('arguments') or {})
        res = replies.get(i) or {}
        t = '\n'.join(c.get('text', '') for c in res.get('content', []) if c.get('type') == 'text')
        try:
            body = json.loads(t)
        except (json.JSONDecodeError, TypeError):
            body = t
        if res.get('isError') or (isinstance(body, dict) and body.get('ok') is False):
            failed += 1
            errors.append((body.get('failed') or {}).get('error') if isinstance(body, dict) else str(body)[:200])
    try:
        out = json.load(open(os.path.join(d, 'claude-output.json'), encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        out = {}
    return {'run': os.path.basename(d.rstrip('/\\')), 'cost_usd': out.get('total_cost_usd'), 'turns': out.get('num_turns'),
            'tool_calls': len(calls), 'failed_calls': failed, 'failed_errors': errors, 'fix': classify(cmds),
            'final_answer': (out.get('result') or '')[:1500], 'measured': measure(d)}


def main():
    root = os.path.join(LAB, 'out', 'runs')
    runs = [score_run(d) for d in sorted(glob.glob(os.path.join(root, '*-*'))) if os.path.isdir(d)]
    with open(os.path.join(root, 'SCORES.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'runs': runs}, f, indent=1)
    for r in runs:
        print(json.dumps({k: r[k] for k in ('run', 'cost_usd', 'fix', 'failed_calls', 'measured')}))


if __name__ == '__main__':
    main()
