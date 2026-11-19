"""Check the portable fresh-process benchmark on a sharing-required query."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_keeps_answers_and_records_solver_avoidance(tmp_path):
    output = tmp_path / 'policy'
    subprocess.run([sys.executable, str(ROOT / 'scripts/benchmark_policy.py'),
                    str(ROOT / 'examples/sharing-gap.jsonl'), '--output', str(output), '--repeats', '2'],
                   check=True, capture_output=True, text=True)
    summary = {r['method']: r for r in csv.DictReader((output / 'summary.csv').open())}
    assert set(summary) == {'simple-filter', 'no-pairs', 'cocert'}
    assert float(summary['cocert']['solver_fraction']) == 0
    assert float(summary['no-pairs']['solver_fraction']) == 1
    assert all(int(r['undecided']) == 0 for r in summary.values())
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['timed_calls'] == 6 and manifest['all_statuses_stable']
    for path in output.glob('*.jsonl'):
        assert all(json.loads(line)['status'] == 'positive' for line in path.read_text().splitlines())


def test_symbolic_benchmark_retains_unresolved_answers(tmp_path):
    pytest.importorskip("z3")
    output = tmp_path / "symbolic"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/benchmark_policy.py"),
         str(ROOT / "examples/sharing-gap.jsonl"), "--output", str(output),
         "--methods", "symbolic_smt", "--repeats", "2", "--smt-timeout-ms", "1"],
        check=True, capture_output=True, text=True,
    )
    summary = next(csv.DictReader((output / "summary.csv").open()))
    answers = [json.loads(line) for path in output.glob("symbolic_smt-*.jsonl")
               for line in path.read_text().splitlines()]
    assert all(a["status"] in {"positive", "undecided"} for a in answers)
    completion = sum(a["status"] != "undecided" for a in answers) / len(answers)
    assert float(summary["completion_fraction"]) == completion
    assert int(summary["undecided"]) == int(completion < 1)
