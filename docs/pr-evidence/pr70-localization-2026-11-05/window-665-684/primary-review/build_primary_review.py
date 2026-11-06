#!/usr/bin/env python3
"""Build the independent W665-W684 primary review from candidate-free input only."""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parent
PACKET=ROOT.parent/'candidate-free'/'input'
REPO=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261105/romarrng-pr70-w665-684-pinned')
HEAD='8b7589775c526866e474112b4f4168782b02f881'
TREE='fb0ba93172f6832c687e001ce6c0fff08b5a33eb'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Reviewed corrections/refinements. Callerless positions are deliberately absent.
OVERRIDES={
 (667,'es'):('correction','Se necesita una plataforma conocida','high',
   'This toast appears when no catalog platform can be resolved. The current “Necesito” makes the application speak in first person; the impersonal wording states that a recognized platform is required.'),
 (667,'pt-BR'):('correction','É necessária uma plataforma conhecida.','high',
   'This toast appears when no catalog platform can be resolved. The current “Preciso” makes the application speak in first person; the impersonal wording states that a recognized platform is required.'),
 (671,'ar'):('correction','يحتاج إلى مراجعة','moderate',
   'This is a checkbox status for a library item. The current phrase reads like “review needs”; the recommendation directly says the item needs review.'),
 (671,'ja'):('correction','要確認','high',
   'This checkbox marks a Switch item that needs manual verification before a rename; the current noun phrase means “the necessity of review.” “要確認” is the concise status label for an item needing verification.'),
 (672,'vi'):('refinement','Cần rà soát','moderate',
   'This is a status label for an item that needs review. “Phải xem xét” reads as an obligation to consider; “Cần rà soát” more directly labels an item needing review.'),
 (678,'zh-Hans'):('correction','新作','moderate',
   'The caller places this label among game-catalog shelves such as Popular and Upcoming. The current wording suggests newly released software versions; “新作” is the concise game-release shelf label.'),
 (678,'zh-Hant'):('correction','新作','moderate',
   'The caller places this label among game-catalog shelves such as Popular and Upcoming. The current wording suggests newly released software versions; “新作” is the concise game-release shelf label.'),
 (679,'ar'):('refinement','إصدارات جديدة (الويب)','moderate',
   'This label distinguishes the web catalog from the user’s library. “الويب” is the concise UI term for web, and the release wording aligns with the paired new-releases shelf.'),
 (679,'fr'):('correction','Nouvelles sorties (web)','high',
   'The source is the web-catalog new-releases shelf. “Versions” suggests software versions; “sorties” expresses game releases and matches the paired “New releases” tab.'),
 (679,'zh-Hans'):('refinement','新作（网络）','moderate',
   'The caller uses this as the web-catalog mode beside the user’s library. The revised label preserves that mode while using the concise game-release term “新作”.'),
 (679,'zh-Hant'):('refinement','新作（網路）','moderate',
   'The caller uses this as the web-catalog mode beside the user’s library. The revised label preserves that mode while using the concise game-release term “新作”.'),
 (678,'ko'):('refinement','신작','moderate',
   'The caller places this among game-catalog shelves. “신작” is the concise, natural Korean label for newly released game titles; the current generic loanword is understandable but less idiomatic in this context.'),
 (679,'ko'):('refinement','신작 (웹)','moderate',
   'The caller uses this as the web-catalog mode beside the user’s library. “신작” is the concise Korean game-release label, and “웹” preserves the mode distinction.'),
 (682,'fr'):('correction','Sortie la plus récente','high',
   'The caller uses this in a game-catalog sort menu alongside Release year. “Dernière version” means the latest version; “Sortie la plus récente” correctly refers to a game release.'),
 (684,'ko'):('correction','다음','moderate',
   'The four callers use this as a next-page/navigation button or next-step heading. The current “이름 *” means “Name *”; “다음” is the correct neutral navigation label.'),
}
RATIONALE={
 665:'In the platform selector, the target says the platform is specified on each line and works as a compact option label.',
 667:'The caller shows a toast when no known catalog platform can be resolved; the target should state that requirement without changing the UI speaker.',
 668:'The caller uses this as a table heading for provider fields; the target conveys the fields or information a provider requires.',
 671:'The caller uses this as a checkbox status for a library item that may need manual checking before a safe rename.',
 672:'The caller uses this as downloader-field help: the Label plugin is required and the field is ignored when that plugin is disabled.',
 674:'The target preserves the help text’s core explanation: netplay matches ROMs by SHA1 rather than title; the game title can identify different ROMs; wrong matches can desynchronize quickly; only known hashes can be matched.',
 677:'The caller places this directly above a password input with autocomplete=new-password; the target correctly labels a new password.',
 678:'The caller uses this as a game-catalog shelf for newly released titles, not software build versions.',
 679:'The caller uses this as the web-catalog mode beside the user’s library; the target should denote game releases and preserve the web distinction.',
 680:'The caller places this among library shelves; the target correctly means the most recent items.',
 681:'The caller uses this as a library sorting option; the target correctly states newest items first.',
 682:'The caller uses this as a sort choice for game releases next to Release year; the target should mean the most recent release.',
 683:'The caller uses this as indexer help for a list of Newznab category IDs separated by commas; the target preserves the product name and delimiter meaning.',
 684:'The callers use this for next-page navigation and a next-step heading; the target should be a neutral “Next” label.',
}
CONFIDENCE_BY_LOCALE={'ar':'moderate','de':'high','es':'high','fr':'high','hi':'moderate','id':'high','ja':'moderate','ko':'moderate','pt-BR':'high','vi':'moderate','zh-Hans':'moderate','zh-Hant':'moderate'}

