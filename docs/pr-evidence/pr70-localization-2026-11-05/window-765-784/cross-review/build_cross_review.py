#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, pathlib, re, subprocess, unicodedata

OUT = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-third-party-cross-review-20261105')
BASE = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105')
CF = BASE / 'candidate-free'
INPUT = CF / 'input'
PRIMARY = BASE / 'primary-review'
REPO = pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD = '9714d7cf69c687685b4f65cbd9627a56830bab85'
TREE = 'c8eb66573f10b2390a02df05033f5133425d5e41'
WINDOW = 'W765-W784'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

# Independent decisions after reviewing candidate-free source/current values and callers.
# A selected primary proposal is reported as a correction or refinement as adjudicated here.
CHANGE_NOTES = {
 ('ui.on-this-install.ca75d54e64','ar'): ('correction', 'في هذا التثبيت', 'The caller is a heading above route-status rows for this software instance. The current phrase means only “on this” and omits the installation; this target supplies it.'),
 ('ui.on-this-install.ca75d54e64','fr'): ('refinement', 'Dans cette installation', 'The heading describes route availability within the current software installation. “Dans” reads more naturally for that scope than the current literal “Sur” phrasing.'),
 ('ui.on-this-install.ca75d54e64','hi'): ('refinement', 'इस इंस्टॉलेशन पर', 'The caller refers to the current software instance. The loanword इंस्टॉलेशन is clearer for software than the broader स्थापना while retaining the locative relation.'),
 ('ui.on-this-install.ca75d54e64','ko'): ('correction', '이 설치에서', 'The route table is scoped to this running installation. The current noun phrase omits the locative relation; this target expresses “in/on this installation.”'),
 ('ui.on-this-install.ca75d54e64','vi'): ('refinement', 'Trong bản cài đặt này', 'The heading scopes route rows to the current software instance. “Trong” expresses being within this installation more naturally than the current “Trên” wording.'),
 ('ui.on-this-install.ca75d54e64','zh-Hans'): ('refinement', '在此安装中', 'The heading scopes route rows to the current software instance. This expresses “within this installation” more naturally than the current literal “on this installation.”'),
 ('ui.on-this-install.ca75d54e64','zh-Hant'): ('refinement', '在此安裝中', 'The heading scopes route rows to the current software instance. This expresses “within this installation” more naturally than the current literal “on this installation.”'),
 ('ui.open-the-submission.4a863bf1dd','fr'): ('correction', 'Ouvrir la soumission', 'The caller links to the user’s external submission for review and posting. “Proposition” means a proposal and changes the object; “soumission” matches the linked submission.'),
 ('ui.openxbl-api-key.90ea47aa7f','zh-Hans'): ('refinement', 'OpenXBL API 密钥', 'The caller is a password credential field. 密钥 is the standard Simplified Chinese term for a secret/API key; OpenXBL and API remain intact.'),
 ('ui.openxbl-api-key.90ea47aa7f','zh-Hant'): ('refinement', 'OpenXBL API 金鑰', 'The caller is a password credential field. 金鑰 is the standard Traditional Chinese term for a secret/API key; OpenXBL and API remain intact.'),
}

