"""Render-ready stills, all drawn by SolidCraft 0.19.0's product renderer (`solidcraft-cli render`), no AI, no repainting.

    docker run --rm -v <lab>:/work -w /work solidcraft-terrain-lab:0.19.0 python3 video/make_frames.py [names...]

Each script that was rendered is kept next to its PNG (video/frames/*.script.json). The camera is set with view.apply
(target, yaw, pitch, distance) at the end of the script. "Floor" is a thin dark plate at z 0 that we add so the floor
line is visible (disclosed in the captions); everything else is the lofted tile.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, LAB)
from terrain import sections as S  # noqa: E402

OUT = os.path.join(HERE, 'frames')
META = json.load(open(os.path.join(LAB, 'data', 'slices.json'), encoding='utf-8'))['meta']
H = META['height_mm']


def steps(name):
    return json.load(open(os.path.join(LAB, 'steps', name + '.json'), encoding='utf-8'))['commands']


def floor():
    return [{'command': 'solid.box', 'params': {'length': 180, 'width': 150, 'height': 0.6, 'corner': [-40, 130, -0.6],
                                                'operation': 'new', 'body_name': 'Floor'}},
            {'command': 'appearance.assign', 'params': {'bodies': ['Floor'], 'color': '#334155'}}]


def view(target, yaw, pitch, distance):
    return [{'command': 'view.apply', 'params': {'camera': {'target': target, 'yaw': yaw, 'pitch': pitch, 'distance': distance}}}]


def render(name, commands, w=1920, h=1080):
    os.makedirs(OUT, exist_ok=True)
    script = os.path.join(OUT, name + '.script.json')
    with open(script, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'commands': commands}, f)
    png = os.path.join(OUT, name + '.png')
    p = subprocess.run(['solidcraft-cli', 'render', script, '--out', png, '--width', str(w), '--height', str(h),
                        '--overwrite', '--timeout', '600'], capture_output=True, text=True, timeout=900)
    print(name, p.returncode, (p.stderr or '')[-300:], flush=True)
    if p.returncode != 0:
        raise SystemExit(f'{name} failed')


def stretched(stretch):
    z = S.read_tiff(os.path.join(LAB, 'data', 'picture-grid.tif'))
    sl = S.slices(S.sample_grid(z, META['rows'], META['cols']), META['width_mm'], H, META['base_mm'], stretch, META['mm_per_m'])
    return S.script(sl, 'plane')['commands']


def plates(every=5):
    """Every 5th slice as a thin plate standing up: the slices with gaps, before the loft fills them."""
    cmds, sel = [], list(range(0, META['rows'], every))
    sk = steps('terrain-plane')
    for k in sel:
        cmds += sk[3 * k: 3 * k + 3]
        cmds.append({'command': 'solid.extrude', 'params': {'sketch': f'Slice{k + 1:02d}', 'distance': 0.8,
                                                            'direction': 'symmetric', 'operation': 'new',
                                                            'body_name': f'Plate{k + 1:02d}'}})
    return cmds


SIDE = view([50, 57, -4], 0.0, 0.0, 175)        # from the south, low, the floor seen almost edge-on
ISO = view([50, 57, 12], -0.7854, 0.62, 230)
TOP = view([50, 57, 0], 0.0, 1.5707, 210)
TILT = view([50, 50, 0], 0.0, 0.95, 190)        # from the south, looking down at the crater: north is up the picture
JOBS = {
    'side-under-floor': lambda: steps('terrain-xz') + floor() + SIDE,
    'side-upright': lambda: steps('terrain-plane') + floor() + SIDE,
    'iso-upright': lambda: steps('terrain-plane') + ISO,
    'iso-plates': lambda: plates() + ISO,
    'top-right': lambda: steps('terrain-plane') + TOP,
    'top-slicer-flip': lambda: steps('terrain-xz') + [
        {'command': 'solid.move', 'params': {'bodies': ['Mountain'], 'axis': [1, 0, 0], 'angle': 180}},
        {'command': 'solid.move', 'params': {'bodies': ['Mountain'], 'translate': [0, H, 0]}}] + TOP,
    'tilt-right': lambda: steps('terrain-plane') + TILT,
    'tilt-slicer-flip': lambda: steps('terrain-xz') + [
        {'command': 'solid.move', 'params': {'bodies': ['Mountain'], 'axis': [1, 0, 0], 'angle': 180}},
        {'command': 'solid.move', 'params': {'bodies': ['Mountain'], 'translate': [0, H, 0]}}] + TILT,
    'iso-1x': lambda: stretched(1.0) + ISO,
    'iso-2x': lambda: stretched(2.0) + ISO,
}

if __name__ == '__main__':
    for name, make in JOBS.items():
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        render(name, make())
