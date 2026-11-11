"""Exact input-bound checks, using only Python's standard library."""

from fractions import Fraction as F
from ._verify_unknown import verify as verify_unknown
from ._verify_known import tv, verify_single, positive_bound

if not __debug__:
    raise RuntimeError("Exact checks require assertions: run without -O")


def _arrays(q):
    A = [[F(v) for v in row] for row in q["A"]]
    B = list(map(F, q["B"]))
    C = [[F(v) for v in row] for row in q["C"]]
    assert B and len(A) == len(C) > 0 and min(B) >= 0
    assert all(len(row) == len(B) and min(row) >= 0 and sum(row) > 0 for row in A + C)
    return A, B, C


def verify(proof, query=None, *, total=None, epsilon=None):
    """Check a proof against the requested counts and information condition.

    ``total=None`` means an unknown split total. A known-total proof must be
    checked with that externally supplied total. Known-total proofs cannot be
    substituted for an unknown-total request.
    """
    A, B, C = _arrays(proof)
    ep = F(proof["epsilon"])
    assert ep >= 0
    if query is not None:
        assert (A, B, C) == _arrays(query), "Proof/input mismatch"
    if epsilon is not None:
        assert ep == F(epsilon), "Proof/threshold mismatch"
    if total is None:
        assert "total" not in proof, "Known-total proof for an unknown-total request"
        answer = verify_unknown(proof)
    else:
        s = F(total)
        assert 0 <= s <= sum(B) and F(proof["total"]) == s
        if proof["kind"] == "direct":
            assert sum(B) == s == 0
            answer = verify_unknown({k: v for k, v in proof.items() if k != "total"})
        elif proof["kind"] == "single":
            k = int(proof["scale_index"])
            value = F(proof["value"])
            verify_single(A[k], B, C[k], list(map(F, proof["allocation"])), value, s)
            assert value > ep
            answer = True
        elif proof["kind"] == "feasible":
            x = list(map(F, proof["allocation"]))
            assert len(x) == len(B) and sum(x) == s
            assert all(0 <= v <= b for v, b in zip(x, B))
            assert max(tv(a, B, c, x) for a, c in zip(A, C)) <= ep
            answer = False
        else:
            assert proof["kind"] == "support" and positive_bound(A, B, C, s, proof) > ep
            answer = True
    assert isinstance(proof["found"], bool) and proof["found"] == answer
    return answer
