"""Independent AU-DB scalar-expression adapter for a fixed histogram query.

Feng et al. SIGMOD 2021, Definition 3; PVLDB 2023, Section 3.
Memberships and bin keys are certain; only mass attributes are uncertain.
The original query is evaluated after clearing positive denominators.
Conditional and nonnegative-tightened absolute-value bounds are supported.
"""

from dataclasses import dataclass
from fractions import Fraction as F


@dataclass(frozen=True)
class Range:
    low: F
    guess: F
    high: F

    def __post_init__(self):
        if not self.low <= self.guess <= self.high:
            raise ValueError("Guess outside its range")

    @staticmethod
    def constant(value):
        value = F(value)
        return Range(value, value, value)

    def __add__(self, other):
        other = other if isinstance(other, Range) else Range.constant(other)
        return Range(
            self.low + other.low, self.guess + other.guess, self.high + other.high
        )

    __radd__ = __add__

    def __neg__(self):
        return Range(-self.high, -self.guess, -self.low)

    def __sub__(self, other):
        other = other if isinstance(other, Range) else Range.constant(other)
        return self + (-other)

    def __rsub__(self, other):
        return Range.constant(other) - self

    def __mul__(self, other):
        other = other if isinstance(other, Range) else Range.constant(other)
        products = [
            u * v for u in [self.low, self.high] for v in [other.low, other.high]
        ]
        return Range(min(products), self.guess * other.guess, max(products))

    __rmul__ = __mul__

    def absolute(self, tightened=False):
        if self.low >= 0:
            return self
        if self.high < 0 or (tightened and self.high == 0):
            return -self
        # Definition 3 joins both complete branch ranges when the condition
        # is uncertain; the tightened variant additionally knows |z| >= 0.
        low = F(0) if tightened else min(self.low, -self.high)
        return Range(low, abs(self.guess), max(-self.low, self.high))


def threshold_ranges(q, epsilon, total=None, tightened=False):
    """Return one bound-preserving polynomial residual range per scale.

    A positive lower endpoint certifies a change. A nonpositive lower
    endpoint is inconclusive; it is not a compatible low-change history.
    """
    B = list(map(F, q["B"]))
    bb = sum(B)
    if any(v < 0 for v in B):
        raise ValueError("Nonnegative bin counts required")
    if total is None:
        x = [Range(F(0), b / 2, b) for b in B]
        split = sum(x, Range.constant(0))
    else:
        total = F(total)
        if not 0 <= total <= bb:
            raise ValueError("Infeasible split total")
        x = [
            Range(
                max(F(0), total - bb + b), b * total / bb if bb else F(0), min(b, total)
            )
            for b in B
        ]
        split = Range.constant(total)
    results = []
    for a, c in zip(q["A"], q["C"]):
        a, c = list(map(F, a)), list(map(F, c))
        aa, cc = sum(a), sum(c)
        if min(aa, cc) <= 0 or any(v < 0 for v in a + c):
            raise ValueError("Positive core totals and nonnegative masses required")
        left_total = aa + split
        right_total = cc + bb - split
        differences = [
            (u + z) * right_total - (v + b - z) * left_total
            for u, v, b, z in zip(a, c, B, x)
        ]
        numerator = sum((d.absolute(tightened) for d in differences), Range.constant(0))
        results.append(numerator - (2 * F(epsilon)) * left_total * right_total)
    return results


def certify(q, epsilon, total=None, tightened=False):
    return any(v.low > 0 for v in threshold_ranges(q, epsilon, total, tightened))
