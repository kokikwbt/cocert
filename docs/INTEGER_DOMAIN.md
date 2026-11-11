# Real mass and integer histories

CoCert solves a real-valued completion problem. A positive certificate excludes every real allocation and therefore every integer history. A negative certificate witnesses a real allocation. Integer compatibility must be checked separately when indivisible observations are required.

The constructed `examples/integer-gap.jsonl` has a common real allocation `(5/11,6/11)` whose maximum TV is `1/11`. The four integer allocations have maximum TV `10/99, 1/6, 1/5, 10/99`. At threshold `1/10`, the real query is negative while every integer history changes.

Run the independent enumeration without installing the package:

```sh
python -B -I -S scripts/audit_integer.py examples/integer-gap.jsonl
```

The script accepts count-only query JSONL and reports an exact optimum for all inputs with integral A/B/C, boundary total at most 20, and at most 100,000 allocations. Larger inputs are reported as ineligible, never treated as compatible. Enumeration runs to completion even if a low-change allocation is found.

The paper applies input-only eligibility to all original primary queries and the disjoint native monitoring period. It separately reports real negatives, integer-compatible negatives, and integer-only changes. This bundled two-bin example checks the interpretation and algorithm. It does not reproduce the empirical cohort from an example alone.

`examples/retained-example.json` contains the six cumulative checkpoints and two retained windows behind the same constructed query. Their binwise differences reproduce A/B/C. The following command checks archive monotonicity, reconstructs both windows, binds the exact negative proof to the reconstructed counts, and uses no solver or installed dependencies:

```sh
python -B -I -S scripts/verify_archive_example.py
```

The example is constructed and is labeled as such. It illustrates a complete archive-to-certificate path independently of empirical provider data.

## Exact integer certificates

The optional integer processor searches fixed-total integer boxes and emits a coverage tree for positives or one integer allocation for negatives:

```sh
python -B -I -S scripts/integer_query.py examples/integer-gap.jsonl --epsilon 1/10
```

It uses no installed dependencies. The independent checker validates every leaf by a discrete exchange condition and checks all splits and total slices. It performs no search. Call `verify(query, proof, epsilon=..., total=...)` with the requested threshold and externally supplied total; omitting `total` checks an unknown-total request. The CLI supplies both arguments automatically. Node or total-slice budget exhaustion returns `undecided`. Worst-case search and proof size can be exponential. The bounded-count experiment resolves all 215,592 reference decisions, with a maximum of 21 nodes. These figures describe the tested cohort, not a general complexity guarantee. Integer processing and exact checkers require Python with assertions enabled.
