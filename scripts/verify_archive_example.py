"""Reconstruct the included retained-checkpoint example and check its proof."""

from fractions import Fraction
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cocert.verification import verify


def reconstruct(example):
    """Difference exact endpoint counts into A, B, and C."""
    checkpoints = example["checkpoints"]
    histograms = [list(map(Fraction, point["counts"])) for point in checkpoints]
    assert all(a["time"] < b["time"] for a, b in zip(checkpoints, checkpoints[1:]))
    assert all(
        all(a <= b for a, b in zip(left, right))
        for left, right in zip(histograms, histograms[1:])
    )

    def difference(first, last):
        return [str(b - a) for a, b in zip(histograms[first], histograms[last])]

    left, right = example["left"], example["right"]
    return dict(
        query_id=example["query_id"],
        dataset=example["dataset"],
        A=[difference(first, left) for first, last in example["windows"]],
        B=difference(left, right),
        C=[difference(right, last) for first, last in example["windows"]],
    )


def main():
    root = Path(__file__).resolve().parents[1]
    example = json.loads((root / "examples/retained-example.json").read_text())
    query = reconstruct(example)
    expected = json.loads((root / "examples/integer-gap.jsonl").read_text())
    for name in ("A", "C"):
        assert [[Fraction(v) for v in row] for row in query[name]] == [
            [Fraction(v) for v in row] for row in expected[name]
        ]
    assert list(map(Fraction, query["B"])) == list(map(Fraction, expected["B"]))
    proof = json.loads((root / "examples/integer-gap-proof.jsonl").read_text())
    assert verify(proof, query, epsilon=example["epsilon"]) is False
    print(
        json.dumps(
            dict(
                status="passed",
                checkpoints=len(example["checkpoints"]),
                reconstructed_windows=len(query["A"]),
                certificate="negative",
                domain="real mass",
            )
        )
    )


if __name__ == "__main__":
    main()
