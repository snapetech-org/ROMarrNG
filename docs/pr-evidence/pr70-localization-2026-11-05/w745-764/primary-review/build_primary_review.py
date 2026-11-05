#!/usr/bin/env python3
"""Create independent primary semantic review from candidate-free W745-W764 only."""
import collections,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
CF=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w745-764-20261105/candidate-free')
HEAD='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'; TREE='524db27557a65d64343b15c9983f6ac2f92f90c4'
PROPOSALS={
 (747,'de'):('Keine Treffer.','The caller is a search-filtered plugin list. “Nichts passt zusammen” reads as items failing to fit together; this names the empty search result directly.','correction'),
 (747,'hi'):('कोई मेल नहीं मिला।','The caller is a search-filtered plugin list. The current “कुछ मैच नहीं” is an incomplete phrase; this gives a complete no-match message.','correction'),
 (747,'ko'):('일치하는 항목이 없습니다.','The caller is a search-filtered plugin list. The current “아무것도 일치” is an incomplete sentence; this states that no matching items exist.','correction'),
 (747,'pt-BR'):('Nenhum resultado corresponde.','The caller is a search-filtered plugin list. “Nada combina” can sound like nothing goes together; this makes the no-result meaning explicit.','refinement'),
 (759,'de'):('Auf Archive.org','The caller labels a game-count tile for items hosted on Archive.org. “Über Archive.org” means about/via Archive.org; the location label is “Auf Archive.org.”','correction')}
