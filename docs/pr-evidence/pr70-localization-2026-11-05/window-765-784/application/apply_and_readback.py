#!/usr/bin/env python3
"""Exact-hash catalog application and readback for ROMarrNG W765-W784."""
from __future__ import annotations
import collections, copy, hashlib, json, re, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
WINDOW=HERE.parent
REPO=HERE.parents[4]
HEAD="9714d7cf69c687685b4f65cbd9627a56830bab85"
TREE="c8eb66573f10b2390a02df05033f5133425d5e41"
CATALOG="romarr/ui-labels.json"
ROOT=WINDOW/"root-adjudication"/"root-adjudication.jsonl"
PLAN=HERE/"exact-hash-apply-plan.jsonl"
READBACK=HERE/"final-head-readback.jsonl"
SUMMARY=HERE/"application-summary.json"
PRODUCT_PIN=HERE/"product-commit.json"
PREFLIGHT=HERE/"preflight.json"

def sha(value):
    if isinstance(value,str): value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()
def read_jsonl(path): return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def git(*args): return subprocess.check_output(["git","-C",str(REPO),*args])
def replace_target_lines(text, plan):
    lines=text.splitlines(keepends=True)
    for row in plan:
        sid=row["sourceId"]; locale=row["locale"]
        marker=f'    {json.dumps(sid,ensure_ascii=False)}: {{'
        try: start=next(i for i,line in enumerate(lines) if line.rstrip("\n")==marker)
        except StopIteration: raise SystemExit(f"source id block missing: {sid}")
        try: tstart=next(i for i in range(start+1,len(lines)) if lines[i].rstrip("\n")=="      \"translations\": {")
        except StopIteration: raise SystemExit(f"translations block missing: {sid}")
        try: tend=next(i for i in range(tstart+1,len(lines)) if lines[i].rstrip("\n")=="      },")
        except StopIteration: raise SystemExit(f"translations close missing: {sid}")
        prefix=f'        {json.dumps(locale,ensure_ascii=False)}: '
        matches=[i for i in range(tstart+1,tend) if lines[i].startswith(prefix)]
        if len(matches)!=1: raise SystemExit(f"locale line mismatch: {sid}::{locale}")
        i=matches[0]; line=lines[i]; newline="\n" if line.endswith("\n") else ""
        value_part=line[len(prefix):].rstrip("\n")
        has_comma=value_part.endswith(",")
        parsed=json.loads(value_part[:-1] if has_comma else value_part)
        if parsed!=row["before"]: raise SystemExit(f"exact before-value mismatch: {sid}::{locale}")
        if sha(parsed)!=row["beforeSha256"]: raise SystemExit(f"before hash mismatch: {sid}::{locale}")
        suffix="," if has_comma else ""
        lines[i]=prefix+json.dumps(row["after"],ensure_ascii=False)+suffix+newline
    return "".join(lines)

