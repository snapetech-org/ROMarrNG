#!/usr/bin/env python3
"""Build candidate-free ROMarrNG PR #70 W805-W824 evidence from pinned Git data."""
import argparse, collections, hashlib, json, re, shutil, subprocess
from pathlib import Path

HEAD = '551cccd03e0acdce208ce11f571378c1dcdfb805'
TREE = 'd77f32ac8ec0ab53200d04819869a2e99c6de73c'
BRANCH = 'task/localization-translation-review-20261030'
WINDOW = 'W805-W824'
PREV_WINDOW = 'W785-W804'
START, END = 805, 824
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER = re.compile(r'\{[^{}]+\}')
TAG = re.compile(r'<[^>]+>')
NUMBER = re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED = ['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']


def sha(v):
    if isinstance(v, str): v = v.encode('utf-8')
    return hashlib.sha256(v).hexdigest()

def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8')
def rj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,v): Path(p).write_text(json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
def wjl(p,rows): Path(p).write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',',':'))+'\n' for x in rows), encoding='utf-8')
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args], text=True).strip()
def json_git(repo,ref,path): return json.loads(subprocess.check_output(['git','-C',str(repo),'show',f'{ref}:{path}']))

def checksum_map(root, checksum_name='SHA256SUMS.txt'):
    root=Path(root).resolve(); sums=root/checksum_name
    listed={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); n=n.removeprefix('./'); p=(root/n).resolve()
        if not p.is_relative_to(root) or not p.is_file() or sha(p.read_bytes())!=h or n in listed:
            raise SystemExit(f'FAIL checksum {p}')
        listed[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}
    if set(listed)!=actual: raise SystemExit(f'FAIL checksum coverage {root}: missing={sorted(set(listed)-actual)} unlisted={sorted(actual-set(listed))}')
    return listed

def protected(s):
    found=[]
    for lit in PROTECTED:
        ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
        if ok: found.append(lit)
    return sorted(set(found))

def tokens(s): return {'placeholders':PLACEHOLDER.findall(s),'markup':TAG.findall(s),'numbers':NUMBER.findall(s),'protectedLiterals':protected(s)}

