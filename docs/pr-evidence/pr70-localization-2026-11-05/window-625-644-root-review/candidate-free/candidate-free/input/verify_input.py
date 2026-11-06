#!/usr/bin/env python3
from __future__ import annotations
import argparse,collections,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEAD='5860fce5d546a772b1df995f8f6321c083ed7d5d'; TREE='561835895972a62e9d3b1f2bfe9bcba01187eb98'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight']
def sha(b): return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def need(v,s):
    if not v: raise SystemExit('FAIL: '+s)
def protected(s):
    out=[t for t in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',s)]
    if re.search(r'(?<![A-Za-z0-9])DATs?(?![A-Za-z0-9])',s) and 'DAT' not in out: out.append('DAT')
    return sorted(set(out))
def tokens(s): return {'placeholders':PH.findall(s),'markup':TAG.findall(s),'numbers':NUM.findall(s),'protectedLiterals':protected(s)}
def check_sums(root,name):
    listed={}
    for line in (root/name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); p=(root/n).resolve(); need(p.is_relative_to(root.resolve()) and p.is_file() and sha(p.read_bytes())==h,'checksum '+n); need(n not in listed,'duplicate checksum '+n); listed[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/name}
    need(set(listed)==actual,'checksum coverage '+str(root)); return listed
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); a=ap.parse_args(); repo=a.repo.resolve()
    check_sums(ROOT,'SHA256SUMS.txt')
    need(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==HEAD,'repository HEAD')
    need(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD^{tree}'],text=True).strip()==TREE,'repository tree')
    need(not subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1','--untracked-files=all'],text=True).strip(),'repository worktree dirty')
    need(not subprocess.check_output(['git','-C',str(repo),'branch','--show-current'],text=True).strip(),'repository not detached')
    m=j(ROOT/'manifest.json'); pins=j(ROOT/'catalog-file-pins.json'); att0=j(ROOT/'PR-attestation-before.json'); att1=j(ROOT/'PR-attestation-after-candidate-free.json')
    need((m.get('repository'),m.get('pullRequest'),m.get('head'),m.get('tree'),m.get('window'))==('snapetech-org/ROMarrNG',70,HEAD,TREE,'W625-W644'),'input manifest pin')
    need((att0.get('head'),att0.get('tree'),att1.get('head'),att1.get('tree'))==(HEAD,TREE,HEAD,TREE),'PR attestations')
    for k in ('head','tree','branchRefOid','pullRefOid','bodySha256','bodyBytes','baseApiSha','baseLiveRefOid'):
        need(att0.get(k)==att1.get(k),'PR attestation changed '+k)
    need((att0.get('state'),att0.get('draft'),att0.get('merged'),att0.get('branchRefOid'),att0.get('pullRefOid'))==('OPEN',True,False,HEAD,HEAD),'PR state/refs')
    catalog=repo/'romarr/ui-labels.json'; doc=j(catalog); messages=doc['messages']; ids=list(messages)
    need(len(ids)==1836 and sha(catalog.read_bytes())==pins['catalogSha256']==m['catalogSha256'],'catalog hash/count')
    need(subprocess.check_output(['git','-C',str(repo),'rev-parse',f'{HEAD}:romarr/ui-labels.json'],text=True).strip()==pins['catalogGitBlob'],'catalog blob')
    need(sha('\n'.join(ids)+'\n')==pins['catalogKeyOrderSha256'],'catalog key order')
    selected=lines(ROOT/'source-inventory-selection.jsonl'); need(len(selected)==20,'selected source count')
    expected=ids[625:645]; need([x['sourceId'] for x in selected]==expected,'source insertion order/window')
    for i,x in enumerate(selected,625):
        msg=messages[x['sourceId']]; need((x['position'],x['catalogZeroBasedIndex'],x['source'],x['sourceSha256'])==(i,i,msg['source'],sha(msg['source'])),'selected source row')
    contexts=lines(ROOT/'source-contexts.jsonl'); need(len(contexts)==20 and {x['sourceId'] for x in contexts}==set(expected),'source context coverage')
    for c in contexts:
        core={k:c[k] for k in ('sourceId','source','sourceSha256','head','searchMethod','productionFilesSearched','exactMatchCount','callerless','callers')}
        need(c['sourceSha256']==sha(c['source']) and c['contextSha256']==sha(canon(core)),'source context hash')
        need(c['callerless']==(c['exactMatchCount']==0)==(len(c['callers'])==0),'callerless flag')
        for r in c['callers']:
            p=repo/r['path']; need(p.is_file(),'caller file '+r['path']); data=p.read_bytes(); txt=data.decode('utf-8','replace'); ll=txt.splitlines(); line=r['line']
            need(sha(data)==r['fileSha256'] and subprocess.check_output(['git','-C',str(repo),'rev-parse',f'{HEAD}:{r["path"]}'],text=True).strip()==r['gitBlob'],'caller file pin')
            need(1<=line<=len(ll) and sha(ll[line-1])==r['lineSha256'],'caller line hash')
            lo=max(1,line-3); hi=min(len(ll),line+3); ex=[{'line':i,'text':ll[i-1]} for i in range(lo,hi+1)]
            need(sha(canon(ex))==r['excerptSha256'] and ex==r['excerpt'],'caller excerpt')
    cells=lines(ROOT/'current-target-cells.jsonl'); need(len(cells)==240 and len({(x['sourceId'],x['locale']) for x in cells})==240,'target cell coverage')
    ctxmap={x['sourceId']:x for x in contexts}
    for c in cells:
        msg=messages[c['sourceId']]; loc=c['locale']; src=msg['source']; target=msg.get('translations',{}).get(loc)
        need(loc in LOCALES and isinstance(target,str),'current target present')
        need(c['currentTarget']==target and c['currentTargetSha256']==sha(target),'current target hash')
        st=tokens(src); tt=tokens(target)
        need(c['sourceSha256']==sha(src) and c['callerContextSha256']==ctxmap[c['sourceId']]['contextSha256'],'cell source/context hash')
        need(c['sourcePlaceholderTokens']==st['placeholders'] and c['currentPlaceholderTokens']==tt['placeholders'] and c['placeholderMultisetMatches']==(collections.Counter(st['placeholders'])==collections.Counter(tt['placeholders'])),'placeholder integrity')
        need(c['sourceMarkupTags']==st['markup'] and c['currentMarkupTags']==tt['markup'] and c['markupMatches']==(collections.Counter(st['markup'])==collections.Counter(tt['markup'])),'markup integrity')
        need(c['sourceNumericTokens']==st['numbers'] and c['currentNumericTokens']==tt['numbers'],'numeric token inventory')
        need(c['sourceProtectedLiterals']==st['protectedLiterals'] and c['containsCandidate'] is False,'candidate-free/token inventory')
        need('proposedTarget' not in c and 'disposition' not in c,'candidate/decision leaked')
    need(m.get('cellCount')==240 and m.get('sourceCount')==20 and m.get('localeCount')==12,'window counts')
    need(m.get('candidateFree') is True and m.get('proposedTargetsIncluded') is False and m.get('reviewDecisionsIncluded') is False,'candidate-free declaration')
    for fn,n in [('prior-selection-reattestation.jsonl',240),('prior-hold-reattestation.jsonl',664),('prior-applied-cell-reattestation.jsonl',73),('prior-window-cell-hash-reattestation.jsonl',240),('prior-w565-window-cell-hash-reattestation.jsonl',240),('prior-w585-window-cell-hash-reattestation.jsonl',240),('prior-w605-window-cell-hash-reattestation.jsonl',240)]:
        rows=lines(ROOT/fn); need(len(rows)==n,fn+' count')
    for r in lines(ROOT/'prior-selection-reattestation.jsonl'):
        msg=messages[r['sourceId']]; need(sha(msg['source'])==r['currentSourceSha256'],'prior selected source reattestation')
    for r in lines(ROOT/'prior-hold-reattestation.jsonl'):
        msg=messages[r['sourceId']]; need(sha(msg['source'])==r['sourceSha256'] and sha(msg['translations'][r['locale']])==r['currentTargetSha256']==r['priorTargetSha256'],'prior hold reattestation')
    for r in lines(ROOT/'prior-applied-cell-reattestation.jsonl'):
        msg=messages[r['sourceId']]; need(sha(msg['source'])==r['sourceSha256'] and sha(msg['translations'][r['locale']])==r['currentTargetSha256']==r['priorSelectedTargetSha256'],'prior application reattestation')
    for fn in ['prior-window-cell-hash-reattestation.jsonl','prior-w565-window-cell-hash-reattestation.jsonl','prior-w585-window-cell-hash-reattestation.jsonl','prior-w605-window-cell-hash-reattestation.jsonl']:
        for r in lines(ROOT/fn):
            msg=messages[r['sourceId']]; need(sha(msg['source'])==r['sourceSha256'] and sha(msg['translations'][r['locale']])==r['currentTargetSha256'],'prior readback reattestation')
    main=j(ROOT/'main-context-drift.json'); need((main['prHead'],main['prTree'])==(HEAD,TREE) and main['selectedSourceCount']==20,'main context comparison pin')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':'W625-W644','sources':20,'cells':240,'callerlessSources':m['callerlessSourceCount'],'callerlessCells':m['callerlessCurrentTargetCellCount'],'priorSelected':m['priorSelectedSourceCount'],'priorHolds':m['priorHoldCellCount'],'priorApplied':m['priorAppliedSelectedCellCount'],'mainHead':main['mainHead'],'mainContextDrift':main['sourcesWithCallerContextDrift'],'candidateFree':True},sort_keys=True))
if __name__=='__main__': main()
