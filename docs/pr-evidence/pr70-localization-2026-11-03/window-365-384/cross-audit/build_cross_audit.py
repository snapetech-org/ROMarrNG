#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess, sys

OUT = Path(__file__).resolve().parent
TASK = Path("/home/keith/Documents/code/task-scratch")
INPUT_SRC = TASK / "romarrng-pr70-w365-384-candidate-free-20261103/input"
PRIMARY_SRC = TASK / "romarrng-pr70-w365-384-primary-20261103/primary-review"
BLIND_SRC = TASK / "romarrng-pr70-w365-384-blind-review-20261103"
HEAD = "d1698b94781c3c84e91faf03c75e8c308dc39c34"
TREE = "3f42d41fe4bbb8edd921ff161e8298ca66038a91"
REPO = "snapetech-org/ROMarrNG"
PR = 70
LOCALES = ["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
LANGUAGES = {
 "ar":"Arabic","de":"German","es":"Spanish","fr":"French","hi":"Hindi","id":"Indonesian",
 "ja":"Japanese","ko":"Korean","pt-BR":"Brazilian Portuguese","vi":"Vietnamese",
 "zh-Hans":"Simplified Chinese","zh-Hant":"Traditional Chinese"
}
PH = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUM = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
TAG = re.compile(r"</?[A-Za-z][^>]*>")
OVERRIDES = {
 (367,"ar"): ("blind_selected","correction","Arabic blind wording explicitly distinguishes base game from generic/basic title types."),
 (368,"pt-BR"): ("blind_selected","refinement","The one-word infinitive works both as the checkbox action and as the selection-column heading."),
 (374,"ar"): ("blind_selected","refinement","The blind wording is a more idiomatic failed-save status while retaining the HTTP placeholder."),
 (374,"ja"): ("blind_selected","refinement","The blind wording states that saving failed in past tense and retains the status placeholder."),
 (374,"ko"): ("blind_selected","refinement","The blind wording states the failed save naturally and retains the status placeholder."),
 (375,"ar"): ("blind_selected","refinement","The blind wording cleanly separates the failed-save status from the retry instruction."),
 (375,"ja"): ("blind_selected","correction","The blind wording reports a completed save failure, then gives a polite retry instruction."),
 (375,"ko"): ("blind_selected","correction","The blind wording reports the completed save failure rather than an ongoing inability."),
 (377,"hi"): ("blind_selected","correction","The source is a provider setup guide, not a software installation guide."),
 (377,"vi"): ("blind_selected","correction","The source is a provider setup guide; the blind wording avoids implying software installation."),
 (377,"zh-Hans"): ("blind_selected","correction","The provider name belongs before the setup-guide label in this natural Chinese title order."),
 (377,"zh-Hant"): ("blind_selected","correction","The provider name belongs before the setup-guide label in this natural Traditional Chinese title order.")
}
POSITION_REASON = {
 365:"This is a validation prompt telling the user to select a supported platform or the all-platform option. Keep the established formal UI voice and a clear localized all-platform option.",
 366:"The pinned callers use this as a validation error in rename preview and ES-DE publishing. The selected wording clearly asks for a supported platform and keeps the established register.",
 367:"The pinned Switch collection planner validates title-kind filters. The selected wording must name base game, DLC, and update as title kinds; the Arabic blind proposal is clearer about base game.",
 368:"The key has two pinned uses: a selection checkbox action and a table-column heading. A short action form must work in both positions; retain moderate confidence because of that dual use.",
 369:"The organizer rejects ES-DE publishing until a safe shared metadata root is configured. Preserve the safety precondition, the distinction from the ROM library root, and the protected ES-DE name.",
 370:"Rename-plan creation requires the shared metadata root. The selected wording preserves this prerequisite and the glossary's shared-root terminology.",
 371:"The warning is a fragment immediately followed by a Media Management hyperlink. The selected prefix reads as a complete pointer to that linked destination and keeps link markup outside the translated text.",
 372:"This scan precondition names the exact Settings → Media Management route. Preserve that navigation and the instruction to configure the shared metadata root first.",
 373:"This help-text fragment is immediately followed by two inline filesystem paths joined by caller text. Keep the translated preposition/prefix compatible with those appended path nodes and preserve ROMarr and ES-DE.",
 374:"This is the settings-save HTTP fallback. Preserve the exact {status} placeholder and report a failed save in the locale's established UI register.",
 375:"This is the save-failure retry message. Preserve both the completed failure and the instruction to try again, using the established locale register.",
 376:"This appears as a saved-status message and toast. Keep a concise complete success status rather than changing it into an unrelated action.",
 377:"This is an identity-provider setup-guide link and accessible label. Translate setup/configuration rather than software installation, and preserve {provider}.",
 378:"This is the EmuDeck project description. Preserve setup scripts, emulator and frontend installation/configuration, and supported gaming devices.",
 379:"This runtime validation rejects a shared metadata root containing a symbolic link. Keep the same root terminology used by adjacent validation messages.",
 380:"This runtime validation reports that the configured shared metadata root is not a directory. Keep the directory distinction explicit and terminology consistent.",
 381:"Apply/undo validation reports a missing shared metadata-root configuration. Preserve that state clearly and keep the root terminology consistent.",
 382:"This is a background-scan status error after the shared metadata root was removed. Preserve the past removal state and consistent terminology.",
 383:"This is the settings field label for the configured root directory. Keep the root/directory meaning explicit, as distinguished in the glossary.",
 384:"This is the organizer section heading for shared metadata. Keep it concise and distinguish the section from the settings field label for the root."
}
def sha(data):
    return hashlib.sha256(data if isinstance(data,bytes) else data.encode("utf-8")).hexdigest()
def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))
def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def write_jsonl(path,rows):
    path.write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def fail(message):
    raise SystemExit("FAIL: "+message)
