#!/usr/bin/env python3
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path

TASK=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[1]/'root-adjudication'
CF=Path(__file__).resolve().parents[1]/'candidate-free'/'input'
REPO_DEFAULT=Path(__file__).resolve().parents[5]
HEAD='bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
TREE='fbf9ada4b4fd43a288ce498b24990312f0c32f22'
CAT_REL='romarr/ui-labels.json'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def sha(data):
    if isinstance(data,str): data=data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()
def jlines(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def token_ok(source,target,protected):
    patterns=[r'\{[^{}]+\}',r'</?[A-Za-z][^>]*>',r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])']
    return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in patterns) and all(x in target for x in protected)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,default=REPO_DEFAULT)
    a=ap.parse_args(); repo=a.repo.resolve()
    assert git(repo,'rev-parse','HEAD')==HEAD
    assert git(repo,'rev-parse','HEAD^{tree}')==TREE
    assert git(repo,'status','--porcelain=v1','--untracked-files=all')=='','product worktree must be clean before application'
    cat=repo/CAT_REL
    before=cat.read_bytes()
    assert before==subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{CAT_REL}'])
    original=json.loads(before)
    assert before==(json.dumps(original,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    data=json.loads(before)
    candidate={(r['position'],r['locale']):r for r in jlines(CF/'candidate-free-cells.jsonl')}
    selections=jlines(ROOT/'selected-targets.jsonl')
    assert len(candidate)==240 and len(selections)==31
    changes=[]
    for r in selections:
        key=(r['position'],r['locale']); c=candidate[key]
        assert (c['sourceId'],c['source'],c['currentTarget'])==(r['sourceId'],r['source'],r['currentTarget'])
        assert (c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256'])==(r['sourceSha256'],r['currentTargetSha256'],r['callerContextSha256'])
        assert sha(c['source'])==c['sourceSha256'] and sha(c['currentTarget'])==c['currentTargetSha256']
        assert sha(r['rootTarget'])==r['rootTargetSha256']
        assert token_ok(c['source'],r['rootTarget'],c['sourceProtectedLiterals'])
        entry=data['messages'][r['sourceId']]
        old=entry['translations'][r['locale']]
        assert old==c['currentTarget']
        entry['translations'][r['locale']]=r['rootTarget']
        changes.append({
            'position':r['position'],'locale':r['locale'],'sourceId':r['sourceId'],
            'sourceSha256':r['sourceSha256'],'currentTarget':old,
            'currentTargetSha256':sha(old),'rootTarget':r['rootTarget'],
            'rootTargetSha256':sha(r['rootTarget']),'rootDisposition':r['rootDisposition'],
            'callerContextSha256':r['callerContextSha256'],
            'integratedTargetSource':r['integratedTargetSource'],
            'confidence':r['confidence'],'nativeSpeakerApproval':False
        })
    out=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    cat.write_bytes(out)
    result=json.loads(cat.read_text(encoding='utf-8'))
    assert list(result['messages'])==list(original['messages'])
    changed=[]
    for sid,entry in original['messages'].items():
        for locale,old in entry['translations'].items():
            new=result['messages'][sid]['translations'][locale]
            if new!=old: changed.append((sid,locale,old,new))
    assert len(changed)==31
    assert {(sid,loc) for sid,loc,_,_ in changed}=={(r['sourceId'],r['locale']) for r in selections}
    for r in selections:
        assert result['messages'][r['sourceId']]['translations'][r['locale']]==r['rootTarget']
    assert all(all(locale in m['translations'] and m['translations'][locale] for m in result['messages'].values()) for locale in LOCALES)
    readback={
        'artifact':'ROMarrNG PR #70 W785-W804 product application readback before commit',
        'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W785-W804',
        'inputHead':HEAD,'inputTree':TREE,'changedCatalogPath':CAT_REL,
        'changedCellCount':len(changes),'expectedChangedCellCount':31,
        'catalogKeyOrderPreserved':True,'allOtherCatalogCellsUnchanged':True,
        'all12DirectLocalesHave1836NonemptyMessages':True,
        'localeCount':12,'messageCountPerLocale':1836,
        'candidateFreeInputSha256':sha((CF/'candidate-free-cells.jsonl').read_bytes()),
        'rootSelectedTargetsSha256':sha((ROOT/'selected-targets.jsonl').read_bytes()),
        'targetReadback':changes,'catalogSha256After':sha(out),
        'productDiffNames':[CAT_REL],
        'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False,
        'productCommitPending':True
    }
    dest=TASK/'readback-before-commit.json'
    dest.write_text(json.dumps(readback,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'changedCellCount':len(changes),'catalogSha256After':readback['catalogSha256After'],'localeCount':12,'messagesPerLocale':1836,'catalogKeyOrderPreserved':True,'allOtherCatalogCellsUnchanged':True,'readback':str(dest)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
