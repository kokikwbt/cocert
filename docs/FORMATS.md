# Input and output formats

## Count-only queries

Each JSONL line contains `query_id`, optional `dataset`, and arrays `A`, `B`, `C`. `A` and `C` have shape K by M; `B` has M entries. A and C are the retained left and right cores at each window. B is the shared boundary histogram. A candidate allocation x must satisfy 0 <= x <= B, and the two completed histograms are A[k]+x and C[k]+B-x for every k. The same x is used for all windows.

Counts are nonnegative, and every core has positive total mass. Integers and rational strings such as `"1/4"` are accepted. JSON float inputs retain their binary floating-point values when converted to exact fractions. Export rational strings when decimal or binary interpretation matters. All windows must use the same bin definitions. Positive decisions mean the minimum over admissible x of the maximum window TV is strictly greater than epsilon. A negative proof provides one common completion with every TV at most epsilon. This does not assert that the fine stream did not change.

The `(dataset, query_id)` pair must be unique within an input file. Fine reference allocations, labels, and implicit `total` fields in a query are discarded by the solver API. Gzip files ending in `.gz` are accepted.

## Known-total condition

Pass `--totals` with a separate JSONL file containing the same ID pairs and a `total` rational value per query. This adds sum(x)=total. Totals must come from an explicitly supplied external observation or an identified evaluation condition; they are never inferred from elapsed time. Omit the file for the unknown-total condition. Epsilon defaults to `1/10`; use `--epsilon 3/10` or `--epsilon 1/2` for the other reported thresholds.

## Solver output

Each record has `status` (`positive`, `negative`, or `undecided`), `stage`, a `proof` for a resolved answer, and timing fields. Exact verification binds the proof to supplied counts, threshold and information condition. A numerical failure to recover a checkable witness yields `undecided`. Input schema errors fail the command.

`seconds` starts after schema normalization and covers numerical proposal, proof recovery and its exact checks. `proposal_seconds` and `proof_seconds` partition that interval for unknown-total queries; known-total calls report the combined work under `proof_seconds`. They are not pure numerical-solver timings. Benchmark timing files record every repetition; the answer file retains the first repetition. Each run has a companion manifest with hashes and environment information.

For unknown totals, methods select full SOCP, decision SOCP, simple/sharp screening, CoCert screening, or balanced facet generation. The `cocert-facets` variant uses CoCert screening before an eight-round facet backend. `facets` starts at the backend directly. Known-total queries use the same fixed-total LP; the screened methods can exit with exact single-window or feasible-completion checks first. SOCP method names do not denote different known-total LP formulations.

## Retained archives

With the archive extra installed:

```sh
uv run --frozen --extra archive python scripts/construct_queries.py archive.parquet metadata.json requests.jsonl --output runs/constructed.jsonl.gz
```

The Parquet schema is `series_id`, `point_id`, `clock`, `b0`, ..., `b(M-1)`; the b columns contain cumulative, temporally nondecreasing bin counts. Metadata maps string series IDs to objects with `bins`. Series with fewer bins may have unused columns; only their declared bin columns are read. Point IDs and clocks must strictly increase within each series.

A request has `request_id`, `series_id`, `dataset`, `unit`, `feature`, `cut_clock`, and `outer_ids` (K pairs of retained point IDs). The cut must lie strictly between retained points, and every window must enclose both points. Endpoint counts are converted to exact fractions before subtraction. The conversion script emits unknown-total queries. The numerical API accepts explicit totals independently; it does not need access to the Parquet archive or original stream.

Actual Parquet layout, compression, retained points and request schedules are required to reproduce physical storage and I/O results. A/B/C inputs alone cannot reproduce those results.

## Integer command

`scripts/integer_query.py` uses the same separate `--totals` file convention. A `total` field hidden inside an input query is ignored. `--max-nodes` and `--max-total-slices` bound the search; exhausting either budget returns `undecided`. `scripts/audit_integer.py` independently enumerates the unknown-total small-count model only.