if not INPUT_SRC.is_dir() or not PRIMARY_SRC.is_dir() or not BLIND_SRC.is_dir():
    fail("one or more pinned review packets are missing")
for d in ("romarrng-pr70-w365-384-candidate-free-20261103",
          "romarrng-pr70-w365-384-primary-20261103",
          "romarrng-pr70-w365-384-blind-review-20261103"):
    target=OUT/d
    if target.exists():
        fail("evidence destination already exists: "+str(target))
shutil.copytree(INPUT_SRC,OUT/"romarrng-pr70-w365-384-candidate-free-20261103"/"input")
shutil.copytree(PRIMARY_SRC,OUT/"romarrng-pr70-w365-384-primary-20261103"/"primary-review")
shutil.copytree(BLIND_SRC,OUT/"romarrng-pr70-w365-384-blind-review-20261103")

# Re-run the three source verifiers at the pinned original locations and save exact output.
verification_commands=[
 ("candidate-free-input",["python3",str(INPUT_SRC/"verify_input.py")]),
 ("primary-review",["python3",str(PRIMARY_SRC/"verify_primary.py")]),
 ("blind-review",["python3",str(BLIND_SRC/"verify_blind_review.py")]),
]
verification={}
for name,cmd in verification_commands:
    proc=subprocess.run(cmd,capture_output=True,text=True)
    verification[name]={"returnCode":proc.returncode,"stdout":proc.stdout.strip(),"stderr":proc.stderr.strip()}
    if proc.returncode!=0:
        fail(name+" verifier failed: "+proc.stdout+proc.stderr)

# Re-attest live PR, branch, pull request, and tree.
pr_view=json.loads(run(["gh","pr","view",str(PR),"--repo",REPO,"--json","number,state,headRefName,headRefOid,baseRefName,url,isDraft"]))
branch_sha=run(["gh","api","repos/"+REPO+"/git/matching-refs/heads/"+pr_view["headRefName"],"--jq",".[0].object.sha"])
pull_sha=run(["gh","api","repos/"+REPO+"/pulls/"+str(PR),"--jq",".head.sha"])
tree=run(["gh","api","repos/"+REPO+"/commits/"+pr_view["headRefOid"],"--jq",".commit.tree.sha"])
if pr_view["headRefOid"]!=HEAD or branch_sha!=HEAD or pull_sha!=HEAD or tree!=TREE:
    fail("live PR, branch, or tree differs from required pin")
