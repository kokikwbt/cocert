# CoCert

CoCert certifies empirical distribution contrasts from retained cumulative histograms. It requires one shared allocation of the unknown boundary counts across the requested windows and returns rational certificates that can be checked without a solver.

## Replay the paper results

From this checkout, run the following with Python 3.9 or later.

```sh
python3 -I -S evaluation/vldb/evidence/reproduce.py --checker . --output runs/review-results.json
```

The command reaggregates the saved certification, verification, and timing records. It also reconstructs the native WMCS query from retained checkpoints and checks its certificate using exact arithmetic. [Evaluation guide](evaluation/vldb/README.md)

A successful run prints:

```text
WMCS certificate replayed.
Paper result records checked.
```

## Solve and verify a query

Install Python 3.11 and [uv](https://docs.astral.sh/uv/), then run:

```sh
uv sync --frozen
uv run --frozen cocert solve examples/sharing-gap.jsonl --output runs/sharing.jsonl
uv run --frozen cocert verify examples/sharing-gap.jsonl runs/sharing.jsonl
uv run --frozen cocert compare examples/sharing-gap.jsonl --output runs/comparison.jsonl
```

On this example, each window admits zero contrast independently, while every shared allocation exceeds TV 0.1 in at least one window. Use a new output path for each solve. [Query and certificate formats](docs/FORMATS.md)

## Get the datasets

The seven maintenance datasets use the external PdMData downloader in a separate Python environment. The data guide lists the commands, dataset IDs, and inputs required for a full rerun. [Data acquisition](docs/DATA.md#download-the-source-data)

## Review the implementation

The paper guide maps the shared solver, screening, and verification steps to source files. Optional dependencies enable the archive adapter and comparison engines. [Paper guide](docs/PAPER_GUIDE.md) · [Dependencies](docs/DEPENDENCIES.md)

```sh
uv sync --frozen --extra all --extra test
uv run --frozen --extra all --extra test python -m pytest -q
```

The source uses the MIT License. Bundled derived examples retain their provider terms. [License](LICENSE) · [Data attribution](THIRD_PARTY.md)
