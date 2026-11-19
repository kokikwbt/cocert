# Fixed execution and audit protocol

`execution-policy.json` fixes the recommended processor. The unknown-total path tries common allocations and single-scale certificates before at most ten paired midpoint tangents among five ranked scales. Descending tangent bounds determine ranks; equal bounds retain input index. Rank-position pairs are lexicographic, beginning with (1,2), (1,3). The first positive numerical candidate proposes an exact rational certificate. Failed recovery uses the sparse SOCP fallback. Known-total requests use the same screened LP path as the Simple filter control. Answer labels never select a processing path.

## Frozen evaluation cohorts

`expected/final-policy/query-selection.csv` lists the frozen input hashes and identifiers. The balanced cohort has 200 queries per source except the pressure-only HydSys selection of 100, giving 1,500 inputs. The answer-stratified cohort has 1,375 queries. Stratum labels are used after execution for analysis. Each query's weight is its original source/stratum population divided by the sampled count; the weights sum to 66,952.

Both cohorts preserve the frozen selection within the current dataset and signal scope. The available-information replay uses metadata-derived totals for five regular sources, supplied explicitly to every processor. Scania, ALPI, and WMCS retain unknown totals. Full query packs and raw provider records are separate data products described in DATA.md; this selection manifest does not contain their histogram counts.

The runner uses three randomized fresh-process repetitions with seed 20261115. The timing boundary starts before the public API call and includes validation, proof recovery, and exact checking. Warmup is outside the timer. Each query contributes its median time across repetitions. The scenario comparison uses unit query weights within each scenario. The answer-stratified comparison instead uses the source/stratum population weights defined above. P95 is the first sorted median whose cumulative weight reaches 95% of total weight. Backend calls are instrumented directly. SMT uses a fresh solver per call and a one-second watchdog; completion and timeout costs remain in the reported aggregates.

```sh
uv run --frozen python scripts/benchmark_policy.py examples/sharing-gap.jsonl --output runs/policy-demo
```

For a separately supplied full count pack, select `--cohort strata` and pass `--weights expected/final-policy/query-selection.csv`. A balanced replay uses `--cohort balanced`. Counts from an available-information condition must be passed through `--totals`; the runner never reads hidden totals from the query record. Output folders must be new. Each run retains all proofs and repetitions, source hashes, input hashes, and an aggregation manifest. Exact wall times depend on the machine.

## Inspectable results

`latency-summary.csv`, `archive-summary.csv`, `integer-comparison.csv`, and `pair-mechanism.json` in `expected/final-policy/` are the complete aggregates used for the revised tables and mechanism discussion. The archive protocol additionally includes retained-file reads, request construction, and compressed proof writes for the same 512-request batches. It is distinct from the public repeated-call runner.

The archive comparison uses a different aggregation: each of three fresh processes measures the same 512-request batch after untimed initialization and warmup. The reported entry is their arithmetic mean divided by 512, including reads, construction, certification, checking, response writes, and any SMT worker restarts. Query-only measurements instead restart workers outside the individual timers. The archive aggregation does not take medians across individual requests.

## Rebuild stratified latency

```sh
python -I -S scripts/reproduce_latency.py
```

The script reads the saved repetitions in `expected/final-policy/stratified-timings.csv` and exact population weights in `query-selection.csv`. It reconstructs each query's three-pass median, then the weighted mean, empirical P95, solver rate, and completion rate. It checks the results against the saved full-precision aggregates. Use `--output runs/latency.csv` to save a new CSV. This rebuilds the reported aggregation; measuring algorithm performance on another machine uses the benchmark runner and separately supplied count inputs. The no-pair control isolates paired screening, whereas Symb-SMT evaluates generic execution of the same shared query.

## One audit record

`examples/audit-record/` contains a fixed motor-current request from a constructed 15-minute MetroPT2 archive, supplied split-count metadata, cumulative checkpoint counts, and a positive rational certificate. The clock follows provider timestamps; a timezone is not inferred. The selected request is the known-total addition nearest the reported oil-leak time, breaking ties by query identifier. Its outer windows can extend beyond the reported event, so the example is a retrospective audit.

```sh
python -I -S scripts/verify_audit_record.py examples/audit-record
```

The input files are `checkpoints.csv`, `request.json` (including bin edges and all window endpoints), and `count-metadata.json` (s=322). The complete `certificate.json` gives all scale weights and support vectors, with exact lower bound `3933750285313/37431865351650`. In the request's bin order, the nonzero-weight supports are alpha_2=(1,0,0,-1,-1,-1) and alpha_4=(-1,0,0,1,1,1), weighted by 3/5 and 2/5.

The checker reconstructs A/B/C from endpoint differences, binds the supplied count to the request, and recomputes the known-total TV support bound using `Fraction`. It reports input and certificate checks separately and verifies `R(s) >= 3933750285313/37431865351650 > 21/200 > 1/10`, including the strict inequality above the displayed 0.1050. This is a TV lower bound, not the unknown-total transformed margin Gamma. Every compatible allocation forces a threshold excess in at least one weighted window pair; the affected pair can depend on the allocation. Raw observations are not read by the checker.