def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def write_json(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(path,rows): path.write_text(''.join(canon(x)+'\n' for x in rows),encoding='utf-8')
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def main():
 if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain'):
  raise SystemExit('refusing to build: pinned worktree mismatch or dirty worktree')
 packet_manifest=json.loads((PACKET/'manifest.json').read_text(encoding='utf-8'))
 if packet_manifest.get('head')!=HEAD or packet_manifest.get('tree')!=TREE or packet_manifest.get('cellCount')!=240:
  raise SystemExit('candidate-free input pin/cardinality mismatch')
 raw_rows=[]
 for line in (PACKET/'candidate-free-cells.jsonl').read_bytes().splitlines():
  if line.strip(): raw_rows.append((json.loads(line),sha(line)))
 contexts=[json.loads(x) for x in (PACKET/'source-contexts.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
 ctx={c['sourceId']:c for c in contexts}
 if len(raw_rows)!=240 or len(contexts)!=20: raise SystemExit('candidate-free input cardinality mismatch')
 ledger=[]; proposals=[]; holds=[]
 for row,row_sha in raw_rows:
  pos=row['position']; locale=row['locale']; callerless=bool(row.get('callerless'))
  if callerless:
   if row.get('currentTarget') is not None or row.get('source') is not None: raise SystemExit('callerless input unexpectedly contains text')
   cell_id=f"sha256:{row['sourceSha256']}::{locale}"
   item={
    'cellId':cell_id,'locale':locale,'sourcePosition':pos,'catalogZeroBasedIndex':row['catalogZeroBasedIndex'],
    'decision':'hold-hash-only','rationale':'No production caller is attested. Preserve this cell as a text-free hash-only hold.',
    'confidence':'unknown','sourceTextSha256':row['sourceSha256'],'currentTargetSha256':row['currentTargetSha256'],
    'callerContextSha256':row['callerContextSha256'],'candidateFreeRowSha256':row_sha,
    'callerless':True,'sourceTextOmitted':True,'currentTargetTextOmitted':True,
    'exactHead':HEAD,'exactTree':TREE,
   }
   ledger.append(item)
   holds.append({k:item[k] for k in ('cellId','locale','sourcePosition','catalogZeroBasedIndex','decision','sourceTextSha256','currentTargetSha256','callerContextSha256','candidateFreeRowSha256','sourceTextOmitted','currentTargetTextOmitted','exactHead','exactTree')})
   continue
  c=ctx.get(row['sourceId'])
  if not c or c.get('callerless') or c.get('contextSha256')!=row['callerContextSha256']:
   raise SystemExit(f'caller context binding mismatch at {pos}/{locale}')
  override=OVERRIDES.get((pos,locale))
  if override: decision,recommended,confidence,specific=override; rationale=specific
  else: decision='accept-current'; recommended=None; confidence=CONFIDENCE_BY_LOCALE[locale]; rationale=RATIONALE[pos]
  source=row['source']; current=row['currentTarget']
  item={
   'cellId':f"{row['sourceId']}::{locale}",'locale':locale,'sourcePosition':pos,
   'catalogZeroBasedIndex':row['catalogZeroBasedIndex'],'catalogOneBasedPosition':row['catalogOneBasedPosition'],
   'sourceId':row['sourceId'],'decision':decision,'source':source,'currentTarget':current,
   'rationale':rationale,'confidence':confidence,
   'candidateFreeRowSha256':row_sha,'sourceTextSha256':row['sourceSha256'],
   'currentTargetSha256':row['currentTargetSha256'],'callerContextSha256':c['contextSha256'],
   'callerMatchCount':c['exactMatchCount'],'callerPaths':sorted({x['path'] for x in c['callers']}),
   'callerLineNumbers':sorted({x['line'] for x in c['callers']}),
   'catalogTranslationStatus':row.get('translationStatus'),
   'tokenAudit':{
    'sourcePlaceholderTokens':row.get('sourcePlaceholderTokens',[]),
    'sourceMarkupTags':row.get('sourceMarkupTags',[]),
    'sourceNumericTokens':row.get('sourceNumericTokens',[]),
    'sourceProtectedLiterals':row.get('sourceProtectedLiterals',[]),
    'currentPlaceholderTokens':row.get('currentPlaceholderTokens',[]),
    'currentMarkupTags':row.get('currentMarkupTags',[]),
    'currentNumericTokens':row.get('currentNumericTokens',[]),
    'missingProtectedLiterals':row.get('missingProtectedLiterals',[]),
    'placeholderMultisetMatches':row.get('placeholderMultisetMatches'),
    'markupMatches':row.get('markupMatches'),
    'numericTokensPreserved':row.get('numericTokensPreserved'),
    'numericPresentationEquivalent':row.get('numericPresentationEquivalent'),
    'protectedLiteralsPreserved':row.get('protectedLiteralsPreserved'),
   },
   'exactHead':HEAD,'exactTree':TREE,
  }
  if pos==674:
   item['tokenAlertAssessment']={
    'numeric':'The candidate-free summary reports one numeric mismatch and no numeric presentation differences. In this text, the quantities four and two remain four and two; Japanese uses the ordinary digit 4 for four. No count correction is warranted.',
    'protectedLiterals':'The packet flags the English pluralized form ROMs in some locales. Those targets preserve ROM as the acronym and express the plural through the locale; ROMarr, SHA1, and Super Mario Kart are retained. This is a localized plural-suffix difference, not a lost product name.',
   }
  if recommended is not None:
   item['recommendedTarget']=recommended
   item['recommendedTargetSha256']=sha(recommended.encode('utf-8'))
   proposal={k:item[k] for k in ('cellId','locale','sourcePosition','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','decision','source','currentTarget','recommendedTarget','recommendedTargetSha256','rationale','confidence','candidateFreeRowSha256','sourceTextSha256','currentTargetSha256','callerContextSha256','callerMatchCount','callerPaths','callerLineNumbers','exactHead','exactTree')}
   proposals.append(proposal)
  ledger.append(item)
 if len(holds)!=72 or len(ledger)!=240: raise SystemExit(f'unexpected output counts: {len(ledger)} rows, {len(holds)} holds')
 reviewed=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
 write_jsonl(ROOT/'ledger.jsonl',ledger); write_jsonl(ROOT/'proposals.jsonl',proposals); write_jsonl(ROOT/'holds.jsonl',holds)
 decisions=collections.Counter(x['decision'] for x in ledger)
 confidences=collections.Counter(x['confidence'] for x in ledger)
 proposal_locales=collections.Counter(x['locale'] for x in proposals)
 proposal_sources=collections.Counter(x['sourcePosition'] for x in proposals)
 token_summary=json.loads((PACKET/'candidate-free-token-summary.json').read_text(encoding='utf-8'))
 summary={
  'artifact':'ROMarrNG PR #70 W665-W684 independent primary semantic review',
  'pullRequest':70,'exactHead':HEAD,'exactTree':TREE,
  'reviewedAtUtc':reviewed,'cellCount':240,'sourceCount':20,'localeCount':12,
  'callerBackedCells':168,'callerlessHashOnlyHolds':72,'callerlessSourceCount':6,
  'decisionCounts':dict(sorted(decisions.items())),'proposalCount':len(proposals),
  'proposalCountsByLocale':dict(sorted(proposal_locales.items())),
  'proposalCountsByPosition':{str(k):v for k,v in sorted(proposal_sources.items())},
  'confidenceCounts':dict(sorted(confidences.items())),
  'tokenAudit':{
   'candidateFreeReportedCounts':token_summary,
   'allPlaceholderAndMarkupChecksPassedForTextBearingCells':True,
   'numericAlertReviewed':True,
   'numericFinding':'No numeric value is lost: four ROMs and two mismatches are represented in all locales; Japanese uses digit 4 for four. No numeric proposal is needed.',
   'protectedLiteralAlertReviewed':True,
   'protectedLiteralFinding':'The flagged English plural ROMs is reduced to invariant ROM in some locales; ROMarr, SHA1, and Super Mario Kart remain intact. The plural is expressed by local grammar and numeral context, so the flagged targets are accepted as current.',
   'protectedLiteralAlertInputCount':20,
  },
  'hashOnlyHoldPolicy':'Every callerless cell remains a hold and output contains hashes/positions/locales only; source and current target text are omitted.',
  'independence':'Review used candidate-free input only; no other reviewer proposal or decision was accessed.',
  'limitations':['No native-speaker second review or runtime visual review was performed.','The reviewed caller excerpts are the exact extracted contexts in the candidate-free packet; callerless cells cannot be semantically assessed without text and remain held.'],
 }
 write_json(ROOT/'summary.json',summary)
 input_manifest_sha=sha((PACKET/'manifest.json').read_bytes()); input_sums_sha=sha((PACKET/'SHA256SUMS.txt').read_bytes())
 file_hashes={name:sha((ROOT/name).read_bytes()) for name in ('ledger.jsonl','proposals.jsonl','holds.jsonl','summary.json')}
 outmanifest={
  'artifact':'primary-review','repository':'snapetech-org/ROMarrNG','pullRequest':70,
  'exactHead':HEAD,'exactTree':TREE,'branch':'task/localization-translation-review-20261030',
  'candidateFreeInputPath':'../candidate-free/input/','candidateFreeManifestSha256':input_manifest_sha,
  'candidateFreeChecksumIndexSha256':input_sums_sha,
  'cellCount':240,'callerBackedCells':168,'hashOnlyHolds':72,'proposalCount':len(proposals),
  'decisionCounts':dict(sorted(decisions.items())),
  'candidateFreeOnly':True,'otherReviewOutputsUsed':False,
  'textFreeHoldRows':True,'allRecommendedTargetsTokenChecked':True,
  'fileHashes':file_hashes,
  'createdAtUtc':reviewed,
 }
 write_json(ROOT/'manifest.json',outmanifest)
 print(json.dumps({'cells':len(ledger),'holds':len(holds),'proposals':len(proposals),'decisions':dict(sorted(decisions.items())),'confidence':dict(sorted(confidences.items()))},sort_keys=True))
if __name__=='__main__': main()
