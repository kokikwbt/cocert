"""Rational allocations and lower bounds for the known-total LP."""

from fractions import Fraction as F


def tv(a, b, c, x):
    left, right = sum(a) + sum(x), sum(c) + sum(b) - sum(x)
    return (
        sum(abs((u + v) / left - (w + z - v) / right) for u, z, w, v in zip(a, b, c, x))
        / 2
    )


def single_optimum(a, b, c, total):
    W = sum(a) + sum(b) + sum(c)
    theta = [(sum(a) + total) * (u + v + w) / W - u for u, v, w in zip(a, b, c)]
    clipped = [max(F(0), min(v, t)) for v, t in zip(b, theta)]
    x = repair(clipped, b, total)
    return tv(a, b, c, x), x


def repair(values, b, total):
    x = [max(F(0), min(cap, F(v))) for v, cap in zip(values, b)]
    gap = total - sum(x)
    for j in range(len(x)):
        d = min(gap, b[j] - x[j]) if gap >= 0 else -min(-gap, x[j])
        x[j] += d
        gap -= d
    assert gap == 0
    return x


def support_bound(A, b, C, total, weights, alpha):
    constant = F(0)
    gradient = [F(0)] * len(b)
    for a, c, w, al in zip(A, C, weights, alpha):
        left, right = sum(a) + total, sum(c) + sum(b) - total
        constant += (
            w
            * sum(
                z * (u / left - (v + cap) / right) for u, v, cap, z in zip(a, c, b, al)
            )
            / 2
        )
        for j in range(len(b)):
            gradient[j] += w * al[j] * (1 / left + 1 / right) / 2
    remaining, bound = total, constant
    for j in sorted(range(len(b)), key=lambda j: gradient[j]):
        amount = min(b[j], remaining)
        remaining -= amount
        bound += amount * gradient[j]
    assert remaining == 0
    return bound


def rational_lp_candidates(A, b, C, total, solution):
    scale = sum(b)
    primal = []
    for den in [10**7, 10**10, 10**13, 10**16]:
        x = repair(
            [
                F(float(v) / float(scale)).limit_denominator(den) * scale
                for v in solution["allocation"]
            ],
            b,
            total,
        )
        primal.append((max(tv(a, b, c, x) for a, c in zip(A, C)), x))
    upper, x = min(primal, key=lambda v: v[0])
    weights = [
        max(F(0), F(float(w)).limit_denominator(10**12)) for w in solution["weights"]
    ]
    assert sum(weights) > 0
    z = sum(weights)
    weights = [w / z for w in weights]
    alpha = [
        [max(F(-1), min(F(1), F(float(v)).limit_denominator(10**12))) for v in row]
        for row in solution["subgradients"]
    ]
    lower = support_bound(A, b, C, total, weights, alpha)
    assert lower <= upper
    return dict(
        lower=lower,
        upper=upper,
        allocation=list(map(str, x)),
        weights=list(map(str, weights)),
        alpha=[list(map(str, row)) for row in alpha],
    )
