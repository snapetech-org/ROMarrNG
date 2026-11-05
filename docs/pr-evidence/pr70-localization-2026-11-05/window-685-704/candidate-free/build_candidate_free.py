#!/usr/bin/env python3
"""Build the ROMarrNG PR #70 W685-W704 candidate-free input packet."""
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

HEAD="43d2858744ef20cd58462643fed534ac61d2ffad"
TREE="73e8f50d65cb611def996b01bab0b00628b65860"
BRANCH="task/localization-translation-review-20261030"
PREV_HEAD="9f8832f67195323955172dd4c3c40e29cbabb5da"
PREV_TREE="d6066baa3d03d3b4c6034e5af061fc4bc278b0f9"
PREV_PRODUCT="fee1da731d13c578d1911884a1567d0124187d29"
PREV_PRODUCT_TREE="fae55bb1f52f49da93bec989fa4feb86dd87548e"
WINDOW="W685-W704"
PREV_WINDOW="W645-W664"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
PLACEHOLDER=re.compile(r"\{[^{}]+\}")
TAG=re.compile(r"<[^>]+>")
NUMBER=re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED=[
 "Gaseous","Retrom","SeerrNG","ROMarrNG","ROMarr","ES-DE","No-Intro","Redump","DAT","IGDB","ISO9660",
 "PLAYSTATION","PlayStation","PS2","ROMs","ROM","PC","API","ROMARR_API_KEY","Linksnappy","Moonlight",
 "PIN","NPSSO","NZBHydra2","Newznab","/torznab/api","NZBVortex","HTTPS","NZB","Preferences"]
PREV_TASK=Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w645-664-20261105")
PREV_PACKET=PREV_TASK/"candidate-free"
PREV_INPUT=PREV_PACKET/"candidate-free"/"input"
PREV_APP=PREV_TASK/"application"
PREV_PRIMARY=PREV_TASK/"primary"
PREV_BLIND=PREV_TASK/"blind-review"
PREV_CROSS=PREV_TASK/"cross-review"
PREV_ROOT_REVIEW=PREV_TASK/"root-adjudication"
PREV_W625_TASK=Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w625-644-20261105")
PREV_W625_ROOT=PREV_W625_TASK/"root-application"
PREV_APP_REL="docs/pr-evidence/pr70-localization-2026-11-05/window-645-664/application"

def sha(v):
 if isinstance(v,str): v=v.encode("utf-8")
 return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def rj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def wj(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def wjl(p,rows):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for x in rows),encoding="utf-8")
write_json=wj
write_jsonl=wjl
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def verify_sums(root,filename="SHA256SUMS.txt"):
 root=Path(root); sf=root/filename; listed={}
 for line in sf.read_text(encoding="utf-8").splitlines():
  if not line.strip(): continue
  digest,name=line.split("  ",1); path=(root/name).resolve()
  if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes())!=digest: raise SystemExit(f"FAIL checksum {root}/{name}")
  if name in listed: raise SystemExit(f"FAIL duplicate checksum entry {name}")
  listed[name]=digest
 actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p!=sf}
 if set(listed)!=actual: raise SystemExit(f"FAIL checksum coverage {root}")
 return listed

def verify_listed_sums(root,filename="SHA256SUMS.txt"):
 root=Path(root);sf=root/filename;listed={}
 for line in sf.read_text(encoding="utf-8").splitlines():
  if not line.strip():continue
  digest,name=line.split("  ",1);path=(root/name).resolve()
  if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes())!=digest:raise SystemExit(f"FAIL checksum {root}/{name}")
  if name in listed:raise SystemExit(f"FAIL duplicate checksum entry {name}")
  listed[name]=digest
 actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p!=sf}
 return listed, sorted(actual-set(listed))

def attestation(repo):
 pr=json.loads(subprocess.check_output(["gh","api","repos/snapetech-org/ROMarrNG/pulls/70"],cwd=repo,text=True))
 cap=json.loads(subprocess.check_output(["gh","api",f"repos/snapetech-org/ROMarrNG/commits/{HEAD}"],cwd=repo,text=True))
 raw=git(repo,"ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/70/head","refs/heads/main")
 refs={x.split("\t")[1]:x.split("\t")[0] for x in raw.splitlines() if x.strip()}
 body=pr.get("body") or ""
 z={"attestedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"repository":"snapetech-org/ROMarrNG","pullRequest":70,
 "state":pr["state"].upper(),"draft":bool(pr["draft"]),"merged":bool(pr["merged"]),"headRefName":pr["head"]["ref"],
 "head":pr["head"]["sha"],"tree":git(repo,"rev-parse",f"{HEAD}^{{tree}}"),"apiCommitTree":cap["commit"]["tree"]["sha"],
 "branchRefOid":refs.get(f"refs/heads/{BRANCH}"),"pullRefOid":refs.get("refs/pull/70/head"),"baseRefName":pr["base"]["ref"],
 "baseApiSha":pr["base"]["sha"],"baseLiveRefOid":refs.get("refs/heads/main"),"baseApiRefMismatch":pr["base"]["sha"]!=refs.get("refs/heads/main"),
 "bodySha256":sha(body),"bodyBytes":len(body.encode()),"checksRerun":False}
 exp=("OPEN",True,False,BRANCH,HEAD,TREE,TREE,HEAD,HEAD,"main")
 act=(z["state"],z["draft"],z["merged"],z["headRefName"],z["head"],z["tree"],z["apiCommitTree"],z["branchRefOid"],z["pullRefOid"],z["baseRefName"])
 if act!=exp: raise SystemExit("FAIL PR/API/branch/pull alignment "+repr(z))
 if git(repo,"rev-parse","HEAD")!=HEAD or git(repo,"rev-parse","HEAD^{tree}")!=TREE: raise SystemExit("FAIL exact source pin")
 if git(repo,"status","--porcelain=v1","--untracked-files=all") or git(repo,"branch","--show-current"): raise SystemExit("FAIL worktree dirty or attached")
 return z
def protected(s):
 out=[]
 for literal in PROTECTED:
  match=literal in s if literal.startswith("/") else bool(re.search(r"(?<![A-Za-z0-9])"+re.escape(literal)+r"(?![A-Za-z0-9])",s))
  if match: out.append(literal)
 return sorted(set(out))
def tokens(s): return {"placeholders":PLACEHOLDER.findall(s),"markup":TAG.findall(s),"numbers":NUMBER.findall(s),"protectedLiterals":protected(s)}
def production_paths(repo,commit):
 raw=subprocess.check_output(["git","-C",str(repo),"ls-tree","-r","--name-only",commit,"--","romarr"],text=True).splitlines()
 ok={".py",".js",".html",".jinja",".jinja2",".css",".ts",".tsx"}; out=[]
 for rel in raw:
  p=Path(rel); parts=rel.lower().split("/")
  if p.suffix.lower() not in ok or any(x in parts for x in ("test","tests","__pycache__")) or p.name.startswith("test_") or p.name.endswith("_test.py"): continue
  out.append(rel)
 return out
def file_tuple(repo,rel,commit):
 b=subprocess.check_output(["git","-C",str(repo),"show",f"{commit}:{rel}"]); t=b.decode("utf-8","replace")
 return t,b,git(repo,"rev-parse",f"{commit}:{rel}")
def match_context(item,files,commit):
 source=item["source"]; back=chr(96)
 variants=list(dict.fromkeys([json.dumps(source,ensure_ascii=False),repr(source),'"'+source+'"',"'"+source+"'",back+source+back]))
 callers=[]
 for rel,(text,data,blob) in files.items():
  hits={}
  for literal in variants:
   at=0
   while True:
    pos=text.find(literal,at)
    if pos<0: break
    hits.setdefault(pos,"exact quoted source literal");at=pos+max(1,len(literal))
  at=0
  while True:
   pos=text.find(item["sourceId"],at)
   if pos<0: break
   hits.setdefault(pos,"exact source ID reference");at=pos+len(item["sourceId"])
  for m in re.finditer(r">[ \t]*"+re.escape(source)+r"[ \t]*<",text): hits.setdefault(m.start(),"exact HTML text node")
  lines=text.splitlines()
  for pos,kind in sorted(hits.items()):
   line=text.count("\n",0,pos)+1
   excerpt=[{"line":n,"text":lines[n-1]} for n in range(max(1,line-3),min(len(lines),line+3)+1)]
   lt=lines[line-1] if line<=len(lines) else ""
   callers.append({"path":rel,"line":line,"lineText":lt,"lineSha256":sha(lt),"excerpt":excerpt,"excerptSha256":sha(canon(excerpt)),"fileSha256":sha(data),"gitBlob":blob,"matchKind":kind})
 callers.sort(key=lambda x:(x["path"],x["line"],x["matchKind"]))
 core={"sourceId":item["sourceId"],"source":source,"sourceSha256":item["sourceSha256"],"head":commit,
 "searchMethod":"exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code under romarr; tests, docs, catalogs, and workflows excluded",
 "productionFilesSearched":len(files),"exactMatchCount":len(callers),"callerless":not callers,"callers":callers}
 return {**core,"contextSha256":sha(canon(core))}