def token_row(source,target):
    s,t=tokens(source),tokens(target)
    ph=collections.Counter(s['placeholders'])==collections.Counter(t['placeholders'])
    mk=collections.Counter(s['markup'])==collections.Counter(t['markup'])
    sn,tn=collections.Counter(s['numbers']),collections.Counter(t['numbers']); extra=list((tn-sn).elements())
    presentation=bool(re.search(r'\bzero\b',source,re.I) and not s['numbers'] and extra==['0'])
    numeric=not (sn-tn) and (not extra or presentation)
    missing=[x for x in s['protectedLiterals'] if x not in target]
    return {'sourcePlaceholderTokens':s['placeholders'],'currentPlaceholderTokens':t['placeholders'],'placeholderMultisetMatches':ph,'sourceMarkupTags':s['markup'],'currentMarkupTags':t['markup'],'markupMatches':mk,'sourceNumericTokens':s['numbers'],'currentNumericTokens':t['numbers'],'numericTokensPreserved':numeric,'numericPresentationEquivalent':presentation,'sourceProtectedLiterals':s['protectedLiterals'],'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}

def prod_paths(repo,commit):
    files=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',commit,'--','romarr'],text=True).splitlines()
    allowed={'.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx'}; out=[]
    for rel in files:
        p=Path(rel); parts=rel.lower().split('/')
        if p.suffix.lower() not in allowed or any(x in parts for x in ('test','tests','__pycache__')) or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
        out.append(rel)
    return out

def file_tuple(repo,rel,commit):
    raw=subprocess.check_output(['git','-C',str(repo),'show',f'{commit}:{rel}'])
    return raw.decode('utf-8','replace'),raw,git(repo,'rev-parse',f'{commit}:{rel}')

def match_context(item,files,commit):
    source=item['source']; back=chr(96)
    variants=list(dict.fromkeys([json.dumps(source,ensure_ascii=False),repr(source),'"'+source+'"',"'"+source+"'",back+source+back]))
    callers=[]
    for rel,(text,data,blob) in files.items():
        hits={}
        for lit in variants:
            pos=0
            while True:
                i=text.find(lit,pos)
                if i<0: break
                hits.setdefault(i,'exact quoted source literal'); pos=i+max(1,len(lit))
        pos=0
        while True:
            i=text.find(item['sourceId'],pos)
            if i<0: break
            hits.setdefault(i,'exact source ID reference'); pos=i+len(item['sourceId'])
        for m in re.finditer(r'>[ \t]*'+re.escape(source)+r'[ \t]*<',text): hits.setdefault(m.start(),'exact HTML text node')
        lines=text.splitlines()
        for pos,kind in sorted(hits.items()):
            line=text.count('\n',0,pos)+1
            excerpt=[{'line':n,'text':lines[n-1]} for n in range(max(1,line-3),min(len(lines),line+3)+1)]
            line_text=lines[line-1] if line<=len(lines) else ''
            callers.append({'path':rel,'line':line,'lineText':line_text,'lineSha256':sha(line_text),'excerpt':excerpt,'excerptSha256':sha(canon(excerpt)),'fileSha256':sha(data),'gitBlob':blob,'matchKind':kind})
    callers.sort(key=lambda x:(x['path'],x['line'],x['matchKind']))
    core={'sourceId':item['sourceId'],'source':source,'sourceSha256':item['sourceSha256'],'head':commit,'searchMethod':'exact quoted source literal, source ID, or exact HTML text node in tracked production code under romarr; tests, docs, catalogs, and workflows excluded','productionFilesSearched':len(files),'exactMatchCount':len(callers),'callerless':not callers,'callers':callers}
    return {**core,'contextSha256':sha(canon(core))}

def safe_context(c):
    fields={k:c[k] for k in ('sourceId','sourceSha256','head','searchMethod','productionFilesSearched','exactMatchCount','callerless','contextSha256')}
    fields.update({'sourceTextOmitted':True,'callerTextOmitted':True,'callers':[]} if c['callerless'] else {'source':c['source'],'callers':c['callers']})
    return fields

def write_sums(root, checksum_name='SHA256SUMS.txt'):
    root=Path(root)
    files=sorted(p for p in root.rglob('*') if p.is_file() and p!=root/checksum_name)
    (root/checksum_name).write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}\n' for p in files),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--predecessor',type=Path,required=True,help='committed W785-W804 candidate-free directory')
    ap.add_argument('--w785-holds',type=Path,required=True,help='hash-only W785 current-window holds file')
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    repo=a.repo.resolve(); prev=a.predecessor.resolve(); cross=a.w785_holds.resolve(); out=a.output.resolve()
    expected_out=Path(__file__).resolve().parent
    if out!=expected_out: raise SystemExit('FAIL output path must be this task packet directory')
    if git(repo,'rev-parse','HEAD')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=TREE or git(repo,'status','--porcelain=v1','--untracked-files=all'):
        raise SystemExit('FAIL exact head/tree or dirty source worktree')
    inp=out/'input'; pred=out/'predecessor'; inp.mkdir(exist_ok=False); pred.mkdir(exist_ok=False)
    # Only candidate-free predecessor files and the sealed hash-only active-hold file are read.
    checksum_map(prev); checksum_map(prev/'input')
    prev_input=prev/'input'; pm=rj(prev_input/'manifest.json')
    if (pm.get('head'),pm.get('tree'),pm.get('window'),pm.get('cellCount'),pm.get('resultingActiveHashOnlyHolds')) != ('bbbf84d0d83138a23143f6aa6075415ebcb36d3e','fbf9ada4b4fd43a288ce498b24990312f0c32f22',PREV_WINDOW,240,1060):
        # Older input manifests may record the previous hold count before a root follow-up; the byte sources below govern count.
        if (pm.get('head'),pm.get('tree'),pm.get('window'),pm.get('cellCount')) != ('bbbf84d0d83138a23143f6aa6075415ebcb36d3e','fbf9ada4b4fd43a288ce498b24990312f0c32f22',PREV_WINDOW,240):
            raise SystemExit('FAIL predecessor candidate-free manifest pin')
    prev_selected=rjl(prev_input/'selected-sources.jsonl')
    prev_boundary=rjl(prev_input/'selection-boundary.jsonl')
    if len(prev_selected)!=20 or prev_selected[0].get('catalogZeroBasedIndex')!=785 or prev_selected[-1].get('catalogZeroBasedIndex')!=804:
        raise SystemExit('FAIL predecessor source range')
    old_holds=prev_input/'prior-active-holds-hash-only.jsonl'
    if not old_holds.is_file(): raise SystemExit('FAIL missing prior active hash-only holds')
    if not cross.is_file(): raise SystemExit('FAIL missing W785 current-window hash-only holds')
    shutil.copyfile(old_holds,pred/'prior-active-holds-hash-only.jsonl')
    shutil.copyfile(cross,pred/'w785-current-window-holds-hash-only.jsonl')
    hold1012=rjl(pred/'prior-active-holds-hash-only.jsonl'); hold48=rjl(pred/'w785-current-window-holds-hash-only.jsonl')
    if len(hold1012)!=1012 or len(hold48)!=48: raise SystemExit(f'FAIL predecessor active hold counts {len(hold1012)} + {len(hold48)}')
    if any(row.get('textOmitted') is not True for row in hold1012+hold48): raise SystemExit('FAIL hold row is not marked hash-only')
    forbidden=('source','sourceText','currentTarget','target','targetText','proposedTarget','translation','reviewDecision','decision')
    if any(k in row for row in hold1012+hold48 for k in forbidden): raise SystemExit('FAIL active hold packet includes text or review fields')
    if len({(r.get('sourceId'),r.get('locale')) for r in hold1012+hold48})!=1060: raise SystemExit('FAIL active hold uniqueness')
    catalog_path='romarr/ui-labels.json'; registry_path='romarr/ui-source-messages.json'; snapshot_path='romarr/ui-source-snapshot.json'
    catalog_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{catalog_path}'])
    registry_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{registry_path}'])
    snapshot_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{snapshot_path}'])
    catalog=json.loads(catalog_raw); msgs=catalog['messages']; ids=list(msgs)
    if len(msgs)!=1836: raise SystemExit('FAIL catalog message count')
    registry_doc=json.loads(registry_raw); regrows=registry_doc['messages']; registry={r['id']:r for r in regrows}
    if len(registry)!=len(regrows): raise SystemExit('FAIL duplicate registry IDs')
    snapshot=json.loads(snapshot_raw)
    if any(snapshot.get(r['id'])!=r['sourceHash'] for r in regrows): raise SystemExit('FAIL registry/source snapshot hash mismatch')
    # The old catalog key order and W785 end boundary must join to this pinned catalog exactly.
    old_order=rjl(prev_input/'catalog-key-order.jsonl')
    if len(old_order)!=len(ids) or any(row.get('sourceId')!=sid or row.get('sourceSha256')!=sha(msgs[sid]['source']) for row,sid in zip(old_order,ids)):
        raise SystemExit('FAIL candidate-free predecessor catalog order/hash differs from pinned current head')
    old_after=[r for r in prev_boundary if r.get('catalogZeroBasedIndex')==START and r.get('role')=='catalog-after-selected-end']
    if len(old_after)!=1: raise SystemExit('FAIL predecessor boundary record at index 805')
    if old_after[0].get('sourceId')!=ids[START] or old_after[0].get('sourceSha256')!=sha(msgs[ids[START]]['source']): raise SystemExit('FAIL predecessor-to-current queue boundary')
    if prev_selected[-1].get('sourceId')!=ids[804] or prev_selected[-1].get('sourceSha256')!=sha(msgs[ids[804]]['source']): raise SystemExit('FAIL previous selected end does not precede current start')
    active_hold_rows=[]
    for row in hold1012+hold48:
        sid,loc=row.get('sourceId'),row.get('locale')
        msg=msgs.get(sid)
        if not msg or loc not in msg.get('translations',{}): raise SystemExit(f'FAIL held cell missing from pinned catalog {sid}/{loc}')
        sh=sha(msg['source']); th=sha(msg['translations'][loc])
        expected=row.get('currentTargetSha256')
        if sh!=row.get('sourceSha256') or expected!=th: raise SystemExit(f'FAIL prior active hold changed at exact head {sid}/{loc}')
        if row.get('catalogZeroBasedIndex') is not None and row['catalogZeroBasedIndex']!=ids.index(sid): raise SystemExit(f'FAIL prior active hold catalog position {sid}/{loc}')
        active_hold_rows.append({'sourceId':sid,'locale':loc,'catalogZeroBasedIndex':ids.index(sid),'sourceSha256':sh,'currentTargetSha256':th})
    production={p:file_tuple(repo,p,HEAD) for p in prod_paths(repo,HEAD)}
    active_rank={sid:i for i,sid in enumerate(sorted(registry),1)}
    selected=[]; contexts=[]; cells=[]; mismatch=collections.Counter()
    for idx in range(START,END+1):
        sid=ids[idx]; msg=msgs[sid]; src=msg['source']; sh=sha(src)
        if msg.get('sourceHash')!=sh or (sid in registry and registry[sid].get('sourceHash')!=sh): raise SystemExit(f'FAIL selected source hash {sid}')
        selected.append({'position':idx,'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'sourceSha256':sh,'activeSourceRank':active_rank.get(sid),'activeSourceRegistry':sid in registry,'registryLocations':registry.get(sid,{}).get('locations',[]),'source':src})
    for item in selected:
        ctx=match_context(item,production,HEAD); contexts.append(ctx)
        for loc in LOCALES:
            target=msgs[item['sourceId']].get('translations',{}).get(loc)
            if not isinstance(target,str) or not target: raise SystemExit(f'FAIL missing current translation {item["sourceId"]}/{loc}')
            base={'window':WINDOW,'position':item['position'],'catalogZeroBasedIndex':item['catalogZeroBasedIndex'],'catalogOneBasedPosition':item['catalogOneBasedPosition'],'sourceId':item['sourceId'],'sourceSha256':item['sourceSha256'],'locale':loc,'callerContextSha256':ctx['contextSha256'],'literalCallerCount':ctx['exactMatchCount'],'callerless':ctx['callerless'],'candidateFree':True,'currentTargetSha256':sha(target)}
            if ctx['callerless']:
                base.update({'cellDisposition':'hold-callerless-hash-only','sourceTextOmitted':True,'currentTargetTextOmitted':True})
            else:
                tok=token_row(item['source'],target)
                mismatch['placeholder']+=int(not tok['placeholderMultisetMatches']); mismatch['markup']+=int(not tok['markupMatches']); mismatch['numeric']+=int(not tok['numericTokensPreserved']); mismatch['numericPresentationDifferences']+=int(tok['numericPresentationEquivalent']); mismatch['protectedLiteral']+=int(not tok['protectedLiteralsPreserved'])
                base.update({'source':item['source'],'currentTarget':target,**tok,'catalogTranslationHash':msgs[item['sourceId']].get('translationHashes',{}).get(loc),'translationStatus':msgs[item['sourceId']].get('translationStatus',{}).get(loc)})
            cells.append(base)
    callerless=sum(1 for c in contexts if c['callerless']); holdcells=callerless*len(LOCALES)
    if len(selected)!=20 or len(cells)!=240 or len({(c['sourceId'],c['locale']) for c in cells})!=240: raise SystemExit('FAIL selection/cell counts')
    if set(r['sourceId'] for r in selected)&set(r['sourceId'] for r in prev_selected): raise SystemExit('FAIL selection overlaps predecessor window')
    order_rows=[{'catalogZeroBasedIndex':i,'sourceId':sid,'sourceSha256':sha(msgs[sid]['source'])} for i,sid in enumerate(ids)]
    boundary_rows=[{'position':i,'catalogZeroBasedIndex':i,'sourceId':ids[i],'sourceSha256':sha(msgs[ids[i]]['source']),'role':role,'sourceTextOmitted':True} for i,role in ((804,'catalog-before-selected-start'),(805,'selected-start'),(824,'selected-end'),(825,'catalog-after-selected-end'))]
    next_boundary={'continuationIndex':END+1,'oneBasedPosition':END+2,'sourceId':ids[END+1],'sourceSha256':sha(msgs[ids[END+1]]['source'])}
    locales=LOCALES
    safe_selected=[]
    for row,ctx in zip(selected,contexts):
        safe_selected.append({k:v for k,v in row.items() if k!='source'}|({'source':row['source']} if not ctx['callerless'] else {'sourceTextOmitted':True}))
    pins={'head':HEAD,'tree':TREE,'catalogPath':catalog_path,'catalogSha256':sha(catalog_raw),'catalogGitBlob':git(repo,'rev-parse',f'{HEAD}:{catalog_path}'),'catalogMessageCount':len(msgs),'catalogKeyOrderSha256':sha(('\n'.join(ids)+'\n').encode()),'sourceQueuePath':registry_path,'sourceQueueSha256':sha(registry_raw),'sourceQueueGitBlob':git(repo,'rev-parse',f'{HEAD}:{registry_path}'),'sourceSnapshotPath':snapshot_path,'sourceSnapshotSha256':sha(snapshot_raw),'sourceSnapshotGitBlob':git(repo,'rev-parse',f'{HEAD}:{snapshot_path}'),'activeUniqueSourceIds':len(registry)}
    source_files={'head':HEAD,'tree':TREE,'productionFilesSearched':len(production),'files':[]}
    for rel,(text,data,blob) in sorted(production.items()): source_files['files'].append({'path':rel,'fileSha256':sha(data),'gitBlob':blob,'bytes':len(data)})
    wj(inp/'catalog-file-pins.json',pins)
    wj(inp/'source-file-pins.json',source_files)
    wjl(inp/'catalog-key-order.jsonl',order_rows)
    wjl(inp/'selected-sources.jsonl',safe_selected)
    wjl(inp/'selection-boundary.jsonl',boundary_rows)
    wjl(inp/'source-contexts.jsonl',[safe_context(c) for c in contexts])
    wjl(inp/'candidate-free-cells.jsonl',cells)
    wj(inp/'candidate-free-token-summary.json',{'callerBackedCellCount':len(cells)-holdcells,'callerlessCellCount':holdcells,'tokenAuditedCellCount':len(cells)-holdcells,**dict(mismatch)})
    wj(inp/'source-snapshot-hashes.json',snapshot)
    wj(inp/'selection.json',{'window':WINDOW,'selectionBasis':f'catalog insertion order at exact pinned {catalog_path} indices {START} through {END} (zero-based)','positions':[START,END],'catalogOneBasedPositions':[START+1,END+1],'sourceCount':20,'localeCount':12,'cellCount':240,'localeOrder':LOCALES,'selectedSources':safe_selected})
    wj(inp/'queue-continuity.json',{'result':'PASS','head':HEAD,'tree':TREE,'predecessorWindow':PREV_WINDOW,'predecessorSelectedEndIndex':804,'predecessorSelectedEndSourceId':prev_selected[-1]['sourceId'],'predecessorBoundaryAtCurrentStart':old_after[0],'currentSelectedStartIndex':START,'currentSelectedStartSourceId':ids[START],'currentSelectedEndIndex':END,'currentSelectedEndSourceId':ids[END],'nextBoundary':next_boundary,'catalogInsertionOrderAndSourceHashesMatchPredecessor':True})
    wj(pred/'active-hold-provenance.json',{'predecessorWindow':PREV_WINDOW,'activeHoldCount':1060,'hashOnly':True,'byteForByteCopied':True,'groups':[{'path':'prior-active-holds-hash-only.jsonl','origin':str(old_holds),'rowCount':len(hold1012),'sha256':sha((pred/'prior-active-holds-hash-only.jsonl').read_bytes())},{'path':'w785-current-window-holds-hash-only.jsonl','origin':str(cross),'rowCount':len(hold48),'sha256':sha((pred/'w785-current-window-holds-hash-only.jsonl').read_bytes())}],'uniqueCells':len({(r['sourceId'],r['locale']) for r in hold1012+hold48}),'allSourceAndTargetHashesMatchPinnedCurrentCatalog':True,'sourceAndTargetTextOmitted':True})
    wj(inp/'input-verification.json',{'result':'PASS','worktree':str(repo),'worktreeCleanAtBuild':True,'head':HEAD,'tree':TREE,'branch':git(repo,'branch','--show-current'),'pullRequest':70,'predecessorCandidateFreeChecksums':'PASS','activeHoldFilesCopiedByteForByte':True,'activeHashOnlyHoldsReattested':1060,'predecessorWindow':PREV_WINDOW,'predecessorNextBoundaryMatchesCurrentStart':True,'catalogQueueBoundaryIndex':START,'selectedSourceCount':20,'selectedCellCount':240,'nextBoundary':next_boundary,'proposalsOrReviewDecisionsIncluded':False,'testsBuildsOrCIExecuted':False})
    manifest={'artifact':'ROMarrNG PR #70 W805-W824 candidate-free exact-head input','repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':git(repo,'branch','--show-current'),'expectedBranch':BRANCH,'head':HEAD,'tree':TREE,'window':WINDOW,'catalogSelectionZeroBased':[START,END],'catalogSelectionOneBased':[START+1,END+1],'sourceCount':20,'localeCount':12,'cellCount':len(cells),'localeOrder':LOCALES,'callerBackedSourceCount':20-callerless,'callerBackedCells':len(cells)-holdcells,'callerlessSourceCount':callerless,'callerlessHashOnlyCells':holdcells,'directCallerReferences':sum(c['exactMatchCount'] for c in contexts),'productionCallerFilesSearched':len(production),'currentTokenMismatchCounts':dict(mismatch),'priorActiveHashOnlyHoldsCopiedByteForByte':1060,'priorActiveHashOnlyHoldsReattested':1060,'resultingActiveHashOnlyHolds':1060+holdcells,'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,'repoEdited':False,'testsBuildsScansCiRun':False,'predecessorWindow':PREV_WINDOW,'nextBoundary':next_boundary}
    wj(inp/'manifest.json',manifest)
    (out/'README.md').write_text(f'''# ROMarrNG PR #70 W805–W824 candidate-free packet

Pinned from Git to head `{HEAD}` and tree `{TREE}` on branch `{git(repo,'branch','--show-current')}`. The selection covers zero-based catalog indices {START}–{END} (one-based positions {START+1}–{END+1}), 20 consecutive sources, and 240 cells in locale order: {', '.join(LOCALES)}.

This packet records {len(cells)-holdcells} caller-backed cells and {holdcells} callerless hash-only cells. For caller-backed sources it includes the exact production caller excerpts, current catalog target text, placeholder/markup/number audits, and protected-literal audit. Callerless cells carry only source/target hashes and caller-context hashes.

The {len(hold1012)+len(hold48)} active W785 hash-only holds were copied byte-for-byte from the committed candidate-free input and the W785 current-window hash-only hold file, then reattested against this exact catalog. Their copied files remain separate and unchanged; the resulting active count for this window is {len(hold1012)+len(hold48)+holdcells}.

The queue boundary continues from W785–W804 index 804 to this window's index 805. The next boundary is index {END+1}, one-based position {END+2}: `{next_boundary['sourceId']}` with source hash `{next_boundary['sourceSha256']}`.

No proposal or review material is included or consulted. No repository or PR files were changed; no tests, builds, scans, or CI were run. Verify the packet with `python3 verify_candidate_free.py --repo {repo} --predecessor {prev} --w785-holds {cross}`.
''',encoding='utf-8')
    write_sums(inp)
    write_sums(pred)
    write_sums(out)
    print(json.dumps({'result':'BUILT','head':HEAD,'tree':TREE,'window':WINDOW,'cells':len(cells),'callerBackedCells':len(cells)-holdcells,'callerlessHashOnlyCells':holdcells,'priorActiveHoldsCopiedByteForByte':len(hold1012)+len(hold48),'resultingActiveHolds':len(hold1012)+len(hold48)+holdcells,'nextBoundary':next_boundary},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
