"""Count-only two-sample TV radii, with an explicit independent-block contract.

Requires independent observations or independent blocks of a supplied maximum
length. The resulting radii specify one threshold per comparison window.
"""

from decimal import Decimal, localcontext
from .queries import calibration_inputs, rounded_threshold


def paired_calibrated(
    q, effect="0", alpha="1/20", total=None, denominator=1000000, block_size=1
):
    A, B, C, effect, alpha, s = calibration_inputs(q, effect, alpha, total, denominator)
    K, M = len(A), len(B)
    if (
        isinstance(block_size, bool)
        or not isinstance(block_size, int)
        or block_size < 1
    ):
        raise ValueError("Invalid calibration contract")
    if M == 1:
        return [rounded_threshold(effect, 0, denominator)] * K
    b = sum(B)
    with localcontext() as ctx:
        ctx.prec = 80
        log = (Decimal(K * alpha.denominator) / Decimal(alpha.numerator)).ln()
        coefficient = Decimal(M - 1).sqrt() / 2 + (log / 2).sqrt()
        values = []
        for a, c in zip(A, C):
            L = sum(a) + (s if s is not None else 0)
            R = sum(c) + (b - s if s is not None else 0)
            if min(L, R) <= 0:
                raise ValueError("Positive core counts required")
            v = block_size * (1 / L + 1 / R)
            radius = (
                coefficient * (Decimal(v.numerator) / Decimal(v.denominator)).sqrt()
            )
            values.append(rounded_threshold(effect, radius, denominator))
    return values
