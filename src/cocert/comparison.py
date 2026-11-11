"""Coverage comparison under identical counts and split-total information."""

from ._split import minimum_exact
from .backends.fixed_certificates import single_optimum
from .baselines.audb import certify
from .baselines.density import query_bounds
from .queries import fraction_arrays, normalize, split_total, threshold


def compare(query, epsilon="1/10", *, total=None):
    """Compare the six strategies in the paper's certification coverage table.

    Separate sharp keeps exact within-scale dependencies. CoCert additionally
    requires all scales to use the same boundary allocation.
    """
    from .api import Engine

    query = normalize(query)
    epsilon = threshold(epsilon)
    total = split_total(total, query["B"])
    before, boundary, after = fraction_arrays(query)
    answer = Engine().query(query, epsilon, total=total)
    single_values = [
        (
            minimum_exact(a, boundary, c)["value"]
            if total is None
            else single_optimum(a, boundary, c, total)[0]
        )
        for a, c in zip(before, after)
    ]
    interval, band = query_bounds(query, total)
    bounds = dict(
        interval=str(interval), density_band=str(band), separate=str(max(single_values))
    )
    decisions = dict(
        audb=certify(query, epsilon, total),
        audb_plus=certify(query, epsilon, total, tightened=True),
        interval=interval > epsilon,
        density_band=band > epsilon,
        separate=max(single_values) > epsilon,
        cocert=answer["status"] == "positive",
    )
    return dict(
        query_id=query["query_id"],
        epsilon=str(epsilon),
        condition="unknown" if total is None else "known",
        bounds=bounds,
        certified=decisions,
        cocert_status=answer["status"],
    )
