"""Deterministic distribution contrasts across one unrecorded histogram cut.

The mass coordinate refers to delivered nonnegative histogram values. It need
not be physical time or a count of independent observations.
"""

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SplitHistogram:
    before: np.ndarray
    boundary: np.ndarray
    after: np.ndarray
    left_mass: float

    def normalized(self):
        arrays = [
            np.asarray(v, dtype=float) for v in (self.before, self.boundary, self.after)
        ]
        if (
            any(v.ndim != 1 or not len(v) for v in arrays)
            or any(v.shape != arrays[0].shape for v in arrays)
            or any(not np.isfinite(v).all() or (v < 0).any() for v in arrays)
        ):
            raise ValueError("Finite, nonnegative vectors of one common shape required")
        scale = sum(float(v.sum()) for v in arrays)
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("Positive total mass required")
        A, B, C = (v / scale for v in arrays)
        s = float(self.left_mass) / scale
        if not np.isfinite(s) or s < -1e-12 or s > B.sum() + 1e-12:
            raise ValueError("Boundary mass outside feasible range")
        s = float(np.clip(s, 0, B.sum()))
        a, b = float(A.sum() + s), float(C.sum() + B.sum() - s)
        if a <= 0 or b <= 0:
            raise ValueError("Both sides must have positive mass")
        coefficient = 1 / a + 1 / b
        theta = ((C + B) / b - A / a) / coefficient
        return A, B, C, s, a, b, coefficient, theta, scale


def allocate_mass(capacity, mass, order=None):
    """An extreme feasible allocation, in the given priority order."""
    capacity = np.asarray(capacity, float)
    order = np.arange(len(capacity)) if order is None else np.asarray(order)
    preceding = np.r_[0.0, np.cumsum(capacity[order])[:-1]]
    result = np.zeros_like(capacity)
    result[order] = np.minimum(capacity[order], np.maximum(0.0, mass - preceding))
    return result


def minimum_tv(problem):
    """Sharp minimum and an attaining allocation in O(number of bins)."""
    A, B, C, s, a, b, coefficient, theta, scale = problem.normalized()
    clipped = np.clip(theta, 0, B)
    mismatch = s - float(clipped.sum())
    x = clipped.copy()
    if mismatch >= 0:
        x += allocate_mass(B - x, mismatch)
    else:
        x -= allocate_mass(x, -mismatch)
    value = 0.5 * coefficient * (float(np.abs(clipped - theta).sum()) + abs(mismatch))
    return dict(value=float(value), allocation=x * scale)


def minimum_unrecorded_cut(before, boundary, after):
    """Sharp minimum with neither bin values nor total mass at the cut.

    Positive known mass on both sides is required. Two monotone envelopes
    cross at the optimum; sweep their at most 2M breakpoints in O(M log M).
    No clock-to-exposure interpolation or scalar stream is required.
    """
    raw_B = np.asarray(boundary, float)
    initial = SplitHistogram(before, raw_B, after, float(raw_B.sum() / 2))
    A, B, C, s, a, b, coefficient, theta, scale = initial.normalized()
    lower_a, upper_a = float(A.sum()), float(A.sum() + B.sum())
    if lower_a <= 0 or C.sum() <= 0:
        raise ValueError("Positive observed core mass required on both sides")
    P = A + B + C  # total normalized mass is one

    def difference(a):
        return float(
            np.maximum(A - a * P, 0).sum() - np.maximum(a * P - A - B, 0).sum()
        )

    if difference(lower_a) <= 0:
        best_a = lower_a
    elif difference(upper_a) >= 0:
        best_a = upper_a
    else:
        positive = P > 0
        starts = A[positive] / P[positive]
        ends = (A[positive] + B[positive]) / P[positive]
        positions = np.r_[starts, ends]
        changes = np.r_[P[positive], -P[positive]]
        keep = (positions > lower_a) & (positions < upper_a)
        order = np.argsort(positions[keep], kind="stable")
        positions, changes = positions[keep][order], changes[keep][order]
        # Use identical rounded breakpoints for initial membership and events.
        slope = -float(
            P[positive][starts > lower_a].sum() + P[positive][ends <= lower_a].sum()
        )
        previous, value = lower_a, difference(lower_a)
        best_a = upper_a
        for point, change in zip(np.r_[positions, upper_a], np.r_[changes, 0.0]):
            next_value = value + slope * float(point - previous)
            if next_value <= 0:
                best_a = previous - value / slope if slope < 0 else previous
                break
            previous, value = float(point), next_value
            slope += float(change)

    # Use bisection when the two crossing envelopes disagree beyond tolerance.
    def envelopes(a):
        denominator = a * (1 - a)
        return (
            float(np.maximum(A - a * P, 0).sum() / denominator),
            float(np.maximum(a * P - A - B, 0).sum() / denominator),
        )

    f1, f2 = envelopes(best_a)
    interior = difference(lower_a) > 0 and difference(upper_a) < 0
    fallback = bool(interior and abs(f1 - f2) > 1e-10)
    if fallback:
        lo, hi = lower_a, upper_a
        for _ in range(64):
            mid = (lo + hi) / 2
            if difference(mid) > 0:
                lo = mid
            else:
                hi = mid
        best_a = (lo + hi) / 2
        f1, f2 = envelopes(best_a)
    best_s = float(np.clip(best_a - lower_a, 0, B.sum()))
    problem = SplitHistogram(
        np.asarray(before), np.asarray(boundary), np.asarray(after), best_s * scale
    )
    result = minimum_tv(problem)
    result["optimization_upper"] = result["value"]
    # The smaller envelope bounds the interior optimum from below.
    # At a boundary optimum, the active envelope is exact.
    if interior:
        result["value"] = min(f1, f2, result["optimization_upper"])
    result["optimization_gap"] = max(
        0.0, result["optimization_upper"] - result["value"]
    )
    result["bisection_fallback"] = fallback
    result["left_mass"] = best_s * scale
    return result
