#!/usr/bin/env python3
"""Build a primary semantic review using only the sealed W805-W824 candidate-free packet."""
import argparse, collections, hashlib, json, re, shutil
from pathlib import Path

PIN_HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'
PIN_TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
WINDOW='W805-W824'
INPUT_DEFAULT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w805-824-candidate-free-20261105')
OUT=Path(__file__).resolve().parent
PLACEHOLDER=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'<[^>]+>')
NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']

# Cell-specific primary semantic recommendations; all other caller-backed targets
# are retained exactly as found in the candidate-free packet.
ALTERNATIVES={
 ('ui.patches.1c22815500','ar'):('refinement','التعديلات','The navigation item covers translation patches, hacks, and improvements. التعديلات keeps that broader modification sense and matches the Arabic wording for the patch catalogue in the same window.'),
 ('ui.patches-translations-hacks-and-impro.b782f10dd3','ar'):('refinement','التعديلات: ترجمات وهاكات وتحسينات','The heading describes translation, hack, and improvement projects rather than corrections alone. التعديلات matches the surrounding Arabic patch-catalogue wording and preserves the category scope.'),
 ('ui.patches.1c22815500','zh-Hant'):('refinement','補丁','補丁 is the conventional software/game noun and matches 補丁目錄 in this window; 修補 reads more like the act of repairing.'),
 ('ui.patches-translations-hacks-and-impro.b782f10dd3','zh-Hant'):('refinement','補丁：翻譯、改版與改良','Use the same noun 補丁 as the navigation item and catalogue URL label; the list still names translations, hacks, and improvements.'),
 ('ui.path-missing.b602374a06','ar'):('correction','المسار غير موجود','This status is shown when the configured filesystem path does not exist. الطريق means a road; المسار is the filesystem-path term used by the adjacent Path label.'),
 ('ui.path-missing.b602374a06','hi'):('correction','पथ नहीं मिला','This is a filesystem-path status. लापता is unnatural for a missing path; नहीं मिला is the concise “not found” wording used for this state.'),
 ('ui.path-missing.b602374a06','id'):('refinement','Jalur tidak ditemukan','The status means the configured path does not exist. Jalur uses the same Indonesian term as the adjacent Path label and tidak ditemukan is more precise than the English-Indonesian mix Path hilang.'),
 ('ui.peering-shares-nothing-by-itself.8dfca30a01','pt-BR'):('correction','O peering, por si só, não compartilha nada.','The current string adds quotation marks that are absent from the source and uses sozinho awkwardly for this technical subject. This keeps the peer-sharing warning as natural Brazilian Portuguese help text.'),
 ('ui.pick-a-type.be4b3c9327','ar'):('correction','اختر نوعًا.','The current imperative has a spelling error (إختر) and the object needs the indefinite accusative form نوعًا. This is a short instruction above the type choices.'),
 ('ui.pick-a-facet-above.95ff025720','de'):('refinement','Wählen Sie oben {facet} aus.','The caller supplies a translated Genre, Franchise, or Company label. Use formal Sie to match the neighboring German type and route instructions.'),
 ('ui.pick-a-facet-above.95ff025720','es'):('correction','Elige {facet} arriba.','The caller substitutes Género, Franquicia, or Empresa. The fixed masculine article un agrees only with Género, so remove it to keep the sentence grammatical for all three labels.'),
 ('ui.pick-a-facet-above.95ff025720','ko'):('correction','위에서 {facet} 선택하세요.','The caller substitutes 장르, 프랜차이즈, or 회사, which take the object particle 를 rather than 을. Omitting the particle avoids a variable ending and remains natural as concise Korean UI copy.'),
 ('ui.platform-folder-names.4486e3993b','es'):('refinement','Nombres de carpetas por plataforma','This settings heading names folder mappings grouped by platform. Por plataforma states the relationship more naturally than the current de plataforma.'),
}

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def read_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def read_jsonl(p): return [json.loads(s) for s in Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
def write_json(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,rows): Path(p).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')

def protected(s):
    found=[]
    for lit in PROTECTED:
        ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
        if ok: found.append(lit)
    return sorted(set(found))
def token_audit(source,target):
    sph=PLACEHOLDER.findall(source); tph=PLACEHOLDER.findall(target)
    sm=TAG.findall(source); tm=TAG.findall(target)
    sn=NUMBER.findall(source); tn=NUMBER.findall(target)
    sp=protected(source); tp=protected(target)
    missing=[lit for lit in sp if lit not in target]
    return {
        'sourcePlaceholderTokens':sph,'currentTargetPlaceholderTokens':tph,'proposedPlaceholderTokens':tph,
        'placeholderMultisetMatches':collections.Counter(sph)==collections.Counter(tph),
        'sourceMarkupTags':sm,'currentMarkupTags':TAG.findall(target),'proposedMarkupTags':tm,
        'markupMultisetMatches':collections.Counter(sm)==collections.Counter(tm),
        'sourceNumericTokens':sn,'currentNumericTokens':NUMBER.findall(target),'proposedNumericTokens':tn,
        'numericTokensPreserved':collections.Counter(sn)==collections.Counter(tn),
        'sourceProtectedLiterals':sp,'currentProtectedLiterals':protected(target),'proposedProtectedLiterals':tp,
        'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing,
    }

def write_sums(root):
    root=Path(root)
    files=sorted(p for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS.txt')
    (root/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}\n' for p in files),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--candidate-free',type=Path,default=INPUT_DEFAULT); a=ap.parse_args()
    inp=a.candidate_free.resolve(); out=OUT
    if out!=Path(__file__).resolve().parent: raise SystemExit('FAIL output directory')
    # All review evidence comes from this candidate-free packet. No blind or cross-review path is opened.
    for root in (inp,inp/'input',inp/'predecessor'):
        import subprocess
        p=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=root,text=True,capture_output=True)
        if p.returncode: raise SystemExit(f'FAIL candidate-free checksum at {root}: {p.stderr}')
    im=read_json(inp/'input/manifest.json')
    if (im.get('head'),im.get('tree'),im.get('window'))!=(PIN_HEAD,PIN_TREE,WINDOW): raise SystemExit('FAIL candidate-free exact head/tree/window')
    rows=read_jsonl(inp/'input/candidate-free-cells.jsonl')
    contexts={d['sourceId']:d for d in read_jsonl(inp/'input/source-contexts.jsonl')}
    if len(rows)!=240 or len({(r['sourceId'],r['locale']) for r in rows})!=240: raise SystemExit('FAIL candidate-free cell coverage')
    if im.get('callerBackedCells')!=240 or im.get('callerlessHashOnlyCells')!=0 or im.get('priorActiveHashOnlyHoldsCopiedByteForByte')!=1060: raise SystemExit('FAIL candidate-free caller/hold count')
    # Preserve both hash-only hold groups exactly as received in the candidate-free packet.
    pred=out/'predecessor'; pred.mkdir(exist_ok=False)
    for name in ('prior-active-holds-hash-only.jsonl','w785-current-window-holds-hash-only.jsonl'):
        shutil.copyfile(inp/'predecessor'/name,pred/name)
        if (pred/name).read_bytes()!=(inp/'predecessor'/name).read_bytes(): raise SystemExit('FAIL active hold byte copy '+name)
    hold1=read_jsonl(pred/'prior-active-holds-hash-only.jsonl'); hold2=read_jsonl(pred/'w785-current-window-holds-hash-only.jsonl')
    holds=hold1+hold2
    if (len(hold1),len(hold2),len(holds))!=(1012,48,1060): raise SystemExit('FAIL active hold row counts')
    if len({(r.get('sourceId'),r.get('locale')) for r in holds})!=1060: raise SystemExit('FAIL active hold uniqueness')
    if any(r.get('textOmitted') is not True or any(k in r for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) for r in holds): raise SystemExit('FAIL active holds not hash-only')
    ledger=[]; counts=collections.Counter(); target_changes=[]
    for row in rows:
        sid,loc=row['sourceId'],row['locale']; ctx=contexts[sid]
        if row.get('callerless') or not ctx.get('callers'): raise SystemExit(f'FAIL unexpected callerless selected cell {sid}/{loc}')
        src=row['source']; current=row['currentTarget']; key=(sid,loc)
        decision=ALTERNATIVES.get(key)
        disposition,target,rationale=(decision if decision else ('accept_current',current,'The current translation preserves the source meaning in its pinned caller context and reads as suitable UI copy for this locale.'))
        if disposition not in ('accept_current','refinement','correction'): raise SystemExit('FAIL disposition '+str(disposition))
        if disposition=='accept_current' and target!=current or disposition!='accept_current' and target==current: raise SystemExit(f'FAIL target/disposition mismatch {sid}/{loc}')
        audit=token_audit(src,target)
        base_audit=token_audit(src,current)
        # Ensure the input's current-token evidence is internally consistent before reviewing it.
        if (base_audit['sourcePlaceholderTokens']!=row['sourcePlaceholderTokens'] or base_audit['currentTargetPlaceholderTokens']!=row['currentPlaceholderTokens'] or base_audit['sourceMarkupTags']!=row['sourceMarkupTags'] or base_audit['currentMarkupTags']!=row['currentMarkupTags'] or base_audit['sourceNumericTokens']!=row['sourceNumericTokens'] or base_audit['currentNumericTokens']!=row['currentNumericTokens'] or base_audit['sourceProtectedLiterals']!=row['sourceProtectedLiterals'] or base_audit['currentProtectedLiterals']!=protected(current)):
            raise SystemExit(f'FAIL candidate-free token audit mismatch {sid}/{loc}')
        if not (audit['placeholderMultisetMatches'] and audit['markupMultisetMatches'] and audit['numericTokensPreserved'] and audit['protectedLiteralsPreserved']):
            raise SystemExit(f'FAIL recommendation breaks token/protected literal at {sid}/{loc}')
        refs=[{'path':c['path'],'line':c['line'],'matchKind':c['matchKind'],'lineSha256':c['lineSha256'],'excerptSha256':c['excerptSha256'],'fileSha256':c['fileSha256'],'gitBlob':c['gitBlob']} for c in ctx['callers']]
        entry={
            'window':WINDOW,'position':row['position'],'catalogZeroBasedIndex':row['catalogZeroBasedIndex'],'catalogOneBasedPosition':row['catalogOneBasedPosition'],
            'sourceId':sid,'locale':loc,'callerless':False,'source':src,'sourceSha256':row['sourceSha256'],
            'currentTarget':current,'currentTargetSha256':row['currentTargetSha256'],
            'proposedTarget':target,'proposedTargetSha256':sha(target),'selectedTargetSha256':sha(target),
            'candidateFreeCellRecordSha256':sha(canon(row)),'callerContextSha256':row['callerContextSha256'],
            'callerReferenceCount':ctx['exactMatchCount'],'callerReferences':refs,
            'sourcePlaceholderTokens':audit['sourcePlaceholderTokens'],'currentTargetPlaceholderTokens':audit['currentTargetPlaceholderTokens'],'proposedPlaceholderTokens':audit['proposedPlaceholderTokens'],'placeholderMultisetMatches':audit['placeholderMultisetMatches'],
            'sourceMarkupTags':audit['sourceMarkupTags'],'currentMarkupTags':audit['currentMarkupTags'],'proposedMarkupTags':audit['proposedMarkupTags'],'markupMultisetMatches':audit['markupMultisetMatches'],
            'sourceNumericTokens':audit['sourceNumericTokens'],'currentNumericTokens':audit['currentNumericTokens'],'proposedNumericTokens':audit['proposedNumericTokens'],'numericTokensPreserved':audit['numericTokensPreserved'],
            'sourceProtectedLiterals':audit['sourceProtectedLiterals'],'currentProtectedLiterals':audit['currentProtectedLiterals'],'proposedProtectedLiterals':audit['proposedProtectedLiterals'],'missingProtectedLiterals':audit['missingProtectedLiterals'],'protectedLiteralsPreserved':audit['protectedLiteralsPreserved'],
            'disposition':disposition,'rationale':rationale,'confidence':'moderate','reviewMethod':'primary machine semantic review from candidate-free source and caller evidence','nativeSpeakerApproval':False,'candidateFree':True,
        }
        if target!=current: target_changes.append({'sourceId':sid,'locale':loc,'disposition':disposition,'currentTargetSha256':row['currentTargetSha256'],'selectedTargetSha256':sha(target)})
        ledger.append(entry); counts[disposition]+=1
    if set(ALTERNATIVES)!={(r['sourceId'],r['locale']) for r in ledger if r['disposition']!='accept_current'}: raise SystemExit('FAIL alternatives coverage')
    write_jsonl(out/'primary-review-ledger.jsonl',ledger)
    prev_src=inp/'predecessor'
    lineage={'predecessorWindow':'W785-W804','activeHashOnlyHoldCount':1060,'copiedByteForByte':True,'sourceCandidateFreeHead':PIN_HEAD,'sourceCandidateFreeTree':PIN_TREE,'sourceCandidateFreeChecksumListSha256':sha((inp/'SHA256SUMS.txt').read_bytes()),'groups':[{'path':'prior-active-holds-hash-only.jsonl','rowCount':len(hold1),'sha256':sha((pred/'prior-active-holds-hash-only.jsonl').read_bytes())},{'path':'w785-current-window-holds-hash-only.jsonl','rowCount':len(hold2),'sha256':sha((pred/'w785-current-window-holds-hash-only.jsonl').read_bytes())}],'uniqueHoldCells':1060,'sourceAndCurrentTargetHashesReattestedInCandidateFreeInput':True,'holdTextOmitted':True,'resultingActiveHashOnlyHolds':1060}
    write_json(out/'hold-lineage.json',lineage)
    next_boundary=im['nextBoundary']
    summary={'artifact':'ROMarrNG PR #70 W805-W824 primary translation review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':WINDOW,'head':PIN_HEAD,'tree':PIN_TREE,'candidateFreePath':str(inp),'candidateFreeSha256SumsListSha256':sha((inp/'SHA256SUMS.txt').read_bytes()),'cells':len(ledger),'callerBackedCells':240,'callerlessHashOnlyCells':0,'priorActiveHashOnlyHoldsCopiedByteForByte':1060,'resultingActiveHashOnlyHolds':1060,'dispositions':dict(sorted(counts.items())),'correctionOrRefinementCells':counts['correction']+counts['refinement'],'alternativeTargets':len(target_changes),'confidenceCounts':dict(collections.Counter(e['confidence'] for e in ledger)),'localeCount':12,'nextBoundary':next_boundary,'reviewType':'primary machine semantic review from candidate-free source/caller evidence','nativeSpeakerApproval':False,'blindOrCrossReviewMaterialUsed':False,'productWorktreeEdited':False,'catalogValuesApplied':False,'testsBuildsScansCiRun':False}
    write_json(out/'summary.json',summary)
    (out/'README.md').write_text(f'''# ROMarrNG PR #70 W805–W824 primary translation review

Pinned to product head `{PIN_HEAD}` / tree `{PIN_TREE}`. The review used the sealed candidate-free packet `{inp}`; its complete checksum-list SHA-256 is `{summary['candidateFreeSha256SumsListSha256']}`. The adjacent W785–W804 primary packet was read for schema and verification conventions. No blind or cross-review material was used.

The ledger covers 240 caller-backed source-locale cells across 12 locales. It preserves source, current-target, recommended-target, caller-context, caller-reference, and token/protected-literal hashes per cell. Dispositions: {counts['accept_current']} accept current, {counts['refinement']} refinements, and {counts['correction']} corrections. All {counts['refinement']+counts['correction']} changed targets preserve the source placeholders, markup, numbers, and protected literals.

The 1,060 active W785–W804 hash-only holds are copied byte-for-byte in two source groups under `predecessor/`; they remain text-free and unchanged. No new callerless holds are added. Native-speaker approval is not included.

The next queue boundary is index {next_boundary['continuationIndex']}, one-based position {next_boundary['oneBasedPosition']}: `{next_boundary['sourceId']}` with source hash `{next_boundary['sourceSha256']}`.

No product or PR files were edited, no values were applied, and no repository tests, builds, or CI were run. Verify with `python3 -B verify_primary_review.py --repo /home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685 --candidate-free {inp}`.
''',encoding='utf-8')
    write_sums(out)
    print(json.dumps({'result':'BUILT','head':PIN_HEAD,'tree':PIN_TREE,'window':WINDOW,'cells':len(ledger),'dispositions':dict(sorted(counts.items())),'alternativeTargets':len(target_changes),'activePriorHashOnlyHoldsCopiedByteForByte':1060,'resultingActiveHashOnlyHolds':1060,'nextBoundary':next_boundary},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