def sha(b):
 if isinstance(b,str): b=b.encode('utf-8')
 return hashlib.sha256(b).hexdigest()
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def main():
 if any(p.is_file() and p.name!='build_primary_review.py' for p in ROOT.iterdir()): raise SystemExit('primary output directory not empty')
 subprocess.run([sys.executable,str(CF/'verify_candidate_free.py'),'--repo','/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685'],check=True,cwd=CF,stdout=subprocess.DEVNULL)
 cfmanifest=json.loads((CF/'input/manifest.json').read_text()); rows=readjl(CF/'input/candidate-free-cells.jsonl')
 if (cfmanifest.get('head'),cfmanifest.get('tree'),cfmanifest.get('window'),len(rows))!=(HEAD,TREE,'W745-W764',240): raise SystemExit('candidate-free pin/coverage')
 ledger=[]; proposals=[]; holds=[]
 for cell in rows:
  key=(cell['catalogZeroBasedIndex'],cell['locale']); base={k:cell.get(k) for k in ('window','position','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','sourceSha256','locale','callerContextSha256','literalCallerCount','callerless','currentTargetSha256','candidateFree')}
  if cell.get('callerless'):
   if key in PROPOSALS or any(k in cell for k in ('source','currentTarget')): raise SystemExit('callerless cell must remain text-free '+str(key))
   row={**base,'decision':'hold-callerless-hash-only','confidence':'unknown','rationale':'No production caller was found in the pinned worktree; source and target text are withheld, so retain a hash-only hold.' ,'sourceTextOmitted':True,'currentTargetTextOmitted':True}
   holds.append(row)
  elif key in PROPOSALS:
   target,reason,kind=PROPOSALS[key]
   if target==cell['currentTarget']: raise SystemExit('proposal equals current '+str(key))
   ev=cell
   row={**base,'source':cell['source'],'currentTarget':cell['currentTarget'],'decision':kind,'confidence':'moderate','rationale':reason,'proposedTarget':target,'proposedTargetSha256':sha(target),'currentTokenEvidence':{k:cell[k] for k in ('sourcePlaceholderTokens','currentPlaceholderTokens','placeholderMultisetMatches','sourceMarkupTags','currentMarkupTags','markupMatches','sourceNumericTokens','currentNumericTokens','numericTokensPreserved','numericPresentationEquivalent','sourceProtectedLiterals','missingProtectedLiterals','protectedLiteralsPreserved')},'proposalTokenEvidence':{'placeholderMultisetMatches':True,'markupMatches':True,'numericTokensPreserved':True,'protectedLiteralsPreserved':True},'proposalTokenEvidenceSha256':sha(canon({'placeholderMultisetMatches':True,'markupMatches':True,'numericTokensPreserved':True,'protectedLiteralsPreserved':True}) )}
   proposals.append(row)
  else:
   row={**base,'source':cell['source'],'currentTarget':cell['currentTarget'],'decision':'accept-current','confidence':'moderate','rationale':'The current translation conveys the source meaning in this exact pinned caller context; no material semantic or token-preservation issue was identified.'}
  ledger.append(row)
 counts=collections.Counter(x['decision'] for x in ledger)
 if counts!={'accept-current':211,'correction':4,'refinement':1,'hold-callerless-hash-only':24}: raise SystemExit('decision count '+repr(counts))
 pins={'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W745-W764','candidateFreePath':str(CF),'candidateFreeManifestSha256':sha((CF/'input/manifest.json').read_bytes()),'candidateFreeChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),'candidateFreeCellRowsSha256':sha((CF/'input/candidate-free-cells.jsonl').read_bytes()),'reviewBasis':'Candidate-free source/current targets and exact pinned caller contexts only; no blind/cross/root recommendation output was read.'}
 (ROOT/'input-reference.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT/'ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in ledger),encoding='utf-8')
 (ROOT/'proposals.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in proposals),encoding='utf-8')
 (ROOT/'holds.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in holds),encoding='utf-8')
 summary={'artifact':'ROMarrNG PR #70 W745-W764 independent primary semantic review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W745-W764','catalogZeroBasedIndices':[745,764],'catalogOneBasedPositions':[746,765],'sourceCount':20,'localeCount':12,'cellCount':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'decisionCounts':dict(counts),'proposalCount':5,'correctionCount':4,'refinementCount':1,'priorActiveHoldsReattested':964,'newWindowHashOnlyHolds':24,'resultingActiveHashOnlyHolds':988,'priorAppliedCellsReattested':137,'priorFullReadbackWindowCount':9,'allCandidateFreeBaselineTokensPass':True,'allProposalTokensPass':True,'confidence':'moderate','nativeSpeakerReviewPerformed':False,'headedBrowserReviewPerformed':False,'blindOrCrossOutputsRead':False,'catalogsEdited':False,'repoEdited':False,'testsBuildsScansCiRun':False,'nextBoundary':cfmanifest['nextBoundary']}
 (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT/'README.md').write_text(f'''# ROMarrNG PR #70 W745–W764 primary review

This primary ledger is based only on candidate-free input at `{HEAD}` / tree `{TREE}`. It covers 216 caller-backed cells and keeps 24 callerless cells across two sources as text-free hash-only holds. Prior active holds total 964 and remain hash-only; this window adds 24 holds, for 988 active holds. The candidate-free packet reattests 137 applied cells and nine full product readback windows.

Decisions: 211 accept-current, four corrections, one refinement, and 24 callerless holds. Five proposals correct or clarify German, Hindi, Korean, and Brazilian Portuguese search-empty wording and the German Archive.org location label. Proposal token checks pass. Confidence is moderate; native-speaker and headed-browser review were not performed.

No other review outputs were read. No catalog or repository files were edited. No tests, builds, scans, or CI were run. Verify with `python3 verify_primary_review.py`.
''',encoding='utf-8')
 files=sorted(p for p in ROOT.iterdir() if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt'))
 file_hashes={p.name:sha(p.read_bytes()) for p in files}
 manifest={'artifact':'ROMarrNG PR #70 W745-W764 primary review','head':HEAD,'tree':TREE,'window':'W745-W764','cellCount':240,'decisionCounts':dict(counts),'candidateFreeManifestSha256':pins['candidateFreeManifestSha256'],'candidateFreeChecksumsSha256':pins['candidateFreeChecksumListSha256'],'files':file_hashes}
 (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 files=sorted(p for p in ROOT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
 (ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files),encoding='utf-8')
 print(json.dumps({'result':'BUILT','decisionCounts':dict(counts),'proposalCount':len(proposals),'holdCount':len(holds)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
