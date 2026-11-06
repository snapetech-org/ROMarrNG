#!/usr/bin/env python3
"""Verify the sealed candidate-free ROMarrNG PR #70 W805-W824 packet."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path

HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'
TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
WINDOW='W805-W824'; PREV_WINDOW='W785-W804'; START=805; END=824
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']

def sha(v):
    if isinstance(v,str): v=v.encode('utf-8')
    return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def check_sums(root,name='SHA256SUMS.txt'):
    root=Path(root).resolve(); sf=root/name; listed={}
    for line in sf.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); n=n.removeprefix('./'); p=(root/n).resolve()
        if not p.is_relative_to(root) or not p.is_file() or sha(p.read_bytes())!=h or n in listed: raise SystemExit(f'FAIL checksum {p}')
        listed[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sf}
    if set(listed)!=actual: raise SystemExit(f'FAIL checksum coverage {root}')
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
    variants=list(dict.fromkeys([json.dumps(source,ensure_ascii=False),repr(source),'"'+source+'"',"'"+source+"'",back+source+back])); callers=[]
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

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); ap.add_argument('--predecessor',type=Path,required=True); ap.add_argument('--w785-holds',type=Path,required=True)
    a=ap.parse_args(); repo=a.repo.resolve(); prev=a.predecessor.resolve(); cross=a.w785_holds.resolve(); out=Path(__file__).resolve().parent
    root_sums=check_sums(out); inp=out/'input'; pred=out/'predecessor'; check_sums(inp); check_sums(pred)
    if git(repo,'rev-parse','HEAD')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=TREE or git(repo,'status','--porcelain=v1','--untracked-files=all'):
        raise SystemExit('FAIL source Git pin or clean worktree')
    if git(repo,'branch','--show-current')!='task/localization-translation-review-20261030': raise SystemExit('FAIL source branch')
    manifest=rj(inp/'manifest.json')
    if (manifest.get('head'),manifest.get('tree'),manifest.get('window'),manifest.get('cellCount'))!=(HEAD,TREE,WINDOW,240): raise SystemExit('FAIL manifest pin')
    p_input=prev/'input'; check_sums(prev); check_sums(p_input)
    prev_sel=rjl(p_input/'selected-sources.jsonl'); prev_bound=rjl(p_input/'selection-boundary.jsonl')
    if len(prev_sel)!=20 or prev_sel[0].get('catalogZeroBasedIndex')!=785 or prev_sel[-1].get('catalogZeroBasedIndex')!=804: raise SystemExit('FAIL predecessor range')
    original1=p_input/'prior-active-holds-hash-only.jsonl'; original2=cross
    if (pred/'prior-active-holds-hash-only.jsonl').read_bytes()!=original1.read_bytes(): raise SystemExit('FAIL first active-hold file was not copied byte-for-byte')
    if (pred/'w785-current-window-holds-hash-only.jsonl').read_bytes()!=original2.read_bytes(): raise SystemExit('FAIL W785 current-hold file was not copied byte-for-byte')
    holds1=rjl(pred/'prior-active-holds-hash-only.jsonl'); holds2=rjl(pred/'w785-current-window-holds-hash-only.jsonl')
    if (len(holds1),len(holds2))!=(1012,48): raise SystemExit('FAIL copied active-hold counts')
    forbidden={'source','sourceText','currentTarget','target','targetText','proposedTarget','translation','reviewDecision','decision'}
    holds=holds1+holds2
    if len({(r.get('sourceId'),r.get('locale')) for r in holds})!=1060: raise SystemExit('FAIL active-hold uniqueness')
    if any(r.get('textOmitted') is not True or forbidden.intersection(r) for r in holds): raise SystemExit('FAIL active holds not hash-only')
    raw_cat=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:romarr/ui-labels.json']); catalog=json.loads(raw_cat); msgs=catalog['messages']; ids=list(msgs)
    raw_reg=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:romarr/ui-source-messages.json']); regdoc=json.loads(raw_reg); registry={r['id']:r for r in regdoc['messages']}
    raw_snap=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:romarr/ui-source-snapshot.json']); snapshot=json.loads(raw_snap)
    if len(msgs)!=1836 or any(snapshot.get(r['id'])!=r['sourceHash'] for r in regdoc['messages']): raise SystemExit('FAIL pinned catalog or registry snapshot')
    order=rjl(inp/'catalog-key-order.jsonl')
    if len(order)!=len(ids) or any(x.get('catalogZeroBasedIndex')!=i or x.get('sourceId')!=sid or x.get('sourceSha256')!=sha(msgs[sid]['source']) for i,(x,sid) in enumerate(zip(order,ids))): raise SystemExit('FAIL full catalog order/source hashes')
    pins=rj(inp/'catalog-file-pins.json')
    if pins.get('catalogSha256')!=sha(raw_cat) or pins.get('catalogGitBlob')!=git(repo,'rev-parse',f'{HEAD}:romarr/ui-labels.json') or pins.get('sourceQueueSha256')!=sha(raw_reg) or pins.get('sourceSnapshotSha256')!=sha(raw_snap): raise SystemExit('FAIL catalog source pins')
    for r in holds:
        sid,loc=r['sourceId'],r['locale']; msg=msgs.get(sid)
        if not msg or loc not in msg.get('translations',{}) or sha(msg['source'])!=r.get('sourceSha256') or sha(msg['translations'][loc])!=r.get('currentTargetSha256'):
            raise SystemExit(f'FAIL active hold reattestation {sid}/{loc}')
        if r.get('catalogZeroBasedIndex') is not None and r['catalogZeroBasedIndex']!=ids.index(sid): raise SystemExit(f'FAIL active-hold position {sid}/{loc}')
    selected=rjl(inp/'selected-sources.jsonl'); contexts=rjl(inp/'source-contexts.jsonl'); cells=rjl(inp/'candidate-free-cells.jsonl')
    if len(selected)!=20 or len(contexts)!=20 or len(cells)!=240: raise SystemExit('FAIL packet row counts')
    if [r.get('catalogZeroBasedIndex') for r in selected]!=list(range(START,END+1)): raise SystemExit('FAIL selected order')
    prev_after=[r for r in prev_bound if r.get('catalogZeroBasedIndex')==START and r.get('role')=='catalog-after-selected-end']
    if len(prev_after)!=1 or prev_after[0].get('sourceId')!=selected[0].get('sourceId') or prev_after[0].get('sourceSha256')!=selected[0].get('sourceSha256'): raise SystemExit('FAIL W785-to-W805 boundary')
    if prev_sel[-1].get('sourceId')!=ids[804] or selected[0].get('sourceId')!=ids[805]: raise SystemExit('FAIL contiguous predecessor selection')
    boundary=rjl(inp/'selection-boundary.jsonl')
    expected_idx=[804,805,824,825]
    if [r.get('catalogZeroBasedIndex') for r in boundary]!=expected_idx: raise SystemExit('FAIL boundary record indices')
    for i,r in zip(expected_idx,boundary):
        if r.get('sourceId')!=ids[i] or r.get('sourceSha256')!=sha(msgs[ids[i]]['source']): raise SystemExit('FAIL boundary source hash')
    nextrow=rj(inp/'queue-continuity.json')['nextBoundary']
    if nextrow!={'continuationIndex':825,'oneBasedPosition':826,'sourceId':ids[825],'sourceSha256':sha(msgs[ids[825]]['source'])}: raise SystemExit('FAIL next boundary')
    production={p:file_tuple(repo,p,HEAD) for p in prod_paths(repo,HEAD)}
    if len(production)!=rj(inp/'source-file-pins.json').get('productionFilesSearched'): raise SystemExit('FAIL source file inventory count')
    for f in rj(inp/'source-file-pins.json')['files']:
        _,data,blob=file_tuple(repo,f['path'],HEAD)
        if sha(data)!=f['fileSha256'] or blob!=f['gitBlob'] or len(data)!=f['bytes']: raise SystemExit('FAIL source file pin '+f['path'])
    expected_contexts=[]; mismatch=collections.Counter(); callerless=0
    for row in selected:
        sid=row['sourceId']; src=msgs[sid]['source']; sh=sha(src)
        if row.get('sourceSha256')!=sh: raise SystemExit('FAIL selected source hash '+sid)
        expected_contexts.append(match_context({'sourceId':sid,'source':src,'sourceSha256':sh},production,HEAD))
    if [safe_context(c) for c in expected_contexts]!=contexts: raise SystemExit('FAIL caller/source context does not match pinned production tree')
    by_key={(r['sourceId'],r['locale']):r for r in cells}
    if len(by_key)!=240: raise SystemExit('FAIL duplicate cells')
    for srow,ctx in zip(selected,expected_contexts):
        sid=srow['sourceId']; src=msgs[sid]['source']; sh=sha(src)
        if len([c for c in cells if c['sourceId']==sid])!=12: raise SystemExit('FAIL locale cell count '+sid)
        if ctx['callerless']: callerless+=1
        for loc in LOCALES:
            c=by_key.get((sid,loc)); target=msgs[sid].get('translations',{}).get(loc)
            if c is None or not isinstance(target,str) or not target: raise SystemExit(f'FAIL cell target {sid}/{loc}')
            if c.get('sourceSha256')!=sh or c.get('currentTargetSha256')!=sha(target) or c.get('callerContextSha256')!=ctx['contextSha256'] or c.get('literalCallerCount')!=ctx['exactMatchCount'] or c.get('callerless')!=ctx['callerless'] or c.get('candidateFree') is not True: raise SystemExit(f'FAIL cell hash/context {sid}/{loc}')
            if ctx['callerless']:
                if c.get('sourceTextOmitted') is not True or c.get('currentTargetTextOmitted') is not True or any(k in c for k in ('source','currentTarget')): raise SystemExit(f'FAIL callerless cell text leak {sid}/{loc}')
            else:
                if c.get('source')!=src or c.get('currentTarget')!=target: raise SystemExit(f'FAIL caller-backed cell text {sid}/{loc}')
                audit=token_row(src,target)
                if any(c.get(k)!=v for k,v in audit.items()): raise SystemExit(f'FAIL token/protected-literal audit {sid}/{loc}')
                mismatch['placeholder']+=int(not audit['placeholderMultisetMatches']); mismatch['markup']+=int(not audit['markupMatches']); mismatch['numeric']+=int(not audit['numericTokensPreserved']); mismatch['numericPresentationDifferences']+=int(audit['numericPresentationEquivalent']); mismatch['protectedLiteral']+=int(not audit['protectedLiteralsPreserved'])
    holdcells=callerless*12
    summary=rj(inp/'candidate-free-token-summary.json')
    expected_summary={'callerBackedCellCount':240-holdcells,'callerlessCellCount':holdcells,'tokenAuditedCellCount':240-holdcells,**dict(mismatch)}
    if summary!=expected_summary: raise SystemExit('FAIL token summary')
    if manifest.get('priorActiveHashOnlyHoldsCopiedByteForByte')!=1060 or manifest.get('resultingActiveHashOnlyHolds')!=1060+holdcells: raise SystemExit('FAIL active hold manifest counts')
    if manifest.get('currentTokenMismatchCounts')!=dict(mismatch) or manifest.get('callerlessHashOnlyCells')!=holdcells: raise SystemExit('FAIL manifest audit summary')
    if manifest.get('proposedTargetsIncluded') is not False or manifest.get('reviewDecisionsIncluded') is not False: raise SystemExit('FAIL candidate-free boundary')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':WINDOW,'cellCount':len(cells),'callerBackedCells':240-holdcells,'callerlessHashOnlyCells':holdcells,'activePriorHashOnlyHoldsCopiedByteForByte':len(holds),'resultingActiveHashOnlyHolds':1060+holdcells,'tokenAuditMismatchCounts':dict(mismatch),'nextBoundary':nextrow,'checksummedFiles':len(root_sums)},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
