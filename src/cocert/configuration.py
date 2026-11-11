"""Execution configurations for the same shared-completion query.

cocert: Algorithm 1, screening followed by sparse SOCP.
cocert-facets: screening followed by the optional eight-round facet fallback.
facets/full/decision: solver-only paths for computational comparisons.
simple-filter/sharp-filter: screening controls in the runtime comparison.
These choices do not change the completion model or proof contract.
"""

METHODS = (
    "cocert",
    "cocert-facets",
    "facets",
    "full",
    "decision",
    "simple-filter",
    "sharp-filter",
)
SCREENED_KNOWN_METHODS = frozenset(
    {"cocert", "cocert-facets", "simple-filter", "sharp-filter"}
)
