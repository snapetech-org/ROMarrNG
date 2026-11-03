#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent
SCRATCH=HERE.parent
def sha(b):return hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def jl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ok(x,msg):
 if not x:raise SystemExit("FAIL: "+msg)
def verify_sums(d):
 sums={}
 for line in (d/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
  h,n=line.split("  ",1); sums[n]=h
 ok(set(sums)=={p.name for p in d.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"},"upstream checksum inventory "+str(d))
 for n,h in sums.items():ok(sha((d/n).read_bytes())==h,"upstream checksum "+str(d/n))
 return sha((d/"SHA256SUMS.txt").read_bytes())
ap=argparse.ArgumentParser()
ap.add_argument("--candidate-free",type=Path,default=SCRATCH/"romarrng-pr70-w405-424-candidate-free-20261103"/"input")
ap.add_argument("--primary",type=Path,default=SCRATCH/"romarrng-pr70-w405-424-primary-20261103"/"primary-review")
ap.add_argument("--blind",type=Path,default=SCRATCH/"romarrng-pr70-w405-424-blind-20261103")
a=ap.parse_args(); inp=a.candidate_free.resolve(); pri=a.primary.resolve(); bli=a.blind.resolve()
own={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 h,n=line.split("  ",1); own[n]=h; ok(sha((HERE/n).read_bytes())==h,"cross packet checksum "+n)
ok(set(own)=={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"},"cross checksum inventory")
ci=verify_sums(inp); ps=verify_sums(pri); bs=verify_sums(bli)
r=subprocess.run([sys.executable,str(inp/"verify_input.py")],cwd=inp,capture_output=True,text=True)
ok(r.returncode==0,"candidate-free verifier "+r.stdout+r.stderr)
primary_meta=j(pri/"input-verification.json")
if primary_meta.get("candidateFreeInputPath")==str(inp):
 r=subprocess.run([sys.executable,str(pri/"verify-primary-review.py"),"--candidate-free",str(inp)],cwd=pri,capture_output=True,text=True)
 ok(r.returncode==0,"primary verifier "+r.stdout+r.stderr)
blind_meta=j(bli/"candidate-free-provenance.json")
if blind_meta.get("candidateFreeInputPath")==str(inp):
 r=subprocess.run([sys.executable,str(bli/"verify_packet.py")],cwd=bli,capture_output=True,text=True)
 ok(r.returncode==0,"blind verifier "+r.stdout+r.stderr)
prov=j(HERE/"provenance.json")
ok(prov["candidateFreeChecksumListSha256"]==ci and prov["primaryChecksumListSha256"]==ps and prov["blindChecksumListSha256"]==bs,"upstream packet seals")
ok(prov["candidateFreeManifestSha256"]==sha((inp/"manifest.json").read_bytes()) and prov["primaryManifestSha256"]==sha((pri/"manifest.json").read_bytes()) and prov["blindManifestSha256"]==sha((bli/"manifest.json").read_bytes()),"upstream manifest pins")
ok(primary_meta["candidateFreeInputManifestSha256"]==sha((inp/"manifest.json").read_bytes()) and primary_meta["candidateFreeInputChecksumListSha256"]==ci,"primary candidate-free provenance")
ok(blind_meta["candidateFreeManifestSha256"]==sha((inp/"manifest.json").read_bytes()) and blind_meta["candidateFreeSha256SumsFileSha256"]==ci,"blind candidate-free provenance")
for name in ("current-target-cells.jsonl","source-contexts.jsonl","prior-hold-reattestation.jsonl"):
 ok(blind_meta["candidateFreeFileHashes"][name]==sha((inp/name).read_bytes()),"blind input content pin "+name)
ok(prov["head"]=="c146189f29db8fbd77d68dff0c33a0ab59a6b601" and prov["tree"]=="3db10f8b87577edd1167e4489524e6afbb50d556","exact input refs")
cells=jl(inp/"current-target-cells.jsonl"); primary=jl(pri/"review-ledger.jsonl"); blind=jl(bli/"review.jsonl")
cross=jl(HERE/"cell-reconciliation.jsonl"); plan=jl(HERE/"apply-plan.jsonl")
ok(len(cells)==len(primary)==len(blind)==len(cross)==len(plan)==240,"240 cells")
def chosen(r):return r["currentTarget"] if r["disposition"] in ("accept-current","hold") else r["proposedTarget"]
hold_ct=0; change_ct=0; noop_ct=0
ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}"); nums=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
for i,(c,p,b,x,q) in enumerate(zip(cells,primary,blind,cross,plan)):
 k=(c["position"],c["locale"],c["sourceId"],c["sourceSha256"],c["currentTargetSha256"])
 ok(k==(p["position"],p["locale"],p["sourceId"],p["sourceSha256"],p["currentTargetSha256"]),"primary exact row "+str(i))
 ok(k==(b["position"],b["locale"],b["sourceId"],b["sourceSha256"],b["currentTargetSha256"]),"blind exact row "+str(i))
 ok(k==(x["position"],x["locale"],x["sourceId"],x["sourceSha256"],x["currentTargetSha256"]),"cross exact row "+str(i))
 ok(x["primarySelectedTarget"]==chosen(p) and x["blindSelectedTarget"]==chosen(b),"review target normalization "+str(i))
 ok(x["primarySelectedTargetSha256"]==sha(chosen(p).encode()) and x["blindSelectedTargetSha256"]==sha(chosen(b).encode()),"selected review hashes "+str(i))
 ok(x["callerContextSha256"]==c["callerContextSha256"]==p["callerContextSha256"]==b.get("callerContextSha256",b.get("sourceContextSha256")),"exact caller hash "+str(i))
 ok((q["position"],q["locale"],q["sourceId"],q["sourceSha256"],q["expectedCurrentTargetSha256"])==(x["position"],x["locale"],x["sourceId"],x["sourceSha256"],x["currentTargetSha256"]),"apply plan current hash "+str(i))
 target=x["adjudicatedTarget"]; ok(sha(target.encode())==x["adjudicatedTargetSha256"]==q["targetSha256"] and target==q["target"],"adjudicated hash "+str(i))
 action="hold" if x["adjudicatedDisposition"]=="hold" else ("replace" if target!=c["currentTarget"] else "no-op")
 ok(x["action"]==q["action"]==action,"action plan "+str(i))
 if action=="hold":
  hold_ct+=1; ok(p["disposition"]==b["disposition"]=="hold" and target==c["currentTarget"],"held target")
 elif action=="replace":
  change_ct+=1; ok(x["adjudicatedDisposition"] in ("correction","refinement"),"replace disposition")
  ok(sorted(ph.findall(c["source"]))==sorted(ph.findall(target))==sorted(c["sourcePlaceholderTokens"]),"proposal placeholders")
  ok(nums.findall(c["source"])==nums.findall(target)==c["sourceNumericTokens"],"proposal numeric tokens")
  ok(all(t in target for t in c["sourceProtectedLiterals"]),"proposal protected literals")
 else:noop_ct+=1;ok(target==c["currentTarget"] and x["adjudicatedDisposition"]=="accept-current","no-op")
summary=j(HERE/"summary.json")
ok((hold_ct,change_ct,noop_ct)==(48,26,166),"final plan counts")
ok(summary["adjudicatedDispositionCounts"]=={"accept-current":166,"correction":20,"refinement":6,"hold":48},"disposition counts")
ok(summary["semanticOrDispositionDisagreements"]==12 and summary["targetHashDisagreements"]==11 and summary["sameTargetDispositionDisagreements"]==1,"disagreement totals")
new_holds=jl(HERE/"primary-new-hold-assessment.jsonl")
ok(len(new_holds)==48 and all(x["primaryHeld"] and x["blindHeld"] and x["disposition"]=="hold" for x in new_holds),"48 new holds independently confirmed")
carry=jl(HERE/"carried-hold-reattestation.jsonl")
ok(len(carry)==288 and all(x["targetUnchanged"] and x["sourceMatchesCurrentCatalog"] and x["priorPositionMatches"] and x["priorSourceMatches"] for x in carry),"288 carry holds unchanged")
ok(summary["primaryNewHoldsConfirmed"]==48 and summary["carriedPriorHoldsChanged"]==0,"hold summary")
disagreements=jl(HERE/"disagreement-resolutions.jsonl")
ok(len(disagreements)==12,"disagreement adjudication coverage")
expected_keys={(409,"es"),(409,"hi"),(409,"vi"),(412,"es"),(412,"hi"),(412,"id"),(412,"pt-BR"),(412,"vi"),(415,"ar"),(422,"vi"),(423,"es"),(424,"ar")}
ok({(r["position"],r["locale"]) for r in disagreements}==expected_keys,"exact disagreement key set")
cross_by={(r["position"],r["locale"]):r for r in cross}
for d in disagreements:
 x=cross_by[(d["position"],d["locale"])]
 for field,other in [("primaryDisposition","primaryDisposition"),("blindDisposition","blindDisposition"),("resolutionDisposition","adjudicatedDisposition"),("resolutionTarget","adjudicatedTarget"),("resolutionTargetSha256","adjudicatedTargetSha256"),("resolution","adjudication")]:
  ok(d[field]==x[other],"disagreement reconciliation linkage "+str((d["position"],d["locale"],field)))
for b in blind:
 ok(b["sourceHashVerified"] and b["currentTargetHashVerified"],"blind source/current self-attestation")
 if b["disposition"] in ("correction","refinement"):
  ok(sha(b["proposedTarget"].encode())==b["proposedTargetSha256"],"blind proposed target hash")
  ok(b["proposedChecks"]=={"numericTokensPreserved":True,"placeholdersPreserved":True,"protectedLiteralsPreserved":True},"blind token checks")
refs=j(HERE/"live-refs-before.json"); after=j(HERE/"live-refs-after.json")
for label,r in [("before",refs),("after",after)]:
 ok(r["headRefOid"]==r["liveBranchRefOid"]==r["livePullRefOid"]=="c146189f29db8fbd77d68dff0c33a0ab59a6b601" and r["headTree"]=="3db10f8b87577edd1167e4489524e6afbb50d556","live ref attestation "+label)
 ok(r["state"]=="OPEN" and r["isDraft"] and r["headRefName"]=="task/localization-translation-review-20261030","PR state "+label)
ok(refs["baseRefOid"]==after["baseRefOid"] and refs["headRefOid"]==after["headRefOid"] and refs["headTree"]==after["headTree"],"refs stable across cross-audit")
print("PASS cross-audit: upstream packet seals and candidate-free/available verifiers; 240 exact-hash cells; 12 disagreements resolved; 166 no-op, 26 replacements, 48 holds; 48 current holds confirmed; 288 carried holds unchanged; token checks pass.")
