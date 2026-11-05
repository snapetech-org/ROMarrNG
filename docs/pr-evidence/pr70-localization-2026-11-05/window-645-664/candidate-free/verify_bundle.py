#!/usr/bin/env python3
"""Verify checksums and exact-head/source/context bindings for this packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_sums(root: Path) -> dict[str, str]:
    sums_path = root / "SHA256SUMS.txt"
    listed = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest:
            raise SystemExit("FAIL checksum: " + name)
        if name in listed:
            raise SystemExit("FAIL duplicate checksum: " + name)
        listed[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums_path}
    if set(listed) != actual:
        raise SystemExit("FAIL checksum coverage")
    return listed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    input_dir = root / "candidate-free" / "input"
    outer = verify_sums(root)
    input_sums = verify_sums(input_dir)
    bundle = json.loads((root / "bundle-manifest.json").read_text(encoding="utf-8"))
    input_manifest_raw = (input_dir / "manifest.json").read_bytes()
    if bundle.get("head") != "9f8832f67195323955172dd4c3c40e29cbabb5da" or bundle.get("tree") != "d6066baa3d03d3b4c6034e5af061fc4bc278b0f9":
        raise SystemExit("FAIL bundle source pin")
    if bundle.get("inputManifestSha256") != sha(input_manifest_raw) or bundle.get("inputChecksumsSha256") != sha((input_dir / "SHA256SUMS.txt").read_bytes()):
        raise SystemExit("FAIL bundle input-manifest/checksum hash")
    listed_input = {row["path"]: row for row in bundle.get("inputFiles", [])}
    if set(listed_input) != set(input_sums):
        raise SystemExit("FAIL bundle input file inventory")
    for name, digest in input_sums.items():
        path = input_dir / name
        record = listed_input[name]
        if record.get("sha256") != digest or record.get("bytes") != path.stat().st_size:
            raise SystemExit("FAIL bundle file record: " + name)
    result = subprocess.check_output([sys.executable, str(input_dir / "verify_input.py"), "--repo", str(args.repo.resolve()), "--input", str(input_dir)], text=True)
    print(json.dumps({"result":"PASS", "bundle":"ROMarrNG PR #70 W645-W664 candidate-free", "outerFiles":len(outer), "inputFiles":len(input_sums), "inputVerifier":json.loads(result)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
