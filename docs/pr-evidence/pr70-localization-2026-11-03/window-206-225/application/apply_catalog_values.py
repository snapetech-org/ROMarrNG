#!/usr/bin/env python3
import copy, hashlib, json, os, re, subprocess, sys, tempfile
from collections import Counter
from pathlib import Path
REPO=Path(sys.argv[1]).resolve()
INPUT=Path(sys.argv[2]).resolve()
ROOT_EVIDENCE=Path(sys.argv[3]).resolve()
CATALOG="romarr/ui-labels.json"
HEAD="bef31ca8a94f21273b11303524d79bd9c5344305"
TREE="7616d96ddd3a1bfe8078d43492eb5bea7213f080"
def rawsha(v): return hashlib.sha256(v.encode("utf-8")).hexdigest()
def canon(v): return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()
def readj(p): return json.loads(p.read_text(encoding="utf-8"))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def git(*args,binary=False): return subprocess.check_output(["git",*args],cwd=REPO,text=not binary)
def require(c,m):
    if not c: raise SystemExit("ABORT: "+m)
assertions=readj(INPUT/"manifest.json")
pins=readj(INPUT/"catalog-file-pins.json")
plan=readjl(ROOT_EVIDENCE/"apply-plan.jsonl")
ledger=readjl(ROOT_EVIDENCE/"root-adjudication.jsonl")
assertions_sha=hashlib.sha256((INPUT/"manifest.json").read_bytes()).hexdigest()
require(assertions["head"]==HEAD and assertions["tree"]==TREE,"input head/tree drift")
require(assertions["cellCount"]==240 and assertions["localeCount"]==12,"input coverage drift")
require(git("rev-parse","HEAD").strip()==HEAD,"worktree head drift")
require(git("rev-parse","HEAD^{tree}").strip()==TREE,"worktree tree drift")
require(git("status","--porcelain","--untracked-files=no").strip()=="","tracked worktree was not clean before application")
require(len(ledger)==240 and len(plan)==34,"root evidence row counts drift")
# Recheck every caller/source file pin from the sealed packet.
for path,pin in pins["callerFiles"].items():
    raw=git("show",f"{HEAD}:{path}",binary=True)
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    require(blob==pin["gitBlob"] and hashlib.sha256(raw).hexdigest()==pin["sha256"],"caller pin drift: "+path)
catpin=pins["clientCatalog"]
require(catpin["path"]==CATALOG,"catalog path drift")
baseline_raw=git("show",f"{HEAD}:{CATALOG}",binary=True)
baseline_blob=git("rev-parse",f"{HEAD}:{CATALOG}").strip()
require(hashlib.sha256(baseline_raw).hexdigest()==catpin["sha256"],"baseline catalog hash drift")
require(baseline_blob==catpin["gitBlob"],"baseline catalog blob drift")
require(len(baseline_raw)==catpin["byteCount"],"baseline catalog byte count drift")
baseline=json.loads(baseline_raw)
require((json.dumps(baseline,ensure_ascii=False,indent=2)+"\n").encode("utf-8")==baseline_raw,"baseline JSON format drift")
require(len(baseline["messages"])==1837,"message key count drift")
require(list(baseline["messages"])==list(json.loads((REPO/CATALOG).read_text(encoding="utf-8"))["messages"]),"worktree catalog key order drift")
inputs=readjl(INPUT/"current-target-cells.jsonl")
input_by={(r["sourceId"],r["locale"]):r for r in inputs}
decision_by={(r["sourceId"],r["locale"]):r for r in ledger}
plan_by={(r["sourceId"],r["locale"]):r for r in plan}
require(len(inputs)==len(input_by)==len(decision_by)==240,"duplicate or missing review cell")
require(input_by.keys()==decision_by.keys(),"input/root key mismatch")
require(len(plan_by)==34,"apply plan duplicate/missing")
for key,row in input_by.items():
    d=decision_by[key]
    message=baseline["messages"][row["sourceId"]]
    require(row["catalogPath"]==CATALOG and row["head"]==HEAD and row["tree"]==TREE,"cell pin drift")
    require(message["source"]==row["source"] and message["sourceHash"]==row["sourceSha256"],"source mismatch")
    require(message["translations"][row["locale"]]==row["currentTarget"],"current target mismatch")
    require(rawsha(row["currentTarget"])==row["currentTargetSha256"],"current raw hash mismatch")
    require(message["translationHashes"][row["locale"]]==canon(row["currentTarget"]),"stored translation hash mismatch")
    require(message["translationStatus"][row["locale"]]=="draft","translation status drift")
    require(d["currentTarget"]==row["currentTarget"] and d["currentTargetSha256"]==row["currentTargetSha256"],"adjudication current-value mismatch")
    disposition=d["rootDisposition"]; target=d["finalTarget"]
    require(disposition in ("accept-current","correction","refinement","hold"),"invalid disposition")
    require(rawsha(target)==d["finalTargetSha256"],"root target raw hash mismatch")
    if disposition in ("correction","refinement"):
        p=plan_by[key]
        require(p["target"]==target and p["targetSha256"]==rawsha(target),"apply target mismatch")
        require(p["expectedCurrent"]==row["currentTarget"] and p["expectedCurrentSha256"]==row["currentTargetSha256"],"apply current mismatch")
        require(target!=row["currentTarget"],"no-op change in apply plan")
    else:
        require(key not in plan_by and target==row["currentTarget"],"unexpected plan row or target")
