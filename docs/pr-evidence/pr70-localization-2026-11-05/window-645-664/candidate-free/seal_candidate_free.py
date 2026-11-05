#!/usr/bin/env python3
"""Create portable SHA256SUMS files and the W645-W664 bundle manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HEAD = "9f8832f67195323955172dd4c3c40e29cbabb5da"
TREE = "d6066baa3d03d3b4c6034e5af061fc4bc278b0f9"


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
    input_dir = root / "candidate-free" / "input"
    if not input_dir.is_dir() or not (input_dir / "manifest.json").is_file():
        raise SystemExit("candidate-free input has not been built")
    input_records = write_sums(input_dir)
    input_manifest = (input_dir / "manifest.json").read_bytes()
    input_sums = (input_dir / "SHA256SUMS.txt").read_bytes()
    bundle = {"artifact":"ROMarrNG PR #70 W645-W664 candidate-free bundle", "repository":"snapetech-org/ROMarrNG", "pullRequest":70, "branch":"task/localization-translation-review-20261030", "head":HEAD, "tree":TREE, "window":"W645-W664", "sourceCount":20, "localeCount":12, "cellCount":240, "callerlessSourceCount":8, "callerlessCellCount":96, "priorSelectedSourceCount":260, "priorHoldCellCount":724, "priorAppliedCellCount":76, "candidateFree":True, "proposedTargetsIncluded":False, "reviewDecisionsIncluded":False, "inputManifestSha256":sha(input_manifest), "inputChecksumsSha256":sha(input_sums), "inputFiles":input_records}
    (root / "bundle-manifest.json").write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    write_sums(root)
    print(json.dumps({"result":"SEALED", "head":HEAD, "tree":TREE, "inputFiles":len(input_records), "inputBytes":sum(row["bytes"] for row in input_records)}, sort_keys=True))


if __name__ == "__main__":
    main()
