"""Rebuild stratified latency aggregates from repeated timings and exact weights."""
import argparse
from collections import defaultdict
import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / 'expected/final-policy'
GROUPS = ['separate_positive', 'shared_only_positive', 'common_negative', 'all']


def quantile(rows, probability):
    target = probability * sum(weight for _, weight in rows)
    cumulative = F(0)
    for value, weight in sorted(rows):
        cumulative += weight
        if cumulative >= target: return value
    raise AssertionError('Empty weighted sample')


def reproduce(folder=DEFAULT_INPUT):
    manifest = json.loads((folder / 'manifest.json').read_text())
    methods = manifest['timing_methods']
    repetitions = manifest['repetitions']
    assert repetitions % 2 == 1
    names = ['query-selection.csv', 'stratified-timings.csv', 'latency-summary.csv']
    for name in names:
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == manifest['files'][name], name
    with (folder / names[0]).open() as stream:
        queries = {(r['dataset'], r['query_id']): r for r in csv.DictReader(stream) if r['cohort'] == 'strata'}
    assert len(queries) == manifest['cohorts']['strata']
    raw = defaultdict(list); calls = 0
    with (folder / names[1]).open() as stream:
        for row in csv.DictReader(stream):
            assert row['method'] in methods and row['solver_called'] in ['0', '1']
            key = row['dataset'], row['query_id']; assert key in queries
            assert F(row['seconds']) >= 0
            raw[row['method'], key].append(row); calls += 1
    assert calls == len(methods) * repetitions * len(queries)
    assert len(raw) == len(methods) * len(queries)
    medians = []
    for (method, key), rows in raw.items():
        assert len(rows) == repetitions and {r['repeat'] for r in rows} == set(map(str, range(repetitions)))
        assert len({r['status'] for r in rows} - {'undecided'}) <= 1
        query = queries[key]; weight = F(query['rational_weight']); assert weight > 0
        medians.append(dict(method=method, group=query['group'], weight=weight,
                            ms=1000 * sorted(F(r['seconds']) for r in rows)[repetitions // 2],
                            solver=F(sum(int(r['solver_called']) for r in rows), repetitions),
                            completed=F(sum(r['status'] != 'undecided' for r in rows), repetitions)))
    summary = []
    for group in GROUPS:
        for method in methods:
            rows = [r for r in medians if r['method'] == method and (group == 'all' or r['group'] == group)]
            mass = sum(r['weight'] for r in rows)
            assert mass.denominator == 1
            summary.append(dict(group=group, method=method, sample=len(rows), population=int(mass),
                                mean_ms=float(sum(r['ms'] * r['weight'] for r in rows) / mass),
                                p95_ms=float(quantile([(r['ms'], r['weight']) for r in rows], F(95, 100))),
                                solver_fraction=float(sum(r['solver'] * r['weight'] for r in rows) / mass),
                                completion_fraction=float(sum(r['completed'] * r['weight'] for r in rows) / mass)))
    with (folder / names[2]).open() as stream:
        expected = {(r['label'], r['method']): r for r in csv.DictReader(stream) if r['cohort'] == 'strata'}
    assert len(expected) == len(summary)
    for row in summary:
        reference = expected[row['group'], row['method']]
        for name in ['sample', 'population']: assert row[name] == int(reference[name])
        for name in ['mean_ms', 'p95_ms', 'solver_fraction', 'completion_fraction']:
            assert math.isclose(row[name], float(reference[name]), rel_tol=1e-10, abs_tol=1e-10), (row, name)
    return dict(status='passed', repeated_timings=calls, sampled_queries=len(queries),
                population=manifest['cohorts']['stratum_population'],
                aggregation='three-pass query medians; exact inverse sampling weights; weighted empirical P95',
                matches_saved_table=True, standard_library_only=True, rows=summary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--inputs', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path); args = parser.parse_args(); result = reproduce(args.inputs)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(result['rows'][0])); writer.writeheader(); writer.writerows(result['rows'])
    print(json.dumps(result, indent=2))
