#!/usr/bin/env python3
import ast,base64,concurrent.futures,hashlib,html,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path("/mnt/datapool_lvm_media/codex-task-scratch/romarrng-pr70-w166-185-20261103")
INPUT=ROOT/"input"; PRIMARY=ROOT/"primary-private"
REPO="snapetech-org/ROMarrNG"; PR=70
HEAD="5e45ce90babf3cf385fbb9775e70d7e8fcc6a783"
TREE="580de0b2db5030101c47a81fbd8a23489e993f75"
BRANCH="task/localization-translation-review-20261030"
LOCALES=["es","zh-Hans","hi","de","ja","fr","pt-BR","ar","ko","zh-Hant","vi","id"]
ORDS=list(range(166,186)); NEXT=list(range(186,206))
BUNDLE="localization/source-bundles/20261101-connect-instructions.json"
MAP="romarr/ui-source-messages.json"; SNAP="romarr/ui-source-snapshot.json"
CAT="romarr/ui-labels.json"; GLOSS="docs/localization-glossary.md"
EXTS={".py",".js",".html",".htm",".jinja",".jinja2",".css"}
PH=re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
MARKUP=re.compile(r"</?[A-Za-z][^<>]*>")
VERSION=re.compile(r"(?<![A-Za-z0-9])v?\d+(?:\.\d)+(?![A-Za-z0-9])")
PROTECTED=["Internet Archive","No-Intro","Redump","SeerrNG","ROMarr","Prowlarr","IGDB","Steam","EmuDeck","ES-DE","DAT","ROM","SHA-1","SHA-256","CRC32","API"]
PINS={
 BUNDLE:{"gitBlob":"0da16cf24d764dbf4b4156c2bc7db5c3ac8b11d5","sha256":"a6f047ba685db67ba51fe5fda0e20f6f83b84cdc94f303a68f648bc6540fe7a8","bytes":246871},
 MAP:{"gitBlob":"ea4ff095d4c9d60c175987926b852dddd1f6aa85","sha256":"612b3a664577c84e3fe60294929f2a97c8f103d2bfd58047aeecc6de348fd134","bytes":275911},
 SNAP:{"gitBlob":"c6e8f3f93cb8784a25422526730b3c21f3f000a4","sha256":"b728cfb7d9e5b321b6ee4b99e315120b91fe4f7561b8b38d957189002d41d801","bytes":202889},
 CAT:{"gitBlob":"59ffc419597b4ecd716daf2c0c4a91e1da974538","sha256":"bdd28b82dbc9c2b32986c7c53488e54336d944293221afa3bed9b23dd998091e","bytes":3007301},
 GLOSS:{"gitBlob":"edfe311cb5a0fd66c49a0923a0b410d207fa315f","sha256":"08f2f2e2ddf722065993a454523e8c353db823c336a6f07e48f9bf215e37ad34","bytes":3031},
}
PREV={"inputSelectionPath":"/mnt/disks/scratch/task-scratch/romarrng-pr70-w146-165-20261103/input/selection.json",
"inputSelectionSha256":"d997f97b5d4bf1acef55f3840c6ce730c3f3d4fe8aab9d37e0b756174fe9e40c",
"primaryLedgerSha256":"e6d04b143e06df5b0cf776281bb17d5fbe6e8b69ec13256d0ed903352215a3a4",
"primaryManifestSha256":"d1088966d8cc79c97414ef78169a7a635530c03b36d59bae25d0b335507ae915",
"head":"db895a97e9871952a0b952e1d119e32e06cf168d","tree":"f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a","firstOrdinal":146,"lastOrdinal":165}

