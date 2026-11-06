#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
BASE=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w725-744-20261105')
C=BASE/'candidate-free'; I=C/'input'; P=BASE/'primary-review'
B=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w725-744-20261105-blind-review-codex')
REPO=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='c3f92c45b4b4f8d79a8caa99417f9970ebc42a26'; TREE='3f835643e4f557999d533c3e832fc92036d4b01a'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def jl(path): return [json.loads(s) for s in path.open(encoding='utf-8') if s.strip()]
def canon_hash(r): return hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def tokens(s): return {'placeholders':re.findall(r'\{[A-Za-z][A-Za-z0-9_]*\}',s or ''),'markup':re.findall(r'</?[A-Za-z][^>]*>',s or ''),'numeric':re.findall(r'\d+(?:[.,]\d+)?',s or '')}
errors=[]; checks={}
def mark(k,ok):
 checks[k]='PASS' if ok else 'FAIL'
 if not ok: errors.append(k)
Crows=jl(I/'candidate-free-cells.jsonl'); Prows=jl(P/'ledger.jsonl'); Props=jl(P/'proposals.jsonl'); Brows=jl(B/'review-cells.jsonl')
Xrows=jl(OUT/'cross-review.jsonl'); Hrows=jl(OUT/'callerless-holds.jsonl'); Rrows=jl(OUT/'root-flags.jsonl')
Cmap={(r['position'],r['locale']):r for r in Crows}; Pmap={(r['position'],r['locale']):r for r in Prows}; Bmap={(r['position'],r['locale']):r for r in Brows}; Xmap={(r['position'],r['locale']):r for r in Xrows}; Prmap={(r['position'],r['locale']):r for r in Props}
expected=[(p,l) for p in range(725,745) for l in LOCALES]
mark('exact-cell-set-and-order',len(Xrows)==240 and [(r['position'],r['locale']) for r in Xrows]==expected and set(Cmap)==set(Pmap)==set(Bmap)==set(Xmap))
head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(); tree=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'],text=True).strip(); status=subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True).strip()
mark('exact-worktree-pin',head==HEAD and tree==TREE and not status)
tokens_ok=True; pins_ok=True; hold_ok=True
for key,c in Cmap.items():
 p=Pmap[key]; b=Bmap[key]; x=Xmap[key]
 if c.get('callerless'):
  if p.get('decision')!='hold-callerless-hash-only' or b.get('decision')!='hold' or x.get('crossDisposition')!='hold-callerless-hash-only': hold_ok=False
  for row in (c,p,b):
   if any(k in row for k in ('source','currentTarget')): hold_ok=False
  if any(k in x for k in ('source','sourceId','currentTarget','primaryRecommendedTarget','blindRecommendedTarget','crossRecommendedTarget','proposedTarget')): hold_ok=False
  if c['catalogZeroBasedIndex']!=732 or c['catalogOneBasedPosition']!=733 or x['catalogZeroBasedIndex']!=732: hold_ok=False
  if canon_hash(c)!=b.get('inputCellRowSha256') or x.get('candidateFreeCellRowSha256')!=canon_hash(c) or x.get('blindInputCellRowSha256')!=b.get('inputCellRowSha256'): hold_ok=False
  if c['sourceSha256']!=p.get('sourceSha256') or c['sourceSha256']!=b.get('sourceSha256') or c['currentTargetSha256']!=p.get('currentTargetSha256') or c['currentTargetSha256']!=b.get('currentTargetSha256'): hold_ok=False
  continue
 prop=Prmap.get(key); pt=prop['proposedTarget'] if prop else c['currentTarget']; bt=b.get('proposedTarget',c['currentTarget'])
 ct=x.get('crossRecommendedTarget')
 if ct!=x.get('currentTarget') and ct!=pt: pins_ok=False
 if x.get('currentTarget')!=c.get('currentTarget') or x.get('primaryRecommendedTarget')!=pt or x.get('blindRecommendedTarget')!=bt: pins_ok=False
 if x.get('sourceSha256')!=c.get('sourceSha256') or x.get('currentTargetSha256')!=c.get('currentTargetSha256') or x.get('callerContextSha256')!=c.get('callerContextSha256'): pins_ok=False
 if p.get('callerContextSha256')!=c.get('callerContextSha256') or b.get('callerContextSha256')!=c.get('callerContextSha256'): pins_ok=False
 if canon_hash(c)!=b.get('inputCellRowSha256') or x.get('candidateFreeCellRowSha256')!=canon_hash(c): pins_ok=False
 expected_tokens={'placeholders':c.get('sourcePlaceholderTokens',[]),'markup':c.get('sourceMarkupTags',[]),'numeric':c.get('sourceNumericTokens',[])}
 for s in (c['currentTarget'],pt,bt,ct):
  actual=tokens(s)
  if actual!=expected_tokens or any(lit not in s for lit in c.get('sourceProtectedLiterals',[])): tokens_ok=False
 if prop and prop.get('proposalTokenCheck')!='PASS': tokens_ok=False
 if b.get('decision')=='proposal' and (not b.get('proposedTokenChecksPass')): tokens_ok=False
mark('current-target-and-review-pins',pins_ok)
mark('all-token-signatures',tokens_ok)
mark('12-hash-only-holds',hold_ok and len(Hrows)==12 and len([r for r in Xrows if r.get('callerless')])==12)
mark('hold-index-summary-discrepancy-flagged',json.loads((OUT/'lineage-flags.json').read_text())['callerlessHoldSummaryDiscrepancy']=={'blindSummaryClaimsCatalogIndex':731,'candidatePrimaryAndBlindRowsCatalogIndex':732,'oneBasedPosition':733,'holdCells':12,'rowBindingsAgree':True})
mark('root-flags-cover-20-positions',len(Rrows)==20 and [r['position'] for r in Rrows]==list(range(725,745)) and Rrows[7].get('sourceKey') is None)
lineage=json.loads((OUT/'lineage-flags.json').read_text()); lm=lineage['inheritedCaveats']
mark('inherited-lineage-caveats',len(lm)==3 and '31' in lm[0]['detail'] and 'stale' in lm[1]['detail'] and '77/77' in lm[2]['detail'])
manifest=json.loads((I/'manifest.json').read_text())
mark('w665-restoration-attestation',manifest.get('priorW665EvidenceRestored') is True and manifest.get('priorW665EvidenceIndexEntries')==77 and manifest.get('priorW665EvidenceIndexMismatches')==0)
# Re-run all authoritative packet verifiers against the exact requested worktree.
commands=[
 ('candidate-free',['python3',str(C/'verify_candidate_free.py'),'--repo',str(REPO)],C),
 ('primary',['python3',str(P/'verify_primary_review.py')],P),
 ('blind',['python3',str(B/'verify_blind_packet.py'),'--repo',str(REPO)],B),
]
for name,cmd,cwd in commands:
 q=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True)
 try: ok=q.returncode==0 and json.loads(q.stdout).get('result')=='PASS'
 except Exception: ok=False
 mark(name+'-verifier',ok)
if (OUT/'SHA256SUMS.txt').exists():
 q=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=OUT,capture_output=True,text=True)
 mark('output-checksums',q.returncode==0)
else: mark('output-checksums',False)
result={'result':'PASS' if not errors and all(v=='PASS' for v in checks.values()) else 'FAIL','head':head,'tree':tree,'cells':len(Xrows),'callerlessHolds':len(Hrows),'rootFlags':len(Rrows),'checks':checks,'errors':errors}
print(json.dumps(result,ensure_ascii=False,indent=2)); sys.exit(0 if result['result']=='PASS' else 1)
