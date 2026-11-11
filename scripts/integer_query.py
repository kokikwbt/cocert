"""Run integer completion queries and independently check each returned proof."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cocert.integer import decide
from cocert.io import indexed
from cocert.verify_integer import verify


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queries", type=Path)
    parser.add_argument(
        "--totals", type=Path, help="Explicit totals; omitted means unknown"
    )
    parser.add_argument("--epsilon", default="1/10")
    parser.add_argument("--max-nodes", type=int, default=100000)
    parser.add_argument("--max-total-slices", type=int, default=1024)
    args = parser.parse_args(argv)
    queries = indexed(args.queries)
    totals = indexed(args.totals) if args.totals else None
    if totals is not None and set(totals) != set(queries):
        raise ValueError("Totals must match the query IDs exactly")
    for identifier, query in queries.items():
        total = None if totals is None else totals[identifier]["total"]
        result = decide(
            query,
            args.epsilon,
            total=total,
            max_nodes=args.max_nodes,
            max_total_slices=args.max_total_slices,
        )
        if result["proof"] is not None:
            checked = verify(query, result["proof"], epsilon=args.epsilon, total=total)
            if checked != (result["status"] == "positive"):
                raise AssertionError("Integer status/proof mismatch")
        print(
            json.dumps(
                dict(
                    query_id=query["query_id"],
                    dataset=query.get("dataset", ""),
                    **result,
                )
            )
        )


if __name__ == "__main__":
    main()