SOURCE_NOTES = {
 'ui.on-this-day.d011904834': 'The pinned games navigation places this beside Multiplayer, Genre, and Franchise as the date-based anniversary view; the current target conveys that meaning.',
 'ui.on-this-install.ca75d54e64': 'The pinned caller uses this as the heading for status rows on the current software installation; the current target adequately scopes that heading.',
 'ui.one-game-one-rom.3372b0856c': 'The pinned caller is a checkbox label in the library/import controls; the current target preserves the one-game/one-ROM relationship and the protected ROM term.',
 'ui.one-other-dump.6710e50b16': 'The pinned caller selects this singular label only when exactly one discarded dump exists; the current target conveys one additional dump in that count branch.',
 'ui.one-title-per-line-comments-ranking.8c54c86102': 'The pinned modal explains a title-list input format; the current target keeps the # comment marker and →tab← separator and conveys line, ranking, and title/platform guidance.',
 'ui.only-dat-verified-dumps.a372d56f1d': 'The pinned peer-scope option limits results to DAT-verified dumps; the current target preserves the uppercase DAT identifier and the “only” restriction.',
 'ui.only-selected-regions.e257690d2c': 'The pinned import checkbox restricts processing to selected regions; the current target preserves that scope.',
 'ui.only-the-platforms-i-name.a25a55c6dd': 'The pinned peer-scope option restricts matches to platforms selected by the user; the current target preserves both the “only” restriction and user choice.',
 'ui.open-navigation.0ed77fd261': 'The pinned use is the accessible label for the mobile navigation toggle; the current target tells the user that the navigation can be opened.',
 'ui.open-on-the-indexer.4766c56d0d': 'The pinned use is a title/tooltip for an outbound indexer link; the current target communicates opening the item at the indexer.',
 'ui.open-on-indexer.202e1ad5f5': 'The pinned use is an accessible-label template for an outbound indexer link; the current target preserves the {indexer} argument and communicates the destination.',
 'ui.open-the-submission.4a863bf1dd': 'The pinned link opens the external submission so the user can review and post it; the current target names that object.',
 'ui.open-this-invitation-on-my-romarr.b76952fe51': 'The pinned use is the invitation action button; the current target preserves the exact ROMarr product name and asks the user to open the invitation there.',
 'ui.openxbl-api-key.90ea47aa7f': 'The pinned use labels a password field for the OpenXBL credential; the current target preserves OpenXBL and the protected API term.',
 'ui.optional-connections-to-the-rest-of.636208f858': 'The pinned general-settings description says service connections are optional, credentials remain in the environment file, this page never exposes secrets, and other integrations have their own settings.',
 'ui.optional-follow-ups.e3fee9a99c': 'The pinned use is a card heading for follow-up actions; the current target identifies those actions as optional.',
 'ui.optional-message-priority.dbcf318711': 'The pinned use is a notification configuration field; the current target identifies message priority as optional.',
 'ui.optional-apprise-urls-to-notify-one.8ef42d4f02': 'The pinned notification configuration help names Apprise URLs and explains one-per-line or comma-separated input; the current target preserves the product name and both accepted formats.',
}
EXTRA_PROTECTED = {
 'ui.one-title-per-line-comments-ranking.8c54c86102': ['#','→tab←'],
 'ui.openxbl-api-key.90ea47aa7f': ['OpenXBL'],
 'ui.optional-apprise-urls-to-notify-one.8ef42d4f02': ['Apprise'],
}

def sha(v):
    if isinstance(v, str): v = v.encode('utf-8')
    return hashlib.sha256(v).hexdigest()

def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8')

def read_json(path): return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def read_jsonl(path): return [json.loads(x) for x in pathlib.Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(path, val): pathlib.Path(path).write_text(json.dumps(val, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
def write_jsonl(path, rows): pathlib.Path(path).write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True)+'\n' for x in rows), encoding='utf-8')
def cellkey(row): return (row['sourceId'], row['locale'])

def verify_dir(root):
    root = pathlib.Path(root)
    sums = root/'SHA256SUMS.txt'
    seen = {}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line: continue
        digest, name = line.split('  ',1)
        path = (root/name).resolve()
        if name in seen or not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest:
            raise SystemExit('input checksum failed: '+str(root/name))
        seen[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != sums}
    if actual != set(seen): raise SystemExit('input checksum inventory mismatch: '+str(root))
    manifest = root/'manifest.json'
    if not manifest.is_file() and (root/'input/manifest.json').is_file(): manifest = root/'input/manifest.json'
    if not manifest.is_file() and (root/'summary.json').is_file(): manifest = root/'summary.json'
    return {'path':str(root), 'checksumListSha256':sha(sums.read_bytes()), 'manifestSha256':sha(manifest.read_bytes()), 'fileCount':len(seen)}

def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args], text=True).strip()

