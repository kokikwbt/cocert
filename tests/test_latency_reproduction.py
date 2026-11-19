"""Check the released timing traces without numerical-library dependencies."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_latency_rebuilds_from_repeated_timings():
    call = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'scripts/reproduce_latency.py')],
                          capture_output=True, text=True, check=True)
    result = json.loads(call.stdout)
    assert result['repeated_timings'] == 16500 and result['sampled_queries'] == 1375
    assert result['population'] == 66952 and result['matches_saved_table']
    overall = {r['method']: r for r in result['rows'] if r['group'] == 'all'}
    assert set(overall) == {'simple-filter', 'no-pairs', 'cocert', 'symbolic_smt'}
    assert all(r['mean_ms'] > 0 and r['p95_ms'] > 0 for r in overall.values())
    assert all(0 <= r['completion_fraction'] <= 1 for r in overall.values())
