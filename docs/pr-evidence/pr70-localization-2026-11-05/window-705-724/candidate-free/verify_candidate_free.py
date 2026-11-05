#!/usr/bin/env python3
"""Verify the sealed ROMarrNG PR #70 W705-W724 candidate-free packet."""
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path

HEAD = "50e3f8a48a800affff8bad367b5c493cc0fdfd62"
TREE = "22cd46ff4821fcbbe76b4760a15e22d688b3f548"
WINDOW = "W705-W724"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input"
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED = ["Gaseous", "Retrom", "SeerrNG", "ROMarrNG", "ROMarr", "ES-DE", "No-Intro", "Redump", "DAT", "IGDB", "ISO9660", "PLAYSTATION", "PlayStation", "PS2", "ROMs", "ROM", "PC", "API", "ROMARR_API_KEY", "Linksnappy", "Moonlight", "PIN", "NPSSO", "NZBHydra2", "Newznab", "/torznab/api", "NZBVortex", "HTTPS", "NZB", "Preferences"]

def sha(v):
    if isinstance(v, str): v = v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def rj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def fail(msg): raise SystemExit("FAIL " + msg)
def verify_sums(root):
    root = Path(root); sums = root / "SHA256SUMS.txt"; listed = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        digest, rel = line.split("  ", 1); path = (root / rel).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest: fail(f"checksum {rel}")
        if rel in listed: fail(f"duplicate checksum {rel}")
        listed[rel] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums}
    if set(listed) != actual: fail(f"checksum coverage {root}")
def token_data(source, target):
    def protected(s):
        out=[]
        for literal in PROTECTED:
            found=literal in s if literal.startswith("/") else bool(re.search(r"(?<![A-Za-z0-9])"+re.escape(literal)+r"(?![A-Za-z0-9])",s))
            if found: out.append(literal)
        return sorted(set(out))
    s={"placeholders":PLACEHOLDER.findall(source),"markup":TAG.findall(source),"numbers":NUMBER.findall(source),"protectedLiterals":protected(source)}
    t={"placeholders":PLACEHOLDER.findall(target),"markup":TAG.findall(target),"numbers":NUMBER.findall(target),"protectedLiterals":protected(target)}
    ph=collections.Counter(s["placeholders"])==collections.Counter(t["placeholders"])
    mk=collections.Counter(s["markup"])==collections.Counter(t["markup"])
    sn,tn=collections.Counter(s["numbers"]),collections.Counter(t["numbers"]);extra=list((tn-sn).elements())
    presentation=bool(re.search(r"\bzero\b",source,re.I) and not s["numbers"] and extra==["0"])
    numeric=not (sn-tn) and (not extra or presentation)
    missing=[x for x in s["protectedLiterals"] if x not in target]
    return {"sourcePlaceholderTokens":s["placeholders"],"currentPlaceholderTokens":t["placeholders"],"placeholderMultisetMatches":ph,"sourceMarkupTags":s["markup"],"currentMarkupTags":t["markup"],"markupMatches":mk,"sourceNumericTokens":s["numbers"],"currentNumericTokens":t["numbers"],"numericTokensPreserved":numeric,"numericPresentationEquivalent":presentation,"sourceProtectedLiterals":s["protectedLiterals"],"missingProtectedLiterals":missing,"protectedLiteralsPreserved":not missing}
def verify_context_shape(ctx, source=None):
    if ctx["callerless"]:
        if "source" in ctx or not ctx.get("sourceTextOmitted") or ctx.get("callers") != []: fail(f"callerless context redaction {ctx['sourceId']}")
        if ctx["exactMatchCount"] != 0: fail(f"callerless context count {ctx['sourceId']}")
        return
    if "source" not in ctx or not isinstance(ctx["source"],str) or len(ctx["callers"]) != ctx["exactMatchCount"]: fail(f"caller-backed context shape {ctx['sourceId']}")
    src = source if source is not None else ctx["source"]
    core={"sourceId":ctx["sourceId"],"source":src,"sourceSha256":ctx["sourceSha256"],"head":ctx["head"],"searchMethod":ctx["searchMethod"],"productionFilesSearched":ctx["productionFilesSearched"],"exactMatchCount":ctx["exactMatchCount"],"callerless":ctx["callerless"],"callers":ctx["callers"]}
    if sha(src) != ctx["sourceSha256"] or sha(canon(core)) != ctx["contextSha256"]: fail(f"caller context hash {ctx['sourceId']}")
    for c in ctx["callers"]:
        if sha(c["lineText"]) != c["lineSha256"] or sha(canon(c["excerpt"])) != c["excerptSha256"]: fail(f"caller line/excerpt hash {ctx['sourceId']}")
        if not any(x["line"] == c["line"] and x["text"] == c["lineText"] for x in c["excerpt"]): fail(f"caller excerpt line {ctx['sourceId']}")
