#!/usr/bin/env python3
"""Read-only verifier for the ROMarrNG PR #70 W245-W264 application packet."""
import argparse, hashlib, json, subprocess
from pathlib import Path

CATALOG='romarr/ui-labels.json'
EVIDENCE=Path(__file__).resolve().parent

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args])
def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()
def raw_hash(text):
    return sha_bytes(text.encode('utf-8'))
def canonical_hash(text):
    return sha_bytes(json.dumps(text,ensure_ascii=False,separators=(',',':')).encode('utf-8'))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True,type=Path)
    ap.add_argument('--commit',default='HEAD')
    args=ap.parse_args()
    summary=json.loads((EVIDENCE/'summary.json').read_text(encoding='utf-8'))
    commit=git(args.repo,'rev-parse',args.commit).decode().strip()
    parent=git(args.repo,'rev-parse',f'{commit}^').decode().strip()
    assert parent==summary['appliedToParentHead'], (parent,summary['appliedToParentHead'])
    before=json.loads(git(args.repo,'show',f'{parent}:{CATALOG}'))
    after=json.loads(git(args.repo,'show',f'{commit}:{CATALOG}'))
    plan=[json.loads(line) for line in (EVIDENCE/'plan-240-cells.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    rows=[json.loads(line) for line in (EVIDENCE/'readback-240-cells.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(rows)==len(plan)==240
    assert len({(r['sourceId'],r['locale']) for r in rows})==240
    plan_by_pair={(r['sourceId'],r['locale']):r for r in plan}
    changed={(r['sourceId'],r['locale']) for r in rows if r['changeExpected']}
    assert len(changed)==30
    assert list(before.keys())==list(after.keys())
    assert list(before['messages'].keys())==list(after['messages'].keys())
    for row in rows:
        sid,locale=row['sourceId'],row['locale']
        plan_row=plan_by_pair[(sid,locale)]
        before_msg=before['messages'][sid]
        after_msg=after['messages'][sid]
        before_text=before_msg['translations'][locale]
        actual=after_msg['translations'][locale]
        assert before_text==plan_row['beforeText']
        assert raw_hash(before_text)==plan_row['beforeRawUtf8Sha256']
        if row['changeExpected']:
            assert before_text!=row['expectedTarget']
        else:
            assert before_text==row['expectedTarget']
        assert actual==row['expectedTarget']==row['actualTarget']
        assert raw_hash(actual)==row['actualRawUtf8Sha256']
        assert canonical_hash(actual)==row['actualCanonicalTranslationHash']==row['expectedCanonicalTranslationHash']
    for sid,bmsg in before['messages'].items():
        amsg=after['messages'][sid]
        assert list(bmsg.keys())==list(amsg.keys())
        for field in bmsg:
            if field not in ('translations','translationHashes'):
                assert amsg[field]==bmsg[field], (sid,field)
        expected_translations=dict(bmsg['translations'])
        expected_hashes=dict(bmsg.get('translationHashes',{}))
        for row in rows:
            if row['sourceId']==sid and row['changeExpected']:
                expected_translations[row['locale']]=row['expectedTarget']
                expected_hashes[row['locale']]=row['expectedCanonicalTranslationHash']
        assert amsg['translations']==expected_translations, sid
        assert amsg.get('translationHashes',{})==expected_hashes, sid
    assert all(not r['changedFromParent'] for r in rows if r['callerPathHold'])
    print(json.dumps({'commit':commit,'tree':git(args.repo,'rev-parse',f'{commit}^{{tree}}').decode().strip(),'parent':parent,'cells':len(rows),'changes':len(changed),'callerPathHolds':sum(r['callerPathHold'] for r in rows),'orderedMessageIdsPreserved':True,'metadataPreserved':True,'status':'pass'},sort_keys=True))
if __name__=='__main__': main()
