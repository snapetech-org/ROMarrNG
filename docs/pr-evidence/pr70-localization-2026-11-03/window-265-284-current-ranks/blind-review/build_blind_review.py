from __future__ import annotations
import collections,hashlib,json,subprocess
from pathlib import Path

input_dir=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-candidate-free-20261103/input')
out=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-independent-blind-20261103')
head='c135c4729582817273c946891186ab4ea87467b5'
tree='32c07150396335a5832b5664fc1e0225d7cebdc1'

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def tsha(s:str)->str:return sha(s.encode('utf-8'))
def jl(o)->str:return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))

changes={}
def put(pos,disp,reason,vals):
 for loc,target in vals.items():changes[(pos,loc)]=(disp,target,reason)

put(265,'correction','The pinned Patches paragraph describes completeness as project-declared, never guessed. Correct meaning/copy issues and use natural target-language punctuation.',{
'de':'Projekte stammen ausschließlich aus Ihrem eigenen Katalog. Als vollständig gilt, was ein Projekt angibt; es wird nichts geraten. Anfragen kommen von SeerrNG.',
'hi':'परियोजनाएँ केवल आपके अपने कैटलॉग से आती हैं। पूर्णता वही है जो परियोजना बताती है; इसका कभी अनुमान नहीं लगाया जाता। अनुरोध SeerrNG से आते हैं।',
'id':'Proyek hanya berasal dari katalog Anda sendiri. Kelengkapan mengikuti apa yang dinyatakan proyek, bukan tebakan. Permintaan berasal dari SeerrNG.',
'ja':'プロジェクトはご自身のカタログからのみ取得されます。完全性は各プロジェクトの申告に基づき、決して推測しません。リクエストは SeerrNG から届きます。',
'zh-Hans':'项目仅来自您自己的目录。完整性以项目声明为准，绝不靠猜测。请求来自 SeerrNG。',
'zh-Hant':'項目僅來自您自己的目錄。完整性以專案聲明為準，絕不靠猜測。請求來自 SeerrNG。'})
put(266,'correction','The pinned caller is a file-rename preview table (“Current path” / “Proposed path”), so use filesystem-path terminology rather than road/route wording.',{
'ar':'المسار المقترح','de':'Vorgeschlagener Pfad','es':'Ruta propuesta','hi':'प्रस्तावित पथ','id':'Jalur yang diusulkan','ja':'提案されたパス','vi':'Đường dẫn đề xuất'})
put(267,'refinement','This is an accessible link label for a provider-specific OIDC setup guide. Preserve the {provider} placeholder exactly and make the phrase grammatical.',{
'ar':'دليل إعداد موفّر الهوية {provider} (يفتح في علامة تبويب جديدة)',
'es':'Guía de configuración del proveedor de identidad {provider} (se abre en una pestaña nueva)',
'ja':'ID プロバイダー {provider} の設定ガイド（新しいタブで開く）',
'ko':'ID 공급자 {provider} 설정 가이드 (새 탭에서 열립니다)',
'vi':'Hướng dẫn thiết lập nhà cung cấp danh tính {provider} (mở trong tab mới)',
'zh-Hant':'身份提供者 {provider} 設定指南（在新分頁中開啟）'})
put(268,'correction','Pinned caller is a confidence/status badge: provider_suggestion means provider-suggested content that needs human review, not a provider rating. Render “review” as an instruction/status.',{
'de':'Vorschlag des Anbieters · prüfen',
'es':'Sugerencia del proveedor · revisar',
'hi':'प्रदाता का सुझाव · समीक्षा आवश्यक',
'ja':'プロバイダーの提案 · 要確認',
'ko':'공급자 제안 · 검토 필요',
'pt-BR':'Sugestão do provedor · revisar',
'vi':'Đề xuất của nhà cung cấp · cần xem xét'})
put(283,'correction','The pinned button publishes gamelist data under metadata root. Put the ES-DE product name together with its data in natural order.',{
'ar':'نشر بيانات ES-DE','de':'ES-DE-Daten veröffentlichen'})
put(284,'correction','This is a count-bearing completion message. Preserve {count} and use grammatical number/order for “{count} ES-DE entries published.”',{
'ar':'تم نشر {count} من إدخالات ES-DE.',
'es':'Se publicaron {count} entradas de ES-DE.',
'fr':'{count} entrées ES-DE publiées.',
'id':'Sebanyak {count} entri ES-DE telah diterbitkan.',
'ko':'ES-DE 항목 {count}개를 게시했습니다.',
'pt-BR':'Foram publicadas {count} entradas de ES-DE.'})

