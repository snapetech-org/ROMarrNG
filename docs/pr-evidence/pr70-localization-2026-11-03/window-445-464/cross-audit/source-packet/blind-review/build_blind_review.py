#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess,sys,os
R=Path(__file__).resolve().parent
I=R/'input/candidate-free-input'
HEAD='81a499b7c022bde61a63dbd8c68c0b1ca39adf26'; TREE='1b075e050610771fc5651d1a4ca95d7c7b4b8e46'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROTECTED=['ROMarr','GG Requestz','RomM','ROMm','ES-DE','gamelist.xml','1G1R','Battle.net','No-Intro','Redump','RetroArch','Steam','EA','Epic','ROM','Hub','DAT']
NAMED=['ROMarrNG','EmuDeck','Flashpoint','Flood','SeerrNG','ROM','DAT','No-Intro','Redump','ES-DE','RomM','GG Requestz','Battle.net']
TOKEN_RE=re.compile(r'\{[A-Za-z][A-Za-z0-9_]*\}')
NUMBER_RE=re.compile(r'(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])')
CHANGES={
 (452,'ar'):{'disposition':'correction','target':'Flashpoint (البث عبر الإنترنت)','confidence':'moderate','rationale':'The caller displays this as a catalogue source-type label. The current Arabic بث مباشر can imply live broadcasting; البث عبر الإنترنت describes streaming without adding a live-only claim. Flashpoint remains unchanged.'},
 (453,'hi'):{'disposition':'correction','target':'Flood में श्रेणियों की जगह टैग होते हैं; यह उनमें से एक है।','confidence':'moderate','rationale':'The caller is explanatory help for Flood’s Tag field. The current wording changes the source statement (“this is one”) into an instruction to enter a tag. The selected wording restores the explanatory statement and keeps Flood exact.'},
 (457,'hi'):{'disposition':'correction','target':'फ़ॉलो करें','confidence':'moderate','rationale':'The checkbox follows the live log as it updates. पालन करना reads as obeying/following instructions; फ़ॉलो करें is the natural action label for this log control.'},
 (461,'pt-BR'):{'disposition':'refinement','target':'Em uma estrutura como a do EmuDeck, defina a raiz da biblioteca ROM como a pasta compartilhada','confidence':'moderate','rationale':'The caller describes an EmuDeck-style shared ROM library. The existing target pluralizes the protected acronym as ROMs, which fails the exact literal check. Biblioteca ROM preserves ROM exactly and remains natural in this technical context.'}
}
HOLD_REASONS={
 458:'No exact source-ID or source-text occurrence exists in the pinned production caller scan. This is a sentence fragment ending in “with”; without its missing partner the target languages’ ending and grammatical completion cannot be checked.',
 460:'No exact source-ID or source-text occurrence exists in the pinned production caller scan. This is a sentence fragment ending in “use”; without the item that follows, completion and punctuation cannot be checked.',
 462:'No exact source-ID or source-text occurrence exists in the pinned production caller scan. The source uses {count} with title(s) number agreement, so without a current caller the possible count values and locale-specific singular/plural rendering cannot be verified.'
}
def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode('utf-8'))
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def phrase_tokens(s): return TOKEN_RE.findall(s)
def nums(s): return NUMBER_RE.findall(TOKEN_RE.sub('',s))
def protected(s):
 return sorted([t for t in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',s)],key=lambda t:s.find(t))
def named(s):
 return sorted([t for t in NAMED if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',s)],key=lambda t:s.find(t))
# Verify candidate-free input offline and save its result as evidence.
env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'
res=subprocess.run([sys.executable,str(I/'verify_input.py')],cwd=I,check=True,capture_output=True,text=True,env=env)
(R/'input-verification.txt').write_text(res.stdout.strip()+'\n',encoding='utf-8')
# Load only the candidate-free source/cell/caller inputs and exact current-head attestation.
sel=readj(I/'selection.json'); sources=readjl(I/'source-inventory-selection.jsonl'); cells=readjl(I/'current-target-cells.jsonl'); contexts=readjl(I/'source-contexts.jsonl')
search=readj(I/'caller-search-audit.json')
latest=readj(R/'latest-head-reattestation.json')
if latest.get('result')!='PASS' or latest.get('latestHead')!=HEAD or latest.get('latestTree')!=TREE: raise SystemExit('FAIL: exact-head reattestation not PASS')
if len(sources)!=20 or len(cells)!=240 or sel.get('cellCount')!=240: raise SystemExit('FAIL: W445-W464 input coverage')
if [x['position'] for x in sources]!=list(range(445,465)): raise SystemExit('FAIL: selection positions/order')
if [x['locale'] for x in cells[:12]]!=LOCALES: raise SystemExit('FAIL: locale order')
if any(x.get('currentTarget') is None for x in cells): raise SystemExit('FAIL: missing current target found')
contexts_by_pos={x['position']:x for x in contexts}
current_by={(x['position'],x['locale']):x for x in cells}
latest_cells={(x['position'],x['locale']):x for x in readjl(R/'latest-head-cell-preimage-comparison.jsonl')}
latest_call_lines=readjl(R/'latest-head-caller-line-comparison.jsonl')
line_ok={(x['position'],x['path'],x['line']) for x in latest_call_lines if x['match']}
queries={(x['position'],x['queryKind']):x for x in search['queries']}
source_catalog=readj(R/'latest-head-files/romarr/ui-labels.json')
ledger=[]
for src in sources:
 pos=src['position']; ctx=contexts_by_pos[pos]
 for locale in LOCALES:
  c=current_by[(pos,locale)]; latest_cell=latest_cells[(pos,locale)]
  entry=source_catalog['messages'][src['sourceId']]
  latest_target=entry['translations'].get(locale)
  if latest_target!=c['currentTarget'] or not latest_cell['currentTargetMatchesD5'] or not latest_cell['sourceMatchesD5']: raise SystemExit(f'FAIL: current source/target drift {pos}/{locale}')
  change=CHANGES.get((pos,locale))
  if change:
   disp=change['disposition']; target=change['target']; confidence=change['confidence']; rationale=change['rationale']
  elif pos in HOLD_REASONS:
   disp='hold'; target=c['currentTarget']; confidence='low'; rationale=HOLD_REASONS[pos]
  else:
   disp='accept-current'; target=c['currentTarget']; confidence='moderate'
   rationale='Current wording fits the source and the verified UI context; preserve the existing translation. Required placeholders, numeric tokens, protected literals, and source-specific names pass.'
  if pos in HOLD_REASONS:
   qid=queries.get((pos,'source-id'),{}); qt=queries.get((pos,'source-text'),{})
   if qid.get('matchCount')!=0 or qt.get('matchCount')!=0 or ctx.get('callerContextRefs'): raise SystemExit(f'FAIL: hold is not supported by caller search {pos}')
  srcph=phrase_tokens(src['source']); tgtph=phrase_tokens(target); curph=phrase_tokens(c['currentTarget'])
  srcnum=nums(src['source']); tgtnum=nums(target)
  srclit=sorted(set(c.get('sourceProtectedLiterals',[]))|set(protected(src['source'])),key=lambda t:src['source'].find(t))
  present=[t for t in srclit if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',target)]
  srcnamed=named(src['source']); nameds=[t for t in srcnamed if t in target]
  refs=ctx.get('callerContextRefs',[])
  verified_refs=[]
  for ref in refs:
   exact=[x for x in ref.get('contextLines',[]) if (pos,ref['path'],x['line']) in line_ok]
   if len(exact)!=len(ref.get('contextLines',[])): raise SystemExit(f'FAIL: caller context not verified on latest head {pos}')
   verified_refs.append({'path':ref['path'],'lineStart':ref['lineStart'],'lineEnd':ref['lineEnd'],'role':ref.get('role'),'anchor':ref.get('anchor'),'contextSha256':ref['contextSha256'],'fileSha256':ref['fileSha256'],'gitBlob':ref['gitBlob'],'latestLineCountMatched':len(exact)})
  caller_names=sorted({t for ref in refs for q in ref.get('contextLines',[]) for t in named(q['text'])})
  target_hash=st(target)
  # Check that the chosen disposition and target are internally consistent.
  if disp=='accept-current' and target!=c['currentTarget']: raise SystemExit('FAIL: accept target differs from current')
  if disp=='hold' and target!=c['currentTarget']: raise SystemExit('FAIL: hold target must retain the current target')
  row={
   'schemaVersion':1,'repository':'snapetech-org/ROMarrNG','pullRequest':70,
   'window':'W445-W464','head':HEAD,'tree':TREE,
   'position':pos,'catalogZeroBasedIndex':src['catalogZeroBasedIndex'],'catalogOneBasedPosition':src['catalogOneBasedPosition'],
   'sourceId':src['sourceId'],'source':src['source'],'sourceSha256':src['sourceSha256'],
   'activeSourceRegistry':src.get('activeSourceRegistry'),'activeSourceRank':src.get('activeSourceRank'),
   'locale':locale,'catalogPath':'romarr/ui-labels.json','catalogSha256':readj(R/'input/candidate-free-input/catalog-file-pins.json')['catalogSha256'],
   'catalogGitBlob':readj(R/'input/candidate-free-input/catalog-file-pins.json')['callerSourceFilePins']['romarr/ui-labels.json']['gitBlob'],
   'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'catalogTranslationHash':c['catalogTranslationHash'],
   'disposition':disp,'selectedTarget':target,'selectedTargetSha256':target_hash,'rationale':rationale,'linguisticConfidence':confidence,
   'callerContext':{'callerCount':len(refs),'sourceIdExactMatchCount':ctx.get('sourceIdExactMatchCount',0),'sourceTextExactMatchCount':ctx.get('sourceTextExactMatchCount',0),'callerContextSha256':c.get('callerContextSha256'),'callerContextRefs':verified_refs,'callerNamedLiterals':caller_names,'callerSearchScope':search.get('scope'),'callerlessHeldForContext':disp=='hold' and len(refs)==0},
   'tokenChecks':{'sourcePlaceholders':srcph,'currentPlaceholders':curph,'selectedPlaceholders':tgtph,'placeholderMultisetMatches':Counter(srcph)==Counter(tgtph),'placeholderSequenceMatches':srcph==tgtph,'sourceNumericTokens':srcnum,'selectedNumericTokens':tgtnum,'numericTokensPreserved':srcnum==tgtnum,'sourceProtectedLiterals':srclit,'selectedProtectedLiteralsPresent':present,'protectedLiteralsPreserved':present==srclit,'sourceNamedLiterals':srcnamed,'selectedNamedLiteralsPresent':nameds,'namedLiteralsPreserved':nameds==srcnamed},
   'baselineDiagnostics':{'currentPlaceholderMultisetMatches':Counter(srcph)==Counter(curph),'currentNumericTokensPreserved':srcnum==nums(c['currentTarget']),'currentProtectedLiteralMismatch':len(srclit)>len([t for t in srclit if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',c['currentTarget'])])}
  }
  if not row['tokenChecks']['placeholderMultisetMatches'] or not row['tokenChecks']['numericTokensPreserved'] or not row['tokenChecks']['protectedLiteralsPreserved'] or not row['tokenChecks']['namedLiteralsPreserved']: raise SystemExit(f'FAIL: selected token/literal check {pos}/{locale}')
  ledger.append(row)
(R/'blind-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in ledger),encoding='utf-8')
disps=Counter(x['disposition'] for x in ledger)
holds=Counter(x['position'] for x in ledger if x['disposition']=='hold')
summary={'schemaVersion':1,'result':'PASS','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W445-W464','candidateFreeInputCommit':'d5ba7f1f268501f45227388c46d5f938ed0c9191','candidateFreeInputTree':'2f8ce1af963b315108f668fc31c94ca90ecd1351','latestAttestedHead':HEAD,'latestAttestedTree':TREE,'latestHeadReattestation':'PASS','cellsReviewed':len(ledger),'sourcesReviewed':20,'localesReviewed':12,'dispositionCounts':dict(disps),'selectedTargetChanges':sum(x['selectedTarget']!=x['currentTarget'] for x in ledger),'placeholderFailures':sum(not x['tokenChecks']['placeholderMultisetMatches'] for x in ledger),'numericFailures':sum(not x['tokenChecks']['numericTokensPreserved'] for x in ledger),'protectedLiteralFailures':sum(not x['tokenChecks']['protectedLiteralsPreserved'] for x in ledger),'namedLiteralFailures':sum(not x['tokenChecks']['namedLiteralsPreserved'] for x in ledger),'sourceRowsWithCallerContext':sum(1 for x in contexts if x.get('callerContextRefs')),'callerlessSourcePositionsHeld':sorted(holds),'callerlessHoldCells':sum(1 for x in ledger if x['disposition']=='hold' and x['callerContext']['callerCount']==0),'baselineProtectedLiteralOmissionsCorrected':1,'baselineLiteralCorrection':{'position':461,'locale':'pt-BR','literal':'ROM'},'inputPriorSelectionSourcesReattested':60,'inputCarriedHoldsReattested':348,'nativeSpeakerReviewClaimed':False,'candidateOrPrimaryOutputsRead':False,'crossReconciliationPerformed':False,'repositoryOrPRChanged':False,'testsBuildsScansCIorBrowserRun':False}
(R/'blind-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme='''# ROMarrNG PR #70 W445-W464 independent blind review

This packet reviews the 240 cells selected by catalog insertion positions 445-464 from the sealed candidate-free source/cell input at d5ba7f1f. The input verifier passed and confirms it contains no proposed targets or current-window decisions. The primary and cross-review outputs were not opened or used.

The PR advanced to the docs-only commit 81a499b7 while this review was underway. Its tree is 1b075e05, parent d5ba7f1f. All 9 d5-pinned source/catalog/caller files, all 240 current-target preimages, all 20 source definitions, and 319 caller context lines (237 unique) match the new exact head. The PR remained OPEN/DRAFT and branch/pull refs matched before and after. This d5 candidate-free input is therefore unchanged at the latest head.

The blind ledger records 200 accept-current, 3 corrections, 1 refinement, and 36 holds. The three callerless source fragments/labels at positions 458 and 460 and the count/plural template at 462 are held for missing exact production callsites. Positions 453 hi and 457 hi are corrected from caller context; position 452 ar is corrected to avoid implying a live broadcast; position 461 pt-BR refines ROMs to the exact protected acronym ROM. All selected placeholders, numeric tokens, protected literals, and source-specific named terms pass.

A preliminary extraction initially interpreted active source-registry ranks as W445-W464. It made no translation decisions and was rejected when the candidate-free packet showed that this window is defined by catalog insertion positions. That source-only extraction is retained under evidence/preliminary-registry-rank-extraction/ for traceability; it is not an input to the blind ledger.

No repository or PR content was changed. No tests, builds, scans, CI, or browser work were performed. No native-speaker review is claimed.

Run python3 verify_blind_review.py to verify the packet and checksums.
'''
(R/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
