"""Check the released timing traces without numerical-library dependencies."""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_table8_rebuilds_from_repeated_timings():
    call = subprocess.run(
        [sys.executable, "-I", "-S", str(ROOT / "scripts/reproduce_table8.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(call.stdout)
    assert result["repeated_timings"] == 14427 and result["sampled_queries"] == 1603
    assert result["population"] == 70233 and result["matches_saved_table"]
    overall = {r["method"]: r for r in result["rows"] if r["group"] == "all"}
    assert round(overall["cocert"]["mean_ms"], 3) == 2.589
    assert round(overall["no-pairs"]["mean_ms"], 3) == 2.654
    assert round(overall["cocert"]["p95_ms"], 3) == 17.052
