from pathlib import Path
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone

REPO = Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-rebase-20261103/repo")
SCRATCH = Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-rebased-candidate-free-20261103")
OUT = SCRATCH / "input"
PREV = Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-candidate-free-20261103/input")
PREV_WINDOW = Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w365-384-candidate-free-20261103/input")
EXPECTED_HEAD = "0afd1d8c150fb96d868394a8d9620371db612185"
REPO_SLUG = "snapetech-org/ROMarrNG"
BRANCH = "task/localization-translation-review-20261030"
LOCALES_EXPECTED = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def raw_target_sha(value):
    return sha(value.encode("utf-8"))

def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def write_jsonl(name, rows):
    (OUT / name).write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()

def gh_json(endpoint):
    return json.loads(run(["gh", "api", endpoint]))

if OUT.exists() and any(OUT.iterdir()):
    raise SystemExit("Refusing to overwrite existing packet: " + str(OUT))
OUT.mkdir(parents=True, exist_ok=True)

head = run(["git", "-C", str(REPO), "rev-parse", "HEAD"])
tree = run(["git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"])
status = run(["git", "-C", str(REPO), "status", "--porcelain=v1"])
if head != EXPECTED_HEAD or status:
    raise SystemExit("Local source worktree is not the pinned clean head")
pr = gh_json("repos/" + REPO_SLUG + "/pulls/70")
branch_ref = gh_json("repos/" + REPO_SLUG + "/git/ref/heads/" + BRANCH)
pull_ref = gh_json("repos/" + REPO_SLUG + "/git/ref/pull/70/head")
gh_commit = gh_json("repos/" + REPO_SLUG + "/commits/" + head)
assert pr["state"] == "open" and pr["draft"] is True
assert pr["head"]["ref"] == BRANCH and pr["head"]["sha"] == head
assert pr["base"]["ref"] == "main"
assert branch_ref["object"]["sha"] == pull_ref["object"]["sha"] == head
assert gh_commit["sha"] == head and gh_commit["commit"]["tree"]["sha"] == tree
assert head == EXPECTED_HEAD

queue_bytes = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:romarr/ui-source-messages.json"], check=True, stdout=subprocess.PIPE).stdout
catalog_bytes = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:romarr/ui-labels.json"], check=True, stdout=subprocess.PIPE).stdout
assert queue_bytes == (REPO / "romarr/ui-source-messages.json").read_bytes()
assert catalog_bytes == (REPO / "romarr/ui-labels.json").read_bytes()
queue_obj = json.loads(queue_bytes)
catalog = json.loads(catalog_bytes)
messages = queue_obj["messages"]
ids = [m["id"] for m in messages]
sorted_messages = sorted(messages, key=lambda m: m["id"])
sorted_ids = [m["id"] for m in sorted_messages]
assert len(messages) == 479 and len(set(ids)) == 479
source_order_sha = sha(("\n".join(sorted_ids) + "\n").encode("utf-8"))
catalog_order_sha = sha(("\n".join(catalog["messages"].keys()) + "\n").encode("utf-8"))
selected = sorted_messages[384:404]
assert len(selected) == 20
locales = selected[0]["pendingLocales"]
assert locales == LOCALES_EXPECTED
assert all(m["pendingLocales"] == locales for m in selected)
assert len(catalog["messages"]) == 1836
source_position = {m["id"]: i for i, m in enumerate(sorted_messages, 1)}
source_by_id = {m["id"]: m for m in messages}
catalog_messages = catalog["messages"]

# Keep only explicit product/format literals from the shared glossary plus common protocol acronyms.
protected_names = ["ROMarr", "SeerrNG", "Prowlarr", "No-Intro", "Redump", "IGDB", "Steam", "EmuDeck", "ES-DE", "TitleDB", "ROM", "DAT", "TOTP", "URI", "HTTP", "SHA-1", "SHA-256", "CRC32"]
ph_re = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
num_re = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
def protected_literals(s):
    found = []
    for token in protected_names:
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])")
        match = pattern.search(s)
        if match:
            found.append((match.start(), token))
    return [token for _, token in sorted(found)]

def locale_tokens(s):
    return {
        "placeholders": ph_re.findall(s),
        "numbers": num_re.findall(s),
    }

