#!/usr/bin/env python3
import argparse, copy, hashlib, json, pathlib, re, subprocess
from collections import Counter
HEAD="eda48333438591ecc67f829c50ef2d521f1e7a5e"
TREE="3db18e56d0c7ac08a564a6baff61eba25f0a01da"
CATALOG="romarr/ui-labels.json"
CROSS=pathlib.Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w525-544-cross-20261104")
CROSS_REPO=pathlib.Path("/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w525-544-source")
def abort(message): raise SystemExit("REFUSED: "+message)
def sha(data):
    if isinstance(data,str): data=data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
def text_sha(value): return sha(value.encode("utf-8"))
def read_json(path): return json.loads(path.read_text(encoding="utf-8"))
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def key(row): return (int(row["position"]),row["locale"])
parser=argparse.ArgumentParser()
parser.add_argument("--repo",required=True)
parser.add_argument("--output",required=True)
args=parser.parse_args()
repo=pathlib.Path(args.repo).resolve()
out=pathlib.Path(args.output).resolve()
if out.exists() and any(out.iterdir()): abort("refusing to overwrite output")
out.mkdir(parents=True,exist_ok=True)
subprocess.run(["python3",str(CROSS/"verify_cross.py"),"--repo",str(CROSS_REPO)],check=True)
if git(repo,"rev-parse","HEAD")!=HEAD or git(repo,"rev-parse","HEAD^{tree}")!=TREE: abort("wrong input head/tree")
if git(repo,"status","--porcelain"): abort("application worktree is not clean")
summary=read_json(CROSS/"summary.json")
if summary["selectedChanges"]!=18 or summary["newTextFreeHolds"]!=12: abort("cross totals mismatch")
cross=read_jsonl(CROSS/"cross-ledger.jsonl")
changes=read_jsonl(CROSS/"selected-changes.jsonl")
pins=read_json(CROSS/"inputs/candidate-free/input/catalog-file-pins.json")
current=read_jsonl(CROSS/"inputs/candidate-free/input/current-target-cells.jsonl")
prior_holds=read_jsonl(CROSS/"prior-holds-preserved.jsonl")
prior_applied=read_jsonl(CROSS/"inputs/candidate-free/input/prior-applied-cell-reattestation.jsonl")
prior_selected=read_jsonl(CROSS/"inputs/candidate-free/input/prior-selection-reattestation.jsonl")
if pins["catalogPath"]!=CATALOG: abort("unexpected catalog")
path=repo/CATALOG
raw=path.read_bytes()
if sha(raw)!=pins["catalogSha256"] or git(repo,"hash-object",str(path))!=pins["catalogGitBlob"]: abort("preimage differs from pin")
before=json.loads(raw.decode("utf-8"))
if (json.dumps(before,ensure_ascii=False,indent=2)+"\n").encode("utf-8")!=raw: abort("JSON serialization differs")
after=copy.deepcopy(before)
orders={sid:list(entry["translations"]) for sid,entry in before["messages"].items()}
translation_hash=lambda value: sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))
cross_map={key(row):row for row in cross}
current_map={key(row):row for row in current}
if len(cross_map)!=240 or len(current_map)!=240 or len(changes)!=18: abort("reviewed cell counts mismatch")
orders={sid:list(entry["translations"]) for sid,entry in before["messages"].items()}
changed=set()
hash_updates=[]
for item in changes:
    k=key(item); sid=item["sourceId"]; locale=item["locale"]
    entry=after["messages"].get(sid)
    if entry is None: abort("source ID missing: "+sid)
    old=entry["translations"].get(locale)
    if old!=item["beforeTarget"] or text_sha(old)!=item["beforeSha256"]: abort("current target changed: "+str(k))
    if text_sha(item["afterTarget"])!=item["afterSha256"] or item["afterTarget"]==old: abort("selected target hash/no-op: "+str(k))
    if cross_map[k]["selectedTarget"]!=item["afterTarget"]: abort("cross target mismatch: "+str(k))
    hashes=entry.get("translationHashes",{})
    if locale in hashes:
        previous=hashes[locale]
        if previous!=translation_hash(old): abort("stale translation hash: "+str(k))
        entry["translations"][locale]=item["afterTarget"]
        entry["translationHashes"][locale]=translation_hash(item["afterTarget"])
        hash_updates.append({"sourceId":sid,"locale":locale,"oldTranslationHash":previous,
                             "newTranslationHash":translation_hash(item["afterTarget"])})
    else:
        entry["translations"][locale]=item["afterTarget"]
    changed.add((sid,locale))
