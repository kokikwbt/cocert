"""Integer answer/proof and verifier execution contracts."""

import copy, json, subprocess, sys, unittest
from pathlib import Path
from cocert.integer import decide
from cocert.verify_integer import verify


class IntegerContracts(unittest.TestCase):
    def setUp(self):
        self.q = dict(A=[[5, 4], [5, 6]], B=[1, 1], C=[[4, 5], [6, 5]])

    def test_integer_gap(self):
        r = decide(self.q, "1/10")
        self.assertEqual(r["status"], "positive")
        self.assertTrue(verify(self.q, r["proof"]))

    def test_negative_witness(self):
        r = decide(self.q, "1/2")
        self.assertEqual(r["status"], "negative")
        self.assertFalse(verify(self.q, r["proof"]))

    def test_fixed_total(self):
        r = decide(self.q, "1/10", total=1)
        self.assertTrue(verify(self.q, r["proof"], epsilon="1/10", total=1))
        self.assertEqual([v["total"] for v in r["proof"]["roots"]], [1])

    def test_missing_root(self):
        p = decide(self.q, "1/10")["proof"]
        p["roots"].pop()
        with self.assertRaises(AssertionError):
            verify(self.q, p)

    def test_changed_input(self):
        p = decide(self.q, "1/10")["proof"]
        q = copy.deepcopy(self.q)
        q["A"][0][0] += 1
        with self.assertRaises(AssertionError):
            verify(q, p)

    def test_optimized_python_rejected(self):
        src = str(Path(__file__).resolve().parents[1] / "src")
        for module in ["verify_integer", "verify_window_thresholds"]:
            code = (
                "import sys;sys.path.insert(0,"
                + repr(src)
                + ");from cocert."
                + module
                + " import verify;verify({}, {})"
            )
            r = subprocess.run(
                [sys.executable, "-B", "-O", "-I", "-S", "-c", code],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("enabled assertions", r.stderr)