# Exact source/caller snippets at the pinned tree. Caller references include direct source
# sites plus their API/UI surfaces where the message crosses a runtime boundary.
ref_specs = {
 385: [("romarr/connect.py",327,347,"direct source: EA account setup help template"),("romarr/ui.py",1024,1040,"UI caller: exact allowlisted connect help template"),("romarr/ui.py",885,890,"UI renderer: localized template and escaped placeholders")],
 386: [("romarr/connect.py",300,314,"direct source: Epic sign-in help template"),("romarr/ui.py",1024,1040,"UI caller: exact allowlisted connect help template"),("romarr/ui.py",885,890,"UI renderer: localized template and escaped placeholders")],
 387: [("romarr/connect.py",354,364,"direct source: Blizzard JSON-list help"),("romarr/ui.py",1024,1040,"UI caller: exact allowlisted connect help template"),("romarr/ui.py",885,890,"UI renderer: localized template and escaped placeholders")],
 388: [("romarr/connect.py",272,285,"direct source: GOG username and public-profile help template"),("romarr/ui.py",1024,1040,"UI caller: exact allowlisted connect help template"),("romarr/ui.py",885,890,"UI renderer: localized template and escaped placeholders")],
 389: [("romarr/connect.py",224,230,"direct source: PlayStation NPSSO help template"),("romarr/ui.py",1024,1040,"UI caller: exact allowlisted connect help template"),("romarr/ui.py",885,890,"UI renderer: localized template and escaped placeholders")],
 390: [("romarr/ui.py",4992,4998,"direct source and UI caller: platform technical-details column heading"),("romarr/ui.py",1308,1312,"UI renderer: locale-aware visible text-tree translation")],
 391: [("romarr/ui.py",2583,2588,"direct source and UI caller: catalog-sort control label"),("romarr/ui.py",1225,1245,"UI renderer: stable catalog key label translation")],
 392: [("romarr/organizer.py",1846,1852,"direct source: blocked organizer rename-plan reason"),("romarr/app.py",6779,6784,"API caller: return rename-plan blocked rows"),("romarr/ui.py",5921,5925,"UI caller: render blocked reason in rename preview"),("romarr/ui.py",5741,5750,"UI renderer: exact organizer-message allowlist and key lookup"),("romarr/ui.py",1042,1049,"fallback renderer: unmatched API messages stay opaque")],
 393: [("romarr/ui.py",5768,5774,"direct source and UI caller: status announcement with nested state and count placeholders"),("romarr/ui.py",885,890,"UI renderer: localized template formatting and RTL metadata")],
 394: [("romarr/ui.py",5768,5780,"direct source and UI caller: status-state label"),("romarr/ui.py",882,883,"UI renderer: catalog-key label translation"),("romarr/ui.py",1295,1312,"UI renderer: translated visible text tree")],
 395: [("romarr/app.py",4461,4485,"direct source: explicit truncated hash-read detail template"),("romarr/ui.py",3343,3349,"UI caller: render hash-read detail through the explicit template guard"),("romarr/ui.py",957,961,"UI renderer: allowlisted status-template key"),("romarr/ui.py",994,1023,"UI renderer: validate explicit template and placeholder values"),("romarr/ui.py",1042,1049,"API fallback: opaque dynamic values")],
 396: [("romarr/playability.py",1813,1819,"direct source: Moonlight PIN submission status and fixed source ID"),("romarr/app.py",3637,3648,"API caller: submit Moonlight PIN"),("romarr/ui.py",4902,4909,"UI caller: show submit result via source-bound Moonlight renderer"),("romarr/ui.py",1050,1063,"UI renderer: exact Moonlight allowlist, source equality guard, opaque fallback")],
 397: [("romarr/ui.py",5779,5785,"direct source and UI caller: organizer suggestions count template"),("romarr/ui.py",885,890,"UI renderer: localized template formatting")],
 398: [("romarr/playability.py",1737,1746,"direct source: fixed Sunshine pairing capability diagnostic and source ID"),("romarr/app.py",3617,3635,"service caller: Moonlight host status"),("romarr/app.py",6992,6993,"API caller: return Moonlight status"),("romarr/ui.py",4863,4868,"UI caller: render pairing detail by exact source ID"),("romarr/ui.py",1050,1063,"UI renderer: exact Moonlight allowlist, source equality guard, opaque fallback")],
 399: [("romarr/playability.py",1804,1812,"direct source: fixed Sunshine no-pending-client response and source ID"),("romarr/app.py",3637,3648,"service caller: submit Moonlight PIN"),("romarr/app.py",8000,8001,"API caller: return PIN submission response"),("romarr/ui.py",4902,4909,"UI caller: render PIN response by exact source ID"),("romarr/ui.py",1050,1063,"UI renderer: exact Moonlight allowlist, source equality guard, opaque fallback")],
 400: [("romarr/ui.py",4235,4238,"direct source and UI caller: Switch DLC folder setting label"),("romarr/ui.py",1295,1312,"UI renderer: locale-aware visible text-tree translation")],
 401: [("romarr/ui.py",5822,5825,"direct source and UI caller: Switch family table heading"),("romarr/ui.py",1295,1312,"UI renderer: locale-aware visible text-tree translation")],
 402: [("romarr/ui.py",4234,4237,"direct source and UI caller: TitleDB-based Switch folder-routing help"),("romarr/ui.py",1295,1312,"UI renderer: locale-aware visible text-tree translation")],
 403: [("romarr/ui.py",5707,5710,"direct source and UI caller: Switch title-ID rename safety help"),("romarr/ui.py",1295,1312,"UI renderer: locale-aware visible text-tree translation")],
 404: [("romarr/ui.py",4235,4238,"direct source and UI caller: Switch update folder setting label"),("romarr/ui.py",1295,1312,"UI renderer: locale-aware visible text-tree translation")],
}

