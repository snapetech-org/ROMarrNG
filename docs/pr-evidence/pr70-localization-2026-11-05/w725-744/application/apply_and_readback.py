#!/usr/bin/env python3
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
TASK = Path(__file__).resolve().parents[1]
ROOT = TASK/'root-adjudication'
CF = TASK/'candidate-free'/'input'
REPO_DEFAULT = Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='c3f92c45b4b4f8d79a8caa99417f9970ebc42a26'
TREE='3f835643e4f557999d533c3e832fc92036d4b01a'
CAT_REL='romarr/ui-labels.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def jlines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def token_ok(source,target,protected):
    patterns=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
    return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in patterns) and all(x in target for x in protected)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,default=REPO_DEFAULT); a=ap.parse_args(); repo=a.repo.resolve()
    assert git(repo,'rev-parse','HEAD')==HEAD and git(repo,'rev-parse','HEAD^{tree}')==TREE
    assert git(repo,'status','--porcelain=v1','--untracked-files=all')=='', 'worktree must be clean before application'
    cat=repo/CAT_REL; before=cat.read_bytes()
    assert before==subprocess.check_output(['git','-C',str(repo),'show',f'HEAD:{CAT_REL}'])
    data=json.loads(before); canonical=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    assert before==canonical, 'catalog formatting differs from the pinned exact-head file'
    candidates={(r['position'],r['locale']):r for r in jlines(CF/'candidate-free-cells.jsonl')}
    selections=jlines(ROOT/'selected-targets.jsonl')
    assert len(candidates)==240 and len(selections)==5
    changes=[]
    for r in selections:
        k=(r['position'],r['locale']); c=candidates[k]
        assert c['sourceId']==r['sourceId'] and c['source']==r['source'] and c['currentTarget']==r['currentTarget']
        assert c['sourceSha256']==r['sourceSha256'] and c['currentTargetSha256']==r['currentTargetSha256']
        assert c['callerContextSha256']==r['callerContextSha256']
        assert tsha(c['source'])==c['sourceSha256'] and tsha(c['currentTarget'])==c['currentTargetSha256']
        assert tsha(r['rootTarget'])==r['rootTargetSha256']
        assert token_ok(c['source'],r['rootTarget'],c['sourceProtectedLiterals'])
        entry=data['messages'][r['sourceId']]
        old=entry['translations'][r['locale']]
        assert old==c['currentTarget'] and tsha(old)==r['currentTargetSha256']
        entry['translations'][r['locale']]=r['rootTarget']
        changes.append({'position':r['position'],'locale':r['locale'],'sourceId':r['sourceId'],
          'before':old,'beforeSha256':tsha(old),'after':r['rootTarget'],'afterSha256':tsha(r['rootTarget']),
          'rootDisposition':r['rootDisposition'],'callerContextSha256':r['callerContextSha256']})
    out=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    cat.write_bytes(out); result=json.loads(cat.read_text(encoding='utf-8'))
    assert list(result['messages'])==list(json.loads(before)['messages'])
    olddata=json.loads(before); changed=[]
    for sid,entry in olddata['messages'].items():
        for locale,old in entry['translations'].items():
            new=result['messages'][sid]['translations'][locale]
            if new!=old: changed.append((sid,locale,old,new))
    assert len(changed)==5 and {(sid,loc) for sid,loc,_,_ in changed}=={(r['sourceId'],r['locale']) for r in selections}
    for r in selections: assert result['messages'][r['sourceId']]['translations'][r['locale']]==r['rootTarget']
    locales=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
    for locale in locales:
        assert all(locale in m['translations'] and m['translations'][locale] for m in result['messages'].values())
    readback={
      'artifact':'ROMarrNG PR #70 W725-W744 product application readback',
      'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W725-W744',
      'inputHead':HEAD,'inputTree':TREE,'changedCatalogPath':CAT_REL,
      'changedCellCount':len(changes),'expectedChangedCellCount':5,
      'catalogKeyOrderPreserved':True,'allOtherCatalogCellsUnchanged':True,
      'all12DirectLocalesHave1836NonemptyMessages':True,'localeCount':12,'messageCountPerLocale':1836,
      'candidateFreeInputSha256':sha((CF/'candidate-free-cells.jsonl').read_bytes()),
      'targetReadback':changes,'catalogSha256After':sha(out),
      'productDiffNames':[CAT_REL], 'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False,
      'productCommitPending':True
    }
    dest=TASK/'application'/'readback-before-commit.json'
    dest.write_text(json.dumps(readback,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'changedCellCount':5,'catalogSha256After':readback['catalogSha256After'],
      'localeCount':12,'messagesPerLocale':1836,'catalogKeyOrderPreserved':True,
      'allOtherCatalogCellsUnchanged':True,'readback':str(dest)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
