"""Mathematical identities, request bindings, and retained-count contracts."""

from fractions import Fraction as F
import itertools
from pathlib import Path
import random
import subprocess
import sys

import pytest

from cocert.integer import decide as integer_decide
from cocert.verify_integer import verify as verify_integer
from cocert.paired_calibration import paired_calibrated
from cocert.window_thresholds import calibrated, decide
from cocert.verify_window_thresholds import verify as verify_windows

ROOT = Path(__file__).resolve().parents[1]
SHARING = dict(A=[[1, 0], [1, 2]], B=[1, 1], C=[[0, 1], [2, 1]])
INTEGER_GAP = dict(A=[[5, 4], [5, 6]], B=[1, 1], C=[[4, 5], [6, 5]])
COUNTS = dict(A=[[100, 100]], B=[20, 20], C=[[100, 100]])


def tvs(query, allocation):
    values = []
    for a, c in zip(query["A"], query["C"]):
        left = [F(u) + x for u, x in zip(a, allocation)]
        right = [F(v) + b - x for v, b, x in zip(c, query["B"], allocation)]
        values.append(
            sum(abs(u / sum(left) - v / sum(right)) for u, v in zip(left, right)) / 2
        )
    return values


@pytest.mark.parametrize("domain", ["integer", "windows"])
def test_known_total_proof_cannot_answer_an_unknown_total_request(domain):
    if domain == "integer":
        request, epsilon, total = INTEGER_GAP, "1/8", 1
        process, check = integer_decide, verify_integer
    else:
        request, epsilon, total = SHARING, ["2/5", "2/5"], 0
        process, check = decide, verify_windows
    answer = process(request, epsilon, total=total)
    assert answer["status"] == "positive"
    assert process(request, epsilon)["status"] == "negative"
    assert check(request, answer["proof"], epsilon=epsilon, total=total)
    with pytest.raises(AssertionError, match="split-total"):
        check(request, answer["proof"], epsilon=epsilon)
    with pytest.raises(AssertionError, match="split-total"):
        check(request, answer["proof"], epsilon=epsilon, total=total + 1)


@pytest.mark.parametrize("domain", ["integer", "windows"])
def test_negative_proof_is_bound_to_the_requested_threshold(domain):
    process, check = (
        (integer_decide, verify_integer)
        if domain == "integer"
        else (decide, verify_windows)
    )
    answer = process(SHARING, "1/2")
    assert answer["status"] == "negative"
    assert check(SHARING, answer["proof"], epsilon="1/2") is False
    with pytest.raises(AssertionError, match="threshold"):
        check(SHARING, answer["proof"], epsilon="1/10")


@pytest.mark.parametrize("module", ["integer", "window_thresholds"])
def test_query_processing_requires_enabled_exact_checks(module):
    code = f"import sys; sys.path.insert(0,{str(ROOT / 'src')!r}); from cocert.{module} import decide; decide({SHARING!r}, '2/5')"
    result = subprocess.run(
        [sys.executable, "-O", "-I", "-c", code], capture_output=True, text=True
    )
    assert result.returncode != 0 and "enabled assertions" in result.stderr


@pytest.mark.parametrize("policy", [calibrated, paired_calibrated])
@pytest.mark.parametrize(
    "kwargs",
    [
        dict(alpha="0"),
        dict(alpha="1"),
        dict(alpha="2"),
        dict(effect="-1/10"),
        dict(denominator=0),
        dict(denominator=1.5),
        dict(total=41),
        dict(total="1/2"),
    ],
)
def test_sampling_policy_rejects_invalid_contracts(policy, kwargs):
    with pytest.raises(ValueError):
        policy(COUNTS, **kwargs)


@pytest.mark.parametrize("policy", [calibrated, paired_calibrated])
def test_sampling_policy_requires_observation_counts(policy):
    weighted = dict(A=[["1/2", "1/2"]], B=[1, 1], C=[[1, 1]])
    with pytest.raises(ValueError, match="observation counts"):
        policy(weighted)
    with pytest.raises(ValueError):
        policy(dict(A=[[1]], B=[1], C=[[1]]), alpha="0")


