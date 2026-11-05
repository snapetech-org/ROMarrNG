#!/usr/bin/env python3
"""Verify ROMarrNG W745-W764 primary review against candidate-free input."""
import collections,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent; CF=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w745-764-20261105/candidate-free'); REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'; TREE='524db27557a65d64343b15c9983f6ac2f92f90c4'
def fail(x): print('FAIL:',x); sys.exit(1)
def sha(b):
 if isinstance(b,str): b=b.encode('utf-8')
 return hashlib.sha256(b).hexdigest()
def rj(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def sums(root):
 root=pathlib.Path(root); out={}
 for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  h,n=line.split('  ',1); n=n.removeprefix('./'); p=(root/n).resolve()
  if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=h or n in out: fail('checksum '+n)
  out[n]=h
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS.txt'}
 if set(out)!=actual: fail('checksum inventory '+str(root))
 return out
def main():
 sums(ROOT); sums(CF)
 subprocess.run([sys.executable,str(CF/'verify_candidate_free.py'),'--repo',str(REPO)],cwd=CF,check=True,stdout=subprocess.DEVNULL)
 pin=rj(ROOT/'input-reference.json'); manifest=rj(ROOT/'manifest.json'); summary=rj(ROOT/'summary.json')
 if (manifest.get('head'),manifest.get('tree'),manifest.get('window'),manifest.get('cellCount'))!=(HEAD,TREE,'W745-W764',240): fail('manifest pin')
 for k,path in [('candidateFreeManifestSha256',CF/'input/manifest.json'),('candidateFreeChecksumListSha256',CF/'SHA256SUMS.txt'),('candidateFreeCellRowsSha256',CF/'input/candidate-free-cells.jsonl')]:
  if pin.get(k)!=sha(path.read_bytes()): fail('candidate-free input binding '+k)
 if pin.get('head')!=HEAD or pin.get('tree')!=TREE or 'candidate-free' not in pin.get('reviewBasis','').lower(): fail('input reference pin')
 if subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()!=HEAD or subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'],text=True).strip()!=TREE or subprocess.check_output(['git','-C',str(REPO),'status','--porcelain=v1','--untracked-files=all'],text=True).strip(): fail('worktree pin/clean')
 cf=rjl(CF/'input/candidate-free-cells.jsonl'); ledger=rjl(ROOT/'ledger.jsonl'); proposals=rjl(ROOT/'proposals.jsonl'); holds=rjl(ROOT/'holds.jsonl')
 if any(len(x)!=240 for x in [cf,ledger]) or len(proposals)!=5 or len(holds)!=24: fail('coverage')
 key=lambda x:(x['catalogZeroBasedIndex'],x['locale']); cm={key(x):x for x in cf}; lm={key(x):x for x in ledger}
 if len(cm)!=240 or len(lm)!=240: fail('duplicate cell keys')
 expected={(747,'de'):'Keine Treffer.',(747,'hi'):'कोई मेल नहीं मिला।',(747,'ko'):'일치하는 항목이 없습니다.',(747,'pt-BR'):'Nenhum resultado corresponde.',(759,'de'):'Auf Archive.org'}
 got={key(x):x.get('proposedTarget') for x in proposals}
 if got!=expected: fail('proposal targets')
 counts=collections.Counter(x['decision'] for x in ledger)
 if counts!=collections.Counter({'accept-current':211,'correction':4,'refinement':1,'hold-callerless-hash-only':24}): fail('decision counts '+repr(counts))
 if collections.Counter(x['decision'] for x in holds)!={'hold-callerless-hash-only':24}: fail('hold decisions')
 for k,c in cm.items():
  r=lm[k]
  for field in ('sourceId','sourceSha256','locale','callerContextSha256','currentTargetSha256','callerless'):
   if r.get(field)!=c.get(field): fail('row input binding '+str(k)+' '+field)
  if c.get('callerless'):
   if r.get('decision')!='hold-callerless-hash-only' or any(field in r for field in ('source','currentTarget','proposedTarget')) or r.get('sourceTextOmitted') is not True or r.get('currentTargetTextOmitted') is not True: fail('hold text leak '+str(k))
  else:
   if r.get('source')!=c.get('source') or r.get('currentTarget')!=c.get('currentTarget'): fail('caller-backed text binding '+str(k))
   if k in expected:
    t=expected[k]
    if r.get('proposedTarget')!=t or r.get('proposedTargetSha256')!=sha(t) or r.get('decisionOutputSha256') not in (None,sha(t)): fail('proposal hash '+str(k))
    if not all(r.get('proposalTokenEvidence',{}).get(x) is True for x in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')): fail('proposal token checks '+str(k))
   elif r.get('decision')!='accept-current' or r.get('decisionOutputSha256') not in (None,c.get('currentTargetSha256')): fail('retained row '+str(k))
 for h in holds:
  k=key(h); r=lm[k]
  if not r.get('callerless') or any(field in h for field in ('source','currentTarget','proposedTarget')) or h.get('sourceId')!=r.get('sourceId') or h.get('currentTargetSha256')!=r.get('currentTargetSha256'): fail('hold packet binding')
 if (summary.get('priorActiveHoldsReattested'),summary.get('newWindowHashOnlyHolds'),summary.get('resultingActiveHashOnlyHolds'),summary.get('priorAppliedCellsReattested'),summary.get('priorFullReadbackWindowCount'))!=(964,24,988,137,9): fail('hold/application lineage')
 print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':'W745-W764','cells':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'decisionCounts':dict(counts),'priorHolds':964,'resultingActiveHolds':988,'candidateFreeVerifier':'PASS','worktreeClean':True},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
