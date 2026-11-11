"""Midpoint TV in the ambiguous-alert case study; this is not a certificate."""

from ..queries import fraction_arrays, normalize
from ..verification import tv


def midpoint_tv(query):
    """Maximum window TV after assigning half of each boundary bin left."""
    before, boundary, after = fraction_arrays(normalize(query))
    allocation = [mass / 2 for mass in boundary]
    return max(tv(a, boundary, c, allocation) for a, c in zip(before, after))
