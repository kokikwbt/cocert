"""Interval and normalized density-band TV lower bounds."""

from fractions import Fraction as F


def bands(a, B, c, total=None):
    a, B, c = [list(map(F, row)) for row in [a, B, c]]
    aa, bb, cc = sum(a), sum(B), sum(c)
    if total is None:
        return (
            [u / (aa + bb - b) for u, b in zip(a, B)],
            [(u + b) / (aa + b) for u, b in zip(a, B)],
            [u / (cc + bb - b) for u, b in zip(c, B)],
            [(u + b) / (cc + b) for u, b in zip(c, B)],
        )
    s = F(total)
    lo = [max(F(0), s - bb + b) for b in B]
    hi = [min(b, s) for b in B]
    assert 0 <= s <= bb
    return (
        [(u + v) / (aa + s) for u, v in zip(a, lo)],
        [(u + v) / (aa + s) for u, v in zip(a, hi)],
        [(u + b - v) / (cc + bb - s) for u, b, v in zip(c, B, hi)],
        [(u + b - v) / (cc + bb - s) for u, b, v in zip(c, B, lo)],
    )


def lower_bounds(pL, pU, qL, qU):
    zero = F(0)
    positive = sum((max(zero, l - u) for l, u in zip(pL, qU)), zero)
    negative = sum((max(zero, l - u) for l, u in zip(qL, pU)), zero)
    interval = (positive + negative) / 2
    density = max(
        zero,
        positive,
        negative,
        sum(map(max, pL, qL), zero) - 1,
        1 - sum(map(min, pU, qU), zero),
    )
    return interval, density


def query_bounds(q, total=None):
    values = [lower_bounds(*bands(a, q["B"], c, total)) for a, c in zip(q["A"], q["C"])]
    return max(v[0] for v in values), max(v[1] for v in values)