@pytest.mark.parametrize("policy", [calibrated, paired_calibrated])
def test_complete_sampling_threshold_is_on_the_declared_grid(policy):
    tolerance = policy(COUNTS, effect="1/3")[0]
    assert tolerance > F(1, 3) and (tolerance * 1000000).denominator == 1
    known = policy(COUNTS, total=20)[0]
    assert known < policy(COUNTS)[0]
    one_bin = policy(dict(A=[[10]], B=[4], C=[[10]]), effect="1/3")[0]
    assert one_bin >= F(1, 3) and (one_bin * 1000000).denominator == 1


@pytest.mark.parametrize("total", [None, 10000])
def test_nonuniform_thresholds_recover_an_exact_answer(total):
    request = {
        name: [[10000 * v for v in row] for row in SHARING[name]] for name in ("A", "C")
    }
    request["B"] = [10000, 10000]
    tolerances = [F(1, 10), F(3, 20)]
    answer = decide(request, tolerances, total=total)
    assert answer["status"] == "positive"
    assert verify_windows(request, answer["proof"], epsilon=tolerances, total=total)
    if total is None:
        assert not answer["separate"] and answer["proof"]["kind"] == "support"


def test_integer_search_matches_independent_complete_enumeration():
    rng = random.Random(8129)
    requests = [INTEGER_GAP]
    for _ in range(24):
        requests.append(
            dict(
                A=[[rng.randint(1, 6) for _ in range(3)] for _ in range(2)],
                B=[rng.randint(0, 3) for _ in range(3)],
                C=[[rng.randint(1, 6) for _ in range(3)] for _ in range(2)],
            )
        )
    for request in requests:
        for total in (None, sum(request["B"]) // 2):
            allocations = [
                x
                for x in itertools.product(*(range(b + 1) for b in request["B"]))
                if total is None or sum(x) == total
            ]
            optimum = min(max(tvs(request, x)) for x in allocations)
            for epsilon in (F(0), F(1, 10), F(1, 2)):
                answer = integer_decide(request, epsilon, total=total)
                assert answer["status"] == (
                    "positive" if optimum > epsilon else "negative"
                )
                assert verify_integer(
                    request, answer["proof"], epsilon=epsilon, total=total
                ) == (optimum > epsilon)


@pytest.mark.parametrize("budget", [dict(max_nodes=0), dict(max_total_slices=0)])
def test_integer_budget_exhaustion_has_no_answer_certificate(budget):
    answer = integer_decide(INTEGER_GAP, "1/10", **budget)
    assert answer["status"] == "undecided" and answer["proof"] is None


@pytest.mark.parametrize("field", ["b0", "point_id", "clock"])
def test_unsigned_retained_values_reject_observed_decreases(tmp_path, field):
    pl = pytest.importorskip("polars")
    from cocert.archive import load_archive

    columns = dict(
        series_id=[0] * 6,
        point_id=list(range(6)),
        clock=list(range(6)),
        b0=[0, 2, 5, 6, 10, 12],
        b1=[0, 3, 7, 8, 11, 13],
    )
    columns[field][3] = columns[field][2] - 1
    path = tmp_path / "decreasing.parquet"
    pl.DataFrame(columns).with_columns(pl.col(field).cast(pl.UInt64)).write_parquet(
        path
    )
    with pytest.raises(ValueError, match="nondecreasing"):
        load_archive(path, {"0": {"bins": 2}})


def test_retained_uint64_counts_preserve_exact_endpoint_differences(tmp_path):
    pl = pytest.importorskip("polars")
    from cocert.archive import load_archive, construct

    large = 2**63 + 3
    frame = pl.DataFrame(
        dict(
            series_id=[0] * 6,
            point_id=list(range(6)),
            clock=list(range(6)),
            b0=pl.Series(
                [0, large, large + 3, large + 4, large + 8, large + 10], dtype=pl.UInt64
            ),
            b1=pl.Series([0, 2, 4, 5, 8, 10], dtype=pl.UInt64),
        )
    )
    path = tmp_path / "large.parquet"
    frame.write_parquet(path)
    archive = load_archive(path, {"0": {"bins": 2}})
    request = dict(
        series_id=0,
        cut_clock=2.5,
        outer_ids=[[1, 4], [0, 5]],
        request_id=0,
        dataset="constructed",
        unit="0",
        feature="counts",
    )
    result = construct(request, archive)
    assert result["A"][0] == ["3", "2"] and result["B"] == ["1", "1"]
    assert F(result["A"][1][0]) == large + 3
    request["outer_ids"] = [[1, 100]]
    with pytest.raises(ValueError, match="enclose"):
        construct(request, archive)


def test_affine_conservation_identity_and_tangent_bound():
    rng = random.Random(2718)
    for _ in range(32):
        request = dict(
            A=[[F(rng.randint(1, 12), 3) for _ in range(3)] for _ in range(2)],
            B=[F(rng.randint(0, 8), 2) for _ in range(3)],
            C=[[F(rng.randint(1, 12), 4) for _ in range(3)] for _ in range(2)],
        )
        epsilon = F(rng.randint(0, 8), 10)
        weights = [F(1, 3), F(2, 3)]
        alpha = [[F(rng.randint(-2, 2), 2) for _ in range(3)] for _ in range(2)]
        Q, constant = F(0), F(0)
        slopes = [F(0)] * 3
        for A, C, weight, al in zip(request["A"], request["C"], weights, alpha):
            W = sum(A) + sum(request["B"]) + sum(C)
            pooled = [a + b + c for a, b, c in zip(A, request["B"], C)]
            dot = sum(a * p for a, p in zip(al, pooled))
            Q += epsilon * weight / W**2
            constant += weight * (
                sum(a * u for a, u in zip(al, A)) / (2 * W)
                - sum(A) * dot / (2 * W**2)
                - epsilon * sum(A) * (W - sum(A)) / W**2
            )
            for j in range(3):
                slopes[j] += weight * (
                    al[j] / (2 * W)
                    - dot / (2 * W**2)
                    + epsilon * (2 * sum(A) - W) / W**2
                )
        s0 = sum(request["B"]) / 3
        gamma = (
            constant
            - Q * s0**2
            + sum(b * min(F(0), r + 2 * Q * s0) for b, r in zip(request["B"], slopes))
        )
        for fractions in itertools.product((F(0), F(1, 2), F(1)), repeat=3):
            x = [b * f for b, f in zip(request["B"], fractions)]
            residuals = []
            for A, C, original_tv in zip(request["A"], request["C"], tvs(request, x)):
                W = sum(A) + sum(request["B"]) + sum(C)
                a = (sum(A) + sum(x)) / W
                n = [
                    (u + v) / W - a * (u + b + c) / W
                    for u, b, c, v in zip(A, request["B"], C, x)
                ]
                assert sum(map(abs, n)) / (2 * a * (1 - a)) == original_tv
                residuals.append(sum(map(abs, n)) / 2 - epsilon * a * (1 - a))
            support = Q * sum(x) ** 2 + sum(r * v for r, v in zip(slopes, x)) + constant
            assert gamma <= support <= max(residuals)


def test_convex_and_facet_dimensions_match_the_paper():
    import numpy as np
    from cocert.backends.conic import solve
    from cocert._facets import threshold_residual

    arrays = [np.array(SHARING[name], dtype=float) for name in ("A", "B", "C")]
    full = solve(*arrays)
    assert full["variables"] == 2 + 2 * 2 + 3
    assert full["constraints"] == 2 * 2 + 2 * 2 * 2 + 2 + 4
    facets = threshold_residual(*arrays, fallback=False)
    assert facets["variables"] == 2 + 3
    F_count = facets["facets"]
    assert facets["constraints"] == 2 * 2 + F_count + 4
    assert facets["nnz"] <= F_count * (2 + 3) + 3 * 2 + 4
