#!/usr/bin/env python3
"""Seal root-level primary review files with a manifest and SHA256SUMS."""
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent
summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
files=[]
for p in sorted(OUT.iterdir()):
    if not p.is_file() or p.name in {'manifest.json','SHA256SUMS.txt'}: continue
    data=p.read_bytes()
    files.append({'path':p.name,'sizeBytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
manifest={
 'artifact':summary['artifact'],'repository':summary['repository'],'pullRequest':summary['pullRequest'],
 'branch':summary['branch'],'head':summary['head'],'tree':summary['tree'],
 'window':'W425-W444','sourceCount':20,'localeCount':12,'cellCount':240,
 'candidateFreeInputPath':summary['candidateFreeInputPath'],
 'candidateFreeInputManifestSha256':summary['candidateFreeInputManifestSha256'],
 'candidateFreeInputChecksumsSha256':summary['candidateFreeInputChecksumsSha256'],
 'dispositions':summary['dispositions'],'proposedCellCount':summary['proposedCellCount'],
 'priorLineageSelectionsReattested':summary['priorLineageSelectionsReattested'],
 'priorHoldCellsReattested':summary['priorHoldCellsReattested'],
 'chineseSemanticNumeralAccepted':summary['chineseSemanticNumeralAccepted'],
 'files':files
}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=[]
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name!='SHA256SUMS.txt':
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
(OUT/'SHA256SUMS.txt').write_text('\n'.join(rows)+'\n',encoding='utf-8')
print(f"SEALED {len(files)} payload files; manifest {hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()}; SHA256SUMS {hashlib.sha256((OUT/'SHA256SUMS.txt').read_bytes()).hexdigest()}")
