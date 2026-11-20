"""Common-completion checks and tangent supports before the conic fallback."""

import time
import numpy as np
from .backends import full


def maximum_pair_support(c1, d1, c2, d2, boundary):
    """Maximize the concave box bound over a two-support mixture."""
    change = d1 - d2
    active = (d2 < 0) | ((d2 == 0) & (change < 0))
    slope = float(c1 - c2 + (boundary * change * active).sum())
    weight = 0.0
    if slope > 0:
        nonzero = change != 0
        points = np.divide(-d2, change, out=np.zeros_like(d2), where=nonzero)
        interior = nonzero & (points > 0) & (points < 1)
        order = np.argsort(points[interior], kind="stable")
        points = points[interior][order]
        drops = (boundary[interior] * abs(change[interior]))[order]
        index = int(np.searchsorted(np.cumsum(drops), slope, side="left"))
        weight = 1.0 if index == len(points) else float(points[index])
    bound = weight * c1 + (1 - weight) * c2
    bound += float((boundary * np.minimum(0, weight * d1 + (1 - weight) * d2)).sum())
    return bound, weight


def ranked_pairs(gamma, limit=5):
    """Enumerate rank-position pairs, breaking score ties by input index."""
    scales = np.argsort(-np.asarray(gamma), kind="stable")[:limit]
    return [
        (int(first), int(second))
        for index, first in enumerate(scales)
        for second in scales[index + 1 :]
    ]


def threshold(
    before, boundary, after, epsilon=0.1, solver="socp", max_iterations=8, pair_scales=5,
    conic_candidate=None,
):
    """Propose an Algorithm 1 decision; exact recovery/checking is separate."""
    started = time.perf_counter()
    A, B, C = [np.asarray(v, float) for v in [before, boundary, after]]
    K, M = A.shape
    scale = B.sum()
    a, b, c = A / scale, B / scale, C / scale
    W = (a + b + c).sum(1)
    ac = a.sum(1)
    P = a + b + c

    def residual(x):
        p = a + x
        q = c + b - x
        return (
            0.5 * abs(p / p.sum(1, keepdims=True) - q / q.sum(1, keepdims=True)).sum(1)
            - epsilon
        )

    # A common midpoint can certify low change.
    point = b * 0.5
    g = residual(point)
    if g.max() < -1e-8:
        return dict(
            found=False,
            kind="feasible",
            stage="midpoint",
            allocation=point * scale,
            seconds=time.perf_counter() - started,
            solver_called=False,
        )
    # Tangent bounds rank the windows for refinement.
    s0 = 0.5
    nc = a / W[:, None] - ac[:, None] * P / W[:, None] ** 2
    nn = nc + point / W[:, None] - s0 * P / W[:, None] ** 2
    alpha = np.where(nn >= 0, 1.0, -1.0)
    dot = (alpha * P).sum(1)
    d = (
        0.5 * (alpha / W[:, None] - dot[:, None] / W[:, None] ** 2)
        + epsilon * (2 * ac - W + 2 * s0)[:, None] / W[:, None] ** 2
    )
    intercept = 0.5 * (alpha * nc).sum(1) + epsilon * (ac**2 - ac * W - s0**2) / W**2
    gamma = intercept + (b * np.minimum(0, d)).sum(1)
    best = int(np.argmax(gamma))
    if gamma[best] > 1e-8:
        weights = np.zeros(K)
        weights[best] = 1
        return dict(
            found=True,
            kind="support",
            stage="tangent_single",
            weights=weights,
            subgradients=alpha,
            tangent_total=s0 * scale,
            seconds=time.perf_counter() - started,
            solver_called=False,
        )
    # Try the remaining proportional allocations.
    for f in [0.0, 0.25, 0.75, 1.0]:
        point = b * f
        if residual(point).max() < -1e-8:
            return dict(
                found=False,
                kind="feasible",
                stage="uniform",
                allocation=point * scale,
                seconds=time.perf_counter() - started,
                solver_called=False,
            )
    from ._histogram import minimum_unrecorded_cut

    # Refine windows in descending bound order.
    for k in np.argsort(-gamma, kind="stable"):
        single = minimum_unrecorded_cut(A[k], B, C[k])
        if single["value"] > epsilon + 1e-8:
            return dict(
                found=True,
                kind="single",
                stage="sharp_single",
                scale_index=int(k),
                seconds=time.perf_counter() - started,
                solver_called=False,
            )
        x = np.clip(single["allocation"] / scale, 0, b)
        if residual(x).max() < -1e-8:
            return dict(
                found=False,
                kind="feasible",
                stage="sharp_completion",
                allocation=x * scale,
                seconds=time.perf_counter() - started,
                solver_called=False,
            )
    # Try paired bounds only after the preceding checks fail.
    if pair_scales:
        for first, second in ranked_pairs(gamma, pair_scales):
            bound, weight = maximum_pair_support(
                intercept[first], d[first], intercept[second], d[second], b
            )
            if bound > 1e-8:
                weights = np.zeros(K)
                weights[first], weights[second] = weight, 1 - weight
                return dict(
                    found=True,
                    kind="support",
                    stage="tangent_pair",
                    weights=weights,
                    subgradients=alpha,
                    tangent_total=s0 * scale,
                    seconds=time.perf_counter() - started,
                    solver_called=False,
                )
    # Send unresolved queries to the selected solver.
    if solver == "socp":
        if conic_candidate is None:
            r = full.threshold_residual(A, B, C, epsilon=epsilon)
        else:
            r = conic_candidate(A, B, C, epsilon=epsilon, scores=gamma)
    elif solver == "facets":
        from ._facets import threshold_residual

        r = threshold_residual(A, B, C, epsilon=epsilon, max_iterations=max_iterations)
    else:
        raise ValueError(solver)
    found = r["lower"] > 1e-8
    return dict(
        r,
        found=found,
        kind="support" if found else "feasible",
        stage="solver",
        solver_called=True,
        seconds=time.perf_counter() - started,
    )
