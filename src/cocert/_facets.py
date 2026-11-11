"""Section 4.4: replace absolute-value auxiliaries by selected norm facets.

The master retains x (M bin allocations), s (their total), v >= s squared,
and eta (the residual bound). Violated sign facets refine the lower bound;
full residuals at x provide an upper bound. After eight master solves the
sparse SOCP fallback supplies another numerical candidate. Exact checking
is performed by the certificate layer, not by solver tolerances.
"""

import time
import numpy as np
from scipy import sparse
import clarabel
from .backends import full


def threshold_residual(
    before,
    boundary,
    after,
    epsilon=0.1,
    tolerance=1e-9,
    max_iterations=8,
    fallback=True,
):
    started = time.perf_counter()
    A, B, C = [np.asarray(v, float) for v in [before, boundary, after]]
    if A.ndim != 2 or A.shape != C.shape or B.shape != (A.shape[1],):
        raise ValueError("shape")
    if (
        any(not np.isfinite(v).all() or (v < 0).any() for v in [A, B, C])
        or B.sum() <= 0
        or min(A.sum(1)) <= 0
        or min(C.sum(1)) <= 0
    ):
        raise ValueError("positive cores")
    scale = B.sum()
    A, B, C = A / scale, B / scale, C / scale
    K, M = A.shape
    n = M + 3
    si, vi, di = M, M + 1, M + 2
    W = (A + B + C).sum(1)
    ac = A.sum(1)
    P = A + B + C
    D = A * (C.sum(1) + B.sum())[:, None] - ac[:, None] * (C + B)
    T = 1 / np.minimum(ac * (C.sum(1) + B.sum()), (ac + B.sum()) * C.sum(1))
    S = W**2 * T

    def residual(x):
        left = ac + x.sum()
        right = C.sum(1) + B.sum() - x.sum()
        nn = D + W[:, None] * x - x.sum() * P
        return T * (0.5 * abs(nn).sum(1) - epsilon * left * right), nn

    _, nn = residual(B * 0.5)
    cuts = [(k, np.where(nn[k] >= 0, 1.0, -1.0)) for k in range(K)]
    seen = {(k, tuple(sign)) for k, sign in cuts}
    objective = np.zeros(n)
    objective[di] = 1.0
    settings = clarabel.DefaultSettings()
    settings.verbose = False
    settings.max_threads = 1
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-10
    best_upper = np.inf
    best_x = None
    assembly = solve_seconds = setup_seconds = 0.0
    conic_iterations = 0
    history = []
    last = None
    for iteration in range(max_iterations):
        tick = time.perf_counter()
        F = len(cuts)
        ks = np.array([k for k, sign in cuts])
        alpha = np.stack([sign for k, sign in cuts])
        facets = 1 + 2 * M + np.arange(F)
        soc = 1 + 2 * M + F
        rr = np.r_[
            np.zeros(M + 1, int),
            1 + np.arange(M),
            1 + M + np.arange(M),
            np.repeat(facets, M),
            facets,
            facets,
            facets,
            soc,
            soc + 1,
            soc + 2,
        ]
        cc = np.r_[
            np.arange(M),
            si,
            np.arange(M),
            np.arange(M),
            np.tile(np.arange(M), F),
            np.full(F, si),
            np.full(F, vi),
            np.full(F, di),
            vi,
            si,
            vi,
        ]
        dot = (alpha * P[ks]).sum(1)
        vv = np.r_[
            -np.ones(M),
            1.0,
            -np.ones(M),
            np.ones(M),
            (0.5 * alpha * T[ks, None] * W[ks, None]).ravel(),
            -0.5 * dot * T[ks] + epsilon * (2 * ac[ks] - W[ks]) * T[ks],
            epsilon * T[ks],
            -np.ones(F),
            -1.0,
            -2.0,
            -1.0,
        ]
        matrix = sparse.csc_matrix((vv, (rr, cc)), shape=(soc + 3, n))
        matrix.eliminate_zeros()
        rhs = np.r_[
            0.0,
            np.zeros(M),
            B,
            T[ks]
            * (epsilon * ac[ks] * (W[ks] - ac[ks]) - 0.5 * (alpha * D[ks]).sum(1)),
            1.0,
            0.0,
            -1.0,
        ]
        assembly += time.perf_counter() - tick
        tick = time.perf_counter()
        solver = clarabel.DefaultSolver(
            sparse.csc_matrix((n, n)),
            objective,
            matrix,
            rhs,
            [
                clarabel.ZeroConeT(1),
                clarabel.NonnegativeConeT(soc - 1),
                clarabel.SecondOrderConeT(3),
            ],
            settings,
        )
        setup_seconds += time.perf_counter() - tick
        tick = time.perf_counter()
        result = solver.solve()
        solve_seconds += time.perf_counter() - tick
        conic_iterations += result.iterations
        if str(result.status) not in ["Solved", "AlmostSolved"]:
            break
        x = np.clip(np.asarray(result.x[:M]), 0, B)
        g, nn = residual(x)
        lower = float(result.obj_val_dual)
        upper = float(g.max())
        if upper < best_upper:
            best_upper = upper
            best_x = x.copy()
        weight = np.maximum(np.asarray(result.z)[facets], 0)
        lam = np.zeros(K)
        subgradient = np.zeros((K, M))
        for i, k in enumerate(ks):
            lam[k] += weight[i]
            subgradient[k] += weight[i] * alpha[i]
        subgradient = np.divide(
            subgradient,
            lam[:, None],
            out=np.zeros_like(subgradient),
            where=lam[:, None] > 1e-12,
        )
        lam *= S
        if lam.sum() > 0:
            lam /= lam.sum()
        last = dict(
            lower=lower,
            upper=best_upper,
            allocation=best_x * scale,
            weights=lam,
            subgradients=np.clip(subgradient, -1, 1),
            iterations=iteration + 1,
            facets=F,
            variables=n,
            constraints=matrix.shape[0],
            nnz=matrix.nnz,
            matrix_bytes=matrix.data.nbytes
            + matrix.indices.nbytes
            + matrix.indptr.nbytes,
            fallback=False,
            assembly_seconds=assembly,
            setup_seconds=setup_seconds,
            solve_seconds=solve_seconds,
            conic_iterations=conic_iterations,
        )
        history.append(dict(facets=F, lower=lower, upper=best_upper))
        if lower > 1e-8 or best_upper < -1e-8 or best_upper - lower < tolerance:
            return dict(last, seconds=time.perf_counter() - started, history=history)
        added = False
        for k in range(K):
            if g[k] <= float(result.obj_val) + tolerance:
                continue
            sign = np.where(nn[k] >= 0, 1.0, -1.0)
            key = (k, tuple(sign))
            if key not in seen:
                cuts.append((k, sign))
                seen.add(key)
                added = True
        if not added:
            break
    if fallback:
        r = full.threshold_residual(A * scale, B * scale, C * scale, epsilon=epsilon)
        return dict(
            r,
            facets=len(cuts),
            fallback=True,
            facet_iterations=len(history),
            history=history,
            seconds=time.perf_counter() - started,
            assembly_seconds=assembly + r["assembly_seconds"],
            setup_seconds=setup_seconds + r["setup_seconds"],
            solve_seconds=solve_seconds + r["solve_seconds"],
            conic_iterations=conic_iterations + r["iterations"],
            master_variables=n,
            master_nnz=matrix.nnz,
            master_matrix_bytes=matrix.data.nbytes
            + matrix.indices.nbytes
            + matrix.indptr.nbytes,
        )
    if last is None:
        raise RuntimeError("facet master failed")
    return dict(
        last, seconds=time.perf_counter() - started, history=history, unresolved=True
    )
