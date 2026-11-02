#!/usr/bin/env python3
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path

HEAD='1adc54cb56dd91731b24e402027476855702f04d'
TREE='76792bcafecfb1c9243a1352f638e2f21c0bad0b'
PACKETS={'runtime-status-candidates.jsonl':'7232e9ae4319aa51ccee525e577920e480580e9574dcedf6236f25859ea2b5d7','browser-surface-candidates.jsonl':'eaa474643ea2a1ce798facbeae5d81bed6e2b58578cdaead8da2dbabf7f98b9b'}
DECISIONS_SHA='e0868118216ff45215d44c80a274f521993dc7c4149246b7f365fcd3999d76d5'
BLOBS={'romarr/ui-labels.json':('cd790e50d5183962fa90ec7de2058894af12b9aa','a9ed76e98a6e22d4974e164aa1d99e3914afd954eee0a9d91701e79d46d90359'),'romarr/app.py':('00efadefa23d905d8af3330a85ca3436c4c6128d','acd980b3e651dc0ea371e71ac66092c65f3375aa9aa83504897e9b8d7d6eeb08'),'romarr/ui.py':('aed3576f6b8508f6530fd45a0bbd79e4c3176998','5587ca39f263715f14e3f050c411177412df7f1dcf183edc4ef598370b5ed6c8')}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(repo,*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
def show(repo,revpath):return subprocess.check_output(['git','show',revpath],cwd=repo)
def fail(condition,msg):
 if not condition:raise SystemExit('FAIL: '+msg)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path('/home/keith/Documents/code/ROMarrNG'));a=ap.parse_args();repo=a.repo.resolve();here=Path(__file__).resolve().parent
 fail(git(repo,'rev-parse',f'{HEAD}^{{tree}}')==TREE,'pinned ROMarr tree mismatch')
 catalogs={}
 for path,(blob_oid,expected_sha) in BLOBS.items():
  raw=show(repo,f'{HEAD}:{path}')
  fail(git(repo,'rev-parse',f'{HEAD}:{path}')==blob_oid,f'git blob mismatch: {path}')
  fail(sha(raw)==expected_sha,f'file SHA-256 mismatch: {path}')
  if path.endswith('ui-labels.json'):catalogs=json.loads(raw.decode('utf-8'))['messages']
 packet_rows={}; all_rows=[]
 for name,expected in PACKETS.items():
  raw=(here/name).read_bytes();fail(sha(raw)==expected,'candidate input hash mismatch: '+name)
  rows=[json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]
  fail(len(rows)==24,'candidate row count mismatch: '+name)
  packet_rows[name]=rows;all_rows.extend((name,r) for r in rows)
 decisions=[json.loads(x) for x in (here/'crossreview-decisions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
 fail(sha((here/'crossreview-decisions.jsonl').read_bytes())==DECISIONS_SHA,'decision ledger hash mismatch')
 fail(len(decisions)==48,'decision ledger row count mismatch')
 dmap={(r['candidateFile'],r['sourceKey'],r['locale']):r for r in decisions}
 fail(len(dmap)==48,'duplicate decision row')
 counts=collections.Counter(r['decision'] for r in decisions)
 fail(counts=={'accept':40,'refine':5,'keep':3},f'decision counts mismatch: {counts}')
 for filename,c in all_rows:
  key=(filename,c['sourceKey'],c['locale']);d=dmap.get(key);fail(d is not None,'missing decision '+str(key))
  fail(c['reviewHead']==HEAD and c['reviewTree']==TREE,'candidate head pin mismatch')
  fail(c.get('sourceCatalogHead') in (None,HEAD) and c.get('sourceCatalogTree') in (None,TREE),'source catalog pin mismatch')
  msg=catalogs.get(c['sourceKey']);fail(msg is not None,'source key missing')
  fail(msg['source']==c['sourceId'] and sha(msg['source'].encode())==c['sourceHash'],'source ID/hash mismatch')
  current=msg['translations'][c['locale']]
  fail(current==c['currentTarget'] and sha(current.encode())==c['currentTargetSha256'],'exact current translation mismatch')
  fail(sha(c['proposedTarget'].encode())==c['proposedTargetSha256'],'candidate proposal hash mismatch')
  fail(d['candidatePacketSha256']==PACKETS[filename],'decision packet pin mismatch')
  fail(d['currentTarget']==current and d['currentTargetSha256']==c['currentTargetSha256'],'decision baseline mismatch')
  fail(d['candidateTarget']==c['proposedTarget'] and d['candidateTargetSha256']==c['proposedTargetSha256'],'decision proposal mismatch')
  fail(sha(d['finalTarget'].encode())==d['finalTargetSha256'],'final target hash mismatch')
  if d['decision']=='accept':fail(d['finalTarget']==c['proposedTarget'],'accepted proposal changed')
  elif d['decision']=='keep':fail(d['finalTarget']==current,'keep target changed')
  else:fail(d['decision']=='refine' and d['finalTarget']!=c['proposedTarget'],'refinement mismatch')
  fail(sorted(re.findall(r'\{[^{}]+\}',msg['source']))==sorted(re.findall(r'\{[^{}]+\}',d['finalTarget'])),'placeholder mismatch')
 fail(len({(d['sourceKey'],d['locale']) for d in decisions})==48,'overlapping source/locale cells')
 app=show(repo,f'{HEAD}:romarr/app.py').decode('utf-8');ui=show(repo,f'{HEAD}:romarr/ui.py').decode('utf-8')
 fail('"message": f"Reading the library from {where}…"' in app,'loading-status caller context missing')
 fail('if not self.game_libraries:' in app and '"message": "no library configured"' in app,'library-configuration caller context missing')
 fail("'<b>Acquire</b> → <b>Verify</b> → <b>File</b> → <b>Scan</b> → <b>Play</b><br>'" in ui,'Get Started pipeline context missing')
 fail('Import a folder you own and let ROMarr identify and file what is there.' in ui,'file-stage supporting context missing')
 fail('Load a DAT and see verified titles and collection progress.' in ui,'complete-set supporting context missing')
 # Verify every non-manifest file with the final evidence checksum list.
 listed=set()
 for line in (here/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  digest,name=line.split('  ',1);path=here/name
  fail(path.is_file() and sha(path.read_bytes())==digest,'bundle checksum mismatch '+name);listed.add(name)
 actual={p.relative_to(here).as_posix() for p in here.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
 fail(listed==actual,'bundle checksum inventory mismatch')
 print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'runtime_status_rows':24,'browser_surface_rows':24,'decisions':dict(sorted(counts.items())),'final_targets_changed':45,'kept_current':3,'unique_cells':48,'placeholder_checks':48,'source_file_pins':len(BLOBS),'native_speaker_approval':False,'romarr_edits':False},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
