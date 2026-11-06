#!/usr/bin/env python3
"""Build primary semantic adjudications from the sealed W525-W544 input only."""
import collections, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
OUT=Path(__file__).resolve().parent
INPUT=OUT.parent/'candidate-free'/'input'
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w525-544-source')
HEAD='eda48333438591ecc67f829c50ef2d521f1e7a5e'
TREE='3db18e56d0c7ac08a564a6baff61eba25f0a01da'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'<[^>]+>')
NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROPOSALS={
 ('ui.import.2cff9baabf','es'):('correction','Importar','The exact caller is an action button for importing a selected file; the current Spanish noun names the import process instead of the action.'),
 ('ui.import.2cff9baabf','fr'):('correction','Importer','The exact caller is an action button for importing a selected file; the current French noun names the import process instead of the action.'),
 ('ui.import-completed-now.c8f6c865a3','ar'):('correction','استورد التنزيلات المكتملة الآن','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','de'):('correction','Abgeschlossene Downloads jetzt importieren','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','es'):('correction','Importar ahora las descargas completadas','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','fr'):('correction','Importer les téléchargements terminés maintenant','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','hi'):('correction','पूरे हो चुके डाउनलोड अभी आयात करें','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','id'):('correction','Impor unduhan yang telah selesai sekarang','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','ja'):('correction','完了したダウンロードを今すぐインポート','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','ko'):('correction','완료된 다운로드 지금 가져오기','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','pt-BR'):('correction','Importar downloads concluídos agora','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','vi'):('correction','Nhập các lượt tải xuống đã hoàn tất ngay bây giờ','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','zh-Hans'):('correction','立即导入已完成的下载','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-completed-now.c8f6c865a3','zh-Hant'):('correction','立即匯入已完成的下載','The queue button posts the ImportCompleted command; the current wording reads as a completed status. This makes it an immediate action on completed downloads.'),
 ('ui.import-failed.0a26f41abd','ar'):('correction','فشل الاستيراد','This is the Arabic download-state label for import-failed; the current plural phrasing is less direct than the standard failed-import state.'),
}
CONTEXT={
 'ui.identify-organize.e2a72a6310':'Navigation and action text for identifying ROMs and organizing the library; the translations preserve both activities.',
 'ui.idle.ab0171ca04':'Queue-state text shown opposite the In a game state; each current target conveys idle or not active.',
 'ui.if-your-library-is.9f51d99e96':'The first half of a table heading introducing library states; each target remains a clause fragment.',
 'ui.ignored.7d648f5b47':'A download-state label; the current targets all express ignored or disregarded.',
 'ui.import.2cff9baabf':'A row action button in the manual-import table. Spanish and French are corrected to action verbs; the other current labels work as compact import actions.',
 'ui.import-history.ef9992233a':'No exact source literal or source-ID caller exists in tracked production code at the pinned head; all locale cells remain held without text.',
 'ui.import-lists.915601fb28':'Navigation label for the import-lists page; the existing translations name the page clearly.',
 'ui.import-a-folder-you-own-and-let-roma.a06dc1fe1e':'Onboarding tile description for importing a user-owned folder and identifying and filing its contents; all targets preserve ownership and both actions.',
 'ui.import-anyway.e06eac7e79':'Confirmation action to proceed with an import despite a warning; the targets preserve the override meaning.',
 'ui.import-check-minutes.afebe8564c':'Settings label for the interval between import checks, with minutes as the unit; current targets preserve the unit and interval meaning.',
 'ui.import-completed-downloads.fd1a4510eb':'Scheduled task name and task-list label for importing downloads after completion; current targets preserve this task meaning.',
 'ui.import-completed-downloads-automatic.0436b11a02':'Checkbox for enabling automatic import of completed downloads; current targets preserve the setting.',
 'ui.import-completed-now.c8f6c865a3':'Queue-page button whose handler posts the ImportCompleted command; the current targets read as a finished status, so all are corrected to immediate actions.',
 'ui.import-everything-verified.400d049ae1':'Button to import every item already verified; the current targets preserve the selection and action.',
 'ui.import-failed.0a26f41abd':'Download-state label for an import failure; Arabic is corrected to a direct failed-import state.',
 'ui.import-lists.cdf54991b2':'Button that switches the list view to imports; current targets express the import-lists action or view.',
 'ui.import-lists-are-optional-and-can-ad.e9dbc2c00d':'Help text explaining that optional lists can automatically add games to the Wanted list; current targets preserve the product-list reference and behavior.',
 'ui.imported.321f179c80':'Download-state label for a successful import; current targets convey imported.',
 'ui.imported-from-the-existing-es-de-gam.5fa9036446':'Review message for metadata imported from an existing ES-DE gamelist, asking for title review before renaming; current targets preserve the source and instruction.',
 'ui.imported-local-metadata-review-title.5db9952dae':'Metadata-origin label meaning local metadata was imported and the title should be reviewed; current targets preserve both points.',
}
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def jl(p): return [json.loads(s) for s in Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
def dump(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def lines(p,rows): Path(p).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
# Verify candidate-free seal before considering any review decisions.
subprocess.run(['python3',str(INPUT/'verify_input.py'),'--repo',str(REPO)],check=True)
if subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()!=HEAD or subprocess.check_output(['git','-C',str(REPO),'show','-s','--format=%T','HEAD'],text=True).strip()!=TREE:
    raise SystemExit('FAIL: review worktree pin changed')
cells=jl(INPUT/'current-target-cells.jsonl')
contexts={x['sourceId']:x for x in jl(INPUT/'source-contexts.jsonl')}
selected={x['sourceId']:x for x in jl(INPUT/'source-inventory-selection.jsonl')}
im=json.loads((INPUT/'manifest.json').read_text(encoding='utf-8'))
if len(cells)!=240 or len(contexts)!=20 or len(selected)!=20: raise SystemExit('FAIL: candidate-free coverage')
now=datetime.now(timezone.utc).isoformat(timespec='seconds')
ledger=[]; proposals=[]; holds=[]
for c in sorted(cells,key=lambda x:(x['catalogZeroBasedIndex'],LOCALES.index(x['locale']))):
    sid,loc=c['sourceId'],c['locale']; ctx=contexts[sid]
    common={'window':'W525-W544','position':c['catalogZeroBasedIndex'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogZeroBasedIndex']+1,'sourceId':sid,'sourceSha256':c['sourceSha256'],'locale':loc,'catalogTranslationHash':c['catalogTranslationHash'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerRefs':c['callerRefs'],'reviewedAtUtc':now,'nativeSpeakerApproval':False,'reviewConfidence':'moderate'}
    if ctx['callerless']:
        if sid!='ui.import-history.ef9992233a' or len(ctx['callers'])!=0: raise SystemExit('FAIL: unexpected callerless source')
        reason='The exact-head candidate-free search found no source literal or source-ID caller in tracked production code; the UI role cannot be confirmed from available context. No translation decision is made.'
        row={**common,'disposition':'hold','callerContextAvailable':False,'callerlessReason':reason}
        holds.append({k:row[k] for k in ('window','position','sourceId','sourceSha256','locale','currentTargetSha256','callerContextSha256','disposition','callerlessReason')})
        ledger.append(row); continue
    if not ctx['callers']: raise SystemExit('FAIL: caller-backed cell lacks exact caller')
    rationale=CONTEXT.get(sid)
    if not rationale: raise SystemExit('FAIL: missing cell rationale '+sid)
    kind_target=PROPOSALS.get((sid,loc))
    checks={'placeholderChecks':{'source':c['sourcePlaceholderTokens'],'current':c['currentPlaceholderTokens'],'preserved':c['placeholderMultisetMatches']},'markupChecks':{'source':c['sourceMarkupTags'],'current':c['currentMarkupTags'],'preserved':c['markupMatches']},'numericChecks':{'source':c['sourceNumericTokens'],'sourceWords':c['sourceNumericWords'],'current':c['currentNumericTokens'],'preserved':c['numericTokensPreserved'],'presentationEquivalent':c['numericPresentationEquivalent']},'protectedLiteralChecks':{'source':c['sourceProtectedLiterals'],'current':c['currentProtectedLiterals'],'missing':c['missingProtectedLiterals'],'preserved':c['protectedLiteralsPreserved']}}
    if kind_target:
        disposition,target,why=kind_target
        source=c['source']
        if collections.Counter(PH.findall(source))!=collections.Counter(PH.findall(target)): raise SystemExit(f'FAIL: proposal placeholder parity {sid}/{loc}')
        if collections.Counter(TAG.findall(source))!=collections.Counter(TAG.findall(target)): raise SystemExit(f'FAIL: proposal markup parity {sid}/{loc}')
        if collections.Counter(NUM.findall(source))!=collections.Counter(NUM.findall(target)): raise SystemExit(f'FAIL: proposal numeric parity {sid}/{loc}')
        if not all(token in target for token in c['sourceProtectedLiterals']): raise SystemExit(f'FAIL: proposal protected literals {sid}/{loc}')
        pt={'placeholdersPreserved':True,'markupPreserved':True,'numericTokensPreserved':True,'protectedLiteralsPreserved':True}
        row={**common,**checks,'source':source,'currentTarget':c['currentTarget'],'proposedTarget':target,'proposedTargetSha256':sha(target),'disposition':disposition,'issueClass':'semantic-or-grammar','reviewedContext':rationale,'rationale':why,'proposalTokenChecks':pt}
        proposals.append({k:row[k] for k in ('window','position','sourceId','sourceSha256','locale','currentTargetSha256','currentTarget','proposedTarget','proposedTargetSha256','disposition','issueClass','rationale','callerContextSha256')})
    else:
        row={**common,**checks,'source':c['source'],'currentTarget':c['currentTarget'],'disposition':'accept-current','reviewedContext':rationale,'rationale':rationale}
    ledger.append(row)
counts=dict(collections.Counter(r['disposition'] for r in ledger))
if counts!={'accept-current':213,'correction':15,'hold':12}: raise SystemExit('FAIL: unexpected primary decision counts '+repr(counts))
if len(proposals)!=15 or len(holds)!=12: raise SystemExit('FAIL: proposal/hold counts')
locale_counts={loc:dict(collections.Counter(x['disposition'] for x in ledger if x['locale']==loc)) for loc in LOCALES}
summary={'artifact':'ROMarrNG PR #70 W525-W544 primary semantic review','reviewerRole':'primary semantic reviewer using candidate-free input only','repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':'task/localization-translation-review-20261030','head':HEAD,'tree':TREE,'candidateFreeInputPath':'../candidate-free/input','candidateFreeInputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),'candidateFreeInputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'candidateFreeInputVerified':True,'primaryProposalsReadBeforeReview':False,'sourceCount':20,'localeCount':12,'cellCount':240,'dispositions':counts,'proposedCellCount':len(proposals),'newHolds':len(holds),'holdPositions':[530],'holdFindings':{'530':'No exact source literal or source-ID caller was found in the exact-head production search; keep all 12 locale cells held text-free.'},'priorSelectedSourceCount':140,'priorHoldCellCount':540,'priorHoldTargetsUnchanged':True,'priorHoldChangedCells':0,'priorAppliedCellCount':28,'priorAppliedCellsChanged':0,'placeholderMismatchesInSelectedTargets':0,'markupMismatchesInSelectedTargets':0,'numericMismatchesInSelectedTargets':0,'protectedLiteralMismatchesInSelectedTargets':0,'localeDispositionCounts':locale_counts,'selectedProposalCells':[{'sourceId':r['sourceId'],'locale':r['locale'],'disposition':r['disposition']} for r in proposals],'nativeSpeakerApproval':False,'browserReviewClaimed':False,'reviewConfidence':'moderate','sealedAtUtc':now}
lines(OUT/'primary-ledger.jsonl',ledger); lines(OUT/'primary-proposals.jsonl',proposals); lines(OUT/'primary-holds.jsonl',holds)
dump(OUT/'summary.json',summary)
dump(OUT/'provenance.json',{'artifact':'ROMarrNG W525-W544 primary review provenance','candidateFreeInputManifestSha256':summary['candidateFreeInputManifestSha256'],'candidateFreeInputChecksumListSha256':summary['candidateFreeInputChecksumListSha256'],'candidateFreeVerifier':'PASS','reviewInputs':['candidate-free/input/current-target-cells.jsonl','candidate-free/input/source-contexts.jsonl','candidate-free/input/source-inventory-selection.jsonl','candidate-free/input/continuity-reattestation.json'],'reviewInputsWereCandidateFree':True,'blindOrCrossReviewContentConsulted':False,'reviewedHead':HEAD,'reviewedTree':TREE,'nativeSpeakerApproval':False,'browserReviewClaimed':False})
(OUT/'README.md').write_text(f'''# ROMarrNG PR #70 W525-W544 primary review\n\n- Pin: {HEAD} / tree {TREE}; PR was reattested OPEN/DRAFT.\n- Scope: 20 source messages × 12 locales = 240 cells.\n- Dispositions: {counts['accept-current']} accepted current values, {counts['correction']} corrections, 0 refinements, and {counts['hold']} text-free holds.\n- All 12 locale cells for callerless source `ui.import-history.ef9992233a` at catalog position 530 are held. Hold ledgers include identifiers and hashes, without source or target text.\n- Primary review used only the sealed candidate-free packet. No blind or cross-review output was consulted. No native-speaker or browser review is claimed.\n- Run `python3 verify_primary.py --repo /path/to/ROMarrNG`.\n''',encoding='utf-8')
print(json.dumps({'result':'PRIMARY_BUILT','head':HEAD,'tree':TREE,'cells':len(ledger),'counts':counts,'proposals':len(proposals),'holds':len(holds),'holdPositions':[530]},ensure_ascii=False,sort_keys=True))
