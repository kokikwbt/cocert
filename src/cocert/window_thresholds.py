"""Certified queries with one tolerance per scale and optional known split total."""

from decimal import Decimal, localcontext
from fractions import Fraction as F
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from .backends.full import threshold_residual
from .backends.fixed_certificates import repair, single_optimum
from ._split import minimum_exact
from .verify_window_thresholds import verify
from .queries import (
    calibration_inputs,
    fraction_arrays,
    normalize,
    rounded_threshold,
    split_total,
    thresholds,
)


def calibrated(q, effect="0", alpha="1/20", total=None, denominator=1000000):
    A, B, C, effect, alpha, s = calibration_inputs(q, effect, alpha, total, denominator)
    K, M = len(A), len(B)
    b = sum(B)
    if M == 1:
        return [rounded_threshold(effect, 0, denominator)] * K
    with localcontext() as ctx:
        ctx.prec = 80
        ratio = F(2 * K * ((1 << M) - 2)) / F(alpha)
        log = (Decimal(ratio.numerator) / Decimal(ratio.denominator)).ln()
        values = []
        for a, c in zip(A, C):
            L = sum(a) + (s if s is not None else 0)
            R = sum(c) + (b - s if s is not None else 0)
            deltas = []
            for n in [L, R]:
                d = (log * Decimal(n.denominator) / (2 * Decimal(n.numerator))).sqrt()
                deltas.append(d)
            values.append(rounded_threshold(effect, sum(deltas), denominator))
        return values


def known_candidate(A, B, C, s, es):
    scale = B.sum()
    A, B, C, s = A / scale, B / scale, C / scale, float(s) / scale
    K, M = A.shape
    N = K * M
    L, R = A.sum(1) + s, C.sum(1) + B.sum() - s
    constant = A / L[:, None] - (C + B) / R[:, None]
    coef = 1 / L + 1 / R
    kk = np.repeat(np.arange(K), M)
    jj = np.tile(np.arange(M), K)
    z = np.arange(N)
    matrix = sparse.csc_matrix(
        (
            np.r_[
                coef[kk],
                -np.ones(N),
                -coef[kk],
                -np.ones(N),
                np.full(N, 0.5),
                -np.ones(K),
            ],
            (
                np.r_[z, z, N + z, N + z, 2 * N + kk, 2 * N + np.arange(K)],
                np.r_[jj, M + z, jj, M + z, M + z, np.full(K, M + N)],
            ),
        ),
        shape=(2 * N + K, M + N + 1),
    )
    equality = sparse.csc_matrix(
        (np.ones(M), (np.zeros(M, int), np.arange(M))), shape=(1, M + N + 1)
    )
    r = linprog(
        np.r_[np.zeros(M + N), 1.0],
        A_ub=matrix,
        b_ub=np.r_[-constant.ravel(), constant.ravel(), es],
        A_eq=equality,
        b_eq=[s],
        bounds=[(0, b) for b in B] + [(0, None)] * N + [(None, None)],
        method="highs",
    )
    if not r.success:
        raise RuntimeError(r.message)
    dual = -r.ineqlin.marginals
    w = np.maximum(dual[2 * N :], 0)
    al = np.divide(
        2 * (dual[:N] - dual[N : 2 * N]).reshape(K, M),
        w[:, None],
        out=np.zeros((K, M)),
        where=w[:, None] > 1e-12,
    )
    return dict(
        allocation=np.clip(r.x[:M], 0, B) * scale,
        weights=w / w.sum(),
        subgradients=np.clip(al, -1, 1),
    )


