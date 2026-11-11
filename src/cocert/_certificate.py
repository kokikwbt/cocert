"""Recover and verify exact rational allocation and support certificates."""

from fractions import Fraction as F
import numpy as np
from ._screen import threshold
from ._split import minimum_exact
from .verification import verify
from .backends import full


def certificate(
    q, e, solver="socp", candidate=None, _alternative=False, _refined=False
):
    """Recover a rational single, feasible, or support proof and check it.

    Rounded proposals are repaired or retried with the full sparse solver.
    A recovery failure propagates to Engine as an undecided answer.
    """
    A = [list(map(F, row)) for row in q["A"]]
    B = list(map(F, q["B"]))
    C = [list(map(F, row)) for row in q["C"]]
    r = (
        threshold(
            np.array(A, float),
            np.array(B, float),
            np.array(C, float),
            epsilon=float(e),
            solver=solver,
        )
        if candidate is None
        else candidate
    )
    record = dict(
        q,
        epsilon=str(e),
        kind=r["kind"],
        found=bool(r["found"]),
        stage=r["stage"],
        numerical_candidate_found=bool(r.get("numerical_candidate_found", r["found"])),
        alternative_witness=_alternative,
    )
    if r["kind"] == "single":
        k = r["scale_index"]
        exact = minimum_exact(A[k], B, C[k])
        record.update(
            scale_index=k,
            value=str(exact["value"]),
            allocation=list(map(str, exact["allocation"])),
        )
    elif r["kind"] == "feasible":
        record["allocation"] = [
            str(max(F(0), min(b, F(float(v))))) for b, v in zip(B, r["allocation"])
        ]
    else:
        w = [
            max(F(0), F(float(v)) if _refined else F(float(v)).limit_denominator(10**9))
            for v in r["weights"]
        ]
        z = sum(w)
        w = [v / z for v in w]
        alpha = [
            [max(F(-1), min(F(1), F(float(v)).limit_denominator(10**9))) for v in row]
            for row in r["subgradients"]
        ]
        # Expand the weighted affine tangent for exact verification.
        Q = F(0)
        gradient = [F(0)] * len(B)
        constant = F(0)
        for a, c, weight, al in zip(A, C, w, alpha):
            if not weight:
                continue
            W = sum(a) + sum(B) + sum(c)
            ac = sum(a)
            pooled = [u + v + z for u, v, z in zip(a, B, c)]
            dot = sum(u * v for u, v in zip(al, pooled))
            Q += e * weight / W**2
            constant += weight * (
                (sum(u * v for u, v in zip(al, a)) / W - ac * dot / W**2) / 2
                + e * ac * (ac - W) / W**2
            )
            for j in range(len(B)):
                gradient[j] += weight * (
                    (al[j] / W - dot / W**2) / 2 + e * (2 * ac - W) / W**2
                )
        if "tangent_total" in r:
            s = F(float(r["tangent_total"]))
        else:
            mass = F(0)
            cost = F(0)
            best = None
            s = F(0)
            for j in sorted(range(len(B)), key=lambda j: gradient[j]):
                end = mass + B[j]
                candidate = max(mass, min(end, -gradient[j] / (2 * Q))) if Q else mass
                value = (
                    Q * candidate * candidate + cost + gradient[j] * (candidate - mass)
                )
                if best is None or value < best:
                    best = value
                    s = candidate
                cost += gradient[j] * B[j]
                mass = end
        bound = (
            constant
            - Q * s * s
            + sum(b * min(F(0), v + 2 * Q * s) for b, v in zip(B, gradient))
        )
        record.update(
            weights=list(map(str, w)),
            alpha=[list(map(str, row)) for row in alpha],
            tangent_total=str(s),
            bound=str(bound),
        )
    try:
        assert verify(record) == record["found"]
    except AssertionError:
        if record["kind"] != "feasible":
            if not _alternative and "allocation" in r:
                return certificate(
                    q,
                    e,
                    candidate=dict(
                        r,
                        found=False,
                        kind="feasible",
                        numerical_candidate_found=r.get(
                            "numerical_candidate_found", r["found"]
                        ),
                    ),
                    _alternative=True,
                    _refined=_refined,
                )
            if not _refined:
                return refined_certificate(q, e, r)
            raise
        # Round candidate allocations and check the exact TV constraints.
        for denominator in [1, 10, 100, 1000, 10000, 100000, 1000000, 1000000000]:
            record["allocation"] = [
                str(max(F(0), min(b, F(float(v)).limit_denominator(denominator))))
                for b, v in zip(B, r["allocation"])
            ]
            try:
                assert verify(record) == False
                break
            except AssertionError:
                continue
        else:
            # Test exact proportional and single-window allocations on the boundary.
            candidates = [
                [b * f for b in B] for f in [F(0), F(1, 4), F(1, 2), F(3, 4), F(1)]
            ]
            candidates += [minimum_exact(a, B, c)["allocation"] for a, c in zip(A, C)]
            for x in candidates:
                record["allocation"] = list(map(str, x))
                try:
                    assert verify(record) == False
                    return record
                except AssertionError:
                    continue
            if not _alternative and "weights" in r:
                return certificate(
                    q,
                    e,
                    candidate=dict(
                        r,
                        found=True,
                        kind="support",
                        numerical_candidate_found=r.get(
                            "numerical_candidate_found", r["found"]
                        ),
                    ),
                    _alternative=True,
                    _refined=_refined,
                )
            if not _refined:
                return refined_certificate(q, e, r)
            raise AssertionError(
                ("no exact witness: unresolved", q["query_id"], str(e))
            )
    return record


def refined_certificate(q, e, previous):
    arrays = [
        (
            np.array([[float(F(v)) for v in row] for row in q[k]])
            if k != "B"
            else np.array([float(F(v)) for v in q[k]])
        )
        for k in ["A", "B", "C"]
    ]
    r = full.threshold_residual(*arrays, epsilon=float(e))
    found = r["lower"] > 0
    record = certificate(
        q,
        e,
        candidate=dict(
            r,
            found=found,
            kind="support" if found else "feasible",
            stage="scaled_refinement",
            numerical_candidate_found=previous.get(
                "numerical_candidate_found", previous["found"]
            ),
        ),
        _refined=True,
    )
    record["scaled_refinement"] = True
    return record
