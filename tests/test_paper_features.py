"""Direct checks of the paper's sharing example and optional threshold layer."""

from fractions import Fraction
from pathlib import Path
import pytest
from cocert import compare, query
from cocert.io import rows
from cocert.paired_calibration import paired_calibrated
from cocert.window_thresholds import calibrated, decide
from cocert.verify_window_thresholds import verify

ROOT = Path(__file__).resolve().parents[1]


def test_nested_sharing_gain_from_proposition_one():
    request = next(rows(ROOT / "examples/sharing-gap.jsonl"))
    result = compare(request)
    assert Fraction(result["bounds"]["separate"]) == 0
    assert result["cocert_status"] == "positive"
    assert result["certified"]["cocert"]
    assert not any(
        value for name, value in result["certified"].items() if name != "cocert"
    )


@pytest.mark.parametrize("total", [None, 20])
@pytest.mark.parametrize("policy", [calibrated, paired_calibrated])
def test_count_aware_answers_have_exact_certificates(total, policy):
    request = dict(A=[[100, 100], [200, 200]], B=[20, 20], C=[[100, 100], [200, 200]])
    tolerances = policy(request, effect="1/10", total=total)
    answer = decide(request, tolerances, total=total)
    assert answer["status"] == "negative"
    assert verify(request, answer["proof"], epsilon=tolerances, total=total) is False


def test_block_contract_increases_the_radius_and_counts_reduce_it():
    request = dict(A=[[100, 100]], B=[20, 20], C=[[100, 100]])
    independent = paired_calibrated(request)[0]
    blocked = paired_calibrated(request, block_size=16)[0]
    larger = {
        name: [[v * 64 for v in row] for row in request[name]] for name in ("A", "C")
    }
    larger["B"] = [v * 64 for v in request["B"]]
    assert paired_calibrated(larger)[0] < independent < blocked
