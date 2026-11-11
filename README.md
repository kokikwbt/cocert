# CoCert

**Certified empirical change queries over retained histogram archives.**

CoCert determines what distribution changes can be certified after individual observations have been discarded. It uses one common allocation of the unknown boundary counts across all requested windows. Numerical solvers propose answers; exact rational certificates determine which answers can be returned.

The processor reads retained histograms without changing their collection or storage format. It supports unknown and explicitly known split totals, exact proof checking, and six certification strategies for matched comparisons.

## Quick start

Use Python 3.11 and [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/kokikwbt/cocert.git
cd cocert
uv sync --frozen
uv run --frozen cocert solve examples/sharing-gap.jsonl --output runs/sharing.jsonl
uv run --frozen cocert verify examples/sharing-gap.jsonl runs/sharing.jsonl
uv run --frozen cocert compare examples/sharing-gap.jsonl --output runs/comparison.jsonl
```

The sharing example has an exact separate-window bound of zero, but CoCert certifies a change at TV 0.1. Each run saves its inputs' hashes, proofs, configuration, and environment information. Use a new output path for each run.

With pip, install the numerical interface using `python -m pip install .`. Direct dependencies are pinned in [pyproject.toml](pyproject.toml); [uv.lock](uv.lock) also pins transitive dependencies.

## Python interface

```python
from cocert import Engine, verify

request = {
    "query_id": "sharing-gap",
    "A": [[1, 0], [1, 2]],
    "B": [1, 1],
    "C": [[0, 1], [2, 1]],
}
answer = Engine().query(request, epsilon="1/10")
assert answer["status"] == "positive"
assert verify(answer["proof"], request, epsilon="1/10")
```

`A` and `C` contain the known left and right cores for each window. `B` contains the shared boundary histogram. A positive answer certifies that every compatible allocation exceeds the threshold in at least one requested window. A negative answer provides one allocation keeping every contrast at most the threshold. `undecided` means that no certificate was recovered.

Supply a known split total through the separate `total` argument. For the CLI, use `--totals` with an explicit totals file. Labels and hidden totals in a query cannot supply this information. See [input and proof formats](docs/FORMATS.md).

## Verify without installing a solver

```sh
python -I -S scripts/verify_offline.py examples/toy.jsonl examples/toy-proofs.jsonl
python -I -S scripts/verify_offline.py examples/real-small.jsonl examples/real-small-proofs.jsonl
python -I -S scripts/verify_archive_example.py
python -I -S scripts/verify_audit_record.py examples/audit-record
python -I -S scripts/reproduce_table8.py
```

These commands use only the Python standard library. The audit example reconstructs a query from retained checkpoints and checks an exact TV lower bound above 0.1050 at threshold 0.1. The Table 8 command reconstructs the published aggregate rows from saved timing repetitions and exact sampling weights; it does not measure new runtimes. Run the checkers without Python's `-O` option.

## Repository layout

| Location | Contents |
| --- | --- |
| `src/cocert/` | Query API, screening, exact certificates, integer queries, and calibrated thresholds |
| `src/cocert/backends/` | Sparse SOCP and fixed-total LP solvers |
| `src/cocert/baselines/` | Matched coverage and symbolic comparisons |
| `scripts/` | Verification, archive conversion, benchmarking, and source packaging |
| `tests/` | Mathematical, input, proof, and packaging contracts |
| `examples/` | Small constructed and attributed measured-data examples |
| `expected/` | Reference answers, frozen selections, and saved experiment summaries |
| `docs/` | Formats, dependencies, algorithm mapping, and reproduction scope |

Read [the paper guide](docs/PAPER_GUIDE.md) to follow the algorithm from query validation to exact verification. [execution-policy.json](execution-policy.json) fixes the default screening order, pair budget, and solver fallback. `Engine(pair_scales=0)` selects the no-pair ablation.

## Optional components

```sh
uv sync --frozen --all-extras
uv run --frozen --all-extras python -m pytest -q
uv run --frozen --all-extras python scripts/integer_query.py examples/integer-gap.jsonl
uv run --frozen --all-extras cocert benchmark examples/toy.jsonl --output runs/timing.jsonl
```

The `archive` extra enables retained Parquet inputs, `symbolic` enables Z3, and `test` installs pytest. See [dependencies](docs/DEPENDENCIES.md), [integer semantics](docs/INTEGER_DOMAIN.md), and [sampling contracts](docs/SAMPLING.md). Sampling interpretations require the stated independence or known-block contract.

## Reproducing the paper

The repository includes the numerical implementation, small measured-data examples, exact proofs, and saved summaries. [Reproduction scope](docs/REPRODUCIBILITY.md) distinguishes executable checks from saved-result replay. [Data inventory](docs/DATA.md) identifies the full input, reference, and archive packs needed for dataset-level experiments. Full raw-data preparation and figure generation are not bundled.

The source archive is built with:

```sh
python scripts/package_release.py
```

This creates `build/cocert-source.zip` and its SHA256 file from the documented file inventory. Local environments, raw datasets, caches, and run outputs are excluded. See [CONTRIBUTING.md](CONTRIBUTING.md) for code changes and source-hash updates.

## License and citation

The implementation and documentation use the [MIT License](LICENSE). Derived examples retain the dataset terms listed in [THIRD_PARTY.md](THIRD_PARTY.md). Citation metadata is provided in [CITATION.cff](CITATION.cff).
