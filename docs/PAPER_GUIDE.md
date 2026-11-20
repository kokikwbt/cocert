# From the paper to the code

## Main path

Read `queries.py` for the input boundary, then `api.Engine.query` for the complete decision path:

1. Validate A/B/C counts and any explicitly supplied split total.
2. For an unknown total, run Algorithm 1 common-allocation and single-scale checks, then ranked paired certificates in `_screen.threshold`; unresolved inputs reach sparse SOCP. Facets are an explicit component control.
3. Recover rational allocations or exclusion supports in `_certificate.certificate`.
4. Check the certificate with `verification.verify`. A failed recovery returns `undecided`.

Known totals follow `_known_certificate` in `api.py`: exact single-window/feasible checks, then `backends/fixed.py`. Both information conditions bind proofs to the original counts. Inputs named `fine`, labels, or a hidden `total` in a query cannot supply information to this path.

In numerical kernels, A[k] and C[k] are known cores, B is the shared boundary, x is its left allocation, s is sum(x), P[k] is A[k]+B+C[k], and W[k] is the pooled total. K and M denote windows and bins. These symbols match the paper rather than separate dataset conventions.

## Algorithms and experiments

| Paper item | Code | How to exercise it |
| --- | --- | --- |
| Proposition 1: strict sharing gain | `examples/sharing-gap.jsonl`, `comparison.py` | `cocert compare` reports Separate false and CoCert true at 0.1 |
| Convex threshold query | `backends/conic.py`, `backends/full.py` | `cocert solve --method full` |
| Exact certificates | `_certificate.py`, `_verify_unknown.py`, `_verify_known.py`, `verification.py` | `scripts/verify_offline.py` replays saved proofs without numerical packages |
| Optional facet master | `_facets.py` | `--method facets` isolates solving; `--method cocert-facets` enables screening first |
| Algorithm 1 | `_screen.py`, `_histogram.py`, `_split.py` | Default `--method cocert` |
| Shared screening and conflicting-slope identity | `_screen.maximum_pair_support`, `_screen.ranked_pairs`, `api.Engine` | Default `Engine()` uses up to ten ranked pairs after preceding screens fail; `Engine(pair_scales=0)` is the ablation |
| Read-only archive adapter | `archive.py`, `scripts/construct_queries.py` | Supply retained Parquet endpoints and an external request schedule |
| Integer completion | `integer.py`, `verify_integer.py` | `scripts/integer_query.py` generates proofs; `scripts/audit_integer.py` independently enumerates small cases |
| Threshold coverage methods | `comparison.py`, `baselines/audb.py`, `baselines/density.py` | `cocert compare`, with a totals file only when available |
| Count-aware comparison | `window_thresholds.py`, `paired_calibration.py`, `verify_window_thresholds.py` | Use the two policies on identical queries and pass their per-window thresholds to `decide` |
| Sampling contract | `paired_calibration.py` | Specify a known block size; independence/block length is not estimated from histograms |
| Runtime controls | `configuration.py`, `backends/`, `runs.py` | `cocert benchmark --method ...`; manifests retain all repetitions and verified answer counts |
| Symbolic comparison | `baselines/symbolic.py`, `baselines/symbolic_isolation.py` | Use `scripts/benchmark_policy.py --methods symbolic_smt`; the Python adapter accepts window-specific tolerances and integer variables |
| Recent formulation comparisons | `baselines/recent/` | Minimum TV, Eris-LP, Conditional LP, Adaptive LP, and MMD-Miss. See [adapter contracts](RECENT_BASELINES.md). |
| VLDB evaluation records | [`evaluation/vldb/`](../evaluation/vldb/) | Recompute reported results and replay the native WMCS certificate |

The sparse SOCP constraints are assembled once in `backends/conic.py`; the full and decision wrappers select its stopping rule. The runtime configurations answer one model. `full` solves the full SOCP; `decision` uses a threshold callback; `simple-filter` and `sharp-filter` isolate simpler screening controls. Default CoCert adds midpoint tangent bounds, scale ordering, and paired certificates gated by preceding checks. [execution-policy.json](../execution-policy.json) fixes the rank order, budget, and fallback. For known totals, all solver configurations use the same fixed-total LP, with early exact checks enabled for screened configurations.

## Count-aware example

```python
from cocert.paired_calibration import paired_calibrated
from cocert.window_thresholds import decide
from cocert.verify_window_thresholds import verify

tolerances = paired_calibrated(query, effect="1/10", block_size=1)
answer = decide(query, tolerances)
if answer["proof"] is not None:
    assert verify(query, answer["proof"], epsilon=tolerances) == (answer["status"] == "positive")
```

Use `window_thresholds.calibrated` for the subset-union control. Positive sampling interpretations require the stated sampling contract; otherwise these runs compare threshold sensitivity on the retained record.

For a known split count, pass the same `total` to the policy, `decide`, and `verify`. The integer checker likewise accepts `epsilon` and `total`. Omitting `total` checks an unknown-total request; a known-total proof is rejected. Both sampling policies require integral observation counts and round the complete threshold onto the declared rational grid.

## Contract checks

`tests/test_paper_contracts.py` checks the conservation identity, tangent bound, integer optima, request/proof bindings, sampling inputs, and retained counters.