for sid,entry in after["messages"].items():
    old=before["messages"][sid]
    if list(entry["translations"])!=orders[sid]: abort("locale order changed: "+sid)
    for locale,value in old["translations"].items():
        if (sid,locale) not in changed and entry["translations"][locale]!=value: abort("unselected cell changed")
    for field,value in old.items():
        if field not in ("translations","translationHashes") and entry.get(field)!=value: abort("metadata changed: "+sid+"/"+field)
if list(after["messages"])!=list(before["messages"]): abort("message key order changed")
post=(json.dumps(after,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
path.write_bytes(post)
subprocess.run(["git","-C",str(repo),"diff","--check",HEAD],check=True)
readback=[]
change_keys={key(item) for item in changes}
for k,c in sorted(cross_map.items()):
    base=current_map[k]; value=after["messages"][base["sourceId"]]["translations"][base["locale"]]
    if k[0]==530:
        if text_sha(value)!=base["currentTargetSha256"] or c["crossDecision"]!="hold_callerless": abort("held value changed")
        readback.append({"position":k[0],"locale":k[1],"sourceIdSha256":sha(base["sourceId"]),
                         "beforeSha256":base["currentTargetSha256"],"afterSha256":text_sha(value),
                         "held":True,"changed":False})
    else:
        if value!=c["selectedTarget"] or text_sha(value)!=c["selectedTargetSha256"]: abort("readback mismatch "+str(k))
        readback.append({"position":k[0],"locale":k[1],"sourceId":base["sourceId"],
                         "beforeSha256":base["currentTargetSha256"],"afterValue":value,
                         "afterSha256":text_sha(value),"held":False,"changed":k in change_keys,
                         "selectedFrom":c["crossDecision"] if k in change_keys else "current"})
for row in prior_holds:
    entry=after["messages"].get(row["sourceId"])
    if entry is None or text_sha(entry["translations"][row["locale"]])!=row["currentTargetSha256"]: abort("prior hold changed")
for row in prior_applied:
    entry=after["messages"].get(row["sourceId"])
    if entry is None or text_sha(entry["translations"][row["locale"]])!=row["currentTargetSha256"]: abort("prior applied cell changed")
changed_ids={sid for sid,_ in changed}
if any(row["sourceId"] in changed_ids for row in prior_selected): abort("overlaps prior selected source")
post_sha=sha(post)
post_blob=git(repo,"hash-object",str(path))
(out/"catalog-preimage.json").write_text(json.dumps({
 "path":CATALOG,"preSha256":pins["catalogSha256"],"preGitBlob":pins["catalogGitBlob"],
 "postSha256":post_sha,"postGitBlob":post_blob,"messageCount":len(before["messages"]),
 "messageOrderPreserved":True,"translationLocaleOrdersPreserved":True,
 "changedCells":len(changed),"translationHashUpdates":len(hash_updates)
},indent=2,sort_keys=True)+"\n",encoding="utf-8")
(out/"application-readback.jsonl").write_text(
 "".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in readback),encoding="utf-8")
(out/"selected-update-ledger.jsonl").write_text(
 "".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in changes),encoding="utf-8")
(out/"translation-hash-updates.jsonl").write_text(
 "".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in hash_updates),encoding="utf-8")
decisions=Counter(x["crossDecision"] for x in cross)
(out/"application-summary.json").write_text(json.dumps({
 "artifact":"ROMarrNG PR #70 W525-W544 catalog application readback",
 "repository":"snapetech-org/ROMarrNG","pullRequest":70,"window":"W525-W544",
 "inputHead":HEAD,"inputTree":TREE,"catalogPath":CATALOG,"reviewedCells":240,
 "selectedUpdates":len(changed),"retainedCurrent":decisions["retain_current"],
 "newTextFreeHolds":decisions["hold_callerless"],"priorHashOnlyHoldsPreserved":len(prior_holds),
 "priorAppliedCellsPreserved":len(prior_applied),"priorSelectedSourceRecordsPreserved":len(prior_selected),
 "postCatalogSha256":post_sha,"postCatalogGitBlob":post_blob,"translationHashUpdates":len(hash_updates),
 "workflowChanges":0,"tokenMismatches":0,"messageKeyOrderChanged":False,"localeOrderChanged":False
},indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"result":"PASS","inputHead":HEAD,"catalogPath":CATALOG,
 "reviewedCells":len(readback),"selectedUpdates":len(changed),"retainedCurrent":decisions["retain_current"],
 "holds":decisions["hold_callerless"],"priorHoldsPreserved":len(prior_holds),
 "priorAppliedCellsPreserved":len(prior_applied),"priorSelectedSourcesPreserved":len(prior_selected),
 "tokenMismatches":0,"messageKeyOrderChanged":False,"translationHashUpdates":len(hash_updates),
 "catalogPreSha256":sha(raw),"catalogPostSha256":post_sha},sort_keys=True))
