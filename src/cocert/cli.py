"""Answer and verify change queries over retained histogram counts."""

import argparse
import json
from pathlib import Path

from .configuration import METHODS
from .io import indexed, replay, rows
from .queries import threshold


COMMANDS = {
    "solve": "Answer queries and save certificates.",
    "verify": "Check saved answers against the original queries.",
    "compare": "Compare certification strategies on the same queries.",
    "benchmark": "Measure repeated answers and save per-call timings.",
}


def _tolerance(text):
    """Validate a tolerance while preserving its exact input text."""
    try:
        threshold(text)
    except (ValueError, ZeroDivisionError) as error:
        raise argparse.ArgumentTypeError(
            "use a nonnegative decimal or fraction, such as 0.1 or 1/10"
        ) from error
    return text


def build_parser():
    """Define solve, compare, verify, and benchmark commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, description in COMMANDS.items():
        command = commands.add_parser(name, help=description, description=description)
        command.add_argument("queries", type=Path, help="Count-only queries in JSONL or .jsonl.gz")
        command.add_argument(
            "--epsilon", type=_tolerance, default="1/10", help="Exact TV tolerance (default: 1/10)"
        )
        command.add_argument("--totals", type=Path, help="Separate JSONL of known split totals")
        if name == "verify":
            command.add_argument("results", type=Path, help="Solver answers to verify")
        else:
            command.add_argument(
                "--output", type=Path, required=True, help="New path for the result JSONL"
            )
        if name in ("solve", "benchmark"):
            command.add_argument(
                "--method", default="cocert", choices=METHODS, help="Execution policy (default: cocert)"
            )
        if name == "benchmark":
            command.add_argument("--repeats", type=int, default=3, help="Repetitions per query (default: 3)")
            command.add_argument("--seed", type=int, default=20261021, help="Seed for shuffling query order")
    return parser


def _execute(args):
    queries = indexed(args.queries)
    totals = indexed(args.totals) if args.totals else None
    if totals is not None and set(totals) != set(queries):
        raise ValueError("The totals file must contain exactly the same dataset/query_id pairs as the query file")
    if args.command == "verify":
        return replay(rows(args.results), queries, epsilon=args.epsilon, totals=totals)
    # Load the numerical path only for commands that run queries.
    from .runs import run

    return run(args, queries, totals)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = _execute(args)
    except KeyError as error:
        parser.error(f"Missing required field: {error.args[0]}")
    except AssertionError as error:
        parser.error(str(error) or "The certificate failed exact verification")
    except (OSError, TypeError, ValueError, ZeroDivisionError) as error:
        parser.error(str(error))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
