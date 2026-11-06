#!/usr/bin/env python3
"""Portable exact-head verifier for ROMarrNG PR #70 W465-W484 application evidence."""
import argparse, collections, copy, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WINDOW=ROOT.parent
CROSS=WINDOW/'cross-audit'
E=ROOT/'evidence'
PARENT='7640720c5e3b1813725cca8d7aa46b5d968bff43'
PARENT_TREE='bdee162cc11115256df8756f192b19d4337ed1dc'
CATALOG_COMMIT='53361f6c2ca8ad7d35cf844ab7901b91a2ecb06d'
CATALOG_TREE='36d371b05d28fa75abd89ef34a6af447f501def5'
CATALOG_PATH='romarr/ui-labels.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def ht(s): return sha(s.encode('utf-8'))
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def need(ok,msg):
 if not ok: raise SystemExit('FAIL: '+msg)
def git(repo,*args):
 return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def gitb(repo,*args):
 return subprocess.check_output(['git','-C',str(repo),*args])
def sums(d):
 sf=d/'SHA256SUMS.txt'
 expected={}
 for line in sf.read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  m=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
  need(bool(m),'malformed checksum line '+str(sf))
  h,name=m.groups(); p=Path(name)
  need(name not in expected and not p.is_absolute() and '..' not in p.parts,'unsafe or duplicate checksum path')
  expected[name]=h
 actual={p.relative_to(d).as_posix() for p in d.rglob('*') if p.is_file() and p!=sf}
 need(actual==set(expected),'checksum inventory mismatch '+str(d))
 for name,h in expected.items(): need(sha((d/name).read_bytes())==h,'checksum mismatch '+name)
 return len(expected)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--repo',type=Path,default=ROOT.parents[4])
 repo=ap.parse_args().repo.resolve()
 m=j(ROOT/'manifest.json')
 need((m['window'],m['parent'],m['parentTree'],m['catalogCommit'],m['catalogTree'])==('W465-W484',PARENT,PARENT_TREE,CATALOG_COMMIT,CATALOG_TREE),'application manifest pin')
 listed={x['path']:x for x in m['files']}
 actual={p.relative_to(ROOT).as_posix():p for p in ROOT.rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in {'manifest.json','SHA256SUMS.txt'}}
 need(set(listed)==set(actual),'application manifest file inventory')
 for name,rec in listed.items():
  p=actual[name]; need(sha(p.read_bytes())==rec['sha256'] and p.stat().st_size==rec['bytes'],'application manifest file '+name)
 app_sum_count=sums(ROOT)
 cross_sum_count=sum(1 for line in (CROSS/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines() if line.strip())
 cross_result=json.loads(subprocess.check_output(['python3',str(CROSS/'verify_cross_audit.py')],text=True))
 need(cross_result['result']=='PASS' and cross_result['exactHead']==PARENT and cross_result['selectedChanges']==12,'cross-audit verifier')
 need(git(repo,'rev-parse',PARENT+'^{tree}')==PARENT_TREE,'parent tree')
 need(git(repo,'rev-parse',CATALOG_COMMIT+'^{tree}')==CATALOG_TREE,'catalog commit tree')
 need(git(repo,'rev-parse',CATALOG_COMMIT+'^')==PARENT,'catalog commit parent')
 changed=git(repo,'diff-tree','--no-commit-id','--name-only','-r',CATALOG_COMMIT).splitlines()
 need(changed==[CATALOG_PATH],'catalog commit path scope')
 before_raw=(E/'pre-apply-ui-labels.json').read_bytes()
 after_raw=(E/'post-apply-ui-labels.json').read_bytes()
 need(before_raw==gitb(repo,'show',PARENT+':'+CATALOG_PATH),'parent catalog bytes')
 need(after_raw==gitb(repo,'show',CATALOG_COMMIT+':'+CATALOG_PATH),'catalog commit bytes')
 before=json.loads(before_raw); after=json.loads(after_raw)
 cross_ledger=jl(CROSS/'cross-audit-ledger.jsonl')
 candidate=CROSS/'candidate-free-input'
 cells=jl(candidate/'current-target-cells.jsonl')
 need(len(cross_ledger)==len(cells)==240,'240 cell coverage')
 cellmap={(x['sourceId'],x['locale']):x for x in cells}
 crossmap={(x['sourceId'],x['locale']):x for x in cross_ledger}
 need(set(cellmap)==set(crossmap),'cross/input cell set')
 pin=j(CROSS/'candidate-free-input/catalog-file-pins.json')
 for path,rec in pin['callerSourceFilePins'].items():
  raw=gitb(repo,'show',PARENT+':'+path)
  need(sha(raw)==rec['fileSha256'] and git(repo,'rev-parse',PARENT+':'+path)==rec['gitBlob'],'pinned source/caller file '+path)
 need(sha(before_raw)==pin['catalogSha256'] and len(before['messages'])==pin['catalogMessageCount']==1836,'preimage catalog pin/count')
 selection=j(candidate/'selection.json')
 order=list(before['messages'])
 order_hash=sha(('\n'.join(order)+'\n').encode('utf-8'))
 need(order_hash==selection['catalogKeyOrderSha256']==pin['catalogKeyOrderSha256'],'catalog insertion order')
 locale_order=selection['localeOrder']
 expected=copy.deepcopy(before)
 selected=[]; holds=[]; changes=set()
 for r in cross_ledger:
  key=(r['sourceId'],r['locale']); c=cellmap[key]
  need((r['latestAttestedHead'],r['latestAttestedTree'])==(PARENT,PARENT_TREE),'cross row pin '+str(key))
  need((r['source'],r['sourceSha256'])==(c['source'],c['sourceSha256']),'source preimage '+str(key))
  need((r['currentTarget'],r['currentTargetSha256'])==(c['currentTarget'],c['currentTargetSha256']),'target preimage packet '+str(key))
  msg=before['messages'].get(r['sourceId'])
  need(msg is not None and msg['source']==r['source'] and ht(msg['source'])==r['sourceSha256'],'catalog source '+str(key))
  current=msg['translations'].get(r['locale'])
  need(current==r['currentTarget'] and ht(current)==r['currentTargetSha256'],'catalog target preimage '+str(key))
  need(ht(r['selectedTarget'])==r['selectedTargetSha256'],'selected target hash '+str(key))
  if r['disposition'] in ('correction','refinement'):
   q=r['tokenAndLiteralChecks']
   need(q['selectedPlaceholderMultisetMatches'] and q['selectedNumericTokensExactMatch'] and q['selectedProtectedLiteralsPreserved'] and q['selectedAdditionalNamedTermsPreserved'],'selected token/literal checks '+str(key))
   need(r['selectedTarget']!=current,'selected value is no-op '+str(key))
   expected['messages'][r['sourceId']]['translations'][r['locale']]=r['selectedTarget']
   selected.append(r); changes.add(key)
  elif r['disposition']=='hold':
   holds.append(r); need(r['selectedTarget']==current,'held value changed in selection '+str(key))
  else:
   need(r['disposition']=='accept-current' and r['selectedTarget']==current,'current disposition mismatch '+str(key))
 need(len(selected)==12 and collections.Counter(r['disposition'] for r in selected)=={'correction':8,'refinement':4},'selected change counts')
 need(len(holds)==60,'current hold count')
 rb=jl(E/'apply-readback.jsonl')
 need(len(rb)==240,'readback rows')
 rbmap={(r['sourceId'],r['locale']):r for r in rb}
 need(set(rbmap)==set(crossmap),'readback cell set')
 for r in cross_ledger:
  key=(r['sourceId'],r['locale']); actual=after['messages'][r['sourceId']]['translations'][r['locale']]
  expected_value=r['selectedTarget']
  q=rbmap[key]
  need(actual==expected_value and ht(actual)==r['selectedTargetSha256'],'240-cell readback '+str(key))
  need(q['readbackMatchesSelection'] is True and q['readbackTarget']==actual and q['expectedReadbackSha256']==ht(actual),'readback evidence '+str(key))
  need(q['preApplyTargetSha256']==r['currentTargetSha256'] and q['selectedTargetSha256']==r['selectedTargetSha256'],'readback preimage/selection pins '+str(key))
 need(after==expected,'catalog contains unselected changes')
 need(list(before)==list(after) and list(before['messages'])==list(after['messages']),'catalog key order')
 need(all(list(before['messages'][s]['translations'])==list(after['messages'][s]['translations']) for s in before['messages']),'locale key order')
 diff={(s,l) for s,msg in before['messages'].items() for l,v in msg['translations'].items() if after['messages'][s]['translations'][l]!=v}
 need(diff==changes and len(diff)==12,'changed translation set')
 need(all(before['messages'][s].get('translationHashes',{})==after['messages'][s].get('translationHashes',{}) for s in before['messages']),'translation hash metadata changed')
 for r in holds:
  sid,loc=r['sourceId'],r['locale']
  need(before['messages'][sid]['translations'][loc]==after['messages'][sid]['translations'][loc] and ht(after['messages'][sid]['translations'][loc])==r['currentTargetSha256'],'current hold changed')
 prior_holds=jl(CROSS/'candidate-free-input/prior-hold-reattestation.jsonl')
 prior_selections=jl(CROSS/'candidate-free-input/prior-selection-reattestation.jsonl')
 ph=jl(E/'prior-hold-reattestation.jsonl'); ps=jl(E/'prior-selection-reattestation.jsonl')
 need(len(prior_holds)==len(ph)==384 and len(prior_selections)==len(ps)==80,'carried lineage counts')
 need(prior_holds==ph and prior_selections==ps,'carried lineage differs from sealed candidate-free packet')
 for r in ph:
  sid,loc=r['sourceId'],r['locale']
  need(r['targetUnchanged'] is True and r['priorTargetSha256']==r['currentTargetSha256'],'prior hold record')
  for cat in (before,after):
   need(ht(cat['messages'][sid]['translations'][loc])==r['currentTargetSha256'],'carried hold hash changed')
 for r in ps:
  sid=r['sourceId']
  need(r['sourceHashMatches'] and r['selectionUnchanged'] and r['registryMembershipAndHashMatch'],'prior selection pin')
  need(before['messages'][sid]['source']==after['messages'][sid]['source'] and before['messages'][sid]['translations']==after['messages'][sid]['translations'],'prior selected source changed')
 checks=j(E/'pre-apply-checks.json')
 need(checks['observedImmediatelyBeforeEdit'] is True and checks['head']==PARENT and checks['tree']==PARENT_TREE and checks['preimageCellsChecked']==240,'pre-apply evidence')
 summary=j(E/'apply-summary.json')
 need(summary['result']=='PASS' and summary['cellsReadBack']==240 and summary['selectedChanges']==12 and summary['holds']==60 and summary['carriedHoldsPreserved']==384 and summary['priorSelectionsPreserved']==80,'application summary')
 commit=j(E/'catalog-commit.json')
 need(commit['parent']==PARENT and commit['commit']==CATALOG_COMMIT and commit['tree']==CATALOG_TREE and commit['changedPaths']==[CATALOG_PATH] and commit['catalogFileSha256']==sha(after_raw),'catalog commit evidence')
 print(json.dumps({'result':'PASS','window':'W465-W484','cellsReadBack':240,'selectedChanges':12,'corrections':8,'refinements':4,'acceptCurrent':168,'currentHoldsPreserved':60,'carriedHoldsPreserved':384,'priorSelectionsPreserved':80,'catalogMessageCount':1836,'nonTargetValuesPreserved':True,'catalogPath':CATALOG_PATH,'catalogCommit':CATALOG_COMMIT,'catalogTree':CATALOG_TREE,'crossPacketFilesChecked':cross_sum_count,'applicationFilesChecked':app_sum_count},indent=2))
if __name__=='__main__': main()
