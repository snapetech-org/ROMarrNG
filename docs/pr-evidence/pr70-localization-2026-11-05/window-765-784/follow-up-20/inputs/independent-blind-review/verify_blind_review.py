#!/usr/bin/env python3
"""Verify the independent blind review packet using static candidate-free evidence only."""
import hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CFROOT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/candidate-free')
INP=CFROOT/'input'
HEAD='9714d7cf69c687685b4f65cbd9627a56830bab85'
TREE='c8eb66573f10b2390a02df05033f5133425d5e41'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']

def fail(msg): raise SystemExit('FAIL: '+msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def read_jsonl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def protected(s):
 out=[]
 for lit in PROTECTED:
  hit=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
  if hit: out.append(lit)
 return sorted(set(out))
def tokens(s): return {'placeholders':PLACEHOLDER.findall(s),'markup':TAG.findall(s),'numbers':NUMBER.findall(s),'protectedLiterals':protected(s)}
def assert_sums(directory, filename):
 r=subprocess.run(['sha256sum','-c',filename],cwd=directory,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if r.returncode: fail(f'checksum validation failed in {directory}: {r.stdout}')
 return r.stdout

# Validate immutable packet seals. This hashes candidate-free target-cell file without opening its text values.
assert_sums(CFROOT,'SHA256SUMS.txt')
assert_sums(INP,'SHA256SUMS.txt')
manifest=read_json(INP/'manifest.json'); selection=read_json(INP/'selection.json')
if (manifest.get('head'),manifest.get('tree'),manifest.get('pullRequest'),manifest.get('window')) != (HEAD,TREE,70,'W765-W784'): fail('manifest pin mismatch')
if selection.get('positions') != [765,784] or selection.get('localeOrder') != LOCALES or selection.get('cellCount') != 240: fail('selection pin/order mismatch')
for name in ('PR-attestation-before.json','PR-attestation-after.json'):
 a=read_json(INP/name)
 if (a.get('head'),a.get('tree'),a.get('pullRequest'),a.get('repository')) != (HEAD,TREE,70,'snapetech-org/ROMarrNG'): fail('PR attestation mismatch')
a=read_json(INP/'PR-attestation-before.json'); b=read_json(INP/'PR-attestation-after.json')
if {k:v for k,v in a.items() if k!='attestedAtUtc'} != {k:v for k,v in b.items() if k!='attestedAtUtc'}: fail('before/after PR attestation changed')

pins=read_json(ROOT/'input-pins.json')
if (pins.get('head'),pins.get('tree'),pins.get('window')) != (HEAD,TREE,'W765-W784'): fail('packet input pin mismatch')
if pins.get('candidateFreeOuterChecksumListSha256') != sha((CFROOT/'SHA256SUMS.txt').read_bytes()): fail('outer checksum-list pin mismatch')
if pins.get('candidateFreeInputChecksumListSha256') != sha((INP/'SHA256SUMS.txt').read_bytes()): fail('inner checksum-list pin mismatch')
if pins.get('changedWorktreeInspected') is not False or pins.get('primaryCrossRootEvidenceInspected') is not False: fail('independence boundary incorrect')

selected=read_jsonl(INP/'selected-sources.jsonl'); contexts=read_jsonl(INP/'source-contexts.jsonl')
if len(selected)!=20 or len(contexts)!=20: fail('source context count mismatch')
selected_by={r['sourceId']:r for r in selected}; context_by={r['sourceId']:r for r in contexts}
if set(selected_by)!=set(context_by): fail('selected source/context IDs differ')
callerless_ids={sid for sid,r in selected_by.items() if r.get('sourceTextOmitted') is True}
callerbacked_ids=set(selected_by)-callerless_ids
if len(callerless_ids)!=2 or len(callerbacked_ids)!=18: fail('callerless/caller-backed source counts mismatch')
if sum(len(context_by[s]['callers']) for s in callerbacked_ids)!=23: fail('caller-reference count mismatch')

proposal_rows=read_jsonl(ROOT/'blind-locale-review.jsonl')
if len(proposal_rows)!=216: fail('proposal row count mismatch')
freeze=read_json(ROOT/'proposal-freeze.json')
if freeze.get('proposalSha256') != sha((ROOT/'blind-locale-review.jsonl').read_bytes()): fail('proposal freeze hash mismatch')
if freeze.get('matrixSha256') != sha((ROOT/'independent-translation-matrix.json').read_bytes()): fail('matrix freeze hash mismatch')
if freeze.get('frozenBeforeCurrentCellHashesOpened') is not True or freeze.get('currentTargetTextsConsulted') is not False: fail('proposal independence claim mismatch')
seen=set(); per_source={}
for row in proposal_rows:
 sid=row.get('sourceId'); locale=row.get('locale'); key=(sid,locale)
 if sid not in callerbacked_ids or locale not in LOCALES or key in seen: fail('unexpected or duplicate proposal row')
 seen.add(key); per_source.setdefault(sid,0); per_source[sid]+=1
 src=selected_by[sid]; ctx=context_by[sid]
 if (row.get('position'),row.get('catalogZeroBasedIndex'),row.get('catalogOneBasedPosition'),row.get('source'),row.get('sourceSha256'),row.get('sourceContextSha256')) != (src['position'],src['catalogZeroBasedIndex'],src['catalogOneBasedPosition'],src['source'],src['sourceSha256'],ctx['contextSha256']): fail('proposal source pin mismatch '+sid)
 if row.get('disposition')!='blind_proposal' or row.get('tokensPreserved') is not True or row.get('nativeSpeakerApproval') is not False: fail('proposal disposition/token state mismatch')
 if row.get('reviewBasis')!='pinned source and caller context only; current locale target not consulted': fail('proposal basis mismatch')
 if row.get('callerCount') != len(ctx['callers']) or row.get('callerReferences') != [{k:c[k] for k in ('path','line','lineText','lineSha256','excerptSha256','fileSha256','gitBlob','matchKind')} for c in ctx['callers']]: fail('caller references differ from pinned evidence '+sid)
 if row.get('proposalSha256') != sha(row['proposal'].encode('utf-8')): fail('proposal text hash mismatch')
 src_sig=tokens(src['source']); target_sig=tokens(row['proposal'])
 for kind in ('placeholders','markup','numbers'):
  if src_sig[kind] != target_sig[kind]: fail(f'{kind} mismatch {sid}/{locale}')
 if not set(src_sig['protectedLiterals']).issubset(target_sig['protectedLiterals']): fail('protected source literal mismatch '+sid+'/'+locale)
 if row.get('sourceTokenSignature') != src_sig or row.get('proposalTokenSignature') != target_sig: fail('token signature mismatch '+sid+'/'+locale)
 for literal in row.get('manualProtectedLiteralsRequired',[]):
  if literal not in row['proposal']: fail('manual literal missing '+sid+'/'+locale)
 if row.get('manualProtectedLiteralsRequired') != ({
   'ui.one-title-per-line-comments-ranking.8c54c86102':['# comments','Title\u00a0→tab←\u00a0platform'],
   'ui.openxbl-api-key.90ea47aa7f':['OpenXBL','API'],
   'ui.optional-apprise-urls-to-notify-one.8ef42d4f02':['Apprise','URLs']
 }.get(sid,[])): fail('manual literal requirement drift '+sid)
if len(seen)!=216 or set(per_source.values())!={12}: fail('proposal locale coverage incomplete')

# Only inspect the 24 callerless row metadata below. No current target value is accessed or copied.
cell_rows=read_jsonl(INP/'candidate-free-cells.jsonl')
raw_holds=[r for r in cell_rows if r.get('callerless') is True and r.get('sourceTextOmitted') is True and r.get('currentTargetTextOmitted') is True]
if len(raw_holds)!=24: fail('candidate-free callerless hash row count mismatch')
output_holds=read_jsonl(ROOT/'current-window-holds.jsonl')
if len(output_holds)!=24: fail('output callerless hash row count mismatch')
raw_hashes={(r['position'],r['sourceId'],r['locale']):r['currentTargetSha256'] for r in raw_holds}
new_hashes={(r['position'],r['sourceId'],r['locale']):r['currentTargetSha256'] for r in output_holds}
if raw_hashes != new_hashes: fail('callerless hold hashes do not match candidate-free pins')
for row in output_holds:
 if row.get('disposition')!='hold_hash_only' or row.get('textOmitted') is not True or row.get('callerless') is not True or row.get('sourceTextOmitted') is not True or row.get('currentTargetTextOmitted') is not True: fail('hold is not text-free')
 if any(k.lower() in {'source','sourcetext','target','targettext','translation','translationtext','currenttarget'} for k in row): fail('held text field present')
 if row['locale'] not in LOCALES: fail('held locale invalid')
if {r['position'] for r in output_holds}!={771,774} or any(sum(1 for r in output_holds if r['position']==pos)!=12 for pos in (771,774)): fail('hold position/locale count mismatch')

# Prior hold hashes are preserved byte-for-byte and remain text-free.
prior_path=INP/'prior-hold-reattestation.jsonl'; out_prior=ROOT/'prior-hold-lineage.jsonl'
prior=read_jsonl(prior_path)
if len(prior)!=988 or out_prior.read_bytes()!=prior_path.read_bytes(): fail('prior hold lineage not preserved byte-for-byte')
if not all(r.get('textOmitted') is True for r in prior): fail('prior hold text-free attestation missing')
if any(any(k.lower() in {'source','sourcetext','target','targettext','translation','translationtext','currenttarget'} for k in r) for r in prior): fail('prior hold text field present')
prior_summary=read_json(INP/'prior-hold-reattestation-summary.json')
if prior_summary.get('count')!=988 or prior_summary.get('allTargetHashesMatch') is not True or prior_summary.get('textInHoldRows') is not False: fail('prior hold summary mismatch')
if (ROOT/'prior-hold-context-reattestation.jsonl').read_bytes() != (INP/'prior-hold-context-reattestation.jsonl').read_bytes(): fail('prior hold context lineage mismatch')
context_rows=read_jsonl(ROOT/'prior-hold-context-reattestation.jsonl')
if len(context_rows)!=86 or any(r.get('callerTextOmitted') is not True or r.get('sourceTextOmitted') is not True for r in context_rows): fail('prior hold caller context is not text-free')
if len(prior)+len(output_holds)!=1012: fail('active hold total mismatch')

# Check one disposition per selected cell, and that held records expose hashes only.
dispositions=read_jsonl(ROOT/'dispositions.jsonl')
if len(dispositions)!=240: fail('disposition count mismatch')
if sum(r.get('disposition')=='blind_proposal' for r in dispositions)!=216 or sum(r.get('disposition')=='hold_hash_only' for r in dispositions)!=24: fail('disposition totals mismatch')
for row in dispositions:
 if row.get('disposition')=='hold_hash_only' and any(k.lower() in {'source','sourcetext','target','targettext','translation','translationtext','currenttarget'} for k in row): fail('held disposition contains text field')

summary=read_json(ROOT/'review-summary.json')
if (summary.get('head'),summary.get('tree'),summary.get('cellCount'),summary.get('callerReferences'),summary.get('priorActiveHolds'),summary.get('newHashOnlyHolds'),summary.get('resultingActiveHashOnlyHolds')) != (HEAD,TREE,240,23,988,24,1012): fail('review summary counts/pin mismatch')
if manifest.get('nextBoundary') != summary.get('nextBoundary') or summary['nextBoundary'].get('continuationIndex')!=785: fail('next boundary mismatch')
print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':'W765-W784','cells':240,'proposalCells':216,'callerReferences':23,'newHashOnlyHolds':24,'priorActiveHolds':988,'resultingActiveHashOnlyHolds':1012,'tokenMismatches':0,'candidateFreeOuterChecksums':'PASS','candidateFreeInnerChecksums':'PASS','productWorktreeRead':'false','nextBoundary':summary['nextBoundary']},ensure_ascii=False,indent=2))
