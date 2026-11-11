"""Exact integer-completion decisions with independently checkable search trees.

The fixed-total resource bound is discrete convex. Numerical solvers are unused.
"""

from fractions import Fraction as F
import hashlib
import json
from .queries import thresholds


def model(q):
    A = [[F(v) for v in row] for row in q["A"]]
    B = list(map(F, q["B"]))
    C = [[F(v) for v in row] for row in q["C"]]
    if not A or len(A) != len(C) or not B or any(len(r) != len(B) for r in A + C):
        raise ValueError("Common nonempty bin arrays required")
    if (
        any(v < 0 or v.denominator != 1 for row in A + [B] + C for v in row)
        or min(map(sum, A + C)) <= 0
    ):
        raise ValueError("Integral nonnegative counts and positive cores required")
    A = [[int(v) for v in row] for row in A]
    B = list(map(int, B))
    C = [[int(v) for v in row] for row in C]
    active = [j for j, b in enumerate(B) if b]
    aa = list(map(sum, A))
    cc = list(map(sum, C))
    bc = sum(B)
    digest = hashlib.sha256(
        json.dumps([A, B, C], separators=(",", ":")).encode()
    ).hexdigest()
    return dict(
        A=A,
        B=B,
        C=C,
        active=active,
        a=aa,
        c=cc,
        b=bc,
        W=[a + bc + c for a, c in zip(aa, cc)],
        digest=digest,
    )


def full_allocation(m, x):
    z = [0] * len(m["B"])
    for j, v in zip(m["active"], x):
        z[j] = int(v)
    return z


def low(m, x, es):
    s = sum(x)
    bb = m["B"]
    if len(x) != len(bb) or any(
        v < 0 or v > b or not isinstance(v, int) for v, b in zip(x, bb)
    ):
        return False
    for a, c, ac, cc, e in zip(m["A"], m["C"], m["a"], m["c"], es):
        L, R = ac + s, cc + m["b"] - s
        value = sum(
            abs((u + v) * R - (w + cap - v) * L) for u, w, cap, v in zip(a, c, bb, x)
        )
        if value * e.denominator > 2 * e.numerator * L * R:
            return False
    return True


def resource_minimum(W, D, offset, lo, hi, S):
    """At most three constant marginal runs per coordinate; no unit expansion."""
    x = lo[:]
    need = S - sum(lo)
    if need < 0 or S > sum(hi):
        return None
    segments = []
    value = offset + sum(abs(W * v + d) for v, d in zip(lo, D))
    for j, (l, u, d) in enumerate(zip(lo, hi, D)):
        crossing = (-d) // W
        cuts = sorted({l, u, max(l, min(u, crossing)), max(l, min(u, crossing + 1))})
        for begin, end in zip(cuts, cuts[1:]):
            if begin < end:
                segments.append(
                    (
                        abs(W * (begin + 1) + d) - abs(W * begin + d),
                        j,
                        begin,
                        end - begin,
                    )
                )
    for slope, j, begin, count in sorted(segments):
        take = min(need, count)
        if take:
            assert x[j] == begin
            x[j] += take
            value += take * slope
            need -= take
        if not need:
            break
    assert need == 0 and sum(x) == S
    return value, x


