# Recent TV comparisons

The optional adapters preserve the objectives of the compared formulations and connect them to the retained-count TV request. These independent implementations are documented in `expected/recent-baselines/adapter-sources.json`.

```sh
uv sync --frozen --extra recent
uv run --frozen --extra recent python -c 'from cocert.baselines.recent import conditional_lp; q={"A":[[1,0],[1,2]],"B":[1,1],"C":[[0,1],[2,1]]}; print(conditional_lp(q))'
python -I -S scripts/reproduce_recent_comparisons.py
```

| Adapter | Public function | Input and output |
| --- | --- | --- |
| Minimum TV | `minimum_tv_bounds(query, total=None)` | Independent lower-probability cores; returns one lower bound per scale. A nonpositive bound is not a shared negative answer. |
| Eris-LP | `eris_lp(query, epsilon="1/10", total=None)` | Known split total and shared linear TV constraints through OSQP; returns positive, negative, undecided, or not applicable. |
| Conditional LP | `conditional_lp(query, epsilon="1/10", total=None, ...)` | Fixed-total LP; unknown totals use nested 9/33/129-point grids with reuse and a one-second budget. Positive bounds include a grid-gap correction. |
| Adaptive LP | `adaptive_lp(query, epsilon="1/10", ...)` | Unknown split total. Bisects intervals and checks Lipschitz lower bounds using the original fixed-total TV LP. Defaults to 129 solves and one CPU second. |
| MMD-Miss TV | `mmd_tv(query, epsilon="1/10", total=None, bandwidth="fixed")` | Eligible integer counts with known sample sizes; fixed and median kernels. Converts a checked lower MMD bound into a one-sided TV certificate. |

All numerical positive and negative answers are checked against the retained counts. An exhausted numerical budget is `undecided`. This does not mean that no answer follows from the input.

Conditional LP and Adaptive LP use SciPy HiGHS by default. `backend="gurobi"` requires the `commercial` extra and a valid Gurobi license. Gurobi is optional and is not needed for normal CoCert use. The matched five-second measurements apply the same wall-clock deadline to all engines. The [VLDB evaluation guide](../evaluation/vldb/README.md) explains how to recompute them from the saved trials.

`expected/recent-baselines/` contains the primary and known-count comparison tables, matched shared-answer summaries, matched timing tables, and validation records. The standard-library command above recomputes the reported aggregate comparisons and checks known-count answer equality. It does not rerun the complete empirical experiments. A full rerun additionally requires the prepared requests described in `DATA.md`; the bundled toy examples cannot reproduce dataset-level measurements.
