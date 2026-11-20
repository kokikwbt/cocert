"""Source archive boundaries and standalone command contracts."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


def packaging_module():
    spec = importlib.util.spec_from_file_location(
        "package_release", ROOT / "scripts/package_release.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_packaged_code_has_an_explicit_paper_mapping():
    files = packaging_module().included_files(ROOT)
    names = {str(path.relative_to(ROOT)) for path in files}
    assert "src/cocert/api.py" in names and "docs/PAPER_GUIDE.md" in names
    assert not any("outputs/" in name or "data/local/" in name for name in names)
    assert {"LICENSE", ".github/workflows/tests.yml"} <= names
    assert {
        "evaluation/vldb/evidence/records.json.gz",
        "evaluation/vldb/tables/split-total-control.json",
    } <= names
    packaging_module().check_sources(ROOT)


def test_unmapped_experiment_cannot_enter_an_archive(tmp_path):
    for name in ("src", "scripts", "tests"):
        (tmp_path / name).mkdir()
    (tmp_path / "paper-map.json").write_text(json.dumps(dict(components=[])))
    (tmp_path / "scripts/old_experiment.py").write_text("pass\n")
    with pytest.raises(ValueError, match="unmapped"):
        packaging_module().included_files(tmp_path)


def test_integer_cli_uses_only_explicit_totals(tmp_path):
    request = dict(
        query_id="gap", A=[[5, 4], [5, 6]], B=[1, 1], C=[[4, 5], [6, 5]], total=1
    )
    path = tmp_path / "queries.jsonl"
    path.write_text(json.dumps(request) + "\n")
    total_path = tmp_path / "totals.jsonl"
    total_path.write_text(json.dumps(dict(query_id="gap", total=1)) + "\n")
    command = [
        sys.executable,
        "-I",
        "-S",
        str(ROOT / "scripts/integer_query.py"),
        str(path),
    ]
    unknown = subprocess.run(command, capture_output=True, text=True, check=True)
    known = subprocess.run(
        command + ["--totals", str(total_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert [root["total"] for root in json.loads(unknown.stdout)["proof"]["roots"]] == [
        0,
        1,
        2,
    ]
    assert [root["total"] for root in json.loads(known.stdout)["proof"]["roots"]] == [1]


def test_personal_paths_are_rejected():
    with pytest.raises(ValueError, match="Personal home path"):
        packaging_module().check_public_text("README.md", "/" + "home/example/code.py")


def test_package_omits_review_extras():
    module = packaging_module()
    module.check_project_metadata(ROOT)
    names = {str(path.relative_to(ROOT)) for path in module.included_files(ROOT)}
    assert {"CITATION.cff", "CONTRIBUTING.md"}.isdisjoint(names)
    assert not any(name.startswith("expected/reviewer-diagnostics/") for name in names)


@pytest.mark.parametrize(
    "content",
    ("researcher" + "@" + "example.org", "experiments/" + "E012-internal/record.json"),
)
def test_contact_data_and_internal_paths_are_rejected(content):
    with pytest.raises(ValueError, match="Contact address|Internal research path"):
        packaging_module().check_public_text("README.md", content)


def test_non_english_repository_text_is_rejected():
    with pytest.raises(ValueError, match="English"):
        packaging_module().check_public_text("README.md", chr(0x3042))


def test_source_archive_is_deterministic(tmp_path):
    module = packaging_module()
    first = module.build(ROOT, tmp_path / "first.zip")
    second = module.build(ROOT, tmp_path / "second.zip")
    assert first["sha256"] == second["sha256"]


def test_source_manifest_contains_only_current_code_hashes():
    manifest = json.loads((ROOT / "source-manifest.json").read_text())
    assert manifest["schema"] == 3
    assert all(set(record) == {"file", "sha256"} for record in manifest["files"])
