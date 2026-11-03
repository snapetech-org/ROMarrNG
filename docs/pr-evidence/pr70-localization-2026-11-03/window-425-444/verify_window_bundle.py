#!/usr/bin/env python3
"""Verify the portable ROMarrNG PR #70 W425-W444 review/application bundle."""
from pathlib import Path
import hashlib,json,subprocess,sys
WINDOW=Path(__file__).resolve().parent
REPO=WINDOW.parents[3]
def sha(b):return hashlib.sha256(b).hexdigest()
def fail(m):raise SystemExit('FAIL: '+m)

# The top-level inventory and manifest seal every copied packet and verifier.
checksum=WINDOW/'SHA256SUMS.txt'
listed={}
for line in checksum.read_text(encoding='utf-8').splitlines():
    if not line.strip():continue
    digest,rel=line.split('  ',1)
    if rel in listed:fail('duplicate checksum path '+rel)
    listed[rel]=digest
actual={p.relative_to(WINDOW).as_posix() for p in WINDOW.rglob('*') if p.is_file() and p!=checksum}
if set(listed)!=actual:fail('top-level checksum inventory mismatch')
for rel,digest in listed.items():
    if sha((WINDOW/rel).read_bytes())!=digest:fail('checksum mismatch '+rel)
manifest=json.loads((WINDOW/'manifest.json').read_text(encoding='utf-8'))
records={r['path']:r for r in manifest['files']}
if set(records)!=actual-{'manifest.json'}:fail('manifest inventory mismatch')
for rel,row in records.items():
    raw=(WINDOW/rel).read_bytes()
    if len(raw)!=row['sizeBytes'] or sha(raw)!=row['sha256']:fail('manifest mismatch '+rel)

# Check each original packet through its supplied verifier; run the portable
# companion for the primary packet because the original uses its scratch input path.
checks=[
    (WINDOW/'candidate-free-input',['python3','verify_input.py']),
    (WINDOW,['python3','verify_primary_portable.py']),
    (WINDOW/'independent-review',['python3','verify_blind.py']),
    (WINDOW/'cross-audit',['python3','verify_cross_audit.py']),
    (WINDOW/'application',['python3','verify_apply.py']),
]
for folder,cmd in checks:
    p=subprocess.run(cmd,cwd=folder,text=True,capture_output=True)
    if p.returncode:fail(f'verifier failed in {folder}: {p.stdout}{p.stderr}')
print(json.dumps({'status':'PASS','bundleFiles':len(listed),'manifestFiles':len(records),
                  'candidateFree':'PASS','primary':'PASS (portable companion; original packet preserved)',
                  'blind':'PASS','crossAudit':'PASS','application':'PASS'},indent=2))
