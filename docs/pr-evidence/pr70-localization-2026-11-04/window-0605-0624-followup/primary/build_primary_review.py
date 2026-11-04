#!/usr/bin/env python3
"""Create a fresh primary semantic review only after candidate-free seal verification."""
from __future__ import annotations
import collections, hashlib, json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
TASK=OUT.parent
CF=TASK/'candidate-free'
INPUT=CF/'candidate-free/input'
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-apply-20261104')
HEAD='872905926887840025ba4c3f17151b96f8d3e6e2'
TREE='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PRODUCT='d44e61d9960c788412da0fadbb8b67744b70e404'
PROPOSALS={
 (611,'ar'):('السجل المباشر','The label refers to a live, updating log; المباشر is more natural than الحي for this interface feature.','moderate'),
 (611,'id'):('Log langsung','Hidup reads as living; langsung better expresses a live or updating log label.','moderate'),
 (618,'ko'):('로컬 경로','지역 경로 reads as a regional path; 로컬 is the established computing term for a local path.','high'),
 (623,'de'):('Nur Magnetlinks. Linksnappy fügt Torrents im pausierten Zustand hinzu, daher startet ROMarr sie im Stammordner des Kontos, bevor etwas heruntergeladen wird.','Magnetlinks is the standard German term for magnet URLs; the current plural Magnets is unclear, and the revised sentence describes the paused torrent state directly.','moderate'),
 (623,'es'):('Solo enlaces magnet. Linksnappy añade los torrents en pausa, así que ROMarr los inicia en la carpeta raíz de la cuenta antes de que descarguen nada.','Enlaces magnet identifies the link type more clearly than the English plural magnets; the paused state is expressed idiomatically.','moderate'),
 (623,'fr'):('Liens magnet uniquement. Linksnappy ajoute les torrents en pause, donc ROMarr les démarre dans le dossier racine du compte avant tout téléchargement.','Liens magnet names the link type explicitly; the rest uses a concise paused-state construction.','moderate'),
 (623,'pt-BR'):('Apenas links magnet. O Linksnappy adiciona torrents pausados, então o ROMarr os inicia na pasta raiz da conta antes que qualquer coisa seja baixada.','Links magnet is clearer than the English plural magnets in Brazilian Portuguese; the revised wording preserves the paused state and download sequence.','moderate'),
 (623,'id'):('Hanya tautan magnet. Linksnappy menambahkan torrent dalam keadaan berhenti, jadi ROMarr memulainya di folder root akun sebelum mengunduh apa pun.','Tautan magnet identifies the link type explicitly instead of the ambiguous borrowed plural magnet.','moderate')
}

def sha(b):
    if isinstance(b,str): b=b.encode()
    return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def readj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def dumpj(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def dumpl(p,x): Path(p).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in x),encoding='utf-8')
def api():
    d=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/ROMarrNG/pulls/70'],text=True))
    refs={}
    raw=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head'],text=True)
    for line in raw.splitlines():
        if line.strip():
            oid,ref=line.split('\t',1); refs[ref]=oid
    body=d.get('body') or ''
    result={'state':d['state'].upper(),'draft':d['draft'],'merged':d['merged'],'headRef':d['head']['ref'],'head':d['head']['sha'],'branchRef':refs.get(f'refs/heads/{BRANCH}'),'pullRef':refs.get('refs/pull/70/head'),'bodySha256':sha(body),'bodyBytes':len(body.encode())}
    if (result['state'],result['draft'],result['merged'],result['headRef'],result['head'],result['branchRef'],result['pullRef'])!=('OPEN',True,False,BRANCH,HEAD,HEAD,HEAD):
        raise SystemExit('FAIL: live PR alignment during primary review: '+repr(result))
    return result

if any(p.name!='build_primary_review.py' for p in OUT.iterdir()):
    raise SystemExit('FAIL: primary output directory contains prior artifacts')
