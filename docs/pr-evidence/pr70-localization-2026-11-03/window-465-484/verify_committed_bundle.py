#!/usr/bin/env python3
"""Verify all W465-W484 evidence files are committed with their sealed hashes."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REL=ROOT.relative_to(ROOT.parents[3]).as_posix()
def sha(b): return hashlib.sha256(b).hexdigest()
def git(repo,*args):
 return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def gitb(repo,*args):
 return subprocess.check_output(['git','-C',str(repo),*args])
def need(ok,msg):
 if not ok: raise SystemExit('FAIL: '+msg)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--repo',type=Path,default=ROOT.parents[3])
 ap.add_argument('--commit',default=None)
 a=ap.parse_args(); repo=a.repo.resolve()
 commit=a.commit or git(repo,'rev-parse','HEAD')
 need(git(repo,'cat-file','-t',commit)=='commit','commit object')
 manifest_path=REL+'/manifest.json'
 sums_path=REL+'/SHA256SUMS.txt'
 m=json.loads(gitb(repo,'show',commit+':'+manifest_path))
 records={x['path']:x for x in m['files']}
 expected=set(records)|{'manifest.json','SHA256SUMS.txt'}
 tracked=git(repo,'ls-tree','-r','--name-only',commit,'--',REL).splitlines()
 actual={x[len(REL)+1:] for x in tracked}
 need(actual==expected,'committed evidence path inventory (missing/extra files)')
 for rel,rec in records.items():
  raw=gitb(repo,'show',commit+':'+REL+'/'+rel)
  need(sha(raw)==rec['sha256'] and len(raw)==rec['bytes'],'committed manifest hash '+rel)
 sums=gitb(repo,'show',commit+':'+sums_path).decode('utf-8').splitlines()
 smap={}
 for line in sums:
  if not line.strip(): continue
  match=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
  need(bool(match),'malformed committed checksum')
  h,name=match.groups()
  need(name not in smap and not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe committed checksum path')
  smap[name]=h
 need(set(smap)==expected-{'SHA256SUMS.txt'},'committed checksum inventory')
 for rel,h in smap.items(): need(sha(gitb(repo,'show',commit+':'+REL+'/'+rel))==h,'committed checksum '+rel)
 need(git(repo,'rev-parse',m['catalogCommit']+'^{tree}')==m['catalogTree'],'catalog commit tree pin')
 print(json.dumps({'result':'PASS','window':m['window'],'evidenceCommit':commit,'files':len(expected),'catalogCommit':m['catalogCommit'],'catalogTree':m['catalogTree']},indent=2))
if __name__=='__main__': main()
