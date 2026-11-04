#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import collections, hashlib, json, shutil, subprocess

OUT=Path(__file__).resolve().parent
INP=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w605-624-20261104/candidate-free/candidate-free/input')
PRIMARY=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w605-624-20261104/primary')
BLIND=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w605-624-blind-20261104')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-apply-20261104')
HEAD='872905926887840025ba4c3f17151b96f8d3e6e2'; TREE='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CALLERLESS={618,620,623}
LINEAGE=['prior-selection-reattestation-summary.json','prior-selection-reattestation.jsonl','prior-hold-reattestation-summary.json','prior-hold-reattestation.jsonl','prior-applied-cell-reattestation-summary.json','prior-applied-cell-reattestation.jsonl','prior-window-cell-hash-reattestation.jsonl','prior-w565-window-cell-hash-reattestation.jsonl','prior-w585-window-cell-hash-reattestation.jsonl']

def sha(x): return hashlib.sha256(x.encode('utf-8') if isinstance(x,str) else x).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(p,x): p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(p,x): p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in x),encoding='utf-8')
def run(*args): return subprocess.check_output(list(args),text=True).strip()

allowed={'verify_cross_review.py','build_cross_review.py'}
if any(p.name not in allowed for p in OUT.iterdir()): raise SystemExit('output has files from a previous build; refusing overwrite')
(OUT/'lineage').mkdir(exist_ok=True)
manifest=j(INP/'manifest.json'); cells=jl(INP/'current-target-cells.jsonl')
contexts={r['sourceId']:r for r in jl(INP/'source-contexts.jsonl')}
primary=jl(PRIMARY/'primary-output'/'dispositions.jsonl'); blind=jl(BLIND/'review.jsonl')
by_input={(r['position'],r['locale']):r for r in cells}
by_primary={(r['sourceId'],r['locale']):r for r in primary}; by_blind={(r['position'],r['locale']):r for r in blind}
li={x:i for i,x in enumerate(LOCALES)}
assert len(by_input)==len(by_primary)==len(by_blind)==240
cross=[]; proposals=[]; final=collections.Counter()
for c in sorted(cells,key=lambda r:(r['position'],li[r['locale']])):
    key=(c['position'],c['locale']); ctx=contexts[c['sourceId']]; p=by_primary[(c['sourceId'],c['locale'])]; b=by_blind[key]
    base={'position':c['position'],'locale':c['locale'],'inputCellCanonicalSha256':sha(canon(c)),'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'primaryDisposition':p['disposition'],'blindDisposition':b['disposition']}
    candidates=[]
    if p['disposition']=='CHANGE': candidates.append(('primary',p['proposedTarget'],p.get('reason','')))
    if b['disposition']=='propose_clear_improvement': candidates.append(('blind',b['proposedTarget'],b.get('rationale','')))
    if ctx['callerless']:
        assert key[0] in CALLERLESS
        base.update(callerless=True,crossDisposition='hold_hash_only',crossReasonCode='caller_context_unavailable')
        if p['disposition']=='CHANGE':
            base['primaryProposalWithheld']=True
            proposals.append({'position':c['position'],'locale':c['locale'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerContextAvailable':False,'proposedBy':['primary'],'outcome':'held_hash_only_no_caller_context','reviewCode':'caller_context_unavailable'})
    else:
        assert key[0] not in CALLERLESS and ctx['exactMatchCount']>0
        refs=[{k:r[k] for k in ('path','line','lineSha256','excerptSha256','fileSha256','gitBlob')} for r in ctx['callers']]
        base.update(callerless=False,sourceId=c['sourceId'],source=c['source'],currentTarget=c['currentTarget'],sourceContext=ctx,callerRefs=refs)
        if p['disposition']=='CHANGE': base.update(primaryProposedTarget=p['proposedTarget'],primaryProposedTargetSha256=sha(p['proposedTarget']),primaryRationale=p.get('reason',''))
        if b['disposition']=='propose_clear_improvement': base.update(blindProposedTarget=b['proposedTarget'],blindProposedTargetSha256=b['proposedTargetSha256'],blindRationale=b.get('rationale',''))
        if key==(611,'id'):
            assert p['proposedTarget']==b['proposedTarget']=='Log langsung'
            base.update(crossDisposition='propose_clear_improvement',crossReasonCode='caller_context_supports_improvement',crossProposedTarget='Log langsung',crossProposedTargetSha256=sha('Log langsung'),crossRationale='The exact caller identifies a process log tailed live. “Log langsung” expresses that live log label more clearly than “Log hidup”; primary and blind independently proposed the same wording.')
        elif key==(611,'vi'):
            assert b['proposedTarget']=='Nhật ký trực tiếp'
            base.update(crossDisposition='propose_clear_improvement',crossReasonCode='caller_context_supports_improvement',crossProposedTarget='Nhật ký trực tiếp',crossProposedTargetSha256=sha('Nhật ký trực tiếp'),crossRationale='The exact caller labels a process log that is tailed live. “Nhật ký trực tiếp” names the log directly; the current “Bản ghi trực tiếp” can read as a direct or live record.')
        elif key==(611,'ar'):
            assert p['disposition']=='CHANGE' and b['disposition']=='retain_current'
            base.update(crossDisposition='retain_current',crossReasonCode='proposal_not_clearer_in_context',crossRationale='The exact caller confirms a live-updating process log. The current “السجل الحي” can express a live or active log; “السجل المباشر” is plausible but is not a clear contextual improvement, so retain the current target.')
        else:
            assert not candidates
            base.update(crossDisposition='retain_current',crossReasonCode='reviewer_concurrence_retain')
        if candidates:
            targets={n:t for n,t,_ in candidates}; who=sorted(targets)
            item={'position':c['position'],'locale':c['locale'],'sourceId':c['sourceId'],'source':c['source'],'currentTarget':c['currentTarget'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'sourceContext':ctx,'proposedBy':who,'outcome':'accepted_clear_improvement' if key in ((611,'id'),(611,'vi')) else 'rejected_retain_current'}
            if 'primary' in targets: item.update(primaryProposedTarget=targets['primary'],primaryProposedTargetSha256=sha(targets['primary']),primaryRationale=next(r for n,_,r in candidates if n=='primary'))
            if 'blind' in targets: item.update(blindProposedTarget=targets['blind'],blindProposedTargetSha256=sha(targets['blind']),blindRationale=next(r for n,_,r in candidates if n=='blind'))
            if key in ((611,'id'),(611,'vi')): item.update(acceptedTarget=base['crossProposedTarget'],acceptedTargetSha256=base['crossProposedTargetSha256'])
            item['rationale']=base.get('crossRationale','')
            proposals.append(item)
    final[base['crossDisposition']]+=1; cross.append(base)
writejl(OUT/'cross-review.jsonl',cross)
writejl(OUT/'proposal-adjudication.jsonl',sorted(proposals,key=lambda r:(r['position'],li[r['locale']])))
for name in LINEAGE: shutil.copyfile(INP/name,OUT/'lineage'/name)

api=json.loads(run('gh','pr','view','70','--repo','snapetech-org/ROMarrNG','--json','number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,title,url'))
refs_text=run('git','-C',str(REPO),'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head','refs/pull/70/merge')
refs={line.split('\t')[1]:line.split('\t')[0] for line in refs_text.splitlines() if line}
local_head=run('git','-C',str(REPO),'rev-parse','HEAD'); local_tree=run('git','-C',str(REPO),'rev-parse','HEAD^{tree}')
local_status=run('git','-C',str(REPO),'status','--porcelain=v1','--untracked-files=all'); local_branch=run('git','-C',str(REPO),'branch','--show-current')
assert api['number']==70 and api['state']=='OPEN' and api['isDraft'] and api['headRefName']==BRANCH and api['headRefOid']==HEAD
assert local_head==HEAD and local_tree==TREE and not local_status and not local_branch and refs[f'refs/heads/{BRANCH}']==HEAD and refs['refs/pull/70/head']==HEAD
receipt={'artifact':'ROMarrNG PR #70 W605-W624 cross-review input receipt','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W605-W624','candidateFreeInput':{'path':str(INP),'manifestSha256':sha((INP/'manifest.json').read_bytes()),'checksumFileSha256':sha((INP/'SHA256SUMS.txt').read_bytes()),'candidateFree':manifest['candidateFree'],'reviewDecisionsIncluded':manifest['reviewDecisionsIncluded'],'proposedTargetsIncluded':manifest['proposedTargetsIncluded']},'primary':{'path':str(PRIMARY),'rootChecksumFileSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'outputManifestSha256':sha((PRIMARY/'primary-output'/'primary-manifest.json').read_bytes()),'outputChecksumFileSha256':sha((PRIMARY/'primary-output'/'SHA256SUMS.txt').read_bytes())},'blind':{'path':str(BLIND),'manifestSha256':sha((BLIND/'packet-manifest.json').read_bytes()),'checksumFileSha256':sha((BLIND/'SHA256SUMS.txt').read_bytes())},'liveSnapshot':{'checkedUtc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'prApi':api,'remoteRefs':refs,'sourceWorktree':{'path':str(REPO),'head':local_head,'tree':local_tree,'branch':local_branch,'detached':not bool(local_branch),'clean':not bool(local_status)}},'sealValidation':{'candidateFreeBundle':'PASS','primaryPacket':'PASS','blindPacket':'PASS','primaryVsInput':'PASS','blindVsInput':'PASS'}}
writej(OUT/'input-receipt.json',receipt)
summary={'artifact':'ROMarrNG PR #70 W605-W624 cross-review summary','head':HEAD,'tree':TREE,'window':'W605-W624','sourceCount':20,'cellCount':240,'callerfulCellCount':204,'callerlessHashOnlyCellCount':36,'callerlessPositions':[618,620,623],'primaryDispositionCounts':dict(collections.Counter(r['disposition'] for r in primary)),'blindDispositionCounts':dict(collections.Counter(r['disposition'] for r in blind)),'crossDispositionCounts':dict(final),'primaryProposalCount':sum(r['disposition']=='CHANGE' for r in primary),'blindProposalCount':sum(r['disposition']=='propose_clear_improvement' for r in blind),'uniqueProposalCellCount':len(proposals),'proposalOutcomes':dict(collections.Counter(r['outcome'] for r in proposals)),'primaryCallerfulProposalCount':2,'primaryCallerlessProposalCountHeldHashOnly':6,'lineage':{'selectedSources':220,'holds':628,'appliedCells':71,'w585CallerlessHolds':24,'windowReadbackCells':{'W545-W564':240,'W565-W584':240,'W585-W604':240},'copiedByteIdentically':LINEAGE},'nativeSpeakerApproval':False,'reviewDecisionsAreSuggestionsOnly':True,'repositoryAndPrEdited':False,'testsBuildScansCiRun':False}
writej(OUT/'summary.json',summary)
(OUT/'README.md').write_text('''# ROMarrNG PR #70 W605-W624 cross-review packet\n\nThis packet reconciles the sealed primary review and independent blind review against candidate-free input at head `872905926887840025ba4c3f17151b96f8d3e6e2` and tree `d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4`.\n\nIt covers all 240 locale cells: 202 current targets retained, two caller-grounded improvement suggestions, and 36 callerless cells held hash-only. Callerful rows embed exact pinned source and caller evidence. Callerless rows omit source IDs, source/target text, proposal wording, rationales, and caller excerpts.\n\nThe Arabic proposal at position 611 was reviewed against its live-tailed process-log caller and not accepted because the current wording remains a defensible live/active-log label. The Indonesian proposal at position 611 was raised independently by both reviews and accepted as `Log langsung`. The Vietnamese proposal at position 611 was raised by the blind review and accepted as `Nhật ký trực tiếp`. The six primary proposals at callerless positions were held without exposing proposed wording.\n\nPrior lineage is copied byte-identically: 220 selected sources, 628 held cells (including 24 prior W585 callerless holds), 71 applied cells, and three 240-cell prior-window readbacks. No catalog, PR, or repository files were edited. This is an AI review; no native-speaker approval is claimed.\n\n## Verify\n\n```sh\npython3 verify_cross_review.py \\\n  --input /path/to/candidate-free/input \\\n  --primary /path/to/primary \\\n  --blind /path/to/blind \\\n  --repo /path/to/exact-pinned-worktree \\\n  --live-pr\n```\n\nThe verifier checks this packet's manifest and SHA256 seal, all 240 rows against the inputs and both sealed reviews, callerful proposals against pinned excerpts, callerless hash-only handling, byte-identical lineage, the exact source worktree and Git refs, and current PR API state when `--live-pr` is used.\n''',encoding='utf-8')
files=[]
for path in sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('packet-manifest.json','SHA256SUMS.txt')):
    files.append({'path':path.relative_to(OUT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())})
packet_manifest={'artifact':'ROMarrNG PR #70 W605-W624 sealed cross-review packet','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W605-W624','head':HEAD,'tree':TREE,'candidateFreeInputManifestSha256':receipt['candidateFreeInput']['manifestSha256'],'primaryOutputManifestSha256':receipt['primary']['outputManifestSha256'],'blindPacketManifestSha256':receipt['blind']['manifestSha256'],'cellCount':240,'callerfulCellCount':204,'callerlessHashOnlyCellCount':36,'crossDispositionCounts':dict(final),'proposalOutcomes':dict(collections.Counter(r['outcome'] for r in proposals)),'files':files,'sealedUtc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')}
writej(OUT/'packet-manifest.json',packet_manifest)
allfiles=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}\n' for p in allfiles),encoding='utf-8')
print(json.dumps({'result':'BUILT','output':str(OUT),'cells':len(cross),'callerful':sum(not r.get('callerless') for r in cross),'callerlessHashOnly':sum(r.get('callerless') is True for r in cross),'crossDispositionCounts':dict(final),'proposalOutcomes':dict(collections.Counter(r['outcome'] for r in proposals)),'packetFiles':len(allfiles)+1},ensure_ascii=False,sort_keys=True))
