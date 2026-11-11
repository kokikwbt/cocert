# Reproduction scope

## Executable in this standalone directory

- Solve unknown-total and explicitly known-total queries, with rational proofs and explicit unresolved answers.
- Compare all six certification strategies under identical counts and information: AU-DB, AU-DB+, Interval, Density Band, Separate, and CoCert.
- Select the full SOCP, decision SOCP, screening variants, or balanced facet backend for unknown totals. The exact checker is shared by those implementations.
- Replay proofs with the standard library alone, or run fresh local timing measurements with the CLI benchmark.
- Construct count-only queries from a supplied retained Parquet archive.
- Run the SMT adapter with its optional dependency. The SMT watchdog is available as `cocert.baselines.symbolic_isolation.IsolatedSMT`; use a normal Python file guarded by `if __name__ == '__main__':` for multiprocessing.

`expected/toy-comparison.jsonl` and `expected/real-small-comparison.jsonl` contain the expected six-strategy decisions for the bundled examples. Compare booleans and statuses rather than solver-produced fraction representations or timing values, which can vary across platforms. The included exact proofs can be replayed independently.

## Validation records

`expected/public-validation.json` records the standalone source installation, regression tests, CLI examples, and standard-library proof replays. Its source-manifest hash binds the checks to the packaged implementation.

`source-manifest.json` lists the SHA256 hashes of packaged Python files. `paper-map.json` assigns each file a role in the paper. Input validation (`queries.py`), solving (`api.py`), six-method comparison (`comparison.py`), and command/run recording (`cli.py`, `runs.py`) have separate entry points.

Tests cover proof/input binding, integer search, threshold policies, archive subtraction, and the packaging boundary. The public source is installed and tested outside the research repository, with dependencies installed from the frozen lockfile.

`expected/paper-contract-validation.json` is a separate saved audit of mathematical identities and fixed research inputs, including 12 queries per dataset. Its source hash identifies that audit snapshot. Current source hashes are in `source-manifest.json`. Saved validation records do not replace the test suite or full raw-data reconstruction.

## Additional inputs for full reproduction

Full raw-data preparation, dataset-level coverage evaluation, physical storage/I/O protocols, case-study waveform rendering, grouped fresh-process scaling experiments, and paper figure/table generation remain in the research workspace. This standalone package provides their numerical building blocks and input boundary, rather than claiming that every result can be regenerated from the small examples.

The full count-only pack has 70,233 queries, but is kept outside the source archive. The published examples are intentionally small. See [DATA.md](DATA.md) for the remaining data products required for a complete artifact.

## Completion-domain audit

[INTEGER_DOMAIN.md](INTEGER_DOMAIN.md) gives a standard-library exhaustive checker and an exact counterexample separating fractional and integer histories. The empirical eligibility protocol is based on counts and state budget alone. The distinction concerns negative answers. It cannot invalidate a positive CoCert certificate.

## Reviewer diagnostics

`expected/reviewer-diagnostics/` contains the fixed configurations, complete dataset-level aggregates, and independent-check summaries for the integer-completion audit, window-composition ablation, answer-stratified runtime, and retained-information/lifecycle audit. They preserve zero-eligible and empty strata. The runtime CSV contains dataset-level mean/median/p95 costs, verification time, and solve rate; paper-level estimates weight by original stratum population rather than equal dataset samples.

These small tables make reported aggregates inspectable. They are saved results, not evidence that the full empirical input packs are bundled. Exact integer checking and checkpoint reconstruction can be exercised with the included constructed example. Full provider-derived query packs and native source snapshots remain distinct data products described in DATA.md.

The calibration diagnostics additionally include the complete effect/count/block grid, all measured-data threshold counts, configurations, and exact-check aggregates. They expose the equal Separate sharp/CoCert power on the single-shift controls alongside the measured-record sharing gains. `calibration-diagnostics-manifest.json` records the included diagnostic files and their SHA256 hashes. The adjacent `integer-large-*` files report the larger-count audit. These saved aggregates do not replace the full experimental inputs.

## Fixed final execution policy

[FINAL_POLICY.md](FINAL_POLICY.md) specifies the default paired-screen gate, stable pair order, no-pair ablation, fresh-process benchmark, weighted quantiles, and checkpoint-to-certificate audit example. `expected/final-policy/` contains the saved aggregates, frozen query selection, and 14,427 individual timing repetitions. `python -I -S scripts/reproduce_table8.py` reconstructs all 12 Table 8 rows using three-pass query medians and exact inverse sampling weights. This replays the aggregation rather than measuring new runtimes. Histogram counts for the full cohorts remain outside the source archive. The standalone runner accepts separately supplied query and count-metadata packs.
