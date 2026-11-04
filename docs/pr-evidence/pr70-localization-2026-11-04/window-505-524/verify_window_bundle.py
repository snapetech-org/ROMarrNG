#!/usr/bin/env python3
"""Verify checksums and portable review/application readbacks for W505-W524."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

WINDOW = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sums(folder, name):
    recorded = set()
    for number, line in enumerate((folder / name).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        rel = rel.strip().lstrip("*")
        path = (folder / rel).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest:
            raise SystemExit(f"FAIL: checksum mismatch: {name}:{number} {rel}")
        recorded.add(path.relative_to(folder.resolve()).as_posix())
    actual = {path.relative_to(folder.resolve()).as_posix() for path in folder.rglob("*")
              if path.is_file() and path.name != name}
    if recorded != actual:
        raise SystemExit(f"FAIL: checksum inventory mismatch: {name}")


def main():
    verify_sums(WINDOW, "SHA256SUMS.txt")
    manifest = json.loads((WINDOW / "manifest.json").read_text(encoding="utf-8"))
    app_output = subprocess.check_output([
        sys.executable, str(WINDOW / "application" / "verify_application.py"),
        "--repo", str(WINDOW.parents[3])
    ], text=True)
    application = json.loads(app_output)
    cross = application.get("crossReview", {})
    if cross.get("result") != "PASS" or application.get("result") != "PASS":
        raise SystemExit("FAIL: cross or application verifier failed")
    expected = {
        "inputHead": application["inputHead"], "inputTree": application["inputTree"],
        "catalogCommit": application["catalogCommit"], "catalogSha256": application["catalogSha256"],
        "reviewedCells": application["cells"], "selectedChanges": application["selectedChanges"],
        "textFreeHolds": application["holds"], "retainedCurrentCells": application["retained"],
        "canonicalTranslationHashUpdates": application["canonicalTranslationHashesUpdated"],
        "carriedHoldsReattested": application["carriedHolds"],
        "priorSelectedSourcesReattested": application["priorSelectedSources"],
        "tokenMismatches": application["tokenMismatches"]
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise SystemExit("FAIL: packet manifest disagrees with the verified readback")
    if application.get("crossBundleManifestSha256") != manifest.get("crossBundleManifestSha256"):
        raise SystemExit("FAIL: cross bundle manifest pin")
    if application.get("crossBundleChecksumListSha256") != manifest.get("crossBundleChecksumListSha256"):
        raise SystemExit("FAIL: cross bundle checksum-list pin")
    print(json.dumps({"result": "PASS", "cross": cross, "application": application}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