def main():
    mode="verify" if "--verify-after" in sys.argv else "apply" if "--apply" in sys.argv else "preflight"
    head=git("rev-parse","HEAD").decode().strip(); tree=git("rev-parse","HEAD^{tree}").decode().strip()
    if mode!="verify" and (head,tree)!=(HEAD,TREE): raise SystemExit("input HEAD/tree mismatch")
    if mode!="verify" and (git("diff","--quiet").decode() if False else subprocess.run(["git","-C",str(REPO),"diff","--quiet"]).returncode!=0 or subprocess.run(["git","-C",str(REPO),"diff","--cached","--quiet"]).returncode!=0):
        raise SystemExit("tracked changes exist before catalog application")
    root=read_jsonl(ROOT); plan=read_jsonl(PLAN)
    if len(root)!=240 or len(plan)!=10: raise SystemExit("root ledger or exact-hash plan coverage mismatch")
    counts=collections.Counter(r["rootDisposition"] for r in root)
    expected={"accept-current":206,"correction":3,"refinement":7,"hold-callerless-hash-only":24}
    if dict(counts)!=expected: raise SystemExit(f"root disposition counts mismatch: {counts}")
    if any(r.get("callerless") and any(k in r for k in ("source","before","after")) for r in root): raise SystemExit("callerless hold exposes text")
    if sum(r.get("rootOverride") is True for r in root)!=10: raise SystemExit("root override count mismatch")
    raw=git("show",f"{HEAD}:{CATALOG}"); before_hash=sha(raw)
    catalog_path=REPO/CATALOG
    current_raw=catalog_path.read_bytes()
    if mode!="verify" and sha(current_raw)!=before_hash: raise SystemExit("catalog blob differs from pinned input")
    old=json.loads(raw); current=json.loads(current_raw)
    if old!=current and mode!="verify": raise SystemExit("catalog changed since pinned input")
    for row in plan:
        msg=old.get("messages",{}).get(row["sourceId"])
        if not msg or msg.get("sourceHash")!=row["sourceSha256"] or sha(msg.get("source",""))!=row["sourceSha256"]: raise SystemExit("source hash mismatch: "+row["sourceId"])
        if msg["translations"].get(row["locale"])!=row["before"]: raise SystemExit("target value mismatch before apply")
        if sha(row["after"])!=row["afterSha256"]: raise SystemExit("selected target hash mismatch")
    if mode=="apply":
        updated=replace_target_lines(current_raw.decode("utf-8"),plan).encode("utf-8")
        tmp=catalog_path.with_suffix(catalog_path.suffix+".w765-784.tmp")
        try:
            tmp.write_bytes(updated); parsed=json.loads(tmp.read_text(encoding="utf-8")); tmp.replace(catalog_path)
        finally:
            if tmp.exists(): tmp.unlink()
        current_raw=catalog_path.read_bytes(); current=parsed
    # Validate only the ten selected translation values changed.
    expected_data=copy.deepcopy(old)
    for row in plan: expected_data["messages"][row["sourceId"]]["translations"][row["locale"]]=row["after"]
    if current!=expected_data: raise SystemExit("catalog has unrelated or missing changes")
    if list(current["messages"])!=list(old["messages"]): raise SystemExit("message order changed")
    readback=[]
    for row in root:
        sid=row["sourceId"]; locale=row["locale"]
        got=current["messages"][sid]["translations"][locale]
        if row["callerless"]:
            if sha(got)!=row["beforeSha256"] or row["afterSha256"]!=row["beforeSha256"]: raise SystemExit("hash-only hold readback failed")
            readback.append({"sourceId":sid,"locale":locale,"callerless":True,"disposition":row["rootDisposition"],"beforeSha256":row["beforeSha256"],"afterSha256":sha(got),"position":row["position"],"oneBasedPosition":row["oneBasedPosition"]})
        else:
            if got!=row["after"] or sha(got)!=row["afterSha256"]: raise SystemExit("exact 240-cell readback failed")
            readback.append({"sourceId":sid,"locale":locale,"callerless":False,"disposition":row["rootDisposition"],"beforeSha256":row["beforeSha256"],"after":got,"afterSha256":sha(got),"position":row["position"],"oneBasedPosition":row["oneBasedPosition"],"callerContextSha256":row["callerContextSha256"],"rootOverride":row["rootOverride"]})
    if len(readback)!=240 or sum(bool(r["callerless"]) for r in readback)!=24: raise SystemExit("full readback coverage mismatch")
    READBACK.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in readback),encoding="utf-8")
    previous_summary=json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}
    summary={"result":"PASS","inputHead":HEAD,"inputTree":TREE,"window":"W765-W784","rootCells":240,"readbackCells":240,"readbackCallerBacked":216,"readbackHashOnly":24,"changedCatalogCells":10,"catalogPath":CATALOG,"catalogSha256Before":before_hash,"catalogSha256After":sha(current_raw),"dispositions":dict(counts),"priorActiveHolds":988,"activeHoldsAfter":1012,"catalogKeysPreserved":list(current["messages"])==list(old["messages"]),"onlySelectedValuesChanged":True,"qualifiedNativeSpeakerApproval":False,"mode":mode}
    if PRODUCT_PIN.exists():
        product=json.loads(PRODUCT_PIN.read_text(encoding="utf-8")); pc=product["productCommit"]
        actual_tree=git("rev-parse",f"{pc}^{{tree}}").decode().strip()
        if actual_tree!=product["productTree"] or product["catalogSha256"]!=sha(current_raw): raise SystemExit("product commit pin/catalog digest mismatch")
        if subprocess.run(["git","-C",str(REPO),"merge-base","--is-ancestor",pc,"HEAD"]).returncode!=0: raise SystemExit("product commit is not an ancestor of current HEAD")
        summary.update({"productCommit":pc,"productTree":actual_tree,"verificationHead":previous_summary.get("verificationHead",head)})
    SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if mode=="preflight":
        PREFLIGHT.write_text(json.dumps({"result":"PASS","head":head,"tree":tree,"catalogSha256":before_hash,"rootPlanCells":len(plan),"trackedWorktreeClean":True},indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
