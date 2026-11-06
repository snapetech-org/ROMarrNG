#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parent
HEAD='8b7589775c526866e474112b4f4168782b02f881'; TREE='fb0ba93172f6832c687e001ce6c0fff08b5a33eb'
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def jb(d): return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def jh(d): return sha(jb(d))
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def raw_index(folder,names):
 out={}
 for name in names:
  for raw in (folder/name).read_bytes().splitlines():
   if raw:
    obj=json.loads(raw); out.setdefault(obj['candidateFreeRowSha256'],[]).append((obj,sha(raw)))
 return out
def sums(folder):
 f=folder/'SHA256SUMS.txt'
 for line in f.read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  expected,rel=line.split(None,1); path=folder/rel.strip().lstrip('*')
  if not path.is_file() or sha(path.read_bytes())!=expected: raise ValueError('checksum mismatch: '+str(path))
 return sha(f.read_bytes())
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo'); ap.add_argument('--input-root',default=str(ROOT)); a=ap.parse_args(); inp=pathlib.Path(a.input_root)
 for line in (HERE/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  expected,rel=line.split(None,1); path=HERE/rel.strip().lstrip('*')
  if not path.is_file() or sha(path.read_bytes())!=expected: raise ValueError('cross checksum mismatch: '+str(path))
 m=read(HERE/'manifest.json'); summary=read(HERE/'summary.json'); before=read(HERE/'exact-head-before.json'); after=read(HERE/'exact-head-after.json')
 if m['exactHead']!=HEAD or m['exactTree']!=TREE: raise ValueError('cross exact pin mismatch')
 for att in (before,after):
  if att['pullRequestApi']['headRefOid']!=HEAD or att['pullRequestApi']['baseRefOid']!=m['pullRequestApiBaseOid'] or att['remoteRefs']['refs/heads/main']!=m['liveMainOid'] or att['remoteRefs']['refs/pull/70/head']!=HEAD or att['remoteRefs']['refs/heads/'+m['branch']]!=HEAD or att['localWorktree']['head']!=HEAD or att['localWorktree']['tree']!=TREE or not att['localWorktree']['clean']:
   raise ValueError('before/after attestation mismatch')
 if before['remoteRefs']!=after['remoteRefs'] or before['pullRequestApi']!=after['pullRequestApi']: raise ValueError('live PR refs changed during review')
 croot=inp/'candidate-free/input'; proot=inp/'primary-review'; broot=inp/'blind-review'
 if sums(croot)!=m['candidateFreeInput']['checksumListSha256'] or sums(proot)!=m['primaryInput']['checksumListSha256'] or sums(broot)!=m['blindInput']['checksumListSha256']: raise ValueError('input checksum-list digest mismatch')
 for folder,manifest_hash,pin_key in ((croot,m['candidateFreeInput']['manifestSha256'],'head'),(proot,m['primaryInput']['manifestSha256'],'exactHead'),(broot,m['blindInput']['manifestSha256'],'exactHead')):
  im=read(folder/'manifest.json')
  if sha((folder/'manifest.json').read_bytes())!=manifest_hash or im[pin_key]!=HEAD: raise ValueError('input manifest pin/digest mismatch')
  if (im.get('tree') if pin_key=='head' else im.get('exactTree'))!=TREE: raise ValueError('input tree pin mismatch')
 cf=rows(croot/'candidate-free-cells.jsonl'); cross=rows(HERE/'cross-ledger.jsonl'); recon=rows(HERE/'input-reconciliation.jsonl')
 if len(cf)!=240 or len(cross)!=240 or len(recon)!=240: raise ValueError('cell coverage count mismatch')
 cm={jh(x):x for x in cf}
 pled=raw_index(proot,['ledger.jsonl']); phold=raw_index(proot,['holds.jsonl'])
 bled=raw_index(broot,['ledger.jsonl']); bhold=raw_index(broot,['holds.jsonl'])
 ppmap=raw_index(proot,['proposals.jsonl']); bpmap=raw_index(broot,['proposals.jsonl'])
 if len(cm)!=240 or len(pled)!=240 or len(bled)!=240 or len(phold)!=72 or len(bhold)!=72: raise ValueError('input review-lane coverage count mismatch')
 if set(pled)!=set(cm) or set(bled)!=set(cm) or set(phold)!={h for h,c in cm.items() if c['callerless']} or set(bhold)!={h for h,c in cm.items() if c['callerless']}: raise ValueError('input review-lane cell binding mismatch')
 pmap={h:(phold[h] if c['callerless'] else pled[h]) for h,c in cm.items()}
 bmap={h:(bhold[h] if c['callerless'] else bled[h]) for h,c in cm.items()}
 cr={x['candidateFreeRowSha256']:x for x in cross}; rr={x['candidateFreeRowSha256']:x for x in recon}
 if len(cr)!=240 or len(rr)!=240 or set(cr)!=set(cm) or set(rr)!=set(cm): raise ValueError('cross output coverage mismatch')
 decisions={}; holds=selected=proposal_rows=0; seen=set()
 for h,c in cm.items():
  r=cr[h]; rec=rr[h]; key=(c['sourceId'],c['locale'])
  if key in seen: raise ValueError('duplicate source/locale')
  seen.add(key)
  if r['sourceId']!=c['sourceId'] or r['locale']!=c['locale'] or r['position']!=c['position'] or r['candidateFreeRowSha256']!=h: raise ValueError('cell identity mismatch')
  if r['sourceSha256']!=c['sourceSha256'] or r['currentTargetSha256']!=c['currentTargetSha256'] or r['callerContextSha256']!=c['callerContextSha256']: raise ValueError('source/current/caller pin mismatch')
  if len(pmap[h])!=1 or len(bmap[h])!=1: raise ValueError('duplicate review evidence row')
  pr,prh=pmap[h][0]; br,brh=bmap[h][0]
  if r['primaryEvidence']['decision']!=pr['decision'] or r['blindEvidence']['decision']!=br['decision'] or r['primaryEvidence']['rowSha256']!=prh or r['blindEvidence']['rowSha256']!=brh: raise ValueError('review evidence row/hash mismatch')
  if rec['sourceSha256']!=c['sourceSha256'] or rec['currentTargetSha256']!=c['currentTargetSha256'] or rec['callerContextSha256']!=c['callerContextSha256'] or rec['primaryRowSha256']!=prh or rec['blindRowSha256']!=brh: raise ValueError('reconciliation pin mismatch')
  if c['callerless']:
   holds+=1
   if r['decision']!='hold-hash-only' or any(k in r for k in ('source','currentTarget','finalTarget','candidateText','sourceText')) or r.get('sourceTextIncluded') is not False or r.get('currentTargetTextIncluded') is not False or r.get('finalTargetTextIncluded') is not False or r.get('candidateTextsIncluded') is not False or r['candidates']:
    raise ValueError('callerless row has text or is not a hash-only hold')
   if pr.get('sourceTextOmitted') is not True or pr.get('currentTargetTextOmitted') is not True: raise ValueError('primary hold not redacted')
   if rec.get('sourceTextIncluded') is not False or rec.get('currentTargetTextIncluded') is not False: raise ValueError('reconciliation contains callerless text')
  else:
   if r.get('source')!=c.get('source') or r.get('currentTarget')!=c.get('currentTarget'): raise ValueError('source/current text differs')
   if tsha(r['source'])!=c['sourceSha256'] or tsha(r['currentTarget'])!=c['currentTargetSha256'] or tsha(r['finalTarget'])!=r['finalTargetSha256']: raise ValueError('source/current/final target hash mismatch')
   if pr.get('sourceTextSha256')!=c['sourceSha256'] or pr.get('currentTargetSha256')!=c['currentTargetSha256'] or br.get('sourceTextSha256')!=c['sourceSha256'] or br.get('currentTargetSha256')!=c['currentTargetSha256'] or pr.get('callerContextSha256')!=c['callerContextSha256'] or br.get('callerContextSha256')!=c['callerContextSha256']: raise ValueError('lane source/current/caller binding mismatch')
   if r['decision']=='accept-current' and r['finalTarget']!=c['currentTarget']: raise ValueError('accept-current target mismatch')
   if r['decision']!='accept-current': selected+=1
   for cand in r['candidates']:
    proposal_rows+=1
    if tsha(cand['candidateText'])!=cand['candidateSha256']: raise ValueError('proposal candidate hash mismatch')
    lane_map=ppmap if cand['lane']=='primary' else bpmap
    found=[(obj,rawh) for obj,rawh in lane_map.get(h,[]) if obj.get('recommendedTarget' if cand['lane']=='primary' else 'proposedTarget')==cand['candidateText']]
    if len(found)!=1 or found[0][1]!=cand['proposalRowSha256']: raise ValueError('proposal row hash/provenance mismatch')
   for lane,map_,keyname in (('primary',ppmap,'primaryProposalRowSha256'),('blind',bpmap,'blindProposalRowSha256')):
    prows=map_.get(h,[])
    expected_hash=prows[0][1] if prows else None
    if rec.get(keyname)!=expected_hash: raise ValueError('reconciliation proposal hash mismatch')
    evkey=lane+'Evidence'; embedded=r[evkey].get('proposalRowSha256')
    if embedded!=expected_hash: raise ValueError('cross proposal evidence hash mismatch')
   if r['position']!=674 and not all(r['finalTargetTokenStatus'].values()): raise ValueError('final target token status failure')
  decisions[r['decision']]=decisions.get(r['decision'],0)+1
 expected={'accept-current':139,'accept-blind':20,'accept-primary':5,'accept-primary-blind':4,'hold-hash-only':72}
 if holds!=72 or selected!=29 or decisions!=expected or summary['dispositionCounts']!=decisions: raise ValueError('decision counts mismatch: '+repr(decisions))
 if a.repo:
  repo=pathlib.Path(a.repo); head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(); tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=repo,text=True).strip(); status=subprocess.check_output(['git','status','--porcelain=v1'],cwd=repo,text=True).strip()
  if head!=HEAD or tree!=TREE or status: raise ValueError('exact repo pin/clean check failed')
 print(json.dumps({'result':'PASS','cells':240,'callerlessHashOnly':holds,'callerBacked':168,'selectedProposalCells':selected,'proposalRowsReconciled':proposal_rows,'decisions':decisions,'exactHead':HEAD,'exactTree':TREE,'checksums':'PASS','inputBindings':'PASS','liveAttestationPins':'PASS','repoPin':'PASS' if a.repo else 'not-requested'},sort_keys=True))
if __name__=='__main__':
 try: main()
 except Exception as e: print('FAIL:',e,file=sys.stderr); sys.exit(1)