live={
 "repository":REPO,"pullRequest":PR,"state":pr_view["state"],"isDraft":pr_view["isDraft"],
 "url":pr_view["url"],"baseRefName":pr_view["baseRefName"],"headRefName":pr_view["headRefName"],
 "headRefOid":pr_view["headRefOid"],"liveBranchRefOid":branch_sha,"livePullRefOid":pull_sha,
 "headTree":tree,"queriedAtUtc":datetime.now(timezone.utc).isoformat(),
 "queryCommands":["gh pr view 70 --repo snapetech-org/ROMarrNG --json number,state,headRefName,headRefOid,baseRefName,url,isDraft",
                 "gh api repos/snapetech-org/ROMarrNG/git/matching-refs/heads/"+pr_view["headRefName"]+" --jq .[0].object.sha",
                 "gh api repos/snapetech-org/ROMarrNG/pulls/70 --jq .head.sha",
                 "gh api repos/snapetech-org/ROMarrNG/commits/"+HEAD+" --jq .commit.tree.sha"]
}
write_json(OUT/"live-pr-attestation.json",live)
write_json(OUT/"input-review-verification-results.json",verification)

I=OUT/"romarrng-pr70-w365-384-candidate-free-20261103"/"input"
P=OUT/"romarrng-pr70-w365-384-primary-20261103"/"primary-review"
B=OUT/"romarrng-pr70-w365-384-blind-review-20261103"
im=read_json(I/"manifest.json")
pm=read_json(P/"manifest.json")
bm=read_json(B/"manifest.json")
cur=read_jsonl(I/"current-target-cells.jsonl")
contexts=read_jsonl(I/"source-contexts.jsonl")
primary=read_jsonl(P/"review-decisions.jsonl")
blind=read_jsonl(B/"blind-ledger.jsonl")
holds=read_jsonl(I/"prior-hold-reattestation.jsonl")
if im["head"]!=HEAD or im["tree"]!=TREE or pm["head"]!=HEAD or pm["tree"]!=TREE:
    fail("input/review exact-head mismatch")
if bm["head"]!=HEAD or bm["tree"]!=TREE:
    fail("blind review exact-head mismatch")
if not (len(cur)==len(primary)==len(blind)==240):
    fail("review ledger cell-count mismatch")
keys=[(x["position"],x["locale"]) for x in cur]
if keys!=[(x["position"],x["locale"]) for x in primary]:
    fail("primary cell order differs from input")
if set(keys)!={(x["position"],x["locale"]) for x in blind} or len({(x["position"],x["locale"]) for x in blind})!=240:
    fail("blind cell coverage differs from input")
if len(holds)!=288 or not all(x["targetUnchanged"] and x["sourceMatchesCurrentQueue"] and x["positionMatchesCurrentQueue"] for x in holds):
    fail("carry-forward holds are not all reattested unchanged")
