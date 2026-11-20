"""Independent input/proof contracts and cross-solver consistency."""

import copy
from fractions import Fraction as F
from pathlib import Path
import random
import subprocess
import sys
import pytest
from cocert.api import Engine, compare
from cocert.io import rows, indexed, replay
from cocert.verification import verify

ROOT = Path(__file__).resolve().parents[1]
TOY = list(rows(ROOT / "examples/toy.jsonl"))


def test_shared_completion_adds_a_certificate():
    r = compare(TOY[0])
    assert r["cocert_status"] == "positive"
    assert not any(v for k, v in r["certified"].items() if k != "cocert")


@pytest.mark.parametrize("q", TOY)
@pytest.mark.parametrize("epsilon", ("0", "1/10", "1"))
def test_matched_methods_and_fractional_counts(q, epsilon):
    engine = Engine()
    answers = [
        engine.query(q, epsilon, method=m)
        for m in (
            "cocert",
            "cocert-facets",
            "facets",
            "full",
            "decision",
            "simple-filter",
            "sharp-filter",
        )
    ]
    assert len({a["status"] for a in answers}) == 1
    assert answers[0]["status"] != "undecided"
    for answer in answers:
        assert verify(answer["proof"], q, epsilon=epsilon) == (
            answer["status"] == "positive"
        )


def test_random_nested_counts_agree_with_full_solver():
    rng = random.Random(20261021)
    engine = Engine()
    for i in range(40):
        a, c = [[rng.randint(1, 10) for _ in range(4)] for _ in range(2)]
        q = dict(
            query_id=i,
            A=[a, [v + rng.randint(0, 25) for v in a]],
            B=[rng.randint(0, 10) for _ in a],
            C=[c, [v + rng.randint(0, 25) for v in c]],
        )
        answers = [
            engine.query(q, method=m) for m in ("cocert", "full", "decision", "facets")
        ]
        assert len({a["status"] for a in answers}) == 1
        assert answers[0]["status"] != "undecided"


def test_exact_input_threshold_and_condition_binding():
    q = TOY[0]
    engine = Engine()
    p = engine.query(q)["proof"]
    changed = copy.deepcopy(q)
    changed["B"][0] += 1
    with pytest.raises(AssertionError):
        verify(p, changed, epsilon="1/10")
    with pytest.raises(AssertionError):
        verify(p, q, epsilon="3/10")
    known = engine.query(q, total=13)["proof"]
    assert verify(known, q, total=13, epsilon="1/10") is True
    with pytest.raises(AssertionError):
        verify(known, q, total=12)
    with pytest.raises(AssertionError):
        verify(known, q)
    assert engine.query(dict(q, total=0, fine=[0] * 3))["proof"] == p


def test_tampered_witness_is_rejected():
    p = Engine().query(TOY[0])["proof"]
    if p["kind"] == "support":
        p["bound"] = str(F(p["bound"]) + 1)
    else:
        p["value"] = "100"
    with pytest.raises(AssertionError):
        verify(p)


@pytest.mark.skipif(not hasattr(sys, "set_int_max_str_digits"), reason="Integer encoding limit unavailable")
def test_large_support_is_recovered_with_a_common_denominator(monkeypatch):
    bins = 256
    query = dict(query_id="large-support", A=[[10] * (bins // 2) + [0] * (bins // 2)],
                 B=[1] * bins, C=[[0] * (bins // 2) + [10] * (bins // 2)])
    rng = random.Random(2811)
    support = [(.75 + rng.random() * .24) * (1 if j < bins // 2 else -1) for j in range(bins)]
    proposal = dict(kind="support", found=True, stage="solver", weights=[1], subgradients=[support])
    engine = Engine()
    monkeypatch.setattr(engine, "propose", lambda *args: proposal)
    previous_limit = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        result = engine.query(query)
        assert result["proof"]["compact_support"]
        assert verify(result["proof"], query, epsilon="1/10")
    finally:
        sys.set_int_max_str_digits(previous_limit)


def test_replay_requires_complete_unique_results():
    queries = indexed(ROOT / "examples/toy.jsonl")
    results = [dict(Engine().query(q), dataset=q["dataset"]) for q in queries.values()]
    assert replay(results, queries, epsilon="1/10")["queries"] == 4
    with pytest.raises(ValueError):
        replay(results[:-1], queries, epsilon="1/10")
    with pytest.raises(ValueError):
        replay(results + results[:1], queries, epsilon="1/10")


@pytest.mark.parametrize("fixture", ("toy", "real-small"))
def test_cli_comparisons_match_expected(fixture, tmp_path):
    output = tmp_path / "comparison.jsonl"
    call = subprocess.run(
        [
            sys.executable,
            "-m",
            "cocert.cli",
            "compare",
            str(ROOT / "examples" / f"{fixture}.jsonl"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert call.returncode == 0, call.stderr
    assert list(rows(output)) == list(
        rows(ROOT / "expected" / f"{fixture}-comparison.jsonl")
    )


def test_cli_reports_malformed_json_with_its_line(tmp_path):
    bad_input = tmp_path / "queries.jsonl"
    bad_input.write_text('{"query_id": "valid"}\n{invalid}\n')
    call = subprocess.run(
        [sys.executable, "-m", "cocert.cli", "verify", str(bad_input), "unused.jsonl"],
        capture_output=True,
        text=True,
    )
    assert call.returncode == 2
    assert f"{bad_input}:2:2:" in call.stderr


def test_cli_rejects_a_saved_proof_under_a_different_threshold():
    call = subprocess.run(
        [
            sys.executable, "-m", "cocert.cli", "verify",
            str(ROOT / "examples/toy.jsonl"), str(ROOT / "examples/toy-proofs.jsonl"),
            "--epsilon", "3/10",
        ],
        capture_output=True,
        text=True,
    )
    assert call.returncode == 2
    assert "Proof/threshold mismatch" in call.stderr


def test_offline_verifier_works_without_site_packages():
    unknown = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(ROOT / "scripts/verify_offline.py"),
            str(ROOT / "examples/toy.jsonl"),
            str(ROOT / "examples/toy-proofs.jsonl"),
        ],
        capture_output=True,
        text=True,
    )
    assert unknown.returncode == 0, unknown.stderr
    optimized = subprocess.run(
        [
            sys.executable,
            "-O",
            "-I",
            "-S",
            str(ROOT / "scripts/verify_offline.py"),
            str(ROOT / "examples/toy.jsonl"),
            str(ROOT / "examples/toy-proofs.jsonl"),
        ],
        capture_output=True,
        text=True,
    )
    assert optimized.returncode != 0 and "without -O" in optimized.stderr


def test_retained_archive_subtraction(tmp_path):
    pl = pytest.importorskip("polars")
    from cocert.archive import load_archive, construct

    path = tmp_path / "archive.parquet"
    pl.DataFrame(
        dict(
            series_id=[0] * 4,
            point_id=[0, 1, 2, 3],
            clock=[0.0, 10.0, 20.0, 30.0],
            b0=[0, 2, 5, 9],
            b1=[0, 3, 7, 12],
        )
    ).write_parquet(path)
    archive = load_archive(path, {"0": {"bins": 2}})
    q = construct(
        dict(
            series_id=0,
            cut_clock=15,
            outer_ids=[[0, 3]],
            request_id=0,
            dataset="test",
            unit="0",
            feature="test",
        ),
        archive,
    )
    assert q["A"] == [["2", "3"]] and q["B"] == ["3", "4"] and q["C"] == [["4", "5"]]
