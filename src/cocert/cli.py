"""Command parsing and dispatch; verification needs only the standard library."""

import argparse
import json
from pathlib import Path
from .configuration import METHODS
from .io import indexed, replay, rows


def build_parser():
    """Define solve, compare, verify, and benchmark commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("solve", "compare", "verify", "benchmark"):
        command = commands.add_parser(name)
        command.add_argument("queries", type=Path)
        command.add_argument("--epsilon", default="1/10")
        command.add_argument(
            "--totals", type=Path, help="Explicit totals JSONL; omitted means unknown"
        )
        if name == "verify":
            command.add_argument("results", type=Path)
        else:
            command.add_argument("--output", type=Path, required=True)
        if name in ("solve", "benchmark"):
            command.add_argument("--method", default="cocert", choices=METHODS)
        if name == "benchmark":
            command.add_argument("--repeats", type=int, default=3)
            command.add_argument("--seed", type=int, default=20261021)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    queries = indexed(args.queries)
    totals = indexed(args.totals) if args.totals else None
    if totals is not None and set(totals) != set(queries):
        raise ValueError("Totals must match the query IDs exactly")
    if args.command == "verify":
        report = replay(
            rows(args.results), queries, epsilon=args.epsilon, totals=totals
        )
    else:
        # Import execution only here, so offline checks never load a solver.
        from .runs import run

        report = run(args, queries, totals)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