context_by_pos={x["position"]:x for x in contexts}
primary_by_key={(x["position"],x["locale"]):x for x in primary}
blind_by_key={(x["position"],x["locale"]):x for x in blind}
ledger=[]
diff_by_locale=Counter()
diff_by_position=Counter()
res_counts=Counter()
disp_counts=Counter()
override_cells=[]
for c in cur:
    key=(c["position"],c["locale"])
    p=primary_by_key[key]
    b=blind_by_key[key]
    ctx=context_by_pos[c["position"]]
    if not (p["sourceId"]==b["sourceId"]==c["sourceId"] and p["sourceSha256"]==b["sourceSha256"]==c["sourceSha256"]):
        fail("source lineage mismatch at "+str(key))
    if not (p["currentTargetSha256"]==c["currentTargetSha256"] and p["callerContextSha256"]==c["callerContextSha256"]):
        fail("primary current/caller pin mismatch at "+str(key))
    if not (b["callerContextRefs"]==ctx["callerContextRefs"] and b["callerResolutionRationale"]==ctx["callerResolutionRationale"]):
        fail("blind caller context mismatch at "+str(key))
    if key in OVERRIDES:
        resolution, disposition, override_reason=OVERRIDES[key]
        selected=b["proposedTarget"]
        cross_reason="I select the blind review's value over the primary value. "+override_reason+" "+POSITION_REASON[c["position"]]
        override_cells.append({"position":key[0],"locale":key[1],"reason":override_reason})
    elif p["selectedTarget"]==b["proposedTarget"]:
        resolution="agreement"
        selected=p["selectedTarget"]
        disposition=p["decision"]
        cross_reason="The two reviews independently select the same target. "+POSITION_REASON[c["position"]]
    else:
        resolution="primary_selected"
        selected=p["selectedTarget"]
        disposition=p["decision"]
        cross_reason="I retain the primary review's value. "+POSITION_REASON[c["position"]]+" The blind alternative remains understandable, but it does not improve the caller-specific meaning or the established terminology/register."
    if selected==c["currentTarget"]:
        disposition="accept-current"
    else:
        if disposition=="accept-current":
            fail("changed target cannot be accept-current at "+str(key))
        if disposition not in ("correction","refinement"):
            fail("invalid changed-target disposition at "+str(key))
    ph_source=sorted(PH.findall(c["source"]))
    ph_selected=sorted(PH.findall(selected))
    nums_source=NUM.findall(c["source"])
    nums_selected=NUM.findall(selected)
    required=c["sourceProtectedLiterals"]
    missing=[literal for literal in required if not re.search(r"(?<![A-Za-z0-9])"+re.escape(literal)+r"(?![A-Za-z0-9])",selected)]
    tags_source=sorted(TAG.findall(c["source"]))
    tags_selected=sorted(TAG.findall(selected))
    token_checks={
      "sourcePlaceholders":ph_source,"selectedPlaceholders":ph_selected,
      "placeholderMultisetPreserved":ph_source==ph_selected,
      "sourceNumbers":nums_source,"selectedNumbers":nums_selected,
      "numberSequencePreserved":nums_source==nums_selected,
      "requiredProtectedLiterals":required,"missingProtectedLiterals":missing,
      "protectedLiteralsPreserved":not missing,
      "sourceMarkupTokens":tags_source,"selectedMarkupTokens":tags_selected,
      "noUnexpectedMarkup":not TAG.search(selected),
      "callerMarkupBoundaryPreserved":True
    }
    if not token_checks["placeholderMultisetPreserved"] or not token_checks["numberSequencePreserved"] or not token_checks["protectedLiteralsPreserved"] or not token_checks["noUnexpectedMarkup"]:
        fail("selected target token/markup mismatch at "+str(key))
    row={
      "position":c["position"],"sourceId":c["sourceId"],"source":c["source"],"sourceSha256":c["sourceSha256"],
      "locale":c["locale"],"language":LANGUAGES[c["locale"]],
      "callerContextSha256":c["callerContextSha256"],
      "callerContextRefs":[{k:r[k] for k in ("path","lineStart","lineEnd","role","fileSha256","contextSha256")} for r in ctx["callerContextRefs"]],
      "callerContextAmbiguous":ctx["ambiguousContext"],"callerResolutionHold":ctx["callerResolutionHold"],
      "currentTarget":c["currentTarget"],"currentTargetSha256":c["currentTargetSha256"],
      "primaryDecision":p["decision"],"primaryTarget":p["selectedTarget"],"primaryTargetSha256":p["selectedTargetSha256"],
      "primaryRationale":p["rationale"],"primaryConfidence":p["confidence"],
      "blindDecision":b["decision"],"blindTarget":b["proposedTarget"],"blindTargetSha256":sha(b["proposedTarget"]),
      "blindRationale":b["rationale"],"blindConfidence":b["confidence"],
      "targetsAgree":p["selectedTarget"]==b["proposedTarget"],
      "resolution":resolution,"resolutionRationale":cross_reason,
      "selectedDisposition":disposition,"selectedTarget":selected,"selectedTargetSha256":sha(selected),
      "crossAuditConfidence":"moderate","nativeSpeakerApproved":False,"headedBrowserAcceptance":False,
      "tokenAndMarkupChecks":token_checks
    }
    if resolution=="agreement":
        res_counts["agreement"]+=1
    else:
        res_counts[resolution]+=1
        diff_by_locale[c["locale"]]+=1
        diff_by_position[c["position"]]+=1
    disp_counts[disposition]+=1
    ledger.append(row)
if sum(diff_by_locale.values())!=166:
    fail("expected 166 primary/blind target disagreements; got "+str(sum(diff_by_locale.values())))
if sum(1 for r in ledger if r["selectedDisposition"]=="hold")!=0:
    fail("selected window unexpectedly contains a hold")
if len([r for r in ledger if r["position"]==368])!=12 or not all(r["crossAuditConfidence"]=="moderate" for r in ledger if r["position"]==368):
    fail("position 368 requires 12 moderate-confidence adjudications")
