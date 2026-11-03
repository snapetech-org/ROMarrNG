#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parent

def fail(msg):
    raise SystemExit("FAIL: "+msg)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+bytes([0])+raw).hexdigest()

def loadj(path):
    return json.loads(path.read_text(encoding="utf-8"))

def loadjl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def verify_sums(directory):
    sums=directory/"SHA256SUMS.txt"
    if not sums.is_file():
        fail("missing "+str(sums.relative_to(ROOT)))
    checked=0
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        if len(line)<66 or line[64:66]!="  ":
            fail("malformed checksum line in "+str(sums.relative_to(ROOT)))
        expected=line[:64]
        name=line[66:]
        if name.startswith("*"):
            name=name[1:]
        path=directory/name
        if not path.is_file() or sha(path.read_bytes())!=expected:
            fail("packet checksum mismatch: "+str(path.relative_to(ROOT)))
        checked+=1
    return checked

def main():
    top_n=verify_sums(ROOT)
    cf=ROOT/"candidate-free-input"
    primary=ROOT/"primary-review"
    blind=ROOT/"blind-review-input"
    d=loadj(ROOT/"head-reattestation.json")
    cf_n=verify_sums(cf)
    primary_n=verify_sums(primary)
    if loadj(cf/"manifest.json").get("head")!="d5ba7f1f268501f45227388c46d5f938ed0c9191":
        fail("candidate-free packet head mismatch")
    if loadj(cf/"manifest.json").get("tree")!="2f8ce1af963b315108f668fc31c94ca90ecd1351":
        fail("candidate-free packet tree mismatch")
    pm=loadj(primary/"manifest.json")
    if (pm.get("head"),pm.get("tree"))!=("d5ba7f1f268501f45227388c46d5f938ed0c9191","2f8ce1af963b315108f668fc31c94ca90ecd1351"):
        fail("primary packet exact pin mismatch")
    if pm.get("candidateFreeInputManifestSha256")!=sha((cf/"manifest.json").read_bytes()):
        fail("primary packet candidate-free manifest pin mismatch")
    if pm.get("candidateFreeInputChecksumsSha256")!=sha((cf/"SHA256SUMS.txt").read_bytes()):
        fail("primary packet candidate-free checksum-list pin mismatch")
    if (d.get("candidateFreeVerifier"),d.get("primaryVerifier"))!=("PASS","PASS"):
        fail("recorded source packet verifier status is not PASS")
    if (d.get("candidateFreeCells"),d.get("primaryCells"))!=(240,240):
        fail("recorded cell coverage is not 240 by 240")
    if d.get("blindInputCandidateFreeCopyByteIdentical") is not True:
        fail("blind input copy not recorded byte-identical")
    import subprocess
    diff=subprocess.run(["diff","-qr",str(cf),str(blind/"candidate-free-input")],capture_output=True)
    if diff.returncode!=0:
        fail("blind candidate-free input differs from candidate-free packet")
    if d.get("blindFinalReviewLedgerAvailable") is not False or d.get("blindFinalReviewLedgerPaths")!=[]:
        fail("blind packet unexpectedly claims a final ledger")
    prelim=d.get("blindPreliminaryRegistryRankExtraction",{})
    if prelim.get("useForCrossAudit") is not False or prelim.get("samePositionSourceIdMatches")!=0 or prelim.get("sourceIdOverlapCount")!=0:
        fail("preliminary blind extraction invalidation mismatch")
    if d.get("latestLiveHead")!="81a499b7c022bde61a63dbd8c68c0b1ca39adf26" or d.get("latestLiveTree")!="1b075e050610771fc5651d1a4ca95d7c7b4b8e46":
        fail("latest live head/tree mismatch")
    want_refs={"refs/heads/task/localization-translation-review-20261030":d["latestLiveHead"],"refs/pull/70/head":d["latestLiveHead"]}
    if d.get("branchAndPullRefsBefore")!=want_refs or d.get("branchAndPullRefsAfter")!=want_refs:
        fail("recorded branch or pull refs mismatch")
    body=d.get("prBodyEvidenceLinks",{})
    if body.get("appliedMarkerCount")!=1 or body.get("w425W444ReadmeLinkPresent") is not True or body.get("w425W444VerifierLinkPresent") is not True:
        fail("recorded PR body README/verifier links or marker mismatch")
    pins=d.get("relevantGitPins",[])
    if len(pins)!=d.get("relevantGitPinCount") or len(pins)!=10:
        fail("relevant source/catalog/caller pin coverage mismatch")
    for pin in pins:
        if not all(pin.get(key) is True for key in ("rawBytesMatch","pinnedShaMatches","pinnedBlobMatches","latestShaMatches","latestBlobMatches")):
            fail("recorded d5ba-to-81a pin mismatch: "+pin.get("path","<unknown>"))
        blobpath=ROOT/"pinned-source-blobs"/pin["path"]
        if not blobpath.is_file():
            fail("missing pinned blob content: "+pin["path"])
        raw=blobpath.read_bytes()
        if sha(raw)!=pin["baseSha256"] or sha(raw)!=pin["latestSha256"] or git_blob(raw)!=pin["baseGitBlob"] or git_blob(raw)!=pin["latestGitBlob"]:
            fail("pinned source bytes do not reproduce Git blob/SHA: "+pin["path"])
        if pin.get("pinnedSha256") and pin["pinnedSha256"]!=sha(raw):
            fail("catalog/input pin SHA mismatch: "+pin["path"])
        if pin.get("pinnedGitBlob") and pin["pinnedGitBlob"]!=git_blob(raw):
            fail("catalog/input pin Git blob mismatch: "+pin["path"])
    if d.get("sourceContextReferenceCount")!=29:
        fail("caller-context reference count mismatch")
    hold_summary=loadj(cf/"prior-hold-reattestation-summary.json")
    selection_summary=loadj(cf/"prior-selection-reattestation-summary.json")
    if hold_summary.get("reattestedCellCount")!=348 or hold_summary.get("currentTargetChangedCells")!=0 or hold_summary.get("allCurrentTargetHashesMatchPriorHoldEvidence") is not True:
        fail("carried hold reattestation mismatch")
    if selection_summary.get("reattestedSelectedSourceCount")!=60 or selection_summary.get("allPriorSelectionsMatchCurrentCatalogAndRegistry") is not True:
        fail("prior selected-source reattestation mismatch")
    if d.get("changedPathCount")!=218 or d.get("allChangesConfinedToNewW425W444Evidence") is not True:
        fail("base-to-live changed-path scope mismatch")
    for ch in d.get("changedPathsBaseToLatest",[]):
        if ch.get("status")!="A" or not ch.get("path","").startswith("docs/pr-evidence/pr70-localization-2026-11-03/window-425-444/"):
            fail("unexpected base-to-live changed path: "+str(ch))
    rows=loadjl(cf/"current-target-cells.jsonl")
    primary_rows=loadjl(primary/"primary-ledger.jsonl")
    if len(rows)!=240 or len(primary_rows)!=240:
        fail("input or primary ledger does not cover all 240 cells")
    c_by={(r["position"],r["locale"]):r for r in rows}
    p_by={(r["position"],r["locale"]):r for r in primary_rows}
    if set(c_by)!=set(p_by):
        fail("candidate-free and primary cell keys differ")
    cat=json.loads((ROOT/"pinned-source-blobs/romarr/ui-labels.json").read_text(encoding="utf-8"))
    if len(cat.get("messages",{}))!=1836:
        fail("catalog message count differs from reattestation")
    for key,c in c_by.items():
        p=p_by[key]
        for field in ("sourceId","sourceSha256","currentTargetSha256","currentTarget"):
            if c.get(field)!=p.get(field):
                fail("candidate-free/primary cell mismatch "+str(key)+" "+field)
        msg=cat.get("messages",{}).get(c["sourceId"])
        if not msg or msg.get("source")!=c["source"] or msg.get("translations",{}).get(c["locale"])!=c["currentTarget"]:
            fail("catalog exact-head target mismatch "+str(key))
        if sha(c["currentTarget"].encode("utf-8"))!=c["currentTargetSha256"]:
            fail("target SHA mismatch "+str(key))
    if d.get("catalogStructure",{}).get("all240CurrentTargetHashesReattestedAtBothHeads") is not True:
        fail("catalog targets not recorded reattested at both heads")
    # Confirm the preliminary evidence remains preliminary and contains no final decision ledger.
    prelim_dir=ROOT/"preliminary-blind-review"
    src_cells=prelim_dir/"input/source-cells.jsonl"
    if not src_cells.is_file() or sha(src_cells.read_bytes())!=prelim.get("fileSha256"):
        fail("preliminary blind evidence checksum mismatch")
    if (prelim_dir/"input/cell-review.jsonl").exists():
        fail("unexpected final decision ledger presented as preliminary evidence")
    print(json.dumps({"result":"PASS","candidateFreeFilesChecked":cf_n,"primaryFilesChecked":primary_n,
      "relevantGitPinsRecomputed":len(pins),"callerContextRefs":29,"currentTargetCells":240,
      "changedEvidenceFiles":218,"head":d["latestLiveHead"],"tree":d["latestLiveTree"],
      "blindFinalLedgerAvailable":False,"selectionGate":d["selectionGate"]},indent=2))

if __name__=="__main__":
    main()
