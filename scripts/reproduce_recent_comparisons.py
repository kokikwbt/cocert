"""Recompute paper comparisons from released audited summary tables."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'expected/recent-baselines'


def read(name):
    with (SOURCE / name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    primary = {(r['scenario'], r['epsilon']): r for r in read('primary-comparison.csv')}
    known = {(r['scenario'], r['epsilon'], r['method']): r for r in read('known-comparison.csv')}
    fields = ['positive', 'negative', 'undecided', 'not_certified', 'not_applicable']
    settings = 0
    for (scenario, epsilon, method), row in known.items():
        if method != 'CoCert':
            continue
        for name in ['Conditional LP/grid', 'Symb-SMT']:
            assert all(row[k] == known[scenario, epsilon, name][k] for k in fields)
        settings += 1
    assert settings == 24
    added = {}
    for scenario in ['Scania', 'ALPI']:
        row = primary[scenario, '1/10']
        added[scenario] = {'positive_added_over_smt': int(row['cocert']) - int(row['symb_smt']),
            'relative_gain_percent': 100 * (int(row['cocert']) / int(row['symb_smt']) - 1)}
    matched = read('shared-matched.csv')
    alpi = next(r for r in matched if r['scenario'] == 'ALPI')
    latency = {(r['scenario'], r['method']): r for r in read('nested-latency.csv') if r['cohort'] == 'unknown'}
    ratios = []
    for scenario in sorted({r[0] for r in latency}):
        control = min(float(latency[scenario, 'Conditional LP/nested (' + name + ')']['mean_ms'])
                      for name in ['HiGHS', 'Gurobi'])
        ratios.append(control / float(latency[scenario, 'CoCert']['mean_ms']))
    smt = [float(r['smt_over_cocert']) for r in read('smt-completed-intersection.csv') if r['cohort'] == 'unknown']
    report = {'passed': True, 'known_settings_with_identical_answers': settings,
        'unknown_positive_gains': added,
        'grid_positive_gain_scenarios': sum(int(r['cocert_positive']) > int(r['gurobi_positive']) for r in matched),
        'matched_alpi_requests': int(alpi['queries']),
        'matched_alpi_added_over_combined': int(alpi['cocert_positive']) - int(alpi['combined_positive']),
        'nested_lp_mean_cost_ratio_range': [min(ratios), max(ratios)],
        'jointly_resolved_smt_mean_cost_ratio_range': [min(smt), max(smt)],
        'scope': 'Summary reaggregation; full solver execution uses the adapters and prepared requests'}
    assert report['grid_positive_gain_scenarios'] == 7
    assert report['matched_alpi_added_over_combined'] == 3
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
