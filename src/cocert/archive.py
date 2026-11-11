"""Retained Parquet endpoints to query counts; optional archive extra."""

from fractions import Fraction as F
import math
from numbers import Integral
import numpy as np
import polars as pl

NUMPY_DTYPES = {
    pl.Int8,
    pl.Int16,
    pl.Int32,
    pl.Int64,
    pl.UInt8,
    pl.UInt16,
    pl.UInt32,
    pl.UInt64,
    pl.Float32,
    pl.Float64,
}


def _finite(values):
    if values.dtype.kind != "O":
        return np.isfinite(values).all()
    return all(
        value is not None
        and (
            isinstance(value, Integral)
            or (
                value.is_finite()
                if hasattr(value, "is_finite")
                else math.isfinite(value)
            )
        )
        for value in values.flat
    )


def _coordinates(series):
    if not series.dtype.is_numeric() or series.null_count():
        raise ValueError("Numeric, nonmissing retained coordinates required")
    return (
        series.to_numpy()
        if series.dtype in NUMPY_DTYPES
        else np.array(series.to_list(), dtype=object)
    )


def _fraction(value):
    if isinstance(value, np.integer):
        return F(int(value))
    if isinstance(value, np.floating):
        return F(float(value))
    return F(value)


def load_archive(path, metadata):
    """Read cumulative bins and require ordered, finite, nondecreasing snapshots."""
    frame = pl.read_parquet(path)
    result = {}
    for (sid,), group in frame.partition_by(
        "series_id", as_dict=True, maintain_order=True
    ).items():
        m = metadata[str(sid)]["bins"]
        if isinstance(m, bool) or not isinstance(m, int) or m < 1:
            raise ValueError("Positive bin count required")
        bins = group.select([f"b{j}" for j in range(m)])
        if not all(dtype.is_numeric() for dtype in bins.dtypes) or sum(
            bins.null_count().row(0)
        ):
            raise ValueError("Exact numeric counts required in every retained bin")
        if len(set(bins.dtypes)) == 1 and bins.dtypes[0] in NUMPY_DTYPES:
            counts = bins.to_numpy()
        else:
            counts = np.array(bins.rows(), dtype=object)
        result[int(sid)] = (
            _coordinates(group["point_id"]),
            _coordinates(group["clock"]),
            counts,
        )
        idx, clock, counts = result[int(sid)]
        if not (
            len(idx) >= 4
            and _finite(idx)
            and _finite(clock)
            and np.all(idx[1:] > idx[:-1])
            and np.all(clock[1:] > clock[:-1])
            and _finite(counts)
            and (counts >= 0).all()
            and (counts[1:] >= counts[:-1]).all()
        ):
            raise ValueError(
                "Ordered points/clocks and finite nondecreasing cumulative counts required"
            )
    return result


def construct(request, archive):
    """Difference a validated archive at a cut strictly inside retained endpoints."""
    idx, clock, H = archive[request["series_id"]]
    left = int(np.searchsorted(clock, request["cut_clock"], side="right")) - 1
    right = left + 1
    if not (
        0 <= left < right < len(idx)
        and clock[left] < request["cut_clock"] < clock[right]
    ):
        raise ValueError("Cut must lie strictly between retained checkpoints")
    if not request["outer_ids"]:
        raise ValueError("At least one retained window required")
    points = set([left, right])
    endpoints = []
    for first_id, last_id in request["outer_ids"]:
        first, last = int(np.searchsorted(idx, first_id)), int(
            np.searchsorted(idx, last_id)
        )
        if not (
            first < len(idx)
            and last < len(idx)
            and idx[first] == first_id
            and idx[last] == last_id
            and first < left < right < last
        ):
            raise ValueError("Retained outer endpoints must enclose the boundary")
        endpoints.append((first, last))
        points.update([first, last])
    # Convert endpoints to exact fractions before subtraction.
    exact = {i: [_fraction(v) for v in H[i]] for i in points}
    subtract = lambda a, b: [str(v - u) for u, v in zip(exact[b], exact[a])]
    q = dict(
        query_id=request["request_id"],
        dataset=request["dataset"],
        unit=request["unit"],
        feature=request["feature"],
        A=[subtract(left, first) for first, last in endpoints],
        B=subtract(right, left),
        C=[subtract(last, right) for first, last in endpoints],
    )
    return q
