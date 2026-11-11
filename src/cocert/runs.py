"""Execute CLI runs and record inputs, proofs, timing, and environment hashes."""

import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import statistics
from .io import replay, sha256, write_rows

THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def output_paths(output, *, benchmark):
    """Derive all files for one run and reject accidental overwrites up front."""
    paths = {
        "answers": output,
        "manifest": output.with_suffix(output.suffix + ".manifest.json"),
    }
    if benchmark:
        paths["timings"] = output.with_suffix(output.suffix + ".timings.jsonl")
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Choose a new output path; existing runs are preserved")
    return paths


def _evaluate(args, queries, totals):
    """Keep first-pass answers and all benchmark timings in a reproducible order."""
    # Set single-thread defaults before loading numerical libraries.
    for name in THREAD_VARIABLES:
        os.environ.setdefault(name, "1")
    from .api import Engine, compare

    engine = Engine()
    repeats = args.repeats if args.command == "benchmark" else 1
    if repeats < 1:
        raise ValueError("Positive repeat count required")
    rng = random.Random(getattr(args, "seed", 0))
    order = list(queries)
    answers, timings = [], []
    for repeat in range(repeats):
        if args.command == "benchmark":
            rng.shuffle(order)
        for identifier in order:
            query = queries[identifier]
            total = None if totals is None else totals[identifier]["total"]
            if args.command == "compare":
                result = compare(query, args.epsilon, total=total)
            else:
                result = engine.query(
                    query, args.epsilon, method=args.method, total=total
                )
            result["dataset"] = query.get("dataset", "")
            if args.command == "benchmark":
                timings.append(
                    dict(
                        dataset=identifier[0],
                        query_id=query["query_id"],
                        repeat=repeat,
                        seconds=result["seconds"],
                        status=result["status"],
                    )
                )
            if repeat == 0:
                answers.append(result)
    return answers, timings


def _manifest(args, totals):
    """Bind each saved run to the exact code, input files, and environment."""
    source = Path(__file__).parent
    manifest = dict(
        schema=1,
        command=args.command,
        method=getattr(args, "method", None),
        condition="known" if totals is not None else "unknown",
        epsilon=args.epsilon,
        inputs={"queries": sha256(args.queries)},
        python=platform.python_version(),
        platform=platform.system(),
        packages={
            name: importlib.metadata.version(name)
            for name in ("cocert", "numpy", "scipy", "clarabel")
        },
        threads={name: os.environ.get(name) for name in THREAD_VARIABLES},
        source_sha256={
            str(path.relative_to(source)): sha256(path)
            for path in sorted(source.rglob("*.py"))
        },
    )
    if totals is not None:
        manifest["inputs"]["totals"] = sha256(args.totals)
    return manifest


def run(args, queries, totals):
    """Evaluate -> verify -> write answers and a run manifest."""
    paths = output_paths(args.output, benchmark=args.command == "benchmark")
    answers, timings = _evaluate(args, queries, totals)
    manifest = _manifest(args, totals)
    if args.command != "compare":
        manifest["verification"] = replay(
            answers, queries, epsilon=args.epsilon, totals=totals
        )
    write_rows(paths["answers"], answers)
    manifest["output_sha256"] = sha256(paths["answers"])
    if timings:
        write_rows(paths["timings"], timings)
        manifest.update(
            seed=args.seed,
            repeats=args.repeats,
            timing_sha256=sha256(paths["timings"]),
            mean_ms=1000 * statistics.mean(record["seconds"] for record in timings),
            median_ms=1000 * statistics.median(record["seconds"] for record in timings),
        )
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest.get("verification", dict(queries=len(queries)))
