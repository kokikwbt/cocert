"""Z3 feasibility for shared-variable TV constraints.

All windows use one allocation in the specified domain. Known split totals
yield linear constraints. Unknown totals retain nonlinear constraints after
clearing positive denominators.
"""

from fractions import Fraction as F
import time
import z3


def number(value):
    f = F(value)
    return z3.RealVal(f"{f.numerator}/{f.denominator}")


def tolerances(epsilon, count):
    values = list(epsilon) if isinstance(epsilon, (list, tuple)) else [epsilon] * count
    if len(values) != count:
        raise ValueError("One tolerance is required per window")
    result = list(map(F, values))
    if any(v < 0 for v in result):
        raise ValueError("Tolerances must be nonnegative")
    return result


def verify_allocation(q, epsilon, allocation, total=None, domain="real"):
    x = list(map(F, allocation))
    B = list(map(F, q["B"]))
    if len(x) != len(B) or any(not 0 <= z <= b for z, b in zip(x, B)):
        return False
    if domain == "integer" and any(v.denominator != 1 for v in x):
        return False
    if total is not None and sum(x) != F(total):
        return False
    for a, c, eps in zip(q["A"], q["C"], tolerances(epsilon, len(q["A"]))):
        left = [F(v) + z for v, z in zip(a, x)]
        right = [F(v) + b - z for v, b, z in zip(c, B, x)]
        ll, rr = sum(left), sum(right)
        if min(ll, rr) <= 0:
            return False
        if (
            sum(abs(u * rr - v * ll) for u, v in zip(left, right))
            > 2 * eps * ll * rr
        ):
            return False
    return True


def decide(q, epsilon, total=None, timeout_ms=1000, seed=20261020, domain="real"):
    start = time.perf_counter()
    if domain not in {"real", "integer"}:
        raise ValueError("Allocation domain must be real or integer")
    eps = tolerances(epsilon, len(q["A"]))
    b = list(map(F, q["B"]))
    variable = z3.Int if domain == "integer" else z3.Real
    x = [variable(f"x_{j}") for j in range(len(b))]
    s = z3.Real('split_total') if total is None else z3.Sum(x)
    solver = (z3.Solver() if domain == "integer" else
              z3.SolverFor("QF_NRA" if total is None else "QF_LRA"))
    solver.set(random_seed=seed)
    if total is None:
        solver.add(s == z3.Sum(x))
    for v, cap in zip(x, b):
        solver.add(v >= 0, v <= number(cap))
    if total is not None:
        solver.add(s == number(total))
    for k, (a, c) in enumerate(zip(q["A"], q["C"])):
        a, c = list(map(F, a)), list(map(F, c))
        aa, cc, bb = sum(a), sum(c), sum(b)
        if min(aa, cc) <= 0 or min(a + b + c) < 0:
            raise ValueError("Nonnegative masses and positive core totals required")
        # Naming the shared sum avoids repeating its full expression.
        # A supplied total makes all remaining constraints linear.
        scalar = s if total is None else number(total)
        left_total = number(aa) + scalar
        right_total = number(cc + bb) - scalar
        terms = []
        for j, (aj, cj, bj, v) in enumerate(zip(a, c, b, x)):
            u = z3.Real(f"abs_{k}_{j}")
            d = (number(aj) + v) * right_total - (number(cj + bj) - v) * left_total
            solver.add(u >= d, u >= -d)
            terms.append(u)
        solver.add(z3.Sum(terms) <= number(2 * eps[k]) * left_total * right_total)
    construction = time.perf_counter() - start
    remaining = max(1, int(timeout_ms - 1000 * construction))
    solver.set(timeout=remaining)
    mark = time.perf_counter()
    status = solver.check()
    solve = time.perf_counter() - mark
    allocation = None
    verified = False
    reason = None
    if status == z3.sat:
        model = solver.model()
        values = [model.eval(v, model_completion=True) for v in x]
        if all(z3.is_rational_value(v) or z3.is_int_value(v) for v in values):
            allocation = [
                str(F(v.as_long()) if z3.is_int_value(v) else
                    F(v.numerator_as_long(), v.denominator_as_long())) for v in values
            ]
            verified = verify_allocation(q, epsilon, allocation, total, domain)
            if not verified:
                raise ArithmeticError("SMT rational allocation fails exact TV check")
        reason = None if verified else "algebraic_model"
    elif status == z3.unknown:
        reason = solver.reason_unknown()
    return dict(
        status=(
            "positive"
            if status == z3.unsat
            else "negative" if status == z3.sat else "undecided"
        ),
        smt_status=str(status),
        reason=reason,
        allocation=allocation,
        rational_model_verified=verified,
        construction_seconds=construction,
        solve_seconds=solve,
        seconds=time.perf_counter() - start,
        timeout_ms=timeout_ms,
        solver=z3.get_version_string(),
    )
