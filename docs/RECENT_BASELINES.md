# Comparison adapters

The adapters connect the compared formulations to the same retained-count TV query.

| Adapter | Public function | Input and output |
| --- | --- | --- |
| Minimum TV | `minimum_tv_bounds(query, total=None)` | Independent lower-probability cores; returns one lower bound per scale. A nonpositive bound is not a shared negative answer. |
| Eris-LP | `eris_lp(query, epsilon="1/10", total=None)` | Known split total and shared linear TV constraints through OSQP; returns positive, negative, undecided, or not applicable. |
| Conditional LP | `conditional_lp(query, epsilon="1/10", total=None, ...)` | Fixed-total LP; unknown totals use nested 9/33/129-point grids with reuse and a one-second budget. Positive bounds include a grid-gap correction. |
| Adaptive LP | `adaptive_lp(query, epsilon="1/10", ...)` | Unknown split total. Bisects intervals and checks Lipschitz lower bounds using the original fixed-total TV LP. The matched timing comparison runs without a wall-time cap or an LP-call cap. |
| MMD-Miss TV | `mmd_tv(query, epsilon="1/10", total=None, bandwidth="fixed")` | Eligible integer counts with known sample sizes; fixed and median kernels. Converts a checked lower MMD bound into a one-sided TV certificate. |

Conditional LP and Adaptive LP use HiGHS by default. The Gurobi variant uses the `commercial` extra and a valid license. When a configured budget is exhausted, the adapter reports `undecided`. [Matched timing protocol](../evaluation/vldb/README.md)
