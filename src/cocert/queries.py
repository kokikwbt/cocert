"""Count-only representations used by the solver, in the paper's A/B/C notation.

Split totals are supplied separately. Hidden fields such as ``fine`` and
``total`` inside a query never become information available to the solver.
"""

from collections.abc import Iterable
from decimal import Decimal, ROUND_CEILING, localcontext
from fractions import Fraction


def fraction_arrays(query):
    """Return exact rational left cores A, boundary B, and right cores C."""
    before = [[Fraction(value) for value in row] for row in query["A"]]
    boundary = [Fraction(value) for value in query["B"]]
    after = [[Fraction(value) for value in row] for row in query["C"]]
    return before, boundary, after


def normalize(query):
    """Validate the counts and copy only public query fields."""
    before, boundary, after = fraction_arrays(query)
    if not boundary or not before or len(before) != len(after):
        raise ValueError("Nonempty arrays and matching scales required")
    if min(boundary) < 0 or any(
        len(row) != len(boundary) or min(row) < 0 or sum(row) <= 0
        for row in before + after
    ):
        raise ValueError("Common bins, nonnegative mass, and positive cores required")
    result = {name: query[name] for name in ("query_id", "dataset") if name in query}
    result.setdefault("query_id", 0)
    result.update(
        A=[list(map(str, row)) for row in before],
        B=list(map(str, boundary)),
        C=[list(map(str, row)) for row in after],
    )
    return result


def numeric_arrays(query):
    """Convert validated counts for numerical proposals, never for checking."""
    import numpy as np

    arrays = tuple(np.array(values, dtype=float) for values in fraction_arrays(query))
    if any(not np.isfinite(array).all() for array in arrays):
        raise ValueError("Counts outside the finite floating-point proposal range")
    return arrays


def threshold(value):
    """Parse a nonnegative exact TV threshold."""
    epsilon = Fraction(value)
    if epsilon < 0:
        raise ValueError("Nonnegative threshold required")
    return epsilon


def split_total(value, boundary):
    """Validate an explicitly supplied total; None means unknown."""
    if value is None:
        return None
    total = Fraction(value)
    if not 0 <= total <= sum(map(Fraction, boundary)):
        raise ValueError("Supplied total outside boundary mass")
    return total


def thresholds(value, windows):
    """Validate a scalar threshold or one threshold per requested window."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        values = [threshold(value)] * windows
    else:
        values = [threshold(item) for item in value]
    if windows < 1 or len(values) != windows:
        raise ValueError("One nonnegative threshold per window required")
    return values


def calibration_inputs(query, effect, alpha, total, denominator):
    """Require observation counts and a valid sampling-threshold contract."""
    before, boundary, after = fraction_arrays(normalize(query))
    if any(
        value.denominator != 1 for row in before + [boundary] + after for value in row
    ):
        raise ValueError("Calibration requires integral observation counts")
    total = split_total(total, boundary)
    if total is not None and total.denominator != 1:
        raise ValueError("Calibration requires an integral split count")
    effect, alpha = threshold(effect), Fraction(alpha)
    if not 0 < alpha < 1:
        raise ValueError("Error probability must lie strictly between zero and one")
    if (
        isinstance(denominator, bool)
        or not isinstance(denominator, int)
        or denominator < 1
    ):
        raise ValueError("Positive integer grid denominator required")
    return before, boundary, after, effect, alpha, total


def rounded_threshold(effect, radius, denominator):
    """Round effect plus a decimal radius upward on the rational grid."""
    base = effect * denominator
    whole = base.numerator // base.denominator
    remainder = base - whole
    if isinstance(radius, int) and radius == 0:
        return Fraction(whole + bool(remainder), denominator)
    with localcontext() as context:
        context.prec = 80
        value = radius * denominator + Decimal(remainder.numerator) / Decimal(
            remainder.denominator
        )
        ticks = whole + int(value.to_integral_value(rounding=ROUND_CEILING)) + 1
    return Fraction(ticks, denominator)
