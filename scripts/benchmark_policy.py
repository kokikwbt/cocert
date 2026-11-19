"""Benchmark the fixed public policy in fresh processes on supplied query packs."""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time


def rows(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def key(row):
    return row.get('dataset', ''), str(row['query_id'])


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def worker(job_path):
    from cocert import Engine
    from cocert.backends import full, decision, fixed
    job = json.loads(Path(job_path).read_text())
    queries = rows(job['queries'])
    if job['cohort']:
        queries = [q for q in queries if q.get('cohort') == job['cohort']]
    totals = {} if not job['totals'] else {key(q): q['total'] for q in rows(job['totals'])}
    assert len({key(q) for q in queries}) == len(queries) > 0
    calls = [0]
    for module, name in [(full, 'threshold_residual'), (decision, 'threshold_residual'), (fixed, 'minimum_shared_tv')]:
        original = getattr(module, name)
        def counted(*args, _function=original, **kwargs):
            calls[0] += 1
            return _function(*args, **kwargs)
        setattr(module, name, counted)
    engine = Engine(pair_scales=0 if job['method'] == 'no-pairs' else 5)
    method = 'cocert' if job['method'] == 'no-pairs' else job['method']
    symbolic = job['method'] == 'symbolic_smt'
    isolated = None
    if symbolic:
        from cocert.baselines.symbolic_isolation import IsolatedSMT
        isolated = IsolatedSMT()
    warm = dict(query_id=-1, A=[[10, 0], [20, 0]], B=[2, 2], C=[[0, 10], [0, 20]])
    if symbolic:
        isolated.decide(warm, job['epsilon'], timeout_ms=1000)
    else:
        engine.query(warm, job['epsilon'], method=method)
        engine.query(warm, job['epsilon'], method='full', total=2)
    random.Random(job['seed'] + job['repeat']).shuffle(queries)
    with Path(job['answers']).open('w') as stream:
        for query in queries:
            if isolated and isolated.process is None:
                isolated.start()
            previous = calls[0]; tick = time.perf_counter()
            if symbolic:
                answer = isolated.decide(query, job['epsilon'], total=totals.get(key(query)),
                                         timeout_ms=job['smt_timeout_ms'], seed=job['seed'])
            else:
                answer = engine.query(query, job['epsilon'], method=method, total=totals.get(key(query)))
            elapsed = time.perf_counter() - tick
            answer.update(query_id=query['query_id'], dataset=query.get('dataset', ''), seconds=elapsed,
                          solver_called=True if symbolic else calls[0] > previous,
                          repeat=job['repeat'], method=job['method'])
            stream.write(json.dumps(answer) + '\n')
    if isolated:
        isolated.close()


def quantile(values, probability):
    values = sorted(values); target = probability * sum(w for _, w in values); cumulative = 0
    for value, weight in values:
        cumulative += weight
        if cumulative >= target: return value
    return values[-1][0]


def main(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    queries = rows(args.queries)
    if args.cohort: queries = [q for q in queries if q.get('cohort') == args.cohort]
    identifiers = {key(q) for q in queries}; assert len(identifiers) == len(queries) > 0
    weights = {identifier: (1.0, '') for identifier in identifiers}
    if args.weights:
        with args.weights.open() as stream:
            supplied = {key(r): (float(r['weight']), r.get('group', '')) for r in csv.DictReader(stream)}
        assert identifiers <= supplied.keys()
        weights = {k: supplied[k] for k in identifiers}
        assert all(w > 0 for w, _ in weights.values())
    jobs = [(method, repeat) for method in args.methods for repeat in range(args.repeats)]
    assert args.repeats > 0 and len(set(args.methods)) == len(args.methods)
    random.Random(args.seed).shuffle(jobs)
    records = []
    environment = dict(os.environ)
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
        environment[name] = '1'
    for method, repeat in jobs:
        path = out / f'{method}-{repeat}.job.json'
        job = dict(method=method, repeat=repeat, seed=args.seed, epsilon=args.epsilon, cohort=args.cohort,
                   smt_timeout_ms=args.smt_timeout_ms,
                   queries=str(args.queries.resolve()), totals=str(args.totals.resolve()) if args.totals else None,
                   answers=str(out / f'{method}-{repeat}.jsonl'))
        path.write_text(json.dumps(job, indent=2) + '\n')
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', str(path)], env=environment, check=True)
        records.extend(rows(job['answers']))
    grouped = defaultdict(list)
    verdicts = defaultdict(set)
    for row in records:
        grouped[row['method'], key(row)].append(row)
        verdicts[key(row)].add(row['status'])
    for statuses in verdicts.values():
        resolved = statuses - {'undecided'}
        assert len(resolved) <= 1
    medians = []; all_statuses_stable = True
    for method in args.methods:
        for identifier in sorted(identifiers):
            rr = grouped[method, identifier]
            assert len(rr) == args.repeats
            resolved = {r['status'] for r in rr} - {'undecided'}
            assert len(resolved) <= 1
            stable = len({r['status'] for r in rr}) == 1
            all_statuses_stable &= stable
            weight, group = weights[identifier]
            medians.append(dict(method=method, group=group, weight=weight, seconds=statistics.median(r['seconds'] for r in rr),
                                solver_fraction=statistics.mean(r['solver_called'] for r in rr),
                                completion_fraction=statistics.mean(r['status'] != 'undecided' for r in rr),
                                undecided_query=any(r['status'] == 'undecided' for r in rr),
                                status=rr[0]['status'] if stable else 'mixed'))
    summary = []
    for group in ['all', *sorted({group for _, group in weights.values()} - {''})]:
        for method in args.methods:
            rr = [r for r in medians if r['method'] == method and (group == 'all' or r['group'] == group)]
            mass = sum(r['weight'] for r in rr)
            summary.append(dict(group=group, method=method, sample=len(rr), population=mass,
                                mean_ms=sum(r['seconds'] * 1000 * r['weight'] for r in rr) / mass,
                                p95_ms=quantile([(r['seconds'] * 1000, r['weight']) for r in rr], .95),
                                solver_fraction=sum(r['solver_fraction'] * r['weight'] for r in rr) / mass,
                                completion_fraction=sum(r['completion_fraction'] * r['weight'] for r in rr) / mass,
                                undecided=sum(r['undecided_query'] for r in rr)))
    with (out / 'summary.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
    import cocert
    source = Path(cocert.__file__).parent
    manifest = dict(schema=1, epsilon=args.epsilon, seed=args.seed, repeats=args.repeats, methods=args.methods, cohort=args.cohort,
                    input_sha256=digest(args.queries), totals_sha256=digest(args.totals) if args.totals else None,
                    weights_sha256=digest(args.weights) if args.weights else None, python=sys.version.split()[0],
                    source_sha256={str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*.py'))},
                    policy_sha256=digest(Path(__file__).resolve().parents[1] / 'execution-policy.json'),
                    timed_calls=len(records), all_statuses_stable=all_statuses_stable,
                    all_resolved_verdicts_agree=True, smt_timeout_ms=args.smt_timeout_ms,
                    summary_sha256=digest(out / 'summary.csv'))
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(status='passed', calls=len(records), summary=summary)))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(sys.argv[2])
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('queries', type=Path); parser.add_argument('--output', required=True, type=Path)
        parser.add_argument('--totals', type=Path); parser.add_argument('--weights', type=Path); parser.add_argument('--cohort', default='')
        parser.add_argument('--epsilon', default='1/10'); parser.add_argument('--repeats', type=int, default=3)
        parser.add_argument('--seed', type=int, default=20261115)
        parser.add_argument('--smt-timeout-ms', type=int, default=1000)
        parser.add_argument('--methods', nargs='+', default=['simple-filter', 'no-pairs', 'cocert'],
                            choices=['full', 'decision', 'sharp-filter', 'simple-filter', 'no-pairs', 'cocert', 'symbolic_smt'])
        main(parser.parse_args())