CANDIDATES={
(170,"hi"):("गेम लाइब्रेरी की सूची","refinement","For the ROMarr collection view, this names a game-library inventory rather than a public library or a generic inventory; the Hindi phrase is clearer than the English-heavy current wording."),
(170,"ar"):("جرد مكتبة الألعاب","refinement","جرد denotes an inventory or audit; it is more precise for the game-library inventory view than مخزون, which commonly refers to stock."),
(172,"zh-Hans"):("无法获取游戏库中游戏的所有权信息","refinement","This states that ownership information for games in the library cannot be retrieved; the current 游戏拥有状态 wording is less idiomatic."),
(172,"de"):("Der Besitzstatus der Spiele in der Bibliothek lässt sich nicht ermitteln.","correction","The current compound can read as ownership of the library itself. This specifies that the unavailable information concerns ownership of the games in it."),
(172,"zh-Hant"):("無法取得遊戲庫中遊戲的擁有資訊","refinement","This clearly refers to ownership information for games in the library; 遊戲持有狀態 is less natural in this UI message."),
(174,"de"):("{library} nicht erreichbar ({error_type})","correction","Nicht erreichbar is the idiomatic German wording for an endpoint or library that cannot be reached; unzugänglich suggests inaccessible rather than unreachable."),
(176,"es"):("Probable conjunto multidisco · revisar","correction","The current cell leaves the central product term in English. This keeps the likelihood cue, translates the multi-disc set, and retains the review action."),
(176,"de"):("Wahrscheinlich ein Set mit mehreren Discs · prüfen","correction","This translates the English-heavy label and expresses review as an action; Bewertung means rating or assessment in this context."),
(176,"ar"):("على الأرجح مجموعة متعددة الأقراص · تحتاج إلى مراجعة","correction","This fixes the plural form for discs and expresses the review-needed status while preserving the likelihood."),
(176,"vi"):("Có khả năng là bộ nhiều đĩa · cần xem lại","correction","The current label leaves Multi-Disc Set in English and uses đánh giá (evaluation/rating); this translates the set and the review-needed status."),
(176,"id"):("Kemungkinan set multi-disk · perlu ditinjau","correction","The current label leaves both the set term and review marker in English; this translates the status while preserving the likely meaning."),
(178,"id"):("Sinkronisasi daftar (jam)","refinement","This uses natural Indonesian word order and removes the extra spacing inside the unit."),
(179,"fr"):("Affichage en liste","correction","Voir la liste reads as an instruction to view a list; the source labels a list-view display mode."),
(179,"id"):("Tampilan daftar","correction","Daftar pandangan is an unnatural calque; tampilan daftar is the natural UI label for list view."),
(181,"zh-Hans"):("已加载 DAT · 已验证的 ROM 转储名称","refinement","The glossary keeps DAT uppercase and distinguishes a ROM dump from a title. This removes the unnecessary English plural suffix and translates dump in the gaming context."),
(181,"zh-Hant"):("已載入 DAT · 已驗證的 ROM 轉儲名稱","refinement","The glossary keeps DAT uppercase and distinguishes a ROM dump from a title. This removes the unnecessary English plural suffix and translates dump in the gaming context."),
(182,"ar"):("جارٍ تحميل جرد مكتبة الألعاب…","correction","The adjacent heading identifies this as a game-library inventory; مخزون means stock. This aligns the term with جرد and uses the source ellipsis."),
(183,"es"):("Registros locales de ES-DE reutilizados: {count}","refinement","A metric-label construction places the count after the description and preserves the ES-DE name; the current word order reads as an incomplete clause."),
(183,"hi"):("पुनः उपयोग किए गए स्थानीय ES-DE रिकॉर्ड: {count}","correction","This gives the count label a complete, natural Hindi noun phrase while preserving ES-DE and the placeholder."),
(183,"de"):("Wiederverwendete lokale ES-DE-Datensätze: {count}","correction","The current German word order is incomplete; this forms a compact metric label and preserves ES-DE."),
(183,"ja"):("再利用したローカル ES-DE レコード: {count}","correction","The current Japanese is a broken sequence of nouns; this presents the reused local ES-DE records as a metric label."),
(183,"ko"):("재사용한 로컬 ES-DE 레코드: {count}","correction","The current Korean is an awkward noun sequence; this makes the reused local ES-DE records a clear metric label."),
(183,"zh-Hant"):("已重用 {count} 筆 ES-DE 本機記錄","refinement","This places the count naturally and uses 本機 to convey local records; the current order is less natural."),
(183,"id"):("Catatan lokal ES-DE yang digunakan kembali: {count}","correction","This gives the Indonesian metric label natural word order and places the count after the description."),
(185,"de"):("Suche fehlgeschlagen: {error_type}","correction","Suche fehlgeschlagen is the idiomatic German error message; versagt is unnatural for a failed lookup."),
(185,"ar"):("فشل البحث: {error_type}","refinement","This uses the natural Arabic word order for a failed lookup while keeping the error-type placeholder."),
(185,"ko"):("검색 실패: {error_type}","refinement","Korean punctuation does not take a space before the colon; the current translation inserts one."),
}
HOLDS={177,184}
HOLD_REASON={
177:"Hold all locales: the source is a text fragment ending immediately before inline code gamelists, and a separately catalogued adjacent fragment begins 'folder and set its Game media directory to'. Isolated changes could duplicate or misorder the noun around the code span. The exact caller is pinned, but coordinated full-sentence review is needed before proposing cell targets.",
184:"Hold all locales: no exact source literal or selected ID is present at this head. The only dynamic-pattern match is app.py:7547 and its nearby template key is ordinal 185 lookup-failed-error-type, so it does not establish a caller for this detail message. The pinned source-map hint app.py:7265 is unrelated; the detail-template render path is unresolved."
}

def gh(ep): return subprocess.check_output(["gh","api",ep])
def sha(b): return hashlib.sha256(b).hexdigest()
def blobsha(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def canon(x): return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())
def wj(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def wjl(p,rows): p.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for x in rows),encoding="utf-8")
def sums(d,skip):
 return "".join(f"{sha(p.read_bytes())}  {p.relative_to(d).as_posix()}\n" for p in sorted(x for x in d.rglob("*") if x.is_file() and x.name not in skip))
def fetch(path,entry):
 rec=json.loads(gh(f"repos/{REPO}/contents/{path}?ref={HEAD}"))
 if rec.get("encoding")=="base64" and rec.get("content"): data=base64.b64decode(rec["content"])
 else:
  b=json.loads(gh(f"repos/{REPO}/git/blobs/{entry['sha']}"))
  if b.get("encoding")!="base64": raise RuntimeError("unsupported encoding for "+path)
  data=base64.b64decode(b["content"])
 calc=blobsha(data)
 if rec.get("sha")!=calc or calc!=entry["sha"]: raise RuntimeError("blob mismatch "+path)
 return path,data,calc
