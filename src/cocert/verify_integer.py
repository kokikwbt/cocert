"""Standard-library checker for integer witnesses and box-partition proofs.

This checker never runs branch-and-bound or the resource-allocation optimizer.
"""

from fractions import Fraction as F
import hashlib
import json
from .queries import thresholds


def verify(q, p, *, epsilon=None, total=None):
    """Bind an integer proof to counts, requested thresholds and split total."""
    if not __debug__:
        raise RuntimeError("Exact checks require enabled assertions")
    A = [[F(v) for v in r] for r in q["A"]]
    B = list(map(F, q["B"]))
    C = [[F(v) for v in r] for r in q["C"]]
    assert A and len(A) == len(C) and B and min(B) >= 0
    assert all(len(r) == len(B) and min(r) >= 0 and sum(r) > 0 for r in A + C)
    assert all(v.denominator == 1 for r in A + [B] + C for v in r)
    A = [[int(v) for v in r] for r in A]
    B = list(map(int, B))
    C = [[int(v) for v in r] for r in C]
    assert (
        p["query_digest"]
        == hashlib.sha256(
            json.dumps([A, B, C], separators=(",", ":")).encode()
        ).hexdigest()
    )
    es = list(map(F, p["epsilon"]))
    assert len(es) == len(A) and min(es) >= 0
    if epsilon is not None:
        assert es == thresholds(epsilon, len(A)), "Proof/threshold mismatch"
    expected_total = None if total is None else F(total)
    total = p["total"]
    assert total == expected_total, "Proof/split-total mismatch"
    assert total is None or isinstance(total, int) and 0 <= total <= sum(B)
    if p["kind"] == "integer_feasible":
        x = p["allocation"]
        assert len(x) == len(B) and all(
            isinstance(v, int) and 0 <= v <= b for v, b in zip(x, B)
        )
        assert total is None or sum(x) == total
        for a, c, e in zip(A, C, es):
            L = [F(u + v) for u, v in zip(a, x)]
            R = [F(u + b - v) for u, b, v in zip(c, B, x)]
            left_total, right_total = sum(L), sum(R)
            assert (
                sum(abs(u / left_total - v / right_total) for u, v in zip(L, R)) / 2
                <= e
            )
        return False
    assert p["kind"] == "integer_exclusion"
    active = [j for j, b in enumerate(B) if b]
    caps = [B[j] for j in active]
    expected = {total} if total is not None else set(range(sum(B) + 1))
    assert len(p["roots"]) == len(expected)
    assert {r["total"] for r in p["roots"]} == expected
    seen = 0

    def tree(node, lo, hi, S):
        nonlocal seen
        seen += 1
        sl, su = sum(lo), sum(hi)
        if node["kind"] == "empty":
            assert S < sl or S > su
            return
        assert sl <= S <= su
        lower = [max(l, S - (su - u)) for l, u in zip(lo, hi)]
        upper = [min(u, S - (sl - l)) for l, u in zip(lo, hi)]
        if node["kind"] == "split":
            j = node["coordinate"]
            cut = node["cut"]
            assert (
                isinstance(j, int)
                and 0 <= j < len(caps)
                and isinstance(cut, int)
                and lower[j] <= cut < upper[j]
            )
            left = upper[:]
            left[j] = cut
            right = lower[:]
            right[j] = cut + 1
            tree(node["left"], lower, left, S)
            tree(node["right"], right, upper, S)
            return
        assert node["kind"] == "bound"
        k = node["scale"]
        assert isinstance(k, int) and 0 <= k < len(A)
        x = node["allocation"]
        assert (
            len(x) == len(caps)
            and all(
                isinstance(v, int) and l <= v <= u for v, l, u in zip(x, lower, upper)
            )
            and sum(x) == S
        )
        a, c = A[k], C[k]
        L, R = sum(a) + S, sum(c) + sum(B) - S
        W = L + R
        offsets = [a[j] * R - (c[j] + B[j]) * L for j in active]
        # Exchange optimality is sufficient for separable discrete convex costs.
        removed = [
            abs(W * xj + d) - abs(W * (xj - 1) + d)
            for xj, d, l in zip(x, offsets, lower)
            if xj > l
        ]
        added = [
            abs(W * (xj + 1) + d) - abs(W * xj + d)
            for xj, d, u in zip(x, offsets, upper)
            if xj < u
        ]
        assert not removed or not added or max(removed) <= min(added)
        full = [0] * len(B)
        for j, v in zip(active, x):
            full[j] = v
        value = sum(
            abs((u + v) * R - (w + cap - v) * L) for u, w, cap, v in zip(a, c, B, full)
        )
        assert value == node["value"] and F(value, 2 * L * R) > es[k]

    for r in p["roots"]:
        tree(r["tree"], [0] * len(caps), caps[:], r["total"])
    return True
