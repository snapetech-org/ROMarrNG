#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess
from pathlib import Path

REPO=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
ROOT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w685-704-root-adjudication-20261105')
CF=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w685-704-20261105/candidate-free/input')
HEAD='43d2858744ef20cd58462643fed534ac61d2ffad'
TREE='73e8f50d65cb611def996b01bab0b00628b65860'
CAT=REPO/'romarr/ui-labels.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return sha(s.encode('utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def digest_tokens(source,target,protected):
    patterns=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
    return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in patterns) and all(x in target for x in protected)

assert git('rev-parse','HEAD')==HEAD and git('rev-parse','HEAD^{tree}')==TREE
assert git('status','--porcelain=v1','--untracked-files=all')==''
before=CAT.read_bytes()
assert before==subprocess.check_output(['git','-C',str(REPO),'show','HEAD:romarr/ui-labels.json'])
data=json.loads(before)
serialized=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
assert serialized.encode('utf-8')==before,'unexpected catalog formatting drift'
candidate={ (r['position'],r['locale']):r for r in rows(CF/'candidate-free-cells.jsonl') }
targets=rows(ROOT/'root-adjudication'/'selected-targets.jsonl')
assert len(candidate)==240 and len(targets)==7
changes=[]
for r in targets:
    k=(r['position'],r['locale']); cell=candidate[k]
    assert cell['sourceId']==r['sourceId']
    assert cell['sourceSha256']==r['sourceSha256'] and cell['currentTargetSha256']==r['currentTargetSha256']
    assert cell['callerContextSha256']==r['callerContextSha256']
    assert textsha(cell['source'])==cell['sourceSha256'] and textsha(cell['currentTarget'])==cell['currentTargetSha256']
    assert digest_tokens(cell['source'],r['rootTarget'],cell['sourceProtectedLiterals'])
    message=data['messages'][r['sourceId']]
    old=message['translations'][r['locale']]
    assert old==cell['currentTarget'] and textsha(old)==r['currentTargetSha256']
    assert r['rootTargetSha256']==textsha(r['rootTarget'])
    message['translations'][r['locale']]=r['rootTarget']
    changes.append({'position':r['position'],'locale':r['locale'],'sourceId':r['sourceId'],
      'before':old,'beforeSha256':textsha(old),'after':r['rootTarget'],'afterSha256':textsha(r['rootTarget']),
      'rootDisposition':r['rootDisposition'],'callerContextSha256':r['callerContextSha256']})
assert len(changes)==7
out=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
CAT.write_bytes(out)
roundtrip=json.loads(CAT.read_text(encoding='utf-8'))
assert list(roundtrip['messages'])==list(json.loads(before)['messages'])
for r in targets:
    assert roundtrip['messages'][r['sourceId']]['translations'][r['locale']]==r['rootTarget']
# Compare every source message/locale cell with the exact pre-edit catalog.
olddata=json.loads(before)
changed=[]
for sid,entry in olddata['messages'].items():
    for loc,val in entry['translations'].items():
        new=roundtrip['messages'][sid]['translations'][loc]
        if new!=val: changed.append((sid,loc,val,new))
assert len(changed)==7
assert { (sid,loc) for sid,loc,_,_ in changed }=={(r['sourceId'],r['locale']) for r in targets}
# Full catalog parity for all direct locales.
locales=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
message_ids=set(roundtrip['messages'])
for loc in locales:
    missing=[sid for sid,m in roundtrip['messages'].items() if loc not in m['translations'] or not m['translations'][loc]]
    assert not missing,(loc,missing[:5])
    assert len(roundtrip['messages'])==1836
readback={
 'artifact':'ROMarrNG PR #70 W685-W704 product application readback',
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W685-W704',
 'inputHead':HEAD,'inputTree':TREE,'changedCatalogPath':'romarr/ui-labels.json',
 'changedCellCount':len(changes),'expectedChangedCellCount':7,
 'catalogKeyOrderPreserved':True,'allOtherCatalogCellsUnchanged':True,
 'all12DirectLocalesHave1836NonemptyMessages':True,
 'localeCount':12,'messageCountPerLocale':1836,
 'candidateFreeInputSha256':sha((CF/'candidate-free-cells.jsonl').read_bytes()),
 'targetReadback':changes,
 'catalogSha256After':sha(out),
 'productDiffNames':['romarr/ui-labels.json'],
 'postApplyWorktreeHead':git('rev-parse','HEAD'),
 'postApplyWorktreeTree':git('write-tree'),
 'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False
}
(ROOT/'application'/'readback-before-commit.json').write_text(json.dumps(readback,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changedCellCount':len(changes),'catalogSha256After':readback['catalogSha256After'],'locales':12,'keysPerLocale':1836,'serializedFormattingPreserved':True},ensure_ascii=False,indent=2))