def protect(src):
 return [t for t in PROTECTED if t in src and not(t=="ROM" and "ROMarr" in src)]
def forms(x):
 if isinstance(x,str): return [x]
 if isinstance(x,dict) and x.get("kind")=="plural" and isinstance(x.get("forms"),dict): return list(x["forms"].values())
 raise RuntimeError("unsupported translation shape")
def tokens(x): return sorted({t for f in forms(x) for t in PH.findall(f)})
def has_terms(x,terms): return all(any(t in f for f in forms(x)) for t in terms)
def delim(line,pat):
 for m in re.finditer(pat,line):
  before=line[m.start()-1] if m.start() else ""
  after=line[m.end()] if m.end()<len(line) else ""
  if before in {"","'",'"',">","(", "=", ",",":","{","["} and after in {"","'",'"',"<",")",",","}","]",";"," ","\t"}: return True
 return False
def doclines(src):
 ignored=set()
 try:
  parsed=ast.parse(src); nodes=[parsed]+[n for n in ast.walk(parsed) if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]
  for node in nodes:
   body=getattr(node,"body",[])
   if body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):
    n=body[0]; ignored.update(range(n.lineno,getattr(n,"end_lineno",n.lineno)+1))
 except SyntaxError: pass
 return ignored
def refs(item,files):
 out=[]; source=item["source"]; ident=item["id"]
 if "{" in source:
  parts=re.split(r"\{[^{}]+\}",source); dyn=r"\{[^{}]+\}".join(re.escape(x) for x in parts)
 else: dyn=None
 for path,raw in sorted(files.items()):
  ext=Path(path).suffix.lower(); src=raw.decode(); lines=src.splitlines(); ignore=doclines(src) if ext==".py" else set()
  for n,line in enumerate(lines,1):
   st=line.lstrip()
   if ext==".py" and (st.startswith("#") or n in ignore): continue
   if ext in {".js",".html",".htm",".css"} and st.startswith("//"): continue
   mt=None
   if ident in line: mt="stable-message-id-call-or-template" if any(t in line for t in ("message_template","data-i18n","interfaceMarkup","toastLabel","messageTemplate","apiMessageMarkup")) else "stable-message-id-in-code"
   elif delim(line,re.escape(source)): mt="exact-source-literal"
   elif delim(html.unescape(line),re.escape(source)): mt="html-entity-decoded-source-literal"
   elif dyn and delim(line,dyn): mt="dynamic-template-source-pattern"
   if mt=="dynamic-template-source-pattern" and ident not in line:
    nearby="\n".join(lines[max(0,n-4):min(len(lines),n+3)])
    nearby_ids=re.findall(r"ui\.[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[0-9a-f]{10}",nearby)
    if any(key!=ident for key in nearby_ids):
     continue
   if mt:
    ctx=[{"line":i,"text":lines[i-1]} for i in range(max(1,n-2),min(len(lines),n+2)+1)]
    out.append({"context":ctx,"fileSha256":sha(raw),"line":n,"lineText":line,"matchType":mt,"path":path})
 return out
def ambiguous_dynamic_matches(item,files):
 out=[]
 if "{" not in item["source"]: return out
 parts=re.split(r"\{[^{}]+\}",item["source"]); dyn=r"\{[^{}]+\}".join(re.escape(x) for x in parts)
 for path,raw in sorted(files.items()):
  lines=raw.decode().splitlines()
  for n,line in enumerate(lines,1):
   if item["id"] in line or not delim(line,dyn): continue
   nearby="\n".join(lines[max(0,n-4):min(len(lines),n+3)])
   keys=sorted(set(re.findall(r"ui\.[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[0-9a-f]{10}",nearby)))
   if keys and any(key!=item["id"] for key in keys):
    out.append({"path":path,"line":n,"lineText":line,"nearbyMessageIds":keys,"matchType":"dynamic-template-pattern-keyed-to-another-message","fileSha256":sha(raw)})
 return out
def hints(item,entry,files):
 out=[]
 for pos in entry.get("locations",[]):
  if ":" not in pos: out.append({"location":pos,"currentLineAvailable":False,"matchesSourceOrId":False}); continue
  path,span=pos.rsplit(":",1)
  try:
   n=int(span.split("-",1)[0]); line=files[path].decode().splitlines()[n-1]
  except (KeyError,ValueError,IndexError): line=None
  out.append({"location":pos,"currentLineAvailable":line is not None,"currentLineText":line,"matchesSourceOrId":bool(line and (item["source"] in line or item["id"] in line))})
 return out