subprocess.run(['python3',str(CF/'verify_bundle.py'),'--repo',str(REPO)],check=True,stdout=subprocess.DEVNULL)
candidate_manifest=readj(CF/'bundle-manifest.json')
candidate_input_manifest=readj(INPUT/'manifest.json')
candidate_checksums=CF/'SHA256SUMS.txt'
candidate_checksum_sha=sha(candidate_checksums.read_bytes())
if (candidate_manifest['head'],candidate_manifest['tree'],candidate_manifest['window'])!=(HEAD,TREE,'W605-W624'):
    raise SystemExit('FAIL: candidate-free sealed pin')
pr_before=api()
pre_att=readj(INPUT/'PR-attestation-before.json')
if pr_before['bodySha256']!=pre_att['bodySha256'] or pr_before['bodyBytes']!=pre_att['bodyBytes']:
    raise SystemExit('FAIL: PR body changed since candidate-free seal')
copy=OUT/'candidate-free-bundle'
shutil.copytree(CF,copy)
copy_sum_sha=sha((copy/'SHA256SUMS.txt').read_bytes())
pre_review={'artifact':'ROMarrNG PR #70 W605-W624 primary semantic review pre-review manifest','sealedUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W605-W624','head':HEAD,'tree':TREE,'branch':BRANCH,'sourceCount':20,'localeCount':12,'cellCount':240,'sourceWorktree':str(REPO),'sourceWorktreeClean':True,'candidateFreeBundleOriginal':str(CF),'candidateFreeBundleCopy':str(copy),'candidateFreeBundleChecksumVerification':'PASS','candidateFreeVerifier':'PASS','candidateFreeBundleManifestSha256':sha((CF/'bundle-manifest.json').read_bytes()),'candidateFreeInputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),'candidateFreeInputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'candidateFreeBundleChecksumListSha256':candidate_checksum_sha,'copiedCandidateFreeBundleChecksumListSha256':copy_sum_sha,'candidateFreeSealBodySha256':pre_att['bodySha256'],'otherW605ReviewDecisionsAccessed':False,'blindOutputInspected':False,'priorW605PrimaryDecisionsReused':False,'semanticReviewStartedBeforeSeal':False,'reviewType':'fresh primary semantic review','scope':'sealed candidate-free input only; no repo or PR modifications; no tests, builds, scans, or CI'}
dumpj(OUT/'PRIMARY-REVIEW-MANIFEST.json',pre_review)
(OUT/'README.md').write_text(f"""# ROMarrNG PR #70 W605-W624 primary semantic review

This is a fresh primary semantic review of the sealed candidate-free packet for head {HEAD}, tree {TREE}. It contains 240 per-locale dispositions for 20 source strings, with exact source/current-value hashes and caller-context references. The candidate-free packet is copied under candidate-free-bundle and retains its original checksum lists.

Review decisions were created only after the candidate-free seal and verifier passed. No blind-review output was inspected, and no prior W605 primary decisions were reused. This review is AI-generated and has not received native-speaker approval; proposals on callerless strings remain context-limited for later independent review.

Verify with python3 verify_primary.py --repo /path/to/the-exact-8729059-ROMarrNG-worktree from this directory.
""",encoding='utf-8')
cells=jl(INPUT/'current-target-cells.jsonl')
ctx={x['sourceId']:x for x in jl(INPUT/'source-contexts.jsonl')}
review_time=datetime.now(timezone.utc).isoformat(timespec='seconds')
rows=[]
for c in cells:
    key=(c['position'],c['locale']); proposal=PROPOSALS.get(key)
    row={'window':'W605-W624','position':c['position'],'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],'locale':c['locale'],'currentTargetSha256':c['currentTargetSha256'],'callerContextAvailable':not ctx[c['sourceId']]['callerless'],'callerContextSha256':c['callerContextSha256'],'disposition':'KEEP' if proposal is None else 'CHANGE','confidence':'moderate' if proposal is None else proposal[2],'reviewedAtUtc':review_time}
    if proposal is not None:
        row['proposedTarget']=proposal[0]
        row['reason']=proposal[1]
    rows.append(row)
if len(rows)!=240 or len({(x['sourceId'],x['locale']) for x in rows})!=240 or set(PROPOSALS)!={(x['position'],x['locale']) for x in rows if x['disposition']=='CHANGE'}:
    raise SystemExit('FAIL: primary disposition coverage')
out=OUT/'primary-output'; out.mkdir()
dumpl(out/'dispositions.jsonl',rows)
(out/'hash-only-holds.jsonl').write_text('',encoding='utf-8')
counts=collections.Counter(x['disposition'] for x in rows)
by_pos=collections.Counter(str(x['position']) for x in rows if x['disposition']=='CHANGE')
by_loc=collections.Counter(x['locale'] for x in rows if x['disposition']=='CHANGE')
callerless={s for s,c in ctx.items() if c['callerless']}
summary={'artifact':'ROMarrNG PR #70 W605-W624 primary semantic review summary','reviewedAtUtc':review_time,'head':HEAD,'tree':TREE,'sourceCount':20,'localeCount':12,'cellCount':240,'dispositionCounts':dict(counts),'proposedChangeCount':counts['CHANGE'],'proposedChangeCountsByPosition':dict(by_pos),'proposedChangeCountsByLocale':dict(by_loc),'hashOnlyHoldCount':0,'callerCoverage':{'sourcesWithCallers':20-len(callerless),'callerlessSources':len(callerless),'callerlessCells':12*len(callerless),'proposedChangesWithCallerContext':sum(x['disposition']=='CHANGE' and x['callerContextAvailable'] for x in rows),'proposedChangesWithoutCallerContext':sum(x['disposition']=='CHANGE' and not x['callerContextAvailable'] for x in rows)},'hashOnlyHoldFile':'hash-only-holds.jsonl','limitations':['AI semantic review; no native-speaker approval.','Callerless entries were reviewed using source and current-target text without exact runtime caller context.','Blind review was not accessed; independent blind review and cross-adjudication are pending.'],'blindness':{'otherW605ReviewDecisionsAccessed':False,'blindOutputInspected':False,'priorW605PrimaryDecisionsReused':False,'candidateFreeInputManifestSha256':sha((INPUT/'manifest.json').read_bytes())}}
dumpj(out/'summary.json',summary)
# Primary output manifest and checksums; include only primary rows, not future blind material.
pm={'artifact':'W605-W624 primary semantic review output','head':HEAD,'tree':TREE,'window':'W605-W624','sourceCount':20,'localeCount':12,'cellCount':240,'dispositionCounts':dict(counts),'proposedChangeCount':counts['CHANGE'],'hashOnlyHoldCount':0,'files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(out.iterdir()) if p.is_file() and p.name not in ('primary-manifest.json','SHA256SUMS.txt')]}
dumpj(out/'primary-manifest.json',pm)
sums=[]
for p in sorted(out.iterdir()):
    if p.is_file() and p.name!='SHA256SUMS.txt': sums.append(f'{sha(p.read_bytes())}  {p.name}')
(out/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
pr_after=api()
if pr_after!=pr_before:
    raise SystemExit('FAIL: PR/API refs/body changed during primary review')
print(json.dumps({'result':'PRIMARY_REVIEW_BUILT','head':HEAD,'tree':TREE,'window':'W605-W624','cells':len(rows),'dispositions':dict(counts),'changesByPosition':dict(by_pos),'changesByLocale':dict(by_loc),'callerlessSources':len(callerless),'callerlessCells':12*len(callerless),'changesWithoutCallerContext':summary['callerCoverage']['proposedChangesWithoutCallerContext'],'blindOutputInspected':False,'PRApiRefsBodyStable':True},sort_keys=True))
