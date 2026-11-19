# Reproduction scope

## Saved results for the VLDB manuscript

[The VLDB evaluation guide](../evaluation/vldb/README.md) maps the manuscript's results to saved decisions, timing repetitions, experiment settings, and a native WMCS certificate. Run `python -I -S evaluation/vldb/evidence/reproduce.py --checker .` from the repository root to confirm the aggregates and verify the certificate. Use `--bootstrap` with the locked numerical environment to also reproduce the confidence intervals.

## Executable in this standalone directory

- Solve unknown-total and explicitly known-total queries, with rational proofs and explicit unresolved answers.
- Compare all six certification strategies under identical counts and information: AU-DB, AU-DB+, Interval, Density Band, Separate, and CoCert.
- Select the full SOCP, decision SOCP, screening variants, or balanced facet backend for unknown totals. The exact checker is shared by those implementations.
- Replay proofs with the standard library alone, or run fresh local timing measurements with the CLI benchmark.
- Construct count-only queries from a supplied retained Parquet archive.
- Run the SMT adapter with its optional dependency. The SMT watchdog is available as `cocert.baselines.symbolic_isolation.IsolatedSMT`; use a normal Python file guarded by `if __name__ == '__main__':` for multiprocessing.

`expected/toy-comparison.jsonl` and `expected/real-small-comparison.jsonl` contain the expected six-strategy decisions for the bundled examples. Compare booleans and statuses rather than solver-produced fraction representations or timing values, which can vary across platforms. The included exact proofs can be replayed independently.

The SMT adapter accepts a list of rational tolerances for window-specific thresholds. Set domain="integer" for integer allocation variables. Both interfaces preserve the shared-variable constraints and use generic Z3 solving. The unknown split total is a named scalar constrained to equal the allocation sum. TV denominators are cleared directly; the adapter does not use the conic reformulation.

`expected/smt-comparisons/` provides dataset-level outcomes for primary thresholds, window composition, retention budgets, calibration, integer allocations, native replication, bin sensitivity, and audit queries. It also includes archive and stress summaries. Its manifest distinguishes parallel coverage evaluation from isolated timing and records both watchdog budgets. Undecided outcomes remain separate from negative answers. SMT UNSAT agreement with certified references is not presented as a solver-free SMT proof.

The [normalized TV adapters](RECENT_BASELINES.md) include Minimum TV, Eris-LP, Conditional LP, Adaptive LP, and MMD-Miss. Their small expected tables can be reaggregated with `python -I -S scripts/reproduce_recent_comparisons.py`. This is summary verification, separate from full empirical solver reruns.

## Saved-certificate replay

`scripts/benchmark_certificates.py` measures fresh query execution and replay of the first saved certificate in separate processes:

```sh
python scripts/benchmark_certificates.py examples/real-small.jsonl --output runs/certificate-replay
```

Add `--totals supplied-totals.jsonl` for a known-total query pack. The runner generates answers with the fixed CoCert policy and invokes replay with `-I -S`, without numerical packages. Timings include exact verification and input binding but exclude imports, warmup, JSON decoding, and disk I/O. Unresolved answers remain in completion counts. Certificate JSONL stores proof payloads, decisions, identifiers, and input hashes separately from the retained count arrays.

`expected/certificate-replay/` contains saved paper summaries for hash-selected inputs and the fixed answer-stratified cohort. These use unweighted sample statistics, distinct from the population-weighted runtime ablation. The command above exercises the bundled examples; full paper timings require the separately prepared fixed query packs. Replay is a separate author-run process, not third-party reproduction.

## Validation records

`expected/packaging-validation.json` reports parity with the existing research engine on a fixed identifier-hash selection of 12 queries per dataset. It checks three thresholds, available known-total conditions, and six-strategy comparisons. This checks behavior on the fixed input cohort. It is not a new run of every paper experiment or a substitute for independent raw-data reconstruction.

`source-manifest.json` lists the SHA256 hashes of submitted Python files. `paper-map.json` assigns each file a role in the paper. Input validation (`queries.py`), solving (`api.py`), six-method comparison (`comparison.py`), and command/run recording (`cli.py`, `runs.py`) have separate entry points.

Tests cover proof/input binding, integer search, threshold policies, archive subtraction, and the upload boundary. `expected/packaging-validation.json` reports fixed-cohort parity; `expected/submission-validation.json` records the standalone command checks.

`expected/submission-validation.json` preserves the earlier standalone extraction checks and their exact source hashes. The extraction was installed in a separate CPython 3.11.15 environment on macOS arm64, with no parent research imports. Those checks establish the package boundary for the recorded source version. Fresh dependency downloads and complete raw-data reconstruction are separate checks.

## Additional inputs for full reproduction

Fresh full-scale runs use the provider inputs, full query packs, and preserved archive files described in [the data inventory](DATA.md). The public evaluation directory checks the reported aggregates using saved measurements, and the executable examples exercise the same numerical components on small inputs.

The full count-only query pack contains 66,952 queries and is separate from the examples and aggregated records in this repository.

## Completion-domain audit

[INTEGER_DOMAIN.md](INTEGER_DOMAIN.md) gives a standard-library exhaustive checker and an exact counterexample separating fractional and integer histories. The empirical eligibility protocol is based on counts and state budget alone. The distinction concerns negative answers. It cannot invalidate a positive CoCert certificate.

## Reviewer diagnostics

`expected/reviewer-diagnostics/` contains the fixed configurations, complete dataset-level aggregates, and independent-check summaries for the integer-completion audit, window-composition ablation, answer-stratified runtime, and retained-information/lifecycle audit. They preserve zero-eligible and empty strata. The runtime CSV contains dataset-level mean/median/p95 costs, verification time, and solve rate; paper-level estimates weight by original stratum population rather than equal dataset samples.

These small tables make reported aggregates inspectable. They are saved results, not evidence that the full empirical input packs are bundled. Exact integer checking and checkpoint reconstruction can be exercised with the included constructed example. Full provider-derived query packs and native source snapshots remain distinct data products described in DATA.md.

The calibration diagnostics additionally include the complete effect/count/block grid, all measured-data threshold counts, configurations, and exact-check aggregates. They expose the equal Separate/CoCert power on the single-shift controls alongside the measured-record sharing gains. `calibration-diagnostics-manifest.json` records the included diagnostic files and their SHA256 hashes. The adjacent `integer-large-*` files report the larger-count audit. These saved aggregates do not replace the full experimental inputs.

## Fixed final execution policy

[FINAL_POLICY.md](FINAL_POLICY.md) specifies the default paired-screen gate, stable pair order, no-pair ablation, fresh-process benchmark, weighted quantiles, and checkpoint-to-certificate audit example. `expected/final-policy/` contains the saved aggregates, frozen query selection, and individual timing repetitions. `python -I -S scripts/reproduce_latency.py` reconstructs the stratified mean, P95, solver rate, and completion rate using three-pass query medians and exact inverse sampling weights. This replays the aggregation rather than measuring new runtimes. Histogram counts for the full cohorts remain outside the upload. The standalone runner accepts separately supplied query and count-metadata packs.
