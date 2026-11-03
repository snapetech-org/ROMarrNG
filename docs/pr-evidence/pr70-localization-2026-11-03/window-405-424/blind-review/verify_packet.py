#!/usr/bin/env python3
from pathlib import Path
import collections,hashlib,json,re,sys
D=Path(__file__).resolve().parent
def fail(m): print("FAIL:",m,file=sys.stderr); raise SystemExit(1)
def digest(b): return hashlib.sha256(b).hexdigest()
def js(n): return json.loads((D/n).read_text(encoding="utf-8"))
def jl(n): return [json.loads(s) for s in (D/n).read_text(encoding="utf-8").splitlines() if s.strip()]
sums={}
for line in (D/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 if line.strip():
  h,n=line.split(maxsplit=1); n=n.strip()
  if n in sums: fail("duplicate checksum "+n)
  sums[n]=h
files={p.name for p in D.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
if files!=set(sums): fail("checksum inventory mismatch")
for n,h in sums.items():
 if digest((D/n).read_bytes())!=h: fail("checksum mismatch "+n)
m=js("manifest.json")
if m.get("schema")!="romarrng-blind-review-v1": fail("schema mismatch")
if m["liveRefs"]["headOid"]!="c146189f29db8fbd77d68dff0c33a0ab59a6b601" or m["liveRefs"]["headTree"]!="3db10f8b87577edd1167e4489524e6afbb50d556": fail("pinned head/tree mismatch")
r=jl("review.jsonl"); c=jl("current-target-cells.jsonl"); x=jl("source-contexts.jsonl"); s=js("selection.json")
if len(r)!=240 or len(c)!=240 or len(x)!=20 or len(s["selectedSources"])!=20: fail("row count mismatch")
cm={(z["position"],z["locale"]):z for z in c}; rm={(z["position"],z["locale"]):z for z in r}; xm={z["position"]:z for z in x}
if len(rm)!=240 or set(cm)!=set(rm): fail("cell inventory mismatch")
selected={z["position"]:z for z in s["selectedSources"]}
ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}"); num=re.compile(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)")
counts=collections.Counter(); holds=set()
for z in r:
 k=(z["position"],z["locale"]); base=cm[k]; ctx=xm[z["position"]]
 for field,value in base.items():
  if z.get(field)!=value: fail("current evidence mismatch "+str(k))
 if z["sourceContextSha256"]!=ctx["callerContextSha256"] or z["callerResolution"]!=ctx["callerResolution"] or z["callerReason"]!=ctx["callerReason"]: fail("caller context mismatch "+str(k))
 if hashlib.sha256(z["source"].encode()).hexdigest()!=z["sourceSha256"] or hashlib.sha256(z["currentTarget"].encode()).hexdigest()!=z["currentTargetSha256"]: fail("source/current hash mismatch "+str(k))
 if not z["languageRationale"].strip(): fail("missing rationale "+str(k))
 d=z["disposition"]; counts[d]+=1
 if d=="hold":
  holds.add(z["position"])
  if any(z[q] is not None for q in ("proposedTarget","proposedTargetSha256","proposedChecks")): fail("held cell has proposal "+str(k))
 elif d in ("accept-current","correction","refinement"):
  p=z["proposedTarget"]
  if not isinstance(p,str) or hashlib.sha256(p.encode()).hexdigest()!=z["proposedTargetSha256"]: fail("proposed hash mismatch "+str(k))
  if d=="accept-current" and p!=z["currentTarget"]: fail("accept-current changed "+str(k))
  if d!="accept-current" and p==z["currentTarget"]: fail("empty change "+str(k))
  ck=z["proposedChecks"] or {}
  if collections.Counter(ph.findall(p))!=collections.Counter(z["sourcePlaceholderTokens"]) or ck.get("placeholdersPreserved") is not True: fail("placeholder mismatch "+str(k))
  if collections.Counter(num.findall(p))!=collections.Counter(z["sourceNumericTokens"]) or ck.get("numericTokensPreserved") is not True: fail("numeric mismatch "+str(k))
  if not all(t in p for t in z["sourceProtectedLiterals"]) or ck.get("protectedLiteralsPreserved") is not True: fail("protected literal mismatch "+str(k))
 else: fail("invalid disposition "+str(k))
 if collections.Counter(ph.findall(z["currentTarget"]))!=collections.Counter(z["sourcePlaceholderTokens"]) or collections.Counter(num.findall(z["currentTarget"]))!=collections.Counter(z["sourceNumericTokens"]): fail("current token mismatch "+str(k))
 if not all(t in z["currentTarget"] for t in z["sourceProtectedLiterals"]): fail("current protected literal mismatch "+str(k))
for pos in range(405,425):
 rows=[z for z in r if z["position"]==pos]
 if len(rows)!=12 or [z["locale"] for z in rows]!=m["selection"]["locales"]: fail("locale set/order mismatch "+str(pos))
 first=rows[0]; q=selected.get(pos)
 if not q or q["sourceId"]!=first["sourceId"] or q["sourceSha256"]!=first["sourceSha256"]: fail("selection mismatch "+str(pos))
 if first["catalogZeroBasedIndex"]!=pos or first["catalogOneBasedPosition"]!=pos+1: fail("catalog index mismatch "+str(pos))
 ctx=xm[pos]; needs=bool(ctx.get("translationDispatchGap") or ctx.get("callerless") or ctx.get("ambiguousCaller"))
 if needs != all(z["disposition"]=="hold" for z in rows): fail("caller hold mismatch "+str(pos))
expected={"accept-current":171,"correction":15,"refinement":6,"hold":48}
if dict(counts)!=expected or m["dispositionCounts"]!=expected or holds!={405,407,408,416}: fail("disposition totals mismatch")
prior=jl("prior-hold-reattestation.jsonl"); ps=js("prior-hold-reattestation-summary.json")
if len(prior)!=288 or ps.get("reattestedCellCount")!=288 or not ps.get("allCurrentTargetHashesMatchPriorHoldEvidence"): fail("carry-forward hold evidence mismatch")
prov=js("candidate-free-provenance.json")
for n,h in prov["candidateFreeFileHashes"].items():
 if digest((D/n).read_bytes())!=h: fail("candidate-free input copy mismatch "+n)
if not prov["candidateFreeVerifierResult"].startswith("PASS candidate-free W405-W424"): fail("input verifier result not passed")
print("PASS: 240 cells, 20 contexts; accept-current=171, correction=15, refinement=6, hold=48; hashes, caller holds, placeholders, numeric tokens, protected literals, carry-forward evidence, and checksums verified.")