def decide(
    q,
    epsilon="1/10",
    *,
    total=None,
    candidate=None,
    max_nodes=100000,
    max_total_slices=1024,
):
    if not __debug__:
        raise RuntimeError("Integer processing requires enabled assertions")
    m = model(q)
    es = thresholds(epsilon, len(m["A"]))
    active = m["active"]
    b = [m["B"][j] for j in active]
    K = len(es)
    nodes = 0
    bounds = 0
    point_checks = 0
    if total is not None and (
        F(total).denominator != 1 or not 0 <= int(F(total)) <= m["b"]
    ):
        raise ValueError("Feasible integral split total required")
    fixed = None if total is None else int(F(total))

    def negative(x):
        return dict(
            kind="integer_feasible",
            query_digest=m["digest"],
            epsilon=list(map(str, es)),
            total=fixed,
            allocation=x,
        )

    trial = []
    if candidate is not None:
        raw = list(map(F, candidate))
        assert len(raw) == len(m["B"])
        nearest = [max(0, min(cap, int(round(v)))) for cap, v in zip(m["B"], raw)]
        trial.append(nearest)
        for target in set([sum(nearest), int(sum(raw)), int(sum(raw)) + 1]):
            x = [max(0, min(cap, int(v))) for cap, v in zip(m["B"], raw)]
            need = target - sum(x)
            for j in sorted(active, key=lambda j: -(raw[j] - int(raw[j]))):
                if need > 0 and x[j] < m["B"][j]:
                    x[j] += 1
                    need -= 1
            if need == 0:
                trial.append(x)
    trial += [[0] * len(m["B"]), m["B"][:], [v // 2 for v in m["B"]]]
    for x in trial:
        point_checks += 1
        if (fixed is None or sum(x) == fixed) and low(m, x, es):
            return dict(
                status="negative",
                proof=negative(x),
                nodes=nodes,
                bounds=bounds,
                point_checks=point_checks,
            )
    if fixed is None and m["b"] + 1 > max_total_slices:
        return dict(
            status="undecided",
            proof=None,
            nodes=nodes,
            bounds=bounds,
            point_checks=point_checks,
            reason="total-slice budget",
        )
    roots = []
    totals = [fixed] if fixed is not None else list(range(m["b"] + 1))
    if candidate is not None:
        totals.sort(key=lambda s: (abs(s - sum(map(F, candidate))), s))

    class Found(Exception):
        def __init__(self, x):
            self.x = x

    class Budget(Exception):
        pass

    for S in totals:
        coefficients = []
        for a, c, ac, cc, W in zip(m["A"], m["C"], m["a"], m["c"], m["W"]):
            L, R = ac + S, cc + m["b"] - S
            D = [u * R - (v + cap) * L for u, v, cap in zip(a, c, m["B"])]
            coefficients.append(
                (
                    W,
                    [D[j] for j in active],
                    sum(abs(v) for j, v in enumerate(D) if not m["B"][j]),
                    L,
                    R,
                )
            )

        def visit(lo, hi):
            nonlocal nodes, bounds, point_checks
            nodes += 1
            if nodes > max_nodes:
                raise Budget()
            sl, su = sum(lo), sum(hi)
            if not sl <= S <= su:
                return dict(kind="empty")
            # Every discarded coordinate value violates the fixed-sum constraint.
            lo, hi = [max(l, S - su + u) for l, u in zip(lo, hi)], [
                min(u, S - sl + l) for l, u in zip(lo, hi)
            ]
            candidates = []
            for k, ((W, D, offset, L, R), e) in enumerate(zip(coefficients, es)):
                value, x = resource_minimum(W, D, offset, lo, hi, S)
                bounds += 1
                if value * e.denominator > 2 * e.numerator * L * R:
                    return dict(kind="bound", scale=k, allocation=x, value=value)
                candidates.append(x)
            for x in candidates:
                point_checks += 1
                full = full_allocation(m, x)
                if low(m, full, es):
                    raise Found(full)
            choices = [j for j, (l, u) in enumerate(zip(lo, hi)) if l < u]
            assert choices
            j = max(
                choices,
                key=lambda j: (
                    max(x[j] for x in candidates) - min(x[j] for x in candidates),
                    hi[j] - lo[j],
                    -j,
                ),
            )
            lower, upper = min(x[j] for x in candidates), max(x[j] for x in candidates)
            split = (lower + upper) // 2 if lower < upper else (lo[j] + hi[j]) // 2
            left_hi = hi[:]
            left_hi[j] = split
            right_lo = lo[:]
            right_lo[j] = split + 1
            return dict(
                kind="split",
                coordinate=j,
                cut=split,
                left=visit(lo, left_hi),
                right=visit(right_lo, hi),
            )

        try:
            tree = visit([0] * len(b), b[:])
        except Found as found:
            return dict(
                status="negative",
                proof=negative(found.x),
                nodes=nodes,
                bounds=bounds,
                point_checks=point_checks,
            )
        except Budget:
            return dict(
                status="undecided",
                proof=None,
                nodes=nodes,
                bounds=bounds,
                point_checks=point_checks,
                reason="node budget",
            )
        roots.append(dict(total=S, tree=tree))
    proof = dict(
        kind="integer_exclusion",
        query_digest=m["digest"],
        epsilon=list(map(str, es)),
        total=fixed,
        roots=roots,
    )
    return dict(
        status="positive",
        proof=proof,
        nodes=nodes,
        bounds=bounds,
        point_checks=point_checks,
    )
