#!/usr/bin/env python3
import hashlib,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path("/mnt/datapool_lvm_media/codex-task-scratch/romarrng-pr70-w166-185-cross-audit-20261103")
PRIMARY=Path("/mnt/datapool_lvm_media/codex-task-scratch/romarrng-pr70-w166-185-20261103")
BLIND=ROOT/"independent-blind"
REPO="snapetech-org/ROMarrNG"
HEAD="5e45ce90babf3cf385fbb9775e70d7e8fcc6a783"
TREE="580de0b2db5030101c47a81fbd8a23489e993f75"
LOCALES=["es","zh-Hans","hi","de","ja","fr","pt-BR","ar","ko","zh-Hant","vi","id"]
PH=re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
PRIORITY={"correction":3,"refinement":2,"accept-current":1,"hold":0,"hold-context":0}
OVERRIDE_SELECT={
 (166,"ar"):"blind",
 (170,"ar"):"blind",
 (176,"es"):"blind",
 (176,"vi"):"primary",
 (176,"id"):"blind",
 (179,"fr"):"blind",
 (181,"zh-Hans"):"primary",
 (181,"zh-Hant"):"primary",
 (182,"ar"):"blind",
 (183,"ko"):"blind",
 (183,"zh-Hant"):"blind",
 (183,"id"):"blind",
}
DISPOSITION_OVERRIDE={
 (170,"ja"):"refinement",(170,"ar"):"correction",(170,"ko"):"refinement",(170,"vi"):"correction",
 (171,"hi"):"correction",
 (172,"zh-Hans"):"refinement",(172,"de"):"correction",(172,"zh-Hant"):"refinement",
 (174,"de"):"correction",
 (176,"es"):"correction",(176,"hi"):"correction",(176,"vi"):"correction",(176,"id"):"correction",
 (178,"id"):"refinement",
 (179,"fr"):"correction",(179,"pt-BR"):"refinement",
 (181,"zh-Hans"):"refinement",(181,"zh-Hant"):"refinement",
 (182,"es"):"refinement",(182,"hi"):"refinement",(182,"ja"):"correction",(182,"pt-BR"):"refinement",(182,"ar"):"correction",(182,"vi"):"correction",
 (183,"es"):"refinement",(183,"ko"):"correction",(183,"zh-Hant"):"refinement",(183,"id"):"correction",
 (185,"zh-Hans"):"refinement",(185,"zh-Hant"):"refinement",(185,"ar"):"correction",(185,"ko"):"correction",
}
WHY={
 (166,"ar"):"At romarr/app.py:5124-5126 the template binds separate item, source, and grabbed counts. The independent wording labels the two quantities explicitly; it is clearer than the compressed current clause and retains every placeholder.",
 (170,"ja"):"romarr/ui.py:5663-5664 places this heading above the game-library inventory items. ゲームライブラリ一覧 is a natural section heading for that list and avoids a transliterated warehouse-style term.",
 (170,"ar"):"romarr/ui.py:5663-5664 places this heading over the library item list. قائمة الألعاب في المكتبة describes the user-facing content directly; مخزون can suggest stock.",
 (170,"ko"):"romarr/ui.py:5663-5664 labels a list of the user's library items. 게임 라이브러리 목록 is clearer than an English-derived inventory loanword.",
 (170,"vi"):"romarr/ui.py:5663-5664 heads the library inventory list. Danh sách trò chơi trong thư viện states what the screen lists and avoids the awkward audit sense of kiểm kê.",
 (171,"hi"):"The API reports this while the configured game library is loading (romarr/app.py:7148). The glossary defines Library as the user's game collection; गेम लाइब्रेरी avoids the public-library reading of पुस्तकालय.",
 (172,"zh-Hans"):"This error concerns unavailable ownership information for games in the library, not ownership of the library itself. The ownership lookup fallback is used at romarr/ui.py:2374 and 2482; the primary proposal states that meaning directly.",
 (172,"de"):"The ownership lookup fallback at romarr/ui.py:2374 and 2482 concerns games in the collection. Der Besitzstatus der Spiele in der Bibliothek lässt sich nicht ermitteln removes the ambiguity that the current compound describes ownership of the library.",
 (172,"zh-Hant"):"The fallback at romarr/ui.py:2374 and 2482 is about ownership data for games in the library. The primary wording says that directly rather than implying ownership of the library as a whole.",
 (174,"de"):"The UI formats an endpoint/library reachability diagnostic at romarr/ui.py:1065-1067. Nicht erreichbar is idiomatic for unreachable; unzugänglich suggests inaccessible.",
 (176,"es"):"romarr/ui.py:5754 uses this as a compact multi-disc classification with a review cue. The independent wording translates the term naturally and preserves both likelihood and review.",
 (176,"hi"):"romarr/ui.py:5754 uses this as a likely multi-disc classification requiring review. The independent proposal translates the English-heavy set label and preserves uncertainty.",
 (176,"vi"):"At romarr/ui.py:5754 the label marks a likely set for review. Có khả năng là preserves the stronger likelihood cue more closely than Có thể là; cần xem lại translates the action.",
 (176,"id"):"romarr/ui.py:5754 is a status label, not a rating. The independent wording makes the multi-disc meaning and review-needed status explicit in Indonesian.",
 (178,"id"):"Both reviews propose the same label for the hours field at romarr/ui.py:4475. It fixes the current awkward word order and spacing; retain refinement rather than correction because the current wording remains understandable.",
 (179,"fr"):"romarr/ui.py:2537 pairs List view with Cover view as a display-mode button. Vue en liste is the concise, parallel label; Affichage en liste is also understandable.",
 (179,"pt-BR"):"romarr/ui.py:2537 labels a display mode beside Cover view. Visualização em lista names the mode more naturally than the current Visão da lista, which reads as a view of a particular list.",
 (181,"zh-Hans"):"romarr/ui.py:2536 labels the DAT source filter for verified ROM dump names. The glossary preserves DAT and distinguishes ROM dumps from game titles; the primary proposal keeps that ROM context explicit.",
 (181,"zh-Hant"):"romarr/ui.py:2536 labels the DAT source filter for verified ROM dump names. The glossary preserves DAT and distinguishes ROM dumps from game titles; the primary proposal keeps that ROM context explicit.",
 (182,"es"):"romarr/ui.py:5664 is the loading empty-state immediately below the Library inventory heading. Cargando el inventario is a natural status phrase; the heading supplies the library context.",
 (182,"hi"):"romarr/ui.py:5664 is the loading state below the game-library inventory heading. The independent wording makes the game-library list explicit and avoids the English-heavy inventario.",
 (182,"ja"):"romarr/ui.py:5664 is a loading state below the library inventory heading. ライブラリ一覧を読み込み中 is a natural status line in that established screen context.",
 (182,"pt-BR"):"romarr/ui.py:5664 is a loading state below the Library inventory heading. Carregando o inventário is natural Brazilian Portuguese status copy.",
 (182,"ar"):"romarr/ui.py:5664 is the loading state beneath the library inventory heading. قائمة الألعاب في المكتبة describes the contents plainly and reads more naturally than جرد for a loading status.",
 (182,"vi"):"romarr/ui.py:5664 is the loading state for the library item list. The independent wording names the game list directly and reads naturally as a status.",
 (183,"es"):"Both reviews propose the same count label for status.local_metadata_imported at romarr/ui.py:5726. The count-after-description order is clear; classify as refinement because the current target is intelligible but incomplete-sounding.",
 (183,"ko"):"romarr/ui.py:5726 passes a formatted record count into a metric label. 재사용된 로컬 ES-DE 레코드: {count} reads naturally as a passive description of reused records.",
 (183,"zh-Hant"):"romarr/ui.py:5726 renders a count of local metadata records. The independent order, 本機 ES-DE 記錄, reads naturally as local ES-DE records and places the count clearly.",
 (183,"id"):"romarr/ui.py:5726 labels the count of reused local metadata records. Entri is more precise for records/entries than Catatan in this software context.",
 (185,"zh-Hans"):"romarr/app.py:7547-7550 formats a failed lookup with an error-type placeholder and the exact selected message key. 查询失败 describes a lookup/query more closely than 搜索失败.",
 (185,"zh-Hant"):"romarr/app.py:7547-7550 formats a failed lookup with an error-type placeholder and the exact selected message key. 查詢失敗 describes a lookup/query more closely than 搜索失敗.",
 (185,"ar"):"romarr/app.py:7547-7550 keys this as the error-type lookup diagnostic. The shared proposal corrects Arabic word order from البحث فشل to فشل البحث.",
 (185,"ko"):"romarr/app.py:7547-7550 keys this as the error-type lookup diagnostic. The shared proposal removes the nonstandard space before the colon.",
}
GENERIC={
 "both-accept":"Both independent reviews accept the current target. Keep it under the pinned source and caller context.",
 "same-proposal":"Both ledgers propose the same target. Ratify the shared target after the recorded placeholder and protected-term checks.",
 "primary-only":"The primary proposal is clearer under the pinned caller context; ratify it.",
 "blind-only":"The independent proposal is clearer under the pinned caller context; ratify it.",
 "different":"Resolve the competing targets using the row-specific rationale and exact caller context recorded here.",
 "hold":"Both reviews hold this locale; keep it held without a candidate."
}
def gh(ep): return subprocess.check_output(["gh","api",ep])
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())
def jl(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def verify_sums(directory,filename="SHA256SUMS.txt"):
 for line in (directory/filename).read_text(encoding="utf-8").splitlines():
  digest,rel=line.split("  ",1)
  if sha((directory/rel).read_bytes())!=digest: raise RuntimeError("checksum mismatch "+str(directory/rel))
def forms(x):
 if isinstance(x,str): return [x]
 if isinstance(x,dict) and x.get("kind")=="plural" and isinstance(x.get("forms"),dict): return list(x["forms"].values())
 raise RuntimeError("unexpected target shape")
def tokens(x): return sorted({p for f in forms(x) for p in PH.findall(f)})
def terms_ok(x,terms): return all(any(t in f for f in forms(x)) for t in terms)
def writej(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def writejl(path,rows): path.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for x in rows),encoding="utf-8")
def checksum_tree(directory,exclude):
 rows=[]
 for p in sorted(x for x in directory.rglob("*") if x.is_file() and x.relative_to(directory).as_posix() not in exclude):
  rows.append(f"{sha(p.read_bytes())}  {p.relative_to(directory).as_posix()}\n")
 return "".join(rows)
