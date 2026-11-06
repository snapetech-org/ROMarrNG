#!/usr/bin/env python3
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
from datetime import datetime, timezone

OUT = pathlib.Path(__file__).resolve().parent
PRIMARY_ROOT = pathlib.Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w525-544-primary-20261104")
BLIND_ROOT = pathlib.Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w525-544-blind-20261104")
REPO = pathlib.Path("/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w525-544-source")
HEAD = "eda48333438591ecc67f829c50ef2d521f1e7a5e"
TREE = "3db18e56d0c7ac08a564a6baff61eba25f0a01da"
BRANCH = "task/localization-translation-review-20261030"
SLUG = "snapetech-org/ROMarrNG"

def run(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def key(row):
    return (int(row["position"]), row["locale"])

if run(["git", "-C", str(REPO), "rev-parse", "HEAD"]) != HEAD:
    raise SystemExit("source head changed")
if run(["git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"]) != TREE:
    raise SystemExit("source tree changed")
if run(["git", "-C", str(REPO), "status", "--porcelain"]):
    raise SystemExit("source worktree must be clean")
inp = OUT / "inputs"
if inp.exists():
    raise SystemExit("refusing to overwrite existing cross-review inputs")
cf = inp / "candidate-free" / "input"
pr = inp / "primary-review"
bl = inp / "blind-review"
shutil.copytree(PRIMARY_ROOT / "candidate-free" / "input", cf)
shutil.copytree(PRIMARY_ROOT / "primary", pr)
shutil.copytree(BLIND_ROOT, bl)

verifications = [
    json.loads(run(["python3", "verify_input.py", "--repo", str(REPO)], cwd=cf)),
    json.loads(run(["python3", "verify_primary.py", "--repo", str(REPO)], cwd=pr)),
    json.loads(run(["python3", "verify_blind_packet.py", "--input", str(cf), "--repo", str(REPO)], cwd=bl)),
]
for directory in (cf, pr, bl):
    run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=directory)

current_rows = read_jsonl(cf / "current-target-cells.jsonl")
primary_rows = read_jsonl(pr / "primary-ledger.jsonl")
primary_proposals = read_jsonl(pr / "primary-proposals.jsonl")
blind_rows = read_jsonl(bl / "blind-decisions.jsonl")
current = {key(x): x for x in current_rows}
primary = {key(x): x for x in primary_rows}
proposal = {key(x): x for x in primary_proposals}
blind = {key(x): x for x in blind_rows}
if any(len(x) != 240 for x in (current, primary, blind)) or set(current) != set(primary) or set(current) != set(blind):
    raise SystemExit("current, primary, and blind cell sets must match at 240")