pr=json.loads(gh(f"repos/{REPO}/pulls/{PR}"))
if not(pr.get("state")=="open" and pr.get("draft") is True and pr.get("head",{}).get("ref")==BRANCH and pr.get("head",{}).get("sha")==HEAD and pr.get("base",{}).get("ref")=="main"): raise RuntimeError("live PR/head/base mismatch")
commit=json.loads(gh(f"repos/{REPO}/git/commits/{HEAD}"))
if commit["tree"]["sha"]!=TREE: raise RuntimeError("head tree mismatch")
td=json.loads(gh(f"repos/{REPO}/git/trees/{HEAD}?recursive=1"))
if td.get("truncated"): raise RuntimeError("truncated tree")
tree={x["path"]:x for x in td["tree"] if x.get("type")=="blob"}
for p,pin in PINS.items():
 if p not in tree or tree[p]["sha"]!=pin["gitBlob"]: raise RuntimeError("pinned tree blob mismatch "+p)
codepaths=sorted(p for p in tree if p.startswith("romarr/") and Path(p).suffix.lower() in EXTS)
paths=sorted(set(codepaths)|set(PINS))
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: data=dict((p,(b,g)) for p,b,g in pool.map(lambda p:fetch(p,tree[p]),paths))
filepins={p:{"bytes":len(b),"gitBlob":g,"sha256":sha(b)} for p,(b,g) in data.items()}
for p,pin in PINS.items():
 if filepins[p]!=pin: raise RuntimeError("pinned content mismatch "+p)
bundle=json.loads(data[BUNDLE][0]); smdoc=json.loads(data[MAP][0]); snap=json.loads(data[SNAP][0]); catalog=json.loads(data[CAT][0])
messages=bundle["messages"]; sm={x["id"]:x for x in smdoc["messages"]}; cats=catalog["messages"]
if len(messages)!=484 or bundle.get("messageCount")!=484 or bundle.get("directPendingCells")!=5808: raise RuntimeError("bundle count mismatch")
if canon(messages)!=bundle.get("manifestHash"): raise RuntimeError("bundle manifest mismatch")
if smdoc.get("schemaVersion")!=1 or len(cats)!=1837: raise RuntimeError("map/catalog schema mismatch")
if catalog.get("locales") and not set(LOCALES).issubset(set(catalog["locales"])): raise RuntimeError("catalog locale set mismatch")
sel=[]
for o in ORDS:
 item=messages[o-1]; entry=cats.get(item["id"]); me=sm.get(item["id"])
 if set(item.get("translationPending",[]))!=set(LOCALES): raise RuntimeError(f"pending mismatch {o}")
 if not entry or not me: raise RuntimeError(f"missing catalog/map row {o}")
 if entry.get("source")!=item["source"] or entry.get("sourceHash")!=item["sourceHash"] or snap.get(item["id"])!=item["sourceHash"] or me.get("source")!=item["source"] or me.get("sourceHash")!=item["sourceHash"]: raise RuntimeError(f"source pins mismatch {o}")
 tg={}
 for loc in LOCALES:
  target=entry.get("translations",{}).get(loc); stored=entry.get("translationHashes",{}).get(loc); status=entry.get("translationStatus",{}).get(loc)
  if target is None or stored!=canon(target) or status!="draft": raise RuntimeError(f"target pin/status mismatch {o}/{loc}")
  st=set(PH.findall(item["source"]))
  if any(set(PH.findall(f))!=st for f in forms(target)): raise RuntimeError(f"placeholder mismatch {o}/{loc}")
  if not has_terms(target,protect(item["source"])): raise RuntimeError(f"protected literal mismatch {o}/{loc}")
  tg[loc]={"value":target,"hash":stored}
 sel.append((o,item,entry,me,tg))
nextrows=[]
for o in NEXT:
 item=messages[o-1]; entry=cats.get(item["id"])
 if set(item.get("translationPending",[]))!=set(LOCALES) or not entry or entry.get("source")!=item["source"] or entry.get("sourceHash")!=item["sourceHash"] or snap.get(item["id"])!=item["sourceHash"]: raise RuntimeError(f"next boundary mismatch {o}")
 nextrows.append({"sourceOrdinal":o,"id":item["id"],"source":item["source"],"sourceSha256":item["sourceHash"],"translationPendingLocales":item["translationPending"]})
files={p:data[p][0] for p in codepaths}
ctxrows=[]; inputrows=[]; struct=[]
for o,item,entry,me,tg in sel:
 r=refs(item,files); hh=hints(item,me,files); exists=bool(r); ambiguous=ambiguous_dynamic_matches(item,files)
 if o==177: status="caller-found-fragment-split-around-inline-code"; resolved=True
 elif o==184 and not exists: status="no-current-caller-and-source-map-hint-is-unrelated"; resolved=False
 else: status="current-code-reference-pinned"; resolved=True
 ctxrows.append({"callerExists":exists,"currentCodeReferences":r,"id":item["id"],"renderPathQuestion":HOLD_REASON.get(o,""),"source":item["source"],"sourceContextResolved":resolved,"sourceContextStatus":status,"sourceKind":item.get("sourceKind",me.get("category")),"sourceMapLocationHintNote":"Map locations are hints; the source/caller references below are resolved from exact-head blobs.","sourceMapLocationHints":me.get("locations",[]),"sourceMapHintVerification":hh,"ambiguousDynamicTemplateMatches":ambiguous,"sourceMessageCategory":me.get("category"),"sourceMessageMapSha256":filepins[MAP]["sha256"],"sourceOrdinal":o,"sourceSha256":item["sourceHash"],"unmappedSourceFinding":HOLD_REASON.get(o),"searchedProductionCodeFiles":codepaths if not exists else []})
 for loc in LOCALES:
  inputrows.append({"currentTarget":tg[loc]["value"],"currentTargetSha256":tg[loc]["hash"],"id":item["id"],"locale":loc,"source":item["source"],"sourceContextResolved":resolved,"sourceContextStatus":status,"callerExists":exists,"sourceKind":item.get("sourceKind",me.get("category")),"sourceOrdinal":o,"sourceSha256":item["sourceHash"],"storedTranslationHash":tg[loc]["hash"],"translationStatus":"draft"})
 struct.append({"id":item["id"],"sourceBundlePlaceholders":item.get("placeholders",PH.findall(item["source"])),"sourceMarkupTags":MARKUP.findall(item["source"]),"sourceOrdinal":o,"sourceProtectedLiterals":protect(item["source"]),"sourceRegexPlaceholders":PH.findall(item["source"]),"sourceSha256":item["sourceHash"],"sourceVersionLiterals":VERSION.findall(item["source"])})
