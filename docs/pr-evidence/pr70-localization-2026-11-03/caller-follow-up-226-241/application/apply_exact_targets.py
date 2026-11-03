import copy, datetime, hashlib, json, pathlib, subprocess

REPO=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261103/romarrng-pr70-w226-review-20261103')
AUDIT=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w226-followup-third-party-cross-audit-20261103')
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w226-followup-apply-20261103')
HEAD='e0cb91389334fe534ff44ccfc72cbb2c152a93b4'
TREE='3876dd57816aaf75bb8b1a56a75a5045d216c461'
CATALOG='romarr/ui-labels.json'
assert not OUT.exists(), f'refusing to overwrite {OUT}'

def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def sha(raw): return hashlib.sha256(raw).hexdigest()
def shat(text): return sha(text.encode('utf-8'))
def translation_hash(value):
    serialized=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return shat(serialized)
def canonical(value): return json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True)

assert git('rev-parse','HEAD').decode().strip()==HEAD
assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert not git('status','--porcelain').decode().strip(), 'worktree must be clean'
summary=json.loads((AUDIT/'summary.json').read_text())
assert summary['reviewedCells']==48 and summary['changedTargetRecommendations']==12
rows=[json.loads(line) for line in (AUDIT/'cross-audit-ledger.jsonl').read_text().splitlines() if line]
assert len(rows)==48 and all(r['head']==HEAD and r['tree']==TREE for r in rows)
raw=git('show',f'HEAD:{CATALOG}').decode('utf-8')
assert all(r['catalogPath']==CATALOG and r['catalogSha256']==sha(raw.encode('utf-8')) for r in rows)
assert all(r['catalogGitBlob']==git('rev-parse',f'HEAD:{CATALOG}').decode().strip() for r in rows)
base=json.loads(raw)
expected=copy.deepcopy(base)
plan=[]; changed_rows=[]; readback=[]
for row in rows:
    sid=row['sourceId']; loc=row['locale']; final=row['final']
    message=base['messages'][sid]
    current=message['translations'][loc]
    assert current==row['currentTarget'] and shat(current)==row['currentTargetSha256']
    target=final['selectedTarget'] if final['disposition']!='hold' else current
    target_hash=final['selectedTargetSha256'] if final['disposition']!='hold' else row['currentTargetSha256']
    if final['disposition']=='hold':
        assert final['selectedTarget'] is None and final['selectedTargetSha256'] is None
    else:
        assert isinstance(target,str) and shat(target)==target_hash
    changed=target!=current
    assert changed==(final['disposition'] in {'correction','refinement'})
    plan.append({'position':row['position'],'locale':loc,'sourceId':sid,'source':row['source'],'currentTarget':current,'currentTargetSha256':row['currentTargetSha256'],'disposition':final['disposition'],'selectedTarget':target,'selectedTargetSha256':target_hash,'catalogTranslationHash':translation_hash(target),'changed':changed})
    if changed:
        changed_rows.append(row)
        expected['messages'][sid]['translations'][loc]=target
        expected['messages'][sid]['translationHashes'][loc]=translation_hash(target)
assert len(changed_rows)==12
assert sum(r['final']['disposition']=='hold' for r in rows)==3
assert len(base['messages'])==1836
assert list(base)==list(expected) and list(base['messages'])==list(expected['messages'])

edited=json.dumps(expected,ensure_ascii=False,indent=2)+'\n'
assert json.loads(edited)==expected
(REPO/CATALOG).write_text(edited,encoding='utf-8')
after=json.loads((REPO/CATALOG).read_text())
assert after==expected
for row,planrow in zip(rows,plan):
    message=after['messages'][row['sourceId']]
    actual=message['translations'][row['locale']]
    target_hash=shat(actual)
    metadata_hash=message['translationHashes'][row['locale']]
    readback.append({'position':row['position'],'locale':row['locale'],'sourceId':row['sourceId'],'disposition':row['final']['disposition'],'expectedTarget':planrow['selectedTarget'],'expectedTargetSha256':planrow['selectedTargetSha256'],'actualTarget':actual,'actualTargetSha256':target_hash,'catalogTranslationHash':metadata_hash,'translationHashMatchesRuntimeRule':metadata_hash==translation_hash(actual),'matches':actual==planrow['selectedTarget'] and target_hash==planrow['selectedTargetSha256']})
assert len(readback)==48 and all(r['matches'] and r['translationHashMatchesRuntimeRule'] for r in readback)
assert sum(r['changed'] for r in plan)==12

OUT.mkdir(parents=True)
application=OUT/'application'; application.mkdir()
(application/'apply-plan.jsonl').write_text(''.join(canonical(x)+'\n' for x in plan),encoding='utf-8')
(application/'readback.jsonl').write_text(''.join(canonical(x)+'\n' for x in readback),encoding='utf-8')
summary_out={'repository':'snapetech-org/ROMarrNG','pullRequest':70,'baseHead':HEAD,'baseTree':TREE,'window':'caller follow-up positions 226, 232, 237, and 241','reviewedCells':48,'finalDispositionCounts':summary['finalDispositionCounts'],'changedTargets':12,'changedCatalogFiles':1,'heldCells':3,'readbackRows':48,'readbackMismatches':0,'translationHashesRecomputed':12,'nonTargetCatalogChanges':0,'catalogMessageCount':len(after['messages'])}
(application/'summary.json').write_text(json.dumps(summary_out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(application/'apply_exact_targets.py').write_text(pathlib.Path(__file__).read_text(),encoding='utf-8')
print(json.dumps(summary_out,ensure_ascii=False,indent=2))
