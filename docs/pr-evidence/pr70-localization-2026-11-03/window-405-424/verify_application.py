#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys
B=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[4]
BASE="c146189f29db8fbd77d68dff0c33a0ab59a6b601"
BASE_TREE="3db10f8b87577edd1167e4489524e6afbb50d556"
def sha(b):return hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def jl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def check(ok,msg):
 if not ok:raise SystemExit("FAIL: "+msg)
def sums(d):
 s={}
 for line in (d/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
  h,n=line.split("  ",1); s[n]=h
 for n,h in s.items():check(sha((d/n).read_bytes())==h,"nested checksum "+str(d/n))
 check(set(s)=={p.name for p in d.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"},"nested checksum inventory "+str(d))
 return sha((d/"SHA256SUMS.txt").read_bytes())
# Verify full application evidence checksum inventory.
top={}
for line in (B/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 h,n=line.split("  ",1); top[n]=h
 check(sha((B/n).read_bytes())==h,"evidence checksum "+n)
actual={p.relative_to(B).as_posix() for p in B.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt"}
check(set(top)==actual,"evidence checksum inventory")
inp=B/"candidate-free/input"; primary=B/"primary-review"; blind=B/"blind-review"; cross=B/"cross-audit"
# Check the four included source packets and their original nested seals.
input_sums=sums(inp); primary_sums=sums(primary); blind_sums=sums(blind); cross_sums=sums(cross)
r=subprocess.run([sys.executable,str(inp/"verify_input.py")],cwd=inp,capture_output=True,text=True)
check(r.returncode==0,"candidate-free verifier: "+r.stdout+r.stderr)
r=subprocess.run([sys.executable,str(cross/"verify-cross-audit.py"),"--candidate-free",str(inp),"--primary",str(primary),"--blind",str(blind)],cwd=cross,capture_output=True,text=True)
check(r.returncode==0,"cross-audit verifier: "+r.stdout+r.stderr)
# Exact base, tree and catalog byte/hash attestations.
head=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
tree=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD^{tree}"],text=True).strip()
if head!=BASE:
 check(subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD^"],text=True).strip()==BASE,"application commit parent")
check(subprocess.check_output(["git","-C",str(ROOT),"rev-parse",f"{BASE}^{{tree}}"],text=True).strip()==BASE_TREE,"pinned base tree")
path="romarr/ui-labels.json"; base_bytes=subprocess.check_output(["git","-C",str(ROOT),"show",f"{BASE}:{path}"])
base=json.loads(base_bytes); after_bytes=(ROOT/path).read_bytes(); after=json.loads(after_bytes)
plan=jl(B/"apply-plan.jsonl"); readback=jl(B/"catalog-readback.jsonl")
cells=jl(inp/"current-target-cells.jsonl"); carried=jl(B/"hold-plan.jsonl")
carry_reattest=jl(cross/"carried-hold-reattestation.jsonl")
new_holds=jl(cross/"primary-new-hold-assessment.jsonl")
check(len(plan)==len(readback)==len(cells)==240,"240-cell readback")
replace={(x["sourceId"],x["locale"]):x for x in plan if x["action"]=="replace"}
noop=[x for x in plan if x["action"]=="no-op"]; holds=[x for x in plan if x["action"]=="hold"]
check(len(replace)==26 and len(noop)==166 and len(holds)==48,"26/166/48 application plan")
check(len(carry_reattest)==288 and len(new_holds)==48,"carried and new holds")
cell_by={(x["position"],x["locale"]):x for x in cells}
for row,rb in zip(plan,readback):
 key=(row["position"],row["locale"]); c=cell_by[key]
 sid=row["sourceId"]; loc=row["locale"]
 check((rb["sourceId"],rb["locale"],rb["expectedCurrentTargetSha256"])==(sid,loc,row["expectedCurrentTargetSha256"]),"readback identity")
 check(c["sourceId"]==sid and c["sourceSha256"]==row["sourceSha256"] and c["currentTargetSha256"]==row["expectedCurrentTargetSha256"],"candidate-free exact current hash")
 actual_text=after["messages"][sid]["translations"][loc]
 check(actual_text==row["target"]==rb["actualTarget"],"catalog exact target")
 check(sha(actual_text.encode())==row["targetSha256"]==rb["actualTargetSha256"] and rb["matches"],"catalog exact target hash")
 if row["action"]=="replace":
  check(actual_text!=c["currentTarget"],"replacement differs from current")
  check(all(token in actual_text for token in c["sourceProtectedLiterals"]),"protected literal check")
 else:
  check(actual_text==c["currentTarget"],"no-op/hold unchanged")
# Compare entire catalog to base outside the exact 26 translations and preserve all metadata.
check(list(base["messages"])==list(after["messages"]),"message ID/key order")
check(base["locales"]==after["locales"] and base["availableLocales"]==after["availableLocales"],"locale structure")
check(len(after["messages"])==1836,"catalog size")
changed=set()
for sid,msg in base["messages"].items():
 out=after["messages"][sid]
 check(msg["source"]==out["source"] and msg["sourceHash"]==out["sourceHash"],"source unchanged "+sid)
 check(list(msg["translations"])==list(out["translations"]),"locale key order "+sid)
 for loc,val in msg["translations"].items():
  if val!=out["translations"][loc]:changed.add((sid,loc))
  if (sid,loc) not in replace:check(val==out["translations"][loc],"non-target translation "+sid+"/"+loc)
 for field in ("translationHashes","translationStatus","translationReview","translationPending"):
  check(msg.get(field,[])==out.get(field,[]),field+" metadata unchanged "+sid)
check(changed==set(replace),"exact 26 translation cells")
# Verify old carries and current holds read back unchanged.
check(all(x["targetUnchanged"] and x["sourceMatchesCurrentCatalog"] and x["priorPositionMatches"] and x["priorSourceMatches"] for x in carry_reattest),"288 carried holds unchanged")
for row in holds:
 sid=row["sourceId"]; loc=row["locale"]
 check(sha(after["messages"][sid]["translations"][loc].encode())==row["expectedCurrentTargetSha256"],"48 current holds unchanged")
# Preserve workflows.
w=subprocess.run(["git","-C",str(ROOT),"diff","--exit-code",BASE,"--",".github/workflows"],capture_output=True)
check(w.returncode==0,"workflow files unchanged")
inv=j(B/"catalog-invariants.json")
check(inv["baseCatalogSha256"]==sha(base_bytes) and inv["appliedCatalogSha256"]==sha(after_bytes),"catalog file hashes")
check(inv["changedTranslationCellCount"]==26 and inv["workflowsUnchanged"],"application invariant manifest")
print("PASS application: 240 exact cells; 26 replacements (20 corrections, 6 refinements); 166 no-ops; 48 holds; 288 carried holds unchanged; 1,836 catalog messages/order preserved; zero non-target changes; workflows unchanged; all packet seals/readbacks pass.")
