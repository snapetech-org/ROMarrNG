#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
BASE='872905926887840025ba4c3f17151b96f8d3e6e2'
BASE_TREE='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
BRANCH='task/localization-translation-review-20261030'
EVIDENCE_PATH='docs/pr-evidence/pr70-localization-2026-11-04/window-0605-0624-followup'
CATALOG='romarr/ui-labels.json'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CALLERLESS={618,620,623}
LINEAGE=['prior-selection-reattestation-summary.json','prior-selection-reattestation.jsonl','prior-hold-reattestation-summary.json','prior-hold-reattestation.jsonl','prior-applied-cell-reattestation-summary.json','prior-applied-cell-reattestation.jsonl','prior-window-cell-hash-reattestation.jsonl','prior-w565-window-cell-hash-reattestation.jsonl','prior-w585-window-cell-hash-reattestation.jsonl']
FORBIDDEN={'sourceId','source','currentTarget','beforeTarget','afterTarget','proposedTarget','acceptedTarget','rationale','sourceContext','callerRefs','primaryProposedTarget','blindProposedTarget'}
def sha(x): return hashlib.sha256(x.encode('utf-8') if isinstance(x,str) else x).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def need(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def check_sums(root,name='SHA256SUMS.txt'):
    root=pathlib.Path(root); listed={}; sums=root/name
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,rel=line.split('  ',1); p=(root/rel).resolve()
        need(p.is_relative_to(root.resolve()) and p.is_file(),'unsafe/missing file '+rel)
        need(sha(p.read_bytes())==digest,'checksum '+rel); need(rel not in listed,'duplicate checksum '+rel); listed[rel]=digest
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}
    need(set(listed)==actual,'checksum coverage '+str(root))
    return listed
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def git_bytes(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def main():
    ap=argparse.ArgumentParser(description='Verify the W605-W624 exact-hash application evidence.')
    ap.add_argument('--repo',type=pathlib.Path,required=True,help='ROMarrNG repository containing base and product commits')
    ap.add_argument('--live-pr',action='store_true',help='verify current PR refs/body and clean evidence worktree')
    a=ap.parse_args(); repo=a.repo.resolve()
    root_sums=check_sums(ROOT); manifest=j(ROOT/'manifest.json')
    files={x['path']:x for x in manifest['files']}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p not in (ROOT/'manifest.json',ROOT/'SHA256SUMS.txt')}
    need(set(files)==actual,'manifest file coverage')
    for rel,row in files.items():
        p=ROOT/rel; need(p.stat().st_size==row['bytes'] and sha(p.read_bytes())==row['sha256'],'manifest hash '+rel)
    need(root_sums.get('manifest.json')==sha((ROOT/'manifest.json').read_bytes()),'manifest checksum')
    need((manifest['baseHead'],manifest['baseTree'],manifest['window'])==(BASE,BASE_TREE,'W605-W624'),'base pin')

    cf=ROOT/'candidate-free'; primary=ROOT/'primary'; blind=ROOT/'blind'; cross=ROOT/'cross'; app=ROOT/'application'
    check_sums(cf); check_sums(cf/'candidate-free'/'input'); check_sums(primary); check_sums(primary/'primary-output'); check_sums(blind); check_sums(cross)
    inp=cf/'candidate-free'/'input'; im=j(inp/'manifest.json')
    need(im.get('candidateFree') is True and im.get('reviewDecisionsIncluded') is False and im.get('proposedTargetsIncluded') is False,'candidate-free status')
    need((im['head'],im['tree'],im['window'],im['cellCount'])==(BASE,BASE_TREE,'W605-W624',240),'candidate-free pin')
    need(j(primary/'primary-output'/'primary-manifest.json')['head']==BASE,'primary pin')
    need(j(blind/'packet-manifest.json')['head']==BASE,'blind pin')
    need(j(cross/'packet-manifest.json')['head']==BASE,'cross pin')
    cells=jl(inp/'current-target-cells.jsonl'); contexts={r['sourceId']:r for r in jl(inp/'source-contexts.jsonl')}
    cross_rows=jl(cross/'cross-review.jsonl'); proposals=jl(cross/'proposal-adjudication.jsonl')
    need(len(cells)==len(cross_rows)==240,'upstream readback input count')
    need(j(inp/'prior-selection-reattestation-summary.json')['reattestedSelectedSourceCount']==220,'prior selected count')
    need(j(inp/'prior-hold-reattestation-summary.json')['reattestedCellCount']==628,'prior hold count')
    need(j(inp/'prior-applied-cell-reattestation-summary.json')['reattestedCellCount']==71,'prior applied count')
    prior_w585=[r for r in jl(inp/'prior-w585-window-cell-hash-reattestation.jsonl') if r.get('held')]
    need(len(prior_w585)==24,'prior W585 callerless hold count')

    product=j(app/'product-commit.json'); product_commit=product['productCommit']; product_tree=product['productTree']
    need(product['baseCommit']==BASE and product['productParent']==BASE and product['productPath']==CATALOG,'product parent/path')
    need(git(repo,'rev-parse',product_commit)==product_commit and git(repo,'rev-parse',product_commit+'^{tree}')==product_tree,'product commit/tree exists')
    need(git(repo,'rev-parse',product_commit+'^')==BASE,'product parent')
    paths=git(repo,'diff-tree','--no-commit-id','--name-only','-r',product_commit).splitlines()
    need(paths==[CATALOG],'product commit file scope')
    before_raw=git_bytes(repo,'show',f'{BASE}:{CATALOG}'); after_raw=git_bytes(repo,'show',f'{product_commit}:{CATALOG}')
    need(sha(before_raw)==im['catalogSha256']==j(app/'catalog-pins.json')['preCatalogSha256'],'pre-catalog hash')
    need(sha(after_raw)==j(app/'catalog-pins.json')['postCatalogSha256']==product['catalogSha256'],'post-catalog hash')
    before=json.loads(before_raw.decode('utf-8')); after=json.loads(after_raw.decode('utf-8'))
    need(len(before['messages'])==1836 and list(before['messages'])==list(after['messages']),'catalog key order/count')
    need(list(before['locales'])==list(after['locales']),'locale order')
    expected=json.loads(before_raw.decode('utf-8'))
    accepted={(611,'id'):'Log langsung',(611,'vi'):'Nhật ký trực tiếp'}
    for (pos,loc),target in accepted.items():
        c=next(x for x in cells if x['position']==pos and x['locale']==loc)
        p=next(x for x in proposals if x['position']==pos and x['locale']==loc)
        need(p['outcome']=='accepted_clear_improvement' and p['acceptedTarget']==target,'accepted proposal '+loc)
        item=expected['messages'][c['sourceId']]
        need(item['source']==c['source'] and sha(item['source'])==c['sourceSha256'],'source exactness '+loc)
        old=item['translations'][loc]
        need(old==c['currentTarget'] and sha(old)==c['currentTargetSha256'],'current target exactness '+loc)
        need(sha(target)==p['acceptedTargetSha256'],'proposal target hash '+loc)
        expected['messages'][c['sourceId']]['translations'][loc]=target
    need(after==expected,'catalog changed beyond the two authorized target values')
    need(product['catalogGitBlob']==git(repo,'rev-parse',f'{product_commit}:{CATALOG}'),'catalog blob receipt')

    readback=jl(app/'application-readback.jsonl'); selected=jl(app/'selected-applied.jsonl'); holds=jl(app/'holds.jsonl')
    key=lambda r:(r['position'],r['locale'])
    rb={key(r):r for r in readback}; need(len(readback)==240 and len(rb)==240,'readback count/uniqueness')
    bycell={(r['position'],r['locale']):r for r in cells}; need(set(rb)==set(bycell),'readback cell identity')
    selected_map={key(r):r for r in selected}; need(set(selected_map)==set(accepted) and len(selected)==2,'selected application coverage')
    hold_map={key(r):r for r in holds}; need(len(holds)==36 and len(hold_map)==36,'hash-only hold coverage')
    counts=collections.Counter()
    for k,c in bycell.items():
        r=rb[k]; context=contexts[c['sourceId']]; is_hold=context['callerless']; is_applied=k in accepted
        need(r['inputCellCanonicalSha256']==sha(canon(c)),'input cell row hash '+str(k))
        need(r['sourceSha256']==c['sourceSha256'] and r['beforeTargetSha256']==c['currentTargetSha256'],'source/before hash '+str(k))
        cell_after=after['messages'][c['sourceId']]['translations'][c['locale']]
        need(sha(cell_after)==r['afterTargetSha256'],'after target hash '+str(k))
        need(r['callerContextSha256']==c['callerContextSha256'],'caller context hash '+str(k))
        if is_hold:
            counts['hold_hash_only']+=1
            need(k[0] in CALLERLESS and r['callerless'] is True and r['changed'] is False and r['disposition']=='hold_hash_only','callerless readback hold '+str(k))
            need(sha(cell_after)==c['currentTargetSha256'] and k in hold_map,'callerless target changed/missing hash ledger '+str(k))
            need(not (FORBIDDEN & set(r)) and not (FORBIDDEN & set(hold_map[k])),'callerless text or id leak '+str(k))
        else:
            need(r['callerless'] is False and r['sourceId']==c['sourceId'] and r['source']==c['source'],'callerful source identity '+str(k))
            need(r['beforeTarget']==c['currentTarget'] and r['afterTarget']==cell_after,'callerful exact target readback '+str(k))
            if is_applied:
                counts['applied']+=1; chosen=accepted[k]
                need(r['changed'] is True and r['disposition']=='applied' and cell_after==chosen,'selected target applied '+str(k))
                need(selected_map[k]['acceptedTarget']==chosen and selected_map[k]['afterTargetSha256']==sha(chosen),'selected apply ledger '+str(k))
            else:
                counts['retain_current']+=1
                need(r['changed'] is False and r['disposition']=='retain_current' and sha(cell_after)==c['currentTargetSha256'],'retained target changed '+str(k))
    need(counts=={'applied':2,'retain_current':202,'hold_hash_only':36},'readback totals '+repr(dict(counts)))
    need(j(app/'application-summary.json')['counts']=={'applied':2,'retain_current':202,'hold_hash_only':36,'total':240},'application summary')
    for name in LINEAGE:
        need((ROOT/'cross'/'lineage'/name).read_bytes()==(inp/name).read_bytes(),'cross lineage copy '+name)

    if a.live_pr:
        evidence_head=git(repo,'rev-parse','HEAD')
        need(git(repo,'status','--porcelain=v1','--untracked-files=all')=='','evidence worktree not clean')
        need(git(repo,'branch','--show-current')=='','evidence worktree must be detached')
        need(git(repo,'rev-parse','HEAD^')==product_commit,'evidence commit is not directly after product commit')
        evidence_paths=git(repo,'diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()
        need(evidence_paths and all(p==EVIDENCE_PATH or p.startswith(EVIDENCE_PATH+'/') for p in evidence_paths),'evidence commit file scope')
        need(git(repo,'show',f'HEAD:{EVIDENCE_PATH}/manifest.json').strip()==(ROOT/'manifest.json').read_text(encoding='utf-8').strip(),'committed evidence manifest differs')
        need(git(repo,'rev-parse',f'HEAD:{CATALOG}')==git(repo,'rev-parse',f'{product_commit}:{CATALOG}'),'evidence commit changed catalog')
        api=json.loads(subprocess.check_output(['gh','pr','view','70','--repo','snapetech-org/ROMarrNG','--json','number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url,body'],text=True))
        need(api['number']==70 and api['state']=='OPEN' and api['isDraft'] is True and api['headRefName']==BRANCH and api['headRefOid']==evidence_head,'live PR state/head')
        prefix=(app/'pr-body-prefix.md').read_text(encoding='utf-8')
        need(api['body'].startswith(prefix),'PR body prefix changed')
        need('<!-- romarrng-pr70-window-605-624-application-20261104 -->' in api['body'],'PR body summary suffix missing')
        need(f'/tree/{evidence_head}/{EVIDENCE_PATH}/README.md' in api['body'],'PR body evidence link missing')
        refs_txt=subprocess.check_output(['git','-C',str(repo),'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head','refs/pull/70/merge'],text=True).strip()
        refs={line.split('\t')[1]:line.split('\t')[0] for line in refs_txt.splitlines() if line.strip()}
        need(refs[f'refs/heads/{BRANCH}']==evidence_head and refs['refs/pull/70/head']==evidence_head,'live branch/pull head')
        runs=json.loads(subprocess.check_output(['gh','api',f'repos/snapetech-org/ROMarrNG/actions/runs?head_sha={evidence_head}&per_page=100'],text=True)).get('workflow_runs',[])
        active=[r for r in runs if r.get('status') in {'queued','in_progress','requested','waiting','pending'}]
        need(not active,'unexpected active run on evidence head')
    print(json.dumps({'result':'PASS','baseHead':BASE,'productCommit':product_commit,'cells':240,'counts':dict(counts),'lineageFiles':len(LINEAGE),'livePrVerified':bool(a.live_pr)},sort_keys=True))
if __name__=='__main__': main()
