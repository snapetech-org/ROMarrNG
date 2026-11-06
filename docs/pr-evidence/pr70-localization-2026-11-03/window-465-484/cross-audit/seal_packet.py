#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
files=sorted(p for p in R.rglob("*") if p.is_file() and p not in (R/"packet-manifest.json",R/"SHA256SUMS.txt",R/"SHA256SUMS.txt.sha256"))
manifest={
 "repository":"snapetech-org/ROMarrNG","pullRequest":70,"window":"W465-W484",
 "candidateFreeHead":"7640720c5e3b1813725cca8d7aa46b5d968bff43",
 "candidateFreeTree":"bdee162cc11115256df8756f192b19d4337ed1dc",
 "latestAttestedHead":"7640720c5e3b1813725cca8d7aa46b5d968bff43",
 "latestAttestedTree":"bdee162cc11115256df8756f192b19d4337ed1dc",
 "files":[{"path":p.relative_to(R).as_posix(),"sha256":sha(p.read_bytes()),"sizeBytes":p.stat().st_size} for p in files]
}
(R/"packet-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
files=sorted(p for p in R.rglob("*") if p.is_file() and p not in (R/"SHA256SUMS.txt",R/"SHA256SUMS.txt.sha256"))
(R/"SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.relative_to(R).as_posix()}\n" for p in files),encoding="utf-8")
(R/"SHA256SUMS.txt.sha256").write_text(f"{sha((R/'SHA256SUMS.txt').read_bytes())}  SHA256SUMS.txt\n",encoding="utf-8")
print(json.dumps({"files":len(files),"sizeBytes":sum(p.stat().st_size for p in files),"rootSha256":sha((R/"SHA256SUMS.txt").read_bytes())},indent=2))

