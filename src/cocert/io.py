"""Portable JSONL inputs and exact input bindings (standard library only)."""

import gzip
import hashlib
import json
from pathlib import Path


def rows(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path}:{number}:{error.colno}: {error.msg}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{number}: Expected a JSON object")
            yield record


def key(q):
    return str(q.get("dataset", "")), str(q["query_id"])


def indexed(path):
    result = {}
    for q in rows(path):
        k = key(q)
        if k in result:
            raise ValueError(f"Duplicate dataset/query_id: {k}")
        result[k] = q
    return result


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_rows(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8") as stream:
        for row in data:
            stream.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")


def replay(results, queries, *, epsilon, totals=None):
    from .verification import verify

    seen = set()
    counts = dict(positive=0, negative=0, undecided=0)
    for record in results:
        k = key(record)
        if k in seen or k not in queries:
            raise ValueError(f"Duplicate or unrequested result: {k}")
        seen.add(k)
        status = record["status"]
        if status not in counts:
            raise ValueError(f"Invalid status: {status}")
        counts[status] += 1
        if status == "undecided":
            if record["proof"] is not None:
                raise ValueError("Undecided answer must carry no proof")
            continue
        total = None if totals is None else totals[k]["total"]
        answer = verify(record["proof"], queries[k], epsilon=epsilon, total=total)
        if answer != (status == "positive"):
            raise ValueError("Status/proof mismatch")
    if seen != set(queries):
        raise ValueError("Missing results")
    return dict(queries=len(seen), **counts)
