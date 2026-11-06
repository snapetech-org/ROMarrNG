#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess,sys,os
R=Path(__file__).resolve().parent
I=R/'input/candidate-free-input'
HEAD='81a499b7c022bde61a63dbd8c68c0b1ca39adf26'; TREE='1b075e050610771fc5651d1a4ca95d7c7b4b8e46'
D5='d5ba7f1f268501f45227388c46d5f938ed0c9191'; D5TREE='2f8ce1af963b315108f668fc31c94ca90ecd1351'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROTECTED=['ROMarr','GG Requestz','RomM','ROMm','ES-DE','gamelist.xml','1G1R','Battle.net','No-Intro','Redump','RetroArch','Steam','EA','Epic','ROM','Hub','DAT']
NAMED=['ROMarrNG','EmuDeck','Flashpoint','Flood','SeerrNG','ROM','DAT','No-Intro','Redump','ES-DE','RomM','GG Requestz','Battle.net']
TOKEN_RE=re.compile(r'\{[A-Za-z][A-Za-z0-9_]*\}')
NUMBER_RE=re.compile(r'(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])')
def fail(s): raise SystemExit('FAIL: '+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode('utf-8'))
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def token(s): return TOKEN_RE.findall(s)
def nums(s): return NUMBER_RE.findall(TOKEN_RE.sub('',s))
def protected(s):
 return sorted([x for x in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',s)],key=lambda x:s.find(x))
def named(s):
 return sorted([x for x in NAMED if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',s)],key=lambda x:s.find(x))
# Verify outer manifest and complete checksum inventory.
manifest=j(R/'manifest.json'); listed={}
for x in manifest['files']:
 p=R/x['path']
 if x['path'] in listed or not p.is_file() or p.stat().st_size!=x['byteCount'] or sha(p.read_bytes())!=x['sha256']: fail('manifest mismatch '+x['path'])
 listed[x['path']]=x['sha256']
actual={p.relative_to(R).as_posix() for p in R.rglob('*') if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
if set(listed)!=actual: fail('outer manifest inventory')
sums={}
for line in (R/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
 m=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
 if not m or m.group(2) in sums: fail('bad/duplicate checksum line')
 sums[m.group(2)]=m.group(1)
 if not (R/m.group(2)).is_file() or sha((R/m.group(2)).read_bytes())!=m.group(1): fail('checksum mismatch '+m.group(2))
needed={p.relative_to(R).as_posix() for p in R.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
if set(sums)!=needed: fail('checksum inventory')
# Confirm the embedded candidate-free source/cell input remains sealed and has no proposals.
env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'
v=subprocess.run([sys.executable,str(I/'verify_input.py')],cwd=I,capture_output=True,text=True,env=env)
if v.returncode!=0: fail('candidate-free input verifier: '+v.stderr)
if 'proposed targets' not in v.stdout and 'no proposed targets' not in v.stdout: fail('candidate-free boundary result')
# Exact current/d5 to latest-head reattestation.
r=j(R/'latest-head-reattestation.json')
if (r.get('result'),r.get('candidateInputCommit'),r.get('candidateInputTree'),r.get('latestHead'),r.get('latestTree'),r.get('changedPinnedFiles'),r.get('currentTargetChanges'),r.get('callerLineChanges'))!=('PASS',D5,D5TREE,HEAD,TREE,[],0,0): fail('latest-head attestation summary')
pins=j(I/'catalog-file-pins.json')['callerSourceFilePins']
pinrows=jl(R/'latest-head-pinned-file-comparison.jsonl')
if len(pinrows)!=len(pins) or len(pins)!=9: fail('pinned file coverage')
tree=j(R/'latest-head-tree.json')
if tree.get('sha')!=TREE or tree.get('truncated'): fail('latest tree mismatch')
entries={x['path']:x for x in tree['tree']}
for x in pinrows:
 b=(R/'latest-head-files'/x['path']).read_bytes()
 pin=pins[x['path']]
 if not x['matchesD5Pin'] or sha(b)!=x['latestSha256'] or blob(b)!=x['latestGitBlob'] or x['treeBlob']!=blob(b) or entries.get(x['path'],{}).get('sha')!=blob(b): fail('latest file/tree hash mismatch '+x['path'])
 if (pin.get('fileSha256',pin.get('sha256')),pin['gitBlob'])!=(x['d5Sha256'],x['d5GitBlob']): fail('d5 pin lineage mismatch '+x['path'])
labels=j(R/'latest-head-files/romarr/ui-labels.json')
contexts=jl(I/'source-contexts.jsonl'); cctx={x['position']:x for x in contexts}
source_rows=jl(I/'source-inventory-selection.jsonl'); input_cells=jl(I/'current-target-cells.jsonl')
latest_cells=jl(R/'latest-head-cell-preimage-comparison.jsonl')
if len(source_rows)!=20 or len(input_cells)!=240 or len(latest_cells)!=240: fail('input coverage')
if [x['position'] for x in source_rows]!=list(range(445,465)): fail('catalog insertion positions')
latest_map={(x['position'],x['locale']):x for x in latest_cells}
cell_map={(x['position'],x['locale']):x for x in input_cells}
srcmap={x['position']:x for x in source_rows}
ledger=jl(R/'blind-ledger.jsonl')
if len(ledger)!=240 or [(x['position'],x['locale']) for x in ledger]!=[(p,l) for p in range(445,465) for l in LOCALES]: fail('ledger coverage/order')
disps=Counter(); baseline_mismatches=0
for x in ledger:
 k=(x['position'],x['locale']); c=cell_map[k]; s=srcmap[x['position']]; la=latest_map[k]
 entry=labels['messages'].get(x['sourceId'])
 if not entry or entry.get('source')!=s['source'] or entry.get('sourceHash')!=s['sourceSha256']: fail('latest source definition '+str(k))
 cur=entry.get('translations',{}).get(x['locale'])
 if cur!=c['currentTarget'] or x['currentTarget']!=cur or st(cur)!=c['currentTargetSha256'] or not la['currentTargetMatchesD5'] or not la['sourceMatchesD5']: fail('current target preimage '+str(k))
 if x['sourceId']!=s['sourceId'] or x['source']!=s['source'] or x['sourceSha256']!=s['sourceSha256'] or x['catalogOneBasedPosition']!=s['catalogOneBasedPosition']: fail('source identity '+str(k))
 if x['selectedTargetSha256']!=st(x['selectedTarget']): fail('selected target hash '+str(k))
 if x['disposition']=='accept-current' and x['selectedTarget']!=x['currentTarget']: fail('accept invariant '+str(k))
 if x['disposition']=='hold' and x['selectedTarget']!=x['currentTarget']: fail('hold invariant '+str(k))
 if x['disposition'] not in ('accept-current','correction','refinement','hold') or not x['rationale']: fail('missing disposition/rationale '+str(k))
 phsrc=token(x['source']); phcur=token(cur); phsel=token(x['selectedTarget'])
 nsrc=nums(x['source']); nsel=nums(x['selectedTarget'])
 lit=sorted(set(c.get('sourceProtectedLiterals',[]))|set(protected(x['source'])),key=lambda t:x['source'].find(t))
 litpresent=[t for t in lit if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',x['selectedTarget'])]
 nl=named(x['source']); nlpresent=[t for t in nl if t in x['selectedTarget']]
 if x['tokenChecks']!={'sourcePlaceholders':phsrc,'currentPlaceholders':phcur,'selectedPlaceholders':phsel,'placeholderMultisetMatches':Counter(phsrc)==Counter(phsel),'placeholderSequenceMatches':phsrc==phsel,'sourceNumericTokens':nsrc,'selectedNumericTokens':nsel,'numericTokensPreserved':nsrc==nsel,'sourceProtectedLiterals':lit,'selectedProtectedLiteralsPresent':litpresent,'protectedLiteralsPreserved':litpresent==lit,'sourceNamedLiterals':nl,'selectedNamedLiteralsPresent':nlpresent,'namedLiteralsPreserved':nlpresent==nl}: fail('token/literal bundle mismatch '+str(k))
 if not all((x['tokenChecks']['placeholderMultisetMatches'],x['tokenChecks']['numericTokensPreserved'],x['tokenChecks']['protectedLiteralsPreserved'],x['tokenChecks']['namedLiteralsPreserved'])): fail('selected token/literal failure '+str(k))
 if x['callerContext']['callerCount']!=len(cctx[x['position']].get('callerContextRefs',[])): fail('caller count '+str(k))
 if x['callerContext']['callerContextSha256']!=c.get('callerContextSha256'): fail('caller context hash '+str(k))
 expected_refs=[(q['path'],q['lineStart'],q['lineEnd'],q['contextSha256'],q['fileSha256'],q['gitBlob']) for q in cctx[x['position']].get('callerContextRefs',[])]
 got_refs=[(q['path'],q['lineStart'],q['lineEnd'],q['contextSha256'],q['fileSha256'],q['gitBlob']) for q in x['callerContext']['callerContextRefs']]
 if expected_refs!=got_refs: fail('caller context ref mismatch '+str(k))
 if x['callerContext']['callerCount']==0 and not x['callerContext']['callerlessHeldForContext'] and x['disposition']=='hold': fail('callerless hold flag '+str(k))
 if x['baselineDiagnostics']['currentProtectedLiteralMismatch']: baseline_mismatches+=1
 disps[x['disposition']]+=1
if disps!=Counter({'accept-current':200,'correction':3,'refinement':1,'hold':36}): fail('disposition totals '+str(disps))
if sum(x['selectedTarget']!=x['currentTarget'] for x in ledger)!=4: fail('selected change count')
if baseline_mismatches!=1: fail('expected single baseline protected literal mismatch')
# Verify the four exact independent changes.
expected={
 (452,'ar'):('correction','Flashpoint (البث عبر الإنترنت)'),
 (453,'hi'):('correction','Flood में श्रेणियों की जगह टैग होते हैं; यह उनमें से एक है।'),
 (457,'hi'):('correction','फ़ॉलो करें'),
 (461,'pt-BR'):('refinement','Em uma estrutura como a do EmuDeck, defina a raiz da biblioteca ROM como a pasta compartilhada')
}
for k,(d,t) in expected.items():
 x=next(z for z in ledger if (z['position'],z['locale'])==k)
 if (x['disposition'],x['selectedTarget'])!=(d,t): fail('blind adjudication changed '+str(k))
# Callerless positions require independent exact-source/ID search evidence and a written reason.
audit=j(I/'caller-search-audit.json')
qmap={(x['position'],x['queryKind']):x for x in audit['queries']}
for pos in (458,460,462):
 cells_at=[x for x in ledger if x['position']==pos]
 if len(cells_at)!=12 or any(x['disposition']!='hold' or x['callerContext']['callerCount']!=0 for x in cells_at): fail('callerless hold disposition '+str(pos))
 if qmap[(pos,'source-id')]['matchCount']!=0 or qmap[(pos,'source-text')]['matchCount']!=0: fail('callerless evidence contradicts exact search '+str(pos))
# Recompute latest caller lines and verify every sealed context block against latest pinned file bytes.
raw={p:(R/'latest-head-files'/p).read_bytes().decode('utf-8').splitlines() for p in pins}
crows=jl(R/'latest-head-caller-line-comparison.jsonl')
expected_lines=[]
for c in contexts:
 for ref in c.get('callerContextRefs',[]):
  for line in ref.get('contextLines',[]):
   expected_lines.append((c['position'],ref['path'],line['line'],line['text']))
if len(crows)!=319 or sum(not x['match'] for x in crows)!=0 or len({(x['path'],x['line']) for x in crows})!=237: fail('caller line comparison counts')
for pos,path,n,text in expected_lines:
 if not (1<=n<=len(raw[path])) or raw[path][n-1]!=text: fail('latest source context text '+str((pos,path,n)))
 if not any(x['position']==pos and x['path']==path and x['line']==n and x['d5Text']==text and x['latestText']==text and x['match'] for x in crows): fail('caller comparison row missing '+str((pos,path,n)))
# Latest live PR status, refs, and before/after stability.
for fname in ('latest-live-pr-before.json','latest-live-pr-after.json'):
 s=j(R/fname)
 if (s.get('state'),s.get('isDraft'),s.get('head'),s.get('tree'),s.get('parents'),s.get('branchRef'),s.get('pullRef'))!=('OPEN',True,HEAD,TREE,[D5],HEAD,HEAD): fail('latest PR snapshot '+fname)
a=j(R/'latest-live-pr-before.json'); b=j(R/'latest-live-pr-after.json')
if any(a[k]!=b[k] for k in ('state','isDraft','head','tree','parents','branchRef','pullRef','prBodySha256')): fail('latest PR moved during attestation')
summary=j(R/'blind-summary.json')
if summary.get('result')!='PASS' or summary.get('dispositionCounts')!=dict(disps) or summary.get('selectedTargetChanges')!=4 or summary.get('placeholderFailures') or summary.get('numericFailures') or summary.get('protectedLiteralFailures') or summary.get('namedLiteralFailures'): fail('blind summary mismatch')
print(json.dumps({'result':'PASS','outerManifestFiles':len(listed),'checksumEntries':len(sums),'cells':len(ledger),'dispositions':dict(disps),'changedTargets':4,'tokenFailures':0,'protectedLiteralFailures':0,'callerlessHoldCells':36,'latestPinnedFiles':9,'latestCallerLines':319,'uniqueCallerLines':237,'livePRStable':True},ensure_ascii=False,indent=2))
