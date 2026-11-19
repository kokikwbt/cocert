# CoCert

**Certified empirical change queries over retained histogram archives.**

CoCert finds distribution contrasts that can be certified from saved histogram counts. Each query uses one allocation of the unknown boundary counts across all requested windows. The result includes a certificate that a reviewer can check against the original counts with exact arithmetic.

## Try a query

Use Python 3.11 and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/kokikwbt/cocert.git
cd cocert
uv sync --frozen
uv run --frozen cocert solve examples/sharing-gap.jsonl --output runs/sharing.jsonl
uv run --frozen cocert verify examples/sharing-gap.jsonl runs/sharing.jsonl
```

Both commands report one positive answer. The output file contains the certificate, and its companion manifest records the inputs and execution environment. Use a fresh output path for each run. For another installation method, run `python -m pip install .` in a Python environment and invoke `cocert` directly.

A query contains the known left and right counts `A` and `C` for each window pair, plus one shared boundary histogram `B`. Counts use the same bins throughout. Supply a known boundary split total through a separate `--totals` file. Set the desired TV tolerance with `--epsilon`; the default is `1/10`. Verify with the same query file, tolerance, and totals used for solving. See the [input and output formats](docs/FORMATS.md) for JSONL and retained Parquet input.

| Answer | Meaning |
| --- | --- |
| `positive` | Every compatible allocation forces at least one requested contrast above the tolerance. |
| `negative` | The certificate exhibits one shared allocation that keeps every contrast within tolerance. |
| `undecided` | The processor did not recover a verifiable answer. |

## Use Python

```python
from cocert import Engine, verify

query = {
    "query_id": "sharing-gap",
    "A": [[1, 0], [1, 2]],
    "B": [1, 1],
    "C": [[0, 1], [2, 1]],
}
answer = Engine().query(query, epsilon="1/10")
assert answer["status"] == "positive"
assert verify(answer["proof"], query, epsilon="1/10")
```

For known totals, pass the same `total` to `query` and `verify`. Use rational strings such as `"1/10"` for exact decimal inputs.

## Verify with Python alone

From the checkout, replay a bundled certificate with the standard library:

```sh
python3 -I -S scripts/verify_offline.py examples/toy.jsonl examples/toy-proofs.jsonl
```

Use `python3 -I -S scripts/verify_audit_record.py examples/audit-record` for an example with retained checkpoints. Exact checks require Python assertions to be enabled.

## Reproduce the paper

```sh
python3 -I -S evaluation/vldb/evidence/reproduce.py --checker .
```

This command recomputes the manuscript's results from saved measurements and verifies the native Wikimedia Cloud Services certificate. The [evaluation guide](evaluation/vldb/) maps the saved records to the reported results. See [reproduction scope](docs/REPRODUCIBILITY.md) for executable comparisons and [data sources](docs/DATA.md) for inputs needed to rerun full experiments.

## Explore and develop

- Run `cocert --help` for commands and `cocert solve --help` for query options. The [paper guide](docs/PAPER_GUIDE.md) maps the algorithm and certificate checker to their source files.
- Use the `archive` extra for retained Parquet files and `symbolic` for Z3 comparisons. See [optional dependencies](docs/DEPENDENCIES.md) for other adapters.
- Run `uv run --frozen --all-extras python -m pytest -q` to check the package. [Contributing](CONTRIBUTING.md) explains testing and reproducible source packaging.

The software uses the [MIT License](LICENSE). [Dataset attribution](THIRD_PARTY.md) covers the bundled examples. Citation metadata is available in [CITATION.cff](CITATION.cff).
