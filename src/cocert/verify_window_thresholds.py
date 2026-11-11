"""Standard-library exact checker for scale-specific thresholds and count metadata."""

from fractions import Fraction as F
from .queries import thresholds


def verify(q, p, *, epsilon=None, total=None):
    """Bind a per-window proof to counts, requested thresholds and split total."""
    if not __debug__:
        raise RuntimeError("Exact checks require enabled assertions")
    A = [[F(v) for v in r] for r in q["A"]]
    B = list(map(F, q["B"]))
    C = [[F(v) for v in r] for r in q["C"]]
    es = list(map(F, p["epsilon"]))
    expected_total = None if total is None else F(total)
    total = None if p["total"] is None else F(p["total"])
    assert len(A) == len(C) == len(es) > 0 and min(es) >= 0 and B and min(B) >= 0
    if epsilon is not None:
        assert es == thresholds(epsilon, len(A)), "Proof/threshold mismatch"
    assert total == expected_total, "Proof/split-total mismatch"
    assert all(len(r) == len(B) and min(r) >= 0 and sum(r) > 0 for r in A + C)
    assert total is None or 0 <= total <= sum(B)
    if p["kind"] in ["feasible", "single"]:
        x = list(map(F, p["allocation"]))
        assert (
            len(x) == len(B)
            and all(0 <= v <= b for v, b in zip(x, B))
            and (total is None or sum(x) == total)
        )
        values = []
        for a, c in zip(A, C):
            L, R = sum(a) + sum(x), sum(c) + sum(B) - sum(x)
            values.append(
                sum(
                    abs((u + v) / L - (w + b - v) / R) for u, w, b, v in zip(a, c, B, x)
                )
                / 2
            )
        if p["kind"] == "feasible":
            assert all(v <= e for v, e in zip(values, es))
            return False
        k = p["scale"]
        v = values[k]
        assert v == F(p["value"]) > es[k]
        a, c = A[k], C[k]
        W = sum(a) + sum(B) + sum(c)
        t = (sum(a) + sum(x)) / W
        if total is None:
            P = [u + b + w for u, b, w in zip(a, B, c)]
            f = sum(max(F(0), u - t * z) for u, z in zip(a, P)) / W
            g = sum(max(F(0), t * z - u - b) for u, b, z in zip(a, B, P)) / W
            assert v == max(f, g) / (t * (1 - t)) and (
                f == g
                or (t == sum(a) / W and f <= g)
                or (t == (sum(a) + sum(B)) / W and f >= g)
            )
        else:
            theta = [t * (u + b + w) - u for u, b, w in zip(a, B, c)]
            clipped = [max(F(0), min(b, z)) for b, z in zip(B, theta)]
            optimum = (
                sum(abs(z - v) for z, v in zip(theta, clipped))
                + abs(total - sum(clipped))
            ) / (2 * W * t * (1 - t))
            assert v == optimum
        return True
    assert p["kind"] == "support"
    w = list(map(F, p["weights"]))
    als = [list(map(F, r)) for r in p["alpha"]]
    assert len(w) == len(als) == len(A) and min(w) >= 0 and sum(w) == 1
    assert all(len(r) == len(B) and all(abs(v) <= 1 for v in r) for r in als)
    constant = F(0)
    grad = [F(0)] * len(B)
    if total is not None:
        for a, c, z, al, e in zip(A, C, w, als, es):
            L, R = sum(a) + total, sum(c) + sum(B) - total
            constant += z * (
                sum(t * (u / L - (v + b) / R) for u, v, b, t in zip(a, c, B, al)) / 2
                - e
            )
            for j in range(len(B)):
                grad[j] += z * al[j] * (1 / L + 1 / R) / 2
        remaining = total
        bound = constant
        for j in sorted(range(len(B)), key=lambda j: grad[j]):
            amount = min(B[j], remaining)
            remaining -= amount
            bound += amount * grad[j]
        assert remaining == 0
    else:
        s = F(p["tangent_total"])
        for a, c, z, al, e in zip(A, C, w, als, es):
            W = sum(a) + sum(B) + sum(c)
            ac = sum(a)
            P = [u + b + v for u, b, v in zip(a, B, c)]
            dot = sum(t * v for t, v in zip(al, P))
            constant += z * (
                sum(t * u for t, u in zip(al, a)) / (2 * W)
                - ac * dot / (2 * W**2)
                + e * (ac**2 - ac * W - s**2) / W**2
            )
            for j in range(len(B)):
                grad[j] += z * (
                    al[j] / (2 * W) - dot / (2 * W**2) + e * (2 * ac - W + 2 * s) / W**2
                )
        bound = constant + sum(b * min(F(0), v) for b, v in zip(B, grad))
    assert bound == F(p["bound"]) > 0
    return True