# Independent cross decisions use pinned caller context plus both sealed review packets.
plan = {
 (527,"ar"):("blind","Arabic needs a conditional verb to introduce the library types in the following table."),
 (527,"ko"):("blind","Korean needs an explicit conditional relation to introduce the library types in the following table."),
 (529,"es"):("agreed","Both reviewers identify an action button; the infinitive Importar labels the action, unlike the current noun."),
 (529,"fr"):("agreed","Both reviewers identify an action button; the infinitive Importer labels the action, unlike the current noun."),
 (537,"ar"):("primary","The queue button runs ImportCompleted; select the direct imperative action label over the blind verbal-noun label."),
 (537,"de"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"es"):("primary","Both reviewers correct the status-like label; placing ahora after Importar gives a concise action label."),
 (537,"fr"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"hi"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"id"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"ja"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"ko"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"pt-BR"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"vi"):("blind","The blind proposal is more concise and places ngay naturally while preserving the immediate action."),
 (537,"zh-Hans"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (537,"zh-Hant"):("agreed","Both reviewers correct the status-like current value to an action on completed downloads."),
 (538,"vi"):("blind","The bulk action is restricted to verified candidates; đã được xác minh preserves verified rather than merely checked."),
 (539,"ar"):("agreed","Both reviewers correct the plural current value to the concise singular failed-import status used by the state map."),
}
proposal_cells = set(proposal) | {k for k,v in blind.items() if v["decision"] == "revise"}
if len(primary_proposals) != 15 or sum(v["decision"] == "revise" for v in blind_rows) != 18 or proposal_cells != set(plan):
    raise SystemExit("unexpected proposal totals or incomplete cross plan")
for k,(basis,_) in plan.items():
    p = proposal.get(k)
    b = blind[k]
    if basis == "agreed" and (p is None or b["decision"] != "revise" or p["proposedTarget"] != b["proposalTarget"]):
        raise SystemExit("proposal agreement mismatch at " + str(k))
    if basis == "primary" and (p is None or b["decision"] != "revise" or p["proposedTarget"] == b["proposalTarget"]):
        raise SystemExit("primary selection is not a conflict at " + str(k))
    if basis == "blind" and b["decision"] != "revise":
        raise SystemExit("blind proposal missing at " + str(k))

pr_state = json.loads(run(["gh","pr","view","70","--repo",SLUG,"--json",
                          "state,isDraft,mergeStateStatus,headRefName,headRefOid,baseRefName,baseRefOid,url"]))
branch_api = json.loads(run(["gh","api","repos/snapetech-org/ROMarrNG/branches/task%2Flocalization-translation-review-20261030"]))
main_sha = run(["gh","api","repos/snapetech-org/ROMarrNG/branches/main","--jq",".commit.sha"])
ref_out = run(["git","-C",str(REPO),"ls-remote","origin","refs/heads/"+BRANCH,"refs/pull/70/head"])
refs = {parts[1]:parts[0] for line in ref_out.splitlines() if len(parts:=line.split()) == 2}
attestation = {
 "repository":SLUG,"pullRequest":70,"state":pr_state["state"],"isDraft":pr_state["isDraft"],
 "mergeStateStatus":pr_state["mergeStateStatus"],"headRefName":pr_state["headRefName"],
 "headRefOid":pr_state["headRefOid"],"branchApiName":branch_api["name"],
 "branchApiSha":branch_api["commit"]["sha"],"branchRefSha":refs.get("refs/heads/"+BRANCH),
 "pullRefSha":refs.get("refs/pull/70/head"),"baseRefName":pr_state["baseRefName"],
 "baseApiSha":pr_state["baseRefOid"],"liveMainSha":main_sha,"headTree":TREE,
 "capturedAtUtc":datetime.now(timezone.utc).isoformat()
}
if (attestation["state"] != "OPEN" or not attestation["isDraft"] or
    attestation["headRefName"] != BRANCH or attestation["headRefOid"] != HEAD or
    attestation["branchApiName"] != BRANCH or attestation["branchApiSha"] != HEAD or
    attestation["branchRefSha"] != HEAD or attestation["pullRefSha"] != HEAD):
    raise SystemExit("live PR/ref attestation failed")
write_json(OUT/"PR-attestation-before.json", read_json(cf/"PR-attestation-before.json"))
write_json(OUT/"PR-attestation-after.json", attestation)
write_json(OUT/"input-verification-results.json", {
 "candidateFree":verifications[0],"primary":verifications[1],"blind":verifications[2],
 "allInputChecksums":"PASS"
})

prior_holds = read_jsonl(cf/"prior-hold-reattestation.jsonl")
blind_prior_holds = read_jsonl(bl/"prior-hold-reattestation-hash-only.jsonl")
prior_applied = read_jsonl(cf/"prior-applied-cell-reattestation.jsonl")
prior_selections = read_jsonl(cf/"prior-selection-reattestation.jsonl")
if len(prior_holds) != 540 or len(blind_prior_holds) != 540 or len(prior_applied) != 28 or len(prior_selections) != 140:
    raise SystemExit("prior lineage counts changed")
pins = read_json(cf/"catalog-file-pins.json")
catalog_path = pins["catalogPath"]
cross_rows=[]; changes=[]; recs=[]; holds=[]
for k,row in sorted(current.items()):
    p=primary[k]; b=blind[k]
    linkage=(row["sourceId"],row["sourceSha256"],row["currentTargetSha256"],row["callerContextSha256"])
    if linkage != (p["sourceId"],p["sourceSha256"],p["currentTargetSha256"],p["callerContextSha256"]):
        raise SystemExit("primary linkage mismatch at "+str(k))
    if linkage != (b["sourceId"],b["sourceSha256"],b["currentTargetSha256"],b["callerContextSha256"]):
        raise SystemExit("blind linkage mismatch at "+str(k))
    if k[0] == 530:
        if p["disposition"] != "hold" or row["callerRefs"]:
            raise SystemExit("position 530 is not the pinned callerless hold")
        holds.append({"position":k[0],"locale":k[1],"sourceIdSha256":sha(row["sourceId"]),
                      "sourceSha256":row["sourceSha256"],"currentTargetSha256":row["currentTargetSha256"],
                      "reasonCode":"callerless-source-id"})
        cross_rows.append({"position":k[0],"locale":k[1],"sourceIdSha256":sha(row["sourceId"]),
                           "sourceSha256":row["sourceSha256"],"currentTargetSha256":row["currentTargetSha256"],
                           "primaryDisposition":"hold","blindDecision":b["decision"],
                           "crossDecision":"hold_callerless","selectedTargetSha256":None,
                           "selectionRationale":"The exact-head search found no source literal or caller for this source ID; keep the cell text-free on hold."})
        continue
    if k in plan:
        basis,rationale=plan[k]
        target = blind[k]["proposalTarget"] if basis=="blind" else proposal[k]["proposedTarget"]
        target_hash=sha(target)
        if basis=="agreed" and target_hash != blind[k]["proposalTargetSha256"]:
            raise SystemExit("agreed target hash mismatch at "+str(k))
        tokens={
          "placeholders":re.findall(r"\{[^{}]+\}",target),
          "markup":re.findall(r"</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>",target),
          "numeric":re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",target)
        }
        if tokens["placeholders"] != row["sourcePlaceholderTokens"] or tokens["markup"] != row["sourceMarkupTags"]:
            raise SystemExit("placeholder/markup mismatch at "+str(k))
        if tokens["numeric"] != row["sourceNumericTokens"]:
            raise SystemExit("numeric token mismatch at "+str(k))
        if any(lit not in target for lit in row["sourceProtectedLiterals"]):
            raise SystemExit("protected literal mismatch at "+str(k))
        primary_target=proposal[k]["proposedTarget"] if k in proposal else p["currentTarget"]
        primary_hash=proposal[k]["proposedTargetSha256"] if k in proposal else p["currentTargetSha256"]
        blind_target=b["proposalTarget"] if b["decision"]=="revise" else b["currentTarget"]
        blind_hash=b["proposalTargetSha256"] if b["decision"]=="revise" else b["currentTargetSha256"]
        cr={"position":k[0],"locale":k[1],"sourceId":row["sourceId"],"source":row["source"],
            "sourceSha256":row["sourceSha256"],"callerContextSha256":row["callerContextSha256"],
            "currentTarget":row["currentTarget"],"currentTargetSha256":row["currentTargetSha256"],
            "primaryDisposition":p["disposition"],"primaryTarget":primary_target,"primaryTargetSha256":primary_hash,
            "blindDecision":b["decision"],"blindTarget":blind_target,"blindTargetSha256":blind_hash,
            "crossDecision":"select_"+basis+"_proposal","selectedTarget":target,"selectedTargetSha256":target_hash,
            "tokenSafety":{"placeholders":"PASS","markup":"PASS","numericTokens":"PASS","protectedLiterals":"PASS"},
            "selectionRationale":rationale,"reviewConfidence":"moderate"}
        cross_rows.append(cr)
        recs.append({"position":k[0],"locale":k[1],"sourceId":row["sourceId"],
                     "primaryTarget":proposal[k]["proposedTarget"] if k in proposal else None,
                     "blindTarget":b["proposalTarget"],"crossDecision":cr["crossDecision"],
                     "selectedTarget":target,"selectedTargetSha256":target_hash,"rationale":rationale})
        changes.append({"position":k[0],"locale":k[1],"sourceId":row["sourceId"],"catalogPath":catalog_path,
                        "beforeTarget":row["currentTarget"],"beforeSha256":row["currentTargetSha256"],
                        "afterTarget":target,"afterSha256":target_hash,"selectedFrom":basis})
    else:
        if p["disposition"] != "accept-current" or b["decision"] != "accept-current":
            raise SystemExit("unresolved review proposal outside plan at "+str(k))
        cross_rows.append({"position":k[0],"locale":k[1],"sourceId":row["sourceId"],"source":row["source"],
                           "sourceSha256":row["sourceSha256"],"callerContextSha256":row["callerContextSha256"],
                           "currentTarget":row["currentTarget"],"currentTargetSha256":row["currentTargetSha256"],
                           "primaryDisposition":p["disposition"],"blindDecision":b["decision"],
                           "crossDecision":"retain_current","selectedTarget":row["currentTarget"],
                           "selectedTargetSha256":row["currentTargetSha256"],
                           "selectionRationale":"Both primary and blind reviews accept the pinned current value.",
                           "reviewConfidence":"moderate"})
for name,rows in (("cross-ledger.jsonl",cross_rows),("proposal-reconciliation.jsonl",recs),
                  ("selected-changes.jsonl",changes),("holds.jsonl",holds)):
    (OUT/name).write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in rows),encoding="utf-8")
