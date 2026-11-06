#!/usr/bin/env python3
"""Portable exact-pin, source/context, token, lineage, and checksum verifier."""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, subprocess, sys
HERE=pathlib.Path(__file__).resolve().parent
HEAD='872905926887840025ba4c3f17151b96f8d3e6e2'
TREE='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight']
FORBIDDEN={'proposedTarget','selectedTarget','disposition','rationale','primaryDisposition','blindDisposition','decision'}
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
def fail(m): raise SystemExit('FAIL: '+m)
def need(v,m):
    if not v: fail(m)
def sha(b):
    if isinstance(b,str): b=b.encode()
    return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def j(name): return json.loads((HERE/name).read_text(encoding='utf-8'))
def jl(name): return [json.loads(x) for x in (HERE/name).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def protected(s):
    out=[x for x in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',s)]
    if re.search(r'(?<![A-Za-z0-9])DATs?(?![A-Za-z0-9])',s) and 'DAT' not in out: out.append('DAT')
    return sorted(set(out))
def tokens(s): return {'placeholders':PH.findall(s),'markup':TAG.findall(s),'numbers':NUM.findall(s),'protectedLiterals':protected(s)}
def safe(v,where='input'):
    if isinstance(v,dict):
        bad=FORBIDDEN.intersection(v)
        need(not bad,'candidate/decision fields in '+where+': '+repr(sorted(bad)))
        for k,x in v.items(): safe(x,where+'.'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v): safe(x,f'{where}[{i}]')
def check_sums(root,filename):
    sums=root/filename; rows={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split('  ',1); p=(root/name).resolve()
        need(p.is_relative_to(root.resolve()) and p.is_file(),'unsafe/missing checksum path '+name)
        need(sha(p.read_bytes())==digest,'checksum '+name)
        need(name not in rows,'duplicate checksum '+name); rows[name]=digest
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}
    need(set(rows)==actual,'checksum coverage')
    return rows
def production_paths(repo):
    raw=git(repo,'ls-files','-z','--','romarr').split(b'\0'); out=[]
    for b in raw:
        if not b: continue
        rel=b.decode(); p=pathlib.Path(rel); parts=rel.lower().split('/')
        if p.suffix.lower() not in ('.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx'): continue
        if any(x in parts for x in ('test','tests','__pycache__')) or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
        out.append(rel)
    return sorted(out)
def make_context(item,files):
    src=item['source']; sid=item['sourceId']; found=[]
    variants=list(dict.fromkeys([json.dumps(src,ensure_ascii=False),repr(src),'"'+src+'"',chr(39)+src+chr(39),chr(96)+src+chr(96)]))
    for rel,(text,b,blob) in files.items():
        occ={}; lines=text.splitlines()
        for literal in variants:
            pos=0
            while True:
                at=text.find(literal,pos)
                if at<0: break
                occ.setdefault(at,'exact quoted source literal'); pos=at+max(1,len(literal))
        pos=0
        while True:
            at=text.find(sid,pos)
            if at<0: break
            occ.setdefault(at,'exact source ID reference'); pos=at+len(sid)
        for hit in re.finditer(r'>[ \t]*'+re.escape(src)+r'[ \t]*<',text): occ.setdefault(hit.start(),'exact HTML text node')
        for at,kind in sorted(occ.items()):
            line=text.count('\n',0,at)+1; lo=max(1,line-3); hi=min(len(lines),line+3)
            excerpt=[{'line':i,'text':lines[i-1]} for i in range(lo,hi+1)]
            line_text=lines[line-1] if line<=len(lines) else ''
            found.append({'path':rel,'line':line,'lineText':line_text,'lineSha256':sha(line_text),'excerpt':excerpt,'excerptSha256':sha(canon(excerpt)),'fileSha256':sha(b),'gitBlob':blob,'matchKind':kind})
    found.sort(key=lambda x:(x['path'],x['line'],x['matchKind']))
    core={'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256'],'searchMethod':'exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code; tests/docs/catalog files excluded','productionFilesSearched':len(files),'exactMatchCount':len(found),'callerless':not found,'callers':found}
    return {**core,'contextSha256':sha(canon(core))}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True); a=ap.parse_args(); repo=a.repo.resolve()
    check_sums(HERE,'SHA256SUMS.txt')
    manifest=j('manifest.json')
    listed={x['path'] for x in manifest.get('files',[])}
    actual={p.name for p in HERE.iterdir() if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
    need(listed==actual,'input manifest file coverage')
    need((manifest.get('head'),manifest.get('tree'),manifest.get('window'),manifest.get('sourceCount'),manifest.get('cellCount'))==(HEAD,TREE,'W605-W624',20,240),'manifest exact pin/counts')
    safe(manifest)
    for p in sorted(HERE.glob('*.json'))+sorted(HERE.glob('*.jsonl')):
        safe(json.loads(p.read_text(encoding='utf-8')) if p.suffix=='.json' else [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()],p.name)
    need(git(repo,'rev-parse','HEAD').decode().strip()==HEAD,'repo HEAD')
    need(git(repo,'rev-parse','HEAD^{tree}').decode().strip()==TREE,'repo tree')
    need(not git(repo,'status','--porcelain=v1','--untracked-files=all').decode().strip(),'repo not clean')
    need(not git(repo,'branch','--show-current').decode().strip(),'repo not detached')
    refs=git(repo,'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head').decode()
    refmap={line.split('\t')[1]:line.split('\t')[0] for line in refs.splitlines() if line.strip()}
    need(refmap.get(f'refs/heads/{BRANCH}')==HEAD and refmap.get('refs/pull/70/head')==HEAD,'live branch/pull refs')
    pins=j('catalog-file-pins.json'); need((pins.get('commit'),pins.get('tree'))==(HEAD,TREE),'catalog pin file')
    for row in j('source-file-pins.json')['files']:
        p=repo/row['path']; need(p.is_file() and sha(p.read_bytes())==row['fileSha256'],'source-file SHA '+row['path'])
        need(git(repo,'rev-parse',f'{HEAD}:{row["path"]}').decode().strip()==row['gitBlob'],'source-file Git blob '+row['path'])
    catpath=pins['catalogPath']; catbytes=(repo/catpath).read_bytes(); cat=json.loads(catbytes); msgs=cat['messages']; ids=list(msgs)
    need(sha(catbytes)==pins['catalogSha256'],'catalog SHA')
    need(len(msgs)==1836 and sha('\n'.join(ids)+'\n')==pins['catalogKeyOrderSha256'],'catalog key order/count')
    registry=json.loads((repo/pins['sourceQueuePath']).read_text(encoding='utf-8'))['messages']; reg={x['id']:x for x in registry}
    snapshot=json.loads((repo/pins['sourceSnapshotPath']).read_text(encoding='utf-8'))
    need(len(registry)==479 and len(reg)==479 and all(snapshot.get(x['id'])==x['sourceHash'] for x in registry),'source registry/snapshot')
    need(j('source-snapshot.json')=={x['id']:x['sourceHash'] for x in registry},'packet source snapshot')
    need(sha(canon({x['id']:x['sourceHash'] for x in registry}))==pins['sourceSnapshotSha256'],'source snapshot digest')
    selection=j('selection.json'); need(selection['positions']==[605,624] and selection['localeOrder']==LOCALES,'selection basis/locales')
    selected=jl('source-inventory-selection.jsonl'); need(len(selected)==20,'selected source rows')
    need([x['catalogZeroBasedIndex'] for x in selected]==list(range(605,625)),'selected insertion positions')
    need([x['sourceId'] for x in selected]==ids[605:625],'selected source key order')
    contexts=jl('source-contexts.jsonl'); need(len(contexts)==20,'caller context rows')
    source_by={x['sourceId']:x for x in selected}; context_by={x['sourceId']:x for x in contexts}
    paths=production_paths(repo); files={}
    for rel in paths:
        b=(repo/rel).read_bytes()
        try: text=b.decode()
        except UnicodeDecodeError: text=b.decode('utf-8','replace')
        files[rel]=(text,b,git(repo,'rev-parse',f'{HEAD}:{rel}').decode().strip())
    for c in contexts:
        item=source_by[c['sourceId']]
        need(make_context(item,files)==c,'exact caller context '+c['sourceId'])
    cells=jl('current-target-cells.jsonl'); need(len(cells)==240,'current cell count')
    need(len({(x['sourceId'],x['locale']) for x in cells})==240,'current cell uniqueness')
    counters=collections.Counter(); presentation=0
    for c in cells:
        sid=c['sourceId']; loc=c['locale']; m=msgs[sid]; src=m['source']; target=m['translations'][loc]; st=tokens(src); tt=tokens(target)
        need(loc in LOCALES and ids[c['catalogZeroBasedIndex']]==sid and sha(src)==c['sourceSha256'],'cell source/key')
        need(target==c['currentTarget'] and sha(target)==c['currentTargetSha256'],'current target hash')
        need(c['position']==c['catalogZeroBasedIndex'] and c['catalogZeroBasedIndex']==ids.index(sid),'cell catalog position')
        need(c['callerContextSha256']==context_by[sid]['contextSha256'],'caller context hash')
        need(c['sourcePlaceholderTokens']==st['placeholders'] and c['sourceMarkupTags']==st['markup'] and c['sourceNumericTokens']==st['numbers'] and c['sourceProtectedLiterals']==st['protectedLiterals'],'cell source token lists')
        ph=collections.Counter(st['placeholders'])==collections.Counter(tt['placeholders']); tags=collections.Counter(st['markup'])==collections.Counter(tt['markup'])
        sn=collections.Counter(st['numbers']); tn=collections.Counter(tt['numbers']); extra=list((tn-sn).elements())
        numeq=bool(re.search(r'\bzero\b',src,re.I) and not st['numbers'] and extra==['0'])
        numok=not(sn-tn) and (not extra or numeq); missing=[x for x in st['protectedLiterals'] if x not in target]
        need(c['placeholderMultisetMatches']==ph and c['markupMatches']==tags and c['numericTokensPreserved']==numok and c['missingProtectedLiterals']==missing and c['containsCandidate'] is False,'cell token/candidate flags')
        counters['placeholder']+=not ph; counters['markup']+=not tags; counters['numeric']+=not numok; counters['protectedLiteral']+=bool(missing); counters['missingTarget']+=not isinstance(target,str)
        presentation+=numeq
    mismatch=j('current-target-token-mismatches.json')
    need(mismatch=={'placeholder':counters['placeholder'],'markup':counters['markup'],'numeric':counters['numeric'],'numericPresentationDifferences':presentation,'protectedLiteral':counters['protectedLiteral'],'missingTarget':counters['missingTarget']},'token mismatch summary')
    prior_sel=jl('prior-selection-reattestation.jsonl'); prior_hold=jl('prior-hold-reattestation.jsonl'); prior_applied=jl('prior-applied-cell-reattestation.jsonl')
    need(len(prior_sel)==220 and len({x['sourceId'] for x in prior_sel})==220,'prior selected-source lineage')
    for x in prior_sel:
        m=msgs.get(x['sourceId']); need(m is not None and sha(m['source'])==x['currentSourceSha256']==x['priorSourceSha256'],'prior selected source hash')
    need(len(prior_hold)==628 and len({(x['sourceId'],x['locale']) for x in prior_hold})==628,'prior hold lineage')
    for x in prior_hold:
        m=msgs[x['sourceId']]; need(sha(m['source'])==x['sourceSha256'] and sha(m['translations'][x['locale']])==x['currentTargetSha256']==x['priorTargetSha256'],'prior hold current hash')
    need(len(prior_applied)==71 and len({(x['sourceId'],x['locale']) for x in prior_applied})==71,'prior applied lineage')
    for x in prior_applied:
        m=msgs[x['sourceId']]; need(sha(m['source'])==x['sourceSha256'] and sha(m['translations'][x['locale']])==x['currentTargetSha256']==x['priorSelectedTargetSha256'],'prior applied current hash')
    for name,win,changed,held in [('prior-window-cell-hash-reattestation.jsonl','W545-W564',2,12),('prior-w565-window-cell-hash-reattestation.jsonl','W565-W584',1,40),('prior-w585-window-cell-hash-reattestation.jsonl','W585-W604',22,24)]:
        rows=jl(name); need(len(rows)==240 and all(x['priorWindow']==win for x in rows),'prior readback count/window '+win)
        need(sum(bool(x.get('applicationChanged')) for x in rows)==changed and sum(bool(x.get('held')) for x in rows)==held,'prior readback changed/hold counts '+win)
        for x in rows:
            m=msgs[x['sourceId']]; need(sha(m['source'])==x['sourceSha256'] and sha(m['translations'][x['locale']])==x['currentTargetSha256'],'prior readback current hash '+win)
    w585=[x for x in jl('prior-w585-window-cell-hash-reattestation.jsonl') if x.get('held')]
    need(len(w585)==24 and all(x['priorWindow']=='W585-W604' for x in w585),'W585 callerless holds carried')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'selectedSources':20,'cells':240,'callerlessSources':sum(x['callerless'] for x in contexts),'callerlessCells':12*sum(x['callerless'] for x in contexts),'directCallerRefs':sum(x['exactMatchCount'] for x in contexts),'priorSelectedSources':len(prior_sel),'priorHolds':len(prior_hold),'priorAppliedCells':len(prior_applied),'priorWindowReadbacks':[240,240,240],'W585CallerlessHolds':len(w585),'sourcePins':'PASS','callerContexts':'PASS','tokenMismatches':dict(counters)},sort_keys=True))
if __name__=='__main__': main()
