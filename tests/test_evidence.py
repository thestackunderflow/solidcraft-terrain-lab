"""The files the video cites say what the script will say:
- every number in video/terminal-*.txt is in out/evidence/numbers.json, and the numbers are recomputed here from out/;
- terminal cards <= 8 rows x 44 cols (phone widths);
- every tool-call panel's result text is in the reply its transcript row got;
- privacy: no host paths, tokens or private words (read from the LAB_PRIVATE_WORDS environment variable, comma-separated,
  never written in this repo) in anything under out/, video/, steps/, claude-run/, lid/, probe/, slicer/."""
import glob
import json
import os
import re

import pytest

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = lambda *a: os.path.join(LAB, *a)  # noqa: E731


def jload(*a):
    with open(P(*a), encoding='utf-8') as f:
        return json.load(f)


def cell(c):
    return jload('out', 'probe', '0.19.0', c, 'summary.json')


def test_numbers_are_recomputed_from_out():
    n = jload('out', 'evidence', 'numbers.json')
    meta = jload('data', 'slices.json')['meta']
    assert n['xz_zmin'] == f"{cell('xz')['bbox_min'][2]:.1f}" and n['up_zmax'] == f"{cell('plane')['bbox_max'][2]:.1f}"
    assert n['hand_volume'] == f"{meta['hand_volume_mm3']:,.0f}" and n['loft_volume'] == f"{cell('plane')['volume_mm3']:,.0f}"
    assert n['flip_top_y'] == f"{cell('slicer-flip')['summit'][1]:.1f}"
    runs = jload('out', 'runs', 'SCORES.json')['runs']
    assert n['runs'] == str(len(runs)) and n['runs_total_usd'] == f"{sum(r['cost_usd'] for r in runs):.2f}"
    assert n['slice_time'] == jload('out', 'slice', 'slice-report.json')['gcode']['print_time']


def tokens(text):
    return re.findall(r'(?<![\w.])\d+(?:\.\d+)?(?![\w.])', text)


ALWAYS = {'0', '0.0', '0.2', '0.4', '1', '2', '3', '4', '44', '50', '400', '320', '2.9.2', '0.19.0', '2009', '1.5'}


@pytest.mark.parametrize('path', sorted(glob.glob(P('video', 'terminal-*.txt'))))
def test_terminal_cards_fit_phones_and_numbers_are_evidence(path):
    lines = open(path, encoding='utf-8').read().rstrip('\n').split('\n')
    assert 1 <= len(lines) <= 8
    assert all(len(l) <= 44 for l in lines), [l for l in lines if len(l) > 44]
    vals = set(json.dumps(jload('out', 'evidence', 'numbers.json')).replace('"', ' ').replace(',', ' ').split())
    text = '\n'.join(lines).replace('$', ' ')
    for t in tokens(text):
        assert t in ALWAYS or t in vals or any(t in v for v in vals), (os.path.basename(path), t)


def test_toolcall_results_are_in_the_logged_replies():
    for tc in jload('video', 'toolcalls.json'):
        path, sel = tc['evidence'].split('#seq=')
        rows = [json.loads(l) for l in open(P(path), encoding='utf-8') if l.strip()]
        call = next(r for r in rows if r['seq'] == int(sel))
        assert call['msg']['params']['name'] == tc['tool']
        reply = next(r for r in rows[rows.index(call) + 1:] if r['dir'] == 'server->client'
                     and r['msg'].get('id') == call['msg']['id'])
        text = ''.join(c.get('text', '') for c in reply['msg']['result']['content'] if c.get('type') == 'text')
        squash = lambda s: ' '.join(s.split())  # noqa: E731  (as the engine compares: whitespace collapsed)
        assert squash(tc['result']) in squash(text) and len(tc['result']) <= 60


def private_words():
    return [w.strip().lower() for w in os.environ.get('LAB_PRIVATE_WORDS', '').split(',') if w.strip()]


SCAN = ['out', 'video', 'steps', 'claude-run', 'terrain', 'probe', 'slicer', 'data', 'README.md', 'LAB-STATUS.md', 'ACCURACY.md']
HOST = re.compile(r'([A-Za-z]:[\\/]+Users[\\/])|(/c/Users/)|(/home/[a-z])|(AppData)', re.I)
TOKEN = re.compile(r'sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}')


def scanned_files():
    for s in SCAN:
        p = P(s)
        if os.path.isfile(p):
            yield p
        for root, _, files in os.walk(p):
            for f in files:
                if not f.endswith(('.stl', '.png', '.gcode', '.pyc', '.tif', '.solidcraft')):
                    yield os.path.join(root, f)


def test_no_host_paths_tokens_or_private_words():
    words = private_words()
    bad = []
    for f in scanned_files():
        text = open(f, encoding='utf-8', errors='replace').read()
        low = text.lower()
        if HOST.search(text) or TOKEN.search(text) or any(w in low for w in words):
            bad.append(os.path.relpath(f, LAB))
    assert bad == []
