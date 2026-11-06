#!/usr/bin/env python3
"""Portable integrity and candidate-free verifier for ROMarrNG PR #70 W485-W504."""
from pathlib import Path
import collections
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
HEAD = "6eb494d362ae19503b9199cd2c05c0767cddbc0e"
TREE = "b9450b9c6d22c816551fc8d528e8f03413d04595"
BRANCH = "task/localization-translation-review-20261030"
WINDOW = "W485-W504"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
FORBIDDEN_KEYS = {"proposedTarget", "proposedTargetSha256", "selectedTarget", "selectedTargetSha256", "disposition", "rationale", "primaryDisposition", "blindDisposition", "decision"}

def fail(message):
    raise SystemExit("FAIL: " + message)

def need(value, message):
    if not value:
        fail(message)

def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def j(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))

def jl(name):
    return [json.loads(line) for line in (HERE / name).read_text(encoding="utf-8").splitlines() if line.strip()]

def check_safe_keys(value, where):
    if isinstance(value, dict):
        bad = FORBIDDEN_KEYS.intersection(value)
        need(not bad, f"decision/proposal fields present in {where}: {sorted(bad)}")
        for key, item in value.items():
            check_safe_keys(item, where + "." + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_safe_keys(item, f"{where}[{index}]")

# Every input file except this checksum list must be covered exactly once.
sums = {}
for line in (HERE / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    match = re.fullmatch(r"([0-9a-f]{64})  ([^/][^\n]*)", line)
    need(match is not None, "malformed checksum row")
    digest, name = match.groups()
    need(name not in sums and Path(name).name == name, "duplicate or unsafe checksum path")
    sums[name] = digest
actual = {p.name for p in HERE.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"}
need(set(sums) == actual, "checksum file inventory")
for name, digest in sums.items():
    need(sha((HERE / name).read_bytes()) == digest, "checksum " + name)

# Candidate-free boundary is checked structurally; current targets are permitted.
for path in sorted(HERE.iterdir()):
    if path.suffix not in {".json", ".jsonl"}:
        continue
    if path.suffix == ".json":
        check_safe_keys(json.loads(path.read_text(encoding="utf-8")), path.name)
    else:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                check_safe_keys(json.loads(line), f"{path.name}:{n}")

manifest = j("manifest.json")
selection = j("selection.json")
pins = j("catalog-file-pins.json")
combined = j("PR-attestation.json")
before = j("PR-attestation-before.json")
after = j("PR-attestation-after.json")
need(manifest["head"] == HEAD and manifest["tree"] == TREE and manifest["branch"] == BRANCH, "manifest refs")
need(manifest["window"] == WINDOW and manifest["sourceCount"] == 20 and manifest["localeCount"] == 12 and manifest["cellCount"] == 240, "window coverage")
need(manifest["locales"] == LOCALES and manifest["candidateFree"] is True, "candidate-free manifest")
need(manifest["proposedTargetsIncluded"] is False and manifest["reviewDecisionsIncluded"] is False, "candidate-free manifest boundary")
need(selection["window"] == WINDOW and selection["positions"] == [485, 504], "selection range")
need(selection["candidateFree"] is True and selection["proposedTargetsIncluded"] is False and selection["reviewDecisionsIncluded"] is False, "selection boundary")
need(pins["commit"] == HEAD and pins["tree"] == TREE, "catalog file pin refs")
need(combined["repository"] == "snapetech-org/ROMarrNG" and combined["pullRequest"] == 70 and combined["branch"] == BRANCH, "PR identity")
need(combined["bothObservationsMatchPinnedHeadAndTree"] is True, "combined attestation status")
need(combined["observedBefore"] == before and combined["observedAfter"] == after, "separate attestation files match combined record")
for name, observation in (("before", before), ("after", after)):
    need(observation["state"] == "OPEN" and observation["isDraft"] is True, name + " PR state")
    need(observation["headRefName"] == BRANCH and observation["baseRefName"] == "main", name + " branch refs")
    need(observation["headRefOid"] == observation["liveBranchRefOid"] == observation["livePullRefOid"] == HEAD, name + " live branch/pull refs")
    need(observation["headTree"] == TREE and observation["url"] == "https://github.com/snapetech-org/ROMarrNG/pull/70", name + " pinned tree/URL")
    need(observation["baseRefOid"] == manifest["baseRefOid"], name + " base ref")
need(before["headRefOid"] == after["headRefOid"] and before["headTree"] == after["headTree"], "head stable across packet generation")

queue_raw = (HERE / "source-queue.json").read_bytes()
queue = json.loads(queue_raw)["messages"]
snapshot = j("source-snapshot.json")
need(sha(queue_raw) == manifest["sourceQueueSha256"] == pins["sourceQueueSha256"], "source queue hash")
need(sha(canon(snapshot)) == manifest["sourceSnapshotSha256"] == pins["sourceSnapshotSha256"], "source snapshot hash")
need(len(queue) == len(snapshot) == 479 == manifest["activeUniqueSourceIdCount"], "active registry size")
reg = {}
for row in queue:
    key = row["id"]
    need(key not in reg, "duplicate active source ID")
    reg[key] = row
    need(snapshot.get(key) == row["sourceHash"], "source snapshot record " + key)
ranks = {key: rank for rank, key in enumerate(sorted(reg), 1)}
source_order_sha = sha(("\n".join(sorted(reg)) + "\n").encode("utf-8"))
need(source_order_sha == manifest["sourceIdOrderSha256"] == pins["sourceIdOrderSha256"], "active source registry order hash")

inventory = jl("catalog-source-inventory.jsonl")
need(len(inventory) == 1836 == manifest["catalogMessageCount"], "catalog inventory count")
need([r["catalogZeroBasedIndex"] for r in inventory] == list(range(1836)), "catalog zero-based order")
need([r["catalogOneBasedPosition"] for r in inventory] == list(range(1, 1837)), "catalog one-based order")
ids = [r["sourceId"] for r in inventory]
need(len(set(ids)) == len(ids), "unique catalog source IDs")
need(sha(("\n".join(ids) + "\n").encode("utf-8")) == manifest["catalogKeyOrderSha256"] == pins["catalogKeyOrderSha256"], "catalog key order hash")
need(pins["catalogSha256"] == manifest["catalogSha256"], "catalog raw file hash")
by_id = {r["sourceId"]: r for r in inventory}
for row in inventory:
    need(sha(row["source"]) == row["sourceSha256"], "catalog source hash " + row["sourceId"])

selected = jl("source-inventory-selection.jsonl")
need(len(selected) == 20 and [r["catalogZeroBasedIndex"] for r in selected] == list(range(485, 505)), "selected source indices")
need([r["catalogOneBasedPosition"] for r in selected] == list(range(486, 506)), "selected source positions")
need([(r["sourceId"], r["source"], r["sourceSha256"]) for r in selected] == [(r["sourceId"], r["source"], r["sourceSha256"]) for r in inventory[485:505]], "selected source slice")
need(selection["selectedSources"] == selected and len(j("catalog-insertion-queue.json")) == 20, "selection files agree")
for row in selected:
    active = row["sourceId"] in reg
    need(row["activeSourceRegistry"] is active, "active source membership " + row["sourceId"])
    if active:
        need(row["activeSourceRank"] == ranks[row["sourceId"]] and row["registryLocations"] == reg[row["sourceId"]].get("locations", []), "active registry metadata " + row["sourceId"])
    else:
        need(row["activeSourceRank"] is None and row["registryLocations"] == [], "inactive registry metadata " + row["sourceId"])

contexts = jl("source-contexts.jsonl")
need(len(contexts) == 20 and {r["sourceId"] for r in contexts} == {r["sourceId"] for r in selected}, "caller context coverage")
file_pins = pins["callerSourceFilePins"]
for ctx in contexts:
    need(sha(canon(ctx["callerContextRefs"])) == ctx["callerContextSha256"], "caller context aggregate hash " + ctx["sourceId"])
    for ref in ctx["callerContextRefs"]:
        need(ref["path"] in file_pins, "caller context file pin")
        need(ref["fileSha256"] == file_pins[ref["path"]]["fileSha256"] and ref["gitBlob"] == file_pins[ref["path"]]["gitBlob"], "caller context file pin match")
        body = {k: ref[k] for k in ("path", "lineStart", "lineEnd", "contextLines")}
        need(sha(canon(body)) == ref["contextSha256"], "caller context excerpt hash")
        hits = sum(1 for line in ref["contextLines"] if ref["anchor"] and ref["anchor"] in line["text"])
        need(hits == ref["anchorOccurrences"] and bool(hits) == ref["anchorFound"], "caller context anchor")

audit = j("caller-search-audit.json")
need(audit["commit"] == HEAD and audit["tree"] == TREE and len(audit["queries"]) == 40, "caller search refs/coverage")
for query in audit["queries"]:
    src = next(r for r in selected if r["sourceId"] == query["sourceId"])
    literal = src["sourceId"] if query["queryKind"] == "source-id" else src["source"]
    need(query["literal"] == literal and query["matchCount"] == len(query["matches"]), "caller search query binding")
    for match in query["matches"]:
        need(match["path"] in file_pins and audit["filePins"].get(match["path"]) == file_pins[match["path"]], "caller search file pin")
        need(match["path"].startswith("romarr/") and match["path"].endswith((".py", ".js")) and literal in match["text"], "caller search scope and exact match")

dispatch = j("dispatch-mechanics.json")
need(dispatch["head"] == HEAD and dispatch["tree"] == TREE, "dispatch refs")
for path, pin in dispatch["filePins"].items():
    need(file_pins.get(path) == pin, "dispatch pin")
for ev in dispatch["evidence"]:
    body = {k: ev[k] for k in ("path", "lineStart", "lineEnd", "contextLines")}
    need(sha(canon(body)) == ev["contextSha256"], "dispatch excerpt hash")
    need(ev["path"] in file_pins and ev["fileSha256"] == file_pins[ev["path"]]["fileSha256"] and ev["gitBlob"] == file_pins[ev["path"]]["gitBlob"], "dispatch file pin")

cells = jl("current-target-cells.jsonl")
need(len(cells) == 240 == manifest["cellCount"], "current target cell count")
need([(r["position"], r["locale"]) for r in cells] == [(r["position"], loc) for r in selected for loc in LOCALES], "current target matrix order")
for cell in cells:
    src = by_id[cell["sourceId"]]
    need(cell["position"] == src["catalogZeroBasedIndex"] and cell["source"] == src["source"] and cell["sourceSha256"] == src["sourceSha256"], "current cell source binding")
    need(cell["locale"] in LOCALES and isinstance(cell["currentTarget"], str), "current target value")
    need(sha(cell["currentTarget"]) == cell["currentTargetSha256"], "current target hash")
    need(sha(cell["currentTarget"].encode("utf-8")) == cell["currentTargetSha256"], "raw target hash")
    need(sha(canon(cell["currentTarget"])) == cell["catalogTranslationHash"], "catalog translation hash")
    need(cell["callerContextSha256"] == next(c["callerContextSha256"] for c in contexts if c["sourceId"] == cell["sourceId"]), "current cell caller context pin")

prior = jl("prior-selection-reattestation.jsonl")
need(len(prior) == 100 == manifest["priorSelectedSourceCount"], "prior selected source count")
need(dict(collections.Counter(r["priorWindow"] for r in prior)) == {"W385-W404":20,"W405-W424":20,"W425-W444":20,"W445-W464":20,"W465-W484":20}, "prior selection window counts")
need(len({r["sourceId"] for r in prior}) == 100, "unique prior selected sources")
for row in prior:
    need(row["selectionUnchanged"] and row["sourceHashMatches"] and row["registryMembershipAndHashMatch"] and row["selectionPositionMatches"], "prior selection lineage unchanged")
    current = by_id.get(row["sourceId"])
    need(current is not None and current["sourceSha256"] == row["currentSourceSha256"], "prior selection current catalog source")
    if "catalog insertion index" in row["selectionPositionBasis"]:
        need(row["catalogZeroBasedIndex"] == row["priorWindowPosition"], "prior selection catalog position")
    else:
        need(row["currentRegistryRank"] == row["priorWindowPosition"], "prior selection registry rank")
prior_summary = j("prior-selection-reattestation-summary.json")
need(prior_summary["allPriorSelectionsMatchCurrentCatalogAndRegistry"] is True and prior_summary["currentHead"] == HEAD and prior_summary["currentTree"] == TREE, "prior selection summary")

holds = jl("prior-hold-reattestation.jsonl")
expected_holds = {"W245-W264":72,"W265-W284":168,"W285-W304":24,"W325-W344":24,"W405-W424":48,"W425-W444":12,"W445-W464":36,"W465-W484":60}
need(len(holds) == 444 == manifest["priorHoldCellCount"], "prior hold cell count")
need(dict(collections.Counter(r["window"] for r in holds)) == expected_holds, "prior hold window counts")
for row in holds:
    need(row["sourceMatchesCurrentCatalog"] and row["selectionPositionMatches"] and row["targetUnchanged"], "prior hold hash reattestation")
    need(len(row["priorHoldEvidenceSha256"]) == 64 and len(row["currentTargetSha256"]) == 64, "hash-only hold lineage")
    current = by_id.get(row["sourceId"])
    need(current is not None and current["sourceSha256"] == row["currentSourceSha256"], "prior hold current source")
    if "catalog insertion index" in row["selectionPositionBasis"]:
        need(row["currentCatalogIndex"] == row["position"], "prior hold catalog position")
    else:
        need(row["currentRegistryRank"] == row["position"], "prior hold registry rank")
hold_summary = j("prior-hold-reattestation-summary.json")
need(hold_summary["allSourcesAndSelectionPositionsMatchCurrentSnapshot"] is True and hold_summary["allCurrentTargetHashesMatchPriorHoldEvidence"] is True and hold_summary["currentTargetChangedCells"] == 0, "prior hold summary")
need(hold_summary["currentHead"] == HEAD and hold_summary["currentTree"] == TREE, "prior hold summary refs")
need(manifest["priorSelectionsUnchanged"] is True and manifest["priorHoldTargetsUnchanged"] is True, "manifest lineage summary")

provenance = j("prior-lineage-provenance.json")
need(provenance["priorEvidenceCommit"] == HEAD and len(provenance["priorEvidenceManifestSha256"]) == 64 and len(provenance["primaryLedgerSha256"]) == 64, "prior evidence hash lineage")
need(provenance["primaryHoldCellCount"] == 60 and set(provenance["hashOnlyEvidenceFiles"]) >= {"cross-audit/primary-review/primary-ledger.jsonl", "cross-audit/cross-audit-ledger.jsonl", "application/evidence/apply-readback.jsonl"}, "hash-only prior evidence references")
need(all(len(v) == 64 for v in provenance["hashOnlyEvidenceFiles"].values()), "prior evidence file hash values")

print("PASS candidate-free W485-W504: exact OPEN/DRAFT PR/branch/pull refs before and after; 20 catalog sources × 12 locales (240 cells); 479-source registry and 1,836-message catalog pins; 100 prior selected sources and 444 prior hold hashes reattested unchanged; no proposal/decision fields; checksums and portable evidence verifier pass.")