notes = {
 385:"EA credential setup help uses a fixed source template with JSON example and provider-message placeholders. The template key and caller are validated; preserve {example}, {provider_message}, EA, and Playnite semantics. The provider-message value is opaque data.",
 386:"Epic login help uses a fixed source template with a JSON authorization-code example. Preserve {example}, Epic, ROMarr, and the single-use/short-lived credential meaning.",
 387:"Blizzard help tells users to paste a complete JSON games list and says it is data, not a credential. Preserve Blizzard and JSON as technical/product literals.",
 388:"GOG help uses JSON example and settings-URL placeholders. Preserve {example}, {settings_url}, GOG, and the public-profile requirement; do not turn the username into a token.",
 389:"PlayStation NPSSO help uses a JSON example placeholder; preserve {example} and distinguish the value between quotes from the whole JSON object.",
 390:"Platform technical-details table header for per-platform maximum file size. Keep it concise and technical.",
 391:"Sort-control label for the current catalog page, not a global page-navigation command.",
 392:"Fixed app-owned blocked reason in rename-plan rows. The backend returns it through the organizer API; the UI exact organizer allowlist now includes this stable source key. Unknown API text remains on the opaque renderer.",
 393:"Organizer scan announcement template with a nested fixed state label and formatted processed/total counts. Preserve {state}, {processed}, and {total}; only the state label is application-owned text.",
 394:"Organizer status enum label shown when its state is unavailable. It is an application-owned fixed label passed to interfaceMarkup.",
 395:"Truncated library-hash read result uses an explicit catalog template. Preserve {seen}, {truncated}, and {added}; the truncation explanation is a dynamic value, while counts are formatted by the renderer.",
 396:"Fixed status returned after a Moonlight PIN submission. The local source branch attaches the stable ID and the UI translates only an allowlisted ID whose catalog source exactly equals this detail; unknown or mismatched API text stays opaque. Do not imply that the host confirmed the PIN was correct.",
 397:"Organizer status count label for proposed metadata matches. Preserve {count}; do not imply accepted or applied suggestions.",
 398:"Fixed Sunshine capability diagnostic explaining that the API cannot list waiting clients. The local status branch attaches the stable ID and the UI translates only an allowlisted ID whose catalog source exactly equals this detail; unknown or mismatched API text stays opaque. Preserve Sunshine and Moonlight as names and the operational instruction.",
 399:"Fixed Sunshine refusal when no Moonlight client is waiting. The fixed local response attaches the stable ID and the UI translates only an allowlisted ID whose catalog source exactly equals this detail; unknown or mismatched API text stays opaque. Preserve that pairing must be started on the client first.",
 400:"Settings label for the Switch DLC destination folder.",
 401:"Column heading for the Nintendo Switch family grouping in the organizer library table.",
 402:"Settings help for filename-based Switch IDs and TitleDB classification. Preserve TitleDB and the limitation that filename metadata does not verify package bytes.",
 403:"Organizer help for Switch title IDs and versions. Preserve TitleDB and DAT, and retain that exact checksums or manual confirmation are required for rename.",
 404:"Settings label for the Switch updates destination folder.",
}

