#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
repo=Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-apply-20261103/repo")
branch="task/localization-translation-review-20261030"
def observe():
 p=json.loads(subprocess.check_output(["gh","pr","view","70","--repo","snapetech-org/ROMarrNG","--json","state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url"],text=True))
 ls=subprocess.check_output(["git","-C",str(repo),"ls-remote","origin",f"refs/heads/{branch}","refs/pull/70/head"],text=True)
 refs={line.split("\t",1)[1]:line.split("\t",1)[0] for line in ls.splitlines()}
 h="7681ea470ee0f387cd3a1a5be0541979d9cd06f6"
 tree=subprocess.check_output(["git","-C",str(repo),"rev-parse",f"{h}^{{tree}}"],text=True).strip()
 status=subprocess.check_output(["git","-C",str(repo),"status","--porcelain=v1"],text=True)
 return {"observedUtc":subprocess.check_output(["date","-u","+%Y-%m-%dT%H:%M:%SZ"],text=True).strip(),"repository":"snapetech-org/ROMarrNG","pullRequest":70,"url":p["url"],"state":p["state"],"isDraft":p["isDraft"],"headRefName":p["headRefName"],"headRefOid":p["headRefOid"],"baseRefName":p["baseRefName"],"baseRefOid":p["baseRefOid"],"headTree":tree,"liveBranchRefOid":refs.get(f"refs/heads/{branch}"),"livePullRefOid":refs.get("refs/pull/70/head"),"readOnlyCheckoutPath":str(repo),"readOnlyCheckoutWorktreeClean":not bool(status),"checkoutHead":subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()}
p=root/"live-pr-attestation.json"; data=json.loads(p.read_text()); data["observedAfter"]=observe(); p.write_text(json.dumps(data,indent=2)+"\n")
