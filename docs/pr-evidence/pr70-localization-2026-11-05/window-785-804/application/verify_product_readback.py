#!/usr/bin/env python3
import hashlib,json,subprocess
from pathlib import Path

APP=Path(__file__).resolve().parent
WINDOW=APP.parent
REPO=Path(__file__).resolve().parents[5]
CAT='romarr/ui-labels.json'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def git_bytes(rev,path): return subprocess.check_output(['git','-C',str(REPO),'show',f'{rev}:{path}'])
def jl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def main():
    pin=json.loads((APP/'product-commit.json').read_text())
    readback=json.loads((APP/'readback.json').read_text())
    before=json.loads(git_bytes(pin['inputHead'],CAT))
    after_bytes=git_bytes(pin['productCommit'],CAT)
    after=json.loads(after_bytes)
    assert git('rev-parse',f"{pin['productCommit']}^")==pin['inputHead']
    assert git('rev-parse',f"{pin['productCommit']}^{{tree}}")==pin['productTree']
    assert git('rev-parse',f"{pin['inputHead']}^{{tree}}")==pin['inputTree']
    assert git('diff-tree','--no-commit-id','--name-only','-r',pin['productCommit']).splitlines()==[CAT]
    assert sha(after_bytes)==pin['catalogSha256']==readback['catalogSha256After']
    assert list(before['messages'])==list(after['messages'])
    selected=jl(WINDOW/'root-adjudication/selected-targets.jsonl')
    candidate=jl(WINDOW/'candidate-free/input/candidate-free-cells.jsonl')
    ledger=jl(APP/'readback-240.jsonl')
    assert (len(selected),len(candidate),len(ledger))==(31,240,240)
    sm={(r['position'],r['locale']):r for r in selected}
    cm={(r['position'],r['locale']):r for r in candidate}
    rm={(r['position'],r['locale']):r for r in ledger}
    changed=[]
    for key,c in cm.items():
        r=rm[key]; sid,locale=c['sourceId'],c['locale']
        old=before['messages'][sid]['translations'][locale]
        new=after['messages'][sid]['translations'][locale]
        assert r['sourceId']==sid and r['sourceSha256']==c['sourceSha256']
        assert r['beforeTargetSha256']==sha(old) and r['afterTargetSha256']==sha(new)
        if key in sm:
            s=sm[key]
            assert r['applied'] is True and r['rootDisposition']==s['rootDisposition']
            assert old==s['currentTarget'] and new==s['rootTarget']
            assert sha(old)==s['currentTargetSha256'] and sha(new)==s['rootTargetSha256']
            changed.append(key)
        else:
            assert r['applied'] is False and old==new
            if c.get('callerless'):
                assert r.get('textOmitted') is True and 'source' not in r and 'afterTarget' not in r
            else:
                assert r['source']==c['source'] and r['currentTarget']==c['currentTarget'] and r['afterTarget']==new
    assert len(changed)==31 and set(changed)==set(sm)
    for locale in LOCALES:
        assert all(m['translations'].get(locale) for m in after['messages'].values())
    assert readback['readbackCellCount']==240 and readback['changedCellCount']==31
    assert readback['nativeSpeakerApproval'] is False and readback['headedBrowserReviewPerformed'] is False
    rows_bytes=(APP/'readback-240.jsonl').read_bytes()
    assert sha(rows_bytes)==readback['readbackRowsSha256']
    print(json.dumps({'result':'PASS','inputHead':pin['inputHead'],'productCommit':pin['productCommit'],'productTree':pin['productTree'],'changedCatalog':CAT,'changedCells':31,'readbackCells':240,'allOtherCellsUnchanged':True,'catalogOrderPreserved':True,'localeCount':12,'messagesPerLocale':1836,'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