api_opaque = set()
newly_renderable_dispatch_positions = [392,396,398,399]
ambiguous_positions = []


def file_pin(path):
    p = REPO / path
    data = p.read_bytes()
    blob = run(["git", "-C", str(REPO), "rev-parse", "HEAD:" + path])
    return data, sha(data), blob

def make_ref(path, start, end, role):
    data, file_sha, blob = file_pin(path)
    lines = data.decode("utf-8").splitlines()
    if not (1 <= start <= end <= len(lines)):
        raise SystemExit("Invalid context range " + path + ":" + str(start) + "-" + str(end))
    context = [{"line": i, "text": lines[i-1]} for i in range(start, end + 1)]
    context_hash = sha(canon({"path":path,"lineStart":start,"lineEnd":end,"contextLines":context}))
    return {
        "contextLines": context,
        "contextSha256": context_hash,
        "fileSha256": file_sha,
        "gitBlob": blob,
        "lineEnd": end,
        "lineStart": start,
        "path": path,
        "role": role,
    }

def check_source_occurrence(position, source, refs):
    combined = "\n".join(line["text"] for ref in refs for line in ref["contextLines"])
    fragments = {
      385: ["Sign in if asked; the page then shows", "{provider_message}", "connectHowMarkup"],
      386: ["Sign in there; the page ends up showing", "ROMarr swaps it for a refresh token"],
      387: ["Signed in to Blizzard, that page is a plain JSON list", "nothing secret is stored"],
      388: ["Signed in to GOG, that page shows", "{settings_url}", "no token"],
      389: ["Signed in to playstation.com, this page shows", "{example}"],
      390: ["Size ceiling"],
      391: ["Sort this page"],
      392: ["Source file is missing or is a symlink", "rename_plan", "organizerApiMessageMarkup"],
      393: ["{state}. {processed} of {total} files checked."],
      394: ["unavailable:'Status unavailable'"],
      395: ["ui.stopped-after-seen-entries-truncated.fc5c0496ad", "detail_template", "Stopped after {seen:,} entries:"],
      396: ["Submitted. The host does not report whether the ", "appears in the paired list.", "moonlightApiMessageMarkup("],
      397: ["Suggestions {count}"],
      398: ["Sunshine has no endpoint that lists waiting clients", "then type the PIN it shows.", "moonlightApiMessageMarkup(", "detail_source_id"],
      399: ["Sunshine refused it: no Moonlight", "pairing on your client first.", "moonlightApiMessageMarkup(", "detail_source_id"],
      400: ["Switch DLC folder"],
      401: ["Switch family"],
      402: ["Switch IDs and version numbers come from the filename and TitleDB."],
      403: ["Switch title IDs and versions are read from filenames and TitleDB."],
      404: ["Switch updates folder"],
    }
    for fragment in fragments[position]:
        assert fragment in combined, "pinned source/caller fragment missing at position " + str(position) + ": " + fragment


