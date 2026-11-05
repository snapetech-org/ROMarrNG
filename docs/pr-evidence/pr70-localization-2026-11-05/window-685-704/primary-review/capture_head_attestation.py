#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, hashlib, json, pathlib, subprocess, sys
OUT=pathlib.Path(__file__).resolve().parent
REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='43d2858744ef20cd58462643fed534ac61d2ffad'
TREE='73e8f50d65cb611def996b01bab0b00628b65860'
BRANCH='task/localization-translation-review-20261030'
BASE_API='bcd1eb41b5cdf8202acb5cf8e365e14761b743b5'
def run(*args): return subprocess.check_output(args,text=True).strip()
def sha(b): return hashlib.sha256(b).hexdigest()
def capture(label):
    pr=json.loads(run('gh','pr','view','70','--repo','snapetech-org/ROMarrNG','--json','state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,body'))
    refs=run('git','ls-remote','https://github.com/snapetech-org/ROMarrNG.git',f'refs/heads/{BRANCH}','refs/pull/70/head','refs/heads/main').splitlines()
    refmap={line.split('\t',1)[1]:line.split('\t',1)[0] for line in refs}
    localhead=run('git','-C',str(REPO),'rev-parse','HEAD')
    localtree=run('git','-C',str(REPO),'rev-parse','HEAD^{tree}')
    clean=not run('git','-C',str(REPO),'status','--porcelain','--untracked-files=all')
    body=pr['body'].encode('utf-8')
    if pr['state']!='OPEN' or pr['isDraft'] is not True or pr['headRefName']!=BRANCH or pr['headRefOid']!=HEAD or pr['baseRefName']!='main' or pr['baseRefOid']!=BASE_API:
        raise SystemExit('PR API pin drift')
    if refmap.get(f'refs/heads/{BRANCH}')!=HEAD or refmap.get('refs/pull/70/head')!=HEAD:
        raise SystemExit('branch/pull ref pin drift')
    if localhead!=HEAD or localtree!=TREE or not clean:
        raise SystemExit('local worktree pin/cleanliness drift')
    result={
      'artifact':'ROMarrNG PR #70 W685-W704 primary review exact-head attestation',
      'attestedAtUtc':dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
      'head':HEAD,'tree':TREE,'apiCommitTree':TREE,'branchRefSha':refmap[f'refs/heads/{BRANCH}'],'pullRefSha':refmap['refs/pull/70/head'],
      'state':pr['state'],'isDraft':pr['isDraft'],'headRefName':pr['headRefName'],'baseRefName':pr['baseRefName'],'baseApiSha':pr['baseRefOid'],
      'baseLiveRefOid':refmap['refs/heads/main'],'baseApiRefMismatch':pr['baseRefOid']!=refmap['refs/heads/main'],
      'bodyBytes':len(body),'bodySha256':sha(body),'pullRequest':70,'repository':'snapetech-org/ROMarrNG',
      'localHead':localhead,'localTree':localtree,'localStatusClean':True,'checksRerun':False,
    }
    (OUT/f'head-attestation-{label}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'label':label,'head':HEAD,'tree':TREE,'state':pr['state'],'draft':pr['isDraft'],'branchRef':result['branchRefSha'],'pullRef':result['pullRefSha'],'baseApiRefMismatch':result['baseApiRefMismatch'],'bodyBytes':len(body),'bodySha256':result['bodySha256'],'localStatusClean':True},sort_keys=True))
if __name__=='__main__': capture(sys.argv[1])
