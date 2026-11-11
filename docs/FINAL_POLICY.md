# Fixed execution and audit protocol

`execution-policy.json` fixes the recommended processor. The unknown-total path tries common allocations and single-scale certificates before at most ten paired midpoint tangents among five ranked scales. Descending tangent bounds determine ranks; equal bounds retain input index. Rank-position pairs are lexicographic, beginning with (1,2), (1,3). The first positive numerical candidate proposes an exact rational certificate. Failed recovery uses the sparse SOCP fallback. Known-total requests use the same screened LP path as the Simple filter control. Answer labels never select a processing path.

## Frozen evaluation cohorts

`expected/final-policy/query-selection.csv` lists the frozen input hashes and identifiers. The balanced cohort has 200 queries for each of nine datasets (1,800 total). The answer-stratified cohort has 1,603 queries: 576 separate-positive, 451 shared-only positive, and 576 common-negative. Stratum labels are used after execution for analysis. Each query's weight is its original dataset/stratum population divided by the sampled count; the weights sum to 70,233.

Both cohorts retain the query selection used before paired screening was added. The available-information replay uses metadata-derived totals for six regular archives, supplied explicitly to every processor. Scania, ALPI, and WMCS retain unknown totals. Full query packs and raw provider records are separate data products described in DATA.md; this selection manifest does not contain their histogram counts.

The runner uses three randomized fresh-process repetitions. The timing boundary starts before the public API call and includes validation, proof recovery, and exact checking. Warmup is outside the timer. Each query contributes its median time across repetitions. Table 6 pools 200 query medians per dataset with unit weights, giving equal dataset weights. Table 8 instead uses the dataset/answer-stratum population weights defined above. P95 is the first sorted median whose cumulative weight reaches 95% of total weight. Backend calls are instrumented directly.

```sh
uv run --frozen python scripts/benchmark_policy.py examples/sharing-gap.jsonl --output runs/policy-demo
```

For a separately supplied full count pack, select `--cohort strata` and pass `--weights expected/final-policy/query-selection.csv`. A balanced replay uses `--cohort balanced`. Counts from an available-information condition must be passed through `--totals`; the runner never reads hidden totals from the query record. Output folders must be new. Each run retains all proofs and repetitions, source hashes, input hashes, and an aggregation manifest. Exact wall times depend on the machine.

## Inspectable results

`latency-summary.csv`, `archive-summary.csv`, `integer-comparison.csv`, and `pair-mechanism.json` in `expected/final-policy/` are the complete aggregates used for the revised tables and mechanism discussion. The archive protocol additionally includes retained-file reads, request construction, and compressed proof writes for the same 512-request batches. It is distinct from the public repeated-call runner.

Table 7 uses a different aggregation: each of three fresh processes measures the complete wall time for the same 512-request batch. The reported entry is their arithmetic mean divided by 512, including reads, construction, certification, checking, and response writes. It does not take medians across the individual requests.

## Rebuild Table 8

```sh
python -I -S scripts/reproduce_table8.py
```

The script reads the 14,427 saved repetitions in `expected/final-policy/stratified-timings.csv` and the exact population weights in `query-selection.csv`. It reconstructs each query's three-pass median, then the weighted mean, empirical P95, and solver rate for all twelve method/stratum rows. It checks the results against the saved full-precision aggregates. Use `--output runs/table8.csv` to save a new CSV. This rebuilds the reported aggregation; measuring algorithm performance on another machine uses the benchmark runner and separately supplied count inputs.

The complete CoCert policy reduces the weighted mean by 13.3% relative to Simple filter. Adding pairs to the no-pair policy supplies a further 2.5% mean reduction. Its overall P95 is 17.014 ms without pairs and 17.052 ms with pairs; the large tail improvement is confined to the sharing-required stratum. These comparisons use the same records and weights.

## One audit record

`examples/audit-record/` contains a fixed motor-current request from a constructed 15-minute MetroPT2 archive, supplied split-count metadata, cumulative checkpoint counts, and a positive rational certificate. The clock follows provider timestamps; a timezone is not inferred. The selected request is the known-total addition nearest the reported oil-leak time, breaking ties by query identifier. Its outer windows can extend beyond the reported event, so the example is a retrospective audit.

```sh
python -I -S scripts/verify_audit_record.py examples/audit-record
```

The input files are `checkpoints.csv`, `request.json` (including bin edges and all window endpoints), and `count-metadata.json` (s=322). The complete `certificate.json` gives all scale weights and support vectors, with exact lower bound `3933750285313/37431865351650`. In the request's bin order, the nonzero-weight supports are alpha_2=(1,0,0,-1,-1,-1) and alpha_4=(-1,0,0,1,1,1), weighted by 3/5 and 2/5.

The checker reconstructs A/B/C from endpoint differences, binds the supplied count to the request, and recomputes the known-total TV support bound using `Fraction`. It reports input and certificate checks separately and verifies `R(s) >= 3933750285313/37431865351650 > 21/200 > 1/10`, including the strict inequality above the displayed 0.1050. This is a TV lower bound, not the unknown-total transformed margin Gamma. Every compatible allocation forces a threshold excess in at least one weighted window pair; the affected pair can depend on the allocation. Raw observations are not read by the checker.