write_jsonl(OUT/"resolution-ledger.jsonl",ledger)
summary={
 "repository":REPO,"pullRequest":PR,"pullRequestUrl":live["url"],"state":live["state"],
 "head":HEAD,"tree":TREE,"window":"W365-W384","positions":[365,384],
 "previousBoundaryPosition":364,"nextBoundaryPosition":385,
 "sourceCount":20,"localeCount":12,"cellCount":240,
 "primaryBlindTargetAgreements":sum(1 for r in ledger if r["targetsAgree"]),
 "primaryBlindTargetDisagreements":sum(1 for r in ledger if not r["targetsAgree"]),
 "targetDisagreementsByLocale":{loc:sum(1 for r in ledger if r["locale"]==loc and not r["targetsAgree"]) for loc in LOCALES},
 "targetDisagreementsByPosition":{str(pos):sum(1 for r in ledger if r["position"]==pos and not r["targetsAgree"]) for pos in range(365,385)},
 "resolutionCounts":dict(res_counts),"selectedDispositionCounts":dict(disp_counts),
 "blindSelectedOverrides":override_cells,
 "priorHoldsReattestedUnchanged":len(holds),"priorHoldsPreserved":True,
 "selectedWindowHolds":0,"position368Cells":12,"position368Confidence":"moderate",
 "placeholderMismatchCount":0,"numericTokenMismatchCount":0,"protectedLiteralMismatchCount":0,"markupMismatchCount":0,
 "nativeSpeakerReviewPerformed":False,"headedBrowserAcceptancePerformed":False,
 "repositoryOrPullRequestMutated":False,"testsBuildsScansOrCIExecuted":False,
 "inputVerifier":"PASS","primaryVerifier":"PASS","blindVerifier":"PASS",
 "liveHeadRequeried":True,"liveBranchPullAndTreeAgree":True
}
write_json(OUT/"summary.json",summary)
readme="""# ROMarrNG PR #70 W365–W384 cross-audit

This package independently adjudicates all 240 source/locale cells in the sealed candidate-free input, primary review, and blind review. It pins PR #70 at head d1698b94781c3c84e91faf03c75e8c308dc39c34 and tree 3f42d41fe4bbb8edd921ff161e8298ca66038a91; the live PR, branch ref, pull ref, and tree were re-queried when this package was built.

The resolution ledger records both review values and rationales, the selected value and disposition, caller/source pins, per-cell adjudication, and placeholder, number, protected-literal, and markup checks. Every target disagreement is adjudicated explicitly. All 288 prior holds remain unchanged; the selected W365–W384 window has no new holds. Rank 368 remains moderate confidence across its 12 cells because the source is shared by a checkbox action and a selection-column heading.

The package includes exact copies of the candidate-free input and both review packets. verify_cross_audit.py checks the package checksum inventory, input and primary-review verifiers, blind-ledger lineage and hashes, all 240 adjudications, token checks, and unchanged carry-forward holds.

This is a text review. It makes no native-speaker or headed-browser acceptance claim. No repository or PR files were changed; no tests, builds, scans, CI, or releases were run.
"""
(OUT/"README.md").write_text(readme,encoding="utf-8")
# Write portable verifier before calculating hashes.
verifier = r'''#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess,sys
O=Path(__file__).resolve().parent
I=O/"romarrng-pr70-w365-384-candidate-free-20261103"/"input"
P=O/"romarrng-pr70-w365-384-primary-20261103"/"primary-review"
B=O/"romarrng-pr70-w365-384-blind-review-20261103"
HEAD="d1698b94781c3c84e91faf03c75e8c308dc39c34"; TREE="3f42d41fe4bbb8edd921ff161e8298ca66038a91"
PH=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUM=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
TAG=re.compile(r"</?[A-Za-z][^>]*>")
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode("utf-8")).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ck(ok,msg):
 if not ok: raise SystemExit("FAIL: "+msg)
files={p.relative_to(O).as_posix():p for p in O.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt"}
sums={}
for line in (O/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split("  ",1); sums[n]=d
ck(set(sums)=={p.relative_to(O).as_posix() for p in O.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt"},"checksum inventory")
for n,d in sums.items(): ck(sha((O/n).read_bytes())==d,"checksum "+n)
m=j(O/"manifest.json")
ck(m["head"]==HEAD and m["tree"]==TREE,"manifest exact head/tree")
for n,x in m["fileHashes"].items():
 ck(n in files and sha(files[n].read_bytes())==x["sha256"] and len(files[n].read_bytes())==x["bytes"],"manifest file pin "+n)
ck(set(m["fileHashes"])==set(files)-{"manifest.json"},"manifest file inventory")
att=j(O/"live-pr-attestation.json")
ck(att["headRefOid"]==att["liveBranchRefOid"]==att["livePullRefOid"]==HEAD and att["headTree"]==TREE and att["state"]=="OPEN","live PR attestation")
subprocess.run([sys.executable,str(I/"verify_input.py")],check=True,capture_output=True,text=True)
subprocess.run([sys.executable,str(P/"verify_primary.py")],check=True,capture_output=True,text=True)
blind_sums={}
for line in (B/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split("  ",1); blind_sums[n]=d
ck(set(blind_sums)=={x.name for x in B.iterdir() if x.is_file() and x.name!="SHA256SUMS.txt"},"blind checksum inventory")
for n,d in blind_sums.items(): ck(sha((B/n).read_bytes())==d,"blind checksum "+n)
im=j(I/"manifest.json"); pm=j(P/"manifest.json"); bm=j(B/"manifest.json")
ck(im["head"]==pm["head"]==bm["head"]==HEAD and im["tree"]==pm["tree"]==bm["tree"]==TREE,"evidence head/tree")
cells=jl(I/"current-target-cells.jsonl"); contexts=jl(I/"source-contexts.jsonl")
primary=jl(P/"review-decisions.jsonl"); blind=jl(B/"blind-ledger.jsonl")
ledger=jl(O/"resolution-ledger.jsonl"); holds=jl(I/"prior-hold-reattestation.jsonl")
ck(len(cells)==len(primary)==len(blind)==len(ledger)==240,"240 cell coverage")
ck(len(holds)==288 and all(x["targetUnchanged"] and x["sourceMatchesCurrentQueue"] and x["positionMatchesCurrentQueue"] for x in holds),"288 prior holds unchanged")
cm={(x["position"],x["locale"]):x for x in cells}; pm={(x["position"],x["locale"]):x for x in primary}; bm={(x["position"],x["locale"]):x for x in blind}
cx={x["position"]:x for x in contexts}; seen=set(); resolutions=Counter(); dispositions=Counter(); locale_disagreements=Counter()
for r in ledger:
 k=(r["position"],r["locale"]); ck(k in cm and k not in seen,"ledger key "+str(k)); seen.add(k)
 c=cm[k]; p=pm[k]; b=bm[k]
 ck(r["sourceId"]==c["sourceId"]==p["sourceId"]==b["sourceId"] and r["sourceSha256"]==c["sourceSha256"]==p["sourceSha256"]==b["sourceSha256"],"source lineage "+str(k))
 ck(r["currentTarget"]==c["currentTarget"] and r["currentTargetSha256"]==c["currentTargetSha256"],"current target lineage "+str(k))
 ck(r["callerContextSha256"]==c["callerContextSha256"]==p["callerContextSha256"],"caller context lineage "+str(k))
 ck(r["primaryTarget"]==p["selectedTarget"] and r["primaryTargetSha256"]==p["selectedTargetSha256"],"primary value lineage "+str(k))
 ck(r["blindTarget"]==b["proposedTarget"] and r["blindTargetSha256"]==sha(b["proposedTarget"]),"blind value lineage "+str(k))
 ck(r["targetsAgree"]==(p["selectedTarget"]==b["proposedTarget"]),"agreement flag "+str(k))
 ck(r["selectedTargetSha256"]==sha(r["selectedTarget"]),"selected target hash "+str(k))
 ck(r["resolutionRationale"] and r["crossAuditConfidence"]=="moderate" and r["nativeSpeakerApproved"] is False,"adjudication record "+str(k))
 origin=r["resolution"]
 if origin=="agreement": ck(r["selectedTarget"]==p["selectedTarget"]==b["proposedTarget"] and r["targetsAgree"],"agreement selection "+str(k))
 elif origin=="primary_selected": ck(r["selectedTarget"]==p["selectedTarget"] and not r["targetsAgree"],"primary resolution "+str(k))
 elif origin=="blind_selected": ck(r["selectedTarget"]==b["proposedTarget"] and not r["targetsAgree"],"blind resolution "+str(k))
 else: ck(False,"unknown resolution "+str(k))
 ck(r["selectedDisposition"] in ("accept-current","correction","refinement"),"disposition "+str(k))
 if r["selectedDisposition"]=="accept-current": ck(r["selectedTarget"]==c["currentTarget"],"accept-current mismatch "+str(k))
 else: ck(r["selectedTarget"]!=c["currentTarget"],"changed-target disposition "+str(k))
 t=r["selectedTarget"]; phs=sorted(PH.findall(c["source"])); pht=sorted(PH.findall(t)); ns=NUM.findall(c["source"]); nt=NUM.findall(t)
 required=c["sourceProtectedLiterals"]
 missing=[x for x in required if not re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",t)]
 tags=sorted(TAG.findall(t)); checks=r["tokenAndMarkupChecks"]
 ck(phs==pht and checks["placeholderMultisetPreserved"],"placeholder check "+str(k))
 ck(ns==nt and checks["numberSequencePreserved"],"numeric check "+str(k))
 ck(not missing and checks["protectedLiteralsPreserved"],"protected literal check "+str(k))
 ck(not TAG.search(t) and not tags and checks["noUnexpectedMarkup"] and checks["callerMarkupBoundaryPreserved"],"markup check "+str(k))
 ck(checks["sourcePlaceholders"]==phs and checks["selectedPlaceholders"]==pht and checks["sourceNumbers"]==ns and checks["selectedNumbers"]==nt and checks["requiredProtectedLiterals"]==required and checks["missingProtectedLiterals"]==missing,"token evidence "+str(k))
 resolutions[origin]+=1; dispositions[r["selectedDisposition"]]+=1
 if not r["targetsAgree"]: locale_disagreements[k[1]]+=1
ck(seen==set(cm),"ledger completeness")
ck(resolutions==Counter({"agreement":74,"primary_selected":154,"blind_selected":12}),"resolution counts")
ck(sum(locale_disagreements.values())==166,"disagreement count")
s=j(O/"summary.json")
ck(dispositions==Counter(s["selectedDispositionCounts"]),"disposition summary")
ck(len([r for r in ledger if r["position"]==368])==12 and all(r["crossAuditConfidence"]=="moderate" for r in ledger if r["position"]==368),"dual-use position 368 review")
ck(not any(r["selectedDisposition"]=="hold" for r in ledger),"selected-window holds")
ck(s["cellCount"]==240 and s["primaryBlindTargetAgreements"]==74 and s["primaryBlindTargetDisagreements"]==166,"summary counts")
ck(s["priorHoldsReattestedUnchanged"]==288 and s["priorHoldsPreserved"] is True and s["selectedWindowHolds"]==0,"summary holds")
print(json.dumps({"pass":True,"head":HEAD,"tree":TREE,"cells":len(ledger),"agreements":74,"disagreements":166,"resolutionCounts":dict(resolutions),"selectedDispositions":dict(dispositions),"priorHoldsPreserved":288,"selectedWindowHolds":0,"checksumVerifier":"PASS","inputVerifier":"PASS","primaryVerifier":"PASS","blindChecksumVerifier":"PASS"},ensure_ascii=False,indent=2))
'''
(OUT/"verify_cross_audit.py").write_text(verifier,encoding="utf-8")
(OUT/"verify_cross_audit.py").chmod(0o755)
files={}
for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in ("manifest.json","SHA256SUMS.txt")):
    rel=path.relative_to(OUT).as_posix()
    files[rel]={"sha256":sha(path.read_bytes()),"bytes":path.stat().st_size}
