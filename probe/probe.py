"""THE PROBE (no AI, $0): Mount St. Helens' 50 slices lofted on SolidCraft over MCP, behind the logging proxy.

    docker run --rm -v <lab>:/work -v <lab>/out/probe/<ver>:/lab/out -w /work solidcraft-terrain-lab:<ver> \
        python3 probe/probe.py <ver>

Cells (each a fresh new_design; one batch of the command file from terrain/make_slices.py, then fixes):
  xz           steps/terrain-xz.json as is (sketches on XZ): the hook
  flip         steps/terrain-flip.json (sketch.create flip: true)
  plane        steps/terrain-plane.json (a plane that says which way is up)
  slicer-flip  xz + the body turned 180 deg about X and moved back over the tile (what a slicer's flip does)
  mirror       xz + the body mirrored across the floor plane (XY), the original removed
After each: measure, export STL, and the lab's own checks (tests/stl_tools.py): watertight, pieces, the highest point.
Every request and reply: <cell>/transcript.jsonl (proxy format: the video's tool-call panels cite these rows).
"""
import datetime
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tests'))
from mcp_client import Hang, McpClient, SERVER_CMD  # noqa: E402
from stl_tools import bodies, read_stl, watertight  # noqa: E402

VER = sys.argv[1] if len(sys.argv) > 1 else '0.19.0'
OUT = '/lab/out'
LAB = os.path.join(HERE, '..')
PROXY = os.path.join(LAB, 'proxy', 'mcp_log_proxy.py')


def load(name):
    with open(os.path.join(LAB, 'steps', name + '.json'), encoding='utf-8') as f:
        return json.load(f)['commands']


META = json.load(open(os.path.join(LAB, 'data', 'slices.json'), encoding='utf-8'))['meta']


class Session:
    def __init__(self):
        self.c = None

    def start(self, transcript):
        self.stop()
        self.c = McpClient(['python3', PROXY, '--log', transcript, '--watchdog', '180', '--'] + SERVER_CMD, timeout_s=240)
        self.c.start()

    def stop(self):
        if self.c is not None:
            self.c.close()
        self.c = None

    def call(self, name, args):
        r = self.c.call_tool(name, args)
        t = '\n'.join(b['text'] for b in r.get('content', []) if b.get('type') == 'text')
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            return t


S = Session()


def save(d, name, obj):
    with open(os.path.join(d, name), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write('\n')


def run_cell(name, base, extra=()):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    res = {'cell': name, 'version': VER, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    try:
        S.start(os.path.join(d, 'transcript.jsonl'))
        S.call('new_design', {'name': name})
        r = S.call('batch', {'commands': load(base)})
        res['ok'] = r.get('ok') if isinstance(r, dict) else False
        res['failed'] = r.get('failed') if isinstance(r, dict) else str(r)[:400]
        last = (r.get('results') or [{}])[-1] if isinstance(r, dict) else {}
        res['loft_warning'] = last.get('warning')
        res['loft_ms'] = last.get('ms')
        for e in extra:
            if e.get('then_remove_original'):
                rr = S.call('execute', {'command': e['command'], 'params': e['params']})
                res.setdefault('extra', []).append(rr)
                S.call('execute', {'command': 'solid.remove', 'params': {'bodies': ['Mountain']}})
            else:
                res.setdefault('extra', []).append(S.call('execute', {'command': e['command'], 'params': e['params']}))
        m = S.call('measure', {})
        save(d, 'measure.json', m)
        b = m['bodies']
        res['bodies'] = [x['name'] for x in b]
        res['volume_mm3'] = round(sum(x['volume_mm3'] for x in b), 3)
        res['bbox_min'] = [round(min(x['bbox']['min'][i] for x in b), 4) for i in range(3)]
        res['bbox_max'] = [round(max(x['bbox']['max'][i] for x in b), 4) for i in range(3)]
        p = f'{OUT}/{name}/terrain.stl'
        S.call('export', {'path': p})
        t = read_stl(p)
        v = t.reshape(-1, 3)
        top = v[int(np.argmax(v[:, 2]))]
        res['summit'] = [round(float(x), 4) for x in top]
        res['stl'] = {'watertight': watertight(t), 'bodies': bodies(t), 'triangles': int(len(t))}
        res['hand_volume_mm3'] = round(META['hand_volume_mm3'], 3)
        res['volume_vs_hand_pct'] = round(100 * (res['volume_mm3'] / META['hand_volume_mm3'] - 1), 4)
    except Hang as e:
        res['HANG'] = str(e)
    finally:
        S.stop()
    save(d, 'summary.json', res)
    print(json.dumps({k: res.get(k) for k in ('cell', 'ok', 'loft_warning', 'bbox_min', 'bbox_max', 'summit',
                                              'volume_mm3', 'volume_vs_hand_pct', 'stl', 'failed')}, default=str), flush=True)
    return res


def main():
    H = META['height_mm']
    run_cell('xz', 'terrain-xz')
    run_cell('flip', 'terrain-flip')
    run_cell('plane', 'terrain-plane')
    run_cell('slicer-flip', 'terrain-xz', [
        {'command': 'solid.move', 'params': {'bodies': ['Mountain'], 'axis': [1, 0, 0], 'angle': 180}},
        {'command': 'solid.move', 'params': {'bodies': ['Mountain'], 'translate': [0, H, 0]}}])
    run_cell('mirror', 'terrain-xz', [
        {'command': 'solid.mirror', 'params': {'bodies': ['Mountain'], 'plane': 'XY'}, 'then_remove_original': True}])


if __name__ == '__main__':
    main()
