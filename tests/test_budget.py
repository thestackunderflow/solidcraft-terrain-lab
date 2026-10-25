"""The shared $20 ledger for the four SolidCraft open-data labs (PLAN rev 2.1 §4.7): a run starts only when the logged
total plus that run's cap stays within $20; a killed run counts at its full cap."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'claude-run'))
import budget  # noqa: E402


def ledger(rows):
    p = os.path.join(tempfile.mkdtemp(), 'BUDGET.tsv')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('# run\tcost_usd\tkind\tlab\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    return p


def test_empty_ledger_total_is_zero():
    assert budget.total(ledger([])) == 0.0
    assert budget.total(os.path.join(tempfile.mkdtemp(), 'missing.tsv')) == 0.0


def test_total_sums_every_lab():
    p = ledger([('a-1', '0.25', 'logged', 'lid'), ('b-1', '1.00', 'killed-floor', 'terrain')])
    assert budget.total(p) == 1.25


def test_allowed_stops_before_the_cap():
    assert budget.allowed(18.9, 1.0, 20.0) is True
    assert budget.allowed(19.1, 1.0, 20.0) is False
    assert budget.allowed(19.0, 1.0, 20.0) is True


def test_record_appends_and_kills_count_at_cap():
    p = ledger([])
    budget.record(p, 'plain-1', None, 1.0, 'lid')
    budget.record(p, 'plain-2', 0.31, 1.0, 'lid')
    rows = [l.rstrip('\n').split('\t') for l in open(p, encoding='utf-8') if not l.startswith('#')]
    assert rows == [['plain-1', '1.0000', 'killed-floor', 'lid'], ['plain-2', '0.3100', 'logged', 'lid']]
    assert budget.total(p) == 1.31