callers=sum(x["callerExists"] for x in ctxrows)
if callers!=19:
 print(json.dumps({"callerCount":callers,"refs184":[x for x in ctxrows if x["sourceOrdinal"]==184]},ensure_ascii=False))
 raise RuntimeError("caller count expected 19, found "+str(callers))
if len(inputrows)!=240: raise RuntimeError("input cell count mismatch")
if any(k in row for row in inputrows for k in ("suggestedTarget","outcome","reviewDisposition","candidate")): raise RuntimeError("candidate leaked into input")
fragment=next((r for x in ctxrows if x["sourceOrdinal"]==177 for r in x["currentCodeReferences"] if r["path"]=="romarr/ui.py"),None)
if not fragment: raise RuntimeError("177 caller missing")
before="ui.set-these-only-when-you-want-romarr.2f1841a46b"; after="ui.folder-and-set-its-game-media-direct.6970455da7"
if before not in sm or after not in sm: raise RuntimeError("177 adjacent source fragments missing")
render=[{"sourceOrdinal":177,"id":sel[11][1]["id"],"source":sel[11][1]["source"],"exactCallerPath":fragment["path"],"exactCallerLine":fragment["line"],"exactCallerFileSha256":fragment["fileSha256"],"fullHtmlTextLine":fragment["lineText"],"inlineCodeValues":["gamelists","downloaded_media"],"precedingSourceFragment":{"id":before,"source":sm[before]["source"]},"followingSourceFragment":{"id":after,"source":sm[after]["source"]},"candidateFree":True,"holdReason":HOLD_REASON[177]}]
no=next(x for x in ctxrows if x["sourceOrdinal"]==184)
if not no["sourceMapHintVerification"] or any(x["matchesSourceOrId"] for x in no["sourceMapHintVerification"]): raise RuntimeError("184 map hint unexpectedly resolves")
if INPUT.exists() or PRIMARY.exists(): raise RuntimeError("refusing to overwrite existing packet")
now=datetime.now(timezone.utc).isoformat()
prmeta={"state":pr["state"],"draft":pr["draft"],"branch":pr["head"]["ref"],"head":HEAD,"tree":TREE,"base":pr["base"]["ref"],"updatedAt":pr["updated_at"],"url":pr["html_url"]}
prev=PREV
boundary={"repository":REPO,"pullRequest":PR,"livePrAtBuild":prmeta,"sourceBundlePath":BUNDLE,"sourceBundleSha256":filepins[BUNDLE]["sha256"],"sourceBundleManifestHash":bundle["manifestHash"],"priorReviewedWindow":prev,"thisWindow":{"firstSourceOrdinal":166,"lastSourceOrdinal":185,"sourceCount":20,"cellCount":240},"nextWindow":{"firstSourceOrdinal":186,"lastSourceOrdinal":205,"sourceCount":20,"cellCount":240,"sourceIdsAndPins":nextrows},"selectionRule":"Continue the source-bundle queue contiguously after W146-W165; next window begins at ordinal 186.","candidateFree":True}
selection={"repository":REPO,"pullRequest":PR,"head":HEAD,"tree":TREE,"livePrState":prmeta,"firstSelectedSourceOrdinal":166,"lastSelectedSourceOrdinal":185,"priorSelectedOrdinal":165,"locales":LOCALES,"selectedSourceCount":20,"selectedCellCount":240,"selectedSourceOrdinals":ORDS,"selectedIds":[x[1]["id"] for x in sel],"eligibilityChecks":{"sourceCatalogMapSnapshotPinsMatch":True,"allSelectedSourcesPendingForAllLocales":True,"allTargetHashesMatchCatalogPins":True,"allTargetsPopulatedAndDraft":True,"exactHeadCallerSearchCompleted":True,"callerPresentSourceCount":callers,"callerAbsentOrdinals":[184],"callerExistenceGatePassed":False,"fragmentedInlineCodeHoldOrdinals":[177],"nextWindowBeginsAtPinnedOrdinal":True,"candidatesOrReviewDecisionsIncluded":False},"previousWindow":prev,"sourceBundlePath":BUNDLE,"sourceBundleSha256":filepins[BUNDLE]["sha256"],"sourceBundleManifestHash":bundle["manifestHash"],"sourceBundleMessageCount":len(messages),"sourceBundleDirectPendingCells":bundle["directPendingCells"],"nextWindowBoundary":{"firstOrdinal":186,"lastOrdinal":205,"firstId":nextrows[0]["id"],"lastId":nextrows[-1]["id"]},"selectionMethod":"Continue the exact-head frozen source-bundle queue after W146-W165. Ordinal 184 has no current caller; ordinal 177 is held because its text is fragmented around inline code and a separately catalogued suffix."}
headpins={"repository":REPO,"pullRequest":PR,"state":prmeta["state"].upper(),"draft":prmeta["draft"],"url":prmeta["url"],"headRefName":prmeta["branch"],"head":HEAD,"tree":TREE,"baseRefName":prmeta["base"],"livePrUpdatedAt":prmeta["updatedAt"],"filePins":filepins,"callerSourcePaths":codepaths,"callerSourcePathCount":len(codepaths),"previousWindowReference":prev,"verification":"PR and exact head/tree rechecked through read-only GitHub API; source/catalog/caller pins come from exact-head Git blobs; no worktree or PR state was modified."}
readme="""ROMarrNG PR #70 W166-W185 candidate-free localization review input

Pinned PR head: {head}
Tree: {tree}
Branch: {branch}
Base: main

This packet contains source, current draft targets and canonical hashes for all 240 cells, caller context resolved from exact-head production-source blobs, and source structure. It contains no translation candidates or review dispositions. The queue continues immediately after W146-W165.

Source-map location hints are stale at this head. Ordinal 177 is held because its text is split around inline code and an adjacent catalogued phrase. Ordinal 184 is held because no current production caller or render path was found; its pinned line hint points to unrelated code.

The next-window boundary is ordinal 186 and is pinned in next-window-boundary.json. This machine review is not native-speaker approval. No repository worktree or PR was changed; no tests, builds, automated security scans, CI, browser work, releases, or tags ran; caller evidence came from a read-only exact-head source-reference search recorded in source-context.jsonl.
""".format(head=HEAD,tree=TREE,branch=BRANCH)
INPUT.mkdir(parents=True); PRIMARY.mkdir(parents=True)
(INPUT/"README.txt").write_text(readme,encoding="utf-8")
wj(INPUT/"head-and-file-pins.json",headpins); wj(INPUT/"selection.json",selection); wj(INPUT/"next-window-boundary.json",boundary)
wjl(INPUT/"review-input.jsonl",inputrows); wjl(INPUT/"source-context.jsonl",ctxrows); wjl(INPUT/"source-structure.jsonl",struct); wjl(INPUT/"render-path-context.jsonl",render)
inputfiles=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(INPUT.iterdir()) if p.is_file()]
im={"artifact":"ROMarrNG PR #70 W166-W185 clean localization review input","sealed":True,"checksumNote":"manifest.json excludes its own hash and SHA256SUMS.txt; SHA256SUMS.txt covers every packet file except itself.","createdAtUtc":now,"files":inputfiles,"head":HEAD,"tree":TREE,"inputPath":"review-input.jsonl","inputRows":len(inputrows),"inputSha256":sha((INPUT/"review-input.jsonl").read_bytes()),"pullRequest":PR,"repository":REPO,"sourceReferenceSearchUsed":True,"searchedProductionCodeFileCount":len(codepaths),"sourceContextRows":len(ctxrows),"sourceStructureRows":len(struct),"renderPathEvidenceRows":len(render),"scopeLimits":{"containsCurrentTargets":True,"containsReviewDispositions":False,"containsTranslationCandidates":False,"repositoryOrPullRequestEdited":False,"automatedTestsBuildsScansCiOrBrowserRun":False},"window":{"firstSourceOrdinal":166,"lastSourceOrdinal":185,"sourceCount":20,"locales":LOCALES,"cellCount":240},"callerContext":{"resolvedAtExactHead":True,"callerPresentSourceCount":callers,"callerAbsentOrdinals":[184],"callerExistenceGatePassed":False},"heldContextOrdinals":[177,184],"nativeSpeakerApproved":False,"sourceReferenceSearchUsed":True,"automatedSecurityScanRun":False}
wj(INPUT/"manifest.json",im); (INPUT/"SHA256SUMS.txt").write_text(sums(INPUT,{"SHA256SUMS.txt"}),encoding="utf-8")
imsha=sha((INPUT/"manifest.json").read_bytes()); insha=sha((INPUT/"review-input.jsonl").read_bytes())
byord={x["sourceOrdinal"]:x for x in struct}; byctx={x["sourceOrdinal"]:x for x in ctxrows}
primary=[]
for item in inputrows:
 o,loc,src,cur=item["sourceOrdinal"],item["locale"],item["source"],item["currentTarget"]
 st=sorted(set(PH.findall(src))); ct=tokens(cur); terms=byord[o]["sourceProtectedLiterals"]; currentok=has_terms(cur,terms); cand=CANDIDATES.get((o,loc))
 if o in HOLDS: outcome,suggested,rationale,confidence="hold-context",None,HOLD_REASON[o],"low"
 elif cand: suggested,outcome,rationale=cand; confidence="moderate"
 else: outcome,suggested,rationale,confidence="accept-current",None,"No clear semantic, placeholder, or protected-term defect was found in the current target under the pinned exact-head context.","moderate"
 candtokens=sorted(set(PH.findall(suggested))) if suggested is not None else None
 okph=set(ct)==set(st) and (suggested is None or set(candtokens)==set(st))
 okterms=currentok and (suggested is None or has_terms(suggested,terms))
 if not okph or not okterms: raise RuntimeError(f"review check failed {o}/{loc}")
 c=byctx[o]
 row={"callerExists":c["callerExists"],"callerRefs":c["currentCodeReferences"],"confidence":confidence,"currentTarget":cur,"currentTargetSha256":item["currentTargetSha256"],"id":item["id"],"locale":loc,"outcome":outcome,"placeholderCheck":{"candidateTokens":candtokens,"currentTokens":ct,"passed":okph,"sourceTokens":st},"protectedLiteralCheck":{"candidatePreserved":[t for t in terms if t in suggested] if suggested is not None else [],"currentPreserved":[t for t in terms if has_terms(cur,[t])],"passed":okterms,"required":terms},"rationale":rationale,"source":src,"sourceContextResolved":item["sourceContextResolved"],"sourceContextStatus":item["sourceContextStatus"],"sourceKind":item["sourceKind"],"sourceOrdinal":o,"sourceSha256":item["sourceSha256"],"targetChanges":suggested is not None and suggested!=cur,"translationStatus":item["translationStatus"]}
 if suggested is not None: row.update({"suggestedTarget":suggested,"suggestedTargetSha256":canon(suggested)})
 primary.append(row)
