# Dependencies

| Purpose | Install with uv | Direct packages |
| --- | --- | --- |
| Numerical proposals, proof recovery, coverage comparison | `uv sync --frozen` | NumPy 2.4.6, SciPy 1.17.1, Clarabel 0.11.1 |
| Parquet archive construction | `uv sync --frozen --extra archive` | Polars 2.0.0 |
| Symbolic feasibility comparison | `uv sync --frozen --extra symbolic` | z3-solver 5.3.1.0 |
| Recent comparison adapters | `uv sync --frozen --extra recent` | NetworkX 3.6.1, OSQP 0.6.7.post3 |
| Optional commercial LP comparison | `uv sync --frozen --extra commercial` | gurobipy 12.0.3; valid license required |
| Tests | `uv sync --frozen --extra test` | pytest 9.1.1 |
| Open comparison paths and tests | `uv sync --frozen --extra all --extra test` | All noncommercial packages above |
| Exact proof replay and integer processing | No installation | Python standard library |

Use the same extra flags with `uv run --frozen`. With pip, install `.[archive,symbolic,recent,test]`. `uv.lock` fixes transitive versions and distribution hashes; the build backend is setuptools 84.0.0.

The package needs no training framework, external source download, data-loader checkout, or LaTeX installation. Numerical libraries are imported only by solving paths. Standard-library proof replay remains usable under `python -I -S`. Run manifests record package versions, input/source hashes, threshold, information condition, and native thread settings.

CPython 3.11.15 on macOS arm64 is the validation environment. The core CLI defaults native math-library threads to one unless already configured by the caller.
