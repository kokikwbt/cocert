"""Small functional checks for optional numerical dependencies."""

from pathlib import Path
import pytest
from cocert.io import rows


def test_symbolic_decisions_and_watchdog():
    pytest.importorskip("z3")
    from cocert.baselines.symbolic import decide
    from cocert.baselines.symbolic_isolation import IsolatedSMT

    qs = list(rows(Path(__file__).resolve().parents[1] / "examples/toy.jsonl"))
    assert decide(qs[2], "1/10")["status"] == "positive"
    worker = IsolatedSMT()
    try:
        r = worker.decide(qs[1], "1/10", timeout_ms=2000)
        assert r["status"] == "negative" and r["rational_model_verified"]
    finally:
        worker.close()


def test_midpoint_is_a_descriptive_contrast():
    from fractions import Fraction
    from cocert.baselines.midpoint import midpoint_tv

    q = dict(A=[[1, 1]], B=[2, 2], C=[[1, 1]])
    assert midpoint_tv(q) == Fraction(0)
    q = dict(A=[[10, 0]], B=[0, 0], C=[[0, 10]])
    assert midpoint_tv(q) == Fraction(1)


def test_symbolic_window_tolerances():
    pytest.importorskip("z3")
    from cocert.baselines.symbolic import decide

    q = dict(A=[[1, 0], [1, 2]], B=[1, 1], C=[[0, 1], [2, 1]])
    assert decide(q, ["0", "1"])["status"] == "negative"
    assert decide(q, ["0", "0"])["status"] == "positive"
    assert decide(q, ["0", "1"], total=1)["rational_model_verified"]


def test_symbolic_integer_history():
    pytest.importorskip("z3")
    from cocert.baselines.symbolic import decide
    from cocert.baselines.symbolic_isolation import IsolatedSMT

    q = dict(A=[[5, 4], [5, 6]], B=[1, 1], C=[[4, 5], [6, 5]])
    assert decide(q, "1/10")["status"] == "negative"
    assert decide(q, "1/10", domain="integer")["status"] == "positive"
    worker = IsolatedSMT()
    try:
        assert worker.decide(q, ["1/10", "1/10"], domain="integer",
                             timeout_ms=2000)["status"] == "positive"
    finally:
        worker.close()
