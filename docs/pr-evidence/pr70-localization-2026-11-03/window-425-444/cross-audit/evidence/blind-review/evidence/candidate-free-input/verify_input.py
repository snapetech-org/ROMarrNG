#!/usr/bin/env python3
from pathlib import Path
import collections
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
HEAD = "7681ea470ee0f387cd3a1a5be0541979d9cd06f6"
TREE = "f8b34f29814233cb10dd9d608d5a69ce539b9f6d"
BRANCH = "task/localization-translation-review-20261030"
WINDOW = "W425-W444"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PROTECTED = ["ROMarr", "GG Requestz", "RomM", "ROMm", "ES-DE", "gamelist.xml", "1G1R", "Battle.net", "No-Intro", "Redump", "RetroArch", "Steam", "EA", "Epic", "ROM", "Hub", "DAT"]
TOKEN_RE = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")

def fail(message):
    raise SystemExit("FAIL: " + message)

def ok(value, message):
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

def protected_terms(text):
    hits = []
    for term in PROTECTED:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text):
            hits.append(term)
    return sorted(hits, key=lambda term: text.find(term))

sums_file = HERE / "SHA256SUMS.txt"
checksum_rows = {}
for line in sums_file.read_text(encoding="utf-8").splitlines():
    digest, name = line.split("  ", 1)
    ok(name not in checksum_rows, "duplicate checksum path " + name)
    checksum_rows[name] = digest
