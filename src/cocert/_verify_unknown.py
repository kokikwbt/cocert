"""Standard-library exact witness identities."""

from fractions import Fraction as F


def verify(r):
    A = [[F(v) for v in a] for a in r["A"]]
    B = list(map(F, r["B"]))
    C = [[F(v) for v in a] for a in r["C"]]
    e = F(r["epsilon"])
    assert e >= 0 and len(A) == len(C) > 0 and len(B) > 0 and min(B) >= 0
    assert all(len(a) == len(B) and min(a) >= 0 and sum(a) > 0 for a in A + C)
    if r["kind"] in ["direct", "feasible", "single"]:
        x = list(map(F, r["allocation"]))
        assert len(x) == len(B) and all(0 <= v <= b for v, b in zip(x, B))
        values = []
        for a, c in zip(A, C):
            p = [u + v for u, v in zip(a, x)]
            q = [u + v - w for u, v, w in zip(c, B, x)]
            left_total, right_total = sum(p), sum(q)
            values.append(
                sum(abs(u / left_total - v / right_total) for u, v in zip(p, q)) / 2
            )
        if r["kind"] == "direct":
            assert sum(B) == 0
            return max(values) > e
        if r["kind"] == "feasible":
            assert max(values) <= e
            return False
        k = int(r["scale_index"])
        value = values[k]
        assert value == F(r["value"]) > e
        a, c = A[k], C[k]
        W = sum(a) + sum(B) + sum(c)
        t = (sum(a) + sum(x)) / W
        P = [u + v + w for u, v, w in zip(a, B, c)]
        f = sum(max(F(0), u - t * p) for u, p in zip(a, P)) / W
        g = sum(max(F(0), t * p - u - b) for u, b, p in zip(a, B, P)) / W
        assert value == max(f, g) / (t * (1 - t))
        assert (
            f == g
            or (t == sum(a) / W and f <= g)
            or (t == (sum(a) + sum(B)) / W and f >= g)
        )
        return True
    assert r["kind"] == "support"
    w = list(map(F, r["weights"]))
    alpha = [list(map(F, a)) for a in r["alpha"]]
    s = F(r["tangent_total"])
    assert len(w) == len(alpha) == len(A) and min(w) >= 0 and sum(w) == 1
    assert all(len(a) == len(B) and all(abs(v) <= 1 for v in a) for a in alpha)
    constant = F(0)
    gradient = [F(0)] * len(B)
    for a, c, weight, al in zip(A, C, w, alpha):
        if not weight:
            continue
        W = sum(a) + sum(B) + sum(c)
        ac = sum(a)
        P = [u + v + z for u, v, z in zip(a, B, c)]
        dot = sum(u * v for u, v in zip(al, P))
        constant += weight * (
            sum(u * v for u, v in zip(al, a)) / (2 * W)
            - ac * dot / (2 * W**2)
            + e * (ac**2 - ac * W - s**2) / W**2
        )
        for j in range(len(B)):
            gradient[j] += weight * (
                al[j] / (2 * W) - dot / (2 * W**2) + e * (2 * ac - W + 2 * s) / W**2
            )
    bound = constant + sum(b * min(F(0), v) for b, v in zip(B, gradient))
    assert bound == F(r["bound"]) and bound > 0
    return True
