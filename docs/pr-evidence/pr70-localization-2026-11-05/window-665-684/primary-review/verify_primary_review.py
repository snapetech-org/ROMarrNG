#!/usr/bin/env python3
"""Portable integrity, hold-redaction, source-binding, and token verifier."""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
PACKET=ROOT.parent/'candidate-free'/'input'
HEAD='8b7589775c526866e474112b4f4168782b02f881'
TREE='fb0ba93172f6832c687e001ce6c0fff08b5a33eb'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
POSITIONS=list(range(665,685))
def sha(b): return hashlib.sha256(b).hexdigest()
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def jsonl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_sums(directory,index):
 entries={}
 for line in index.read_text(encoding='utf-8').splitlines():
  if line.strip():
   h,name=line.split(None,1); entries[name.lstrip(' *')]=h
 if not entries: raise ValueError(f'empty checksum file: {index}')
 for name,h in entries.items():
  p=directory/name
  if not p.is_file() or sha(p.read_bytes())!=h: raise ValueError(f'checksum failed: {p}')
 return len(entries)
def token_signature(s):
 placeholders=re.findall(r'\{[A-Za-z][A-Za-z0-9_]*\}',s)
 markup=re.findall(r'</?[A-Za-z][^>]*>',s)
 numbers=re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])',s)
 protected=[]
 for x in re.findall(r'(?<![A-Za-z0-9])(?:[A-Z]{2,}[A-Z0-9]*|ffmpeg|Chromaprint|Soulseek|Spotify|YouTube|Pushbullet|Matrix|WebSocket|OpenAI)(?![A-Za-z0-9])',s):
  if x not in protected: protected.append(x)
 return placeholders,markup,numbers,protected
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',help='optional exact detached worktree')
 args=ap.parse_args()
 input_file_count=verify_sums(PACKET,PACKET/'SHA256SUMS.txt')
 output_file_count=verify_sums(ROOT,ROOT/'SHA256SUMS.txt')
 input_manifest=readj(PACKET/'manifest.json'); manifest=readj(ROOT/'manifest.json'); summary=readj(ROOT/'summary.json')
 if (input_manifest.get('head'),input_manifest.get('tree'))!=(HEAD,TREE): raise ValueError('candidate-free input pin mismatch')
 if (manifest.get('exactHead'),manifest.get('exactTree'))!=(HEAD,TREE): raise ValueError('review manifest pin mismatch')
 if manifest.get('candidateFreeManifestSha256')!=sha((PACKET/'manifest.json').read_bytes()): raise ValueError('candidate-free manifest hash mismatch')
 if manifest.get('candidateFreeChecksumIndexSha256')!=sha((PACKET/'SHA256SUMS.txt').read_bytes()): raise ValueError('candidate-free input checksum index hash mismatch')
 raw={}
 for line in (PACKET/'candidate-free-cells.jsonl').read_bytes().splitlines():
  if line.strip():
   r=json.loads(line); raw[(r['position'],r['locale'])]=(r,sha(line))
 contexts={c['sourceId']:c for c in jsonl(PACKET/'source-contexts.jsonl')}
 ledger=jsonl(ROOT/'ledger.jsonl'); proposals=jsonl(ROOT/'proposals.jsonl'); holds=jsonl(ROOT/'holds.jsonl')
 if len(raw)!=240 or len(ledger)!=240: raise ValueError('expected 240 input and ledger cells')
 if len(contexts)!=20: raise ValueError('expected 20 caller-context rows')
 if len({x['cellId'] for x in ledger})!=240: raise ValueError('duplicate ledger cell IDs')
 if len({x['cellId'] for x in proposals})!=len(proposals): raise ValueError('duplicate proposal IDs')
 if len({x['cellId'] for x in holds})!=len(holds): raise ValueError('duplicate hold IDs')
 seen=set(); changed=[]; hold_rows=[]; decisions=collections.Counter()
 for item in ledger:
  key=(item['sourcePosition'],item['locale'])
  if key not in raw or key in seen: raise ValueError(f'bad or duplicate position/locale {key}')
  seen.add(key); source,rowhash=raw[key]
  if item['exactHead']!=HEAD or item['exactTree']!=TREE: raise ValueError('ledger row pin mismatch')
  if item['candidateFreeRowSha256']!=rowhash: raise ValueError('candidate-free row hash mismatch')
  if item['sourceTextSha256']!=source['sourceSha256'] or item['currentTargetSha256']!=source['currentTargetSha256']:
   raise ValueError('candidate-free source/current hash mismatch')
  if item['callerContextSha256']!=source['callerContextSha256']: raise ValueError('caller-context binding mismatch')
  is_hold=bool(source.get('callerless'))
  if is_hold:
   if item['decision']!='hold-hash-only': raise ValueError('callerless cell not held')
   if any(k in item for k in ('source','sourceText','currentTarget','recommendedTarget','sourceId')):
    raise ValueError('callerless source/current text or slug leaked into ledger')
   if item.get('cellId')!=f"sha256:{source['sourceSha256']}::{source['locale']}": raise ValueError('hash-only cell ID mismatch')
   if item.get('sourceTextOmitted') is not True or item.get('currentTargetTextOmitted') is not True: raise ValueError('hash-only omission flags missing')
   hold_rows.append(item)
  else:
   c=contexts.get(source['sourceId'])
   if not c or c.get('callerless') or c.get('contextSha256')!=source['callerContextSha256']:
    raise ValueError('caller-backed context mismatch')
   if item.get('cellId')!=f"{source['sourceId']}::{source['locale']}": raise ValueError('caller-backed cell ID mismatch')
   if item.get('sourceId')!=source['sourceId'] or item.get('source')!=source['source'] or item.get('currentTarget')!=source['currentTarget']:
    raise ValueError('caller-backed source/current text mismatch')
   if sha(item['source'].encode())!=source['sourceSha256'] or sha(item['currentTarget'].encode())!=source['currentTargetSha256']:
    raise ValueError('caller-backed text hash mismatch')
   if item.get('callerMatchCount')!=c['exactMatchCount'] or item.get('callerPaths')!=sorted({x['path'] for x in c['callers']}):
    raise ValueError('caller identity mismatch')
   if item.get('decision') not in ('accept-current','correction','refinement'): raise ValueError('bad caller-backed decision')
   if item['decision']=='accept-current' and 'recommendedTarget' in item: raise ValueError('accept-current row contains target proposal')
   if item['decision'] in ('correction','refinement'):
    if 'recommendedTarget' not in item: raise ValueError('changed row lacks recommended target')
    if item.get('recommendedTargetSha256')!=sha(item['recommendedTarget'].encode()): raise ValueError('recommendation hash mismatch')
    if token_signature(item['source'])[:3]!=token_signature(item['recommendedTarget'])[:3]: raise ValueError('proposal changes placeholder/markup/numeric tokens')
    required=source.get('sourceProtectedLiterals') or []
    if any(t not in item['recommendedTarget'] for t in required): raise ValueError('proposal drops protected literal')
    changed.append(item)
  decisions[item['decision']]+=1
 if len(seen)!=240 or len(hold_rows)!=72 or len(changed)!=len(proposals) or len(holds)!=72:
  raise ValueError(f'coverage mismatch: rows={len(seen)} holds={len(hold_rows)}/{len(holds)} changed={len(changed)}/{len(proposals)}')
 if set((p,l) for p,l in seen)!={(p,l) for p in POSITIONS for l in LOCALES}: raise ValueError('locale/source coverage mismatch')
 if {x['cellId'] for x in proposals}!={x['cellId'] for x in changed}: raise ValueError('proposal set mismatch')
 hold_by_id={x['cellId']:x for x in holds}
 if set(hold_by_id)!={x['cellId'] for x in hold_rows}: raise ValueError('hold set mismatch')
 for item in hold_rows:
  h=hold_by_id[item['cellId']]
  for k in ('sourcePosition','locale','sourceTextSha256','currentTargetSha256','callerContextSha256','candidateFreeRowSha256','exactHead','exactTree'):
   if h.get(k)!=item.get(k): raise ValueError(f'hold copy mismatch: {k}')
 for item in changed:
  p=next(x for x in proposals if x['cellId']==item['cellId'])
  for k in ('decision','recommendedTarget','recommendedTargetSha256','candidateFreeRowSha256','sourceTextSha256','currentTargetSha256','callerContextSha256','exactHead','exactTree'):
   if p.get(k)!=item.get(k): raise ValueError(f'proposal/ledger mismatch: {k}')
 if summary.get('cellCount')!=240 or summary.get('proposalCount')!=len(proposals) or summary.get('decisionCounts')!=dict(sorted(decisions.items())):
  raise ValueError('summary counts mismatch')
 for name in ('ledger.jsonl','proposals.jsonl','holds.jsonl','summary.json'):
  if manifest.get('fileHashes',{}).get(name)!=sha((ROOT/name).read_bytes()): raise ValueError(f'manifest hash mismatch for {name}')
 for name in ('head-attestation-before.json','head-attestation-after.json'):
  a=readj(ROOT/name)
  if (a.get('head'),a.get('tree'),a.get('branchRefSha'),a.get('pullRefSha'),a.get('state'),a.get('isDraft'))!=(HEAD,TREE,HEAD,HEAD,'OPEN',True):
   raise ValueError(f'live head attestation mismatch: {name}')
  if a.get('localHead')!=HEAD or a.get('localTree')!=TREE or a.get('localStatusClean') is not True:
   raise ValueError(f'local worktree attestation mismatch: {name}')
 repo_pin='NOT_CHECKED'
 if args.repo:
  r=pathlib.Path(args.repo)
  def git(*x): return subprocess.check_output(['git','-C',str(r),*x],text=True).strip()
  if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain'):
   raise ValueError('provided repository pin/cleanliness mismatch')
  repo_pin='PASS'
 print(json.dumps({'result':'PASS','cells':len(ledger),'callerBacked':len(ledger)-len(hold_rows),'hashOnlyHolds':len(hold_rows),'proposals':len(proposals),'decisions':dict(sorted(decisions.items())),'inputFilesVerified':input_file_count,'outputFilesVerified':output_file_count,'holdTextRedaction':'PASS','callerBindings':'PASS','repoPin':repo_pin},sort_keys=True))
if __name__=='__main__':
 try: main()
 except Exception as e:
  print(json.dumps({'result':'FAIL','error':str(e)}),file=sys.stderr); raise