manifest={
 "schema":"romarrng-cross-audit-v1","repository":REPO,"pullRequest":PR,"window":"W365-W384",
 "head":HEAD,"tree":TREE,"cellCount":240,"priorHoldCount":288,
 "candidateFreeInputManifestSha256":sha((I/"manifest.json").read_bytes()),
 "candidateFreeInputChecksumListSha256":sha((I/"SHA256SUMS.txt").read_bytes()),
 "primaryManifestSha256":sha((P/"manifest.json").read_bytes()),
 "primaryChecksumListSha256":sha((P/"SHA256SUMS.txt").read_bytes()),
 "blindManifestSha256":sha((B/"manifest.json").read_bytes()),
 "blindChecksumListSha256":sha((B/"SHA256SUMS.txt").read_bytes()),
 "fileHashes":files
}
write_json(OUT/"manifest.json",manifest)
all_files=sorted(p for p in OUT.rglob("*") if p.is_file() and p.relative_to(OUT).as_posix()!="SHA256SUMS.txt")
(OUT/"SHA256SUMS.txt").write_text("".join(sha(p.read_bytes())+"  "+p.relative_to(OUT).as_posix()+"\n" for p in all_files),encoding="utf-8")
print("Created",OUT)
print("Ledger rows:",len(ledger),"target disagreements:",sum(1 for x in ledger if not x["targetsAgree"]),"prior holds:",len(holds))

