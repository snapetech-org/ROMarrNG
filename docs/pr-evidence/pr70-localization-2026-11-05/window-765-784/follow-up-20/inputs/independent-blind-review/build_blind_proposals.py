#!/usr/bin/env python3
"""Build source-only blind proposals for ROMarrNG PR #70 W765-W784."""
import collections, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
INPUT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/candidate-free/input')
OUT=Path(__file__).resolve().parent
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED_HEAD='9714d7cf69c687685b4f65cbd9627a56830bab85'
EXPECTED_TREE='c8eb66573f10b2390a02df05033f5133425d5e41'
PLACEHOLDER=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']
MANUAL_LITERALS={
 'ui.one-title-per-line-comments-ranking.8c54c86102':['# comments','Title\u00a0→tab←\u00a0platform'],
 'ui.openxbl-api-key.90ea47aa7f':['OpenXBL','API'],
 'ui.optional-apprise-urls-to-notify-one.8ef42d4f02':['Apprise','URLs']
}
MEANINGS={
 'ui.on-this-day.d011904834':'Anniversary tab for games associated with this calendar day.',
 'ui.on-this-install.ca75d54e64':'Heading for routes available on the currently running installation.',
 'ui.one-game-one-rom.3372b0856c':'Checkbox label for a one-game/one-ROM rule in a collection workflow.',
 'ui.one-other-dump.6710e50b16':'Singular disclosure summary for one additional ROM dump among discarded alternatives.',
 'ui.one-title-per-line-comments-ranking.8c54c86102':'Help explaining the accepted multiline title-list syntax, comments, ranking numbers, and tab-separated title/platform form.',
 'ui.only-dat-verified-dumps.a372d56f1d':'Peer visibility scope that includes only dumps verified by DAT.',
 'ui.only-selected-regions.e257690d2c':'Strict region allowlist; a title is omitted if no dump matches a selected region.',
 'ui.only-the-platforms-i-name.a25a55c6dd':'Peer scope limited to the platforms explicitly selected by the user.',
 'ui.open-navigation.0ed77fd261':'Accessible name for the control that opens the navigation rail.',
 'ui.open-on-the-indexer.4766c56d0d':'Tooltip/accessible label for opening a release on its indexer.',
 'ui.open-on-indexer.202e1ad5f5':'Parameterized tooltip/accessible label naming the indexer.',
 'ui.open-the-submission.4a863bf1dd':'Link to open a submission for the user to review and post.',
 'ui.open-this-invitation-on-my-romarr.b76952fe51':'Button on the invitation landing page to open the invitation on the user’s own ROMarr.',
 'ui.openxbl-api-key.90ea47aa7f':'Label for the OpenXBL API credential field.',
 'ui.optional-connections-to-the-rest-of.636208f858':'General-settings description of optional integrations and the secret-handling boundary.',
 'ui.optional-follow-ups.e3fee9a99c':'Card heading for additional optional actions after core search/grab/file steps.',
 'ui.optional-message-priority.dbcf318711':'Notification webhook field help stating that message priority is optional.',
 'ui.optional-apprise-urls-to-notify-one.8ef42d4f02':'Notification field help for optional Apprise destination URLs and accepted list separators.'
}
def sha(b): return hashlib.sha256(b).hexdigest()
def j(path): return json.loads(path.read_text(encoding='utf-8'))
def jl(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def protected(s):
 found=[]
 for lit in PROTECTED:
  ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
  if ok: found.append(lit)
 return sorted(set(found))
def tokens(s):
 return {'placeholders':PLACEHOLDER.findall(s),'markup':TAG.findall(s),'numbers':NUMBER.findall(s),'protectedLiterals':protected(s)}
def main():
 manifest=j(INPUT/'manifest.json'); selection=j(INPUT/'selection.json')
 if (manifest.get('head'),manifest.get('tree'),manifest.get('window'))!=(EXPECTED_HEAD,EXPECTED_TREE,'W765-W784'): raise SystemExit('candidate-free exact pin mismatch')
 if selection.get('localeOrder')!=LOCALES or selection.get('positions')!=[765,784]: raise SystemExit('selection pin/order mismatch')
 before=j(INPUT/'PR-attestation-before.json'); after=j(INPUT/'PR-attestation-after.json')
 for att in (before,after):
  if (att.get('head'),att.get('tree'),att.get('pullRequest'),att.get('repository'))!=(EXPECTED_HEAD,EXPECTED_TREE,70,'snapetech-org/ROMarrNG'): raise SystemExit('PR attestation pin mismatch')
 selected=jl(INPUT/'selected-sources.jsonl'); contexts=jl(INPUT/'source-contexts.jsonl'); matrix=j(OUT/'independent-translation-matrix.json')
 if matrix.get('locales')!=LOCALES: raise SystemExit('proposal locale order mismatch')
 sby={r['sourceId']:r for r in selected}; cby={r['sourceId']:r for r in contexts}; mby={r['sourceId']:r for r in matrix['proposals']}
 callerbacked=[r for r in selected if not r.get('sourceTextOmitted')]
 callerless=[r for r in selected if r.get('sourceTextOmitted')]
 if len(selected)!=20 or len(callerbacked)!=18 or len(callerless)!=2 or len(mby)!=18: raise SystemExit('source/callerless coverage mismatch')
 rows=[]; source_rows=[]
 for src in callerbacked:
  sid=src['sourceId']; ctx=cby[sid]; item=mby[sid]
  if ctx['callerless'] or item['sourceId']!=sid or len(ctx['callers'])<1: raise SystemExit('caller/source mapping failure '+sid)
  if src['source']!=ctx['source'] or src['sourceSha256']!=ctx['sourceSha256'] or len(item['targets'])!=12: raise SystemExit('source text/hash mismatch '+sid)
  source_sig=tokens(src['source']); manual=MANUAL_LITERALS.get(sid,[])
  for locale,target in zip(LOCALES,item['targets']):
   target_sig=tokens(target)
   ok=(source_sig['placeholders']==target_sig['placeholders'] and source_sig['markup']==target_sig['markup'] and source_sig['numbers']==target_sig['numbers'] and all(x in target_sig['protectedLiterals'] for x in source_sig['protectedLiterals']) and all(x in target for x in manual))
   if not ok: raise SystemExit(f'token/literal preservation failure {sid}/{locale}: {source_sig} => {target_sig}, manual={manual}')
   refs=[{'path':c['path'],'line':c['line'],'lineText':c['lineText'],'lineSha256':c['lineSha256'],'excerptSha256':c['excerptSha256'],'fileSha256':c['fileSha256'],'gitBlob':c['gitBlob'],'matchKind':c['matchKind']} for c in ctx['callers']]
   rows.append({'position':src['position'],'catalogZeroBasedIndex':src['catalogZeroBasedIndex'],'catalogOneBasedPosition':src['catalogOneBasedPosition'],'sourceId':sid,'source':src['source'],'sourceSha256':src['sourceSha256'],'sourceContextSha256':ctx['contextSha256'],'locale':locale,'proposal':target,'proposalSha256':sha(target.encode()),'disposition':'blind_proposal','callerCount':len(ctx['callers']),'callerReferences':refs,'sourceTokenSignature':source_sig,'proposalTokenSignature':target_sig,'manualProtectedLiteralsRequired':manual,'tokensPreserved':True,'semanticMeaning':MEANINGS[sid],'reviewBasis':'pinned source and caller context only; current locale target not consulted','nativeSpeakerApproval':False})
  source_rows.append({'position':src['position'],'catalogZeroBasedIndex':src['catalogZeroBasedIndex'],'catalogOneBasedPosition':src['catalogOneBasedPosition'],'sourceId':sid,'source':src['source'],'sourceSha256':src['sourceSha256'],'sourceContextSha256':ctx['contextSha256'],'callerCount':len(ctx['callers']),'callers':refs,'semanticMeaning':MEANINGS[sid],'sourceTokenSignature':source_sig,'manualProtectedLiteralsRequired':manual})
 rows.sort(key=lambda r:(r['position'],LOCALES.index(r['locale'])))
 if len(rows)!=216 or sum(r['callerCount'] for r in source_rows)!=23: raise SystemExit('cell or caller reference count mismatch')
 (OUT/'blind-locale-review.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
 (OUT/'source-review.json').write_text(json.dumps({'artifact':'ROMarrNG PR #70 W765-W784 independent blind source/context review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'window':'W765-W784','sourceCount':18,'callerReferenceCount':23,'localeCount':12,'cellProposalCount':216,'callerlessSourceCount':2,'candidateFreeManifestSha256':sha((INPUT/'manifest.json').read_bytes()),'candidateFreeInputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'independentProposalMatrixSha256':sha((OUT/'independent-translation-matrix.json').read_bytes()),'currentTargetsConsulted':False,'primaryCrossRootConsulted':False,'changedWorktreeConsulted':False,'reviewConfidence':'moderate','nativeSpeakerApproval':False,'sources':source_rows},ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 proposal_sha=sha((OUT/'blind-locale-review.jsonl').read_bytes())
 (OUT/'proposal-freeze.json').write_text(json.dumps({'artifact':'ROMarrNG PR #70 W765-W784 blind proposal freeze','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'window':'W765-W784','proposalRows':216,'proposalSha256':proposal_sha,'matrixSha256':sha((OUT/'independent-translation-matrix.json').read_bytes()),'sourceContextsSha256':sha((INPUT/'source-contexts.jsonl').read_bytes()),'selectedSourcesSha256':sha((INPUT/'selected-sources.jsonl').read_bytes()),'frozenBeforeCurrentCellHashesOpened':True,'currentTargetTextsConsulted':False,'createdAtUtc':datetime.now(timezone.utc).isoformat()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'result':'PROPOSALS_FROZEN','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'sourceCount':18,'callerReferences':23,'proposalCells':len(rows),'callerlessSources':len(callerless),'proposalSha256':proposal_sha,'matrixSha256':sha((OUT/'independent-translation-matrix.json').read_bytes()),'currentTargetsConsulted':False},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