assert out.exists() and [p.name for p in out.iterdir()]==['build_blind_review.py']
subprocess.check_call(['sha256sum','-c','SHA256SUMS.txt'],cwd=input_dir,stdout=subprocess.DEVNULL)
manifest=json.loads((input_dir/'manifest.json').read_text(encoding='utf-8'))
rows=[json.loads(l) for l in (input_dir/'current-target-cells.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
sources=[json.loads(l) for l in (input_dir/'source-contexts.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
holds=[json.loads(l) for l in (input_dir/'caller-resolution-holds.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
assert manifest['head']==head and manifest['tree']==tree and len(rows)==240
assert len(sources)==20 and len(holds)==168
hold_keys={(r['position'],r['locale']):r for r in holds}
source_by_pos={r['position']:r for r in sources}
ledger=[]
for r in rows:
 key=(r['position'],r['locale'])
 assert r['head']==head and r['tree']==tree and r['placeholderMultisetMatchesSource']
 if key in hold_keys:
  h=hold_keys[key]; disp='hold'; target=None; rationale=h['holdReason']
 elif key in changes:
  disp,target,rationale=changes[key]
 else:
  disp='accept-current';target=r['currentTarget'];rationale='Current target accurately conveys the pinned source and caller semantics; source identity, metadata, and placeholders are preserved.'
 if target is not None:
  assert sorted([t for t in r['sourcePlaceholders']])==sorted([t for t in r['targetPlaceholders']]),key
  target_hash=tsha(target)
 else:target_hash=None
 ctx=source_by_pos[r['position']]
 ledger.append({'head':head,'tree':tree,'position':r['position'],'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':r['sourceSha256'],'locale':r['locale'],'catalogPath':r['catalogPath'],'catalogFileSha256':r['catalogSha256'],'catalogGitBlob':r['catalogGitBlob'],'currentTarget':r['currentTarget'],'currentTargetSha256':r['currentTargetSha256'],'recommendedDisposition':disp,'recommendedTarget':target,'recommendedTargetSha256':target_hash,'changeFromCurrent':target is not None and target!=r['currentTarget'],'selectedForApplication':False,'placeholderMultisetMatchesSource':r['placeholderMultisetMatchesSource'],'sourcePlaceholders':r['sourcePlaceholders'],'targetPlaceholders':r['targetPlaceholders'],'callerReferenceCount':ctx['callerReferenceCount'],'currentCallerLocations':ctx['currentCallerLocations'],'callerContextSha256':ctx['references'][0]['contextSha256'] if ctx.get('references') else None,'rationale':rationale,'inputRowSha256':sha(jl(r).encode('utf-8'))})
counts=collections.Counter(r['recommendedDisposition'] for r in ledger)
assert len(ledger)==240 and counts['hold']==168 and sum(r['changeFromCurrent'] for r in ledger)==sum(counts[x] for x in ('correction','refinement'))
assert all(r['recommendedTarget'] is None and not r['changeFromCurrent'] for r in ledger if r['recommendedDisposition']=='hold')

out.mkdir(parents=True,exist_ok=True)
ledger_path=out/'blind-decisions.jsonl'
ledger_path.write_text(''.join(jl(r)+'\n' for r in ledger),encoding='utf-8')
input_checksum_list_sha=sha((input_dir/'SHA256SUMS.txt').read_bytes())
manifest_json_sha=sha((input_dir/'manifest.json').read_bytes())
summary={'schemaVersion':1,'reviewer':'independent blind machine review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W265-W284','head':head,'tree':tree,'candidateFreeInputChecksumListSha256':input_checksum_list_sha,'candidateFreeManifestJsonSha256':manifest_json_sha,'sourceCount':20,'localeCount':12,'cellCount':240,'dispositions':dict(sorted(counts.items())),'recommendedChangedCells':sum(r['changeFromCurrent'] for r in ledger),'callerPathHoldCells':counts['hold'],'heldPositions':sorted({r['position'] for r in ledger if r['recommendedDisposition']=='hold'}),'recommendationsSelectedForApplication':0,'qualifiedNativeSpeakerApproval':False,'exactHeadBrowserReview':False,'releaseApproved':False}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'provenance.json').write_text(json.dumps({'reviewMethod':'independent blind target review from checksummed candidate-free input; no primary review consulted','inputDirectory':str(input_dir),'inputChecksumListSha256':input_checksum_list_sha,'candidateFreeManifestJsonSha256':manifest_json_sha,'head':head,'tree':tree,'sealedBeforePrimaryReviewCompletion':True,'positionsWithCallerPathHolds':summary['heldPositions'],'holdDisposition':'preserve current cell; no target selected'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'README.md').write_text(f'''# ROMarrNG PR #70 W265–W284 independent blind review\n\nThis packet covers 20 active source IDs × 12 locales (240 cells) at exact head `{head}` / tree `{tree}` from candidate-free input `{input_dir}`. It was sealed without consulting the primary review.\n\nRanks 269–282 remain caller-path holds (168 cells): the pinned API returns dynamic provider/Prowlarr diagnostic strings and the UI renders them without explicit localized templates. No targets are recommended for these values. The other 72 cells have direct, pinned caller context.\n\nDisposition counts: {dict(sorted(counts.items()))}. Recommended changed cells: {summary['recommendedChangedCells']}. The row ledger records hashes, targets, exact caller pins, and rationales. Recommendations are not selected for application until cross-audit. Native-speaker approval and exact-head browser review are not established. This packet does not approve a release.\n''',encoding='utf-8')
seal={'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W265-W284','head':head,'tree':tree,'candidateFreeInputChecksumListSha256':input_checksum_list_sha,'candidateFreeManifestJsonSha256':manifest_json_sha,'blindLedgerSha256':sha(ledger_path.read_bytes()),'cellCount':240,'dispositionCounts':dict(sorted(counts.items())),'recommendedChangedCells':summary['recommendedChangedCells'],'callerPathHoldCells':counts['hold'],'primaryReviewNotConsulted':True}
(out/'blind-seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files=sorted(p for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS.txt')
(out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n' for p in files),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