def file_records(directory,exclude):
 return [{"name":p.relative_to(directory).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(x for x in directory.rglob("*") if x.is_file() and x.relative_to(directory).as_posix() not in exclude)]

# Validate packet checksums and exact source/current input before adjudicating.
verify_sums(BLIND); verify_sums(BLIND/"input"); verify_sums(PRIMARY/"input"); verify_sums(PRIMARY/"primary-private")
p_in=jl(PRIMARY/"input/review-input.jsonl"); b_in=jl(BLIND/"input/review-input.jsonl")
p_ledger=jl(PRIMARY/"primary-private/review-decisions.jsonl"); b_ledger=jl(BLIND/"blind-review.jsonl")
if not(len(p_in)==len(b_in)==len(p_ledger)==len(b_ledger)==240): raise RuntimeError("expected four 240-row ledgers")
pmap={(x["id"],x["locale"]):x for x in p_ledger}; bmap={(x["id"],x["locale"]):x for x in b_ledger}
pinput={(x["id"],x["locale"]):x for x in p_in}; binput={(x["id"],x["locale"]):x for x in b_in}
if set(pmap)!=set(bmap) or set(pmap)!=set(pinput) or set(bmap)!=set(binput): raise RuntimeError("cell key sets differ")
for key in sorted(pinput):
 x,y=pinput[key],binput[key]; p=pmap[key]; b=bmap[key]
 for field in ("sourceOrdinal","source","sourceSha256","currentTarget","currentTargetSha256","translationStatus"):
  if x.get(field)!=y.get(field): raise RuntimeError(f"candidate-free input mismatch {key}/{field}")
 for row in (p,b):
  for field in ("sourceOrdinal","source","sourceSha256","currentTarget","currentTargetSha256","translationStatus","callerExists"):
   if row.get(field)!=x.get(field): raise RuntimeError(f"review/input pin mismatch {key}/{field}")
 if canon(x["currentTarget"])!=x["currentTargetSha256"] or x["storedTranslationHash"]!=x["currentTargetSha256"]:
  raise RuntimeError(f"current target hash mismatch {key}")
 if p["outcome"] in ("accept-current","hold-context") and p.get("suggestedTarget") is not None:
  raise RuntimeError(f"unexpected primary proposal {key}")
 if p["outcome"] in ("correction","refinement") and p.get("suggestedTarget") is None:
  raise RuntimeError(f"missing primary proposal {key}")
 if b["disposition"] in ("accept-current","hold") and b.get("proposedTarget") is not None:
  raise RuntimeError(f"unexpected independent proposal {key}")
 if b["disposition"] in ("correction","refinement") and b.get("proposedTarget") is None:
  raise RuntimeError(f"missing independent proposal {key}")
pctx=jl(PRIMARY/"input/source-context.jsonl"); bctx=jl(BLIND/"input/source-context.jsonl")
pstruct=jl(PRIMARY/"input/source-structure.jsonl"); bstruct=jl(BLIND/"input/source-structure.jsonl")
prender=jl(PRIMARY/"input/render-path-context.jsonl"); brender=jl(BLIND/"input/render-path-context.jsonl")
if pctx!=bctx or pstruct!=bstruct or prender!=brender: raise RuntimeError("candidate-free source/caller context differs between packets")
p_pins=json.loads((PRIMARY/"input/head-and-file-pins.json").read_text())
b_pins=json.loads((BLIND/"input/head-and-file-pins.json").read_text())
if p_pins.get("head")!=HEAD or b_pins.get("head")!=HEAD or p_pins.get("tree")!=TREE or b_pins.get("tree")!=TREE:
 raise RuntimeError("packet head/tree pin mismatch")
if p_pins.get("filePins")!=b_pins.get("filePins"): raise RuntimeError("file pin sets differ")
source_by_ord={x["sourceOrdinal"]:x for x in pstruct}
ctx_by_ord={x["sourceOrdinal"]:x for x in pctx}
# Check every proposal's canonical hash, source placeholder set, and protected literal set.
p_changes=[]; b_changes=[]
for key in sorted(pmap):
 p=pmap[key]; b=bmap[key]; src=p["source"]; required=sorted(set(PH.findall(src))); terms=source_by_ord[p["sourceOrdinal"]]["sourceProtectedLiterals"]
 if p.get("targetChanges"):
  t=p.get("suggestedTarget")
  if t is None or p.get("suggestedTargetSha256")!=canon(t): raise RuntimeError(f"primary target hash mismatch {key}")
  if tokens(t)!=required or not terms_ok(t,terms): raise RuntimeError(f"primary target structure mismatch {key}")
  p_changes.append(key)
 bt=b.get("proposedTarget")
 if bt is not None:
  if b.get("proposedTargetSha256")!=canon(bt): raise RuntimeError(f"independent target hash mismatch {key}")
  if tokens(bt)!=required or not terms_ok(bt,terms): raise RuntimeError(f"independent target structure mismatch {key}")
  b_changes.append(key)
if len(p_changes)!=27 or len(b_changes)!=37: raise RuntimeError("proposal counts differ from packet summaries")
for ordinal in (177,184):
 cells=[key for key in pmap if pmap[key]["sourceOrdinal"]==ordinal]
 if len(cells)!=12: raise RuntimeError(f"hold count mismatch {ordinal}")
 for key in cells:
  if pmap[key]["outcome"]!="hold-context" or bmap[key]["disposition"]!="hold" or pmap[key].get("suggestedTarget") is not None or bmap[key].get("proposedTarget") is not None:
   raise RuntimeError(f"held cell mismatch {key}")
# Fresh live PR check.
pr=json.loads(gh(f"repos/{REPO}/pulls/70"))
head=pr["head"]["sha"]; tree=json.loads(gh(f"repos/{REPO}/git/commits/{head}"))["tree"]["sha"]
if not(pr["state"]=="open" and pr["draft"] is True and pr["head"]["ref"]=="task/localization-translation-review-20261030" and head==HEAD and tree==TREE and pr["base"]["ref"]=="main"):
 raise RuntimeError("live PR no longer matches exact packet pin")
live={"checkedAtUtc":datetime.now(timezone.utc).isoformat(),"state":pr["state"],"draft":pr["draft"],"branch":pr["head"]["ref"],"head":head,"tree":tree,"base":pr["base"]["ref"],"updatedAt":pr["updated_at"],"unchangedFromBothPackets":True}
writej(ROOT/"live-pr-recheck.json",live)
# Root's cell-level adjudication: keep the 24 no-candidate holds, otherwise reconcile the two proposals.
root_rows=[]; mismatch_rows=[]
for key in sorted(pmap,key=lambda k:(pmap[k]["sourceOrdinal"],LOCALES.index(k[1]))):
 p=pmap[key]; b=bmap[key]; inp=pinput[key]; ordinal=p["sourceOrdinal"]; cell=(ordinal,p["locale"])
 pt=p.get("suggestedTarget") if p.get("targetChanges") else None
 bt=b.get("proposedTarget")
 pd=p["outcome"]; bd=b["disposition"]
 if ordinal in (177,184):
  final=None; disp="hold-context"; relation="both-hold"; reason=(
   "Keep all 12 locales held. " + (ctx_by_ord[ordinal].get("renderPathQuestion") or ctx_by_ord[ordinal].get("unmappedSourceFinding") or "Both reviews withheld candidates.")
  )
 elif pt is None and bt is None:
  final=inp["currentTarget"]; disp="accept-current"; relation="both-accept"; reason=GENERIC["both-accept"]
 elif pt is not None and bt is not None and pt==bt:
  final=pt; relation="same-proposal"
  disp=DISPOSITION_OVERRIDE.get(cell, pd if pd in ("correction","refinement") else bd)
  reason=WHY.get(cell,GENERIC["same-proposal"])
  if pd!=bd: relation="same-proposal-disposition-diff"
 elif pt is not None and bt is not None:
  if cell not in OVERRIDE_SELECT: raise RuntimeError(f"unresolved competing proposals {key}")
  final=pt if OVERRIDE_SELECT[cell]=="primary" else bt
  disp=DISPOSITION_OVERRIDE.get(cell, pd if OVERRIDE_SELECT[cell]=="primary" else bd)
  relation="different-proposals"
  reason=WHY.get(cell,GENERIC["different"])
 elif pt is not None:
  final=pt; disp=DISPOSITION_OVERRIDE.get(cell,pd); relation="primary-only-proposal"
  reason=WHY.get(cell,GENERIC["primary-only"])
 else:
  final=bt; disp=DISPOSITION_OVERRIDE.get(cell,bd); relation="independent-only-proposal"
  reason=WHY.get(cell,GENERIC["blind-only"])
 changed=final is not None and final!=inp["currentTarget"]
 st=sorted(set(PH.findall(inp["source"])))
 ft=tokens(final) if final is not None else None
 terms=source_by_ord[ordinal]["sourceProtectedLiterals"]
 checks={"sourceTokens":st,"finalTokens":ft,"placeholderParity":final is None or ft==st,
         "requiredProtectedLiterals":terms,"protectedLiteralsPreserved":final is None or terms_ok(final,terms)}
 if not checks["placeholderParity"] or not checks["protectedLiteralsPreserved"]:
  raise RuntimeError(f"root candidate structure mismatch {key}")
 refs=p.get("callerRefs",[])
 for ref in refs:
  pin=p_pins["filePins"].get(ref["path"])
  if not pin or pin["sha256"]!=ref["fileSha256"]: raise RuntimeError(f"caller reference file pin mismatch {key}/{ref['path']}")
 context_evidence={
  "callerExists":p["callerExists"],
  "sourceContextResolved":p["sourceContextResolved"],
  "sourceContextStatus":p["sourceContextStatus"],
  "callerRefs":refs,
  "ambiguousDynamicTemplateMatches":ctx_by_ord[ordinal].get("ambiguousDynamicTemplateMatches",[]) if ordinal==184 else [],
  "sourceMapHintVerification":ctx_by_ord[ordinal].get("sourceMapHintVerification",[]),
 }
 row={
  "id":p["id"],"locale":p["locale"],"sourceOrdinal":ordinal,"source":inp["source"],
  "sourceSha256":inp["sourceSha256"],"currentTarget":inp["currentTarget"],
  "currentTargetSha256":inp["currentTargetSha256"],"translationStatus":inp["translationStatus"],
  "primaryDisposition":pd,"primaryTarget":pt,"primaryTargetSha256":p.get("suggestedTargetSha256") if pt is not None else None,
  "independentDisposition":bd,"independentTarget":bt,"independentTargetSha256":b.get("proposedTargetSha256"),
  "comparison":relation,"adjudicatedDisposition":disp,"adjudicatedTarget":final,
  "adjudicatedTargetSha256":canon(final) if final is not None else None,"targetChanges":changed,
  "adjudicationRationale":reason,"structureChecks":checks,"exactCallerContext":context_evidence,
  "nativeSpeakerApproved":False,
 }
 root_rows.append(row)
 if pd!=bd or pt!=bt:
  mismatch_rows.append({
   "id":p["id"],"locale":p["locale"],"sourceOrdinal":ordinal,
   "primaryDisposition":pd,"primaryTarget":pt,"independentDisposition":bd,"independentTarget":bt,
   "holdEquivalent":ordinal in (177,184),"rootDisposition":disp,"rootTarget":final,
   "rootRationale":reason,"callerRefs":refs,
  })
# Cross-ledger agreement diagnostics.
from collections import Counter
raw_diff=len(mismatch_rows)
semantic_nonhold=sum(1 for r in mismatch_rows if not r["holdEquivalent"])
same_target_label_diff=sum(1 for r in mismatch_rows if not r["holdEquivalent"] and r["primaryTarget"]==r["independentTarget"])
target_recommendation_diffs=sum(1 for r in mismatch_rows if not r["holdEquivalent"] and r["primaryTarget"]!=r["independentTarget"])
root_counts=Counter(x["adjudicatedDisposition"] for x in root_rows)
root_changes=[x for x in root_rows if x["targetChanges"]]
if raw_diff!=57 or semantic_nonhold!=33 or len(root_rows)!=240 or len(root_changes)!=len(set(p_changes)|set(b_changes)):
 raise RuntimeError(f"cross-review count mismatch diff={raw_diff}, nonhold={semantic_nonhold}, rootchanges={len(root_changes)}")
# Validate all rows remain in source queue and root holds are exact.
if Counter(x["sourceOrdinal"] for x in root_rows if x["adjudicatedDisposition"]=="hold-context")!={177:12,184:12}:
 raise RuntimeError("root hold boundary incorrect")
writejl(ROOT/"root-adjudicated-ledger.jsonl",root_rows)
writejl(ROOT/"cross-review-differences.jsonl",mismatch_rows)
summary={
 "artifact":"ROMarrNG PR #70 W166-W185 primary/blind cross-audit and root adjudication",
 "repository":REPO,"pullRequest":70,"livePr":live,"head":HEAD,"tree":TREE,
 "window":{"firstSourceOrdinal":166,"lastSourceOrdinal":185,"sourceCount":20,"locales":LOCALES,"cellCount":240},
 "candidateFreeInput":{"primaryInputManifestSha256":sha((PRIMARY/"input/manifest.json").read_bytes()),"blindInputManifestSha256":sha((BLIND/"input/manifest.json").read_bytes()),"primaryReviewInputSha256":sha((PRIMARY/"input/review-input.jsonl").read_bytes()),"blindReviewInputSha256":sha((BLIND/"input/review-input.jsonl").read_bytes()),"all240SourceAndCurrentTargetCellsIdentical":True,"sourceContextIdentical":True,"sourceStructureIdentical":True,"renderPathContextIdentical":True,"filePinsIdentical":True},
 "primary":{"manifestSha256":sha((PRIMARY/"primary-private/manifest.json").read_bytes()),"ledgerSha256":sha((PRIMARY/"primary-private/review-decisions.jsonl").read_bytes()),"dispositions":dict(sorted(__import__("collections").Counter(x["outcome"] for x in p_ledger).items())),"proposalCount":len(p_changes)},
 "independentBlind":{"packetPath":"independent-blind/","ledgerSha256":sha((BLIND/"blind-review.jsonl").read_bytes()),"dispositions":dict(sorted(__import__("collections").Counter(x["disposition"] for x in b_ledger).items())),"proposalCount":len(b_changes)},
 "crossReview":{"rawDispositionOrProposalDifferenceRows":raw_diff,"nonHoldDifferenceRows":semantic_nonhold,"sameTargetButDispositionClassDiffRows":same_target_label_diff,"differentCandidateOrAcceptVsProposeRows":target_recommendation_diffs,"holdsAgreeFor24Cells":True},
 "rootAdjudication":{"rows":len(root_rows),"dispositions":dict(sorted(root_counts.items())),"recommendedTargetChanges":len(root_changes),"targetChangesByDisposition":dict(sorted(Counter(x["adjudicatedDisposition"] for x in root_changes).items())),"heldOrdinals":[177,184],"heldCellCount":24},
 "holdFindings":{
  "177":{"callerExists":True,"caller":"romarr/ui.py:4163","evidence":"Full inline text is split around code value gamelists and a separate source fragment beginning 'folder and set its Game media directory to'; keep all 12 targets held for coordinated phrase treatment."},
  "184":{"callerExists":False,"selectedMessageIdReference":False,"ambiguousMatch":"romarr/app.py:7547 dynamically forms lookup failed: {exc.__class__.__name__}; adjacent exact key is ui.lookup-failed-error-type.6d33ec9b4f (ordinal 185), not the selected detail key.","mapHint":"romarr/app.py:7265 points to unrelated Seerr request code at this head; keep all 12 targets held."}
 },
 "sourceMapFinding":{"hintCount":sum(len(x.get("sourceMapHintVerification",[])) for x in pctx),"hintsMatchingCurrentSourceOrId":sum(sum(bool(h.get("matchesSourceOrId")) for h in x.get("sourceMapHintVerification",[])) for x in pctx),"callerResolution":"All direct references were taken from the identical exact-head caller-context packets and checked against pinned code-file SHA-256 values."},
 "nativeSpeakerApproved":False,"repoPrMutation":False,"worktreeInspected":False,"testsBuildsScansCiBrowser":False,
 "createdAtUtc":datetime.now(timezone.utc).isoformat()
}
writej(ROOT/"summary.json",summary)
writej(ROOT/"live-pr-recheck.json",live)
readme="""# ROMarrNG PR #70 W166-W185 cross-audit

This packet independently compares the primary review under the pinned primary scratch path with the independent candidate-free review copied into independent-blind/. Both are pinned to head {head}, tree {tree}; the live PR was rechecked and remains open/draft.

The two clean inputs have the same SHA-256 for the 240 source/current-target rows. Their source context, source structure, render-path context and exact code-file pins also match. The root-adjudicated ledger contains 240 cell recommendations, including every exact caller reference and pinned file hash.

The primary has {pcount} proposed targets; the blind review has {bcount}. There are {raw} raw disposition/proposal differences, of which {holds} are only the equivalent hold label for ordinals 177 and 184. The other {nonhold} cell differences are resolved in the root ledger. Ordinals 177 and 184 remain held in all locales.

Ordinal 177 has a caller at romarr/ui.py:4163 but spans text split by inline code and a separately catalogued suffix. Ordinal 184 has no selected caller; its only dynamic-text match is keyed to ordinal 185, and its source-map hint is unrelated at this head. See summary.json and cross-review-differences.jsonl.

This is machine adjudication, not native-speaker approval. No repo worktree or PR was changed; no tests, builds, automated security scans, CI, or browser work ran.
""".format(head=HEAD,tree=TREE,pcount=len(p_changes),bcount=len(b_changes),raw=raw_diff,holds=24,nonhold=semantic_nonhold)
(ROOT/"README.md").write_text(readme,encoding="utf-8")
# Manifest covers report files, nested independent evidence, and excludes itself/checksum list.
records=file_records(ROOT,{"manifest.json","SHA256SUMS.txt"})
manifest={"artifact":"ROMarrNG PR #70 W166-W185 root-style cross-audit packet","sealed":True,"checksumNote":"manifest.json excludes itself and SHA256SUMS.txt; SHA256SUMS.txt covers all other report files, including the independently copied blind packet.","createdAtUtc":datetime.now(timezone.utc).isoformat(),"repository":REPO,"pullRequest":70,"head":HEAD,"tree":TREE,"fileCount":len(records),"files":records,"rootLedgerPath":"root-adjudicated-ledger.jsonl","rootLedgerRows":len(root_rows),"rootLedgerSha256":sha((ROOT/"root-adjudicated-ledger.jsonl").read_bytes()),"summarySha256":sha((ROOT/"summary.json").read_bytes()),"blindEvidenceOriginalPath":"/mnt/disks/scratch/task-scratch/romarrng-pr70-w166-185-independent-blind-20261103","primaryEvidencePath":str(PRIMARY),"repoPrMutation":False,"nativeSpeakerApproved":False}
writej(ROOT/"manifest.json",manifest)
(ROOT/"SHA256SUMS.txt").write_text(checksum_tree(ROOT,{"SHA256SUMS.txt"}),encoding="utf-8")
# Read back every report checksum after sealing.
verify_sums(ROOT)
print(json.dumps({"root":str(ROOT),"head":HEAD,"tree":TREE,"primaryProposals":len(p_changes),"blindProposals":len(b_changes),"rawDiffRows":raw_diff,"nonHoldDiffRows":semantic_nonhold,"rootRows":len(root_rows),"rootChanges":len(root_changes),"rootDispositions":dict(root_counts),"inputSame":True},ensure_ascii=False,separators=(",",":")))