def main():
    selected_rows = []
    context_rows = []
    current_cells = []
    placeholder_mismatches = []
    numeric_mismatches = []
    protected_mismatches = []
    source_context_files = {}

    for position, message in enumerate(selected, 385):
        source = message["source"]
        source_sha = message["sourceHash"]
        assert sha(source.encode("utf-8")) == source_sha
        catalog_row = catalog_messages[message["id"]]
        assert catalog_row["source"] == source and catalog_row["sourceHash"] == source_sha
        source_protected = protected_literals(source)
        source_numbers = num_re.findall(source)
        refs = [make_ref(*spec) for spec in ref_specs[position]]
        check_source_occurrence(position, source, refs)
        for ref in refs:
            source_context_files[ref["path"]] = {"fileSha256":ref["fileSha256"],"gitBlob":ref["gitBlob"]}
        ref_hash = sha(json.dumps(refs, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        selected_rows.append({
            "dynamicPlaceholders": message.get("dynamicPlaceholders", []),
            "position": position,
            "reportedLocations": message.get("locations", []),
            "source": source,
            "sourceId": message["id"],
            "sourceKind": message["category"],
            "sourceNumericTokens": source_numbers,
            "sourceProtectedLiterals": source_protected,
            "sourceSha256": source_sha,
        })
        context_rows.append({
            "ambiguousContext": position in ambiguous_positions,
            "ambiguityNotes": notes[position] if position in ambiguous_positions else "",
            "callerContextRefs": refs,
            "callerContextSha256": ref_hash,
            "callerResolutionHold": False,
            "callerResolutionRationale": "Exact source occurrence and caller/API/UI context are pinned in callerContextRefs.",
            "localizableUiMessageEstablished": True,
            "localizationDispatchObservation": notes[position],
            "position": position,
            "reportedLocations": message.get("locations", []),
            "source": source,
            "sourceId": message["id"],
            "sourceKind": message["category"],
            "sourceSha256": source_sha,
            "translationDispatchGap": position in api_opaque,
        })
        for locale in locales:
            target = catalog_row["translations"][locale]
            target_canonical_hash = sha(canon(target))
            assert catalog_row["translationHashes"][locale] == target_canonical_hash
            src_ph = ph_re.findall(source)
            dst_ph = ph_re.findall(target)
            src_nums = num_re.findall(source)
            dst_nums = num_re.findall(target)
            current_protected = [t for t in source_protected if re.search(r"(?<![A-Za-z0-9])"+re.escape(t)+r"(?![A-Za-z0-9])", target)]
            missing_protected = [t for t in source_protected if t not in current_protected]
            row = {
                "callerContextSha256": ref_hash,
                "catalogPath": "romarr/ui-labels.json",
                "catalogTranslationHash": target_canonical_hash,
                "currentNumericTokens": dst_nums,
                "currentPlaceholderTokens": dst_ph,
                "currentProtectedLiterals": current_protected,
                "currentTarget": target,
                "currentTargetSha256": raw_target_sha(target),
                "locale": locale,
                "missingProtectedLiterals": missing_protected,
                "numericTokensPreserved": src_nums == dst_nums,
                "placeholderMultisetMatches": sorted(src_ph) == sorted(dst_ph),
                "placeholderTokens": src_ph,
                "position": position,
                "protectedLiteralsPreserved": not missing_protected,
                "source": source,
                "sourceId": message["id"],
                "sourceNumericTokens": src_nums,
                "sourceProtectedLiterals": source_protected,
                "sourceSha256": source_sha,
                "translationStatus": catalog_row.get("translationStatus", {}).get(locale, "missing"),
            }
            current_cells.append(row)
            mismatch = {
                "currentTarget": target,
                "currentTargetSha256": row["currentTargetSha256"],
                "locale": locale,
                "position": position,
                "source": source,
                "sourceId": message["id"],
            }
            if not row["placeholderMultisetMatches"]:
                placeholder_mismatches.append(mismatch)
            if not row["numericTokensPreserved"]:
                numeric_mismatches.append(mismatch)
            if not row["protectedLiteralsPreserved"]:
                protected_mismatches.append({**mismatch,"missingProtectedLiterals":missing_protected})

    (OUT / "source-queue.json").write_bytes(queue_bytes)
    source_snapshot = {m["id"]:m["sourceHash"] for m in messages}
    write_json("source-snapshot.json", source_snapshot)
    write_jsonl("source-inventory-selection.jsonl", selected_rows)
    write_jsonl("source-contexts.jsonl", context_rows)
    write_jsonl("current-target-cells.jsonl", current_cells)
    write_json("current-target-placeholder-mismatches.json", {"mismatchCount":len(placeholder_mismatches),"mismatches":placeholder_mismatches})
    write_json("current-target-numeric-mismatches.json", {"mismatchCount":len(numeric_mismatches),"mismatches":numeric_mismatches})
    write_json("current-target-protected-literal-mismatches.json", {"mismatchCount":len(protected_mismatches),"mismatches":protected_mismatches})

    boundary_specs = [(384,"previous-window-final"),(385,"selected-start"),(404,"selected-end"),(405,"next-source")]
    boundary_rows = []
    for pos, role in boundary_specs:
        m = sorted_messages[pos-1]
        boundary_rows.append({"position":pos,"role":role,"source":m["source"],"sourceId":m["id"],"sourceSha256":m["sourceHash"]})
    write_jsonl("selection-boundary.jsonl", boundary_rows)
    selection = {
        "window":"W385-W404",
        "method":"Sort all unique active IDs lexicographically by stable ID; reattest W365-W384; select the immediate next 20 IDs.",
        "activeUniqueSourceIds":len(sorted_ids),
        "sourceIdOrderSha256":source_order_sha,
        "priorWindow":"W365-W384",
        "priorWindowPositions":[365,384],
        "priorWindowSelectionReattested":True,
        "positions":[385,404],
        "sourceCount":20,
        "localeCount":len(locales),
        "cellCount":len(current_cells),
        "localeOrder":locales,
        "boundaries":boundary_rows,
        "selectedSources":[{"position":i,"sourceId":m["id"],"source":m["source"],"sourceSha256":m["sourceHash"]} for i,m in enumerate(selected,385)],
    }
    write_json("selection.json", selection)

    prev_manifest = json.loads((PREV_WINDOW / "manifest.json").read_text(encoding="utf-8"))
    prev_selection = json.loads((PREV_WINDOW / "selection.json").read_text(encoding="utf-8"))
    prev_sources = [json.loads(x) for x in (PREV_WINDOW / "source-inventory-selection.jsonl").read_text(encoding="utf-8").splitlines() if x]
    assert prev_manifest["window"] == "W365-W384"
    prior_window_rows = []
    for row in prev_sources:
        position = row["position"]
        current = sorted_messages[position-1]
        prior_window_rows.append({
            "currentSourceId":current["id"],
            "currentSourceSha256":current["sourceHash"],
            "matchesCurrentQueue":current["id"]==row["sourceId"] and current["sourceHash"]==row["sourceSha256"],
            "position":position,
            "sourceId":row["sourceId"],
            "sourceSha256":row["sourceSha256"],
        })
    assert len(prior_window_rows)==20 and all(r["matchesCurrentQueue"] for r in prior_window_rows)
    write_jsonl("prior-window-reattestation.jsonl", prior_window_rows)
    prior_window_selection = {
        "priorWindow":"W365-W384",
        "priorHead":prev_manifest["head"],
        "priorTree":prev_manifest["tree"],
        "priorInputChecksumListSha256":sha((PREV/"SHA256SUMS.txt").read_bytes()),
        "priorInputManifestJsonSha256":sha((PREV/"manifest.json").read_bytes()),
        "positions":[365,384],
        "sourceOrderSha256":source_order_sha,
        "selectedSources":[{"position":r["position"],"sourceId":r["sourceId"],"sourceSha256":r["sourceSha256"]} for r in prev_sources],
    }
    write_json("prior-window-selection.json", prior_window_selection)
    write_json("prior-window-reattestation-summary.json",{
        "priorWindow":"W365-W384",
        "priorHead":prev_manifest["head"],
        "priorTree":prev_manifest["tree"],
        "currentHead":head,
        "currentTree":tree,
        "currentSourceOrderSha256":source_order_sha,
        "reattestedSources":len(prior_window_rows),
        "allPriorSourceIdsAndHashesMatchCurrentQueue":all(r["matchesCurrentQueue"] for r in prior_window_rows),
        "priorWindowHoldCells":prev_manifest.get("callerResolutionHoldCells",0),
        "priorWindowHoldPositions":prev_manifest.get("callerResolutionHoldPositions",[]),
    })

    previous_holds = [json.loads(x) for x in (PREV / "prior-hold-reattestation.jsonl").read_text(encoding="utf-8").splitlines() if x]
    prior_holds = []
    for row in previous_holds:
        source = source_by_id.get(row["sourceId"])
        position_now = source_position.get(row["sourceId"])
        catalog_row = catalog_messages.get(row["sourceId"])
        if source is None or catalog_row is None:
            raise SystemExit("Prior hold source disappeared from current queue/catalog")
        locale = row["locale"]
        target = catalog_row["translations"][locale]
        target_hash = raw_target_sha(target)
        prior_hash = row.get("priorCurrentTargetSha256", row.get("currentTargetSha256"))
        prior_holds.append({
            "currentTargetSha256":target_hash,
            "locale":locale,
            "position":row["position"],
            "positionMatchesCurrentQueue":position_now==row["position"],
            "priorCurrentTargetSha256":prior_hash,
            "sourceId":row["sourceId"],
            "sourceMatchesCurrentQueue":source["sourceHash"]==row["sourceSha256"],
            "sourceSha256":source["sourceHash"],
            "targetUnchanged":target_hash==prior_hash,
            "window":row["window"],
        })
    assert len(prior_holds)==288 and all(r["targetUnchanged"] and r["sourceMatchesCurrentQueue"] and r["positionMatchesCurrentQueue"] for r in prior_holds)
    write_jsonl("prior-hold-reattestation.jsonl",prior_holds)
    hold_counts={}
    for row in prior_holds: hold_counts[row["window"]]=hold_counts.get(row["window"],0)+1
    write_json("prior-hold-reattestation-summary.json",{
        "candidateFreeHoldPackets":["W245-W264","W265-W284","W285-W304","W325-W344"],
        "reattestedCellCount":len(prior_holds),
        "sourceAndPositionMatches":all(r["sourceMatchesCurrentQueue"] and r["positionMatchesCurrentQueue"] for r in prior_holds),
        "allCurrentTargetHashesMatchPriorHoldEvidence":all(r["targetUnchanged"] for r in prior_holds),
        "windowCounts":hold_counts,
        "note":"W305-W324 application summary records zero holds; carry-forward covers the candidate-free callerless hold ledgers available at this input head.",
    })

    locale_metadata={loc:catalog["locales"][loc] for loc in locales}
    catalog_pins={
        "commit":head,
        "tree":tree,
        "activeUniqueSourceIds":len(sorted_ids),
        "catalogMessageCount":len(catalog_messages),
        "baseLocale":catalog["baseLocale"],
        "locales":locales,
        "localeMetadata":locale_metadata,
        "catalogSha256":sha(catalog_bytes),
        "catalogKeyOrderSha256":catalog_order_sha,
        "sourceQueueSha256":sha(queue_bytes),
        "sourceQueuePath":"romarr/ui-source-messages.json",
        "sourceSnapshotSha256":sha(canon(source_snapshot)),
        "callerSourceFilePins":source_context_files,
    }
    write_json("catalog-file-pins.json",catalog_pins)
    body_sha=sha(pr["body"].encode("utf-8"))
    attestation={
        "repository":REPO_SLUG,
        "pullRequest":70,
        "url":pr["html_url"],
        "state":pr["state"].upper(),
        "isDraft":pr["draft"],
        "baseRefName":pr["base"]["ref"],
        "baseRefOid":pr["base"]["sha"],
        "headRefName":pr["head"]["ref"],
        "headRefOid":pr["head"]["sha"],
        "headTree":tree,
        "liveBranchRefOid":branch_ref["object"]["sha"],
        "livePullRefOid":pull_ref["object"]["sha"],
        "prBodySha256":body_sha,
        "checkedAtUtc":datetime.now(timezone.utc).isoformat(),
    }
    write_json("PR-attestation.json",attestation)
    source_context_holds=[]
    ambiguous_cells=len(ambiguous_positions)*len(locales)
    created=datetime.now(timezone.utc).isoformat()
    manifest={
        "artifact":"ROMarrNG PR #70 W385-W404 candidate-free input",
        "repository":REPO_SLUG,
        "pullRequest":70,
        "branch":BRANCH,
        "baseRefName":pr["base"]["ref"],
        "baseRefOid":pr["base"]["sha"],
        "head":head,
        "tree":tree,
        "window":"W385-W404",
        "sourceCount":20,
        "localeCount":len(locales),
        "cellCount":len(current_cells),
        "locales":locales,
        "activeUniqueSourceIdCount":len(sorted_ids),
        "sourceIdOrderSha256":source_order_sha,
        "catalogMessageCount":len(catalog_messages),
        "catalogPath":"romarr/ui-labels.json",
        "catalogSha256":sha(catalog_bytes),
        "catalogKeyOrderSha256":catalog_order_sha,
        "priorWindow":"W365-W384",
        "priorWindowReattested":True,
        "priorHoldCellCount":len(prior_holds),
        "priorHoldTargetsUnchanged":all(r["targetUnchanged"] for r in prior_holds),
        "currentTargetPlaceholderMismatches":len(placeholder_mismatches),
        "currentTargetNumericMismatches":len(numeric_mismatches),
        "currentTargetProtectedLiteralMismatches":len(protected_mismatches),
        "callerResolutionHoldPositions":source_context_holds,
        "callerResolutionHoldCells":0,
        "translationDispatchGapPositions":sorted(api_opaque),
        "translationDispatchGapCells":len(api_opaque)*len(locales),
        "newlyRenderableDispatchPositions":newly_renderable_dispatch_positions,
        "newlyRenderableDispatchCells":len(newly_renderable_dispatch_positions)*len(locales),
        "previouslyOpaqueDispatchCellsNowRenderable":len(newly_renderable_dispatch_positions)*len(locales),
        "callerlessSourcePositions":[],
        "callerlessCells":0,
        "ambiguousCallerPositions":ambiguous_positions,
        "ambiguousCallerCells":ambiguous_cells,
        "candidateFree":True,
        "proposedTargetsIncluded":False,
        "reviewDecisionsIncluded":False,
        "sourceQueuePath":"romarr/ui-source-messages.json",
        "sourceQueueSha256":sha(queue_bytes),
        "sourceSnapshotSha256":sha(canon(source_snapshot)),
        "createdUtc":created,
        "ambiguousCallerNotes":[],
        "reviewBoundary":"No proposed targets, primary decisions, or blind-review material are included.",
        "candidateFreeBasisHead":"8a15dd1c3487d17e62d78a1b80222b7eb6033c6b",
        "candidateFreeBasisTree":"452cda96454624cfa7068b9925d15e821d4828f7",
        "candidateFreeBasisInputChecksumListSha256":sha((PREV/"SHA256SUMS.txt").read_bytes()),
        "newlyRenderableDispatchPositions":newly_renderable_dispatch_positions,
        "newlyRenderableDispatchCells":len(newly_renderable_dispatch_positions)*len(locales),
    }
    write_json("manifest.json",manifest)
    (OUT / "localization-glossary.md").write_bytes((PREV / "localization-glossary.md").read_bytes())
    (OUT / "README.md").write_text(
        "# Candidate-free input: ROMarrNG PR #70 W385-W404\n\n"
        "Pinned to the live OPEN/DRAFT PR head " + head + " / tree " + tree +
        " on branch " + BRANCH + ". The live PR head, branch ref, pull ref, and GitHub commit tree were reattested before packet generation.\n\n"
        "The stable source queue contains 479 unique active IDs. Sorting by stable ID and hashing the newline-terminated order reproduces " + source_order_sha +
        ". The sealed W365-W384 selection reattaches to current ranks 365-384; W385-W404 are the immediate next 20 IDs. Boundary rows include ranks 384, 385, 404, and 405.\n\n"
        "This packet contains the complete pinned source queue and source snapshot, exact source/caller excerpts with source-file SHA-256 and Git blob pins, catalog file/key-order pins, and all 240 current locale values. It contains no proposed targets and no review decisions.\n\n"
        "All 288 carried callerless hold cells from W245-W264, W265-W284, W285-W304, and W325-W344 were reattested against current source IDs, ranks, and catalog values; every target hash is unchanged. The prior W365-W384 selection was reattested; that input records zero selected-window holds.\n\n"
        "No callerless or ambiguous source was identified. The source-bound dispatch update at this head makes ranks 392, 396, 398, and 399 renderable through exact local source IDs and exact catalog-source checks; unknown or mismatched API text remains opaque. Other entries use the pinned UI text or template localization paths. No semantic translation decisions are included.\n\n"
        "Run sha256sum -c SHA256SUMS.txt and python3 verify_input.py from this directory to verify the sealed packet. This is a packet verifier, not a project test.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "inputPath":str(OUT),
        "head":head,
        "tree":tree,
        "sourceCount":len(selected),
        "localeCount":len(locales),
        "cellCount":len(current_cells),
        "priorHolds":len(prior_holds),
        "ambiguousPosition":ambiguous_positions,
        "callerlessPositions":[],
        "placeholderMismatches":len(placeholder_mismatches),
        "numericMismatches":len(numeric_mismatches),
        "protectedLiteralMismatches":len(protected_mismatches),
        "sourceQueueSha256":sha(queue_bytes),
        "catalogSha256":sha(catalog_bytes),
        "sourceIdOrderSha256":source_order_sha,
        "catalogKeyOrderSha256":catalog_order_sha,
        "prBodySha256":body_sha,
    },ensure_ascii=False,indent=2))

main()
