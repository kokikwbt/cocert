"""Standard sparse LP for shared multiscale TV with a known cut mass."""

import numpy as np
from scipy import sparse
from scipy.optimize import linprog


def minimum_shared_tv(before, boundary, after, left_mass):
    A, B, C = (np.asarray(v, float) for v in (before, boundary, after))
    if A.ndim != 2 or A.shape != C.shape or B.shape != (A.shape[1],):
        raise ValueError("Common bins required")
    if any(not np.isfinite(v).all() or (v < 0).any() for v in (A, B, C)):
        raise ValueError("Nonnegative finite inputs required")
    scale = B.sum()
    s = float(left_mass)
    if scale <= 0 or not 0 <= s <= scale or min(A.sum(1)) <= 0 or min(C.sum(1)) <= 0:
        raise ValueError("Positive cores and feasible cut mass required")
    A, B, C, s = A / scale, B / scale, C / scale, s / scale
    K, M = A.shape
    N = K * M
    left, right = A.sum(1) + s, C.sum(1) + B.sum() - s
    constant = A / left[:, None] - (C + B) / right[:, None]
    coefficient = 1 / left + 1 / right
    kk = np.repeat(np.arange(K), M)
    jj = np.tile(np.arange(M), K)
    z = np.arange(N)
    rows = np.r_[z, z, N + z, N + z, 2 * N + kk, 2 * N + np.arange(K)]
    cols = np.r_[jj, M + z, jj, M + z, M + z, np.full(K, M + N)]
    vals = np.r_[
        coefficient[kk],
        -np.ones(N),
        -coefficient[kk],
        -np.ones(N),
        np.full(N, 0.5),
        -np.ones(K),
    ]
    matrix = sparse.csc_matrix((vals, (rows, cols)), shape=(2 * N + K, M + N + 1))
    equality = sparse.csc_matrix(
        (np.ones(M), (np.zeros(M, int), np.arange(M))), shape=(1, M + N + 1)
    )
    objective = np.r_[np.zeros(M + N), 1.0]
    r = linprog(
        objective,
        A_ub=matrix,
        b_ub=np.r_[-constant.ravel(), constant.ravel(), np.zeros(K)],
        A_eq=equality,
        b_eq=[s],
        bounds=[(0, b) for b in B] + [(0, None)] * N + [(0, 1)],
        method="highs",
        options={
            "dual_feasibility_tolerance": 1e-9,
            "primal_feasibility_tolerance": 1e-9,
        },
    )
    if not r.success:
        raise RuntimeError(r.message)
    dual = -r.ineqlin.marginals
    weights = np.maximum(dual[2 * N :], 0)
    alpha = np.divide(
        2 * (dual[:N] - dual[N : 2 * N]).reshape(K, M),
        weights[:, None],
        out=np.zeros((K, M)),
        where=weights[:, None] > 1e-12,
    )
    if weights.sum() > 0:
        weights /= weights.sum()
    return dict(
        value=float(r.fun),
        allocation=np.clip(r.x[:M], 0, B) * scale,
        weights=weights,
        subgradients=np.clip(alpha, -1, 1),
        iterations=r.nit,
    )
