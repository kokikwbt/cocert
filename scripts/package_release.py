"""Package the documented source, examples, and saved results in a stable ZIP."""

import argparse
import gzip
import hashlib
import json
import re
import tomllib
from pathlib import Path
import zipfile

ROOT_FILES = {
    "README.md",
    "LICENSE",
    "THIRD_PARTY.md",
    "pyproject.toml",
    "uv.lock",
    "source-manifest.json",
    "paper-map.json",
    "execution-policy.json",
    ".gitignore",
    ".gitattributes",
    ".python-version",
    ".github/workflows/tests.yml",
}
REVIEW_FILES = {
    "docs/DATA.md",
    "docs/DEPENDENCIES.md",
    "docs/FORMATS.md",
    "docs/INTEGER_DOMAIN.md",
    "docs/PAPER_GUIDE.md",
    "docs/RECENT_BASELINES.md",
    "docs/SAMPLING.md",
    "examples/integer-gap-proof.jsonl",
    "examples/integer-gap.jsonl",
    "examples/real-small-proofs.jsonl",
    "examples/real-small-provenance.json",
    "examples/real-small.jsonl",
    "examples/retained-example.json",
    "examples/sharing-gap.jsonl",
    "examples/toy-proofs.jsonl",
    "examples/toy-totals.jsonl",
    "examples/toy.jsonl",
    "expected/main-input-inventory.json",
    "expected/real-small-comparison.jsonl",
    "expected/toy-comparison.jsonl",

    "evaluation/vldb/README.md",
    "evaluation/vldb/evidence/records.json.gz",
    "evaluation/vldb/evidence/wmcs-audit.json",
    "evaluation/vldb/tables/adaptive-comparison.json",
    "evaluation/vldb/tables/archive-results.json",
    "evaluation/vldb/tables/split-total-control.json",
    "evaluation/vldb/tables/certificate-replay-data.json",
    "evaluation/vldb/tables/screening-comparison.csv",
}
HOME_PATH = re.compile(
    r"(?i)(?:/(?:users|home)/[^\s\"'<>]+|[a-z]:[\\/](?:users|documents and settings)[\\/][^\s\"'<>]+)"
)
RESEARCH_PATH = re.compile(r"(?:themes/[\w-]+/|experiments/E[0-9]{3}-[\w-]+/)")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
ACCESS_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")
NON_ENGLISH = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def check_public_text(name, content):
    """Check artifact text for local paths and unnecessary contact data."""
    if HOME_PATH.search(content):
        raise ValueError(f"Personal home path in {name}")
    if RESEARCH_PATH.search(content):
        raise ValueError(f"Internal research path in {name}")
    if EMAIL.search(content) or ACCESS_TOKEN.search(content):
        raise ValueError(f"Contact address or access token in {name}")
    if NON_ENGLISH.search(content):
        raise ValueError(f"Use English text in {name}")


def check_project_metadata(root):
    """Check the package name, license, and reviewer metadata."""
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    if project.get("name") != "cocert" or project.get("license") != "MIT":
        raise ValueError("Expected the cocert package under the MIT license")
    if {"authors", "maintainers", "urls"} & project.keys():
        raise ValueError("Package metadata must omit contact and hosting records")


def mapped_code(root):
    """Match the code inventory to its documented paper roles."""
    mapping = json.loads((root / "paper-map.json").read_text())
    listed = [
        name for component in mapping["components"] for name in component["files"]
    ]
    code = set(listed)
    if len(listed) != len(code):
        raise ValueError("Duplicate paper-map entry")
    actual = {
        str(path.relative_to(root))
        for folder in ("src", "scripts", "tests", "evaluation/vldb")
        for path in (root / folder).rglob("*.py")
        if not path.is_symlink()
    }
    if actual != code:
        raise ValueError(
            f"Paper code map mismatch: unmapped={sorted(actual-code)}, missing={sorted(code-actual)}"
        )
    return code


def included_files(root):
    """Select documented files without environments, raw inputs, or run outputs."""
    code = mapped_code(root)
    files = code | ROOT_FILES | REVIEW_FILES
    result = []
    for name in sorted(files):
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing regular repository file: {name}")
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                content = stream.read()
        else:
            content = path.read_text(encoding="utf-8")
        check_public_text(name, content)
        result.append(path)
    return result


def check_sources(root):
    """Check the code inventory against the recorded source hashes."""
    manifest = json.loads((root / "source-manifest.json").read_text())
    records = manifest["files"]
    mapped = mapped_code(root)
    if len(records) != len({record["file"] for record in records}):
        raise ValueError("Duplicate source-manifest record")
    if {record["file"] for record in records} != mapped:
        raise ValueError("Source manifest must cover exactly the paper-mapped code")
    for record in records:
        path = root / record["file"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != record["sha256"]:
            raise ValueError(f"Source hash mismatch: {record['file']}")


def refresh_sources(root):
    """Record the hashes of the current documented Python files."""
    records = [
        {"file": name, "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
        for name in sorted(mapped_code(root))
    ]
    (root / "source-manifest.json").write_text(
        json.dumps({"schema": 3, "files": records}, indent=2) + "\n"
    )


def build(root, output):
    check_project_metadata(root)
    check_sources(root)
    files = included_files(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            entry = zipfile.ZipInfo(str(path.relative_to(root)), (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(digest + "\n")
    return dict(files=len(files), bytes=output.stat().st_size, sha256=digest)


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "build/cocert-source.zip")
    parser.add_argument(
        "--refresh-manifest",
        action="store_true",
        help="Update hashes after editing code",
    )
    args = parser.parse_args(argv)
    if args.refresh_manifest:
        refresh_sources(root)
    print(json.dumps(build(root, args.output)))


if __name__ == "__main__":
    main()
