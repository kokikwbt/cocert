"""Common-completion and single-window filters before SOCP."""

import numpy as np


def simple_two_sided(before, boundary, after, epsilon, minimum_solver, conic_solver):
    A, B, C = (np.asarray(v, float) for v in (before, boundary, after))

    def feasible(x):
        p = A + x
        q = C + B - x
        return bool(
            (
                0.5
                * abs(p / p.sum(1, keepdims=True) - q / q.sum(1, keepdims=True)).sum(1)
                <= epsilon - 1e-8
            ).all()
        )

    for fraction in [0.5, 0.0, 0.25, 0.75, 1.0]:
        x = B * fraction
        if feasible(x):
            return dict(
                found=False,
                kind="feasible",
                stage="simple_uniform",
                allocation=x,
                solver_called=False,
            )
    for k, (a, c) in enumerate(zip(A, C)):
        r = minimum_solver(a, B, c)
        if r["value"] > epsilon + 1e-8:
            return dict(
                found=True,
                kind="single",
                stage="simple_single",
                scale_index=k,
                solver_called=False,
            )
        if feasible(r["allocation"]):
            return dict(
                found=False,
                kind="feasible",
                stage="simple_sharp_completion",
                allocation=r["allocation"],
                solver_called=False,
            )
    r = conic_solver(A, B, C, epsilon=epsilon)
    found = r["lower"] > 1e-8
    return dict(
        r,
        found=found,
        kind="support" if found else "feasible",
        stage="solver",
        solver_called=True,
    )
