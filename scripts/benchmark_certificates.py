"""Compare fresh query execution with solver-free replay of saved certificates."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def identity(query):
    return str(query.get("dataset", "")), str(query["query_id"])


def input_hash(query, total, epsilon):
    return hashlib.sha256(encoded([query, total, epsilon]).encode()).hexdigest()


def loaded(job):
    queries = {identity(q): q for q in rows(job["queries"])}
    assert len(queries) == len(rows(job["queries"])) > 0
    totals = {} if job["totals"] is None else {
        identity(row): row["total"] for row in rows(job["totals"])
    }
    if job["totals"] is not None:
        assert set(totals) == set(queries)
    return queries, totals


def generation_worker(job):
    from cocert import Engine

    queries, totals = loaded(job)
    engine = Engine()
    warm = dict(query_id=-1, A=[[10, 0], [20, 0]], B=[2, 2], C=[[0, 10], [0, 20]])
    engine.query(warm, job["epsilon"])
    engine.query(warm, job["epsilon"], total="2")
    saved = {}
    with Path(job["generation"]).open("w") as stream:
        for repetition in range(job["repeats"]):
            keys = list(queries)
            random.Random(job["seed"] + repetition).shuffle(keys)
            for key in keys:
                query, total = queries[key], totals.get(key)
                started = time.perf_counter()
                answer = engine.query(query, job["epsilon"], total=total)
                elapsed = time.perf_counter() - started
                record = dict(dataset=key[0], query_id=key[1], status=answer["status"],
                              repetition=repetition, seconds=elapsed, stage=answer["stage"])
                stream.write(encoded(record) + "\n")
                if repetition == 0:
                    proof = answer["proof"]
                    payload = None if proof is None else {
                        name: value for name, value in proof.items() if name not in query
                    }
                    saved[key] = dict(dataset=key[0], query_id=key[1], status=answer["status"],
                        input_sha256=input_hash(query, total, job["epsilon"]), proof=payload)
    with Path(job["certificates"]).open("w") as stream:
        for key in sorted(saved):
            stream.write(encoded(saved[key]) + "\n")


def replay_worker(job):
    from cocert.verification import verify

    queries, totals = loaded(job)
    certificates = {identity(row): row for row in rows(job["certificates"])}
    assert set(queries) == set(certificates)

    def check(key):
        query, record, total = queries[key], certificates[key], totals.get(key)
        assert record["input_sha256"] == input_hash(query, total, job["epsilon"])
        if record["status"] == "undecided":
            assert record["proof"] is None
            return
        assert not set(query).intersection(record["proof"])
        proof = dict(query, **record["proof"])
        answer = verify(proof, query, total=total, epsilon=job["epsilon"])
        assert answer == (record["status"] == "positive")

    check(next(iter(queries)))
    with Path(job["replay"]).open("w") as stream:
        for repetition in range(job["repeats"]):
            keys = list(queries)
            random.Random(job["seed"] + repetition).shuffle(keys)
            for key in keys:
                started = time.perf_counter()
                check(key)
                elapsed = time.perf_counter() - started
                stream.write(encoded(dict(dataset=key[0], query_id=key[1], repetition=repetition,
                    seconds=elapsed, status=certificates[key]["status"])) + "\n")
    forbidden = {"numpy", "scipy", "clarabel", "cvxpy", "z3", "gurobipy", "osqp"}
    assert not forbidden.intersection(name.split(".")[0] for name in sys.modules)
    assert sys.flags.isolated and sys.flags.no_site
    write(job["replay_check"], dict(standard_library_only=True, isolated=True,
        raw_observations_read=False, certificate_replay_passed=True, queries=len(queries),
        statuses=dict(Counter(row["status"] for row in certificates.values()))))


def percentile(values, probability):
    values = sorted(values)
    location = (len(values) - 1) * probability
    lo, hi = int(location), min(int(location) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (location - lo)


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    job = dict(queries=str(args.queries.resolve()),
        totals=None if args.totals is None else str(args.totals.resolve()),
        epsilon=args.epsilon, repeats=args.repeats, seed=args.seed,
        **{name: str(output / filename) for name, filename in {
            "generation": "generation.jsonl", "certificates": "certificates.jsonl",
            "replay": "replay.jsonl", "replay_check": "replay-check.json"}.items()})
    path = output / "job.json"
    write(path, job)
    environment = dict(os.environ)
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"]:
        environment[name] = "1"
    script = str(Path(__file__).resolve())
    subprocess.run([sys.executable, "-I", script, "--generate", str(path)], env=environment, check=True)
    subprocess.run([sys.executable, "-I", "-S", script, "--replay", str(path)], env=environment, check=True)
    queries, totals = loaded(job)
    certificates = {identity(row): row for row in rows(job["certificates"])}
    samples = defaultdict(list)
    statuses = defaultdict(set)
    for name in ["generation", "replay"]:
        for row in rows(job[name]):
            key = identity(row)
            samples[name, key].append(row["seconds"])
            statuses[key].add(row["status"])
    details = []
    for key in sorted(queries):
        assert len(statuses[key]) == 1
        assert all(len(samples[name, key]) == args.repeats for name in ["generation", "replay"])
        record = certificates[key]
        details.append(dict(dataset=key[0], query_id=key[1], status=record["status"],
            generation_ms=1000 * statistics.median(samples["generation", key]),
            replay_ms=1000 * statistics.median(samples["replay", key]),
            input_bytes=len((encoded(queries[key]) + "\n").encode()),
            certificate_bytes=len((encoded(record) + "\n").encode())))
    summary = []
    for label in sorted({key[0] for key in queries}):
        selected = [row for row in details if row["dataset"] == label]
        resolved = [row for row in selected if row["status"] != "undecided"]
        counts = Counter(row["status"] for row in selected)
        summary.append(dict(dataset=label, n=len(selected), positive=counts["positive"],
            negative=counts["negative"], undecided=counts["undecided"],
            generation_median_ms=statistics.median(row["generation_ms"] for row in resolved),
            replay_median_ms=statistics.median(row["replay_ms"] for row in resolved),
            replay_p95_ms=percentile([row["replay_ms"] for row in resolved], .95),
            certificate_median_bytes=statistics.median(row["certificate_bytes"] for row in resolved),
            generation_mean_ms=statistics.mean(row["generation_ms"] for row in resolved),
            replay_mean_ms=statistics.mean(row["replay_ms"] for row in resolved),
            speedup_median=statistics.median(row["generation_ms"] / row["replay_ms"] for row in resolved)))
    for filename, records in [("per-query.csv", details), ("summary.csv", summary)]:
        with (output / filename).open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    write(output / "manifest.json", dict(python=sys.version, platform=platform.platform(),
        repeats=args.repeats, threshold=args.epsilon, input_sha256=digest(args.queries),
        totals_sha256=None if args.totals is None else digest(args.totals),
        source_sha256={str(p.relative_to(SOURCE)): digest(p) for p in SOURCE.rglob("*.py")},
        script_sha256=digest(__file__),
        timing="Per-query median of fresh calls; excludes imports, warmup, JSON decoding and disk I/O",
        replay="Separate isolated standard-library process; includes input hashing, binding and exact checking",
        storage="Uncompressed JSONL proof record, with IDs and input hash; input counts stored separately",
        all_statuses_stable=True, queries=len(queries),
        outputs={p.name: digest(p) for p in output.iterdir() if p.is_file()}))
    print(encoded(dict(output=str(output), queries=len(queries), summary=summary)), flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in {"--generate", "--replay"}:
        job = json.loads(Path(sys.argv[2]).read_text())
        (generation_worker if sys.argv[1] == "--generate" else replay_worker)(job)
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("queries", type=Path)
        parser.add_argument("--totals", type=Path)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--epsilon", default="1/10")
        parser.add_argument("--repeats", type=int, default=3)
        parser.add_argument("--seed", type=int, default=20261116)
        run(parser.parse_args())
