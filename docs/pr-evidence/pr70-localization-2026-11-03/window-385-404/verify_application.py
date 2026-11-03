import hashlib,json,subprocess
from pathlib import Path
repo=Path(__file__).resolve().parents[4]
p=Path(__file__).parent
base="0afd1d8c150fb96d868394a8d9620371db612185"
base_tree="0ba717d05c49356d8b1f55ac4a6b8844c161a402"
head=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
if head!=base: assert subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD^"],text=True).strip()==base
assert subprocess.check_output(["git","-C",str(repo),"rev-parse",f"{base}^{{tree}}"],text=True).strip()==base_tree
path="romarr/ui-labels.json"
before=json.loads(subprocess.check_output(["git","-C",str(repo),"show",f"{base}:{path}"]))
after=json.loads((repo/path).read_text())
plans=[json.loads(x) for x in (p/"apply-plan.jsonl").read_text().splitlines() if x]
noops=[json.loads(x) for x in (p/"no-op-plan.jsonl").read_text().splitlines() if x]
holds=[json.loads(x) for x in (p/"hold-plan.jsonl").read_text().splitlines() if x]
readback=[json.loads(x) for x in (p/"catalog-readback.jsonl").read_text().splitlines() if x]
assert len(plans)==29 and len(noops)==211 and len(holds)==288 and len(readback)==240
base_bytes=subprocess.check_output(["git","-C",str(repo),"show",f"{base}:{path}"])
assert hashlib.sha256(base_bytes).hexdigest()==json.loads((p/"catalog-invariants.json").read_text())["baseSha256"]
assert list(before["messages"])==list(after["messages"])
expected={(r["sourceId"],r["locale"]):r for r in plans+noops}
assert len(expected)==240
changed=[]
for sid,msg in before["messages"].items():
 out=after["messages"][sid]
 assert msg["source"]==out["source"] and msg["sourceHash"]==out["sourceHash"]
 assert list(msg["translations"])==list(out["translations"])
 for loc,val in msg["translations"].items():
  if val!=out["translations"][loc]: changed.append((sid,loc))
  if (sid,loc) in expected:
   r=expected[(sid,loc)]
   assert hashlib.sha256(val.encode()).hexdigest()==r["expectedCurrentTargetSha256"]
   want=r["target"] if r in plans else val
   assert out["translations"][loc]==want
   assert hashlib.sha256(want.encode()).hexdigest()==(r["targetSha256"] if r in plans else r["targetSha256"])
assert set(changed)=={(r["sourceId"],r["locale"]) for r in plans} and len(changed)==29
for r in holds:
 val=after["messages"][r["sourceId"]]["translations"][r["locale"]]
 assert hashlib.sha256(val.encode()).hexdigest()==r["expectedCurrentTargetSha256"]
assert all(r["matches"] for r in readback)
print("PASS: 240 cells, 29 updates, 211 no-ops, 288 preserved holds; base",base)
