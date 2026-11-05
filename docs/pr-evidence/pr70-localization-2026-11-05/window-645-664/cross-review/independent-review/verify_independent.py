#!/usr/bin/env python3
import collections, hashlib, json, pathlib, re
HERE=pathlib.Path(__file__).resolve().parent
CF=HERE.parents[1]/'candidate-free'/'candidate-free'/'input'
HEAD='9f8832f67195323955172dd4c3c40e29cbabb5da'
TREE='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def readjl(path): return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
def require(ok,msg):
 if not ok: raise SystemExit('FAIL: '+msg)
# Check the sealed independent-review files, including the verifier itself.
sums={}
for line in (HERE/'SHA256SUMS.txt').read_text().splitlines():
 h,n=line.split('  ',1); sums[n]=h
actual={p.relative_to(HERE).as_posix():sha(p.read_bytes()) for p in HERE.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
require(sums==actual,'independent-review checksums')
manifest=json.loads((CF/'manifest.json').read_text())
summary=json.loads((HERE/'independent-summary.json').read_text())
rows=readjl(HERE/'independent-cross-ledger.jsonl')
cells=readjl(CF/'current-target-cells.jsonl')
contexts={r['sourceId']:r for r in readjl(CF/'source-contexts.jsonl')}
require(manifest['head']==summary['exactHead']==HEAD and summary['exactTree']==TREE,'head/tree pins')
require(summary['candidateFreeInputSha256']==sha((CF/'SHA256SUMS.txt').read_bytes()),'candidate-free input seal')
require(len(rows)==len(cells)==240,'row dimensions')
require(summary['cells']==240,'summary cell count')
assert_keys={(r['position'],r['sourceId'],r['locale']) for r in cells}
maprows={(r['position'],r['sourceId'],r['locale']):r for r in rows}
require(len(maprows)==240 and set(maprows)==assert_keys,'row identity/order set')
PH=re.compile(r'\{[^{}]+\}'); MARK=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])')
PROT=re.compile(r'\b(?:[A-Z][A-Z0-9]{1,}|[A-Z]+[0-9][A-Z0-9]*)\b')
counts=collections.Counter()
for c in cells:
 r=maprows[(c['position'],c['sourceId'],c['locale'])]; ctx=contexts[c['sourceId']]
 require(r['exactHead']==HEAD and r['exactTree']==TREE,'cell head/tree '+c['sourceId'])
 require(r['sourceSha256']==c['sourceSha256'] and r['currentTargetSha256']==c['currentTargetSha256'],'source/target hash '+c['sourceId']+'/'+c['locale'])
 require(r['callerContextSha256']==c['callerContextSha256']==ctx['contextSha256'],'caller hash '+c['sourceId'])
 require(r['candidateFreeCellSha256']==sha(canon(c)),'candidate-free row hash '+c['sourceId']+'/'+c['locale'])
 if ctx['callerless']:
  require(r['disposition']=='text-free-hold' and r['sourceTextIncluded'] is False and r['currentTargetIncluded'] is False,'callerless hold '+c['sourceId'])
  require('source' not in r and 'currentTarget' not in r and r['recommendedTarget'] is None,'callerless text boundary '+c['sourceId'])
 else:
  require(r['callerfulVerified'] is True and r['callerReferenceCount']==ctx['exactMatchCount']>0,'callerful evidence '+c['sourceId'])
  if r['disposition']=='accept-current':
   require(r['recommendedTarget'] is None and r['integrityChecks']['currentTargetPlaceholderMultisetMatches'] and r['integrityChecks']['currentTargetMarkupMatches'] and r['integrityChecks']['currentTargetNumericTokensPreserved'] and r['integrityChecks']['currentTargetProtectedLiteralsPreserved'],'accept-current checks '+c['sourceId'])
  else:
   target=r['recommendedTarget']; source=c['source']
   require(r['disposition'] in ('propose-correction','propose-refinement') and isinstance(target,str),'proposal shape '+c['sourceId'])
   require(r['recommendedTargetSha256']==sha(target.encode()),'proposal hash '+c['sourceId'])
   require(collections.Counter(PH.findall(source))==collections.Counter(PH.findall(target)),'placeholder parity '+c['sourceId'])
   require(MARK.findall(source)==MARK.findall(target),'markup parity '+c['sourceId'])
   require(collections.Counter(NUM.findall(source))==collections.Counter(NUM.findall(target)),'numeric parity '+c['sourceId'])
   require(all(x in target for x in PROT.findall(source)),'protected literals '+c['sourceId'])
 counts[r['disposition']]+=1
require(dict(counts)==summary['counts'],'summary disposition counts')
require(counts['text-free-hold']==96 and counts['accept-current']+counts['propose-correction']+counts['propose-refinement']==144,'disposition totals')
print(json.dumps({'result':'PASS','cells':240,'callerfulCells':144,'callerlessHashOnlyHolds':96,'counts':dict(counts),'proposalCount':counts['propose-correction']+counts['propose-refinement']},indent=2))
