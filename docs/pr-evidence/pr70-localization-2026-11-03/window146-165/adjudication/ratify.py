#!/usr/bin/env python3
import hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
REPO=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=OUT,text=True).strip())
def sha_source(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha_target(value):
 return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()

# Resolutions for low-consensus cells and decisions grounded in the exact caller/glossary.
manual={
 (146,'es'):('refinement','IGDB · portadas, géneros y calificaciones','Use the established Spanish catalog term for game cover art, aligning with the existing Portada/Cover wording.'),
 (146,'zh-Hant'):('correction','IGDB · 封面、類型與評分','Use Traditional Chinese and avoid the redundant 美術 after 封面 already expresses cover art.'),
 (146,'id'):('correction','IGDB · sampul, genre, dan rating','Penutup means a lid/covering; sampul is the natural term for game cover art.'),
 (147,'pt-BR'):('correction','Importe uma pasta sua e deixe o ROMarr identificar e organizar o conteúdo.','Use a complete imperative matching the English instruction and keep the product name unchanged.'),
 (147,'vi'):('correction','Nhập một thư mục của bạn để ROMarr nhận diện và sắp xếp nội dung bên trong.','The current word lưu trữ means store/archive; sắp xếp expresses identifying and organizing the folder contents.'),
 (148,'es'):('refinement','Intervalo de comprobación de importación (minutos)','The exact caller is a numeric scheduled interval; name the check interval rather than a generic control.'),
 (148,'zh-Hans'):('correction','导入检查间隔（分钟）','Use the software term 导入 and clarify that the numeric value is the interval between import checks.'),
 (148,'hi'):('correction','आयात जाँच का अंतराल (मिनट)','Remove the mixed English word and malformed spacing; the caller is the import-check interval.'),
 (148,'de'):('refinement','Intervall der Importprüfung (Minuten)','The numeric caller controls the import-check interval; make that interval explicit.'),
 (148,'fr'):('refinement','Intervalle de vérification de l’importation (minutes)','Clarify that this number is the interval between scheduled import checks.'),
 (148,'pt-BR'):('refinement','Intervalo de verificação da importação (minutos)','Clarify that this numeric field is the interval between import checks.'),
 (148,'ar'):('refinement','الفاصل بين فحوص الاستيراد (بالدقائق)','The exact scheduler field is the interval between import checks, not an import verification count.'),
 (148,'ko'):('correction','가져오기 확인 간격(분)','Use the software term 가져오기 instead of 수입, which suggests trade imports, and state the interval.'),
 (148,'zh-Hant'):('correction','匯入檢查間隔（分鐘）','Use Traditional Chinese 匯入 rather than 進口 and clarify the interval between checks.'),
 (148,'vi'):('refinement','Khoảng thời gian giữa các lần kiểm tra nhập (phút)','The caller is an interval in minutes; express the time between import checks clearly.'),
 (148,'id'):('refinement','Interval pemeriksaan impor (menit)','Clarify that this number is the interval between import checks.'),
 (149,'id'):('refinement','Impor unduhan yang telah selesai secara otomatis','Use Indonesian unduhan for downloads and make completed mean finished rather than complete/whole.'),
 (150,'zh-Hans'):('correction','导入已完成的下载','Use the software term 导入; 进口 means importing goods/customs.'),
 (150,'hi'):('correction','पूरे हो चुके डाउनलोड आयात करें','The current wording is garbled; use a clear action for importing finished downloads.'),
 (150,'ja'):('correction','完了したダウンロードをインポート','輸入 means trade imports; use the established software term インポート.'),
 (150,'ko'):('correction','완료된 다운로드 가져오기','Use the software term 가져오기 rather than 수입, which means trade/customs import.'),
 (150,'zh-Hant'):('correction','匯入已完成的下載','Use Traditional Chinese 匯入 rather than 進口, which means importing goods.'),
 (150,'id'):('refinement','Impor unduhan yang telah selesai','Use unduhan for downloads and distinguish finished downloads from “complete” downloads.'),
 (152,'pt-BR'):('refinement','Importado da lista de jogos ES-DE existente; revise o título antes de renomear.','Complete the review instruction and identify the title as what must be checked before renaming; preserve ES-DE.'),
 (152,'ar'):('correction','تم الاستيراد من قائمة الألعاب الحالية في ES-DE؛ راجع العنوان قبل إعادة تسميته.','Use a completed-import sentence and make the title the object of the review instruction; preserve ES-DE.'),
 (153,'hi'):('correction','पूरे हुए {total} डाउनलोड में से {imported} आयात किए गए','Correct the agreement and word order for finished downloads while preserving both numeric placeholders.'),
 (154,'es'):('correction','Metadatos locales importados · revisar el título','Make the second half an instruction to review the title, rather than the noun phrase “title of review”.'),
 (154,'ar'):('correction','تم استيراد البيانات الوصفية المحلية · راجع العنوان','Use the precise metadata term and express the completed import plus review-title instruction.'),
 (155,'es'):('correction','Se importaron {total}','Use a natural completed-action count without inventing an item noun.'),
 (155,'de'):('refinement','Importiert: {total}','Use punctuation to make the count label clear.'),
 (155,'fr'):('refinement','Importés : {total}','Use the plural participle for a count of imported downloads, without adding a generic item noun.'),
 (155,'hi'):('refinement','आयात किए गए: {total}','Use a grammatical completed-action count and avoid adding a generic item noun.'),
 (155,'ja'):('correction','インポート済み：{total}','輸入 means importing goods; use the software term and a completed-action count label.'),
 (155,'ko'):('correction','가져온 수: {total}','The exact caller passes the number of finished downloads; state the count without adding an unsupported generic item noun.'),
 (155,'zh-Hans'):('correction','已导入 {total}','Use the software term 导入 and keep the count unit-neutral, as in the source.'),
 (155,'zh-Hant'):('correction','已匯入 {total}','Use Traditional Chinese 匯入 and keep the count unit-neutral, as in the source.'),
 (155,'id'):('correction','Diimpor: {total}','Use a completed passive count label rather than the ongoing verb Mengimport.'),
 (157,'zh-Hant'):('correction','正在遊戲中','Use Traditional Chinese 遊戲; the current value contains Simplified 戏. The caller is a live busy-state label.'),
 (158,'id'):('refinement','di koleksi game','The glossary defines the library as the user’s game collection; avoid wording that suggests a public library.'),
 (161,'de'):('correction','Internet Archive hat die Anfrage abgelehnt.','The current German verb phrase is ungrammatical; use a complete rejection sentence.'),
 (161,'ja'):('correction','Internet Archive はリクエストを拒否しました。','Use a complete, natural sentence for this authored refusal message.'),
 (161,'ko'):('correction','Internet Archive가 요청을 거부했습니다.','The current Korean verb is an incomplete stem; use a complete past-tense refusal sentence.'),
 (162,'ja'):('correction','ゲームの識別情報が無効です。','Replace the awkward アイデンティティ loanword with a natural game-identifier error.'),
 (162,'ko'):('correction','게임 식별자가 유효하지 않습니다.','The caller validates a stable identifier; use 식별자 rather than a person’s identity or broad information.'),
 (163,'fr'):('correction','Résultat invalide du hub : {detail}','Add the required article in French and preserve the opaque exception detail.'),
 (163,'ja'):('refinement','ハブの結果が無効です：{detail}','Use a natural error sentence for the returned hub result and preserve the opaque detail placeholder.'),
 (163,'zh-Hans'):('correction','Hub 返回的结果无效：{detail}','中心 means a physical/central center; the caller parses a software hub result. Preserve the technical Hub term and opaque detail.'),
 (163,'ar'):('correction','نتيجة hub غير صالحة: {detail}','المركز means a center; use the technical hub term and preserve the opaque detail placeholder.'),
 (163,'zh-Hant'):('correction','Hub 傳回的結果無效：{detail}','中心 means a physical/central center; use the software hub meaning and Traditional Chinese punctuation.'),
 (164,'ja'):('refinement','プランのトークンが無効です。','Separate plan from token to avoid the ambiguous compound プラントークン; the caller validates plan_id.'),
 (165,'ja'):('refinement','招待 · ROMarr','For this active web page title, 招待 is a general invitation; 招待状 suggests a physical invitation card.')
}

review=[json.loads(s) for s in (ROOT/'input/review-input.jsonl').read_text().splitlines()]
mine=[json.loads(s) for s in (ROOT/'candidate-free/adjudication-ledger.jsonl').read_text().splitlines()]
primary=[json.loads(s) for s in (ROOT/'primary/review-decisions.jsonl').read_text().splitlines()]
independent=[json.loads(s) for s in (ROOT/'independent/independent-ledger.jsonl').read_text().splitlines()]
rootblind=[json.loads(s) for s in (ROOT/'root-blind/ledger.jsonl').read_text().splitlines()]
def key(x): return (x['sourceOrdinal'],x['locale'])
assert all(len(x)==240 for x in (review,mine,primary,independent,rootblind))
idx={n:{key(x):x for x in rows} for n,rows in [('mine',mine),('primary',primary),('independent',independent),('root',rootblind)]}
assert all(len(x)==240 for x in idx.values())
ctx={x['id']:x for x in map(json.loads,(ROOT/'input/source-context.jsonl').read_text().splitlines())}
meta={x['id']:x for x in map(json.loads,(ROOT/'input/source-structure.jsonl').read_text().splitlines())}
def tgt(w,x):
 if w=='mine': return x['proposedTarget'] if x['proposedTarget'] is not None else x['currentTarget']
 if w=='primary': return x['suggestedTarget'] if x['targetChanges'] else x['currentTarget']
 if w=='independent': return x['decisionTarget'] if x['decisionTarget'] is not None else x['currentTarget']
 return x.get('proposedTarget') or x['currentTarget']
def disp(w,x):
 return x['outcome'] if w=='primary' else x['disposition']

out=[]
for cell in review:
 k=key(cell)
 if cell['sourceOrdinal']==160:
  final_disp='hold-context'; final=None
  rationale='Hold this locale cell: exact-head context is resolved, but no production-code caller exists for this lowercase key. The case-distinct title key has its own caller and does not satisfy this gate.'
 elif k in manual:
  final_disp,final,rationale=manual[k]
 else:
  votes={w:tgt(w,idx[w][k]) for w in idx}
  c=Counter(votes.values())
  top=max(c.values())
  if top<3: raise ValueError(f'unresolved disagreement {k}: {dict(c)}')
  final=next(v for v,n in c.items() if n==top)
  if final==cell['currentTarget']:
   final_disp='accept-current'; rationale='Retain the current value: candidate reviews and exact caller context support its meaning and locale usage.'
  else:
   voters=[w for w in idx if votes[w]==final]
   dc=Counter(disp(w,idx[w][k]) for w in voters)
   final_disp='correction' if dc['correction']>dc['refinement'] else 'refinement'
   rationale=next((idx[w][k].get('rationale') for w in ('primary','independent','root','mine') if votes[w]==final and idx[w][k].get('rationale')), 'The agreed target improves fidelity in the exact pinned caller context.')
assert len(out)==0
for cell in review:
 k=key(cell)
 if cell['sourceOrdinal']==160:
  final_disp='hold-context'; final=None
  rationale='Hold this locale cell: exact-head context is resolved, but no production-code caller exists for this lowercase key. The case-distinct title key has its own caller and does not satisfy this gate.'
 elif k in manual:
  final_disp,final,rationale=manual[k]
 else:
  votes={w:tgt(w,idx[w][k]) for w in idx}
  c=Counter(votes.values()); top=max(c.values())
  if top<3: raise ValueError(f'unresolved disagreement {k}: {dict(c)}')
  final=next(v for v,n in c.items() if n==top)
  if final==cell['currentTarget']:
   final_disp='accept-current'; rationale='Retain the current value: candidate reviews and exact caller context support its meaning and locale usage.'
  else:
   voters=[w for w in idx if votes[w]==final]
   dc=Counter(disp(w,idx[w][k]) for w in voters)
   final_disp='correction' if dc['correction']>dc['refinement'] else 'refinement'
   rationale=next((idx[w][k].get('rationale') for w in ('primary','independent','root','mine') if votes[w]==final and idx[w][k].get('rationale')), 'The agreed target improves fidelity in the exact pinned caller context.')
 assert sha_source(cell['source'])==cell['sourceSha256'] and sha_target(cell['currentTarget'])==cell['currentTargetSha256']
 assert cell['callerExists']==ctx[cell['id']]['callerExists'] and cell['sourceContextResolved']==ctx[cell['id']]['sourceContextResolved']
 sm=meta[cell['id']]
 if final is not None:
  assert sorted(re.findall(r'\{[^{}]+\}',cell['source']))==sorted(re.findall(r'\{[^{}]+\}',final)),(k,'placeholders')
  for lit in sm.get('sourceProtectedLiterals',[]): assert lit in final,(k,lit)
 refs=[{'path':r['path'],'line':r['line'],'fileSha256':r['fileSha256'],'lineText':r['lineText'],'matchType':r['matchType']} for r in ctx[cell['id']].get('currentCodeReferences',[])]
 hold_pins=None
 if cell['sourceOrdinal']==160:
  hctx=ctx[cell['id']]
  nearby=[]
  for r in hctx.get('nearbyCaseDistinctReferences',[]):
   file_bytes=(REPO/r['path']).read_bytes()
   nearby.append({'path':r['path'],'line':r['line'],'lineText':r['lineText'],'messageId':r['messageId'],'source':r['source'],'relationship':r['relationship'],'fileSha256':hashlib.sha256(file_bytes).hexdigest()})
  hold_pins={'head':'db895a97e9871952a0b952e1d119e32e06cf168d','tree':'f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a','sourceContextFile':'input/source-context.jsonl','sourceContextFileSha256':hashlib.sha256((ROOT/'input/source-context.jsonl').read_bytes()).hexdigest(),'sourceContextRecordSha256':sha_target(hctx),'contextStatus':hctx['sourceContextStatus'],'callerExists':hctx['callerExists'],'currentCodeReferencesCount':len(hctx.get('currentCodeReferences',[])),'searchedProductionCodeFilesCount':len(hctx.get('searchedProductionCodeFiles',[])),'searchedProductionCodeFilesSha256':sha_target(hctx.get('searchedProductionCodeFiles',[])),'unmappedSourceFinding':hctx.get('unmappedSourceFinding'),'caseDistinctNeighbor':nearby}
 rv={}
 for w in idx:
  x=idx[w][k]; t=tgt(w,x)
  rv[w]={'disposition':disp(w,x),'target':t,'targetSha256':sha_target(t) if t is not None else None}
 out.append({'sourceOrdinal':cell['sourceOrdinal'],'id':cell['id'],'locale':cell['locale'],'source':cell['source'],'sourceSha256':cell['sourceSha256'],'currentTarget':cell['currentTarget'],'currentTargetSha256':cell['currentTargetSha256'],'callerExists':cell['callerExists'],'sourceContextResolved':cell['sourceContextResolved'],'sourceContextStatus':cell['sourceContextStatus'],'callerRefs':refs,'holdPins':hold_pins,'sourcePlaceholders':sm.get('sourceBundlePlaceholders',[]),'sourceProtectedLiterals':sm.get('sourceProtectedLiterals',[]),'reviewVotes':rv,'finalDisposition':final_disp,'finalTarget':final,'finalTargetSha256':sha_target(final) if final is not None else None,'rationale':rationale})
assert len(out)==240
counts=Counter(x['finalDisposition'] for x in out)
changed=[x for x in out if x['finalDisposition'] in ('correction','refinement')]
byord=Counter(str(x['sourceOrdinal']) for x in changed)
OUT.joinpath('ratified-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+chr(10) for x in out))
summary={'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W146-W165','head':'db895a97e9871952a0b952e1d119e32e06cf168d','tree':'f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a','inputReviewSha256':'d649bb321a80fbbf28bf3aae88266db04f4f3e839a4c0f33ab4f84d24d26c83d','candidateFreeLedgerSha256':hashlib.sha256((ROOT/'candidate-free/adjudication-ledger.jsonl').read_bytes()).hexdigest(),'ratifiedCells':len(out),'dispositions':dict(counts),'changedCells':len(changed),'changedCellsByOrdinal':dict(byord),'callerAbsentOrdinal160HeldAll12':sum(x['finalDisposition']=='hold-context' and x['sourceOrdinal']==160 for x in out)==12,'placeholderMismatches':0,'protectedLiteralMismatches':0,'nativeSpeakerApproved':False,'headedBrowserAcceptance':False,'blindBoundary':'Candidate-free ledger was sealed before reading candidate texts. Aggregate summaries and changed-cell source/hash metadata were visible before sealing, so strict blinding is not claimed.','repositoryOrPrMutatedDuringAdjudication':False,'applicationPerformedAfterAdjudication':True,'applicationRecord':'../application/apply-summary.json','testsBuildsScansCiBrowserOrWorkflowChanges':False}
summary['hashMethods']={'source':'SHA-256 of source UTF-8 text','currentTarget':'SHA-256 of canonical JSON string (UTF-8, ensure_ascii=False, sorted keys, compact separators), matching the pinned catalog translationHashes','finalTarget':'SHA-256 of canonical JSON string (UTF-8, ensure_ascii=False, sorted keys, compact separators)'}
summary['comparisonLedgerSha256']={'primary':hashlib.sha256((ROOT/'primary/review-decisions.jsonl').read_bytes()).hexdigest(),'independent':hashlib.sha256((ROOT/'independent/independent-ledger.jsonl').read_bytes()).hexdigest(),'root':hashlib.sha256((ROOT/'root-blind/ledger.jsonl').read_bytes()).hexdigest()}
OUT.joinpath('ratified-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+chr(10))
notes='''# ROMarrNG W146–W165 ratification notes

This 240-cell adjudication is pinned to PR #70 head db895a97e9871952a0b952e1d119e32e06cf168d and tree f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a. It combines the frozen current/source/caller input, candidate-free adjudication, and the primary, independent, and root ledgers. Every final target carries source/current/final hashes and an exact caller reference or hold pin. Source hashes use SHA-256 of UTF-8 text; current and final target hashes use the catalog's canonical JSON string encoding (UTF-8, sorted keys, compact separators).

The lowercase integration-guide key at ordinal 160 has no current production-code caller. All 12 locale cells remain hold-context. Each row carries a hold pin to the exact-head source-context record and the separate case-distinct title caller, including its file hash and line.

Context-sensitive ratifications include interval wording for Import check (minutes) based on the auto_import_interval_minutes caller; busy-state language for In a game; the user's game collection meaning for In library; a software-hub rather than physical-center meaning for invalid hub result; and Imported {total} count labels that avoid generic item nouns unsupported by the source.

The candidate-free ledger was sealed before candidate text was read. Aggregate summaries and changed-cell source/hash metadata were visible before sealing, so this packet does not claim strict blinding. Machine review is not native-speaker approval. No repository or PR files were edited during this review phase; the subsequent approved catalog application is documented separately. No tests, builds, scans, CI, browser work, or workflows were run for adjudication.
'''
OUT.joinpath('README.md').write_text(notes)
artifact_names=['ratified-ledger.jsonl','ratified-summary.json','README.md','ratify.py']
manifest={'artifact':'ROMarrNG PR #70 W146-W165 ratification','repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':'db895a97e9871952a0b952e1d119e32e06cf168d','tree':'f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a','rows':len(out),'manifestExcludesOwnHash':True,'sha256sumsCoversManifestAndEveryArtifact':True,'files':[{'name':n,'bytes':(OUT/n).stat().st_size,'sha256':hashlib.sha256((OUT/n).read_bytes()).hexdigest()} for n in artifact_names],'evidenceInputs':[{'name':'input/review-input.jsonl','sha256':summary['inputReviewSha256']},{'name':'candidate-free/adjudication-ledger.jsonl','sha256':summary['candidateFreeLedgerSha256']},{'name':'primary/review-decisions.jsonl','sha256':summary['comparisonLedgerSha256']['primary']},{'name':'independent/independent-ledger.jsonl','sha256':summary['comparisonLedgerSha256']['independent']},{'name':'root-blind/ledger.jsonl','sha256':summary['comparisonLedgerSha256']['root']}]}
OUT.joinpath('manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+chr(10))
checksum_names=artifact_names+['manifest.json']
OUT.joinpath('SHA256SUMS.txt').write_text(''.join(f"{hashlib.sha256((OUT/n).read_bytes()).hexdigest()}  {n}\n" for n in checksum_names))
print(json.dumps(summary,ensure_ascii=False))
