#!/usr/bin/env python3
"""Portable cross-review packet verifier for ROMarrNG PR #70 W645-W664."""
import argparse, collections, hashlib, json, pathlib, re, subprocess, sys
OUT=pathlib.Path(__file__).resolve().parent; BASE=OUT.parent
CF=BASE/'candidate-free'/'candidate-free'/'input'; PRIMARY=BASE/'primary'/'primary-output'; BLIND=BASE/'blind-review'
HEAD='9f8832f67195323955172dd4c3c40e29cbabb5da'; TREE='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
def sha(b):return hashlib.sha256(b).hexdigest()
def shat(s):return sha(s.encode('utf-8'))
def canon(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def j(p):return json.loads(p.read_text())
def require(ok,msg):
 if not ok:raise SystemExit('FAIL: '+msg)
def sums(directory):
 expected={}
 for line in (directory/'SHA256SUMS.txt').read_text().splitlines():
  h,n=line.split('  ',1); expected[n]=h
 actual={p.relative_to(directory).as_posix():sha(p.read_bytes()) for p in directory.rglob('*') if p.is_file() and p != directory/'SHA256SUMS.txt'}
 require(expected==actual,'checksums '+str(directory))
 return sha((directory/'SHA256SUMS.txt').read_bytes())
def token_ok(source,target,protected):
 return (collections.Counter(re.findall(r'\{[^{}]+\}',source))==collections.Counter(re.findall(r'\{[^{}]+\}',target)) and re.findall(r'<[^>]+>',source)==re.findall(r'<[^>]+>',target) and collections.Counter(re.findall(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])',source))==collections.Counter(re.findall(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])',target)) and all(x in target for x in protected))