actual_files = {p.name for p in HERE.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"}
ok(set(checksum_rows) == actual_files, "checksum inventory")
for name, digest in checksum_rows.items():
    ok(sha((HERE / name).read_bytes()) == digest, "checksum " + name)

manifest = j("manifest.json")
attestation = j("PR-attestation.json")
pins = j("catalog-file-pins.json")
selection = j("selection.json")
ok(manifest["head"] == HEAD and manifest["tree"] == TREE and manifest["branch"] == BRANCH, "exact manifest refs")
ok(manifest["window"] == WINDOW and manifest["sourceCount"] == 20 and manifest["localeCount"] == 12 and manifest["cellCount"] == 240, "window coverage")
ok(manifest["locales"] == LOCALES and manifest["candidateFree"] is True, "candidate-free manifest")
ok(manifest["proposedTargetsIncluded"] is False and manifest["reviewDecisionsIncluded"] is False, "candidate-free boundary")
ok(selection["candidateFree"] is True and not selection["proposedTargetsIncluded"] and not selection["reviewDecisionsIncluded"], "selection boundary")
ok(attestation["repository"] == "snapetech-org/ROMarrNG" and attestation["pullRequest"] == 70 and attestation["branch"] == BRANCH, "PR attestation identity")
ok(attestation["bothObservationsMatchPinnedHeadAndTree"] is True, "before/after attestation summary")
for label in ("observedBefore", "observedAfter"):
    observed = attestation[label]
    ok(observed["state"] == "OPEN" and observed["isDraft"] is True, label + " PR state")
    ok(observed["headRefName"] == BRANCH and observed["baseRefName"] == "main", label + " branch")
    ok(observed["headRefOid"] == observed["liveBranchRefOid"] == observed["livePullRefOid"] == HEAD, label + " branch/pull refs")
    ok(observed["headTree"] == TREE, label + " tree")
    ok(observed["url"] == "https://github.com/snapetech-org/ROMarrNG/pull/70", label + " PR url")
    ok(observed["baseRefOid"] == manifest["baseRefOid"], label + " base ref")
ok(attestation["observedBefore"]["headRefOid"] == attestation["observedAfter"]["headRefOid"], "head unchanged across packet creation")
ok(attestation["observedBefore"]["headTree"] == attestation["observedAfter"]["headTree"], "tree unchanged across packet creation")

queue_raw = (HERE / "source-queue.json").read_bytes()
snapshot = j("source-snapshot.json")
queue = json.loads(queue_raw)["messages"]
ok(sha(queue_raw) == manifest["sourceQueueSha256"] == pins["sourceQueueSha256"], "source queue hash")
ok(sha(canon(snapshot)) == manifest["sourceSnapshotSha256"] == pins["sourceSnapshotSha256"], "source snapshot hash")
ok(len(queue) == len(snapshot) == 479 == manifest["activeUniqueSourceIdCount"], "active source registry count")
registry_by_id = {}
for row in queue:
    key = row["id"]
    ok(key not in registry_by_id, "unique active source id " + key)
    registry_by_id[key] = row
    ok(snapshot.get(key) == row["sourceHash"], "source snapshot entry " + key)
sorted_ids = sorted(registry_by_id)
rank_by_id = {key: rank + 1 for rank, key in enumerate(sorted_ids)}
source_order_sha = sha(("\n".join(sorted_ids) + "\n").encode("utf-8"))
ok(source_order_sha == manifest["sourceIdOrderSha256"] == pins["sourceIdOrderSha256"], "active source id-order hash")
ok(pins["commit"] == HEAD and pins["tree"] == TREE, "catalog pin refs")

snapshot_file = (HERE / "source-snapshot.json").read_bytes()
ok(sha(canon(snapshot)) == manifest["sourceSnapshotSha256"], "snapshot canonical hash")
inventory = jl("catalog-source-inventory.jsonl")
ok(len(inventory) == 1836 == manifest["catalogMessageCount"], "catalog source inventory count")
ok([row["catalogZeroBasedIndex"] for row in inventory] == list(range(1836)), "catalog source inventory zero-based order")
ok([row["catalogOneBasedPosition"] for row in inventory] == list(range(1, 1837)), "catalog source inventory one-based order")
catalog_ids = [row["sourceId"] for row in inventory]
ok(len(set(catalog_ids)) == len(catalog_ids), "unique catalog ids")
key_order_sha = sha(("\n".join(catalog_ids) + "\n").encode("utf-8"))
ok(key_order_sha == manifest["catalogKeyOrderSha256"] == pins["catalogKeyOrderSha256"], "catalog key order hash")
ok(pins["catalogSha256"] == manifest["catalogSha256"], "catalog file pin hash")
for row in inventory:
    ok(sha(row["source"]) == row["sourceSha256"], "source text hash " + row["sourceId"])

selected = jl("source-inventory-selection.jsonl")
ok(len(selected) == 20, "selected source count")
ok([row["catalogZeroBasedIndex"] for row in selected] == list(range(425, 445)), "exact selected catalog indices")
ok([row["catalogOneBasedPosition"] for row in selected] == list(range(426, 446)), "exact selected catalog positions")
expected_slice = inventory[425:445]
ok([(a["sourceId"], a["source"], a["sourceSha256"]) for a in selected] == [(a["sourceId"], a["source"], a["sourceSha256"]) for a in expected_slice], "selected source inventory lineage")
ok(selection["selectedSources"] == selected, "selection manifest/file consistency")
ok(len(j("catalog-insertion-queue.json")) == 20, "catalog insertion queue count")
for index, row in enumerate(selected):
    ok(row["activeSourceRegistry"] == (row["sourceId"] in registry_by_id), "active source membership " + row["sourceId"])
    if row["activeSourceRegistry"]:
        reg = registry_by_id[row["sourceId"]]
        ok(row["activeSourceRank"] == rank_by_id[row["sourceId"]], "sorted active registry rank " + row["sourceId"])
        ok(row["registryLocations"] == reg.get("locations", []), "registry locations " + row["sourceId"])
    else:
        ok(row["activeSourceRank"] is None and row["registryLocations"] == [], "inactive source metadata " + row["sourceId"])

contexts = jl("source-contexts.jsonl")
ok(len(contexts) == 20, "source context coverage")
ctx_by_id = {row["sourceId"]: row for row in contexts}
ok(set(ctx_by_id) == {row["sourceId"] for row in selected}, "source context ids")
file_pins = pins["callerSourceFilePins"]
for row in contexts:
    selected_row = next(item for item in selected if item["sourceId"] == row["sourceId"])
    ok(row["position"] == selected_row["position"] and row["source"] == selected_row["source"] and row["sourceSha256"] == selected_row["sourceSha256"], "source context lineage " + row["sourceId"])
    refs = row["callerContextRefs"]
    ok(sha(canon(refs)) == row["callerContextSha256"], "aggregate caller context hash " + row["sourceId"])
    for ref in refs:
        path = ref["path"]
        ok(path in file_pins, "caller file pin exists " + path)
        ok(ref["fileSha256"] == file_pins[path]["fileSha256"] and ref["gitBlob"] == file_pins[path]["gitBlob"], "caller file pin " + path)
        ok(ref["lineStart"] <= ref["lineEnd"] and len(ref["contextLines"]) == ref["lineEnd"] - ref["lineStart"] + 1, "caller excerpt range " + path)
        body = {"path": path, "lineStart": ref["lineStart"], "lineEnd": ref["lineEnd"], "contextLines": ref["contextLines"]}
        ok(sha(canon(body)) == ref["contextSha256"], "caller excerpt hash " + path)
        count = sum(1 for line in ref["contextLines"] if ref["anchor"] and ref["anchor"] in line["text"])
        ok(count == ref["anchorOccurrences"] and bool(count) == ref["anchorFound"], "caller excerpt anchor " + path)
    ok(not any(k in row for k in ("decision", "proposal", "replacement", "selectedTarget")), "candidate-free source context")

audit = j("caller-search-audit.json")
ok(audit["commit"] == HEAD and audit["tree"] == TREE, "caller search exact refs")
ok(len(audit["queries"]) == 40 == manifest["callerSearchQueryCount"], "caller query count")
audit_pins = audit["filePins"]
for query in audit["queries"]:
    expected_source = next(item for item in selected if item["sourceId"] == query["sourceId"])
    expected_literal = expected_source["sourceId"] if query["queryKind"] == "source-id" else expected_source["source"]
    ok(query["literal"] == expected_literal, "caller search literal " + query["sourceId"])
    ok(query["matchCount"] == len(query["matches"]), "caller search match count " + query["sourceId"])
    for match in query["matches"]:
        path = match["path"]
        ok(path in audit_pins and path in file_pins, "caller search file pin " + path)
        ok(audit_pins[path] == file_pins[path], "caller search pin consistency " + path)
        ok(path.startswith("romarr/") and path.endswith((".py", ".js")), "caller search scope " + path)
        ok(query["literal"] in match["text"], "caller search exact line " + path)
        ok(match["line"] > 0, "caller search line number " + path)

dispatch = j("dispatch-mechanics.json")
ok(dispatch["head"] == HEAD and dispatch["tree"] == TREE, "dispatch exact refs")
for path, pin in dispatch["filePins"].items():
    ok(file_pins.get(path) == pin, "dispatch file pin " + path)
for ev in dispatch["evidence"]:
    path = ev["path"]
    ok(path in file_pins and ev["fileSha256"] == file_pins[path]["fileSha256"] and ev["gitBlob"] == file_pins[path]["gitBlob"], "dispatch evidence file pin " + path)
    ok(len(ev["contextLines"]) == ev["lineEnd"] - ev["lineStart"] + 1, "dispatch excerpt range " + path)
    body = {"path": path, "lineStart": ev["lineStart"], "lineEnd": ev["lineEnd"], "contextLines": ev["contextLines"]}
    ok(sha(canon(body)) == ev["contextSha256"], "dispatch excerpt hash " + path)
    anchor_count = sum(1 for line in ev["contextLines"] if ev["anchor"] in line["text"])
    ok(anchor_count == ev["anchorOccurrences"] and anchor_count > 0, "dispatch anchor " + path)

cells = jl("current-target-cells.jsonl")
ok(len(cells) == 240 == manifest["cellCount"], "current target cell count")
ok([(row["position"], row["locale"]) for row in cells] == [(source["position"], locale) for source in selected for locale in LOCALES], "source-locale cell matrix order")
mismatches = {"placeholder": [], "numeric": [], "protectedLiteral": []}
for cell in cells:
    source = next(row for row in selected if row["sourceId"] == cell["sourceId"])
    ok(cell["position"] == source["position"] and cell["source"] == source["source"] and cell["sourceSha256"] == source["sourceSha256"], "cell source lineage " + cell["sourceId"])
    ok(cell["locale"] in LOCALES and isinstance(cell["currentTarget"], str), "cell current target " + cell["sourceId"])
    ok(sha(cell["currentTarget"]) == cell["currentTargetSha256"], "raw current target hash " + cell["sourceId"])
    ok(sha(canon(cell["currentTarget"])) == cell["catalogTranslationHash"], "catalog target hash " + cell["sourceId"])
    ctx = ctx_by_id[cell["sourceId"]]
    ok(cell["callerContextSha256"] == ctx["callerContextSha256"], "cell caller context pin " + cell["sourceId"])
    src_tokens = TOKEN_RE.findall(cell["source"])
    tgt_tokens = TOKEN_RE.findall(cell["currentTarget"])
    src_nums = NUMBER_RE.findall(cell["source"])
    tgt_nums = NUMBER_RE.findall(cell["currentTarget"])
    src_literals = protected_terms(cell["source"])
    tgt_literals = [term for term in src_literals if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", cell["currentTarget"])]
    missing_literals = [term for term in src_literals if term not in tgt_literals]
    ok(cell["sourcePlaceholderTokens"] == src_tokens and cell["currentPlaceholderTokens"] == tgt_tokens, "placeholder token inventory " + cell["sourceId"])
    ok(cell["placeholderMultisetMatches"] == (sorted(src_tokens) == sorted(tgt_tokens)), "placeholder token check " + cell["sourceId"])
    ok(cell["sourceNumericTokens"] == src_nums and cell["currentNumericTokens"] == tgt_nums, "numeric token inventory " + cell["sourceId"])
    ok(cell["numericTokensPreserved"] == (src_nums == tgt_nums), "numeric token check " + cell["sourceId"])
    ok(cell["sourceProtectedLiterals"] == src_literals and cell["currentProtectedLiterals"] == tgt_literals and cell["missingProtectedLiterals"] == missing_literals, "protected literal inventory " + cell["sourceId"])
    ok(cell["protectedLiteralsPreserved"] == (not missing_literals), "protected literal check " + cell["sourceId"])
    identity = {"position": cell["position"], "sourceId": cell["sourceId"], "locale": cell["locale"]}
    if not cell["placeholderMultisetMatches"]:
        mismatches["placeholder"].append({**identity, "sourceTokens": src_tokens, "targetTokens": tgt_tokens})
    if not cell["numericTokensPreserved"]:
        mismatches["numeric"].append({**identity, "sourceTokens": src_nums, "targetTokens": tgt_nums})
    if missing_literals:
        mismatches["protectedLiteral"].append({**identity, "missing": missing_literals})

for kind, filename, field in [
    ("placeholder", "current-target-placeholder-mismatches.json", "currentTargetPlaceholderMismatches"),
    ("numeric", "current-target-numeric-mismatches.json", "currentTargetNumericMismatches"),
    ("protectedLiteral", "current-target-protected-literal-mismatches.json", "currentTargetProtectedLiteralMismatches")
]:
    report = j(filename)
    ok(report["mismatchCount"] == len(mismatches[kind]), "mismatch report count " + kind)
    ok(report["mismatches"] == mismatches[kind], "mismatch report contents " + kind)
    ok(manifest[field] == len(mismatches[kind]), "manifest mismatch count " + kind)

prior_selections = jl("prior-selection-reattestation.jsonl")
prior_selection_summary = j("prior-selection-reattestation-summary.json")
ok(len(prior_selections) == 40 == manifest["priorSelectedSourceCount"], "prior selection reattestation count")
ok(collections.Counter(row["priorWindow"] for row in prior_selections) == {"W385-W404": 20, "W405-W424": 20}, "prior selection window coverage")
for row in prior_selections:
    ok(row["selectionPositionMatches"] and row["sourceHashMatches"] and row["registryMembershipAndHashMatch"] and row["selectionUnchanged"], "prior selection unchanged " + row["sourceId"])
    if row["priorWindow"] == "W405-W424":
        ok(row["selectionPositionBasis"] == "catalog insertion index (zero-based)" and row["catalogZeroBasedIndex"] == row["priorWindowPosition"], "W405 selection position " + row["sourceId"])
    else:
        ok(row["selectionPositionBasis"] == "one-based rank in lexicographically sorted active source IDs" and row["currentRegistryRank"] == row["priorWindowPosition"], "W385 selection rank " + row["sourceId"])
ok(prior_selection_summary["allPriorSelectionsMatchCurrentCatalogAndRegistry"] is True, "prior selection summary")
ok(prior_selection_summary["currentHead"] == HEAD and prior_selection_summary["currentTree"] == TREE, "prior selection summary refs")

prior_holds = jl("prior-hold-reattestation.jsonl")
hold_summary = j("prior-hold-reattestation-summary.json")
ok(len(prior_holds) == 336 == manifest["priorHoldCellCount"], "prior hold reattestation count")
expected_hold_counts = {"W245-W264": 72, "W265-W284": 168, "W285-W304": 24, "W325-W344": 24, "W405-W424": 48}
ok(dict(collections.Counter(row["window"] for row in prior_holds)) == expected_hold_counts, "prior hold window coverage")
for row in prior_holds:
    ok(row["sourceMatchesCurrentCatalog"] and row["selectionPositionMatches"] and row["targetUnchanged"], "prior hold unchanged " + row["sourceId"])
    if row["window"] == "W405-W424":
        ok(row["selectionPositionBasis"] == "catalog insertion index (zero-based)" and row["currentCatalogIndex"] == row["position"], "W405 hold position " + row["sourceId"])
    else:
        ok(row["selectionPositionBasis"] == "one-based rank in lexicographically sorted active source IDs" and row["currentRegistryRank"] == row["position"], "prior hold source rank " + row["sourceId"])
ok(hold_summary["allSourcesAndSelectionPositionsMatchCurrentSnapshot"] is True, "prior hold source/position summary")
ok(hold_summary["allCurrentTargetHashesMatchPriorHoldEvidence"] is True and hold_summary["currentTargetChangedCells"] == 0, "prior hold target summary")
ok(hold_summary["currentHead"] == HEAD and hold_summary["currentTree"] == TREE, "prior hold summary refs")
ok(manifest["priorSelectionsUnchanged"] is True and manifest["priorHoldTargetsUnchanged"] is True, "manifest reattestation summaries")

provenance = j("prior-lineage-provenance.json")
ok(provenance["W405CurrentHoldPlanCommit"] == HEAD and provenance["W405CurrentHoldPlanPath"].endswith("window-405-424/hold-plan.jsonl"), "prior hold plan provenance")
ok(len(provenance["W405CurrentHoldPlanSha256"]) == 64 and len(provenance["W405CurrentHoldPlanGitBlob"]) == 40, "prior hold plan hashes")
ok(len(provenance["sourceCandidateFreeChecksumListSha256"]) == len(provenance["sourceCandidateFreeManifestSha256"]) == 64, "prior candidate-free provenance hashes")
ok(provenance["priorHoldRows"] == {"inherited": 288, "W405-W424": 48}, "prior hold provenance counts")

print(
    "PASS candidate-free W425-W444: exact OPEN/DRAFT PR/branch/pull refs before and after; "
    "20 catalog sources × 12 locales (240 cells); 479-source registry and 1,836-message catalog pins; "
    "40 prior selected sources and 336 prior holds reattested unchanged; "
    f"{len(mismatches['placeholder'])} placeholder, {len(mismatches['numeric'])} numeric, "
    f"{len(mismatches['protectedLiteral'])} protected-literal mismatches recorded; "
    "no proposed targets or current-window decisions; checksums and portable evidence verifier pass."
)