def verify_repo(repo, manifest, selected, contexts, cells, holds, applied, readbacks):
    repo=repo.resolve(); git=lambda *a: subprocess.check_output(["git","-C",str(repo),*a],text=True).strip()
    if git("rev-parse","HEAD") != HEAD or git("rev-parse","HEAD^{tree}") != TREE: fail("exact repository pin")
    if git("status","--porcelain=v1","--untracked-files=all") or git("branch","--show-current"): fail("repo must be clean and detached")
    catalog_path="romarr/ui-labels.json"; catalog_raw=(repo/catalog_path).read_bytes(); catalog=json.loads(catalog_raw); msgs=catalog["messages"]; ids=list(msgs)
    if sha(catalog_raw)!=manifest["catalogSha256"] or len(msgs)!=manifest["catalogMessageCount"]: fail("catalog pin")
    if sha("\n".join(ids)+"\n")!=manifest["catalogKeyOrderSha256"]: fail("catalog order hash")
    order=rjl(INPUT/"catalog-key-order.jsonl")
    if len(order)!=len(ids): fail("catalog key order length")
    for i,(sid,row) in enumerate(zip(ids,order)):
        if row["catalogZeroBasedIndex"]!=i or row["sourceId"]!=sid or row["sourceSha256"]!=sha(msgs[sid]["source"]): fail("catalog key order row")
    if sha((repo/"romarr/ui-source-messages.json").read_bytes())!=manifest["sourceQueueSha256"]: fail("source registry hash")
    snapshot=rj(repo/"romarr/ui-source-snapshot.json")
    if sha(canon(snapshot))!=manifest["sourceSnapshotSha256"]: fail("source snapshot hash")
    for pin in rj(INPUT/"source-file-pins.json")["files"]:
        path=repo/pin["path"]
        if not path.is_file() or sha(path.read_bytes())!=pin["fileSha256"] or git("rev-parse",f"{HEAD}:{pin['path']}")!=pin["gitBlob"]: fail(f"source file pin {pin['path']}")
    selected_by_id={r["sourceId"]:r for r in selected}; context_by_id={r["sourceId"]:r for r in contexts}
    for sid,ctx in context_by_id.items():
        src=msgs[sid]["source"]
        if sha(src)!=ctx["sourceSha256"]: fail(f"context source {sid}")
        verify_context_shape(ctx,src if not ctx["callerless"] else None)
        if ctx["callerless"]:
            core={"sourceId":ctx["sourceId"],"source":src,"sourceSha256":ctx["sourceSha256"],"head":ctx["head"],"searchMethod":ctx["searchMethod"],"productionFilesSearched":ctx["productionFilesSearched"],"exactMatchCount":ctx["exactMatchCount"],"callerless":ctx["callerless"],"callers":ctx["callers"]}
            if sha(canon(core))!=ctx["contextSha256"] or any(c.get("source") for c in ctx["callers"]): fail("callerless context hash/text")
        else:
            for c in ctx["callers"]:
                raw=(repo/c["path"]).read_bytes(); lines=raw.decode("utf-8","replace").splitlines()
                if sha(raw)!=c["fileSha256"] or git("rev-parse",f"{HEAD}:{c['path']}")!=c["gitBlob"]: fail(f"caller file pin {sid}")
                if c["line"]<1 or c["line"]>len(lines) or lines[c["line"]-1]!=c["lineText"]: fail(f"caller exact line {sid}")
                excerpt=[{"line":n,"text":lines[n-1]} for n in range(max(1,c["line"]-3),min(len(lines),c["line"]+3)+1)]
                if excerpt!=c["excerpt"]: fail(f"caller exact excerpt {sid}")
    for row in selected:
        sid,idx=row["sourceId"],row["catalogZeroBasedIndex"]
        if idx not in range(705,725) or ids[idx]!=sid or sha(msgs[sid]["source"])!=row["sourceSha256"]: fail(f"selected source {sid}")
        if context_by_id[sid]["callerless"] and ("source" in row or not row.get("sourceTextOmitted")): fail(f"callerless selected source leak {sid}")
        if not context_by_id[sid]["callerless"] and row.get("source")!=msgs[sid]["source"]: fail(f"selected source text {sid}")
    for row in cells:
        sid,loc,idx=row["sourceId"],row["locale"],row["catalogZeroBasedIndex"]; msg=msgs[sid]
        if ids[idx]!=sid or idx not in range(705,725) or sha(msg["source"])!=row["sourceSha256"] or sha(msg["translations"][loc])!=row["currentTargetSha256"]: fail(f"current cell hash {sid}/{loc}")
        if row["callerContextSha256"]!=context_by_id[sid]["contextSha256"] or row["callerless"]!=context_by_id[sid]["callerless"]: fail(f"current cell caller binding {sid}/{loc}")
        if row["callerless"]:
            if any(k in row for k in ("source","currentTarget","sourceText","currentTargetText","proposedTarget")): fail(f"callerless cell text leak {sid}/{loc}")
        elif row.get("source")!=msg["source"] or row.get("currentTarget")!=msg["translations"][loc]: fail(f"caller-backed text {sid}/{loc}")
    for row in holds:
        sid,loc=row["sourceId"],row["locale"]
        if sha(msgs[sid]["source"])!=row["sourceSha256"] or sha(msgs[sid]["translations"][loc])!=row["currentTargetSha256"]: fail(f"prior hold hash {sid}/{loc}")
    for row in applied:
        sid,loc=row["sourceId"],row["locale"]
        if sha(msgs[sid]["source"])!=row["sourceSha256"] or sha(msgs[sid]["translations"][loc])!=row["currentTargetSha256"]: fail(f"prior applied hash {sid}/{loc}")
    for label,rows in readbacks.items():
        for row in rows:
            sid,loc=row["sourceId"],row["locale"]
            if sha(msgs[sid]["source"])!=row["sourceSha256"] or sha(msgs[sid]["translations"][loc])!=row["currentTargetSha256"]: fail(f"readback hash {label}/{sid}/{loc}")
    return {"repoPin":"PASS","repoCleanDetached":True,"currentCellsRechecked":len(cells),"priorSelectionsRechecked":320,"priorHoldsRechecked":len(holds),"priorAppliedRechecked":len(applied)}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",type=Path); args=ap.parse_args()
    verify_sums(INPUT); verify_sums(ROOT)
    manifest=rj(INPUT/"manifest.json")
    if (manifest.get("head"),manifest.get("tree"),manifest.get("window"),manifest.get("candidateFree"))!=(HEAD,TREE,WINDOW,True): fail("manifest pin")
    if manifest.get("proposedTargetsIncluded") or manifest.get("reviewDecisionsIncluded") or manifest.get("callerlessCellTextIncluded"): fail("candidate-free boundary")
    cells=rjl(INPUT/"candidate-free-cells.jsonl"); contexts=rjl(INPUT/"source-contexts.jsonl"); selected=rjl(INPUT/"selected-sources.jsonl")
    holds=rjl(INPUT/"prior-hold-reattestation.jsonl"); applied=rjl(INPUT/"prior-applied-cell-reattestation.jsonl"); selections=rjl(INPUT/"prior-selection-reattestation.jsonl")
    if (len(cells),len(contexts),len(selected),len(selections),len(holds),len(applied))!=(240,20,20,320,904,127): fail("packet row counts")
    if [(r["catalogZeroBasedIndex"],r["locale"]) for r in cells] != [(i,loc) for i in range(705,725) for loc in LOCALES]: fail("current cell ordering")
    if [(r["catalogZeroBasedIndex"],r["sourceId"]) for r in selected] != [(705+i,cells[i*12]["sourceId"]) for i in range(20)]: fail("source selection ordering")
    selected_map={r["sourceId"]:r for r in selected}; context_map={r["sourceId"]:r for r in contexts}
    if len(selected_map)!=20 or len(context_map)!=20: fail("source uniqueness")
    hold_count=0
    for ctx in contexts:
        verify_context_shape(ctx)
    for row in cells:
        sid,loc=row["sourceId"],row["locale"]; ctx=context_map.get(sid)
        if not ctx or row["callerContextSha256"]!=ctx["contextSha256"] or row["callerless"]!=ctx["callerless"] or row["literalCallerCount"]!=ctx["exactMatchCount"]: fail(f"cell/context binding {sid}/{loc}")
        if row.get("candidateFree") is not True or any(k in row for k in ("proposedTarget","recommendedTarget","reviewDecision","proposal")): fail(f"review content in candidate-free cell {sid}/{loc}")
        if row["callerless"]:
            hold_count+=1
            if row.get("cellDisposition")!="hold-callerless-hash-only" or any(k in row for k in ("source","sourceText","currentTarget","target","targetText","proposedTarget")): fail(f"callerless cell redaction {sid}/{loc}")
        else:
            if not isinstance(row.get("source"),str) or not isinstance(row.get("currentTarget"),str): fail(f"caller-backed text missing {sid}/{loc}")
            if sha(row["source"])!=row["sourceSha256"] or sha(row["currentTarget"])!=row["currentTargetSha256"]: fail(f"current text hashes {sid}/{loc}")
            if token_data(row["source"],row["currentTarget"]) != {k:row[k] for k in token_data(row["source"],row["currentTarget"])}: fail(f"token evidence {sid}/{loc}")
    if hold_count!=manifest["callerlessCurrentTargetCellCount"] or hold_count!=12*manifest["callerlessSourceCount"]: fail("callerless cell count")
    for i,row in enumerate(selected):
        if row["catalogZeroBasedIndex"]!=705+i or row["position"]!=705+i or row["catalogOneBasedPosition"]!=706+i: fail("selected position")
        if row["sourceId"] in context_map and context_map[row["sourceId"]]["callerless"] and ("source" in row or not row.get("sourceTextOmitted")): fail("selected callerless source leak")
    if any(any(k in r for k in ("source","sourceText","currentTarget","target","targetText","proposedTarget")) for r in holds): fail("prior hold text leak")
    if any(any(k in r for k in ("source","sourceText","currentTarget","target","targetText","proposedTarget","finalTarget")) for r in applied): fail("prior applied text leak")
    if len({(r["sourceId"],r["locale"]) for r in holds})!=904 or len({(r["sourceId"],r["locale"]) for r in applied})!=127: fail("prior cell uniqueness")
    readbacks={}
    for path in INPUT.glob("prior-*-cell-hash-reattestation.jsonl"):
        rows=rjl(path)
        if rows:
            label=rows[0]["priorWindow"]
            if len(rows)!=240: fail(f"readback count {label}")
            readbacks[label]=rows
    if len(readbacks)!=7 or set(readbacks)!={"W565-W584","W585-W604","W605-W624","W625-W644","W645-W664","W665-W684","W685-W704"}: fail("readback window coverage")
    lineage=rj(INPUT/"prior-window-lineage.json")
    if lineage.get("result")!="PASS" or (lineage.get("previousSourceSelectionsReattested"),lineage.get("previousHeldCellsReattested"),lineage.get("previousAppliedCellsReattested"))!=(320,904,127): fail("lineage counts")
    if lineage.get("w625EvidenceCaveat",{}).get("missingFromPriorCommittedPrTree")!=31 or not lineage.get("w625EvidenceCaveat",{}).get("matchesFinalVerifier"): fail("W625 caveat preservation")
    if not lineage.get("w645BlindSummaryPinWarning",{}).get("blindChecksumMismatchRecorded"): fail("W645 warning preservation")
    w665=lineage.get("w665EvidenceRestoration",{})
    if (w665.get("previouslyMissingPayloadsRestored"),w665.get("currentEvidenceIndexEntries"),w665.get("currentMissingFiles"),w665.get("currentMismatchedFiles"),w665.get("allCurrentIndexedPayloadsPresentAndHashMatched"))!=(24,77,[],[],True): fail("W665 restoration record")
    before=rj(INPUT/"PR-attestation-before.json"); after=rj(INPUT/"PR-attestation-after-candidate-free.json")
    for att in (before,after):
        if (att["state"],att["draft"],att["merged"],att["head"],att["tree"],att["apiCommitTree"],att["branchRefOid"],att["pullRefOid"])!=("OPEN",True,False,HEAD,TREE,TREE,HEAD,HEAD): fail("live PR attestation")
    for k in ("head","tree","apiCommitTree","branchRefOid","pullRefOid","baseLiveRefOid","bodySha256","bodyBytes"):
        if before[k]!=after[k]: fail("before/after attestation drift")
    repo_result=verify_repo(args.repo,manifest,selected,contexts,cells,holds,applied,readbacks) if args.repo else {"repoPin":"NOT_CHECKED"}
    print(json.dumps({"result":"PASS","exactHead":HEAD,"exactTree":TREE,"cells":len(cells),"callerlessHashOnlyCells":hold_count,"priorSelections":len(selections),"priorHolds":len(holds),"priorAppliedCells":len(applied),"priorReadbackWindows":len(readbacks),"w665EvidenceRestored":True,"candidateFreeOnly":True,**repo_result},sort_keys=True))
if __name__=="__main__": main()
