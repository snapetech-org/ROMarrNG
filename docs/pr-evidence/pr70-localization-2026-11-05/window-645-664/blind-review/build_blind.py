#!/usr/bin/env python3
"""Independent blind semantic review of ROMarrNG PR #70 W645-W664."""
import hashlib,json,re,subprocess
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
INPUT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w645-664-20261105/candidate-free/candidate-free/input')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261105/romarrng-pr70-w625-644-pinned')
HEAD='9f8832f67195323955172dd4c3c40e29cbabb5da'; TREE='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
LOCS=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
FIXES={
 ('ui.missing.6be36ca49e','id'):('propose-correction','Tidak ditemukan',
  'Tidak ada means “there is none” and can read opposite to the Missing status. This value labels both a Wanted/Missing navigation item and a count of missing inventory entries; Tidak ditemukan means not found and preserves the intended status.','moderate'),
 ('ui.multi-disc-set-is-grouped-for-metada.86db33ad47','ar'):('propose-correction','يُجمَّع الإصدار متعدد الأقراص لأغراض البيانات الوصفية؛ وتبقى ملفات الأقراص معًا.',
  'The current “الميتا البيانات” is not idiomatic Arabic for metadata and the spacing around the semicolon is wrong. البيانات الوصفية is the established Arabic term and this wording retains the grouped-set and files-stay-together meaning.','moderate'),
 ('ui.multi-disc-set-is-grouped-for-metada.86db33ad47','es'):('propose-refinement','El conjunto de varios discos se agrupa para los metadatos; sus archivos de disco permanecen juntos',
  'The current “multi-disc” is an English borrowing in Spanish. “Conjunto de varios discos” states the same grouped-set meaning in plain Spanish.','moderate'),
 ('ui.multi-disc-set-is-grouped-for-metada.86db33ad47','hi'):('propose-refinement','मल्टी-डिस्क सेट को मेटाडेटा के लिए एक समूह में रखा जाता है; इसकी डिस्क फ़ाइलें साथ रहती हैं',
  'The current “समूह किया जाता है” is an awkward construction. “एक समूह में रखा जाता है” states that the set is grouped for metadata while retaining the meaning that its disc files stay together.','moderate'),
 ('ui.multi-disc-set-is-grouped-for-metada.86db33ad47','id'):('propose-correction','Set multi-disk dikelompokkan untuk metadata; berkas tiap disk tetap bersama',
  'The current “dikumpulkan” means collected, rather than grouped. “Dikelompokkan” carries the source operation; this also keeps the invariant that the disc files stay together.','moderate'),
 ('ui.my-library.fbc3b89e6a','pt-BR'):('propose-refinement','Minha biblioteca',
  'The current value adds a terminal period to a short button label, unlike the English source and peer-locale label values. Remove the sentence punctuation for consistent UI labeling.','high'),
}
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']
def sha(x): return hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def readjl(path): return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s]
def wj(path,x): path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def wjl(path,x): path.write_text(''.join(canon(a)+'\n' for a in x),encoding='utf-8')
def tokens(text):
 p=re.findall(r'\{[^{}]+\}',text); m=re.findall(r'<[^>]+>',text); n=re.findall(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])',text)
 z=[]
 for x in PROTECTED:
  if (x.startswith('/') and x in text) or (not x.startswith('/') and re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',text)): z.append(x)
 return p,m,n,sorted(set(z))
def main():
 subprocess.check_call(['python','verify_input.py','--repo',str(REPO),'--input',str(INPUT)],cwd=INPUT)
 m=json.loads((INPUT/'manifest.json').read_text(encoding='utf-8'))
 if (m['head'],m['tree'])!=(HEAD,TREE): raise RuntimeError('candidate-free input head/tree mismatch')
 contexts={x['sourceId']:x for x in readjl(INPUT/'source-contexts.jsonl')}
 cells=readjl(INPUT/'current-target-cells.jsonl'); rows=[]; proposals=[]; holds=[]
 for c in cells:
  sid,loc,p=c['sourceId'],c['locale'],c['position']; ctx=contexts[sid]
  if ctx['callerless']:
   row={'position':p,'sourceId':sid,'sourceSha256':c['sourceSha256'],'locale':loc,'callerContextSha256':c['callerContextSha256'],'callerless':True,
    'currentTargetSha256':c['currentTargetSha256'],'disposition':'text-free-hold','reason':'No production caller resolves this source ID at the pinned head; preserve as a hash-only hold until valid caller context exists.','confidence':'high'}
   holds.append({k:row[k] for k in ('position','sourceId','sourceSha256','locale','callerContextSha256','currentTargetSha256','reason','confidence')})
  else:
   key=(sid,loc)
   if key in FIXES: disp,target,reason,confidence=FIXES[key]
   else:
    disp='accept-current'; target=c['currentTarget']; confidence='moderate'
    reason=f"The current localized value preserves the meaning of {c['source']!r} in the pinned caller context ({', '.join(sorted({x['path'] for x in ctx['callers']}))})."
   if disp not in ('accept-current','propose-correction','propose-refinement'): raise RuntimeError('invalid caller-backed disposition')
   source_tokens=tokens(c['source']); target_tokens=tokens(target)
   if source_tokens[:3]!=target_tokens[:3] or any(x not in target_tokens[3] for x in source_tokens[3]): raise RuntimeError(f'token/literal mismatch: {sid}/{loc}')
   row={'position':p,'sourceId':sid,'sourceSha256':c['sourceSha256'],'source':c['source'],'locale':loc,'callerContextSha256':c['callerContextSha256'],
    'callerPaths':sorted({x['path'] for x in ctx['callers']}),'callerRefCount':ctx['exactMatchCount'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
    'disposition':disp,'selectedTarget':target,'selectedTargetSha256':sha(target),'reason':reason,'confidence':confidence,'placeholdersPreserved':source_tokens[0]==target_tokens[0],
    'markupPreserved':source_tokens[1]==target_tokens[1],'numericTokensPreserved':source_tokens[2]==target_tokens[2],'protectedLiteralsPreserved':all(x in target_tokens[3] for x in source_tokens[3])}
   if disp!='accept-current': proposals.append({k:row[k] for k in ('position','sourceId','sourceSha256','locale','callerContextSha256','currentTargetSha256','selectedTarget','selectedTargetSha256','disposition','reason','confidence')})
  rows.append(row)
 wjl(P/'blind-ledger.jsonl',rows); wjl(P/'proposals.jsonl',proposals); wjl(P/'hash-only-holds.jsonl',holds)
 counts={d:sum(x['disposition']==d for x in rows) for d in ('accept-current','propose-correction','propose-refinement','text-free-hold')}
 summary={'artifact':'ROMarrNG PR #70 W645-W664 independent blind semantic review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,
  'candidateFreeChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'sourceCount':20,'localeCount':12,'cellCount':len(rows),'callerBackedCellCount':len(rows)-len(holds),
  'counts':counts,'proposalCount':len(proposals),'holdCount':len(holds),'allCallerBackedCellsIndependentlyReviewed':True,'placeholderMarkupNumericProtectedLiteralReview':True,
  'nativeSpeakerSignoff':False,'browserReviewPerformed':False,'createdAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds')}
 wj(P/'SUMMARY.json',summary)
 (P/'README.md').write_text(f'''# ROMarrNG PR #70 W645-W664 blind review

Independent blind semantic review of all 240 catalog cells in the sealed candidate-free packet at {INPUT}. Pinned PR head/tree: {HEAD} / {TREE}. The review contains {summary['callerBackedCellCount']} caller-backed cells and {len(holds)} callerless cells held without translation text.

Dispositions: {counts}. Proposed targets were selected independently from the source text, exact caller context, and current target values. This machine-assisted review does not constitute native-speaker approval or browser acceptance.
''',encoding='utf-8')
 sums=[f'{sha(p.read_bytes())}  {p.name}' for p in sorted(P.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt']
 (P/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
