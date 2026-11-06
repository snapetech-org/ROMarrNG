import collections, hashlib, json, re
from pathlib import Path

ROOT=Path('/mnt/disks/scratch/task-scratch')
OUT=ROOT/'romarrng-pr70-w226-245-primary-20261103'
INPUT=ROOT/'romarrng-pr70-w226-245-candidate-free-20261103'/'input'
HEAD='1ab8fd8b171afbfe43cd6998cde920f9f9b12b0c'
TREE='c65a2206c95cd13b3eca5174aca2e4c812eff8bc'
REPO='snapetech-org/ROMarrNG'
PR=70
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROTECTED=['ROMarr','TitleDB','No-Intro','Redump','DAT']

# Candidate recommendations are limited to clear semantic, grammar, or untranslated-value issues.
CANDIDATES={
 (227,'ar'):('refinement','لا يوجد معرّف في TitleDB','The current wording repeats the abbreviation as “ID identifier.” This shorter Arabic phrase keeps the TitleDB label and conveys that no identifier is available.','moderate'),
 (227,'vi'):('correction','Không có ID TitleDB','The current phrase omits the Vietnamese negative/existential wording and reads as an incomplete noun phrase. This states that the TitleDB ID is absent.','moderate'),
 (228,'ja'):('correction','これらのフィルターに一致するタイトルはありません。','The current wording is an awkward negative construction (“titles do not match these filters”). The proposal is the natural empty-state message that no titles match the selected filters.','moderate'),
 (228,'zh-Hans'):('refinement','没有符合这些筛选条件的标题。','The current wording is understandable, but “筛选条件” is the natural UI term for filter criteria and the proposed order reads more naturally for an empty state.','moderate'),
 (228,'zh-Hant'):('refinement','沒有符合這些篩選條件的標題。','The current wording is understandable, but “篩選條件” is the natural UI term for filter criteria and the proposed order reads more naturally for an empty state.','moderate'),
 (231,'ar'):('correction','غير موجود في المكتبة','The current Arabic “لا في المكتبة” is not a grammatical status label. The proposal says that the game is not present in the library.','moderate'),
 (231,'id'):('refinement','Tidak ada di pustaka','The current “perpustakaan” can suggest a physical library. “Pustaka” is a concise software-catalog term for the game library in this table status.','low'),
 (231,'vi'):('correction','Không có trong thư viện','The current “Không phải trong thư viện” is an awkward copular construction for a presence status. The proposal states that it is absent from the library.','moderate'),
 (233,'de'):('refinement','Nichts wurde abgeschlossen','The current “Nichts ist fertig” can mean that nothing is ready. The proposal more directly expresses that no task finished.','moderate'),
 (233,'pt-BR'):('refinement','Nada foi concluído','“Nada acabou” can mean that nothing ended. The proposal makes the task-result meaning, that nothing was completed, explicit.','moderate'),
 (233,'vi'):('refinement','Không có gì được hoàn tất','The current wording can read as “nothing ended.” The proposal more clearly expresses the task-result meaning that nothing was completed.','low'),
 (233,'zh-Hant'):('refinement','沒有任何項目完成','The current “沒甚麼結束” reads as “nothing much ended.” The proposal clearly states that no item completed.','moderate'),
 (236,'ar'):('correction','أقدم من أحدث إصدار مُدرج','The current phrase has an awkward definite article sequence. This is a natural comparison label for a version older than the latest listed version.','moderate'),
 (236,'id'):('refinement','Lebih lama dari versi terbaru yang tercantum','The current wording omits that the comparison is against the latest listed version. This keeps the status concise while preserving “listed.”','moderate'),
 (236,'pt-BR'):('correction','Anterior à versão mais recente listada','“Mais velho” is masculine and does not agree with the feminine noun “versão.” This avoids the agreement error and retains “listed.”','moderate'),
 (238,'ja'):('refinement','この日','The current target adds a trailing Japanese comma although the English tab label has no trailing punctuation.','moderate'),
 (238,'zh-Hans'):('refinement','这一天','The current target adds a trailing comma although the English tab label has no trailing punctuation.','moderate'),
 (238,'zh-Hant'):('refinement','這一天','The current target adds a trailing comma although the English tab label has no trailing punctuation.','moderate'),
 (241,'ja'):('correction','、または No-Intro / Redump DAT を読み込む場合は','The exact caller concatenates this fragment between the Metadata and Collections links. The current wording says “please open” and adds a sentence break; the proposal better expresses the alternative of loading the DATs. Caller-fragment ordering limits confidence.','low'),
 (241,'ko'):('correction','또는 No-Intro / Redump DAT를 불러오는 경우','The exact caller concatenates this fragment before the Collections link. The current wording says “open” rather than load and does not form a clear alternative. Caller-fragment ordering limits confidence.','low'),
}
# Every locale shares the same Spanish text at position 234; replace it with a localized title-match status.
WANTED={
 'ar':('لا توجد عناوين مطلوبة لمطابقتها','moderate'),
 'de':('Keine gewünschten Titel zum Abgleichen','moderate'),
 'es':('No hay títulos solicitados que comparar','moderate'),
 'fr':('Aucun titre demandé à faire correspondre','moderate'),
 'hi':('मिलान करने के लिए कोई वांछित गेम नहीं है','moderate'),
 'id':('Tidak ada judul yang diminta untuk dicocokkan','moderate'),
 'ja':('照合する希望タイトルがありません','moderate'),
 'ko':('매칭할 요청 게임이 없습니다','moderate'),
 'pt-BR':('Não há títulos solicitados para comparar','moderate'),
 'vi':('Không có tựa game nào được yêu cầu để đối chiếu','moderate'),
 'zh-Hans':('没有待匹配的心愿游戏','low'),
 'zh-Hant':('沒有待比對的心願遊戲','low'),
}


