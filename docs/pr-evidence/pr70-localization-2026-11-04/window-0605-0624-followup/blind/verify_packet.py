#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, sys
HERE=Path(__file__).resolve().parent
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CALLERLESS={618,620,623}
LINEAGE=[
'prior-selection-reattestation-summary.json','prior-selection-reattestation.jsonl',
'prior-hold-reattestation-summary.json','prior-hold-reattestation.jsonl',
'prior-applied-cell-reattestation-summary.json','prior-applied-cell-reattestation.jsonl',
'prior-window-cell-hash-reattestation.jsonl','prior-w565-window-cell-hash-reattestation.jsonl',
'prior-w585-window-cell-hash-reattestation.jsonl']
def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def need(x,msg):
    if not x: raise SystemExit('FAIL: '+msg)
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path); a=ap.parse_args()
    sums=HERE/'SHA256SUMS.txt'; listed={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        d,n=line.split('  ',1); p=(HERE/n).resolve()
        need(p.is_relative_to(HERE.resolve()) and p.is_file(),'unsafe/missing file '+n)
        need(sha(p.read_bytes())==d,'checksum '+n); need(n not in listed,'duplicate checksum '+n); listed[n]=d
    actual={p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p!=sums}
    need(set(listed)==actual,'checksum coverage')
    meta=j(HERE/'packet-manifest.json')
    need(meta['head']=='872905926887840025ba4c3f17151b96f8d3e6e2' and meta['tree']=='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4','pinned head/tree')
    rows=jl(HERE/'review.jsonl'); need(len(rows)==240,'cell count')
    need(len({(x['position'],x['locale']) for x in rows})==240,'cell uniqueness')
    need([x['locale'] for x in rows[:12]]==LOCALES,'locale order')
    counts={}; by={(x['position'],x['locale']):x for x in rows}
    for r in rows:
        p=r['position']; loc=r['locale']; need(loc in LOCALES and 605<=p<=624,'cell bounds')
        counts[r['disposition']]=counts.get(r['disposition'],0)+1
        need(r['disposition'] in ('retain_current','propose_clear_improvement','hold_hash_only'),'unknown disposition')
        need(len(r['sourceSha256'])==64 and len(r['currentTargetSha256'])==64 and len(r['inputCellCanonicalSha256'])==64,'cell hash fields')
        if p in CALLERLESS:
            need(r['disposition']=='hold_hash_only' and r.get('callerless') is True,'callerless hold')
            need(not any(k in r for k in ('sourceId','source','currentTarget','proposedTarget','sourceContext','callerRefs')),'callerless text/context leakage')
        else:
            need(r['disposition']!='hold_hash_only','callerful hold')
            need(isinstance(r.get('source'),str) and isinstance(r.get('currentTarget'),str),'missing callerful text')
            need(sha(r['source'])==r['sourceSha256'] and sha(r['currentTarget'])==r['currentTargetSha256'],'source/target hash')
            c=r.get('sourceContext'); need(isinstance(c,dict) and c.get('callerless') is False and c.get('exactMatchCount',0)>0,'caller context missing')
            core={k:v for k,v in c.items() if k!='contextSha256'}
            need(sha(canon(core))==c['contextSha256']==r['callerContextSha256'],'caller context hash')
            need(c['sourceId']==r['sourceId'] and c['source']==r['source'],'source/context mismatch')
            refs=[{'path':z['path'],'line':z['line'],'lineSha256':z['lineSha256'],'excerptSha256':z['excerptSha256'],'fileSha256':z['fileSha256'],'gitBlob':z['gitBlob']} for z in c['callers']]
            need(refs==r['callerRefs'],'caller refs mismatch')
            if r['disposition']=='propose_clear_improvement':
                need(isinstance(r.get('proposedTarget'),str) and sha(r['proposedTarget'])==r['proposedTargetSha256'],'proposal hash')
            else:
                need('proposedTarget' not in r,'proposal on retained cell')
    need(counts=={'retain_current':202,'propose_clear_improvement':2,'hold_hash_only':36},'disposition counts '+repr(counts))
    need(all((p,l) in by and by[(p,l)]['disposition']=='hold_hash_only' for p in CALLERLESS for l in LOCALES),'all callerless cells held')
    for n in LINEAGE:
        need((HERE/'lineage'/n).is_file(),'missing lineage '+n)
    if a.input:
        src=a.input.resolve(); im=j(src/'manifest.json')
        need(im.get('candidateFree') is True and im.get('proposedTargetsIncluded') is False and im.get('reviewDecisionsIncluded') is False,'input is not candidate-free')
        need((im['head'],im['tree'],im['window'],im['cellCount'])==(meta['head'],meta['tree'],'W605-W624',240),'input pin')
        # Verify input bundle checksum coverage and contents.
        inrows={}
        for line in (src/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            d,n=line.split('  ',1); q=(src/n).resolve(); need(q.is_relative_to(src) and q.is_file() and sha(q.read_bytes())==d,'input checksum '+n); inrows[n]=d
        need(set(inrows)=={q.name for q in src.iterdir() if q.is_file() and q.name!='SHA256SUMS.txt'},'input checksum coverage')
        raw=jl(src/'current-target-cells.jsonl'); inp={(x['position'],x['locale']):x for x in raw}
        ictx={x['sourceId']:x for x in jl(src/'source-contexts.jsonl')}
        need(len(inp)==240,'input cell count')
        for r in rows:
            c=inp[(r['position'],r['locale'])]
            need(sha(canon(c))==r['inputCellCanonicalSha256'],'input cell canonical hash')
            need(c['sourceSha256']==r['sourceSha256'] and c['currentTargetSha256']==r['currentTargetSha256'] and c['callerContextSha256']==r['callerContextSha256'],'input hashes match')
            if r['position'] not in CALLERLESS:
                need(c['source']==r['source'] and c['currentTarget']==r['currentTarget'],'input text match')
                need(ictx[c['sourceId']]==r['sourceContext'],'input caller context match')
            else:
                need(ictx[c['sourceId']]['callerless'] is True,'input callerless status')
        for n in LINEAGE:
            need((HERE/'lineage'/n).read_bytes()==(src/n).read_bytes(),'lineage byte copy '+n)
    print(json.dumps({'result':'PASS','head':meta['head'],'tree':meta['tree'],'cells':len(rows),'dispositions':counts,'callerlessHashOnly':True,'inputCompared':bool(a.input),'lineageCopiesChecked':len(LINEAGE)},ensure_ascii=False,sort_keys=True))
if __name__=='__main__': main()
