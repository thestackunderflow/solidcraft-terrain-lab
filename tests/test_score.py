"""claude-run/score.py on synthetic run folders: which fix Claude used (a mirror, a rotation, re-drawn sketches, or
none), and the lab's own checks of the exported STL against the data: right way up, the right way round (the highest
point where the data's is), volume vs the hand count."""
import json
import os
import shutil
import sys
import tempfile

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(LAB, 'claude-run'))
import score  # noqa: E402

PROBE = os.path.join(LAB, 'out', 'probe', '0.19.0')


def row(d, msg):
    return json.dumps({'t': 'x', 'seq': 1, 'dir': d, 'msg': msg})


def call(i, name, args):
    return row('client->server', {'jsonrpc': '2.0', 'id': i, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}})


def reply(i, body, err=False):
    return row('server->client', {'jsonrpc': '2.0', 'id': i, 'result': {'isError': err, 'content': [{'type': 'text', 'text': json.dumps(body)}]}})


def make_run(cmds, stl_from=None, final='Done.'):
    d = tempfile.mkdtemp()
    rows = []
    for i, (name, args) in enumerate(cmds, 1):
        rows += [call(i, name, args), reply(i, {'ok': True})]
    with open(os.path.join(d, 'transcript.jsonl'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(rows) + '\n')
    with open(os.path.join(d, 'claude-output.json'), 'w', encoding='utf-8') as f:
        json.dump({'total_cost_usd': 0.5, 'num_turns': 12, 'result': final}, f)
    if stl_from:
        shutil.copy(os.path.join(PROBE, stl_from, 'terrain.stl'), os.path.join(d, 'terrain.stl'))
    return d


def test_mirror_fix_is_right_way_up_and_round():
    d = make_run([('open', {'path': '/lab/data/slices.solidcraft'}),
                  ('execute', {'command': 'solid.loft', 'params': {}}),
                  ('execute', {'command': 'solid.mirror', 'params': {'plane': 'XY'}})], 'mirror')
    s = score.score_run(d)
    assert s['fix'] == 'mirror' and s['cost_usd'] == 0.5
    assert s['measured']['up'] is True and s['measured']['round'] is True
    assert abs(s['measured']['volume_vs_hand_pct']) < 1


def test_rotation_fix_is_up_but_mirrored():
    d = make_run([('execute', {'command': 'solid.loft', 'params': {}}),
                  ('batch', {'commands': [{'command': 'solid.move', 'params': {'axis': [1, 0, 0], 'angle': 180}}]})],
                 'slicer-flip')
    s = score.score_run(d)
    assert s['fix'] == 'rotate'
    assert s['measured']['up'] is True and s['measured']['round'] is False


def test_no_fix_hangs_under_the_floor():
    s = score.score_run(make_run([('execute', {'command': 'solid.loft', 'params': {}})], 'xz'))
    assert s['fix'] == 'none' and s['measured']['up'] is False


def test_redrawn_sketches_count_as_a_rebuild():
    d = make_run([('batch', {'commands': [{'command': 'sketch.create', 'params': {'plane': 'XZ', 'flip': True}}]}),
                  ('execute', {'command': 'solid.loft', 'params': {}})], 'flip')
    assert score.score_run(d)['fix'] == 'rebuild'


def test_no_stl():
    assert score.score_run(make_run([]))['measured'] is None
