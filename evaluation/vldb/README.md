# CoCert PVLDB evaluation

## Verify the reported results

From the repository root, run this command with Python 3.9 or later.

```sh
python3 -I -S evaluation/vldb/evidence/reproduce.py --checker . --output runs/review-results.json
```

The replay command reaggregates the saved results and writes the recomputed values to `runs/review-results.json`. It reconstructs five window pairs from eight retained WMCS snapshots, verifies the rational certificate at threshold 0.1, and checks that the displayed allocation attains a maximum TV of 5/39. Success prints `WMCS certificate replayed.` followed by `Paper result records checked.`

To also regenerate the paired bootstrap intervals, use the locked environment.

```sh
uv run --frozen --python 3.11 python evaluation/vldb/evidence/reproduce.py --bootstrap --checker . --output runs/review-results-bootstrap.json
```

The bootstrap resamples complete units with a fixed seed. It uses the number of fine-reference positives in each resample as the denominator.

## Find a result

All paths in the table are relative to this directory.

| Manuscript result | Saved inputs and recomputation |
|---|---|
| Thresholds and certification recall (Tables 4 and 5) | `tables/archive-results.json` holds the threshold sweep. The `coverage` records preserve counts of query outcomes by scenario, tolerance, input condition, and cluster. Recompute Separate and CoCert counts, fine-reference recall, and remaining compatible cases. The relaxed bounds in Table 4 are saved aggregates. The table records the Minimum TV lower bounds and Symb-SMT counts for the coverage sweep. Symb-SMT has a one-second limit per call and reuses implications across thresholds. The runtime comparison uses an uncapped protocol. |
| Split totals and shared allocations (Table 6) | `tables/split-total-control.json` gives counts of paired decision patterns on fixed requests with derivable totals. The script checks the four marginal counts against the coverage records and partitions the fine-reference positives left uncertified by Separate with unknown totals. |
| Window composition and native replication | `windows` gives the fixed-cohort totals for nested window sets. `native` counts each period's outcomes by maximum window observations and metric class, with the number of distinct added count inputs. Each native run also records decision counts by process-start continuity status, so the check can confirm that excluding intervals with a detected process change or insufficient metadata retains all positive answers at TV 0.1. The four `reload_controls` records preserve the decisions at recorded event times selected before fetching the latency histograms. |
| Scania audit coverage | Group the unknown-total Scania queries at TV 0.1 by the truck indices in `coverage`. Count a truck once per method if any of its queries is certified. |
| Certificate replay and binding (Table 7) | `replay` contains per-query medians and sizes. Take unweighted medians within each answer group. `binding` records the valid and rejected counts, where the retained count, threshold, and label were each changed separately. |
| Native latency example (Table 8) | `evidence/wmcs-audit.json` holds the checkpoints and certificate for the worked query. Replay it with the command above. |
| Matched runtime (Figure 3) | `matched` records calls on the same 128 distinct inputs per scenario with no experimental time limit and no Adaptive LP call limit. Median and interpolated P95 use actual query times on the common resolved set. Paired speedup divides the baseline time by the CoCert time on each input and uses the faster LP backend on that input. `known_alpi` records the 16-input observed-total control, using the mean of per-input medians. |
| Archive reuse | `cache` records each of the three measurements of the same 128 WMCS requests in each cache condition. The median is taken across full batches. A populated cache still checks certificates against the corresponding requests. |
| Input scaling (Figure 4 and distinct inputs) | `equivalent` preserves the trial duration and decision route for equivalent window and bin expansions. Take the geometric mean of per-input medians and fit log time against log expansion. `scaling` records all three trials for each measured configuration of distinct windows and bins. Use linear interpolation for P95. The `threshold_stress` records contain all three trials at each tested offset and answer for the 12 ALPI inputs. Compute P95 over per-input medians and mean exact-check time over all trials in the cohort. |
| Support precision | `precision` records three independent checker timings for each candidate encoding of the 36 positive ALPI near-threshold settings. The checker receives a finished certificate, with the tangent point fixed across encodings. Recompute acceptance counts and medians on matched accepted inputs. |
| Integer evaluation | `integer_small` preserves the enumeration and search summaries. `integer_large` preserves the archive controls, including reuse of real-valued positive proofs and integer allocations recovered by rounding. |
| Screening (Table 9 and exact pair diagnostic) | `screening` records the three trials for each variant. Use the inverse sampling fractions in `weights` for the mean, P95, and solver use. `pairs` gives tested two-window outcomes from a separate fixed diagnostic. |

The named record groups are keys in `evidence/records.json.gz`. The saved wall-clock times describe the paper environment.

## Run a fresh example

The [quick start](../../README.md#solve-and-verify-a-query) solves and verifies a bundled query with the numerical implementation. To run a derived measured-data example, use this command from the repository root:

```sh
uv run --frozen --python 3.11 cocert solve examples/real-small.jsonl --output runs/review-real-small.jsonl
```

To acquire the original data, follow the [PdMData setup and dataset IDs](../../docs/DATA.md#download-the-source-data). Use the frozen WMCS snapshots for the monitoring runs.

The published commands can replay the saved aggregates and solve the bundled queries. Fresh dataset-wide measurements also require the frozen query cohorts, fine-reference records, and retained archives. The proprietary LP comparison additionally requires Gurobi with a license. [Full-run data requirements](../../docs/DATA.md#inputs-for-full-runs)