changes=[x for x in primary if x["targetChanges"]]; holds=[x for x in primary if x["outcome"]=="hold-context"]
if len(primary)!=240 or len({(x["id"],x["locale"]) for x in primary})!=240 or len(changes)!=len(CANDIDATES) or len(holds)!=24: raise RuntimeError("primary ledger count mismatch")
if any("suggestedTarget" in x for x in holds): raise RuntimeError("held row has a candidate")
disps={}
changeord={}
for x in primary:
 disps[x["outcome"]]=disps.get(x["outcome"],0)+1
 if x["targetChanges"]: changeord[str(x["sourceOrdinal"])]=changeord.get(str(x["sourceOrdinal"]),0)+1
holdcells=[{"id":x["id"],"locale":x["locale"],"sourceOrdinal":x["sourceOrdinal"]} for x in holds]
summary={"artifact":"ROMarrNG PR #70 W166-W185 primary semantic/context review","repository":REPO,"pullRequest":PR,"head":HEAD,"tree":TREE,"window":"W166-W185","inputManifestSha256":imsha,"inputReviewSha256":insha,"sourceIds":20,"locales":12,"cells":240,"callerPresentSourceCount":callers,"callerAbsentSourceOrdinals":[184],"fragmentedInlineCodeHoldOrdinals":[177],"dispositions":disps,"targetChanges":len(changes),"targetChangesByDisposition":{k:sum(x["outcome"]==k for x in changes) for k in ("correction","refinement")},"targetChangesBySourceOrdinal":dict(sorted(changeord.items(),key=lambda z:int(z[0]))),"placeholderChecksPassed":sum(x["placeholderCheck"]["passed"] for x in primary),"protectedLiteralChecksPassed":sum(x["protectedLiteralCheck"]["passed"] for x in primary),"exactCallerReferenceRows":sum(x["callerExists"] for x in primary),"holdContextCells":holdcells,"holdRationales":{"177":HOLD_REASON[177],"184":HOLD_REASON[184]},"nativeSpeakerApproved":False,"sourceReferenceSearchUsed":True,"automatedSecurityScanRun":False,"repositoryOrPrMutations":False,"automatedTestsBuildsScansCiBrowser":False,"workflowChanges":False,"releaseOrTagChanges":False,"createdAtUtc":now}
checks={"expectedCellCount":240,"actualCellCount":len(primary),"uniqueCellCount":len({(x["id"],x["locale"]) for x in primary}),"missingCellCount":0,"duplicateCellCount":0,"allStatusesRemainDraft":all(x["translationStatus"]=="draft" for x in inputrows),"allPlaceholderChecksPassed":all(x["placeholderCheck"]["passed"] for x in primary),"allProtectedLiteralChecksPassed":all(x["protectedLiteralCheck"]["passed"] for x in primary),"holdContextCellsOnlyOrdinals177And184":all(x["sourceOrdinal"] in HOLDS for x in holds),"holdContextCellCount":len(holds),"holdContextHasNoCandidates":all("suggestedTarget" not in x for x in holds),"suggestedTargetHashesValid":all("suggestedTarget" not in x or x["suggestedTargetSha256"]==canon(x["suggestedTarget"]) for x in primary),"inputHeadTreePinned":True,"cleanInputHashPinned":True,"candidateFreeInputRemainsSeparate":True,"noRepositoryOrPrMutation":True,"automatedTestsBuildsScansCiBrowserNotRun":True,"nativeSpeakerApprovalClaimed":False}
prreadme="""# ROMarrNG PR #70 W166-W185 primary review

Pinned to head {head} and tree {tree}. This ledger was created from the separate candidate-free input packet, whose review-input SHA-256 is {inputsha}.

The 240-cell ledger proposes {changes} corrections or refinements, accepts current targets for {accepted} cells, and holds all 12 cells at each of ordinals 177 and 184. Ordinal 177 is split around inline code and adjacent separately catalogued text; ordinal 184 has no current production caller at the pinned head and its source-map hint points to unrelated code.

Candidates occur only in this primary-private packet. Held rows have no suggested target. Placeholder and glossary-protected literal checks passed for every cell. These are machine-review decisions, not native-speaker approval. No repository worktree or PR was edited, and no tests, builds, automated security scans, CI, browser work, releases, or tags ran; caller evidence came from a read-only exact-head source-reference search recorded in source-context.jsonl.
""".format(head=HEAD,tree=TREE,inputsha=insha,changes=len(changes),accepted=disps.get("accept-current",0))
(PRIMARY/"README.md").write_text(prreadme,encoding="utf-8"); wjl(PRIMARY/"review-decisions.jsonl",primary); wj(PRIMARY/"summary.json",summary); wj(PRIMARY/"review-completion-checks.json",checks)
pfiles=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(PRIMARY.iterdir()) if p.is_file()]
pm={"artifact":"ROMarrNG PR #70 W166-W185 primary review packet","sealed":True,"checksumNote":"manifest.json excludes its own hash and SHA256SUMS.txt; SHA256SUMS.txt covers every packet file except itself.","createdAtUtc":now,"files":pfiles,"head":HEAD,"tree":TREE,"inputManifestSha256":imsha,"inputReviewSha256":insha,"reviewDecisionRows":len(primary),"reviewDecisionPath":"review-decisions.jsonl","reviewDecisionSha256":sha((PRIMARY/"review-decisions.jsonl").read_bytes()),"repository":REPO,"pullRequest":PR,"window":{"firstSourceOrdinal":166,"lastSourceOrdinal":185,"sourceCount":20,"locales":12,"cellCount":240},"scopeLimits":{"repositoryOrPrEdited":False,"automatedTestsBuildsScansCiOrBrowserRun":False,"nativeSpeakerApproved":False,"sourceReferenceSearchUsed":True,"automatedSecurityScanRun":False},"holdContext":{"ordinals":[177,184],"cellCount":24,"callerAbsentOrdinal":184}}
wj(PRIMARY/"manifest.json",pm); (PRIMARY/"SHA256SUMS.txt").write_text(sums(PRIMARY,{"SHA256SUMS.txt"}),encoding="utf-8")
pmsha=sha((PRIMARY/"manifest.json").read_bytes()); builderhash=sha(Path(__file__).read_bytes())
task={"artifact":"ROMarrNG PR #70 W166-W185 localization primary review task package","createdAtUtc":now,"repository":REPO,"pullRequest":PR,"livePr":prmeta,"inputPath":"input","inputManifestSha256":imsha,"primaryPath":"primary-private","primaryManifestSha256":pmsha,"builder":"build_w166_185.py","builderSha256":builderhash,"window":{"firstSourceOrdinal":166,"lastSourceOrdinal":185,"sourceCount":20,"cellCount":240},"nextWindowBoundary":{"firstSourceOrdinal":186,"lastSourceOrdinal":205,"firstId":nextrows[0]["id"],"lastId":nextrows[-1]["id"]},"dispositions":disps,"targetChanges":len(changes),"holdOrdinals":[177,184],"repositoryWorktreeAccessed":False,"repoPrMutation":False,"automatedTestsBuildsScansCiBrowser":False,"nativeSpeakerApproved":False,"sourceReferenceSearchUsed":True,"automatedSecurityScanRun":False}
wj(ROOT/"task-summary.json",task)
(ROOT/"README.md").write_text("# ROMarrNG PR #70 W166-W185 primary localization review\n\nExact-head candidate-free input is in input/; primary machine-review decisions are in primary-private/. The next window begins at ordinal 186. Verify each packet SHA256SUMS.txt before use. See task-summary.json for exact pins and counts. No repository worktree or PR was changed. No tests, builds, automated security scans, CI, or browser work ran; caller evidence came from a read-only exact-head source-reference search.\n",encoding="utf-8")
(ROOT/"task-SHA256SUMS.txt").write_text(sums(ROOT,{"task-SHA256SUMS.txt"}),encoding="utf-8")
print(json.dumps({"output":str(ROOT),"head":HEAD,"tree":TREE,"sourceCodePaths":len(codepaths),"callerPresentSources":callers,"cells":len(primary),"changes":len(changes),"dispositions":disps,"inputManifestSha256":imsha,"primaryManifestSha256":pmsha,"nextWindow":"186-205"},ensure_ascii=False,separators=(",",":")))
