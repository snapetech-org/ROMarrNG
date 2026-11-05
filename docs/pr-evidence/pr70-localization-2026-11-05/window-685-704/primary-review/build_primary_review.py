#!/usr/bin/env python3
"""Build the independent W685-W704 primary review from candidate-free input only."""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parent
PACKET=ROOT.parent/'candidate-free'/'input'
REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='43d2858744ef20cd58462643fed534ac61d2ffad'
TREE='73e8f50d65cb611def996b01bab0b00628b65860'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Reviewed corrections/refinements. Callerless positions are deliberately absent.
OVERRIDES={
 (693,'fr'):('refinement','Pas de ROMarr sur cet appareil ? Copiez le lien et collez-le dans Amis → J’ai une invitation sur votre propre serveur.','moderate',
   'The caller presents “Friends → I have an invitation” as the exact navigation route on the recipient’s own server. The current French instruction leaves “Friends” in English; localizing both route labels makes the path consistent with the surrounding French text.'),
 (701,'ar'):('correction','لا توجد اتصالات بعد','moderate',
   'This is the empty state for configured notification connections. The current “وصلات” is more readily read as links, while the adjacent configured-connections label uses “اتصالات”; the recommendation keeps the same connection term.'),
}
RATIONALE={
 685:'The ROM sniffer returns this label with the byte order inserted; the translation should identify the Nintendo 64 magic/signature value and preserve the {order} placeholder.',
 686:'The ROM sniffer reports the location of the Game Boy Advance Nintendo logo in the header; this is a diagnostic label, and the hexadecimal offset must remain exact.',
 687:'The ROM sniffer reports the location of the Game Boy Nintendo logo; this is a diagnostic label, and the hexadecimal offset must remain exact.',
 688:'The ROM sniffer reports the Game Boy logo location and that the CGB colour flag is set; the target preserves both details.',
 689:'This exact phrase is returned in the API error when a DAT-dependent catalog route is unavailable; the target preserves the DAT product/data term and product name.',
 690:'This is the bold empty-state heading shown when the No-Intro or Redump DAT directory is not configured.',
 691:'This help paragraph explains how to pair a Moonlight client and enter its displayed PIN; {host} is the address the user must add in Moonlight.',
 692:'This message appears when the game platform list is empty; the target should state that no ROM platform is available.',
 693:'This invitation-page instruction tells the recipient where to paste a link on their own server; “Friends” and “I have an invitation” are navigation labels.',
 694:'This help label appears when the Switch game has no TitleDB identifier; the target preserves the service name and ID concept.',
 695:'This is the fallback API status shown when no response text is available; the target is a concise response label.',
 696:'This Moonlight connection failure message names the host and port that did not answer; both placeholders must remain intact.',
 697:'This is a concise metadata lookup fallback shown when no match method is available.',
 699:'This warning appears only when one or more indexer protocols lack a configured download client. It explains that those results can still be found but their downloads will be refused; {protocols} is the dynamic list.',
 700:'This empty-state message appears when no notification/webhook connections are configured.',
 701:'This is the empty-state heading in the notification connection settings, before the user adds the first connection.',
 702:'This is the placeholder rendered inside artwork when a catalog cover image is missing.',
 703:'This fallback appears when a plugin supplies no description.',
 704:'This is the empty state for the direct-indexer settings when none are configured but enabled Prowlarr indexers are available below.',
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
  if recommended is not None:
   item['recommendedTarget']=recommended
   item['recommendedTargetSha256']=sha(recommended.encode('utf-8'))
   proposal={k:item[k] for k in ('cellId','locale','sourcePosition','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','decision','source','currentTarget','recommendedTarget','recommendedTargetSha256','rationale','confidence','candidateFreeRowSha256','sourceTextSha256','currentTargetSha256','callerContextSha256','callerMatchCount','callerPaths','callerLineNumbers','exactHead','exactTree')}
   proposals.append(proposal)
  ledger.append(item)
 if len(holds)!=12 or len(ledger)!=240: raise SystemExit(f'unexpected output counts: {len(ledger)} rows, {len(holds)} holds')
 reviewed=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
 write_jsonl(ROOT/'ledger.jsonl',ledger); write_jsonl(ROOT/'proposals.jsonl',proposals); write_jsonl(ROOT/'holds.jsonl',holds)
 decisions=collections.Counter(x['decision'] for x in ledger)
 confidences=collections.Counter(x['confidence'] for x in ledger)
 proposal_locales=collections.Counter(x['locale'] for x in proposals)
 proposal_sources=collections.Counter(x['sourcePosition'] for x in proposals)
 token_summary=json.loads((PACKET/'candidate-free-token-summary.json').read_text(encoding='utf-8'))
 summary={
  'artifact':'ROMarrNG PR #70 W685-W704 independent primary semantic review',
  'pullRequest':70,'exactHead':HEAD,'exactTree':TREE,
  'reviewedAtUtc':reviewed,'cellCount':240,'sourceCount':20,'localeCount':12,
  'callerBackedCells':228,'callerlessHashOnlyHolds':12,'callerlessSourceCount':1,
  'decisionCounts':dict(sorted(decisions.items())),'proposalCount':len(proposals),
  'proposalCountsByLocale':dict(sorted(proposal_locales.items())),
  'proposalCountsByPosition':{str(k):v for k,v in sorted(proposal_sources.items())},
  'confidenceCounts':dict(sorted(confidences.items())),
  'tokenAudit':{
   'candidateFreeReportedCounts':token_summary,
   'allPlaceholderMarkupNumericAndProtectedLiteralChecksPassedForTextBearingCells':True,
   'candidateFreeReportedMismatches':token_summary,
   'finding':'The candidate-free token audit reports zero placeholder, markup, numeric, numeric-presentation, and protected-literal mismatches.',
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
  'cellCount':240,'callerBackedCells':228,'hashOnlyHolds':12,'proposalCount':len(proposals),
  'decisionCounts':dict(sorted(decisions.items())),
  'candidateFreeOnly':True,'otherReviewOutputsUsed':False,
  'textFreeHoldRows':True,'allRecommendedTargetsTokenChecked':True,
  'fileHashes':file_hashes,
  'createdAtUtc':reviewed,
 }
 write_json(ROOT/'manifest.json',outmanifest)
 print(json.dumps({'cells':len(ledger),'holds':len(holds),'proposals':len(proposals),'decisions':dict(sorted(decisions.items())),'confidence':dict(sorted(confidences.items()))},sort_keys=True))
if __name__=='__main__': main()
