#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parent
INPUT = (OUT.parent / "romarrng-pr70-w445-464-candidate-free-20261103" / "input").resolve()

def sha(value):
    return hashlib.sha256(value).hexdigest()

summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
input_manifest = json.loads((INPUT / "manifest.json").read_text(encoding="utf-8"))
payload = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS.txt"}:
        payload.append({
            "path": path.name,
            "sha256": sha(path.read_bytes()),
            "sizeBytes": path.stat().st_size,
        })
manifest = {
    "artifact": "ROMarrNG PR #70 W445-W464 primary review",
    "repository": "snapetech-org/ROMarrNG",
    "pullRequest": 70,
    "branch": "task/localization-translation-review-20261030",
    "head": "d5ba7f1f268501f45227388c46d5f938ed0c9191",
    "tree": "2f8ce1af963b315108f668fc31c94ca90ecd1351",
    "window": "W445-W464",
    "sourceCount": 20,
    "localeCount": 12,
    "cellCount": 240,
    "dispositions": summary["dispositions"],
    "proposedCellCount": summary["proposedCellCount"],
    "holdPositions": summary["holdPositions"],
    "priorLineageSelectionsReattested": summary["priorLineageSelectionsReattested"],
    "priorHoldCellsReattested": summary["priorHoldCellsReattested"],
    "sourceContextAvailable": summary["sourceContextAvailable"],
    "callerlessCellCount": summary["callerlessCellCount"],
    "candidateFreeInputPath": str(INPUT),
    "candidateFreeInputRelativePath": "../romarrng-pr70-w445-464-candidate-free-20261103/input",
    "candidateFreeInputManifestSha256": summary["candidateFreeInputManifestSha256"],
    "candidateFreeInputChecksumsSha256": summary["candidateFreeInputChecksumsSha256"],
    "catalogMessageCount": input_manifest["catalogMessageCount"],
    "catalogKeyOrderSha256": input_manifest["catalogKeyOrderSha256"],
    "activeSourceRegistryCount": input_manifest["activeUniqueSourceIdCount"],
    "currentProtectedLiteralMismatches": input_manifest["currentTargetProtectedLiteralMismatches"],
    "placeholderMismatchesInSelectedTargets": summary["placeholderMismatchesInSelectedTargets"],
    "numericExactMismatchesAfterSemanticReview": summary["numericExactMismatchesAfterSemanticReview"],
    "protectedLiteralMismatchesInSelectedTargets": summary["protectedLiteralMismatchesInSelectedTargets"],
    "nativeSpeakerReview": "not performed",
    "browserReview": "not performed",
    "reviewBoundary": "Independent primary review from candidate-free source/caller evidence only; no blind or cross-review output inspected.",
    "files": payload,
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
checksum_rows = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != "SHA256SUMS.txt":
        checksum_rows.append(f"{sha(path.read_bytes())}  {path.name}")
(OUT / "SHA256SUMS.txt").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
print(json.dumps({
    "files": len(payload),
    "checksummedFiles": len(checksum_rows),
    "manifestSha256": sha((OUT / "manifest.json").read_bytes()),
    "checksumListSha256": sha((OUT / "SHA256SUMS.txt").read_bytes()),
}, ensure_ascii=False))

