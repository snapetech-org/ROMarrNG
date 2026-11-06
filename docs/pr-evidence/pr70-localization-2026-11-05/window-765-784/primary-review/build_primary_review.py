#!/usr/bin/env python3
"""Create independent primary semantic review from sealed candidate-free W765-W784 only."""
import collections, hashlib, json, pathlib, re, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
CF=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/candidate-free')
REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='9714d7cf69c687685b4f65cbd9627a56830bab85'; TREE='c8eb66573f10b2390a02df05033f5133425d5e41'
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences','OpenXBL','Apprise']
PROPOSALS={
 (766,'ar'):('في هذا التثبيت','correction','The current phrase “على هذا” means “on this” and omits the installation named by the heading; this gives “in this installation.”'),
 (766,'fr'):('Dans cette installation','refinement','The caller labels diagnostics for the current software installation; dans is the idiomatic preposition for this context.'),
 (766,'hi'):('इस इंस्टॉलेशन पर','refinement','The heading refers to the current software installation; इंस्टॉलेशन is clearer here than the broader/formal स्थापना.'),
 (766,'ko'):('이 설치에서','correction','The source includes the relation “on/in”; the current 이 설치 is only “this installation” and lacks that relation.'),
 (766,'vi'):('Trong bản cài đặt này','refinement','The caller describes the current installation; trong is more idiomatic than trên for this section heading.'),
 (766,'zh-Hans'):('在此安装中','refinement','The section describes this software installation; 在此安装中 is natural for “in this installation.”'),
 (766,'zh-Hant'):('在此安裝中','refinement','The section describes this software installation; 在此安裝中 is natural for “in this installation.”'),
 (778,'fr'):('Ouvrir la soumission','correction',"This link opens the user's submission to review and post; proposition means a proposal and changes the object."),
 (780,'zh-Hans'):('OpenXBL API 密钥','refinement','This labels an API credential field; 密钥 is the standard term for a secret/API key.'),
 (780,'zh-Hant'):('OpenXBL API 金鑰','refinement','This labels an API credential field; 金鑰 is the standard Traditional Chinese term for a secret/API key.'),
}
RATIONALE={
 765:'The pinned caller places this in the games navigation beside Multiplayer, Genre, and Franchise; the target labels the date-based view.',
 766:'The caller uses this as the heading above route diagnostics for the current software installation.',
 767:'The caller is an import setting checkbox; the target preserves the one-game/one-ROM rule.',
 768:'The caller labels the singular-item expandable summary for a discarded dump.',
 769:'The caller is parser help text; the target explains one title per line, hash comments, ranking numbers, and the title/tab/platform line format.',
 770:'The caller is a peer-scope option; the target restricts sharing to DAT-verified dumps.',
 772:'The caller labels the region allowlist checkbox in import planning; the target preserves the selected-regions scope.',
 773:'The caller is a peer-scope option; the target restricts sharing to platforms the user specifies.',
 775:'The caller supplies the navigation toggle accessible name and translated label; the target describes opening navigation.',
 776:'The caller supplies an indexer-link title and accessible-name fallback; the target names opening the result on its indexer.',
 777:'The caller builds the indexer-link title with this dynamic indexer name; the placeholder is preserved.',
 778:"The caller labels a link to the user's submission for review and posting.",
 779:'The caller is the invitation-flow button; the target preserves the invitation action and ROMarr product name.',
 780:'The caller labels the OpenXBL credential field; the product name and API term are preserved.',
 781:'The caller places this explanation on General settings; the target covers optional integrations, environment-file credentials, secrets, and separate settings pages.',
 782:'The caller uses this as a section heading for non-required follow-up actions.',
 783:'The caller uses this as the webhook message-priority field description; the target marks the field optional.',
 784:'The caller uses this as the notification URL field description; the target preserves Apprise and the line/comma-separated input formats.',
}

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def protected(source):
    found=[]
    for lit in PROTECTED:
        ok=lit in source if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',source))
        if ok: found.append(lit)
    return sorted(set(found))
