from pathlib import Path
import hashlib,json,subprocess
E=Path(__file__).resolve().parent
REPO=E.parents[3]
BASE="6eb40719ea270bb3cae024d771665e7006a85822"
TREE="55031e7e234a7035de7682d0b49f2f60882164f6"
BRANCH="task/localization-translation-review-20261030"
def run(*args):
    return subprocess.check_output(args,cwd=REPO,text=True).strip()
head=run("git","rev-parse","HEAD")
tree=run("git","rev-parse","HEAD^{tree}")
pr=json.loads(run("gh","api","repos/snapetech-org/ROMarrNG/pulls/70"))
assert (pr["state"],pr["draft"],pr["head"]["sha"],pr["head"]["ref"],pr["base"]["ref"])==("open",True,head,BRANCH,"main")
refs=run("git","ls-remote","origin",f"refs/heads/{BRANCH}","refs/pull/70/head")
refmap={line.split()[1]:line.split()[0] for line in refs.splitlines() if line.strip()}
assert refmap=={f"refs/heads/{BRANCH}":head,"refs/pull/70/head":head}
paths=["romarr/ui.py","romarr/app.py","romarr/ui-labels.json","romarr/ui-source-snapshot.json"]
files={}
for path in paths:
    raw=(REPO/path).read_bytes()
    files[path]={"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"gitBlob":run("git","rev-parse",f"HEAD:{path}")}
data={"schemaVersion":1,"repository":"snapetech-org/ROMarrNG","pullRequest":70,"branch":BRANCH,"baseRef":"main","reviewedBaseHead":BASE,"reviewedBaseTree":TREE,"applicationCommit":head,"applicationTree":tree,"livePullRequestHead":pr["head"]["sha"],"files":files,"catalogsUnchanged":True,"testsBuildsScansCi":"not run","mergeReleaseTag":"not performed"}
(E/"application-verification.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
entries=[]
for p in sorted(E.rglob("*")):
    if p.is_file() and p.name!="SHA256SUMS.txt":
        entries.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(E).as_posix()}")
(E/"SHA256SUMS.txt").write_text("\n".join(entries)+"\n")
print(json.dumps({"applicationCommit":head,"applicationTree":tree,"livePullRequestHead":pr["head"]["sha"],"files":files},indent=2))
