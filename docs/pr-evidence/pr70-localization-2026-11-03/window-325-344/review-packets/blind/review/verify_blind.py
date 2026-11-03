#!/usr/bin/env python3
"""Read-only verifier for the ROMarr W325-W344 candidate-free blind review."""
import collections, hashlib, json, re, sys
from pathlib import Path

review=Path(__file__).resolve().parent
input_dir=Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w325-344-primary-20261103/input")
def read_json(p): return json.loads(p.read_text(encoding="utf-8"))
def jsonl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def digest(b): return hashlib.sha256(b).hexdigest()
def fail(msg): raise SystemExit("FAIL: "+msg)
# Verify candidate-free source packet checksum list and its distinct manifest pin.
for line in (input_dir/"SHA256SUMS.txt").read_text().splitlines():
 if not line.strip(): continue
 expected,name=line.split(None,1); name=name.strip().lstrip("*")
 actual=digest((input_dir/name).read_bytes())
 if actual!=expected: fail("candidate-free input checksum: "+name)
manifest_bytes=(input_dir/"manifest.json").read_bytes()
manifest_sha=digest(manifest_bytes)
input_sums_sha=digest((input_dir/"SHA256SUMS.txt").read_bytes())
manifest=read_json(input_dir/"manifest.json")
summary=read_json(review/"summary.json")
prov=read_json(review/"provenance.json")
att=read_json(review/"PR-attestation.json")
if manifest_sha!=summary["candidateFreeManifestSha256"] or manifest_sha!=prov["candidateFreeManifestJsonSha256"]: fail("candidate-free manifest SHA")
if input_sums_sha!=summary["candidateFreeChecksumListSha256"] or input_sums_sha!=prov["candidateFreeChecksumListSha256"]: fail("candidate-free checksum-list SHA")
head="018937dc98d451ddd04d2d0942bca2777ef64dd3"; tree="c13dc4fc091565318d11a19ad9e851215a5f917e"
if (att["head"],att["tree"],att["branchRef"],att["pullRef"])!=(head,tree,head,head): fail("live PR refs/head/tree")
if att["state"]!="OPEN" or not att["isDraft"] or att["prBodyRead"]: fail("PR attestation boundary")
pins=read_json(input_dir/"catalog-file-pins.json")
for f in pins["files"].values():
 if f["gitBlob"] not in [x["gitBlob"] for x in att["sourceAndCatalogBlobPins"] if x["matches"]]: fail("pinned source/catalog Git blob")
for x in att["sourceAndCatalogBlobPins"]:
 if not x["matches"] or x["gitBlob"]!=x["expectedGitBlob"]: fail("live blob mismatch: "+x["path"])
source_rows={x["position"]:x for x in jsonl(input_dir/"source-inventory-selection.jsonl")}
context_rows={x["position"]:x for x in jsonl(input_dir/"source-contexts.jsonl")}
input_cells=jsonl(input_dir/"current-target-cells.jsonl")
ledger=jsonl(review/"blind-ledger.jsonl")
if len(ledger)!=240 or len(input_cells)!=240: fail("row count")
if [(x["position"],x["locale"]) for x in ledger]!=[(x["position"],x["locale"]) for x in input_cells]: fail("stable cell order / keys")
if len({(x["position"],x["locale"]) for x in ledger})!=240: fail("duplicate cell")
phre=re.compile(r"\{[^{}]+\}"); tagre=re.compile(r"</?[A-Za-z][^>]*>")
counts=collections.Counter()
for row,cell in zip(ledger,input_cells):
 key=(row["position"],row["locale"]); pos=row["position"]
 for field in ("sourceId","source","sourceSha256","catalogPath","catalogFileSha256","catalogGitBlob","currentTarget","currentTargetSha256"):
  if row[field]!=cell[field]: fail(f"{key} input pin mismatch: {field}")
 ctx=context_rows[pos]
 if row["callerResolutionHold"]!=ctx.get("callerResolutionHold",False) or row["callerContextRefs"]!=ctx.get("callerContextRefs",[]): fail(f"{key} caller context mismatch")
 sel=source_rows[pos]
 if row["placeholderTokens"]!=sorted(phre.findall(cell["source"])): fail(f"{key} source placeholder pin")
 if row["sourceNumericTokens"]!=sel.get("sourceNumericTokens",[]): fail(f"{key} source numeric pin")
 if row["sourceProtectedLiterals"]!=cell.get("sourceProtectedLiterals",[]): fail(f"{key} source protected-literal pin")
 disp=row["disposition"]; counts[disp]+=1
 if disp=="hold":
  if pos not in (329,330) or row["blindTarget"] is not None or row["blindTargetSha256"] is not None: fail(f"{key} unauthorized hold or candidate")
  if not row["callerResolutionHold"] or row["callerContextRefs"]: fail(f"{key} callerless hold evidence")
  if row["structuralChecks"] is not None: fail(f"{key} hold structural marker")
  continue
 target=row["blindTarget"]
 if not isinstance(target,str) or digest(target.encode())!=row["blindTargetSha256"]: fail(f"{key} reviewed target/hash")
 if disp=="retain" and target!=cell["currentTarget"]: fail(f"{key} retain differs from current")
 if disp in ("correction","refinement") and target==cell["currentTarget"]: fail(f"{key} no-op change disposition")
 if disp not in ("retain","correction","refinement"): fail(f"{key} unknown disposition")
 if sorted(phre.findall(target))!=sorted(phre.findall(cell["source"])): fail(f"{key} placeholder mismatch")
 nums=collections.Counter(re.findall(r"\d+",target))
 required=collections.Counter(sel.get("sourceNumericTokens",[]))
 if any(nums[n]<count for n,count in required.items()): fail(f"{key} numeric token mismatch")
 missing=[literal for literal in cell.get("sourceProtectedLiterals",[]) if literal not in target]
 if missing: fail(f"{key} protected literal mismatch: {missing}")
 if tagre.findall(target)!=tagre.findall(cell["source"]): fail(f"{key} markup mismatch")
 checks=row["structuralChecks"]
 if not checks or not all(checks[k] for k in ("placeholdersMatch","numericTokensPreserved","protectedLiteralsPreserved","markupTokensMatch")) or checks["missingProtectedLiterals"]: fail(f"{key} recorded structural checks")
expected={"correction":34,"refinement":18,"retain":164,"hold":24}
if dict(counts)!=expected or summary["counts"]!=expected: fail(f"disposition counts: {dict(counts)}")
if summary["cells"]!=240 or summary["selectedChanges"]!=52 or summary["mandatoryCallerlessHoldCells"]!=24 or summary["additionalHolds"]!=0: fail("summary counts")
if summary["nativeSpeakerSignoff"] is not False or prov["primaryReviewInspected"] or prov["crossAuditInspected"] or prov["repositoryModified"]: fail("independence/signoff boundary")
# Verify sealed output file sums. The sidecar records SHA256SUMS.txt SHA separately.
sums_path=review/"SHA256SUMS.txt"
for line in sums_path.read_text().splitlines():
 if not line.strip(): continue
 expected_hash,name=line.split(None,1); name=name.strip().lstrip("*")
 actual=digest((review/name).read_bytes())
 if actual!=expected_hash: fail("review checksum: "+name)
sidecar=(review/"SHA256SUMS.txt.sha256").read_text().split()[0]
if sidecar!=digest(sums_path.read_bytes()): fail("review checksum-list sidecar SHA")
print("PASS: 240 cells; 34 corrections, 18 refinements, 164 retains, 24 mandatory holds; input/live pins, callers, placeholders, numeric/protected literals, markup, ledger hashes, and review checksums verified.")
