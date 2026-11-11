"""Shared sparse construction and solution of the paper's single-cone query.

Full SOCP and Decision SOCP have identical constraints and proof recovery.
Only Decision SOCP permits the sign-based early termination callback.
"""

import time
import numpy as np
from scipy import sparse
import clarabel


def solve(before, boundary, after, epsilon=0.1, *, stop_on_decision=False):
    """Propose primal/dual witnesses for the normalized convex residual.

    Variables are [x (M), absolute residuals (K*M), s, v, delta]. The equality
    fixes s=sum(x); one second-order cone enforces v >= s**2. Delta bounds
    every window residual. Row balancing changes conditioning, not feasibility.
    Rational recovery and verification are performed outside this function.
    """
    started = time.perf_counter()
    A, B, C = (np.asarray(v, float) for v in (before, boundary, after))
    if A.ndim != 2 or A.shape != C.shape or B.shape != (A.shape[1],):
        raise ValueError("Common bins required")
    if any(not np.isfinite(v).all() or (v < 0).any() for v in (A, B, C)):
        raise ValueError("Nonnegative finite inputs required")
    if min(A.sum(1)) <= 0 or min(C.sum(1)) <= 0 or B.sum() <= 0:
        raise ValueError("Positive cores and boundary required")
    scale = B.sum()
    A, B, C = A / scale, B / scale, C / scale
    K, M = A.shape
    N = K * M
    n = M + N + 3
    si, vi, di = n - 3, n - 2, n - 1
    ac = A.sum(1)
    cc = C.sum(1)
    bc = B.sum()
    W = ac + bc + cc
    P = A + B + C
    product_min = np.minimum(ac * (cc + bc), (ac + bc) * cc)
    T = 1 / product_min
    # Equality, two box inequalities per bin, two absolute-value rows per (k,j), K epigraph rows, one cone.
    kk = np.repeat(np.arange(K), M)
    jj = np.tile(np.arange(M), K)
    j = np.arange(M)
    pos = 1 + 2 * M + np.arange(N)
    neg = pos + N
    groups = 1 + 2 * M + 2 * N + np.arange(K)
    soc = 1 + 2 * M + 2 * N + K
    rows_count = soc + 3
    rows = np.r_[
        np.zeros(M + 1, int),
        1 + j,
        1 + M + j,
        pos,
        pos,
        pos,
        neg,
        neg,
        neg,
        1 + 2 * M + 2 * N + kk,
        groups,
        groups,
        groups,
        soc,
        soc + 1,
        soc + 2,
    ]
    cols = np.r_[
        j,
        si,
        j,
        j,
        jj,
        np.full(N, si),
        M + np.arange(N),
        jj,
        np.full(N, si),
        M + np.arange(N),
        M + np.arange(N),
        np.full(K, si),
        np.full(K, vi),
        np.full(K, di),
        vi,
        si,
        vi,
    ]
    values = np.r_[
        -np.ones(M),
        1.0,
        -np.ones(M),
        np.ones(M),
        T[kk] * W[kk],
        -T[kk] * P.ravel(),
        -np.ones(N),
        -T[kk] * W[kk],
        T[kk] * P.ravel(),
        -np.ones(N),
        np.full(N, 0.5),
        epsilon * T * (ac - cc - bc),
        epsilon * T,
        -np.ones(K),
        -1.0,
        -2.0,
        -1.0,
    ]
    matrix = sparse.csc_matrix((values, (rows, cols)), shape=(rows_count, n))
    matrix.eliminate_zeros()
    nc = (T[:, None] * (A * (cc + bc)[:, None] - ac[:, None] * (C + B))).ravel()
    rhs = np.r_[
        0.0, np.zeros(M), B, -nc, nc, epsilon * T * ac * (cc + bc), 1.0, 0.0, -1.0
    ]
    objective = np.zeros(n)
    objective[di] = 1
    cones = [
        clarabel.ZeroConeT(1),
        clarabel.NonnegativeConeT(soc - 1),
        clarabel.SecondOrderConeT(3),
    ]
    settings = clarabel.DefaultSettings()
    settings.verbose = False
    settings.max_threads = 1
    settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-10
    assembly = time.perf_counter() - started
    tick = time.perf_counter()
    solver = clarabel.DefaultSolver(
        sparse.csc_matrix((n, n)), objective, matrix, rhs, cones, settings
    )
    if stop_on_decision:
        solver.set_termination_callback(
            lambda info: info.iterations >= 2
            and max(info.res_primal, info.res_dual) < 1e-10
            and (info.cost_dual > 1e-8 or info.cost_primal < -1e-8)
        )
    setup = time.perf_counter() - tick
    tick = time.perf_counter()
    result = solver.solve()
    solve_seconds = time.perf_counter() - tick
    accepted = ("Solved", "AlmostSolved")
    if stop_on_decision:
        accepted += ("CallbackTerminated",)
    if str(result.status) not in accepted:
        raise RuntimeError(str(result.status))
    x = np.clip(np.asarray(result.x[:M]), 0, B)
    s = x.sum()
    left = ac + s
    right = cc + bc - s
    residual = T * (
        0.5 * np.abs((A + x) * right[:, None] - (C + B - x) * left[:, None]).sum(1)
        - epsilon * left * right
    )
    z = np.asarray(result.z)
    lam = np.maximum(z[groups], 0)
    alpha = np.divide(
        2 * (z[pos] - z[neg]).reshape(K, M),
        lam[:, None],
        out=np.zeros((K, M)),
        where=lam[:, None] > 1e-12,
    )
    lam *= W**2 * T  # Map scaled row weights back to the original g_k support.
    if lam.sum() > 0:
        lam /= lam.sum()
    return dict(
        value=float(result.obj_val),
        lower=float(result.obj_val_dual),
        upper=float(residual.max()),
        allocation=x * scale,
        weights=lam,
        subgradients=np.clip(alpha, -1, 1),
        status=str(result.status),
        residual_scaling="inverse_minimum_fraction",
        iterations=result.iterations,
        variables=n,
        constraints=rows_count,
        nnz=matrix.nnz,
        matrix_bytes=matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes,
        assembly_seconds=assembly,
        setup_seconds=setup,
        solve_seconds=solve_seconds,
        internal_solve_seconds=result.solve_time,
        seconds=time.perf_counter() - started,
    )