(OUT/"prior-holds-preserved.jsonl").write_text(
    (cf/"prior-hold-reattestation.jsonl").read_text(encoding="utf-8"),encoding="utf-8")
decision_counts={}
for x in cross_rows: decision_counts[x["crossDecision"]]=decision_counts.get(x["crossDecision"],0)+1
selected_by={}
for x in changes: selected_by[x["selectedFrom"]]=selected_by.get(x["selectedFrom"],0)+1
write_json(OUT/"summary.json",{
 "artifact":"ROMarrNG PR #70 W525-W544 independent cross adjudication","repository":SLUG,
 "pullRequest":70,"window":"W525-W544","head":HEAD,"tree":TREE,"sourceCount":20,
 "localeCount":12,"cellCount":240,"crossDecisionCounts":decision_counts,
 "proposalCells":len(recs),"primaryProposalCount":len(primary_proposals),
 "blindRevisionCount":sum(x["decision"]=="revise" for x in blind_rows),
 "selectedChanges":len(changes),"selectedBy":selected_by,"newTextFreeHolds":len(holds),
 "priorHashOnlyHoldsPreserved":len(prior_holds),"priorAppliedCellsReattested":len(prior_applied),
 "priorSelectedSourcesReattested":len(prior_selections),"tokenMismatchesInSelectedTargets":0,
 "baseApiLiveMainMismatchDocumented":attestation["baseApiSha"]!=attestation["liveMainSha"],
 "reviewConfidence":"moderate","browserAcceptance":False,"nativeSpeakerApproval":False,
 "testsBuildsScansCI":False,"workflowChanges":0,"mergeReleaseTag":False,
 "capturedAtUtc":datetime.now(timezone.utc).isoformat()
})
(OUT/"README.md").write_text("""# ROMarrNG PR #70 W525-W544 cross-review packet

The independent cross review reconciles 240 catalog cells from 20 English source IDs across all 12 target locales. This packet contains the sealed candidate-free input, primary review, blind review, per-cell reconciliation, selected changes, hash-only hold records, PR attestations, and portable verifiers.

The final review retains 210 current cells, selects 18 reviewed proposals (12 exact primary/blind agreements, 2 primary selections, and 4 blind selections), and holds 12 callerless cells at position 530 text-free. The 540 earlier hash-only holds, 28 earlier application hashes, and 140 earlier selected-source hashes are preserved. Placeholder, markup, numeric-token, and protected-literal checks pass for every selected change.

The queue button submits the ImportCompleted command, so position 537 is an action label. The bulk import button at position 538 is limited to verified candidates. The conditional library heading at position 527 now expresses the conditional relation in Arabic and Korean. Review confidence is moderate. Browser acceptance and native-speaker signoff are not claimed. No tests, builds, scans, CI, workflow edits, merge, release, or tag were performed.

The PR remained open and draft at the pinned head during review. Its base API SHA differs from live main; both are recorded without changing the base.

Run python3 verify_cross.py --repo /path/to/clean/ROMarrNG-worktree from this directory.
""",encoding="utf-8")
print(json.dumps({"result":"BUILT","cells":len(cross_rows),"changes":len(changes),
                  "proposalCells":len(recs),"decisions":decision_counts,"selectedBy":selected_by,
                  "holds":len(holds),"attestation":attestation},sort_keys=True))