def token_evidence(source, target, row):
    placeholders = lambda s: collections.Counter(re.findall(r'\{[^{}]+\}', s))
    tags = lambda s: collections.Counter(re.findall(r'<[^>]+>', s))
    numbers = lambda s: collections.Counter([''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in m) for m in re.findall(r'\d+', s)])
    source_nums, target_nums = numbers(source), numbers(target)
    protected = list(row.get('sourceProtectedLiterals',[]))
    additional = EXTRA_PROTECTED.get(row['sourceId'],[])
    missing = [x for x in protected+additional if x not in target]
    return {
      'placeholderMultisetMatches':placeholders(source)==placeholders(target),
      'markupMatches':tags(source)==tags(target),
      'numericTokensPreserved':not bool(source_nums-target_nums),
      'sourceNumericTokens':list(numbers(source).elements()),
      'selectedNumericTokens':list(numbers(target).elements()),
      'sourceProtectedLiterals':protected,
      'additionalProtectedLiterals':additional,
      'missingProtectedLiterals':missing,
      'protectedLiteralsPreserved':not missing,
    }

def verify_contexts(contexts, cells):
    by_source={c['sourceId']:c for c in contexts}
    refs=0
    for sid, context in by_source.items():
        if context.get('head') != HEAD or context.get('tree') not in (None,TREE): raise SystemExit('caller context pin: '+sid)
        associated=[x for x in cells if x['sourceId']==sid]
        if not associated or any(x.get('callerContextSha256') != context.get('contextSha256') for x in associated): raise SystemExit('cell/context binding: '+sid)
        if context.get('callerless'):
            if context.get('callers') not in (None,[]) or 'source' in context or context.get('sourceTextOmitted') is not True: raise SystemExit('callerless context is not redacted: '+sid)
            continue
        for caller in context.get('callers',[]):
            raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{caller["path"]}'])
            if sha(raw)!=caller['fileSha256'] or git('rev-parse',f'{HEAD}:{caller["path"]}')!=caller['gitBlob']: raise SystemExit('pinned caller file mismatch: '+caller['path'])
            lines=raw.decode('utf-8').splitlines()
            if lines[caller['line']-1] != caller['lineText']: raise SystemExit('pinned caller line mismatch: '+caller['path'])
            for excerpt in caller['excerpt']:
                if lines[excerpt['line']-1] != excerpt['text']: raise SystemExit('pinned caller excerpt mismatch: '+caller['path'])
            refs+=1
    return by_source,refs

