"""Decision SOCP control: the common formulation with early sign termination."""

from .conic import solve


def threshold_residual(before, boundary, after, epsilon=0.1):
    return solve(before, boundary, after, epsilon, stop_on_decision=True)