def safe_context(c):
 z={k:c[k] for k in ("sourceId","sourceSha256","head","searchMethod","productionFilesSearched","exactMatchCount","callerless","contextSha256")}
 if c["callerless"]: z.update({"sourceTextOmitted":True,"callers":[]})
 else: z.update({"source":c["source"],"callers":c["callers"]})
 return z
def write_sums(root):
 root=Path(root); target=root/"SHA256SUMS.txt"
 files=sorted(p for p in root.rglob("*") if p.is_file() and p!=target)
 target.write_text("".join(f"{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}\n" for p in files),encoding="utf-8")

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo",type=Path,required=True);repo=ap.parse_args().repo.resolve()
 out=Path(__file__).resolve().parent; inp=out/"input"
 permitted_existing={"w665-current-context-reattestation.jsonl","w665-current-context-reattestation-summary.json"}
 if inp.exists() and ({p.name for p in inp.iterdir()}-permitted_existing): raise SystemExit("FAIL input directory contains unexpected files")
 if any(p.is_file() for p in out.iterdir() if p.name not in ("build_candidate_free.py","verify_candidate_free.py")): raise SystemExit("FAIL output directory not empty")
 api0=attestation(repo)
 # Verify predecessor packets and sealed previous review/application artifacts.
 for d in (PREV_PACKET,PREV_INPUT,PREV_PRIMARY,PREV_PRIMARY/"primary-output",PREV_BLIND,PREV_CROSS,PREV_CROSS/"independent-review",PREV_ROOT_REVIEW):
  verify_sums(d)
 app_task_index,app_task_unlisted=verify_listed_sums(PREV_APP)
 app_task_unlisted_hashes=[{"path":p,"sha256":sha((PREV_APP/p).read_bytes())} for p in app_task_unlisted]
 prev_manifest=rj(PREV_INPUT/"manifest.json")
 if (prev_manifest.get("head"),prev_manifest.get("tree"),prev_manifest.get("window"))!=(PREV_HEAD,PREV_TREE,PREV_WINDOW): raise SystemExit("FAIL prior packet pin")
 if (prev_manifest.get("priorSelectedSourceCount"),prev_manifest.get("priorHoldCellCount"),prev_manifest.get("priorAppliedSelectedCellCount"))!=(260,724,76): raise SystemExit("FAIL prior lineage counts")
 app_dir=repo/PREV_APP_REL
 verify_sums(app_dir)
 plan=rj(app_dir/"root-application-plan.json"); appread=rj(app_dir/"readback.json"); product=rj(app_dir/"product-commit-record.json")
 root_summary=rj(PREV_ROOT_REVIEW/"summary.json"); primary_summary=rj(PREV_PRIMARY/"primary-output"/"summary.json")
 blind_summary=rj(PREV_BLIND/"SUMMARY.json"); cross_summary=rj(PREV_CROSS/"cross-review-summary.json")
 if plan.get("sourcePin")!={"head":PREV_HEAD,"tree":PREV_TREE} or (plan.get("window"),plan.get("candidateCells"),len(plan.get("changes",[])))!=(PREV_WINDOW,240,15): raise SystemExit("FAIL previous application plan")
 if (product.get("productCommit"),product.get("productTree"),product.get("parent"))!=(PREV_PRODUCT,PREV_PRODUCT_TREE,PREV_HEAD): raise SystemExit("FAIL previous product commit record")
 if (appread.get("result"),appread.get("sourcePin"),appread.get("readbackCellCount"),appread.get("appliedTargetCells"))!=("PASS",{"head":PREV_HEAD,"tree":PREV_TREE},240,15): raise SystemExit("FAIL previous application readback")
 if git(repo,"rev-parse",f"{PREV_PRODUCT}^")!=PREV_HEAD or git(repo,"rev-parse",f"{PREV_PRODUCT}^{{tree}}")!=PREV_PRODUCT_TREE: raise SystemExit("FAIL prior product ancestry/tree")
 if subprocess.run(["git","-C",str(repo),"merge-base","--is-ancestor",PREV_PRODUCT,HEAD],check=False).returncode: raise SystemExit("FAIL prior product not in current history")
 if root_summary.get("applicationPerformed") is not False or root_summary.get("rootChangeCellCount")!=15: raise SystemExit("FAIL previous adjudication/application boundary")
 if cross_summary.get("result")!="PASS_WITH_BLIND_SUMMARY_PIN_WARNING" or (primary_summary.get("cellCount",primary_summary.get("cells")),blind_summary.get("cellCount"),cross_summary.get("cells"))!=(240,240,240): raise SystemExit("FAIL prior review packet coverage/status")
 prev_sel=rjl(PREV_INPUT/"prior-selection-reattestation.jsonl"); prev_window_sel=rjl(PREV_INPUT/"source-inventory-selection.jsonl")
 prev_holds=rjl(PREV_INPUT/"prior-hold-reattestation.jsonl"); prev_applied=rjl(PREV_INPUT/"prior-applied-cell-reattestation.jsonl")
 prev_baseline_rows=rjl(PREV_INPUT/"current-target-cells.jsonl"); prev_baseline={(r["sourceId"],r["locale"]):r for r in prev_baseline_rows}
 prev_contexts={r["sourceId"]:r for r in rjl(PREV_INPUT/"source-contexts.jsonl")}
 app_rows=appread["readback"]
 if (len(prev_sel),len(prev_window_sel),len(prev_holds),len(prev_applied),len(prev_baseline_rows),len(app_rows))!=(260,20,724,76,240,240): raise SystemExit("FAIL previous row counts")

 w625_cont=rj(PREV_INPUT/"continuity-reattestation.json")
 w625_raw=(PREV_W625_ROOT/"final-head-readback.jsonl").read_bytes(); w625_final=rj(PREV_W625_ROOT/"final-head-verification.json")
 w625_hash=sha(w625_raw)
 if w625_hash != w625_cont.get("priorW625ReadbackSha256") or w625_final.get("readbackSha256") != w625_hash: raise SystemExit("FAIL W625 full readback hash chain")
 if (w625_cont.get("priorApplicationEvidenceIndexMissingFromPRTreeCount"),w625_cont.get("priorW625FullReadbackSha256MatchedCommittedFinalVerifier"))!=(31,True): raise SystemExit("FAIL W625 evidence limitation absent")

 catalog_path="romarr/ui-labels.json"; registry_path="romarr/ui-source-messages.json"; snapshot_path="romarr/ui-source-snapshot.json"
 catalog_raw=(repo/catalog_path).read_bytes(); catalog=json.loads(catalog_raw); msgs=catalog["messages"]; ids=list(msgs)
 if len(msgs)!=1836: raise SystemExit("FAIL catalog key count")
 registry_raw=(repo/registry_path).read_bytes(); registry_doc=rj(repo/registry_path); registry_rows=registry_doc["messages"]
 registry={r["id"]:r for r in registry_rows}
 if len(registry)!=len(registry_rows): raise SystemExit("FAIL duplicate active registry IDs")
 active_rank={sid:i for i,sid in enumerate(sorted(registry),1)}; snapshot=rj(repo/snapshot_path)
 if any(snapshot.get(r["id"])!=r["sourceHash"] for r in registry_rows): raise SystemExit("FAIL registry/snapshot")
 id_order_sha=sha("\n".join(sorted(registry))+"\n"); cat_order_sha=sha("\n".join(ids)+"\n")
 source_snapshot_sha=sha(canon(snapshot)); source_queue_sha=sha(registry_raw)

 # All prior selected source identities, indices and English-source hashes are checked at the new head.
 selection_rows=[]
 for row in prev_sel:
  sid,idx=row["sourceId"],row["catalogZeroBasedIndex"]; msg=msgs.get(sid)
  if msg is None or idx<0 or idx>=len(ids) or ids[idx]!=sid: raise SystemExit(f"FAIL prior source position {sid}")
  sh=sha(msg["source"])
  if sh!=row["priorSourceSha256"] or msg.get("sourceHash")!=sh or registry.get(sid,{}).get("sourceHash") not in (None,sh): raise SystemExit(f"FAIL prior source hash {sid}")
  selection_rows.append({"priorWindow":row["priorWindow"],"position":row.get("position",idx),"catalogZeroBasedIndex":idx,"sourceId":sid,"priorSourceSha256":row["priorSourceSha256"],"currentSourceSha256":sh,"selectionPositionMatches":True,"sourceHashMatches":True,"registryMembershipAndHashMatch":sid in registry,"priorSelectionEvidenceSha256":row.get("priorSelectionEvidenceSha256",sha(canon(row))),"reattestedAtHead":HEAD})
 for row in prev_window_sel:
  sid,idx=row["sourceId"],row["catalogZeroBasedIndex"]; msg=msgs.get(sid)
  if msg is None or idx not in range(645,665) or ids[idx]!=sid or sha(msg["source"])!=row["sourceSha256"] or msg.get("sourceHash")!=row["sourceSha256"]: raise SystemExit(f"FAIL W645 source selection {sid}")
  selection_rows.append({"priorWindow":PREV_WINDOW,"position":idx,"catalogZeroBasedIndex":idx,"sourceId":sid,"priorSourceSha256":row["sourceSha256"],"currentSourceSha256":row["sourceSha256"],"selectionPositionMatches":True,"sourceHashMatches":True,"registryMembershipAndHashMatch":sid in registry,"priorSelectionEvidenceSha256":sha(canon(row)),"reattestedAtHead":HEAD})
 if len(selection_rows)!=280 or len({r["sourceId"] for r in selection_rows})!=280: raise SystemExit("FAIL prior selection count/unique")

 # Reattest past holds by hashes only; no held target text is read into the output.
 hold_rows=[]
 for row in prev_holds:
  sid,loc=row["sourceId"],row["locale"]; idx=ids.index(sid); basis=row.get("selectionPositionBasis","")
  posok=idx==row["position"] if "catalog insertion index" in basis else active_rank.get(sid)==row["position"]
  msg=msgs[sid]; sh=sha(msg["source"]); th=sha(msg["translations"][loc])
  if sh!=row["sourceSha256"] or th!=row["priorTargetSha256"] or not posok: raise SystemExit(f"FAIL prior hold changed {sid}/{loc}")
  if any(k in row for k in ("source","sourceText","currentTarget","target","targetText")): raise SystemExit("FAIL prior hold input contains text")
  hold_rows.append({"window":row["window"],"position":row["position"],"selectionPositionBasis":basis,"catalogZeroBasedIndex":idx,"sourceId":sid,"sourceSha256":sh,"locale":loc,"priorTargetSha256":row["priorTargetSha256"],"currentTargetSha256":th,"selectionPositionMatches":True,"targetUnchanged":True,"priorHoldEvidenceSha256":row.get("priorHoldEvidenceSha256",sha(canon(row))),"textOmitted":True,"reattestedAtHead":HEAD})

 prod_paths=production_paths(repo,HEAD); prod_files={p:file_tuple(repo,p,HEAD) for p in prod_paths}
 # Re-search caller status for every previously held source ID, retaining hashes and counts only.
 prior_hold_contexts=[]
 for sid in sorted({r["sourceId"] for r in prev_holds}):
  msg=msgs[sid]; ctx=match_context({"sourceId":sid,"source":msg["source"],"sourceSha256":sha(msg["source"])},prod_files,HEAD)
  prior_hold_contexts.append({"sourceId":sid,"sourceSha256":sha(msg["source"]),"callerlessAtCurrentHead":ctx["callerless"],"exactMatchCount":ctx["exactMatchCount"],"callerContextSha256":ctx["contextSha256"],"heldCellCount":sum(r["sourceId"]==sid for r in prev_holds),"sourceTextOmitted":True,"callerTextOmitted":True})
 hold_sources_with_callers=sum(not r["callerlessAtCurrentHead"] for r in prior_hold_contexts)

 # Previous W645 source/caller contexts must have unchanged exact caller signatures on current production files.
 w645_ctx_rows=[]; w645_ctx_by_id={}
 for row in prev_window_sel:
  sid=row["sourceId"]; msg=msgs[sid]; old=prev_contexts[sid]
  if sha(msg["source"])!=row["sourceSha256"] or sha(old["source"])!=row["sourceSha256"]: raise SystemExit(f"FAIL W645 context source {sid}")
  new=match_context({"sourceId":sid,"source":msg["source"],"sourceSha256":row["sourceSha256"]},prod_files,HEAD)
  sig=lambda c:[(x["path"],x["line"],x["lineSha256"],x["excerptSha256"],x["fileSha256"],x["gitBlob"],x["matchKind"]) for x in c["callers"]]
  if old["callerless"]!=new["callerless"] or old["exactMatchCount"]!=new["exactMatchCount"] or sig(old)!=sig(new): raise SystemExit(f"FAIL W645 caller context changed {sid}")
  w645_ctx_by_id[sid]=new
  w645_ctx_rows.append({"sourceId":sid,"sourceSha256":row["sourceSha256"],"priorCallerContextSha256":old["contextSha256"],"currentCallerContextSha256":new["contextSha256"],"callerless":new["callerless"],"exactMatchCount":new["exactMatchCount"],"callerSignaturesUnchanged":True,"sourceTextOmitted":True,"callerTextOmitted":new["callerless"]})

 # W645 application readback is hash-only; compare every postimage hash to the exact current catalog.
 baseline=prev_baseline; app_by_key={}
 for row in app_rows:
  key=(row["sourceId"],row["locale"])
  if key in app_by_key: raise SystemExit("FAIL duplicate W645 application cell")
  app_by_key[key]=row
 if len(app_by_key)!=240: raise SystemExit("FAIL W645 application coverage")
 change_keys={(r["sourceId"],r["locale"]) for r in plan["changes"]}
 w645_holds=set()
 for row in app_rows:
  sid,loc,idx=row["sourceId"],row["locale"],row["position"]; key=(sid,loc); msg=msgs[sid]
  if idx not in range(645,665) or ids[idx]!=sid or sha(msg["source"])!=baseline[key]["sourceSha256"]: raise SystemExit(f"FAIL W645 readback position/source {sid}/{loc}")
  th=sha(msg["translations"][loc])
  if row["expectedTargetSha256"]!=row["actualTargetSha256"] or row["actualTargetSha256"]!=th: raise SystemExit(f"FAIL W645 postimage target {sid}/{loc}")
  held=row["rootDisposition"]=="text-free-hold"; ctx=w645_ctx_by_id[sid]
  if held:
   if not ctx["callerless"]: raise SystemExit(f"FAIL W645 hash-only hold has caller {sid}/{loc}")
   w645_holds.add(key)
  before=baseline[key]["currentTargetSha256"]
  if key in change_keys:
   change=next(x for x in plan["changes"] if (x["sourceId"],x["locale"])==key)
   if change["currentTargetSha256"]!=before or change["finalTargetSha256"]!=th: raise SystemExit(f"FAIL W645 applied hash lineage {sid}/{loc}")
  elif th!=before: raise SystemExit(f"FAIL unplanned W645 target change {sid}/{loc}")
  if any(k in row for k in ("source","sourceText","currentTarget","target","targetText","proposedTarget","finalTarget")): raise SystemExit("FAIL W645 readback text leak")
 if len(w645_holds)!=96 or len(change_keys)!=15: raise SystemExit("FAIL W645 applied/hold counts")
 for row in plan["changes"]:
  sid,loc,idx=row["sourceId"],row["locale"],row["position"]; msg=msgs[sid]
  if (sid,loc) not in app_by_key or idx not in range(645,665) or ids[idx]!=sid or row["sourceSha256"]!=sha(msg["source"]) or row["finalTargetSha256"]!=sha(msg["translations"][loc]): raise SystemExit(f"FAIL W645 change current hash {sid}/{loc}")
 hold_rows.extend({"window":PREV_WINDOW,"catalogZeroBasedIndex":app_by_key[sid,loc]["position"],"sourceId":sid,"sourceSha256":sha(msgs[sid]["source"]),"locale":loc,"priorTargetSha256":app_by_key[sid,loc]["actualTargetSha256"],"currentTargetSha256":sha(msgs[sid]["translations"][loc]),"callerless":True,"callerContextSha256":w645_ctx_by_id[sid]["contextSha256"],"targetUnchanged":True,"textOmitted":True,"reattestedAtHead":HEAD} for sid,loc in sorted(w645_holds,key=lambda k:(ids.index(k[0]),LOCALES.index(k[1]))))
 if len(hold_rows)!=820 or len({(r["sourceId"],r["locale"]) for r in hold_rows})!=820: raise SystemExit("FAIL total prior holds")

 # Reattest earlier applied cells and W645's 15 applied targets by final hashes.
 applied_rows=[]
 for row in prev_applied:
  sid,loc=row["sourceId"],row["locale"]; msg=msgs[sid]; sh=sha(msg["source"]); th=sha(msg["translations"][loc])
  if sh!=row["sourceSha256"] or th!=row["priorSelectedTargetSha256"] or th!=row["currentTargetSha256"]: raise SystemExit(f"FAIL prior applied cell {sid}/{loc}")
  applied_rows.append({"priorWindow":row["priorWindow"],"catalogZeroBasedIndex":ids.index(sid),"sourceId":sid,"sourceSha256":sh,"locale":loc,"priorSelectedTargetSha256":th,"currentTargetSha256":th,"targetUnchanged":True,"applicationCommit":row["applicationCommit"],"priorAppliedEvidenceSha256":row.get("priorAppliedEvidenceSha256",sha(canon(row))),"textOmitted":True,"reattestedAtHead":HEAD})
 for row in plan["changes"]:
  sid,loc,idx=row["sourceId"],row["locale"],row["position"]; msg=msgs[sid]; key=(sid,loc); th=sha(msg["translations"][loc])
  before=baseline[key]["currentTargetSha256"]
  if row["currentTargetSha256"]!=before or row["finalTargetSha256"]!=th or row["sourceSha256"]!=sha(msg["source"]): raise SystemExit(f"FAIL W645 applied target {sid}/{loc}")
  applied_rows.append({"priorWindow":PREV_WINDOW,"catalogZeroBasedIndex":idx,"sourceId":sid,"sourceSha256":sha(msg["source"]),"locale":loc,"beforeTargetSha256":before,"priorSelectedTargetSha256":th,"currentTargetSha256":th,"targetUnchanged":True,"applicationCommit":PREV_PRODUCT,"priorAppliedEvidenceSha256":sha(canon(row)),"textOmitted":True,"reattestedAtHead":HEAD})
 if len(applied_rows)!=91 or len({(r["sourceId"],r["locale"]) for r in applied_rows})!=91: raise SystemExit("FAIL total prior applied cells")

 def reattest_readback(rows,label):
  if len(rows)!=240: raise SystemExit(f"FAIL {label} full readback count")
  out=[]
  for row in rows:
   sid,loc=row["sourceId"],row["locale"]; idx=row.get("position",row.get("catalogZeroBasedIndex")); msg=msgs[sid]
   sh=sha(msg["source"]); th=sha(msg["translations"][loc])
   recorded=next((row[k] for k in ("currentTargetSha256","actualTargetSha256","afterTargetSha256","observedAfterSha256") if k in row),None)
   if row.get("sourceSha256") not in (None,sh) or recorded!=th: raise SystemExit(f"FAIL {label} readback hash {sid}/{loc}")
   if idx is not None and (idx<0 or idx>=len(ids) or ids[idx]!=sid): raise SystemExit(f"FAIL {label} readback position {sid}/{loc}")
   item={"priorWindow":label,"catalogZeroBasedIndex":ids.index(sid),"sourceId":sid,"sourceSha256":sh,"locale":loc,"priorTargetSha256":recorded,"currentTargetSha256":th,"matchesPriorReadback":True,"targetUnchanged":True,"textOmitted":True,"reattestedAtHead":HEAD}
   if "rootDisposition" in row: item["rootDisposition"]=row["rootDisposition"];item["callerlessHeld"]=row["rootDisposition"]=="text-free-hold"
   out.append(item)
  if len({(r["sourceId"],r["locale"]) for r in out})!=240: raise SystemExit(f"FAIL {label} duplicate cells")
  return out
 readback_paths=[("W565-W584",PREV_INPUT/"w565w584-cell-hash-reattestation.jsonl"),("W585-W604",PREV_INPUT/"w585w604-cell-hash-reattestation.jsonl"),("W605-W624",PREV_INPUT/"w605w624-cell-hash-reattestation.jsonl"),("W625-W644",PREV_INPUT/"w625-application-cell-hash-reattestation.jsonl")]
 readbacks={label:reattest_readback(rjl(p),label) for label,p in readback_paths}
 readbacks[PREV_WINDOW]=reattest_readback(app_rows,PREV_WINDOW)
 
 # Reattest W665-W684, the immediately preceding window, from its sealed packet and exact PR evidence.
 W665_TASK=Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w665-684-20261105")
 W665_INPUT=W665_TASK/"candidate-free"/"input"
 W665_EVID=repo/"docs/pr-evidence/pr70-localization-2026-11-05/window-665-684"
 for d in (W665_TASK/"candidate-free",W665_INPUT,W665_TASK/"primary-review",W665_TASK/"blind-review",W665_TASK/"cross-review"):
  verify_sums(d)
 # The previous PR-tree evidence root index is preserved, but its bundle omits 24 listed payloads.
 # Verify every extant file against that index and fail on any hash mismatch; record missing entries.
 w665_index={};w665_missing=[];w665_mismatch=[]
 for line in (W665_EVID/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
  if not line.strip():continue
  digest,name=line.split("  ",1)
  if name in w665_index: raise SystemExit("FAIL duplicate W665 evidence checksum entry")
  w665_index[name]=digest;path=(W665_EVID/name).resolve()
  if not path.is_relative_to(W665_EVID.resolve()): raise SystemExit("FAIL W665 evidence checksum path escapes bundle")
  if not path.is_file():w665_missing.append(name);continue
  if sha(path.read_bytes())!=digest:w665_mismatch.append(name)
 if w665_mismatch: raise SystemExit("FAIL W665 evidence checksum mismatch: "+repr(w665_mismatch))
 required_w665_evidence=("application/root-application-plan.json","application/readback.json","application/delivery.json","root-adjudication/summary.json")
 if any(name not in w665_index or name in w665_missing for name in required_w665_evidence): raise SystemExit("FAIL required W665 application evidence absent from PR tree")
 w665_manifest=rj(W665_INPUT/"manifest.json")
 w665_sources=rjl(W665_INPUT/"selected-sources.jsonl")
 w665_cells=rjl(W665_INPUT/"candidate-free-cells.jsonl")
 w665_contexts={r["sourceId"]:r for r in rjl(W665_INPUT/"source-contexts.jsonl")}
 w665_plan=rj(W665_EVID/"application"/"root-application-plan.json")
 w665_readback=rj(W665_EVID/"application"/"readback.json")
 w665_delivery=rj(W665_EVID/"application"/"delivery.json")
 w665_root_summary=rj(W665_EVID/"root-adjudication"/"summary.json")
 w665_primary_summary=rj(W665_TASK/"primary-review"/"summary.json")
 w665_blind_summary=rj(W665_TASK/"blind-review"/"summary.json")
 w665_cross_summary=rj(W665_TASK/"cross-review"/"summary.json")
 W665_HEAD="8b7589775c526866e474112b4f4168782b02f881";W665_TREE="fb0ba93172f6832c687e001ce6c0fff08b5a33eb"
 W665_PRODUCT="38718aa6c60e3366aa67ba5372531b77d6539862";W665_PRODUCT_TREE="d0d3ec426190114e9efb2378f5a9dd44ac81e91f"
 if (w665_manifest.get("head"),w665_manifest.get("tree"),w665_manifest.get("window"),w665_manifest.get("cellCount"))!=(W665_HEAD,W665_TREE,"W665-W684",240): raise SystemExit("FAIL W665 candidate-free pin")
 if (w665_manifest.get("priorSelectedSourceCount"),w665_manifest.get("priorHoldCellCount"),w665_manifest.get("priorAppliedSelectedCellCount"))!=(280,820,91): raise SystemExit("FAIL W665 lineage counts")
 if w665_plan.get("sourcePin")!={"head":W665_HEAD,"tree":W665_TREE} or (w665_plan.get("window"),w665_plan.get("candidateCells"),len(w665_plan.get("changes",[])),len(w665_plan.get("translationHashUpdates",[])))!=("W665-W684",240,29,9): raise SystemExit("FAIL W665 plan pin/counts")
 if (w665_readback.get("result"),w665_readback.get("sourcePin"),w665_readback.get("readbackCellCount"),w665_readback.get("appliedTargetCells"),w665_readback.get("updatedTranslationHashCells"))!=("PASS",{"head":W665_HEAD,"tree":W665_TREE},240,29,9): raise SystemExit("FAIL W665 readback status")
 if (w665_root_summary.get("cellCount"),w665_root_summary.get("appliedTargets"),w665_root_summary.get("translationHashUpdates"),w665_root_summary.get("dispositionCounts",{}).get("hold-hash-only"))!=(240,29,9,72): raise SystemExit("FAIL W665 root summary")
 if (w665_primary_summary.get("cellCount"),w665_blind_summary.get("cellCount"),w665_cross_summary.get("cellCount"))!=(240,240,240): raise SystemExit("FAIL W665 review coverage")
 if (w665_delivery.get("productCommit"),w665_delivery.get("productTree"),w665_delivery.get("evidenceCommit"))!=(W665_PRODUCT,W665_PRODUCT_TREE,"68d4f0c9a69d956ff237b5bee6978619bff59e40"): raise SystemExit("FAIL W665 delivery record")
 if git(repo,"rev-parse",f"{W665_PRODUCT}^")!=W665_HEAD or git(repo,"rev-parse",f"{W665_PRODUCT}^{{tree}}")!=W665_PRODUCT_TREE: raise SystemExit("FAIL W665 product ancestry/tree")
 if subprocess.run(["git","-C",str(repo),"merge-base","--is-ancestor",W665_PRODUCT,HEAD],check=False).returncode: raise SystemExit("FAIL W665 product absent from current history")
 if subprocess.run(["git","-C",str(repo),"diff","--quiet",W665_PRODUCT,HEAD,"--",catalog_path],check=False).returncode: raise SystemExit("FAIL catalog changed after W665 product commit")
 if sha(catalog_raw)!=w665_readback.get("catalogPostimageSha256"): raise SystemExit("FAIL W665 catalog postimage no longer matches current head")
 if len(w665_sources)!=20 or len(w665_cells)!=240 or len(w665_contexts)!=20: raise SystemExit("FAIL W665 source/context/cell counts")
 w665_by_key={(r["sourceId"],r["locale"]):r for r in w665_readback["readback"]}
 if len(w665_by_key)!=240: raise SystemExit("FAIL W665 duplicate readback cell")
 w665_sources_seen=set()
 w665_context_rows=[];w665_ctx_by_id={}
 sig=lambda c:[(x["path"],x["line"],x["lineSha256"],x["excerptSha256"],x["fileSha256"],x["gitBlob"],x["matchKind"]) for x in c["callers"]]
 for row in w665_sources:
  sid,idx=row["sourceId"],row["catalogZeroBasedIndex"];msg=msgs.get(sid)
  if msg is None or idx not in range(665,685) or ids[idx]!=sid or sha(msg["source"])!=row["sourceSha256"]: raise SystemExit(f"FAIL W665 selected source changed {sid}")
  if sid in w665_sources_seen or sid in {r["sourceId"] for r in selection_rows}: raise SystemExit(f"FAIL W665 source selection duplicate {sid}")
  w665_sources_seen.add(sid)
  selection_rows.append({"priorWindow":"W665-W684","position":idx,"catalogZeroBasedIndex":idx,"sourceId":sid,"priorSourceSha256":row["sourceSha256"],"currentSourceSha256":row["sourceSha256"],"selectionPositionMatches":True,"sourceHashMatches":True,"registryMembershipAndHashMatch":sid in registry,"priorSelectionEvidenceSha256":sha(canon(row)),"reattestedAtHead":HEAD})
  old=w665_contexts[sid];new=match_context({"sourceId":sid,"source":msg["source"],"sourceSha256":row["sourceSha256"]},prod_files,HEAD)
  if old["callerless"]!=new["callerless"] or old["exactMatchCount"]!=new["exactMatchCount"] or sig(old)!=sig(new): raise SystemExit(f"FAIL W665 caller context changed {sid}")
  w665_ctx_by_id[sid]=new
  w665_context_rows.append({"sourceId":sid,"sourceSha256":row["sourceSha256"],"priorCallerContextSha256":old["contextSha256"],"currentCallerContextSha256":new["contextSha256"],"callerless":new["callerless"],"exactMatchCount":new["exactMatchCount"],"callerSignaturesUnchanged":True,"sourceTextOmitted":True,"callerTextOmitted":new["callerless"]})
 if len(selection_rows)!=300 or len({r["sourceId"] for r in selection_rows})!=300: raise SystemExit("FAIL total prior selected sources including W665")
 w665_hold_keys=set()
 for row in w665_cells:
  sid,loc,idx=row["sourceId"],row["locale"],row["position"]
  if idx not in range(665,685) or ids[idx]!=sid: raise SystemExit(f"FAIL W665 cell position {sid}/{loc}")
  read=w665_by_key.get((sid,loc));msg=msgs[sid];actual=sha(msg["translations"][loc])
  if read is None or read.get("actualTargetSha256")!=actual or read.get("expectedTargetSha256")!=actual: raise SystemExit(f"FAIL W665 current target/readback {sid}/{loc}")
  if row["callerless"]:
   if row.get("source") is not None or row.get("currentTarget") is not None or read.get("rootDisposition")!="text-free-hold": raise SystemExit("FAIL W665 callerless hold text/status")
   w665_hold_keys.add((sid,loc))
   hold_rows.append({"window":"W665-W684","catalogZeroBasedIndex":idx,"sourceId":sid,"sourceSha256":row["sourceSha256"],"locale":loc,"priorTargetSha256":row["currentTargetSha256"],"currentTargetSha256":actual,"callerless":True,"callerContextSha256":row["callerContextSha256"],"targetUnchanged":True,"textOmitted":True,"reattestedAtHead":HEAD})
  elif not isinstance(row.get("source"),str) or not isinstance(row.get("currentTarget"),str): raise SystemExit("FAIL W665 caller-backed source/target absent")
 if len(w665_hold_keys)!=72 or len(hold_rows)!=892 or len({(r["sourceId"],r["locale"]) for r in hold_rows})!=892: raise SystemExit("FAIL total prior holds including W665")
 w665_changes={(r["sourceId"],r["locale"]):r for r in w665_plan["changes"]}
 for (sid,loc),change in w665_changes.items():
  msg=msgs[sid];idx=ids.index(sid);th=sha(msg["translations"][loc])
  if idx!=change["position"] or idx not in range(665,685) or sha(msg["source"])!=change["sourceSha256"] or th!=change["finalTargetSha256"]: raise SystemExit(f"FAIL W665 applied target {sid}/{loc}")
  if change["currentTargetSha256"]==th: raise SystemExit(f"FAIL W665 change is an unexpected no-op {sid}/{loc}")
  applied_rows.append({"priorWindow":"W665-W684","catalogZeroBasedIndex":idx,"sourceId":sid,"sourceSha256":sha(msg["source"]),"locale":loc,"beforeTargetSha256":change["currentTargetSha256"],"priorSelectedTargetSha256":th,"currentTargetSha256":th,"targetUnchanged":True,"applicationCommit":W665_PRODUCT,"priorAppliedEvidenceSha256":sha(canon(change)),"textOmitted":True,"reattestedAtHead":HEAD})
 for update in w665_plan["translationHashUpdates"]:
  msg=msgs[update["sourceId"]];loc=update["locale"]
  if msg.get("translationHashes",{}).get(loc)!=update["newHash"] or update["newHash"]!=sha(canon(msg["translations"][loc])): raise SystemExit(f"FAIL W665 translation content hash {update['sourceId']}/{loc}")
 if len(applied_rows)!=120 or len({(r["sourceId"],r["locale"]) for r in applied_rows})!=120: raise SystemExit("FAIL total prior applied cells including W665")
 readbacks["W665-W684"]=reattest_readback(w665_readback["readback"],"W665-W684")
 wjl(inp/"w665-current-context-reattestation.jsonl",w665_context_rows)
 wj(inp/"w665-current-context-reattestation-summary.json",{"head":HEAD,"priorHead":W665_HEAD,"priorTree":W665_TREE,"sourceCount":20,"allCallerSignaturesUnchanged":True})
 if set(readbacks)!=set(("W565-W584","W585-W604","W605-W624","W625-W644","W645-W664","W665-W684")): raise SystemExit("FAIL prior full-window readback lineage")

 # Prior hold context output contains hashes/counts only; verify current statuses without emitting any source/caller text.
 prior_hold_context_records=[]
 for sid in sorted({r["sourceId"] for r in hold_rows}):
  msg=msgs[sid];ctx=match_context({"sourceId":sid,"source":msg["source"],"sourceSha256":sha(msg["source"])},prod_files,HEAD)
  prior_hold_context_records.append({"sourceId":sid,"sourceSha256":sha(msg["source"]),"callerlessAtCurrentHead":ctx["callerless"],"exactMatchCount":ctx["exactMatchCount"],"callerContextSha256":ctx["contextSha256"],"heldCellCount":sum(r["sourceId"]==sid for r in hold_rows),"sourceTextOmitted":True,"callerTextOmitted":True})

 # Pin all tracked production code and source/catalog inputs.
 pin_rows=[]
 for rel in sorted(set(prod_paths)|{catalog_path,registry_path,snapshot_path}):
  raw=(repo/rel).read_bytes();pin_rows.append({"path":rel,"fileSha256":sha(raw),"gitBlob":git(repo,"rev-parse",f"{HEAD}:{rel}"),"bytes":len(raw)})
 old_pins={r["path"]:r for r in rj(PREV_INPUT/"source-file-pins.json")["files"]}
 for row in pin_rows:
  if row["path"] in old_pins and row["path"]!=catalog_path and (row["fileSha256"],row["gitBlob"])!=(old_pins[row["path"]]["fileSha256"],old_pins[row["path"]]["gitBlob"]): raise SystemExit(f"FAIL production source/caller drift since W645: {row['path']}")
 if any(p!="romarr/ui-labels.json" and p not in {r["path"] for r in pin_rows} for p in old_pins): raise SystemExit("FAIL prior production source file disappeared")

 selected=[]
 for idx in range(685,705):
  sid=ids[idx];msg=msgs[sid];sh=sha(msg["source"])
  if msg.get("sourceHash")!=sh: raise SystemExit(f"FAIL current source hash at {idx}")
  selected.append({"position":idx,"catalogZeroBasedIndex":idx,"catalogOneBasedPosition":idx+1,"sourceId":sid,"sourceSha256":sh,"activeSourceRegistry":sid in registry,"activeSourceRank":active_rank.get(sid),"registryLocations":registry.get(sid,{}).get("locations",[]),"_source":msg["source"]})
 if len({r["sourceId"] for r in selected})!=20 or {r["sourceId"] for r in selected}&{r["sourceId"] for r in selection_rows}: raise SystemExit("FAIL W685 selection overlap")
 contexts=[match_context({"sourceId":r["sourceId"],"source":r["_source"],"sourceSha256":r["sourceSha256"]},prod_files,HEAD) for r in selected];ctxmap={r["sourceId"]:r for r in contexts}
 selected_public=[]
 for r in selected:
  item={k:v for k,v in r.items() if k!="_source"}
  if ctxmap[r["sourceId"]]["callerless"]: item["sourceTextOmitted"]=True
  else: item["source"]=r["_source"]
  selected_public.append(item)
 boundary=[]
 for idx,role in ((684,"catalog-before-selected-start"),(685,"selected-start"),(704,"selected-end"),(705,"catalog-after-selected-end")):
  sid=ids[idx];boundary.append({"position":idx,"catalogZeroBasedIndex":idx,"sourceId":sid,"sourceSha256":sha(msgs[sid]["source"]),"role":role,"sourceTextOmitted":True})

 cells=[]; mismatch=collections.Counter()
 for item in selected:
  sid=item["sourceId"];msg=msgs[sid];src=msg["source"];st=tokens(src);ctx=ctxmap[sid]
  for loc in LOCALES:
   target=msg.get("translations",{}).get(loc)
   if not isinstance(target,str) or not target: mismatch["missingTarget"]+=1;target=""
   tt=tokens(target);ph=collections.Counter(st["placeholders"])==collections.Counter(tt["placeholders"])
   mk=collections.Counter(st["markup"])==collections.Counter(tt["markup"])
   sn,tn=collections.Counter(st["numbers"]),collections.Counter(tt["numbers"]);extra=list((tn-sn).elements())
   pres=bool(re.search(r"\bzero\b",src,re.I) and not st["numbers"] and extra==["0"])
   num=not (sn-tn) and (not extra or pres);missing=[x for x in st["protectedLiterals"] if x not in target]
   mismatch["placeholder"]+=not ph;mismatch["markup"]+=not mk;mismatch["numeric"]+=not num
   mismatch["numericPresentationDifferences"]+=pres;mismatch["protectedLiteral"]+=bool(missing)
   cell={"window":WINDOW,"position":item["position"],"catalogZeroBasedIndex":item["catalogZeroBasedIndex"],"catalogOneBasedPosition":item["catalogOneBasedPosition"],"sourceId":sid,"sourceSha256":item["sourceSha256"],"locale":loc,"callerContextSha256":ctx["contextSha256"],"literalCallerCount":ctx["exactMatchCount"],"callerless":ctx["callerless"],"candidateFree":True,"currentTargetSha256":sha(target)}
   if ctx["callerless"]:
    cell.update({"cellDisposition":"hold-callerless-hash-only","sourceTextOmitted":True,"currentTargetTextOmitted":True})
   else:
    cell.update({"source":src,"currentTarget":target,"sourcePlaceholderTokens":st["placeholders"],"currentPlaceholderTokens":tt["placeholders"],"placeholderMultisetMatches":ph,"sourceMarkupTags":st["markup"],"currentMarkupTags":tt["markup"],"markupMatches":mk,"sourceNumericTokens":st["numbers"],"currentNumericTokens":tt["numbers"],"numericTokensPreserved":num,"numericPresentationEquivalent":pres,"sourceProtectedLiterals":st["protectedLiterals"],"missingProtectedLiterals":missing,"protectedLiteralsPreserved":not missing,"catalogTranslationHash":msg.get("translationHashes",{}).get(loc),"translationStatus":msg.get("translationStatus",{}).get(loc)})
   cells.append(cell)
 if len(cells)!=240: raise SystemExit("FAIL W685 cell count")

 # Compare source and caller context against live main.
 main_head=api0["baseLiveRefOid"];main_tree=git(repo,"rev-parse",f"{main_head}^{{tree}}")
 main_msgs=json.loads(subprocess.check_output(["git","-C",str(repo),"show",f"{main_head}:{catalog_path}"],text=True))["messages"]
 main_files={p:file_tuple(repo,p,main_head) for p in production_paths(repo,main_head)}
 sig=lambda c:{(r["path"],r["matchKind"],r["lineText"].strip()) for r in c["callers"]}
 drift=[]
 for item,pc in zip(selected,contexts):
  mm=main_msgs.get(item["sourceId"]);ms=mm.get("source") if isinstance(mm,dict) else None;mh=sha(ms) if isinstance(ms,str) else None
  mc=match_context({"sourceId":item["sourceId"],"source":ms,"sourceSha256":mh},main_files,main_head) if isinstance(ms,str) else {"callerless":True,"callers":[],"exactMatchCount":0}
  nr=sorted(sig(mc)-sig(pc));rr=sorted(sig(pc)-sig(mc))
  drift.append({"sourceId":item["sourceId"],"prSourceSha256":item["sourceSha256"],"mainSourcePresent":isinstance(ms,str),"mainSourceSha256":mh,"sourceSame":mh==item["sourceSha256"],"prCallerCount":pc["exactMatchCount"],"mainCallerCount":mc["exactMatchCount"],"prCallerless":pc["callerless"],"mainCallerless":mc["callerless"],"newMainCallerSignatures":[{"path":x[0],"matchKind":x[1],"lineText":x[2]} for x in nr],"prOnlyCallerSignatures":[{"path":x[0],"matchKind":x[1],"lineText":x[2]} for x in rr],"contextDrift":mh!=item["sourceSha256"] or bool(nr) or bool(rr) or pc["exactMatchCount"]!=mc["exactMatchCount"]})
 main_drift={"repository":"snapetech-org/ROMarrNG","prHead":HEAD,"prTree":TREE,"mainHead":main_head,"mainTree":main_tree,"baseApiSha":api0["baseApiSha"],"baseApiRefMismatch":api0["baseApiRefMismatch"],"comparison":"same stable source IDs and exact quoted source/source-ID/HTML text searches over tracked production files under romarr; tests, docs, catalogs, and workflows excluded","selectedSourceCount":20,"sourcesMissingFromMain":sum(not r["mainSourcePresent"] for r in drift),"sourceTextChanges":sum(not r["sourceSame"] for r in drift),"sourcesWithCallerContextDrift":sum(r["contextDrift"] for r in drift),"sourcesWithNewMainCallers":sum(bool(r["newMainCallerSignatures"]) for r in drift),"results":drift}

 inp=out/"input";inp.mkdir(parents=True,exist_ok=True)
 wj(inp/"PR-attestation-before.json",api0)
 write_jsonl(inp/"catalog-key-order.jsonl",[{"catalogZeroBasedIndex":i,"sourceId":sid,"sourceSha256":sha(msgs[sid]["source"])} for i,sid in enumerate(ids)])
 wj(inp/"source-registry-redacted.json",{"sourceQueuePath":"romarr/ui-source-messages.json","sourceQueueSha256":source_queue_sha,"sourceSnapshotPath":"romarr/ui-source-snapshot.json","sourceSnapshotSha256":source_snapshot_sha,"activeSourceCount":len(registry),"messages":[{k:v for k,v in row.items() if k!="source"} for row in registry_rows]})
 wj(inp/"source-snapshot-hashes.json",snapshot)
 wj(inp/"catalog-file-pins.json",{"head":HEAD,"tree":TREE,"catalogPath":catalog_path,"catalogSha256":sha(catalog_raw),"catalogGitBlob":git(repo,"rev-parse",f"{HEAD}:{catalog_path}"),"catalogMessageCount":len(msgs),"catalogKeyOrderSha256":cat_order_sha,"sourceQueuePath":registry_path,"sourceQueueSha256":source_queue_sha,"sourceSnapshotPath":snapshot_path,"sourceSnapshotSha256":source_snapshot_sha,"sourceIdOrderSha256":id_order_sha,"activeUniqueSourceIds":len(registry)})
 wj(inp/"source-file-pins.json",{"head":HEAD,"tree":TREE,"files":pin_rows})
 wjl(inp/"selected-sources.jsonl",selected_public);wjl(inp/"selection-boundary.jsonl",boundary)
 wjl(inp/"source-contexts.jsonl",[safe_context(c) for c in contexts])
 wj(inp/"caller-search-audit.json",{"head":HEAD,"tree":TREE,"queryCount":20,"searchScope":"tracked production source files under romarr; tests, docs, locale catalogs, and workflows excluded","productionFilesSearched":len(prod_files),"callerlessSourceCount":sum(c["callerless"] for c in contexts),"callerlessCellCount":12*sum(c["callerless"] for c in contexts),"results":[{"sourceId":c["sourceId"],"sourceSha256":c["sourceSha256"],"matchCount":c["exactMatchCount"],"callerless":c["callerless"],"contextSha256":c["contextSha256"],"sourceTextOmitted":c["callerless"]} for c in contexts]})
 wjl(inp/"candidate-free-cells.jsonl",cells);wj(inp/"candidate-free-token-summary.json",dict(mismatch));wj(inp/"main-context-drift.json",main_drift)
 wjl(inp/"prior-selection-reattestation.jsonl",selection_rows);wj(inp/"prior-selection-reattestation-summary.json",{"windows":dict(collections.Counter(r["priorWindow"] for r in selection_rows)),"count":len(selection_rows),"allSelectionsMatchCurrentCatalogAndRegistry":True,"head":HEAD,"tree":TREE})
 wjl(inp/"prior-hold-reattestation.jsonl",hold_rows);wj(inp/"prior-hold-reattestation-summary.json",{"count":len(hold_rows),"windows":dict(collections.Counter(r["window"] for r in hold_rows)),"allTargetHashesMatch":True,"changedTargets":0,"callerlessW645Cells":len(w645_holds),"callerlessW665Cells":len(w665_hold_keys),"textInHoldRows":False,"head":HEAD,"tree":TREE})
 wjl(inp/"prior-hold-context-reattestation.jsonl",prior_hold_contexts)
 wjl(inp/"prior-applied-cell-reattestation.jsonl",applied_rows);wj(inp/"prior-applied-cell-reattestation-summary.json",{"count":len(applied_rows),"windows":dict(collections.Counter(r["priorWindow"] for r in applied_rows)),"allFinalTargetHashesMatch":True,"changedTargets":0,"head":HEAD,"tree":TREE})
 for label,rows in readbacks.items(): wjl(inp/("prior-"+label.lower().replace("-","")+"-cell-hash-reattestation.jsonl"),rows)
 wjl(inp/"prior-w645-context-reattestation.jsonl",w645_ctx_rows)
 lineage={
 "result":"PASS","currentHead":HEAD,"currentTree":TREE,"previousCandidateFreeHead":PREV_HEAD,"previousCandidateFreeTree":PREV_TREE,
 "previousProductCommit":PREV_PRODUCT,"previousProductTree":PREV_PRODUCT_TREE,
 "previousSourceSelectionsReattested":len(selection_rows),"previousHeldCellsReattested":len(hold_rows),"previousAppliedCellsReattested":len(applied_rows),
 "previousReadbackWindows":{k:len(v) for k,v in readbacks.items()},"currentCallerlessStatusCheckedForPriorHeldSources":len(prior_hold_contexts),
 "priorHoldSourcesWithCurrentCallers":hold_sources_with_callers,"w645CallerContextsReattested":len(w645_ctx_rows),
 "w645CallerContextsUnchanged":all(r["callerSignaturesUnchanged"] for r in w645_ctx_rows),
 "w645CallerlessHashOnlyHolds":len(w645_holds),"w645AppliedTargetCells":len(plan["changes"]),
 "w665LatestWindow":{"head":W665_HEAD,"tree":W665_TREE,"productCommit":W665_PRODUCT,"productTree":W665_PRODUCT_TREE,"appliedTargetCells":len(w665_changes),"holdCells":len(w665_hold_keys),"evidenceIndexEntries":len(w665_index),"evidenceIndexMissingFiles":len(w665_missing),"evidenceIndexMismatchedFiles":len(w665_mismatch),"missingFiles":w665_missing,"description":"W665 task-scratch candidate-free, primary, blind, and cross packets pass their own checksum verifiers. The PR-tree evidence checksum index lists 77 files, has no hash mismatch among extant files, but 24 listed payloads are absent from the committed PR evidence tree."},
 "w625EvidenceCaveat":{"missingFromPriorCommittedPrTree":31,"priorFullReadbackSha256":w625_hash,"matchesFinalVerifier":True,"description":"The W645 predecessor records 31 W625 bulky stage files absent from the prior committed PR evidence tree. The full W625 readback and final verifier remain hash-bound; the absent PR-tree stage files are not claimed as verified."},
 "w645BlindSummaryPinWarning":{"crossReviewResult":cross_summary["result"],"blindChecksumMismatchRecorded":bool(cross_summary.get("blindSummaryChecksumPinMismatch")),"rowLevelBindingsReported":cross_summary.get("blindSummaryChecksumPinMismatch",{}).get("directRowsAndSixProposalTargetsBindToCurrentInput"),"rootOutcome":root_summary.get("result"),"description":"The W645 cross-review records a stale blind top-level checksum pointer and passing row-level binding/proposal-target hash checks. This warning is retained."},
 "priorReviewSummaryPins":{"candidateFreeManifestSha256":sha((PREV_INPUT/"manifest.json").read_bytes()),"candidateFreeChecksumListSha256":sha((PREV_INPUT/"SHA256SUMS.txt").read_bytes()),"primarySummarySha256":sha((PREV_PRIMARY/"primary-output"/"summary.json").read_bytes()),"blindSummarySha256":sha((PREV_BLIND/"SUMMARY.json").read_bytes()),"crossSummarySha256":sha((PREV_CROSS/"cross-review-summary.json").read_bytes()),"rootAdjudicationSummarySha256":sha((PREV_ROOT_REVIEW/"summary.json").read_bytes()),"applicationReadbackSha256":sha((PREV_APP/"readback.json").read_bytes()),"applicationChecksumsVerified":True,"taskScratchApplicationChecksumEntries":len(app_task_index),"taskScratchUnindexedSidecarCount":len(app_task_unlisted_hashes),"taskScratchUnindexedSidecars":app_task_unlisted_hashes},
 "previousWindowSelectionCounts":dict(collections.Counter(r["priorWindow"] for r in selection_rows)),"previousWindowHoldCounts":dict(collections.Counter(r["window"] for r in hold_rows)),"previousWindowAppliedCellCounts":dict(collections.Counter(r["priorWindow"] for r in applied_rows)),
 "callerlessHoldTextIncluded":False,"currentWindowReviewDecisionsIncluded":False,"currentWindowProposalTextIncluded":False}
 wj(inp/"prior-window-lineage.json",lineage)
 wj(inp/"selection.json",{"window":WINDOW,"method":"Select catalog message insertion indices 685 through 704 (zero-based) from the exact pinned romarr/ui-labels.json message-key order.","positions":[685,704],"catalogOneBasedPositions":[686,705],"sourceCount":20,"localeCount":12,"cellCount":240,"localeOrder":LOCALES,"activeUniqueSourceIds":len(registry),"sourceIdOrderSha256":id_order_sha,"catalogMessageCount":len(msgs),"catalogKeyOrderSha256":cat_order_sha,"selectedSources":selected_public})
 wj(inp/"registry-order-note.json",{"selectionBasis":"catalog JSON message-key insertion order","selectedCatalogZeroBasedIndices":[685,704],"activeRegistryCount":len(registry),"selectedIdsInActiveRegistry":sum(r["activeSourceRegistry"] for r in selected),"activeRegistryMatches":[{"sourceId":r["sourceId"],"activeRank":r["activeSourceRank"],"registryLocations":r["registryLocations"]} for r in selected if r["activeSourceRegistry"]],"lineHintCaveat":"Active source registry metadata does not substitute for exact literal caller search and excerpt evidence."})
 wj(inp/"prior-application-source-pin.json",{"sourceHead":PREV_HEAD,"sourceTree":PREV_TREE,"productCommit":PREV_PRODUCT,"productTree":PREV_PRODUCT_TREE,"productParent":PREV_HEAD,"currentHead":HEAD,"currentTree":TREE,"productCommitAncestor":True,"latestProductCommit":W665_PRODUCT,"latestProductTree":W665_PRODUCT_TREE,"latestWindowApplicationPlanSha256":sha((W665_EVID/"application"/"root-application-plan.json").read_bytes()),"latestWindowReadbackSha256":sha((W665_EVID/"application"/"readback.json").read_bytes()),"applicationPlanSha256":sha((PREV_APP/"root-application-plan.json").read_bytes()),"applicationReadbackSha256":sha((PREV_APP/"readback.json").read_bytes()),"productCommitRecordSha256":sha((PREV_APP/"product-commit-record.json").read_bytes()),"applicationChecksumListSha256":sha((PREV_APP/"SHA256SUMS.txt").read_bytes())})

 api1=attestation(repo)
 keys=("state","draft","merged","headRefName","head","tree","apiCommitTree","branchRefOid","pullRefOid","baseRefName","baseApiSha","baseLiveRefOid","bodySha256","bodyBytes")
 if any(api0[k]!=api1[k] for k in keys): raise SystemExit("FAIL PR/API/head/body changed during extraction")
 wj(inp/"PR-attestation-after-candidate-free.json",api1)
 if git(repo,"rev-parse","HEAD")!=HEAD or git(repo,"rev-parse","HEAD^{tree}")!=TREE or git(repo,"status","--porcelain=v1","--untracked-files=all"): raise SystemExit("FAIL worktree changed during extraction")
 manifest={"artifact":"ROMarrNG PR #70 W685-W704 candidate-free input","repository":"snapetech-org/ROMarrNG","pullRequest":70,"branch":BRANCH,"baseRefName":api0["baseRefName"],"head":HEAD,"tree":TREE,"window":WINDOW,"selectionBasis":"catalog insertion order; exact ui-labels.json indices 685..704","sourceCount":20,"localeCount":12,"cellCount":240,"locales":LOCALES,"activeUniqueSourceIdCount":len(registry),"sourceIdOrderSha256":id_order_sha,"catalogMessageCount":len(msgs),"catalogPath":catalog_path,"catalogSha256":sha(catalog_raw),"catalogGitBlob":git(repo,"rev-parse",f"{HEAD}:{catalog_path}"),"catalogKeyOrderSha256":cat_order_sha,"sourceQueuePath":registry_path,"sourceQueueSha256":source_queue_sha,"sourceSnapshotSha256":source_snapshot_sha,"priorSelectedSourceCount":len(selection_rows),"priorSelectionsUnchanged":True,"priorHoldCellCount":len(hold_rows),"priorHoldTargetsUnchanged":True,"priorHoldCellChangedCount":0,"priorAppliedSelectedCellCount":len(applied_rows),"priorAppliedTargetsUnchanged":True,"priorFullWindowReadbackCounts":{k:len(v) for k,v in readbacks.items()},"priorW625EvidenceIndexMissingFromPrTreeCount":31,"priorW625ReadbackSha256MatchedFinalVerifier":True,"priorW645BlindSummaryPinWarningPreserved":True,"priorW665EvidenceIndexEntries":len(w665_index),"priorW665EvidenceIndexMissingFiles":len(w665_missing),"priorW665EvidenceIndexMismatches":len(w665_mismatch),"callerlessSourceCount":sum(c["callerless"] for c in contexts),"callerlessCurrentTargetCellCount":12*sum(c["callerless"] for c in contexts),"callerContextCount":len(contexts),"directCallerRefCount":sum(c["exactMatchCount"] for c in contexts),"currentTargetPlaceholderMismatches":mismatch["placeholder"],"currentTargetMarkupMismatches":mismatch["markup"],"currentTargetNumericMismatches":mismatch["numeric"],"currentTargetNumericPresentationDifferences":mismatch["numericPresentationDifferences"],"currentTargetProtectedLiteralMismatches":mismatch["protectedLiteral"],"currentTargetMissingCells":mismatch["missingTarget"],"mainHead":main_head,"mainTree":main_tree,"mainSourcesMissing":main_drift["sourcesMissingFromMain"],"mainSourceTextChanges":main_drift["sourceTextChanges"],"mainContextDriftCount":main_drift["sourcesWithCallerContextDrift"],"candidateFree":True,"proposedTargetsIncluded":False,"reviewDecisionsIncluded":False,"callerlessCellTextIncluded":False,"createdUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"reviewBoundary":"Candidate-free extraction only. Current callerless cells are hash-only with source/current target text omitted. Prior source selections, held-cell hashes, applied-cell hashes, and six 240-cell readbacks are reattested to this exact head. W625, W645, and W665 provenance limitations are preserved in prior-window-lineage.json; the W665 committed index lists 77 files with 24 missing payloads and zero mismatches among present files, while complete task-scratch packets verify."}
 wj(inp/"manifest.json",manifest)
 (out/"README.md").write_text(f"""# ROMarrNG PR #70 W685-W704 candidate-free packet

Pinned to open draft PR head {HEAD}, tree {TREE}, branch {BRANCH}. It selects catalog insertion indices 685-704 (one-based positions 686-705): 20 source keys and 240 locale cells.

This packet contains source/caller context and current target text only for caller-backed keys. Its {manifest['callerlessCurrentTargetCellCount']} callerless locale cells are hash-only; their source and current target text are omitted. It contains no proposal or review decision for W685-W704.

Prior lineage is reattested at this head: {len(selection_rows)} source selections, {len(hold_rows)} held cells, {len(applied_rows)} applied cells, and full readbacks for W565-W584, W585-W604, W605-W624, W625-W644, W645-W664, and W665-W684. Two inherited caveats remain explicit in input/prior-window-lineage.json: 31 W625 stage files were absent from the prior committed PR evidence tree although its full readback matched the final verifier; W645 cross-review recorded a stale blind summary checksum pointer while reporting passing row-level bindings; and W665 PR evidence lists 77 files but omits 24 listed payloads (with zero mismatches among extant files), while the full task-scratch review packets pass their checksums.

The packet checks live PR API, branch, pull ref, API commit tree, source pins, and worktree before and after extraction. The API base SHA differs from live main; that is recorded. No repository, catalog, PR, or workflow files were changed. No tests, builds, scans, or CI were run.

Run python3 verify_candidate_free.py for portable packet checks, or add --repo /path/to/the-exact-head-worktree to verify local Git data and cell hashes.
""",encoding="utf-8")
 wj(inp/"manifest.json",manifest)
 write_sums(inp);write_sums(out)
 print(json.dumps({"result":"CANDIDATE_FREE_DATA_BUILT","head":HEAD,"tree":TREE,"window":WINDOW,"selectedSources":len(selected),"cells":len(cells),"callerlessSources":sum(c["callerless"] for c in contexts),"callerlessCells":12*sum(c["callerless"] for c in contexts),"directCallerRefs":sum(c["exactMatchCount"] for c in contexts),"tokenMismatches":dict(mismatch),"priorSelectedSources":len(selection_rows),"priorHoldCells":len(hold_rows),"priorAppliedCells":len(applied_rows),"priorReadbackCounts":{k:len(v) for k,v in readbacks.items()},"mainContextDrift":{"missing":main_drift["sourcesMissingFromMain"],"sourceChanged":main_drift["sourceTextChanges"],"contextDrift":main_drift["sourcesWithCallerContextDrift"]},"blindSummaryWarningPreserved":True},ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
