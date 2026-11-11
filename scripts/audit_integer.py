"""Independent exhaustive small-count audit, using only the standard library."""

import argparse
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path


def maximum_tv(query, allocation):
    """Evaluate the original normalized histograms, independently of the solver."""
    boundary = list(map(Fraction, query["B"]))
    contrasts = []
    for before, after in zip(query["A"], query["C"]):
        before, after = list(map(Fraction, before)), list(map(Fraction, after))
        left_total = sum(before) + sum(allocation)
        right_total = sum(after) + sum(boundary) - sum(allocation)
        contrast = (
            sum(
                abs((a + x) / left_total - (c + b - x) / right_total)
                for a, b, c, x in zip(before, boundary, after, allocation)
            )
            / 2
        )
        contrasts.append(contrast)
    return max(contrasts)


def audit(query, limit=100000, boundary_limit=20):
    """Enumerate the unknown-total model only when its declared budget permits."""
    counts = [
        Fraction(value)
        for row in query["A"] + [query["B"]] + query["C"]
        for value in row
    ]
    if any(value < 0 for value in counts):
        raise ValueError("Nonnegative counts required")
    if any(value.denominator != 1 for value in counts):
        return dict(status="ineligible", reason="noninteger counts")
    boundary = [int(Fraction(value)) for value in query["B"]]
    states = math.prod(value + 1 for value in boundary)
    if sum(boundary) > boundary_limit or states > limit:
        return dict(status="ineligible", reason="enumeration budget", states=states)
    active = [j for j, value in enumerate(boundary) if value]
    best, witness = None, None
    for coordinates in itertools.product(*(range(boundary[j] + 1) for j in active)):
        allocation = [0] * len(boundary)
        for j, value in zip(active, coordinates):
            allocation[j] = value
        value = maximum_tv(query, allocation)
        if best is None or value < best:
            best, witness = value, allocation
    return dict(
        status="enumerated",
        states=states,
        integer_value=str(best),
        integer_allocation=witness,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queries", type=Path)
    parser.add_argument("--max-states", type=int, default=100000)
    parser.add_argument("--max-boundary", type=int, default=20)
    args = parser.parse_args(argv)
    for line in args.queries.read_text().splitlines():
        if line.strip():
            query = json.loads(line)
            result = audit(query, args.max_states, args.max_boundary)
            print(json.dumps(dict(query_id=query.get("query_id"), **result)))


if __name__ == "__main__":
    main()