def main():
    if not OUT.is_dir(): raise SystemExit('output directory missing')
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'):
        raise SystemExit('worktree is not clean at pinned head/tree')
    cf_pin=verify_dir(CF); input_pin=verify_dir(INPUT); primary_pin=verify_dir(PRIMARY)
    cf_manifest=read_json(INPUT/'manifest.json')
    primary_manifest=read_json(PRIMARY/'manifest.json')
    primary_summary=read_json(PRIMARY/'summary.json')
    primary_ref=read_json(PRIMARY/'input-reference.json')
    if (cf_manifest.get('repository'),cf_manifest.get('pullRequest'),cf_manifest.get('window'),cf_manifest.get('head'),cf_manifest.get('tree')) != ('snapetech-org/ROMarrNG',70,WINDOW,HEAD,TREE): raise SystemExit('candidate-free input pin mismatch')
    if (cf_manifest.get('cellCount'),cf_manifest.get('callerBackedCells'),cf_manifest.get('callerlessHashOnlyCells'),cf_manifest.get('priorActiveHoldsReattested'),cf_manifest.get('newWindowHashOnlyHolds')) != (240,216,24,988,24): raise SystemExit('candidate-free count mismatch')
    if (primary_summary.get('head'),primary_summary.get('tree'),primary_summary.get('window'),primary_summary.get('cellCount')) != (HEAD,TREE,WINDOW,240): raise SystemExit('primary summary pin mismatch')
    if primary_summary.get('decisionCounts') != {'accept-current':206,'correction':3,'refinement':7,'hold-callerless-hash-only':24}: raise SystemExit('primary decisions summary mismatch')
    if (primary_manifest.get('head'),primary_manifest.get('tree'),primary_manifest.get('window'),primary_manifest.get('cellCount')) != (HEAD,TREE,WINDOW,240): raise SystemExit('primary manifest pin mismatch')
    if primary_ref.get('candidateFreeManifestSha256') != sha((INPUT/'manifest.json').read_bytes()) or primary_ref.get('candidateFreeChecksumListSha256') != cf_pin['checksumListSha256'] or primary_ref.get('candidateFreeCellRowsSha256') != sha((INPUT/'candidate-free-cells.jsonl').read_bytes()): raise SystemExit('primary/candidate-free binding mismatch')
    if primary_summary.get('nativeSpeakerReviewPerformed') is not False or primary_summary.get('headedBrowserReviewPerformed') is not False: raise SystemExit('primary review limitations mismatch')

    cells=read_jsonl(INPUT/'candidate-free-cells.jsonl')
    contexts=read_jsonl(INPUT/'source-contexts.jsonl')
    prior_holds=read_jsonl(INPUT/'prior-hold-reattestation.jsonl')
    primary_rows=read_jsonl(PRIMARY/'ledger.jsonl')
    proposals=read_jsonl(PRIMARY/'proposals.jsonl')
    primary_holds=read_jsonl(PRIMARY/'holds.jsonl')
    if (len(cells),len(contexts),len(prior_holds),len(primary_rows),len(proposals),len(primary_holds)) != (240,20,988,240,10,24): raise SystemExit('row counts mismatch')
    expected_order=[(i,loc) for i in range(765,785) for loc in LOCALES]
    if [(x['catalogZeroBasedIndex'],x['locale']) for x in cells] != expected_order: raise SystemExit('candidate-free cell order mismatch')
    cmap={cellkey(x):x for x in cells}; pmap={cellkey(x):x for x in primary_rows}; propmap={cellkey(x):x for x in proposals}; holdmap={cellkey(x):x for x in primary_holds}
    if any(len(m)!=240 for m in (cmap,pmap)) or cmap.keys()!=pmap.keys() or len(propmap)!=10 or len(holdmap)!=24: raise SystemExit('input cell identity mismatch')
    contexts_by_source, caller_refs=verify_contexts(contexts,cells)
    cross=[]; selected_changes=[]; current_holds=[]
    counts=collections.Counter(); action_table=collections.Counter(); token_failures=[]
    for c in cells:
        k=cellkey(c); p=pmap[k]; proposal=propmap.get(k); ph=holdmap.get(k); cid=f'{c["sourceId"]}::{c["locale"]}'
        bind_fields=('sourceId','locale','sourceSha256','currentTargetSha256','callerContextSha256','callerless','catalogZeroBasedIndex','catalogOneBasedPosition','position')
        for field in bind_fields:
            if c.get(field)!=p.get(field): raise SystemExit(f'candidate/primary row mismatch {cid} field={field}')
        if c.get('callerless'):
            if not ph or p.get('decision')!='hold-callerless-hash-only': raise SystemExit('callerless primary hold missing: '+cid)
            if any(field in row for row in (c,p,ph) for field in ('source','currentTarget','proposedTarget','target')): raise SystemExit('callerless input text leak: '+cid)
            if proposal is not None: raise SystemExit('callerless proposal present: '+cid)
            out={
              'cellId':cid,'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],'position':c['position'],
              'sourceId':c['sourceId'],'locale':c['locale'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],
              'callerContextSha256':c['callerContextSha256'],'candidateFreeRecordSha256':sha(canon(c)),'primaryRecordSha256':sha(canon(p)),
              'callerless':True,'sourceTextOmitted':True,'targetTextOmitted':True,'primaryDecision':'hold-callerless-hash-only',
              'crossDisposition':'hold-callerless-hash-only','confidence':'unknown','reviewOnly':True,
            }
            cross.append(out)
            current_holds.append({'cellId':cid,'sourceId':c['sourceId'],'locale':c['locale'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'sourceTextOmitted':True,'targetTextOmitted':True})
            counts['hold-callerless-hash-only']+=1; action_table['hold-callerless-hash-only|hold-callerless-hash-only']+=1
            continue
        if any(field not in c for field in ('source','currentTarget')): raise SystemExit('caller-backed source/target missing: '+cid)
        if p.get('source')!=c['source'] or p.get('currentTarget')!=c['currentTarget']: raise SystemExit('primary text mismatch: '+cid)
        if sha(c['source'])!=c['sourceSha256'] or sha(c['currentTarget'])!=c['currentTargetSha256']: raise SystemExit('source/current target hash mismatch: '+cid)
        if c['callerContextSha256']!=contexts_by_source[c['sourceId']]['contextSha256']: raise SystemExit('caller context hash mismatch: '+cid)
        current_ev=token_evidence(c['source'],c['currentTarget'],c)
        if not all(current_ev[k2] for k2 in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')): raise SystemExit('candidate current token failure: '+cid)
        if c.get('placeholderMultisetMatches') is not True or c.get('markupMatches') is not True or c.get('numericTokensPreserved') is not True or c.get('protectedLiteralsPreserved') is not True: raise SystemExit('candidate-free token summary mismatch: '+cid)
        if proposal:
            expected=CHANGE_NOTES.get(k)
            if not expected: raise SystemExit('unadjudicated primary proposal: '+cid)
            disposition,target,note=expected
            if p.get('decision')!=disposition or proposal.get('decision')!=disposition or proposal.get('proposedTarget')!=target or proposal.get('proposedTargetSha256')!=sha(target): raise SystemExit('proposal binding/adjudication mismatch: '+cid)
            selected=target; selected_from='primary'; cross_disposition=disposition; cross_note=note
            if proposal.get('source')!=c['source'] or proposal.get('currentTarget')!=c['currentTarget'] or proposal.get('sourceSha256')!=c['sourceSha256'] or proposal.get('currentTargetSha256')!=c['currentTargetSha256'] or proposal.get('callerContextSha256')!=c['callerContextSha256']: raise SystemExit('proposal source/context binding mismatch: '+cid)
            if p.get('decisionOutputSha256')!=sha(selected): raise SystemExit('primary decision output hash mismatch: '+cid)
        else:
            if p.get('decision')!='accept-current' or p.get('decisionOutputSha256')!=c['currentTargetSha256']: raise SystemExit('unresolved primary decision or proposal: '+cid)
            selected=c['currentTarget']; selected_from='current'; cross_disposition='accept-current'
            cross_note=SOURCE_NOTES.get(c['sourceId'])
            if not cross_note: raise SystemExit('source context note missing: '+c['sourceId'])
        selected_ev=token_evidence(c['source'],selected,c)
        if not all(selected_ev[k2] for k2 in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')):
            token_failures.append(cid)
        context=contexts_by_source[c['sourceId']]
        caller_evidence=[{'file':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'excerptSha256':x['excerptSha256'],'matchKind':x['matchKind']} for x in context.get('callers',[])]
        out={
          'cellId':cid,'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],'position':c['position'],
          'sourceId':c['sourceId'],'locale':c['locale'],'callerless':False,'source':c['source'],'sourceSha256':c['sourceSha256'],
          'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'catalogTranslationHash':c['catalogTranslationHash'],
          'callerContextSha256':c['callerContextSha256'],'callerCount':c['literalCallerCount'],'callerEvidence':caller_evidence,
          'candidateFreeRecordSha256':sha(canon(c)),'primaryRecordSha256':sha(canon(p)),
          'primaryDecision':p['decision'],'primaryProposal':proposal.get('proposedTarget') if proposal else None,
          'primaryProposalSha256':proposal.get('proposedTargetSha256') if proposal else None,
          'primaryRationale':proposal.get('rationale') if proposal else p.get('rationale'),
          'crossDisposition':cross_disposition,'selectedFrom':selected_from,'selectedTarget':selected,'selectedTargetSha256':sha(selected),
          'tokenEvidence':selected_ev,'crossRationale':cross_note,'confidence':'moderate','nativeSpeakerApproval':False,'reviewOnly':True,
        }
        cross.append(out); counts[cross_disposition]+=1; action_table[f'{p["decision"]}|{cross_disposition}']+=1
        if proposal:
            selected_changes.append({
              'cellId':cid,'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],
              'sourceId':c['sourceId'],'locale':c['locale'],'source':c['source'],'sourceSha256':c['sourceSha256'],
              'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'selectedTarget':selected,
              'selectedTargetSha256':sha(selected),'callerContextSha256':c['callerContextSha256'],
              'primaryDecision':p['decision'],'crossDisposition':cross_disposition,'selectedFrom':'primary',
              'crossRationale':cross_note,'tokenEvidence':selected_ev,'reviewOnly':True,
            })
    if token_failures: raise SystemExit('selected target token failures: '+','.join(token_failures))
    expected_counts=collections.Counter({'accept-current':206,'correction':3,'refinement':7,'hold-callerless-hash-only':24})
    if counts!=expected_counts: raise SystemExit('cross disposition counts mismatch: '+str(counts))
    if len(selected_changes)!=10 or len(current_holds)!=24: raise SystemExit('selected change or current hold count mismatch')
    prior_summary=read_json(INPUT/'prior-hold-reattestation-summary.json')
    if prior_summary.get('count')!=988 or prior_summary.get('allTargetHashesMatch') is not True or prior_summary.get('textInHoldRows') is not False or prior_summary.get('changedTargets')!=0: raise SystemExit('prior hold reattestation summary mismatch')
    if len(prior_holds)!=988 or any(any(f in row for f in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) for row in prior_holds): raise SystemExit('prior active holds contain text or wrong count')
    if len(current_holds)!=24 or any(any(f in row for f in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) for row in current_holds): raise SystemExit('current hash-only holds contain text or wrong count')
    if collections.Counter((r['sourceId'],r['catalogZeroBasedIndex']) for r in current_holds) != collections.Counter({('ui.only-for-an-http-endpoint-and-only-w.b82289ba66',771):12,('ui.only-useful-if-romarr-runs-on-the-ma.0db665240e',774):12}): raise SystemExit('current callerless source counts mismatch')
    boundary=read_jsonl(INPUT/'selection-boundary.jsonl')
    next_row=next((x for x in boundary if x.get('role')=='catalog-after-selected-end'),None)
    next_boundary={'continuationIndex':785,'oneBasedPosition':786,'sourceId':'ui.optional-overrides-the-webhook-s-dis.4116a5e8e4','sourceSha256':'4116a5e8e4222045299ae89f3577810da389c5c65f51cf8a3b097ecf05ef348e'}
    if not next_row or (next_row.get('catalogZeroBasedIndex'),next_row.get('sourceId'),next_row.get('sourceSha256'))!=(next_boundary['continuationIndex'],next_boundary['sourceId'],next_boundary['sourceSha256']): raise SystemExit('next boundary mismatch')
    primary_counts=collections.Counter(x['decision'] for x in primary_rows)
    if dict(primary_counts)!={'accept-current':206,'correction':3,'refinement':7,'hold-callerless-hash-only':24}: raise SystemExit('primary row decisions mismatch')
    if action_table != collections.Counter({'accept-current|accept-current':206,'correction|correction':3,'refinement|refinement':7,'hold-callerless-hash-only|hold-callerless-hash-only':24}): raise SystemExit('primary/cross action table mismatch')

    # Pin the original input checksum inventories so the cross packet can be rechecked later.
    for src,name in ((CF/'SHA256SUMS.txt','candidate-free-SHA256SUMS.txt'),(INPUT/'SHA256SUMS.txt','candidate-free-input-SHA256SUMS.txt'),(PRIMARY/'SHA256SUMS.txt','primary-SHA256SUMS.txt')):
        (OUT/name).write_bytes(src.read_bytes())
    write_jsonl(OUT/'cross-ledger.jsonl',cross)
    write_jsonl(OUT/'selected-changes.jsonl',selected_changes)
    write_jsonl(OUT/'prior-active-holds-hash-only.jsonl',prior_holds)
    write_jsonl(OUT/'current-window-holds-hash-only.jsonl',current_holds)
    (OUT/'caller-contexts-pinned.jsonl').write_bytes((INPUT/'source-contexts.jsonl').read_bytes())
    pins={
      'schemaVersion':1,'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':WINDOW,
      'catalogZeroBasedIndices':[765,784],'catalogOneBasedPositions':[766,785],'head':HEAD,'tree':TREE,
      'candidateFree':cf_pin,'candidateFreeInput':input_pin,'candidateFreeCellsSha256':sha((INPUT/'candidate-free-cells.jsonl').read_bytes()),
      'sourceContextsSha256':sha((INPUT/'source-contexts.jsonl').read_bytes()),
      'primaryReview':primary_pin,'primaryManifestSha256':sha((PRIMARY/'manifest.json').read_bytes()),
      'primaryInputReferenceSha256':sha((PRIMARY/'input-reference.json').read_bytes()),
      'primaryLedgerSha256':sha((PRIMARY/'ledger.jsonl').read_bytes()),'primaryProposalsSha256':sha((PRIMARY/'proposals.jsonl').read_bytes()),
      'exactCallerFilesRechecked':True,'worktree':str(REPO),'worktreeClean':True,
      'reviewBasis':'Candidate-free exact-head current values and caller contexts independently adjudicated against the sealed primary ledger; no earlier-window recommendations were used.'
    }
    write_json(OUT/'input-pins.json',pins)
    summary={
      'result':'PASS','artifact':'ROMarrNG PR #70 W765-W784 independent third-party cross-review',
      'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':WINDOW,
      'catalogZeroBasedIndices':[765,784],'catalogOneBasedPositions':[766,785],
      'cells':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'callerReferences':caller_refs,
      'primaryDecisionCounts':dict(primary_counts),
      'crossDispositionCounts':dict(counts),'primaryCrossActionTable':dict(action_table),
      'primaryProposalsAdjudicated':len(selected_changes),'primaryProposalsAccepted':len(selected_changes),
      'priorActiveHoldsPreservedHashOnly':len(prior_holds),'newCallerlessHoldsHashOnly':len(current_holds),
      'resultingActiveHashOnlyHolds':len(prior_holds)+len(current_holds),
      'currentTokenFailures':0,'selectedTokenFailures':len(token_failures),
      'nativeSpeakerReviewPerformed':False,'headedBrowserReviewPerformed':False,'confidence':'moderate',
      'nextBoundary':next_boundary,'repositoryEdited':False,'catalogsEdited':False,'testsBuildsScansCiRun':False,
    }
    write_json(OUT/'summary.json',summary)
    readme=f'''# ROMarrNG PR #70 W765–W784 independent third-party cross-review

Pinned to PR head `{HEAD}` and tree `{TREE}`. The cross-review covers all 240 catalog cells across 12 locales, using the sealed candidate-free source/current-target packet and sealed primary review. Candidate-free, input, and primary checksum inventories and their packet verifiers passed; the pinned worktree was clean.

Cross dispositions: 206 accept-current, 3 corrections, 7 refinements, and 24 callerless hash-only holds. The 10 primary proposals were individually checked against the exact caller context and selected as review-only changes. Callerless cells remain text-free and hash-only. The packet preserves 988 prior active holds and adds 24 current callerless holds, for 1,012 active holds.

All current and selected targets pass placeholder, markup, numeric, and protected-literal checks. The additional checks preserve `#` and `→tab←` in the title-list instructions, `OpenXBL`, and `Apprise`. The next boundary is catalog index 785 / one-based position 786, source `ui.optional-overrides-the-webhook-s-dis.4116a5e8e4`.

Confidence is moderate. Native-speaker and headed-browser review were not performed. Verify with `python3 -B verify_cross_review.py`. This packet is review-only: no repository/catalog files were changed, and no tests, builds, scans, or CI were run.
'''
    (OUT/'README.md').write_text(readme,encoding='utf-8')
    file_hashes={p.relative_to(OUT).as_posix():sha(p.read_bytes()) for p in OUT.rglob('*') if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
    manifest={
      'schemaVersion':1,'artifact':'ROMarrNG PR #70 W765-W784 independent third-party cross-review',
      'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':WINDOW,
      'cellCount':240,'crossDispositionCounts':dict(counts),'priorActiveHoldsPreserved':988,
      'currentCallerlessHolds':24,'resultingActiveHolds':1012,'nextBoundary':next_boundary,'files':file_hashes,
    }
    write_json(OUT/'manifest.json',manifest)
    entries=[f'{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt']
    (OUT/'SHA256SUMS.txt').write_text('\n'.join(entries)+'\n',encoding='utf-8')
    print(json.dumps({'result':'SEALED','output':str(OUT),'counts':dict(counts),'selectedChanges':len(selected_changes),'priorHolds':len(prior_holds),'activeHolds':len(prior_holds)+len(current_holds),'callerReferences':caller_refs,'checksumListSha256':sha((OUT/'SHA256SUMS.txt').read_bytes())},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