require(set(plan_by)=={k for k,d in decision_by.items() if d["rootDisposition"] in ("correction","refinement")},"plan coverage mismatch")
updated=copy.deepcopy(baseline)
for (source_id,locale),p in plan_by.items():
    updated["messages"][source_id]["translations"][locale]=p["target"]
    updated["messages"][source_id]["translationHashes"][locale]=canon(p["target"])
require(list(updated)==list(baseline) and list(updated["messages"])==list(baseline["messages"]),"key/order changes")
allowed={(source_id,field,locale) for source_id,locale in plan_by for field in ("translations","translationHashes")}
for source_id,before in baseline["messages"].items():
    after=updated["messages"][source_id]
    require(before.keys()==after.keys(),"message field structure changed")
    for field in before:
        if field in ("translations","translationHashes"):
            require(before[field].keys()==after[field].keys(),"locale key structure changed")
            for locale in before[field]:
                if (source_id,field,locale) not in allowed:
                    require(before[field][locale]==after[field][locale],"unplanned catalog leaf changed")
        else:
            require(before[field]==after[field],"non-translation message field changed")
payload=(json.dumps(updated,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
target_path=REPO/CATALOG
with tempfile.NamedTemporaryFile(prefix=".ui-labels.w206-225-",dir=target_path.parent,delete=False) as f:
    temp=Path(f.name); f.write(payload); f.flush(); os.fsync(f.fileno())
try: os.replace(temp,target_path)
finally: temp.unlink(missing_ok=True)
actual_raw=target_path.read_bytes()
actual=json.loads(actual_raw)
require(actual==updated,"actual catalog differs from staged plan")
require(list(actual["messages"])==list(baseline["messages"]),"message order changed")
require(hashlib.sha256("\n".join(actual["messages"]).encode()).hexdigest()==hashlib.sha256("\n".join(baseline["messages"]).encode()).hexdigest(),"message order digest changed")
counts=Counter(); readback=[]
for key,row in input_by.items():
    d=decision_by[key]; m=actual["messages"][row["sourceId"]]
    value=m["translations"][row["locale"]]; th=m["translationHashes"][row["locale"]]
    status=m["translationStatus"][row["locale"]]; expected=d["finalTarget"]
    match=value==expected and th==canon(expected) and status=="draft"
    require(match,"readback mismatch")
    counts[d["rootDisposition"]]+=1
    readback.append({"position":row["position"],"sourceId":row["sourceId"],"locale":row["locale"],"disposition":d["rootDisposition"],"previousTarget":row["currentTarget"],"previousTargetRawSha256":row["currentTargetSha256"],"actualTarget":value,"actualTargetRawSha256":rawsha(value),"actualTranslationHash":th,"translationStatus":status,"changed":value!=row["currentTarget"],"match":match})
require(counts=={"accept-current":194,"correction":22,"refinement":12,"hold":12},str(counts))
require(sum(x["changed"] for x in readback)==34,"changed cell count mismatch")
(ROOT_EVIDENCE/"application"/"readback.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in readback),encoding="utf-8")
summary={"repository":"snapetech-org/ROMarrNG","pullRequest":70,"window":"W206-W225","baseHead":HEAD,"baseTree":TREE,"inputManifestSha256":assertions_sha,"baselineCatalogSha256":hashlib.sha256(baseline_raw).hexdigest(),"finalCatalogSha256":hashlib.sha256(actual_raw).hexdigest(),"cellsReadBack":len(readback),"mismatches":0,"changes":34,"rootDispositions":dict(counts),"messageKeys":len(actual["messages"]),"orderedMessageKeysUnchanged":True,"translationStatusPreserved":"draft","workflowsChanged":False}
(ROOT_EVIDENCE/"application"/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
