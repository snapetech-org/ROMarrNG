#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re

R=Path(__file__).resolve().parent
HEAD="7640720c5e3b1813725cca8d7aa46b5d968bff43"
TREE="bdee162cc11115256df8756f192b19d4337ed1dc"
BRANCH="task/localization-translation-review-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
TOKEN=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUMBER=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
CHOICES={
 (475,"de"):("refinement","Seite von GG Requestz","blind-adjunct+cross"),
 (475,"id"):("correction","Halaman GG Requestz","primary"),
 (475,"zh-Hans"):("correction","GG Requestz 页面","primary"),
 (475,"zh-Hant"):("correction","GG Requestz 頁面","primary"),
 (476,"de"):("correction","Anfragen von GG Requestz","blind-adjunct+cross"),
 (476,"id"):("correction","Permintaan GG Requestz","primary"),
 (479,"ar"):("refinement","اسم مستخدم GOG","blind-adjunct+cross"),
 (479,"de"):("refinement","GOG-Benutzername","primary"),
 (479,"id"):("refinement","Nama pengguna GOG","primary"),
 (479,"pt-BR"):("correction","Nome de usuário do GOG","primary"),
 (483,"hi"):("correction","0x1c पर GameCube डिस्क सिग्नेचर","primary"),
 (483,"id"):("correction","Tanda pengenal cakram GameCube pada 0x1c","primary"),
}
def fail(message): raise SystemExit("FAIL: "+message)
def ok(value,message):
 if not value: fail(message)