def token_check(source,target):
    source_tokens={'placeholders':PH.findall(source),'markup':TAG.findall(source),'numbers':NUMBER.findall(source),'protected':protected(source)}
    target_tokens={'placeholders':PH.findall(target),'markup':TAG.findall(target),'numbers':NUMBER.findall(target)}
    check={
       'placeholderMultisetMatches':collections.Counter(source_tokens['placeholders'])==collections.Counter(target_tokens['placeholders']),
       'markupMatches':collections.Counter(source_tokens['markup'])==collections.Counter(target_tokens['markup']),
       'numericTokensPreserved':collections.Counter(source_tokens['numbers'])==collections.Counter(target_tokens['numbers']),
       'protectedLiteralsPreserved':all(x in target for x in source_tokens['protected']),
    }
    return source_tokens,target_tokens,check

def main():
    if any(p.is_file() and p.name!='build_primary_review.py' for p in ROOT.iterdir()): raise SystemExit('primary output directory not empty')
    subprocess.run([sys.executable,str(CF/'verify_candidate_free.py'),'--repo',str(REPO)],check=True,cwd=CF,stdout=subprocess.DEVNULL)
    manifest=json.loads((CF/'input/manifest.json').read_text(encoding='utf-8'))
    cells=readjl(CF/'input/candidate-free-cells.jsonl')
    if (manifest.get('head'),manifest.get('tree'),manifest.get('window'),len(cells))!=(HEAD,TREE,'W765-W784',240): raise SystemExit('candidate-free pin/coverage')
    ledger=[]; proposals=[]; holds=[]
    for cell in cells:
        key=(cell['catalogZeroBasedIndex'],cell['locale'])
        base={k:cell.get(k) for k in ('window','position','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','sourceSha256','locale','callerContextSha256','literalCallerCount','callerless','currentTargetSha256','candidateFree')}
        if cell.get('callerless'):
            if key in PROPOSALS or any(k in cell for k in ('source','currentTarget')): raise SystemExit('callerless cell must remain text-free '+str(key))
            row={**base,'decision':'hold-callerless-hash-only','confidence':'unknown','rationale':'No production caller was found in the pinned worktree; keep this cell hash-only until caller context exists.','sourceTextOmitted':True,'currentTargetTextOmitted':True}
            holds.append(row)
        else:
            if 'source' not in cell or 'currentTarget' not in cell: raise SystemExit('caller-backed text missing '+str(key))
            source=cell['source']; target=cell['currentTarget']; src_tokens,tgt_tokens,cur_check=token_check(source,target)
            if not all(cur_check.values()): raise SystemExit('current token mismatch '+str(key)+' '+repr(cur_check))
            if any(not cell.get(field) for field in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')): raise SystemExit('candidate-free token mismatch '+str(key))
            proposal=PROPOSALS.get(key)
            context={'callerContextSha256':cell['callerContextSha256'],'literalCallerCount':cell['literalCallerCount'],'source':source,'currentTarget':target}
            if proposal:
                proposed,kind,reason=proposal
                if proposed==target: raise SystemExit('proposal equals current '+str(key))
                src_prop,tgt_prop,prop_check=token_check(source,proposed)
                if not all(prop_check.values()): raise SystemExit('proposal token mismatch '+str(key)+' '+repr(prop_check))
                row={**base,**context,'decision':kind,'confidence':'moderate','rationale':reason,'proposedTarget':proposed,'proposedTargetSha256':sha(proposed),'decisionOutputSha256':sha(proposed),
                     'currentTokenEvidence':{k:cell[k] for k in ('sourcePlaceholderTokens','currentPlaceholderTokens','placeholderMultisetMatches','sourceMarkupTags','currentMarkupTags','markupMatches','sourceNumericTokens','currentNumericTokens','numericTokensPreserved','numericPresentationEquivalent','sourceProtectedLiterals','missingProtectedLiterals','protectedLiteralsPreserved')},
                     'proposalTokenEvidence':prop_check|{'sourceTokens':src_prop,'targetTokens':tgt_prop},'proposalTokenEvidenceSha256':sha(canon(prop_check|{'sourceTokens':src_prop,'targetTokens':tgt_prop}))}
                proposals.append(row)
            else:
                rank=cell['catalogZeroBasedIndex']
                if rank not in RATIONALE: raise SystemExit('no rationale for source '+str(rank))
                row={**base,**context,'decision':'accept-current','confidence':'moderate','rationale':RATIONALE[rank],'decisionOutputSha256':cell['currentTargetSha256'],
                     'currentTokenEvidence':{k:cell[k] for k in ('sourcePlaceholderTokens','currentPlaceholderTokens','placeholderMultisetMatches','sourceMarkupTags','currentMarkupTags','markupMatches','sourceNumericTokens','currentNumericTokens','numericTokensPreserved','numericPresentationEquivalent','sourceProtectedLiterals','missingProtectedLiterals','protectedLiteralsPreserved')}}
        ledger.append(row)
    counts=collections.Counter(x['decision'] for x in ledger)
    expected=collections.Counter({'accept-current':206,'correction':3,'refinement':7,'hold-callerless-hash-only':24})
    if counts!=expected: raise SystemExit('decision count '+repr(counts))
    candidate_input={
       'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W765-W784',
       'candidateFreePath':str(CF),'candidateFreeManifestSha256':sha((CF/'input/manifest.json').read_bytes()),
       'candidateFreeChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),
       'candidateFreeCellRowsSha256':sha((CF/'input/candidate-free-cells.jsonl').read_bytes()),
       'reviewBasis':'Sealed candidate-free source/current targets and exact pinned caller contexts; no primary proposal targets were copied from other windows.',
       'provenanceNote':'For packet schema only, the W745 primary builder script was consulted after this candidate-free packet sealed. Its hard-coded W745 proposal targets were not used as evidence or targets; current window decisions were independently reviewed from this packet.'}
    (ROOT/'input-reference.json').write_text(json.dumps(candidate_input,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in ledger),encoding='utf-8')
    (ROOT/'proposals.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in proposals),encoding='utf-8')
    (ROOT/'holds.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in holds),encoding='utf-8')
    summary={'artifact':'ROMarrNG PR #70 W765-W784 independent primary semantic review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W765-W784','catalogZeroBasedIndices':[765,784],'catalogOneBasedPositions':[766,785],'sourceCount':20,'localeCount':12,'cellCount':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'decisionCounts':dict(counts),'proposalCount':len(proposals),'correctionCount':3,'refinementCount':7,'priorActiveHoldsReattested':988,'newWindowHashOnlyHolds':24,'resultingActiveHashOnlyHolds':1012,'priorAppliedCellsReattested':144,'priorFullReadbackWindowCount':10,'allCandidateFreeBaselineTokensPass':True,'allProposalTokensPass':True,'confidence':'moderate','nativeSpeakerReviewPerformed':False,'headedBrowserReviewPerformed':False,'priorRecommendationsUsed':False,'processProvenanceNoteIncluded':True,'catalogsEdited':False,'repoEdited':False,'testsBuildsScansCiRun':False,'nextBoundary':manifest['nextBoundary']}
    (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'''# ROMarrNG PR #70 W765–W784 primary review

This primary ledger uses the sealed candidate-free packet at `{HEAD}` / tree `{TREE}`. It covers 216 caller-backed cells and keeps 24 cells from two callerless sources as text-free hash-only holds. The candidate-free packet reattests 988 active prior holds, 144 applied cells, and ten full readback windows. This window adds 24 callerless holds, for 1,012 active hash-only holds.

Decisions: 206 accept-current, three corrections, seven refinements, and 24 callerless hash-only holds. The ten draft proposals refine “On this install” in seven locales, correct the French submission label, and use standard Simplified and Traditional Chinese API-key terminology. Placeholder, markup, numeric, and protected-literal checks pass for all proposals. Confidence is moderate; native-speaker and headed-browser review were not performed.

Provenance: no W765–W784 recommendation from another reviewer was read. After candidate-free sealed, the W745 primary builder script was consulted only for packet schema. It contains W745-specific hard-coded targets; none were reused as evidence or proposals here.

No repository/catalog files were changed. No tests, builds, scans, or CI were run. Verify with `python3 verify_primary_review.py`.
''',encoding='utf-8')
    files=sorted(p for p in ROOT.iterdir() if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt'))
    manifest_out={'artifact':'ROMarrNG PR #70 W765-W784 primary review','head':HEAD,'tree':TREE,'window':'W765-W784','cellCount':240,'decisionCounts':dict(counts),'candidateFreeManifestSha256':candidate_input['candidateFreeManifestSha256'],'candidateFreeChecksumsSha256':candidate_input['candidateFreeChecksumListSha256'],'files':{p.name:sha(p.read_bytes()) for p in files}}
    (ROOT/'manifest.json').write_text(json.dumps(manifest_out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files=sorted(p for p in ROOT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
    (ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files),encoding='utf-8')
    print(json.dumps({'result':'BUILT','decisionCounts':dict(counts),'proposalCount':len(proposals),'holdCount':len(holds)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
