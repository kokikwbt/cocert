# Contributing

Use English for documentation, comments, commit messages, and filenames. Comments should explain a constraint, an invariant, or a non-obvious step. Keep development history in commits.

## Set up and test

```sh
uv sync --frozen --all-extras
uv run --frozen --all-extras python -m pytest -q
```

Solvers propose numerical candidates. Every returned decision must pass exact verification against the requested counts, threshold, and split-total condition. Preserve `undecided` when certificate recovery fails. Keep the standard-library checkers independent of numerical dependencies.

The default execution policy is defined in [execution-policy.json](execution-policy.json). Algorithm changes should include a mathematical justification and tests that check the proof contract. Keep benchmark inputs and aggregation rules explicit.

## Add a source file

1. Add the file to its component in [paper-map.json](paper-map.json).
2. Update the source hashes and build the source archive:

   ```sh
   python scripts/package_release.py --refresh-manifest
   ```

3. Run the tests above and the independent examples in the [README](README.md).

The packager checks the file inventory, English text, source hashes, and portable paths. It excludes raw datasets, local environments, caches, and run outputs. Derived data need attribution and compatible redistribution terms in [THIRD_PARTY.md](THIRD_PARTY.md).
