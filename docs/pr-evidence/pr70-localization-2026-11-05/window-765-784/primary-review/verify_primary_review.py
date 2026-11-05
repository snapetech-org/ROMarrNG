#!/usr/bin/env python3
"""Verify ROMarrNG W765-W784 primary review against sealed candidate-free input."""
import collections,hashlib,json,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
CF=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/candidate-free')
REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='9714d7cf69c687685b4f65cbd9627a56830bab85'; TREE='c8eb66573f10b2390a02df05033f5133425d5e41'
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
EXPECTED={(766,'ar'):'في هذا التثبيت',(766,'fr'):'Dans cette installation',(766,'hi'):'इस इंस्टॉलेशन पर',(766,'ko'):'이 설치에서',(766,'vi'):'Trong bản cài đặt này',(766,'zh-Hans'):'在此安装中',(766,'zh-Hant'):'在此安裝中',(778,'fr'):'Ouvrir la soumission',(780,'zh-Hans'):'OpenXBL API 密钥',(780,'zh-Hant'):'OpenXBL API 金鑰'}
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
 if set(out)!=actual: fail('checksum inventory '+str(root)+' missing='+repr(sorted(set(out)-actual))+' unlisted='+repr(sorted(actual-set(out))))
 return out
def main():
 sums(ROOT); sums(CF)
 subprocess.run([sys.executable,str(CF/'verify_candidate_free.py'),'--repo',str(REPO)],cwd=CF,check=True,stdout=subprocess.DEVNULL)
 pin=rj(ROOT/'input-reference.json'); manifest=rj(ROOT/'manifest.json'); summary=rj(ROOT/'summary.json')
 for k,path in [('candidateFreeManifestSha256',CF/'input/manifest.json'),('candidateFreeChecksumListSha256',CF/'SHA256SUMS.txt'),('candidateFreeCellRowsSha256',CF/'input/candidate-free-cells.jsonl')]:
  if pin.get(k)!=sha(path.read_bytes()): fail('candidate-free binding '+k)
 if (pin.get('head'),pin.get('tree'),pin.get('window'))!=(HEAD,TREE,'W765-W784'): fail('input reference pin')
 if 'W745 primary builder script was consulted after this candidate-free packet sealed' not in pin.get('provenanceNote',''): fail('provenance note')
 if subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()!=HEAD or subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'],text=True).strip()!=TREE or subprocess.check_output(['git','-C',str(REPO),'status','--porcelain=v1','--untracked-files=all'],text=True).strip(): fail('worktree pin/clean')
 att1=rj(CF/'input/PR-attestation-before.json'); att2=rj(CF/'input/PR-attestation-after.json')
 for att in [att1,att2]:
  if (att.get('state'),att.get('draft'),att.get('merged'),att.get('head'),att.get('tree'))!=('OPEN',True,False,HEAD,TREE): fail('PR open/draft/head attestation')
 cf=rjl(CF/'input/candidate-free-cells.jsonl'); ledger=rjl(ROOT/'ledger.jsonl'); proposals=rjl(ROOT/'proposals.jsonl'); holds=rjl(ROOT/'holds.jsonl')
 if any(len(x)!=240 for x in [cf,ledger]) or len(proposals)!=10 or len(holds)!=24: fail('coverage')
 key=lambda x:(x['catalogZeroBasedIndex'],x['locale']); cm={key(x):x for x in cf}; lm={key(x):x for x in ledger}
 if len(cm)!=240 or len(lm)!=240: fail('duplicate cell keys')
 got={key(x):x.get('proposedTarget') for x in proposals}
 if got!=EXPECTED: fail('proposal targets')
 counts=collections.Counter(x['decision'] for x in ledger)
 if counts!=collections.Counter({'accept-current':206,'correction':3,'refinement':7,'hold-callerless-hash-only':24}): fail('decision counts '+repr(counts))
 if collections.Counter(x['decision'] for x in holds)!=collections.Counter({'hold-callerless-hash-only':24}): fail('hold decisions')
 for k,c in cm.items():
  r=lm[k]
  for field in ('sourceId','sourceSha256','locale','callerContextSha256','literalCallerCount','currentTargetSha256','callerless'):
   if r.get(field)!=c.get(field): fail('row input binding '+str(k)+' '+field)
  if c.get('callerless'):
   if r.get('decision')!='hold-callerless-hash-only' or any(f in r for f in ('source','currentTarget','proposedTarget')) or r.get('sourceTextOmitted') is not True or r.get('currentTargetTextOmitted') is not True: fail('hold text leak '+str(k))
  else:
   if r.get('source')!=c.get('source') or r.get('currentTarget')!=c.get('currentTarget'): fail('caller-backed text binding '+str(k))
   if sha(r['source'])!=r['sourceSha256'] or sha(r['currentTarget'])!=r['currentTargetSha256']: fail('source/current hash '+str(k))
   if collections.Counter(PH.findall(r['source']))!=collections.Counter(PH.findall(r['currentTarget'])): fail('current placeholder '+str(k))
   if key(r) in EXPECTED:
    target=EXPECTED[key(r)]
    if (r.get('proposedTarget'),r.get('proposedTargetSha256'),r.get('decisionOutputSha256'))!=(target,sha(target),sha(target)): fail('proposal hash '+str(k))
    if not all(r.get('proposalTokenEvidence',{}).get(x) is True for x in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')): fail('proposal token evidence '+str(k))
    evidence=r['proposalTokenEvidence']; src=evidence['sourceTokens']; tgt=evidence['targetTokens']
    if collections.Counter(PH.findall(r['source']))!=collections.Counter(src['placeholders']) or collections.Counter(PH.findall(target))!=collections.Counter(tgt['placeholders']): fail('proposal placeholders '+str(k))
    if collections.Counter(TAG.findall(r['source']))!=collections.Counter(src['markup']) or collections.Counter(TAG.findall(target))!=collections.Counter(tgt['markup']): fail('proposal markup '+str(k))
    if collections.Counter(NUMBER.findall(r['source']))!=collections.Counter(src['numbers']) or collections.Counter(NUMBER.findall(target))!=collections.Counter(tgt['numbers']): fail('proposal numbers '+str(k))
   elif r.get('decision')!='accept-current' or r.get('decisionOutputSha256')!=c.get('currentTargetSha256'): fail('retained row '+str(k))
 for h in holds:
  k=key(h); r=lm[k]
  if not r.get('callerless') or any(f in h for f in ('source','currentTarget','proposedTarget')) or h.get('sourceId')!=r.get('sourceId') or h.get('currentTargetSha256')!=r.get('currentTargetSha256'): fail('hold packet binding')
 if (summary.get('priorActiveHoldsReattested'),summary.get('newWindowHashOnlyHolds'),summary.get('resultingActiveHashOnlyHolds'),summary.get('priorAppliedCellsReattested'),summary.get('priorFullReadbackWindowCount'))!=(988,24,1012,144,10): fail('hold/application lineage')
 if summary.get('nextBoundary')!=rj(CF/'input/manifest.json').get('nextBoundary'): fail('next boundary')
 result={'result':'PASS','head':HEAD,'tree':TREE,'window':'W765-W784','cells':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'decisionCounts':dict(counts),'proposalCount':10,'priorActiveHolds':988,'resultingActiveHolds':1012,'priorAppliedCells':144,'readbackWindows':10,'candidateFreeVerifier':'PASS','proposalTokenChecks':'PASS','PRState':'OPEN_DRAFT','worktreeClean':True,'provenanceNoteIncluded':True}
 (ROOT/'verification-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
