"""Pin every file a card cites to the lab's HEAD commit: video/panel-sources.json with the sha256 of the committed blob
(git show <commit>:<path>, so a Windows working-copy line ending can never slip in). Fails if the working copy differs.

    python video/pin_sources.py     (on the host: needs git; run right after the commit that holds the sources)
"""
import hashlib
import json
import os
import subprocess
import sys

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NAME = 'solidcraft-terrain-lab'


def paths():
    out = ['out/evidence/numbers.json', 'out/runs/SCORES.json', 'out/slice/slice-report.json', 'data/slices.json', 'data/SOURCE.json',
           'terrain/sections.py', 'video/python-cards.json', 'steps/terrain-plane.json', 'steps/terrain-xz.json',
           'claude-run/run.sh', 'video/toolcalls.json', 'video/json-cards.json']
    out += sorted('video/' + f for f in os.listdir(os.path.join(LAB, 'video')) if f.startswith('terminal-'))
    for tc in json.load(open(os.path.join(LAB, 'video', 'toolcalls.json'), encoding='utf-8')):
        out.append(tc['evidence'].split('#')[0])
    for c in json.load(open(os.path.join(LAB, 'video', 'json-cards.json'), encoding='utf-8')):
        out.append(c['src'].split('#')[0])
    out += sorted('video/frames/' + f for f in os.listdir(os.path.join(LAB, 'video', 'frames')) if f.endswith('.png'))
    return sorted(set(out))


def main():
    git = lambda *a: subprocess.run(['git', '-C', LAB, *a], capture_output=True, check=True).stdout  # noqa: E731
    commit = git('rev-parse', 'HEAD').decode().strip()
    sources, bad = [], []
    for p in paths():
        blob = git('show', f'{commit}:{p}')
        with open(os.path.join(LAB, p), 'rb') as f:
            if f.read() != blob:
                bad.append(p)
        sources.append({'path': p, 'pin': f'{NAME}@{commit}:{p}', 'sha256': hashlib.sha256(blob).hexdigest()})
    if bad:
        sys.exit(f'working copy differs from {commit}: {bad}')
    with open(os.path.join(LAB, 'video', 'panel-sources.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'lab': NAME, 'commit': commit,
                   'note': f'every card pins {NAME}@<commit>:<path>; sha256 of the committed blob', 'sources': sources}, f, indent=1)
        f.write('\n')
    print(commit, len(sources))


if __name__ == '__main__':
    main()