def sha(b): return hashlib.sha256(b).hexdigest()
def jload(path): return json.loads(path.read_text(encoding='utf-8'))
def jl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]
def dump(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dumpjl(path,rows): path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def tokens(s): return re.findall(r'\{[^{}]+\}',s)
def tags(s): return re.findall(r'<[^>]+>',s)
def numbers(s): return re.findall(r'(?<![\w])\d+(?:[.,:/-]\d+)*(?!\w)',s)
def edge(s): return [len(s)-len(s.lstrip()),len(s)-len(s.rstrip())]
def checksum_file(directory, filename):
    result={}
    for line in (directory/filename).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,name=line.split(None,1); name=name.lstrip('* ')
        actual=sha((directory/name).read_bytes())
        result[name]={'expected':expected,'actual':actual,'matches':expected==actual}
    return result

checksums=checksum_file(INPUT,'SHA256SUMS.txt')
assert len(checksums)==13 and all(v['matches'] for v in checksums.values())
manifest=jload(INPUT/'manifest.json')
attestation=jload(INPUT/'PR-attestation.json')
final_live=jload(INPUT/'final-live-pr-verification.json')
scan=jload(INPUT/'caller-scan-attestation.json')
assert manifest['candidateFreeInputOnly'] and not manifest['proposedTranslationsIncluded'] and not manifest['reviewDecisionsIncluded']
assert manifest['head']==HEAD and manifest['tree']==TREE
assert attestation['headRefOid']==HEAD and attestation['localWorktreeHead']==HEAD and attestation['localWorktreeTree']==TREE
assert final_live['head']==HEAD and final_live['tree']==TREE
assert scan['head']==HEAD and scan['tree']==TREE
assert attestation['pullRequest']==PR and attestation['repository']==REPO and attestation['state']=='OPEN' and attestation['draft']
assert final_live['verificationPassed'] and final_live['head']==HEAD and final_live['tree']==TREE
assert scan['allExactCallRefsIncluded'] and scan['resolvedProductionCallerReferences']==25

cells=jl(INPUT/'current-target-cells.jsonl')
sources=jl(INPUT/'source-contexts.jsonl')
holds=jl(INPUT/'caller-resolution-holds.jsonl')
reconciliations=jl(INPUT/'caller-location-reconciliation.jsonl')
boundary=jl(INPUT/'selection-boundary.jsonl')
assert len(cells)==240 and len(sources)==20 and len(holds)==48
assert len(boundary)==22
by_source={s['position']:s for s in sources}
by_cell={(c['position'],c['locale']):c for c in cells}
hold_by_cell={(h['position'],h['locale']):h for h in holds}
assert len(by_cell)==240 and set(by_source)==set(range(226,246))
assert {p:sum(1 for h in holds if h['position']==p) for p in [226,232,237,242]}=={226:12,232:12,237:12,242:12}
assert set(hold_by_cell)=={k for k in by_cell if k[0] in (226,232,237,242)}
assert {r['position'] for r in reconciliations}=={229,239}

# Revalidate source/current hashes and packet caller pins.
identity_issues=[]
caller_refs=0
for key,c in by_cell.items():
    s=by_source[key[0]]
    if (c['source']!=s['source'] or c['sourceId']!=s['sourceId'] or c['sourceSha256']!=s['sourceSha256']):
        identity_issues.append({'key':key,'issue':'source identity differs from source context'})
    if sha(c['source'].encode())!=c['sourceSha256'] or sha(c['currentTarget'].encode())!=c['currentTargetSha256']:
        identity_issues.append({'key':key,'issue':'source/current hash recomputation failed'})
    if c['locale'] not in LOCALES or c['head']!=HEAD or c['tree']!=TREE or c['pullRequest']!=PR:
        identity_issues.append({'key':key,'issue':'locale or pin mismatch'})
    caller_refs += s['callerReferenceCount'] if key[1]==LOCALES[0] else 0
assert not identity_issues, identity_issues[:3]
assert caller_refs==25

# Check the stale position-239 index pointer against its exact reconciliation and active caller.
r239=next(r for r in reconciliations if r['position']==239)
active239=r239['resolvedCurrentCallsites'][0]
assert active239['path']=='romarr/ui.py' and active239['startLine']==4444 and active239['endLine']==4447
assert r239['sourceIndexLocations']==['romarr/ui.py:4208']

review=[]
for key in sorted(by_cell,key=lambda k:(k[0],LOCALES.index(k[1]))):
    pos,locale=key
    c=by_cell[key]; s=by_source[pos]
    caller_summary=[{'path':r['path'],'startLine':r['startLine'],'endLine':r['endLine'],'contextSha256':r['contextSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob'],'matchBasis':r['matchBasis']} for r in s.get('references',[])]
    if pos in (226,232,237,242):
        h=hold_by_cell[key]
        assert h['currentTarget']==c['currentTarget'] and h['sourceSha256']==c['sourceSha256'] and h['candidateTarget'] is None
        decision='hold'; candidate=None; selected=None; rationale=h['holdReason']; confidence='low'
    elif pos==234:
        decision='correction'; candidate,confidence=WANTED[locale]
        selected=candidate
        rationale='The current value is the same Spanish phrase (“No hay juegos solicitados que comparar”) in every locale. It does not translate the source “nothing wanted, nothing to match”; the candidate states that no wanted/requested game titles are available to match.'
    elif key in CANDIDATES:
        decision,candidate,rationale,confidence=CANDIDATES[key]
        selected=candidate
    else:
        decision='accept-current'; candidate=None; selected=c['currentTarget']; confidence='moderate'
        rationale=f"The current target conveys the source meaning for the pinned {s['category']} context. No material omission, reversal, caller mismatch, or structural token issue was found."
    checked=selected if selected is not None else c['currentTarget']
    source_literals=[lit for lit in PROTECTED if lit in c['source']]
    structural={
       'placeholders':{'source':tokens(c['source']),'current':tokens(c['currentTarget']),'checkedTarget':tokens(checked),'matchesSource':tokens(c['source'])==tokens(checked)},
       'markupTags':{'source':tags(c['source']),'current':tags(c['currentTarget']),'checkedTarget':tags(checked),'matchesSource':tags(c['source'])==tags(checked)},
       'numericTokens':{'source':numbers(c['source']),'current':numbers(c['currentTarget']),'checkedTarget':numbers(checked),'matchesSource':numbers(c['source'])==numbers(checked)},
       'edgeWhitespace':{'source':edge(c['source']),'current':edge(c['currentTarget']),'checkedTarget':edge(checked),'matchesSource':edge(c['source'])==edge(checked)},
       'protectedLiterals':[{'literal':lit,'preserved':lit in checked,'presentInCurrent':lit in c['currentTarget']} for lit in source_literals]
    }
    assert all(structural[k]['matchesSource'] for k in ('placeholders','markupTags','numericTokens','edgeWhitespace')),(key,structural)
    assert all(x['preserved'] for x in structural['protectedLiterals']),(key,structural['protectedLiterals'])
    row={
      'schemaVersion':1,'reviewId':f'W226-rank-{pos}-{locale}','repository':REPO,'pullRequest':PR,
      'head':HEAD,'tree':TREE,'window':'W226–W245','position':pos,'locale':locale,
      'sourceId':c['sourceId'],'source':c['source'],'sourceSha256':c['sourceSha256'],'category':s['category'],
      'catalogPath':c['catalogPath'],'catalogSha256':c['catalogSha256'],'catalogGitBlob':c['catalogGitBlob'],
      'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
      'callerReferenceCount':s['callerReferenceCount'],'callerLocations':s['locations'],'pinnedCallers':caller_summary,
      'callerResolutionHold':hold_by_cell[key]['holdReason'] if key in hold_by_cell else None,
      'decision':decision,'candidateTarget':candidate,'candidateTargetSha256':sha(candidate.encode()) if candidate is not None else None,
      'selectedTarget':selected,'selectedTargetSha256':sha(selected.encode()) if selected is not None else None,
      'rationale':rationale,'confidence':confidence,'nativeSpeakerApproved':False,
      'integrityChecks':structural
    }
    if pos==239:
        row['callerLocationReconciliation']={'sourceIndexLocationStale':r239['sourceIndexLocations'][0],'activePath':active239['path'],'activeStartLine':active239['startLine'],'activeEndLine':active239['endLine'],'activeContextSha256':active239['contextSha256'],'finding':'The source-index location is stale; review uses the active settings help literal at romarr/ui.py:4444–4447.'}
    review.append(row)

assert len(review)==240
counts=collections.Counter(r['decision'] for r in review)
assert counts['hold']==48 and counts['correction']+counts['refinement']==32 and counts['accept-current']==160

# Save explicit hold evidence, including all 48 locale cells.
hold_rows=[r for r in review if r['decision']=='hold']
dumpjl(OUT/'holds.jsonl',[{'position':r['position'],'locale':r['locale'],'sourceId':r['sourceId'],'currentTarget':r['currentTarget'],'holdReason':r['callerResolutionHold'],'callerLocations':r['callerLocations'],'candidateTarget':None} for r in hold_rows])
dumpjl(OUT/'primary-decisions.jsonl',review)

# Detailed input integrity and live pin record; live state independently rechecked with gh and ls-remote.
input_verification={
 'candidateFreePacket':{'directory':str(INPUT),'checksumFile':'SHA256SUMS.txt','checksumFileSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'files':checksums,'allChecksumsPass':all(v['matches'] for v in checksums.values())},
 'manifestSha256':sha((INPUT/'manifest.json').read_bytes()),
 'sourceAndCurrentPins':{'sourceRows':20,'cellRows':240,'localeOrder':LOCALES,'sourceHashesRecomputed':True,'currentTargetHashesRecomputed':True,'allRowsAtExpectedHeadTree':True,'productionCallerReferences':caller_refs,'holdCells':48,'holdPositions':[226,232,237,242]},
 'position239':{'staleSourceIndexLocation':r239['sourceIndexLocations'][0],'activeCaller':{'path':active239['path'],'startLine':active239['startLine'],'endLine':active239['endLine'],'contextSha256':active239['contextSha256']},'reconciliationVerified':True},
 'livePin':{'repository':REPO,'pullRequest':PR,'state':'OPEN','isDraft':True,'branch':BRANCH,'head':HEAD,'tree':TREE,'remoteBranchHead':HEAD,'pullRefHead':HEAD,'matchesExpected':True}
}
dump(OUT/'input-verification.json',input_verification)

live={'repository':REPO,'pullRequest':PR,'url':'https://github.com/snapetech-org/ROMarrNG/pull/70','state':'OPEN','isDraft':True,'baseRefName':'main','headRefName':BRANCH,'headRefOid':HEAD,'headTree':TREE,'remoteBranchHead':HEAD,'pullRefHead':HEAD,'verifiedAt':'2026-11-03','verification':'gh pr view, gh API commit tree, git ls-remote branch and refs/pull/70/head','matchesExpected':True}
dump(OUT/'live-pr-verification.json',live)

summary={
 'artifact':'ROMarrNG PR #70 W226–W245 primary semantic localization review','repository':REPO,'pullRequest':PR,'branch':BRANCH,'head':HEAD,'tree':TREE,'state':'OPEN','isDraft':True,
 'window':'W226–W245','reviewedCells':240,'sourceCount':20,'localeCount':12,'productionCallerReferences':25,
 'decisionCounts':dict(counts),'holdsByPosition':{str(p):sum(r['position']==p for r in hold_rows) for p in (226,232,237,242)},
 'recommendedCellsByPosition':{str(p):sum(r['position']==p and r['decision'] in ('correction','refinement') for r in review) for p in sorted({r['position'] for r in review if r['decision'] in ('correction','refinement')})},
 'recommendedCellsByLocale':{l:sum(r['locale']==l and r['decision'] in ('correction','refinement') for r in review) for l in LOCALES},
 'structuralChecks':{'cellsChecked':240,'placeholderMismatches':0,'markupMismatches':0,'numericTokenMismatches':0,'edgeWhitespaceMismatches':0,'protectedLiteralChecks':sum(len(r['integrityChecks']['protectedLiterals']) for r in review),'protectedLiteralMismatches':0},
 'position234Finding':'All 12 current values are identical to the Spanish string “No hay juegos solicitados que comparar”; localized replacement proposals are included for every locale.',
 'position239Finding':'The packet’s source-index line 4208 is stale. The active caller is verified at romarr/ui.py:4444–4447 and was used for semantic review.',
 'callerHolds':'Positions 226, 232, 237, and 242 remain held in all 12 locales for the exact caller-path reasons recorded in the packet.',
 'nativeSpeakerApproval':False,'repositoryOrPREdited':False,'testsBuildsScansCIWorkflowsBrowserMergeReleaseOrTagActions':False,
 'reviewLimit':'Machine-assisted semantic review against pinned source and callers; not native-speaker approval.'
}
dump(OUT/'summary.json',summary)

readme='''# ROMarrNG PR #70 W226–W245 primary review\n\nThis primary semantic review covers all 240 cells in the candidate-free packet at exact head `'''+HEAD+'''`, tree `'''+TREE+'''`. The open draft PR and both remote refs were rechecked.\n\n## Review totals\n\n- 160 accept current\n- 32 correction or refinement proposals\n- 48 holds (positions 226, 232, 237, and 242; all 12 locales each)\n\nPosition 234 has the same Spanish string in every locale, so this review proposes localized wording for all 12. Position 239’s source-index line is stale; review uses the active caller at `romarr/ui.py:4444–4447`.\n\nInput checksums, source/current hashes, caller references, placeholders, markup, numbers, edge whitespace, and protected product literals were checked. No repository or PR edits, tests, builds, CI, or browser work were performed. Native-speaker approval is not claimed.\n\nSee `primary-decisions.jsonl`, `holds.jsonl`, `input-verification.json`, `live-pr-verification.json`, and `summary.json`. Verify sealed outputs with `sha256sum -c SHA256SUMS.txt` from this directory.\n'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

manifest_files=[]
for f in sorted(OUT.iterdir()):
    if f.name in ('manifest.json','SHA256SUMS.txt') or not f.is_file(): continue
    data=f.read_bytes(); manifest_files.append({'path':f.name,'bytes':len(data),'sha256':sha(data)})
dump(OUT/'manifest.json',{'artifact':summary['artifact'],'head':HEAD,'tree':TREE,'files':manifest_files,'decisionCounts':dict(counts)})
with (OUT/'SHA256SUMS.txt').open('w',encoding='utf-8') as f:
    for p in sorted(OUT.iterdir()):
        if p.name=='SHA256SUMS.txt' or not p.is_file(): continue
        f.write(f'{sha(p.read_bytes())}  {p.name}\n')
print(json.dumps({'output':str(OUT),'decisionCounts':dict(counts),'ledgerSha256':sha((OUT/'primary-decisions.jsonl').read_bytes()),'holdCells':len(hold_rows),'recommendedCells':sum(counts[d] for d in ('correction','refinement'))},ensure_ascii=False,indent=2))
