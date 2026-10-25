"""The shared agent-run ledger of the SolidCraft open-data labs: $20 for all four videos (owner, 22 Oct 2026).

    python3 budget.py check  LEDGER RUN_CAP [TOTAL_CAP]          exit 0 = may start, 2 = stop
    python3 budget.py record LEDGER RUN COST_OR_EMPTY RUN_CAP LAB  (an empty cost = a killed run, counted at RUN_CAP)
"""
import os
import sys

TOTAL_CAP = 20.0


def total(path):
    if not os.path.exists(path):
        return 0.0
    s = 0.0
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            s += float(line.split('\t')[1])
    return round(s, 4)


def allowed(spent, run_cap, cap=TOTAL_CAP):
    return spent + run_cap <= cap + 1e-9


def record(path, run, cost, run_cap, lab):
    new = not os.path.exists(path)
    kind = 'logged' if cost is not None else 'killed-floor'
    value = float(cost) if cost is not None else float(run_cap)
    with open(path, 'a', encoding='utf-8', newline='\n') as f:
        if new:
            f.write('# run\tcost_usd\tkind\tlab\n')
        f.write(f'{run}\t{value:.4f}\t{kind}\t{lab}\n')
    return total(path)


if __name__ == '__main__':
    cmd, ledger = sys.argv[1], sys.argv[2]
    if cmd == 'check':
        cap = float(sys.argv[4]) if len(sys.argv) > 4 else TOTAL_CAP
        t = total(ledger)
        ok = allowed(t, float(sys.argv[3]), cap)
        print(f'spent ${t:.4f} of ${cap:.2f}; this run may cost up to ${float(sys.argv[3]):.2f}: {"GO" if ok else "STOP"}')
        sys.exit(0 if ok else 2)
    if cmd == 'record':
        c = sys.argv[4]
        print(f'total now ${record(ledger, sys.argv[3], float(c) if c else None, float(sys.argv[5]), sys.argv[6]):.4f}')
