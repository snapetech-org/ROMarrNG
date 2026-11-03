#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,subprocess,sys

E=Path(__file__).resolve().parent
REPO=E.parents[3]
BASE="6eb40719ea270bb3cae024d771665e7006a85822"
TREE="55031e7e234a7035de7682d0b49f2f60882164f6"
BRANCH="task/localization-translation-review-20261030"
PREFIX="docs/pr-evidence/pr70-localization-2026-11-03/romarr-source-bound-localization/"
LOCALES=["es","zh-Hans","hi","de","ja","fr","pt-BR","ar","ko","zh-Hant","vi","id"]
mode=sys.argv[1] if len(sys.argv)>1 else "--postpush"
assert mode in {"--precommit","--prepush","--evidence","--postpush"},mode

def run(*args):
    return subprocess.check_output(args,cwd=REPO,text=True).strip()
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def content_hash(value):
    return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))
def verify_sums():
    sums=E/"SHA256SUMS.txt"
    if not sums.exists():
        return
    listed={}
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest,name=line.split(None,1); name=name.strip().lstrip("*")
        target=E/name
        assert target.is_file() and sha(target.read_bytes())==digest,(name,"checksum")
        assert name not in listed,name
        listed[name]=digest
    actual={p.relative_to(E).as_posix() for p in E.rglob("*") if p.is_file() and p!=sums}
    assert set(listed)==actual,{"missing":sorted(actual-set(listed)),"extra":sorted(set(listed)-actual)}

baseline=json.loads((E/"baseline-pins.json").read_text())
assert (baseline["reviewedBaseHead"],baseline["reviewedBaseTree"],baseline["branch"])==(BASE,TREE,BRANCH)
files=baseline["files"]
for path,pin in files.items():
    raw=subprocess.check_output(["git","show",f"{BASE}:{path}"],cwd=REPO)
    assert len(raw)==pin["bytes"] and sha(raw)==pin["sha256"],(path,"baseline sha")
    assert run("git","rev-parse",f"{BASE}:{path}")==pin["gitBlob"],(path,"baseline blob")
for path in ["romarr/app.py","romarr/ui-labels.json","romarr/ui-source-snapshot.json"]:
    raw=(REPO/path).read_bytes()
    assert sha(raw)==files[path]["sha256"] and run("git","rev-parse",f"HEAD:{path}")==files[path]["gitBlob"],(path,"must remain unchanged")
catalog=json.loads((REPO/"romarr/ui-labels.json").read_text())
snapshot=json.loads((REPO/"romarr/ui-source-snapshot.json").read_text())
for key,item in baseline["sourceKeys"].items():
    msg=catalog["messages"][key]
    assert msg["source"]==item["source"] and sha(msg["source"].encode())==item["sourceHash"]
    assert snapshot[key]==item["sourceHash"]==baseline["sourceSnapshotHashes"][key]
    for loc in LOCALES:
        old=item["translations"][loc]
        value=msg["translations"].get(loc)
        assert value==old["value"] and content_hash(value)==old["translationHash"]==msg["translationHashes"][loc],(key,loc)
ui=(REPO/"romarr/ui.py").read_text()
assert "/api/v1/launchers/connect" in ui
assert "r.error.match(/^scan failed: ([A-Za-z_][A-Za-z0-9_]*)$/)" in ui
assert "'ui.scan-failed-error-type.e99ccb8157'" in ui
assert "{error_type:scanFailure[1]}" in ui
assert "else toastAppMessage(r.error);" in ui
assert "/api/v1/totp/enroll" in ui
assert "note===UI_MESSAGES[noteKey]?.source" in ui
assert "?interfaceMarkup(noteKey):apiMessageMarkup(note)" in ui
assert "ui.scan-the-uri-or-enter-the-secret-in.612ce1fd46" in ui
assert "apiMessageMarkup(d.note||'')" not in ui
diff=set(filter(None,run("git","diff","--name-only",BASE).splitlines()))
assert all(p=="romarr/ui.py" or p.startswith(PREFIX) for p in diff),sorted(diff)
assert not any(p.startswith(".github/workflows/") for p in diff)
checked=subprocess.run(["git","-C",str(REPO),"diff","--check",BASE],capture_output=True,text=True)
assert checked.returncode==0,checked.stdout+checked.stderr
status=run("git","status","--porcelain","--untracked-files=all").splitlines()
status_paths=[line[2:].strip() for line in status]
assert all(p=="romarr/ui.py" or p.startswith(PREFIX) for p in status_paths),status_paths
head=run("git","rev-parse","HEAD")
tree=run("git","rev-parse","HEAD^{tree}")
pr=json.loads(run("gh","api","repos/snapetech-org/ROMarrNG/pulls/70"))
assert (pr["state"],pr["draft"],pr["head"]["ref"],pr["base"]["ref"])==("open",True,BRANCH,"main")
refs=run("git","ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/70/head")
refmap={line.split()[1]:line.split()[0] for line in refs.splitlines() if line.strip()}
remote_branch=refmap[f"refs/heads/{BRANCH}"]
remote_pr=refmap["refs/pull/70/head"]
if mode=="--precommit":
    assert head==BASE and tree==TREE and pr["head"]["sha"]==remote_branch==remote_pr==BASE
    assert "romarr/ui.py" in status_paths and any(p.startswith(PREFIX) for p in status_paths)
elif mode=="--prepush":
    assert run("git","rev-parse",f"{head}^")==BASE and not status_paths
    assert pr["head"]["sha"]==remote_branch==remote_pr==BASE
elif mode=="--evidence":
    app=json.loads((E/"application-verification.json").read_text())
    assert head==app["applicationCommit"] and pr["head"]["sha"]==remote_branch==remote_pr==head
    assert all(p.startswith(PREFIX) for p in status_paths),status_paths
    verify_sums()
else:
    app=json.loads((E/"application-verification.json").read_text())
    assert pr["head"]["sha"]==remote_branch==remote_pr==head and not status_paths
    assert app["applicationCommit"] in run("git","rev-list",f"{BASE}..{head}").split()
    assert run("git","rev-parse",f'{app["applicationCommit"]}^')==BASE
    assert run("git","rev-parse",f'{app["applicationCommit"]}^{{tree}}')==app["applicationTree"]
    assert app["livePullRequestHead"]==app["applicationCommit"] and app["branch"]==BRANCH
    current_files=app["files"]
    for path,pin in current_files.items():
        raw=(REPO/path).read_bytes()
        assert len(raw)==pin["bytes"] and sha(raw)==pin["sha256"] and run("git","rev-parse",f"HEAD:{path}")==pin["gitBlob"],(path,"current application pin")
    verify_sums()
print(json.dumps({"pass":True,"mode":mode,"base":BASE,"head":head,"tree":tree,"sourceBoundCallers":2,"catalogKeys":len(baseline["sourceKeys"]),"localesPerKey":len(LOCALES),"catalogValuesChanged":False,"nonTargetChanges":0,"workflowFilesTouched":False,"wholeDiffCheck":"PASS","pr":"OPEN/DRAFT"},indent=2))
