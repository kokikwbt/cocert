"""Build count-only queries from a retained Parquet archive and request JSONL."""

import argparse
import json
from pathlib import Path
from cocert.archive import load_archive, construct
from cocert.queries import normalize
from cocert.io import rows, write_rows, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("requests", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    archive = load_archive(args.archive, json.loads(args.metadata.read_text()))
    queries = []
    seen = set()
    for request in rows(args.requests):
        q = construct(request, archive)
        q = normalize(q)
        k = q["dataset"], str(q["query_id"])
        if k in seen:
            raise ValueError("Duplicate dataset/request_id")
        seen.add(k)
        queries.append(q)
    write_rows(args.output, queries)
    args.output.with_suffix(args.output.suffix + ".manifest.json").write_text(
        json.dumps(
            dict(
                schema=1,
                queries=len(queries),
                condition="unknown",
                input_sha256={
                    k: sha256(getattr(args, k))
                    for k in ("archive", "metadata", "requests")
                },
                output_sha256=sha256(args.output),
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(dict(queries=len(queries))))


if __name__ == "__main__":
    main()