def sha(data): return hashlib.sha256(data).hexdigest()
def j(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def jl(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
def verify_sums(folder,fname="SHA256SUMS.txt",strict=False,excluded=()):
 folder=Path(folder); table={}
 for line in (folder/fname).read_text(encoding="utf-8").splitlines():
  if not line.strip(): continue
  digest,rel=line.split("  ",1)
  ok(rel not in table,"duplicate checksum "+rel); table[rel]=digest
 actual={p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name not in excluded and p != folder/fname}
 ok((set(table)==actual) if strict else set(table)<=actual,"checksum inventory "+str(folder))
 for rel,digest in table.items(): ok(sha((folder/rel).read_bytes())==digest,"checksum "+str(folder/rel))
 return len(table)
# Packet manifest inventory and root checksums.
root_files={p.relative_to(R).as_posix() for p in R.rglob("*") if p.is_file() and p not in (R/"SHA256SUMS.txt",R/"SHA256SUMS.txt.sha256",R/"packet-manifest.json")}
manifest=j(R/"packet-manifest.json")
listed={x["path"]:x for x in manifest["files"]}
ok(set(listed)==root_files,"packet manifest inventory")
for rel,item in listed.items():
 p=R/rel
 ok(sha(p.read_bytes())==item["sha256"] and p.stat().st_size==item["sizeBytes"],"packet manifest pin "+rel)
root_count=verify_sums(R,strict=True,excluded=("SHA256SUMS.txt.sha256",))
side=(R/"SHA256SUMS.txt.sha256").read_text().split()
ok(side[0]==sha((R/"SHA256SUMS.txt").read_bytes()) and side[-1]=="SHA256SUMS.txt","root checksum sidecar")
cf=R/"candidate-free-input"; pr=R/"primary-review"; bl=R/"blind-review"
cf_n=verify_sums(cf); pr_n=verify_sums(pr); bl_n=verify_sums(bl)
# Exact input identities.
cmf=j(cf/"manifest.json"); pmf=j(pr/"manifest.json"); bmf=j(bl/"manifest.json")
ok(cmf.get("head")==HEAD and cmf.get("tree")==TREE,"candidate-free exact pin")
ok(pmf.get("head")==HEAD and pmf.get("tree")==TREE,"primary exact pin")
ok(bmf.get("head")==HEAD and bmf.get("tree")==TREE,"blind exact pin")
att=j(R/"source-pin-attestation.json")
ok(att["result"]=="PASS" and att["candidateFreeSourceRepoHead"]==HEAD and att["candidateFreeSourceRepoTree"]==TREE,"source repo pin")
ok(att["candidateFreeSourceRepoDirty"] is False and att["candidateFreePrimaryBlindPinsAgreeForAll240Cells"] is True and att["sourceCatalogCallerDrift"] is False,"source/caller drift")
ok(att["candidateFreeManifestSha256"]==sha((cf/"manifest.json").read_bytes()),"candidate-free manifest hash")
ok(att["primaryManifestSha256"]==sha((pr/"manifest.json").read_bytes()),"primary manifest hash")
ok(att["blindManifestSha256"]==sha((bl/"manifest.json").read_bytes()),"blind manifest hash")
# Live ref attestations.
live0=j(R/"live-PR-attestation-before.json"); live1=j(R/"live-PR-attestation-after.json")
for label,x in (("before",live0),("after",live1)):
 ok(x["repository"]=="snapetech-org/ROMarrNG" and x["pullRequest"]==70,label+" identity")
 ok(x["state"]=="OPEN" and x["isDraft"] is True,label+" open/draft")
 ok(x["branch"]==BRANCH and x["head"]==HEAD and x["tree"]==TREE,label+" exact PR head")
 ok(x["branchRef"]==HEAD and x["pullRef"]==HEAD,label+" exact refs")
 ok(x["baseRefName"]=="main" and x["deploymentCountForExactHead"]==0,label+" base/deployment")
ok(live0["head"]==live1["head"] and live0["tree"]==live1["tree"] and live0["branchRef"]==live1["branchRef"] and live0["pullRef"]==live1["pullRef"],"stable live refs")
# Exact 240-cell reconciliation.
cells=jl(cf/"current-target-cells.jsonl")
primary=jl(pr/"primary-ledger.jsonl")
blind=jl(bl/"blind-ledger.jsonl")
adjunct=jl(bl/"six-locale-adjunct"/"independent-subset.jsonl")
ledger=jl(R/"cross-audit-ledger.jsonl")
rec=jl(R/"primary-blind-reconciliation.jsonl")
expected=[(p,l) for p in range(465,485) for l in LOCALES]
ok(len(cells)==len(primary)==len(blind)==len(ledger)==len(rec)==240,"240-cell row counts")
ok([(x["position"],x["locale"]) for x in ledger]==expected,"cross row order")
cm={(x["position"],x["locale"]):x for x in cells}
pm={(x["position"],x["locale"]):x for x in primary}
bm={(x["position"],x["locale"]):x for x in blind}
am={(x.get("position"),x.get("locale")):x for x in adjunct}
counts=Counter(); changed=[]; held=Counter(); disagreements=0
for row in ledger:
 key=(row["position"],row["locale"]); c=cm[key]; p=pm[key]; b=bm[key]
 ok(row["sourceId"]==c["sourceId"]==p["sourceId"]==b["sourceId"],"source ID "+str(key))
 ok(row["source"]==c["source"] and row["sourceSha256"]==c["sourceSha256"]==p["sourceSha256"]==b["sourceSha256"]==sha(row["source"].encode()),"source pin "+str(key))
 ok(row["currentTarget"]==c["currentTarget"] and row["currentTargetSha256"]==c["currentTargetSha256"]==p["currentTargetSha256"]==b["currentTargetSha256"]==sha(row["currentTarget"].encode()),"current target pin "+str(key))
 ok(row["catalogTranslationHash"]==c["catalogTranslationHash"],"catalog hash "+str(key))
 ok(row["sourceContextSha256"]==c["callerContextSha256"]==p["inputCallerContextSha256"]==b["callerContextSha256"],"caller context pin "+str(key))
 ok(row["primaryDisposition"]==p["disposition"] and row["blindDisposition"]==b["disposition"],"review lineage "+str(key))
 ok(row["selectedTargetSha256"]==sha(row["selectedTarget"].encode()),"selected target hash "+str(key))
 ok(row["position"]==row["catalogZeroBasedIndex"] and row["catalogOneBasedPosition"]==row["position"]+1,"catalog position "+str(key))
 ok(row["disposition"] in ("accept-current","correction","refinement","hold"),"valid decision "+str(key))
 if key in CHOICES:
  disp,target,origin=CHOICES[key]
  ok((row["disposition"],row["selectedTarget"],row["selectedTargetOrigin"])==(disp,target,origin),"cross selection "+str(key))
  if origin=="primary": ok(p.get("proposedTarget")==target,"primary target "+str(key))
  else: ok(am[key].get("proposedTarget")==target,"adjunct target "+str(key))
  ok(target!=row["currentTarget"],"change differs from current "+str(key))
  changed.append(key)
 elif row["disposition"]=="hold":
  ok(row["selectedTarget"]==row["currentTarget"] and p["disposition"]=="hold" and b["disposition"]=="continued-hold","hold retained "+str(key))
  held[row["position"]]+=1
 else:
  ok(row["disposition"]=="accept-current" and p["disposition"]=="accept-current" and b["disposition"]=="accept-current","unreviewed target "+str(key))
  ok(row["selectedTarget"]==row["currentTarget"],"accept-current target "+str(key))
 checks=row["tokenAndLiteralChecks"]
 source_ph=sorted(TOKEN.findall(row["source"])); selected_ph=sorted(TOKEN.findall(row["selectedTarget"]))
 source_num=NUMBER.findall(row["source"]); selected_num=NUMBER.findall(row["selectedTarget"])
 ok(checks["sourcePlaceholderTokens"]==source_ph and checks["selectedPlaceholderTokens"]==selected_ph and checks["selectedPlaceholderMultisetMatches"]==(Counter(source_ph)==Counter(selected_ph)),"placeholder check "+str(key))
 ok(checks["sourceNumericTokens"]==source_num and checks["selectedNumericTokens"]==selected_num and checks["selectedNumericTokensExactMatch"]==(source_num==selected_num),"numeric check "+str(key))
 ok(checks["selectedProtectedLiteralsPreserved"] is True,"protected literal check "+str(key))
 ok(checks["selectedAdditionalNamedTermsPreserved"] is True,"named-term check "+str(key))
 if row["disposition"]!="hold":
  ok(checks["selectedPlaceholderMultisetMatches"] and checks["selectedNumericTokensExactMatch"],"selected target token mismatch "+str(key))
 counts[row["disposition"]]+=1
ok(set(changed)==set(CHOICES) and len(changed)==12,"selected change set")
ok(dict(sorted(counts.items()))=={"accept-current":168,"correction":8,"hold":60,"refinement":4},"cross disposition totals")
ok(dict(sorted(held.items()))=={470:12,471:12,473:12,474:12,477:12},"callerless holds")
ok(sum(not x["dispositionAgreement"] for x in rec)==9,"primary/blind disposition disagreements")
ok(len(jl(cf/"prior-selection-reattestation.jsonl"))==80,"prior selected lineage")
ok(len(jl(cf/"prior-hold-reattestation.jsonl"))==384,"carried hold lineage")
ok(all(x["applied"] is False for x in ledger),"no catalog application in cross packet")
summary=j(R/"reconciliation-summary.json")
ok(summary["crossDispositionCounts"]==dict(sorted(counts.items())) and summary["selectedChanges"]==12 and summary["primaryBlindDispositionDisagreements"]==9,"summary counts")
ok(summary["catalogApplied"] is False and summary["selectedTargetTokenLiteralFailures"]==0,"summary gates")
print(json.dumps({"result":"PASS","rootFilesCoveredBySha256":root_count,"candidateFreeFilesChecked":cf_n,"primaryFilesChecked":pr_n,"blindFilesChecked":bl_n,"crossCells":len(ledger),"selectedChanges":len(changed),"crossCounts":dict(sorted(counts.items())),"primaryBlindDispositionDisagreements":9,"carriedPriorSelections":80,"carriedPriorHolds":384,"sourceCatalogCallerDrift":False,"exactHead":HEAD,"exactHeadDeploymentCount":live1["deploymentCountForExactHead"]},ensure_ascii=False,indent=2))

