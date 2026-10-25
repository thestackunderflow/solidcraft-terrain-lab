"""The probe cells on SolidCraft 0.19.0, as recorded in out/probe/0.19.0/<cell>/summary.json (PLAN rev 2.1 §6.2):
- xz: the 50 slices drawn on XZ and lofted: ok, no warning, and the mountain hangs under the floor (z <= 0);
- flip / plane: right way up (z from 0), the highest point where the data's is (handedness), volume = the hand count;
- slicer-flip (the xz body turned 180 deg about X, what "flip it in the slicer" does): right way up but MIRRORED;
- mirror (the xz body mirrored across the floor plane XY): right way up and the right way round.
Tolerances written before the run: volume within 1% of the hand count (a smooth loft is not a ruled one); the highest
point within one slice spacing (2.35 mm) of the data's highest sample."""
import json
import os

import pytest

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(LAB, 'out', 'probe', '0.19.0')


def cell(name):
    with open(os.path.join(OUT, name, 'summary.json'), encoding='utf-8') as f:
        return json.load(f)


def meta():
    with open(os.path.join(LAB, 'data', 'slices.json'), encoding='utf-8') as f:
        return json.load(f)['meta']


def test_xz_loft_is_ok_and_hangs_under_the_floor():
    s = cell('xz')
    assert s['ok'] is True and s['loft_warning'] is None
    assert s['bbox_max'][2] <= 1e-6 and s['bbox_min'][2] == pytest.approx(-meta()['slices_max_at']['z_mm'], abs=0.05)


@pytest.mark.parametrize('c', ['flip', 'plane', 'mirror'])
def test_right_way_up_and_right_way_round(c):
    s, m = cell(c), meta()
    assert s['ok'] is True
    assert s['bbox_min'][2] == pytest.approx(0.0, abs=1e-3)
    top = m['slices_max_at']
    assert s['summit'][2] == pytest.approx(top['z_mm'], abs=0.05)
    assert abs(s['summit'][0] - top['x_mm']) <= 2.35 and abs(s['summit'][1] - top['y_mm']) <= 2.35
    assert s['volume_mm3'] == pytest.approx(m['hand_volume_mm3'], rel=0.01)
    assert s['stl']['watertight'] and s['stl']['bodies'] == 1


def test_slicer_flip_is_up_but_mirrored():
    s, m = cell('slicer-flip'), meta()
    assert s['bbox_min'][2] == pytest.approx(0.0, abs=1e-3)
    top = m['slices_max_at']
    assert abs(s['summit'][1] - (m['height_mm'] - top['y_mm'])) <= 2.35        # north and south swapped
    assert abs(s['summit'][1] - top['y_mm']) > 10
    assert s['volume_mm3'] == pytest.approx(cell('flip')['volume_mm3'], rel=1e-6)
