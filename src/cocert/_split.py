"""Exact breakpoint sweep for the single-window Separate sharp bound."""

from fractions import Fraction
from numbers import Integral


def minimum_exact(before, boundary, after):
    """Return the exact TV minimum and an attaining allocation.

    Floating-point inputs retain their exact binary rational values.
    """

    def convert(v):
        return [
            (
                x
                if isinstance(x, Fraction)
                else Fraction(int(x)) if isinstance(x, Integral) else Fraction(float(x))
            )
            for x in v
        ]

    A, B, C = map(convert, (before, boundary, after))
    if not len(A) or not (len(A) == len(B) == len(C)):
        raise ValueError("Equal nonempty shapes required")
    if any(x < 0 for v in (A, B, C) for x in v) or sum(A) <= 0 or sum(C) <= 0:
        raise ValueError("Nonnegative masses and positive cores required")
    W = sum(A) + sum(B) + sum(C)
    A, B, C = [[x / W for x in v] for v in (A, B, C)]
    P = [a + b + c for a, b, c in zip(A, B, C)]
    lo, hi = sum(A), sum(A) + sum(B)

    def fg(a):
        return (
            sum(max(u - a * p, 0) for u, p in zip(A, P)),
            sum(max(a * p - u - v, 0) for u, v, p in zip(A, B, P)),
        )

    def difference(a):
        f, g = fg(a)
        return f - g

    if difference(lo) <= 0:
        a = lo
    elif difference(hi) >= 0:
        a = hi
    else:
        events = {}
        slope = Fraction(0)
        for u, v, p in zip(A, B, P):
            if p == 0:
                continue
            start, end = u / p, (u + v) / p
            if start > lo:
                slope -= p
            if end <= lo:
                slope -= p
            if lo < start < hi:
                events[start] = events.get(start, 0) + p
            if lo < end < hi:
                events[end] = events.get(end, 0) - p
        left = lo
        value = difference(lo)
        for right in sorted(set(events) | {hi}):
            next_value = value + slope * (right - left)
            if next_value <= 0:
                assert slope < 0
                a = left - value / slope
                break
            value = next_value
            left = right
            slope += events.get(right, 0)
        else:
            raise AssertionError("Exact root not bracketed")
    theta = [a * p - u for u, p in zip(A, P)]
    allocation = [min(max(t, 0), v) for t, v in zip(theta, B)]
    remaining = a - sum(A) - sum(allocation)
    for j in range(len(B)):
        change = (
            min(remaining, B[j] - allocation[j])
            if remaining >= 0
            else -min(-remaining, allocation[j])
        )
        allocation[j] += change
        remaining -= change
    assert remaining == 0 and all(0 <= x <= b for x, b in zip(allocation, B))
    f, g = fg(a)
    value = max(f, g) / (a * (1 - a))
    primal = (
        sum(
            abs((u + x) / a - (c + b - x) / (1 - a))
            for u, b, c, x in zip(A, B, C, allocation)
        )
        / 2
    )
    assert primal == value
    return dict(value=value, left_fraction=a, allocation=[x * W for x in allocation])
