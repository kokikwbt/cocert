"""Adaptive subdivision using the normalized TV LPs and Lipschitz bounds."""

from fractions import Fraction
import heapq
import time

from ..tv_query_common import fractions, solve_fixed


def search(query, epsilon, *, backend="highs", time_limit=1.0, max_calls=129):
    """Certify the same predicate as the grid by refining unresolved intervals."""
    start = time.process_time()
    before, boundary, after = fractions(query)
    mass = sum(boundary)
    core_totals = [(sum(a), sum(c)) for a, c in zip(before, after)]
    model = None
    calls = 0
    checked = []
    queue = [(Fraction(-1), Fraction(0), mass)]
    try:
        while queue and calls < max_calls:
            remaining = time_limit - (time.process_time() - start)
            if remaining <= 0:
                break
            _, lo, hi = heapq.heappop(queue)
            total = (lo + hi) / 2
            if backend == "highs":
                result = solve_fixed(query, total, epsilon, remaining)
            elif backend == "gurobi":
                if model is None:
                    from .gurobi import ConditionalLP

                    model = ConditionalLP(query, total, epsilon)
                result = model.solve(total, remaining)
            else:
                raise ValueError(f"Unknown LP backend: {backend}")
            calls += 1
            if result["status"] == "negative":
                return dict(result, lp_calls=calls, route="verified_allocation")
            if "lower" not in result or lo == hi:
                return dict(status="undecided" if "lower" not in result else result["status"],
                            lp_calls=calls, route="point")
            lower = Fraction(result["lower"])
            for left, right in ((lo, total), (total, hi)):
                lipschitz = max(1 / (a + left) + 1 / (c + mass - right)
                                for a, c in core_totals)
                bound = lower - lipschitz * (right - left)
                if bound > 0:
                    checked.append(bound)
                else:
                    heapq.heappush(queue, (bound, left, right))
        if queue:
            return dict(status="undecided", lp_calls=calls, route="interval_budget")
        return dict(status="positive", lower=str(min(checked)), lp_calls=calls,
                    route="verified_interval_cover")
    finally:
        if model is not None:
            model.close()
