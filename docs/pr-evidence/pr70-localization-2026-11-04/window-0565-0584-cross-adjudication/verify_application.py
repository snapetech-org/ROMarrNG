#!/usr/bin/env python3
"""Verify ROMarrNG PR #70 W565-W584 application and all 240 post-application cells."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

HEAD = "726db9138af2fc716056c7c36a9e842de04265e0"
PRODUCT = "89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac"
PRODUCT_TREE = "919e8da45270e8938db8ca0b1634e38028d147a5"
CATALOG = "romarr/ui-labels.json"
WINDOW = "W565-W584"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
MARKUP = re.compile(r"<[^>]*>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
FORBIDDEN_HOLD_FIELDS = {"sourceId","source","sourceText","currentTarget","beforeTarget","afterTarget","proposedTarget","selectedTarget","recommendedTarget","rationale"}

def sha(v):
    if isinstance(v,str): v=v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()

def read_json(p): return json.loads(p.read_text(encoding="utf-8"))
def read_jsonl(p):
    out=[]
    for raw in p.read_bytes().splitlines():
        if raw.strip(): out.append((json.loads(raw),sha(raw)))
    return out

def need(value,message):
    if not value: raise SystemExit("FAIL: "+message)

def checksum_dir(root, relsum="SHA256SUMS.txt"):
    lines=(root/relsum).read_text(encoding="utf-8").splitlines()
    listed={}
    for line in lines:
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.strip(); listed[rel]=expected
        path=root/rel
        need(path.is_file() and sha(path.read_bytes())==expected,f"checksum {root}/{rel}")
    return listed

def verify_packet(root):
    listed=checksum_dir(root)
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.relative_to(root).as_posix()!="SHA256SUMS.txt"}
    need(set(listed)==actual,"evidence checksum coverage")
    manifest=read_json(root/"manifest.json")
    file_map={x["path"]:x for x in manifest["files"]}
    expected=actual-{"manifest.json"}
    need(set(file_map)==expected,"evidence manifest coverage")
    for rel,record in file_map.items():
        raw=(root/rel).read_bytes()
        need(record["bytes"]==len(raw) and record["sha256"]==sha(raw),"manifest file hash "+rel)

def check_input_sums(directory):
    checksum_dir(directory)

def key(row):
    return (int(row.get("catalogZeroBasedIndex",row.get("position"))),row["locale"])

def keyed(path):
    out={}
    for row,digest in read_jsonl(path):
        k=key(row)
        need(k not in out,"duplicate "+str(k)+" in "+path.name)
        out[k]=(row,digest)
    return out

def git(repo,*args):
    return subprocess.check_output(["git","-C",str(repo),*args])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,required=True)
    ap.add_argument("--candidate-free",type=Path,required=True)
    ap.add_argument("--primary",type=Path,required=True)
    ap.add_argument("--blind",type=Path,required=True)
    args=ap.parse_args()
    repo=args.repo.resolve(); cf=args.candidate_free.resolve(); primary=args.primary.resolve(); blind=args.blind.resolve()
    root=Path(__file__).resolve().parent
    verify_packet(root)
    for d in (cf,primary.parent,primary,blind): check_input_sums(d)
    # Verify the copied cross packet against the original candidate-free and review packets.
    subprocess.run(["python3",str(root/"cross-review"/"verify_cross_review.py"),"--candidate-free",str(cf),"--primary",str(primary),"--blind",str(blind)],check=True)

    summary=read_json(root/"application-summary.json")
    pins=read_json(root/"catalog-pins.json")
    prov=read_json(root/"cross-packet-provenance.json")
    before_att=read_json(root/"PR-attestation-before.json")
    after_att=read_json(root/"PR-attestation-after-product.json")
    need((summary["preHead"],summary["productCommit"],summary["productTree"],summary["window"])==(HEAD,PRODUCT,PRODUCT_TREE,WINDOW),"summary pins")
    need(git(repo,"rev-parse",PRODUCT).decode().strip()==PRODUCT and git(repo,"rev-parse",PRODUCT+"^{tree}").decode().strip()==PRODUCT_TREE,"product commit/tree")
    need(git(repo,"rev-parse",PRODUCT+"^").decode().strip()==HEAD,"product parent")
    need(git(repo,"merge-base","--is-ancestor",PRODUCT,"HEAD").decode()=="" ,"product ancestry")
    need(git(repo,"diff-tree","--no-commit-id","--name-only","-r",PRODUCT).decode().splitlines()==[CATALOG],"product commit file scope")
    need(before_att["pullRequest"]["headSha"]==HEAD and before_att["pullRequest"]["headTree"]=="6669dc9117dbbbe6587d4183ec5bd0184c87e983","pre-application PR pin")
    fresh=before_att["finalizationFreshRecheck"]
    need(fresh["performedBeforeCatalogWrite"] and fresh["pullRequest"]["headSha"]==HEAD and fresh["branchRef"]["sha"]==HEAD and fresh["pullHeadRef"]["sha"]==HEAD,"fresh pre-write ref attestation")
    need(after_att["pullRequest"]["headSha"]==PRODUCT and after_att["pullRequest"]["headTree"]==PRODUCT_TREE,"post-product PR head/tree")
    need(after_att["refs"]["branch"]["sha"]==PRODUCT and after_att["refs"]["pullHead"]["sha"]==PRODUCT,"post-product branch/pull refs")
    need(after_att["sourceWorktree"]["clean"] and after_att["sourceWorktree"]["head"]==PRODUCT,"post-product worktree")
    need(after_att["pullRequest"]["state"]=="OPEN" and after_att["pullRequest"]["draft"] is True,"PR open/draft")
    need(before_att["pullRequest"]["baseApiSha"]==after_att["pullRequest"]["baseApiSha"]=="bcd1eb41b5cdf8202acb5cf8e365e14761b743b5","base API pin")
    need(before_att["refs"]["liveMain"]["sha"]==after_att["refs"]["liveMain"]["sha"]=="65d8747e3a068473396227bae5e85ddc71c7d4d8","live main pin")
    need(after_att["baseDrift"]["apiBaseRefMismatch"] is True,"base drift was hidden")

    input_manifest=read_json(cf/"manifest.json")
    pre_raw=git(repo,"show",f"{HEAD}:{CATALOG}")
    post_raw=git(repo,"show",f"{PRODUCT}:{CATALOG}")
    need(sha(pre_raw)==input_manifest["catalogSha256"]==pins["preCatalogSha256"],"pre-catalog hash")
    need(sha(post_raw)==pins["postCatalogSha256"],"post-catalog hash")
    need(git(repo,"rev-parse",f"{HEAD}:{CATALOG}").decode().strip()==pins["preCatalogGitBlob"],"pre-catalog blob")
    need(git(repo,"rev-parse",f"{PRODUCT}:{CATALOG}").decode().strip()==pins["postCatalogGitBlob"],"post-catalog blob")
    pre=json.loads(pre_raw); post=json.loads(post_raw)
    need(len(pre["messages"])==len(post["messages"])==1836 and list(pre["messages"])==list(post["messages"]),"catalog key order/count")
    need(list(pre["locales"])==list(post["locales"])==pins["localeOrder"],"locale registry order")
    key_order=sha(("\n".join(pre["messages"])+"\n").encode("utf-8"))
    need(key_order==input_manifest["catalogKeyOrderSha256"]==pins["catalogKeyOrderSha256"],"catalog key order hash")

    contexts={}
    for row,digest in read_jsonl(cf/"source-contexts.jsonl"): contexts[row["sourceId"]]=(row,digest)
    current=keyed(cf/"current-target-cells.jsonl")
    cross=keyed(root/"cross-review"/"cross-review-cells.jsonl")
    readback=keyed(root/"application-readback.jsonl")
    expected={(i,loc) for i in range(565,585) for loc in LOCALES}
    need(set(current)==set(cross)==set(readback)==expected,"240-cell coverage")
    changes=[json.loads(x) for x in (root/"selected-changes.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    need(len(changes)==1,"one selected change")
    change=changes[0]
    need((change["catalogZeroBasedIndex"],change["sourceId"],change["locale"],change["recommendedTarget"])==(573,"ui.invitation.af4ea02852","de","Einladung"),"selected change identity/target")
    need(sha(change["recommendedTarget"])==change["recommendedTargetSha256"],"selected target hash")
    hold_lines=read_jsonl(root/"holds.jsonl")
    need(len(hold_lines)==40,"40 hold records")
    for h,_ in hold_lines: need(not(FORBIDDEN_HOLD_FIELDS & set(h)),"hold file contains text/identifier")

    changed=kept=held=0
    mismatches=collections.Counter()
    for k in sorted(expected,key=lambda x:(x[0],LOCALES.index(x[1]))):
        c,csha=current[k]; x,xsha=cross[k]; rb,_=readback[k]
        sid=c["sourceId"]; ctx,ctxsha=contexts[sid]
        source=post["messages"][sid]["source"]
        source_sha=sha(source)
        before_target=c["currentTarget"]
        before_sha=sha(before_target)
        after_target=post["messages"][sid]["translations"][k[1]]
        after_sha=sha(after_target)
        idx,loc=k
        need(list(pre["messages"]).index(sid)==idx,"catalog index "+str(k))
        need(source_sha==ctx["sourceSha256"]==c["sourceSha256"]==x["sourceSha256"]==rb["sourceSha256"],"source hash "+str(k))
        need(before_sha==c["currentTargetSha256"]==x["currentTargetSha256"]==rb["beforeTargetSha256"],"pre-target hash "+str(k))
        need(rb["afterTargetSha256"]==after_sha and rb["callerContextSha256"]==ctx["contextSha256"]==x["callerContextSha256"],"readback target/context "+str(k))
        need(rb["candidateFreeSourceContextRowSha256"]==ctxsha and rb["candidateFreeCurrentTargetRowSha256"]==csha and rb["crossReviewCellRowSha256"]==xsha,"row hash linkage "+str(k))
        if x["disposition"]=="recommend-change":
            need((sid,loc)==("ui.invitation.af4ea02852","de"),"unexpected change row")
            need(after_target==change["recommendedTarget"] and after_sha==change["recommendedTargetSha256"] and rb["disposition"]=="selected-change" and rb["changed"] is True,"selected target readback")
            need(rb.get("sourceId")==sid and rb["selectedTargetSha256"]==after_sha,"selected readback identity")
            changed+=1
        elif x["disposition"]=="hold-text-free":
            need(after_sha==before_sha and rb["disposition"]=="hold-text-free" and rb["changed"] is False,"held cell changed")
            need(not(FORBIDDEN_HOLD_FIELDS & set(rb)) and rb.get("holdReasonCode")==x["holdReasonCode"] and rb.get("callerless")==x["callerless"],"hold row is not text-free/hash-linked")
            need("sourceId" not in rb,"held readback exposes source ID")
            held+=1
        else:
            need(x["disposition"]=="accept-current" and after_sha==before_sha and rb["disposition"]=="keep-current" and rb["changed"] is False,"unselected cell changed")
            need(rb.get("sourceId")==sid,"kept row source linkage")
            kept+=1
        # Check source-token parity in both the preimage and the applied catalog value.
        placeholders=collections.Counter(PLACEHOLDER.findall(source))
        markup=collections.Counter(MARKUP.findall(source))
        numbers=collections.Counter(NUMBER.findall(source))
        protected=c.get("sourceProtectedLiterals",[])
        for target in (before_target,after_target):
            if collections.Counter(PLACEHOLDER.findall(target))!=placeholders: mismatches["placeholder"]+=1
            if collections.Counter(MARKUP.findall(target))!=markup: mismatches["markup"]+=1
            if collections.Counter(NUMBER.findall(target))!=numbers: mismatches["numeric"]+=1
            if any(term not in target for term in protected): mismatches["protectedLiteral"]+=1
    need((changed,kept,held)==(1,199,40),"final readback totals")
    need(not mismatches,"token mismatches "+json.dumps(mismatches))
    # The only catalog value change is the selected translation; all metadata remains byte-value stable.
    for sid,old in pre["messages"].items():
        new=post["messages"][sid]
        for field in ("source","sourceHash","translationHashes","translationStatus","translationReview"):
            need(old.get(field)==new.get(field),"message metadata "+sid+"/"+field)
        for loc,oldval in old["translations"].items():
            expectedval=change["recommendedTarget"] if (sid,loc)==(change["sourceId"],change["locale"]) else oldval
            need(new["translations"][loc]==expectedval,"unexpected locale edit "+sid+"/"+loc)
    need(summary["readbackCellCount"]==240 and summary["changedCellCount"]==1 and summary["keptCurrentCellCount"]==199 and summary["textFreeHoldCount"]==40,"summary counts")
    need(summary["nonTargetProductFilesChanged"]==0 and summary["translationMetadataChanged"] is False,"summary scope/metadata")
    need(summary["placeholderMismatches"]==summary["markupMismatches"]==summary["numericMismatches"]==summary["protectedLiteralMismatches"]==0,"summary token checks")
    print(json.dumps({"result":"PASS","productCommit":PRODUCT,"productTree":PRODUCT_TREE,"cells":240,"changed":changed,"keepCurrent":kept,"textFreeHolds":held,"tokenMismatches":dict(mismatches),"crossReview":"PASS","checksums":"PASS"},sort_keys=True))

if __name__=="__main__": main()

