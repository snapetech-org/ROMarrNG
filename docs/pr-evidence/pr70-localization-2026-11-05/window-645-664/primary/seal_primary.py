#!/usr/bin/env python3
"""Create portable checksums for the W645-W664 primary review packet."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_sums(root: Path) -> list[dict]:
    sums = root / "SHA256SUMS.txt"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != sums)
    records = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        records.append({"path":rel, "sha256":sha(data), "bytes":len(data)})
    sums.write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in records), encoding="utf-8")
    return records


def main() -> None:
    root = Path(__file__).resolve().parent
    output = root / "primary-output"
    if not (output / "primary-manifest.json").is_file():
        raise SystemExit("primary review output has not been built")
    output_records = write_sums(output)
    root_records = write_sums(root)
    print(json.dumps({"result":"SEALED", "primaryOutputFiles":len(output_records), "primaryPacketFiles":len(root_records), "primaryPacketBytes":sum(row["bytes"] for row in root_records)}, sort_keys=True))


if __name__ == "__main__":
    main()