def verify(repo=None):
 sums(OUT); sums(CF); sums(BASE/'candidate-free'); sums(BASE/'primary'); sums(PRIMARY); sums(BLIND)
 independent=json.loads(subprocess.check_output([sys.executable,str(OUT/'independent-review'/'verify_independent.py')],text=True))
 require(independent['result']=='PASS','independent ledger')
 att=j(OUT/'attestation'/'final-pr-attestation.json'); api=j(OUT/'attestation'/'final-pr-api.json')
 refs={line.split()[1]:line.split()[0] for line in (OUT/'attestation'/'final-remote-refs.txt').read_text().splitlines()}
 require(att['result']=='PASS' and att['state']=='open' and att['draft'] is True and att['mergedAt'] is None,'PR state')
 require(att['headSha']==HEAD and att['headTree']==TREE and api['head']['sha']==HEAD,'exact PR pin')
 require(refs['refs/heads/task/localization-translation-review-20261030']==refs['refs/pull/70/head']==HEAD,'remote refs')
 require(att['branchRefSha']==att['pullRefSha']==HEAD,'attested refs')
 if repo:
  repo=pathlib.Path(repo)
  require(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==HEAD,'repo head')
  require(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD^{tree}'],text=True).strip()==TREE,'repo tree')
  require(subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1','--untracked-files=all'],text=True).strip()=='','repo clean')
 cfmanifest=j(CF/'manifest.json'); require(cfmanifest['head']==HEAD and cfmanifest['tree']==TREE and cfmanifest['candidateFree'] is True,'candidate-free pins')
 cells=jl(CF/'current-target-cells.jsonl'); contexts={r['sourceId']:r for r in jl(CF/'source-contexts.jsonl')}
 cross=jl(OUT/'cross-review-ledger.jsonl'); recon=jl(OUT/'proposal-reconciliation.jsonl'); summary=j(OUT/'cross-review-summary.json')
 require(len(cells)==len(cross)==240 and len(recon)==18,'output dimensions')
 cmap={(r['sourceId'],r['locale']):r for r in cells}; xmap={(r['sourceId'],r['locale']):r for r in cross}
 require(len(xmap)==240 and set(xmap)==set(cmap),'cross cell identities')
 counts=collections.Counter()
 for key,c in cmap.items():
  x=xmap[key]; ctx=contexts[c['sourceId']]
  require(x['exactHead']==HEAD and x['exactTree']==TREE,'cell exact pin')
  require(x['sourceSha256']==c['sourceSha256'] and x['currentTargetSha256']==c['currentTargetSha256'] and x['callerContextSha256']==c['callerContextSha256']==ctx['contextSha256'],'cell source/target/caller hashes')
  require(x['candidateFreeCellSha256']==sha(canon(c)),'candidate-free row pin')
  if ctx['callerless']:
   require(x['crossDisposition']=='text-free-hold' and x['sourceTextIncluded'] is False and x['currentTargetIncluded'] is False,'hash-only hold')
   require('source' not in x and 'currentTarget' not in x and x['crossRecommendedTarget'] is None,'hold text boundary')
  else:
   require(x['callerful'] is True and x['callerReferenceCount']==ctx['exactMatchCount']>0,'callerful context count')
   require(x['source']==c['source'] and x['currentTarget']==c['currentTarget'],'current text binding')
   if x['crossRecommendedTarget'] is not None:
    target=x['crossRecommendedTarget']; require(x['crossRecommendedTargetSha256']==shat(target),'cross target hash')
    require(token_ok(c['source'],target,c['sourceProtectedLiterals']),'cross target token preservation')
   require(x['crossDisposition'] in ('accept-current','propose-correction','propose-refinement'),'cross disposition')
  counts[x['crossDisposition']]+=1
 require(counts==collections.Counter(summary['crossCounts']),'cross disposition counts')
 # Bind each review’s proposed targets to current sources, targets, and exact caller context.
 primap={(r['sourceId'],r['locale']):r for r in jl(PRIMARY/'dispositions.jsonl')}
 blindrows={(r['sourceId'],r['locale']):r for r in jl(BLIND/'blind-ledger.jsonl')}
 primaprops=[r for r in primap.values() if r['disposition']=='CHANGE']; blindprops=jl(BLIND/'proposals.jsonl')
 require(len(primaprops)==12 and len(blindprops)==6,'proposal counts')
 for row in primaprops:
  key=(row['sourceId'],row['locale']); c=cmap[key]; ctx=contexts[key[0]]; target=row['proposedTarget']
  require(row['sourceSha256']==c['sourceSha256'] and row['currentTargetSha256']==c['currentTargetSha256'] and row['callerContextSha256']==ctx['contextSha256'],'primary proposal cell hashes')
  require(row['proposedTargetSha256']==shat(target) and token_ok(c['source'],target,c['sourceProtectedLiterals']),'primary target hash/tokens')
 for row in blindrows.values():
  key=(row['sourceId'],row['locale']); c=cmap[key]; ctx=contexts[key[0]]
  require(row['position']==c['position'] and row['sourceSha256']==c['sourceSha256'] and row['currentTargetSha256']==c['currentTargetSha256'] and row['callerContextSha256']==ctx['contextSha256'],'blind cell direct binding')
 for row in blindprops:
  key=(row['sourceId'],row['locale']); c=cmap[key]; target=row['selectedTarget']
  require(row['selectedTargetSha256']==shat(target) and token_ok(c['source'],target,c['sourceProtectedLiterals']),'blind target hash/tokens')
 # The blind packet’s own files are sealed, but its summary points to an old input checksum list.
 bsum=j(BLIND/'SUMMARY.json'); actual_cf_sums=sha((CF/'SHA256SUMS.txt').read_bytes()); expected_cf_sums=bsum['candidateFreeChecksumListSha256']
 require(expected_cf_sums!=actual_cf_sums,'expected stale blind checksum pin recorded')
 warning=j(OUT/'cross-review-summary.json')['blindSummaryChecksumPinMismatch']
 require(warning['expected']==expected_cf_sums and warning['actual']==actual_cf_sums and warning['directRowsAndSixProposalTargetsBindToCurrentInput'] is True,'blind checksum warning record')
 require(summary['primaryVerifier']['result']=='PASS' and summary['result']=='PASS_WITH_BLIND_SUMMARY_PIN_WARNING','verification summary')
 return {'result':'PASS_WITH_RECORDED_BLIND_INPUT_PIN_WARNING','head':HEAD,'tree':TREE,'cells':240,'callerfulCells':144,'callerlessHashOnlyHolds':96,'crossCounts':dict(counts),'primaryProposalsBound':12,'blindProposalsBound':6,'proposalRecordsReconciled':18,'blindPacketOwnChecksums':'PASS','blindRowsAndProposalTargetsBindToCurrentInput':'PASS','blindSummaryCandidateFreeChecksumPin':'MISMATCH_RECORDED'}

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--repo'); a=p.parse_args(); print(json.dumps(verify(a.repo),ensure_ascii=False,indent=2))