def support(A, B, C, es, total, r, den):
    w = [max(F(0), F(float(v)).limit_denominator(den)) for v in r["weights"]]
    if not sum(w):
        return None
    z = sum(w)
    w = [v / z for v in w]
    als = [
        [max(F(-1), min(F(1), F(float(v)).limit_denominator(den))) for v in row]
        for row in r["subgradients"]
    ]
    constant = F(0)
    grad = [F(0)] * len(B)
    Q = F(0)
    for a, c, z, al, e in zip(A, C, w, als, es):
        if total is not None:
            L, R = sum(a) + total, sum(c) + sum(B) - total
            constant += z * (
                sum(t * (u / L - (v + b) / R) for u, v, b, t in zip(a, c, B, al)) / 2
                - e
            )
            for j in range(len(B)):
                grad[j] += z * al[j] * (1 / L + 1 / R) / 2
        else:
            W = sum(a) + sum(B) + sum(c)
            ac = sum(a)
            P = [u + b + v for u, b, v in zip(a, B, c)]
            dot = sum(t * v for t, v in zip(al, P))
            Q += e * z / W**2
            constant += z * (
                sum(t * u for t, u in zip(al, a)) / (2 * W)
                - ac * dot / (2 * W**2)
                + e * ac * (ac - W) / W**2
            )
            for j in range(len(B)):
                grad[j] += z * (
                    al[j] / (2 * W) - dot / (2 * W**2) + e * (2 * ac - W) / W**2
                )
    p = dict(
        kind="support",
        weights=list(map(str, w)),
        alpha=[list(map(str, r)) for r in als],
    )
    if total is not None:
        remaining = total
        bound = constant
        for j in sorted(range(len(B)), key=lambda j: grad[j]):
            amount = min(B[j], remaining)
            remaining -= amount
            bound += amount * grad[j]
    else:
        mass = cost = F(0)
        best = None
        s = F(0)
        for j in sorted(range(len(B)), key=lambda j: grad[j]):
            end = mass + B[j]
            candidate = max(mass, min(end, -grad[j] / (2 * Q))) if Q else mass
            value = Q * candidate**2 + cost + grad[j] * (candidate - mass)
            if best is None or value < best:
                best = value
                s = candidate
            cost += grad[j] * B[j]
            mass = end
        bound = (
            constant
            - Q * s * s
            + sum(b * min(F(0), g + 2 * Q * s) for b, g in zip(B, grad))
        )
        p["tangent_total"] = str(s)
    p["bound"] = str(bound)
    return p if bound > 0 else None


def decide(q, epsilon, total=None, singles=None):
    q = normalize(q)
    A, B, C = fraction_arrays(q)
    es = thresholds(epsilon, len(A))
    total = split_total(total, B)
    common = dict(
        epsilon=list(map(str, es)), total=None if total is None else str(total)
    )
    if singles is None:
        singles = [
            (
                minimum_exact(a, B, c)
                if total is None
                else dict(zip(["value", "allocation"], single_optimum(a, B, c, total)))
            )
            for a, c in zip(A, C)
        ]
    sep = any(F(s["value"]) > e for s, e in zip(singles, es))
    if sep:
        k = next(k for k, (s, e) in enumerate(zip(singles, es)) if F(s["value"]) > e)
        p = dict(
            common,
            kind="single",
            scale=k,
            value=str(singles[k]["value"]),
            allocation=list(map(str, singles[k]["allocation"])),
        )
        if verify(q, p, epsilon=es, total=total) is not True:
            raise AssertionError("Positive status/proof mismatch")
        return dict(status="positive", separate=True, stage="single", proof=p)

    def feasible(x):
        p = dict(common, kind="feasible", allocation=list(map(str, x)))
        try:
            if verify(q, p, epsilon=es, total=total) is not False:
                raise AssertionError("Negative status/proof mismatch")
        except AssertionError:
            return None
        return dict(status="negative", separate=False, stage="feasible", proof=p)

    for x in [[b * t for b in B] for t in [F(1, 2), F(0), F(1)]] + [
        list(map(F, s["allocation"])) for s in singles
    ]:
        if total is not None:
            x = repair(x, B, total)
        a = feasible(x)
        if a:
            return a
    aa, bb, cc = [np.array(v, float) for v in [A, B, C]]
    try:
        r = (
            threshold_residual(aa, bb, cc, epsilon=np.array(es, float))
            if total is None
            else known_candidate(aa, bb, cc, total, np.array(es, float))
        )
    except RuntimeError as err:
        return dict(status="undecided", separate=False, proof=None, stage=str(err))
    for den in [10**6, 10**9, 10**12, 10**16]:
        x = [
            max(F(0), min(b, F(float(v)).limit_denominator(den)))
            for b, v in zip(B, r["allocation"])
        ]
        if total is not None:
            x = repair(x, B, total)
        a = feasible(x)
        if a:
            a["stage"] = "solver"
            return a
        p = support(A, B, C, es, total, r, den)
        if p:
            p.update(common)
            if verify(q, p, epsilon=es, total=total) is not True:
                raise AssertionError("Positive status/proof mismatch")
            return dict(status="positive", separate=False, stage="solver", proof=p)
    return dict(
        status="undecided", separate=False, proof=None, stage="rational_recovery"
    )
