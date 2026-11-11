"""Standard-library known-total identities."""

from fractions import Fraction as F


def tv(a, b, c, x):
    L, R = sum(a) + sum(x), sum(c) + sum(b) - sum(x)
    return (
        sum(abs((u + v) / L - (w + cap - v) / R) for u, w, cap, v in zip(a, c, b, x))
        / 2
    )


def verify_single(a, b, c, x, value, total=None):
    assert len(x) == len(b) and all(0 <= v <= cap for v, cap in zip(x, b))
    assert tv(a, b, c, x) == value
    W = sum(a) + sum(b) + sum(c)
    if total is None:
        left = (sum(a) + sum(x)) / W
        p = [u + v + w for u, v, w in zip(a, b, c)]
        f = sum(max(F(0), u - left * v) for u, v in zip(a, p)) / W
        g = sum(max(F(0), left * v - u - cap) for u, cap, v in zip(a, b, p)) / W
        assert value == max(f, g) / (left * (1 - left))
        assert (
            f == g
            or (left == sum(a) / W and f <= g)
            or (left == (sum(a) + sum(b)) / W and f >= g)
        )
    else:
        assert sum(x) == total
        L = sum(a) + total
        theta = [L * (u + cap + w) / W - u for u, cap, w in zip(a, b, c)]
        z = [max(F(0), min(cap, t)) for cap, t in zip(b, theta)]
        # Distance to the box plus the unavoidable sum correction is sharp.
        bound = (
            (1 / L + 1 / (W - L))
            * (sum(abs(v - t) for v, t in zip(z, theta)) + abs(total - sum(z)))
            / 2
        )
        assert value == bound


def positive_bound(A, b, C, total, r):
    weights = list(map(F, r["weights"]))
    alpha = [list(map(F, v)) for v in r["alpha"]]
    assert (
        len(weights) == len(alpha) == len(A) and min(weights) >= 0 and sum(weights) == 1
    )
    assert all(len(v) == len(b) and all(abs(z) <= 1 for z in v) for v in alpha)
    intercept = F(0)
    slopes = [F(0)] * len(b)
    for a, c, w, al in zip(A, C, weights, alpha):
        L, R = sum(a) + total, sum(c) + sum(b) - total
        intercept += (
            w
            * sum(z * (u / L - (v + cap) / R) for z, u, v, cap in zip(al, a, c, b))
            / 2
        )
        for j in range(len(b)):
            slopes[j] += w * al[j] * (1 / L + 1 / R) / 2
    remaining = total
    bound = intercept
    for j in sorted(range(len(b)), key=lambda j: slopes[j]):
        v = min(remaining, b[j])
        remaining -= v
        bound += v * slopes[j]
    assert remaining == 0 and bound == F(r["lower"])
    return bound
