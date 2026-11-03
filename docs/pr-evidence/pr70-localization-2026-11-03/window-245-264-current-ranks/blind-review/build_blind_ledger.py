from pathlib import Path
import collections, hashlib, json, re
OUT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w245-264-independent-blind-20261103')
INP=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w245-264-candidate-free-20261103/input')
manifest=json.loads((INP/'manifest.json').read_text(encoding='utf-8'))
assert manifest['head']=='e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6'
assert manifest['tree']=='016587d26f04d2920a30878236f1933a57e27901'
assert manifest['candidateFreeInputOnly'] is True and manifest['proposedTranslationsIncluded'] is False
assert manifest['cellCount']==240
packet_sha=hashlib.sha256((INP/'SHA256SUMS.txt').read_bytes()).hexdigest()
def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
cell_lines=[x for x in (INP/'current-target-cells.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
cells=[json.loads(x) for x in cell_lines]
contexts={x['position']:x for x in map(json.loads,(INP/'source-contexts.jsonl').read_text(encoding='utf-8').splitlines())}
hold_rows=[json.loads(x) for x in (INP/'caller-resolution-holds.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
hold_map={(x['position'],x['locale']):x for x in hold_rows}
assert len(cells)==240 and len({(x['position'],x['locale']) for x in cells})==240
assert len(contexts)==20 and len(hold_rows)==72
assert {p for p,_ in hold_map}=={248,249,256,257,258,259}
base={
245:"The current term is an adequate short status label for the local check of whether a game is already present in the user's library; the caller context resolves 'owned' as library ownership, not property rights.",
246:"The target expresses the page-load failure heading and fits the adjacent retry action.",
247:"The target communicates an optional URL field for the patch catalogue; URL is technical field terminology.",
248:"The target accurately states that {path} is absent from the container and tells the user to mount the library volume there or change the setting; the opaque path placeholder is retained.",
249:"The target preserves the distinction between missing {path} and existing {fallback_path}, states that the first-run stored path outranks the environment variable, and points to the setting as the fix.",
250:"The target labels the path-to-path mapping used for the accessible group name and retains {path} as an opaque value.",
251:"The target conveys the onboarding instruction to choose one starting route and return later to add the remaining parts.",
252:"The target conveys the platform-folder mapping label and retains {folder} as an opaque folder name.",
253:"The target labels the platform-folder-names fieldset; the caller context confirms the platform means game systems and the folder names they map to.",
254:"The target conveys the platform browse heading grouped by era.",
255:"The target labels the value as an M3U playlist manifest path; the path itself is deliberately rendered as opaque text.",
256:"The target communicates a plugin-fetch failure and preserves {error_type}; file retrieval/download wording fits the caller's fetch of plugin output.",
257:"The target expresses that plugin output lies outside the staging directory; the source is an internal exception that is not surfaced verbatim.",
258:"The target expresses that the named plugin is disabled and retains {slug}; this diagnostic is opaque in the current UI path.",
259:"The target expresses that the named plugin is not installed, retains {slug} and {detail}, and leaves the dynamic detail opaque in the current UI path.",
260:"The target expresses the Popular discovery shelf/tab label.",
261:"The target expresses the button action to preview the next batch.",
262:"The target expresses the button action to preview safe rename operations.",
263:"The target expresses progress as processed files out of total files checked and preserves both count placeholders.",
264:"The target labels the Project column in the patch-results table.",
}
overrides={
 (247,'de'):('refinement',"The label is understandable, but the separated hybrid 'Patch Katalog URL' is awkward German compound construction for a field label."),
 (247,'es'):('correction',"The noun order leaves URL detached after 'Catálogo de patches'; this does not read naturally as a URL field label."),
 (247,'pt-BR'):('correction',"The noun order leaves URL detached after 'Catálogo de Patch'; this does not read naturally as a field for the patch-catalogue URL."),
 (250,'es'):('correction',"The source identifies one path mapping, while the target says 'rutas' in the plural, changing the number conveyed by this accessible label."),
 (251,'es'):('correction',"The sentence switches from formal 'Seleccione' to informal 'Puedes' without a contextual reason."),
 (251,'pt-BR'):('correction',"The second sentence begins with lowercase 'você' after a full stop; this is an orthographic error in the displayed instruction."),
 (251,'vi'):('correction',"'Mảnh' reads as a physical fragment, which is out of place for returning to an onboarding flow to add more setup choices."),
 (251,'zh-Hans'):('correction',"'零件' means physical/mechanical parts and is misleading in this onboarding instruction; the route metaphor also needs a natural Chinese construction."),
 (251,'zh-Hant'):('correction',"'零件' means physical/mechanical parts and is misleading in this onboarding instruction; the route metaphor also needs a natural Traditional Chinese construction."),
 (253,'de'):('correction',"'Plattformfoldernamen' is an awkward English/German hybrid compound; it is not natural German for the platform-folder-names fieldset."),
 (253,'hi'):('refinement',"'मंच' can mean a stage or platform; the software/game-platform sense would benefit from the product's technical platform terminology."),
 (255,'pt-BR'):('correction',"'Lista de jogos' means a list of games, but the caller labels an M3U playlist file path."),
 (255,'zh-Hans'):('correction',"'游戏名单' means a list/roster of games, but the caller labels an M3U playlist file path."),
 (255,'zh-Hant'):('correction',"'遊戲名單' means a list/roster of games, but the caller labels an M3U playlist file path."),
 (259,'pt-BR'):('correction',"'não é instalado' describes an installation action rather than the plugin's current state of not being installed."),
 (259,'zh-Hant'):('correction',"'不安裝' reads as 'does not install' rather than the plugin's current state of not being installed."),
}
pre=re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')
ledger=[]
for line,row in zip(cell_lines,cells):
 pos,loc=row['position'],row['locale']; ctx=contexts[pos]
 disp,why=overrides.get((pos,loc),('accept-current',base[pos]))
 st=pre.findall(row['source']); tt=pre.findall(row['currentTarget'])
 assert row['head']==manifest['head'] and row['tree']==manifest['tree']
 assert sha(row['source'])==row['sourceSha256'] and sha(row['currentTarget'])==row['currentTargetSha256']
 assert row.get('translationHashEntryMatchesCanonicalJson') is True
 assert collections.Counter(st)==collections.Counter(tt),(pos,loc,st,tt)
 ledger.append({
  'schemaVersion':1,'repository':manifest['repository'],'pullRequest':70,
  'head':manifest['head'],'tree':manifest['tree'],'window':'W245-W264',
  'position':pos,'sourceId':row['sourceId'],'sourceIdSha256':sha(row['sourceId']),
  'source':row['source'],'sourceSha256':row['sourceSha256'],'locale':loc,
  'currentTarget':row['currentTarget'],'currentTargetSha256':row['currentTargetSha256'],
  'currentTargetCanonicalTranslationHash':row['currentTargetCanonicalTranslationHash'],
  'translationHashEntryMatchesCanonicalJson':True,
  'callerResolution':ctx.get('callerResolution'),'callerResolutionReason':ctx.get('callerResolutionReason'),
  'callerPathHold':(pos,loc) in hold_map,'callerPathHoldReason':hold_map.get((pos,loc),{}).get('holdReason'),
  'disposition':disp,'rationale':why,'confidence':'high' if disp=='correction' else 'moderate',
  'sourcePlaceholderSequence':st,'currentTargetPlaceholderSequence':tt,
  'placeholderTokenMultisetMatches':True,'placeholderOrderChanged':st!=tt,
  'proposedTarget':None,'candidateProposalSeen':False,
  'reviewerType':'independent blind semantic review; machine-assisted; not qualified native-speaker approval',
  'qualifiedLocaleReviewRequired':True,'releaseApprovedByThisReview':False,
 })
counts=collections.Counter(x['disposition'] for x in ledger)
assert len(ledger)==240 and counts=={'accept-current':224,'correction':14,'refinement':2},counts
assert sum(x['callerPathHold'] for x in ledger)==72
assert all(x['proposedTarget'] is None and not x['candidateProposalSeen'] for x in ledger)
order_changed=sum(x['placeholderOrderChanged'] for x in ledger)
assert order_changed==4
lp=OUT/'blind-ledger.jsonl'; lp.write_text(''.join(canon(x)+'\n' for x in ledger),encoding='utf-8')
summary={
 'schemaVersion':1,'repository':manifest['repository'],'pullRequest':70,'head':manifest['head'],'tree':manifest['tree'],'window':'W245-W264',
 'candidateFreeInputChecksumFileSha256':packet_sha,'cellCount':240,'sourceCount':20,'localeCount':12,
 'semanticDispositions':dict(sorted(counts.items())),
 'callerPathHoldCells':72,'callerPathHoldPositions':[248,249,256,257,258,259],
 'callerPathHoldsDoNotEqualSemanticHolds':True,'semanticHoldCount':0,
 'placeholderTokenMultisetMismatchCount':0,'placeholderOrderChangedCount':order_changed,
 'candidateProposalsIncluded':False,'candidateProposalSeen':False,
 'qualifiedNativeSpeakerApproval':False,'releaseApproved':False,
 'method':'Independent blind assessment of current catalog values against the candidate-free pinned source/caller/runtime packet; no primary ledger or candidate target was read.'
}
sp=OUT/'summary.json'; sp.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
seal={
 'schemaVersion':1,'repository':manifest['repository'],'pullRequest':70,'head':manifest['head'],'tree':manifest['tree'],'window':'W245-W264',
 'candidateFreeInputChecksumFileSha256':packet_sha,'blindLedgerSha256':hashlib.sha256(lp.read_bytes()).hexdigest(),
 'summarySha256':hashlib.sha256(sp.read_bytes()).hexdigest(),'cellCount':240,
 'candidateProposalsIncluded':False,'nativeSpeakerApproval':False,'releaseApproved':False
}
(OUT/'blind-seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'README.md').write_text(f'''# ROMarrNG PR #70 W245–W264 independent blind semantic review\n\nThis review is pinned to PR head `{manifest['head']}` / tree `{manifest['tree']}` and the candidate-free input packet whose `SHA256SUMS.txt` hash is `{packet_sha}`. It covers all 240 current cells: 20 source IDs × 12 direct locales.\n\nThe reviewer inspected only the candidate-free input and current targets, not the primary ledger or proposed candidates. It records **224 accept-current, 14 correction findings, and 2 refinement findings**. The 72 caller-path holds at positions 248–249 and 256–259 are recorded separately and were not converted into translation holds. Placeholder-token multisets match in all 240 cells; four target-language strings reorder the two placeholders, which is acceptable for the target-language sentence structure.\n\n`blind-ledger.jsonl` contains each source/target pair, its exact pinned hashes, semantic disposition, rationale, caller-path status, and placeholder check. It deliberately contains no replacement translations. `summary.json` and `blind-seal.json` record counts and packet lineage.\n\nThis is machine-assisted review, not qualified native-speaker approval; it does not approve a release.\n''',encoding='utf-8')
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
