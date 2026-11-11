"""Bind the saved audit request to checkpoint counts and a rational TV bound."""

import importlib.util
import json
from pathlib import Path
import shutil
from fractions import Fraction as F

import pytest

ROOT = Path(__file__).resolve().parents[1]


def checker():
    spec = importlib.util.spec_from_file_location(
        "audit_record", ROOT / "scripts/verify_audit_record.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check


def test_audit_record_reconstructs_a_tv_bound():
    result = checker()(ROOT / "examples/audit-record")
    assert result["status"] == "passed" and result["TV_lower_bound_float"] > 0.1050
    assert result["checkpoint_reconstruction"] and not result["uses_transformed_Gamma"]
    assert (
        F(result["verified_TV_lower_bound"])
        > F(result["display_TV_lower_bound"])
        == F(21, 200)
    )
    assert all(result["input_checks"].values()) and all(
        result["certificate_checks"].values()
    )


@pytest.mark.parametrize(
    "filename,field,value",
    [
        ("request.json", "cut_us", 1657533918948001),
        ("count-metadata.json", "split_total", "323"),
    ],
)
def test_audit_record_rejects_a_different_request(tmp_path, filename, field, value):
    folder = tmp_path / "record"
    shutil.copytree(ROOT / "examples/audit-record", folder)
    path = folder / filename
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(AssertionError):
        checker()(folder)


def test_audit_record_rejects_an_unsupported_display_bound(tmp_path):
    folder = tmp_path / "record"
    shutil.copytree(ROOT / "examples/audit-record", folder)
    path = folder / "audit-statement.json"
    statement = json.loads(path.read_text())
    statement["display_TV_lower_bound"] = "106/1000"
    path.write_text(json.dumps(statement))
    with pytest.raises(AssertionError):
        checker()(folder)
