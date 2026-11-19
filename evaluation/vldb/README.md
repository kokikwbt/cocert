# CoCert evaluation records

This archive accompanies the PVLDB manuscript. It contains saved decisions and measurements used to check the reported comparisons. The archive uses opaque case and cluster indices where identity is immaterial. The native audit example retains the published metric and its checkpoint counts.

## Check the results

The saved results correspond to the PVLDB manuscript revision with SHA-256 `2f0166348bf4d6e047c1098fa92157334cf2041c4070d19aba03158caced7ac3`.

Run this command from the repository root with Python 3.11 or later.

```sh
python3 -I -S evaluation/vldb/evidence/reproduce.py --checker .
```

The command uses the standard library. It checks the recomputed comparisons against the supplied table and figure inputs. To regenerate the paired bootstrap intervals, run `uv run --frozen python evaluation/vldb/evidence/reproduce.py --bootstrap --checker .`. The bootstrap uses the frozen seed and resamples complete units; its ratio uses the total reference positives in the resample as the denominator.

| Manuscript result | Saved inputs and recomputation |
|---|---|
| Thresholds and certification recall (Tables 4 and 5) | `tables/archive-results.json` holds the threshold sweep for all comparators. The `coverage` records preserve counts of query outcomes by scenario, tolerance, input condition, and cluster. Recompute Separate, CoCert, and Symb-SMT counts, fine-reference recall, and remaining compatible cases. Other baseline counts in Table 4 are saved aggregates. |
| Split totals and shared allocations (Table 6) | `tables/split-total-control.json` gives counts of paired decision patterns on fixed requests with derivable totals. The script checks the four marginal counts against the coverage records and partitions the fine-reference positives left uncertified by Separate with unknown totals. |
| Window composition and native replication | `windows` gives the fixed-cohort totals for nested window sets from E089. `native` counts each period's outcomes by maximum window observations and metric class, with the number of distinct added count inputs. E059 is the primary WMCS period and E061 is the disjoint replication. Each native run also records decision counts by process-start continuity status from E071, so the check can confirm that excluding intervals with a detected process change or insufficient metadata retains all positive answers at TV 0.1. The four `reload_controls` records preserve the decisions at recorded event times selected before fetching the latency histograms. |
| Scania audit coverage | Group the unknown-total Scania queries at TV 0.1 by the truck indices in `coverage`. Count a truck once per method if any of its queries is certified. |
| Supplemental storage sensitivity | `storage` in `tables/archive-results.json` gives measured archive sizes and outcome counts at 49 settings for each of the eight scenarios with a fine reference. The script returns the smallest measured archive for each method at 25%, 50%, 75%, 90%, and 95% recall. Certificate bytes include saved proof records and request references. |
| Certificate replay and binding (Table 7) | `replay` contains per-query medians and sizes. Take unweighted medians within each answer group. `binding` records the valid and rejected counts from E096, where the retained count, threshold, and label were each changed separately. |
| Native latency example (Table 8) | `evidence/wmcs-audit.json` holds the checkpoints and certificate for the worked query. Replay it with the command above. |
| Matched runtime (Figure 3) | `matched` contains three calls per method on each fixed input. Count completion only when all three calls return a decision within five seconds. Compute median and interpolated P95 from per-input medians on the common completed set. For paired speedup, divide the baseline median by the CoCert median on each input, choosing the faster of HiGHS and Gurobi for Adaptive LP on that input. `full` separately records the workload-weighted one-second CPU and 129-LP runs. `known_alpi` records the 16-input control with an observed split total, using the mean of per-input medians. |
| Archive reuse | `cache` records each of the three measurements of the same 128 WMCS requests in each cache condition. The median is taken across full batches. A populated cache still checks certificates against the corresponding requests. |
| Input scaling (Figure 4 and distinct inputs) | `equivalent` preserves the trial duration and decision route for equivalent window and bin expansions. Take the geometric mean of per-input medians and fit log time against log expansion. `scaling` records all three trials for each measured configuration of distinct windows and bins. Use linear interpolation for P95. The `threshold_stress` records contain all three trials at each tested offset and answer for the 12 ALPI inputs. Compute P95 over per-input medians and mean exact-check time over all trials in the cohort. |
| Screening (Table 9 and exact pair diagnostic) | `screening` records the three trials for each variant. Use the inverse sampling fractions in `weights` for the mean, P95, and solver use. `pairs` gives tested two-window outcomes from a separate fixed diagnostic. |

The named record groups come from `evidence/records.json.gz`, whose `sources` field gives run paths and SHA-256 digests. The paired outcome counts come from E101, which matches the fixed E052 and E069 requests. The reproduction command checks saved decisions and measurements. Fresh, full-scale solver and storage evaluation requires the original provider archives, prepared query packs, and the solver environment. The [reproduction guide](../../docs/REPRODUCIBILITY.md) describes the executable examples and the data needed for full reproduction.

## Replay the native certificate

The `--checker .` option in the command above enables exact replay. Pass `--output PATH` to save the recomputed values as JSON.

The command reconstructs the five histogram pairs from the eight snapshots in `evidence/wmcs-audit.json` and checks the rational certificate on those counts at TV 0.1 with an unknown split total. This check runs without the numerical solver.
