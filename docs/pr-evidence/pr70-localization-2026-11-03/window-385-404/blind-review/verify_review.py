#!/usr/bin/env python3
import hashlib,json,re
from collections import Counter
from pathlib import Path
p=Path(__file__).resolve().parent
m=json.loads((p/"manifest.json").read_text()); s=json.loads((p/"summary.json").read_text())
assert m["head"]=="0afd1d8c150fb96d868394a8d9620371db612185" and m["tree"]=="0ba717d05c49356d8b1f55ac4a6b8844c161a402"
assert m["blind"]=="yes" and m["candidateFreeOnly"]=="yes" and m["primaryReviewAccessed"]=="no"
rows=[json.loads(x) for x in (p/"review-decisions.jsonl").read_text().splitlines() if x.strip()]
assert len(rows)==240 and len({(r["position"],r["locale"]) for r in rows})==240
c=Counter(r["disposition"] for r in rows)
assert c==Counter({"accept-current":216,"correction":16,"refinement":8})
ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
for r in rows:
 if r["disposition"]=="accept-current": assert "proposedTarget" not in r
 else:
  assert hashlib.sha256(r["proposedTarget"].encode()).hexdigest()==r["proposedTargetSha256"]
  assert Counter(ph.findall(r["currentTarget"]))==Counter(ph.findall(r["proposedTarget"]))
h=[json.loads(x) for x in (p/"prior-hold-reattestation.jsonl").read_text().splitlines() if x.strip()]
assert len(h)==288 and all(x["targetUnchanged"] and x["sourceMatchesCurrentQueue"] and x["positionMatchesCurrentQueue"] and x["currentTargetSha256"]==x["priorCurrentTargetSha256"] for x in h)
assert s["dispositions"]==dict(sorted(c.items())) and s["carriedHoldCellCount"]==288 and s["carriedHoldCellsUnchanged"] is True and s["newHolds"]==0
print("PASS: 240 blind decisions; 216 accept-current, 16 corrections, 8 refinements; 288 carried holds unchanged; exact head/tree pinned")
