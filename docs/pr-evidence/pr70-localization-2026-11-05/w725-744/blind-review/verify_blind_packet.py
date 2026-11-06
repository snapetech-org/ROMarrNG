#!/usr/bin/env python3
"""Verify the sealed independent blind packet against its candidate-free input and pinned worktree."""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, subprocess
HERE=pathlib.Path(__file__).resolve().parent
DEFAULT_INPUT=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w725-744-20261105/candidate-free')
DEFAULT_REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='c3f92c45b4b4f8d79a8caa99417f9970ebc42a26'; TREE='3f835643e4f557999d533c3e832fc92036d4b01a'; WINDOW='W725-W744'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
def sha(b): return hashlib.sha256(b.encode('utf-8') if isinstance(b,str) else b).hexdigest()
def blobsha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def need(ok,msg):
 if not ok: raise SystemExit('FAIL: '+msg)
def verify_sums(root):
 sums=root/'SHA256SUMS.txt'; listing={}
 for line in sums.read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  h,rel=line.split('  ',1); p=(root/rel).resolve(); need(p.is_relative_to(root.resolve()) and p.is_file() and sha(p.read_bytes())==h,'checksum '+rel); need(rel not in listing,'duplicate checksum '+rel); listing[rel]=h
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}; need(actual==set(listing),'checksum coverage')
def token_pass(source,target):
 def prot(s):
  out=[]
  for x in PROTECTED:
   found=x in s if x.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',s))
   if found: out.append(x)
  return set(out)
 sp,st,sn,sl=PH.findall(source),TAG.findall(source),NUMBER.findall(source),prot(source)
 tp,tt,tn,tl=PH.findall(target),TAG.findall(target),NUMBER.findall(target),prot(target)
 sc,tc=collections.Counter(sn),collections.Counter(tn); extra=tc-sc
 presentation=bool(re.search(r'\bzero\b',source,re.I) and not sn and extra==collections.Counter(['0']))
 return (collections.Counter(sp)==collections.Counter(tp) and collections.Counter(st)==collections.Counter(tt) and not (sc-tc) and (not extra or presentation) and all(x in target for x in sl))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=pathlib.Path,default=DEFAULT_INPUT); ap.add_argument('--repo',type=pathlib.Path,default=DEFAULT_REPO); a=ap.parse_args()
 verify_sums(a.input); verify_sums(HERE); need((HERE/'input-SHA256SUMS.txt').read_bytes()==(a.input/'SHA256SUMS.txt').read_bytes(),'copied input checksum list')
 inp=a.input/'input'; m=j(inp/'manifest.json'); s=j(HERE/'summary.json'); need((m['head'],m['tree'],m['window'])==(HEAD,TREE,WINDOW),'input manifest pin'); need((s['head'],s['tree'],s['window'])==(HEAD,TREE,WINDOW),'output summary pin')
 repo=a.repo.resolve(); git=lambda *x:subprocess.check_output(['git','-C',str(repo),*x],text=True).strip()
 need(git('rev-parse','HEAD')==HEAD and git('rev-parse','HEAD^{tree}')==TREE,'repo head/tree'); need(git('status','--porcelain=v1','--untracked-files=all')=='','repo clean')
 pins={x['path']:x for x in j(inp/'source-file-pins.json')['files']}
 for path in ('romarr/ui-labels.json','romarr/ui-source-messages.json','romarr/ui-source-snapshot.json'):
  pin=pins[path]; raw=(repo/path).read_bytes(); need(len(raw)==pin['bytes'] and sha(raw)==pin['fileSha256'] and blobsha(raw)==pin['gitBlob'],'file pin '+path); need(git('rev-parse',f'{HEAD}:{path}')==pin['gitBlob'],'file Git blob '+path)
 ctxs=jl(inp/'source-contexts.jsonl'); pinned=set()
 for c in ctxs:
  if c['callerless']: continue
  for call in c['callers']:
   path=call['path']; raw=(repo/path).read_bytes(); lines=raw.decode('utf-8').splitlines(); pin=pins[path]
   need(sha(raw)==call['fileSha256']==pin['fileSha256'] and blobsha(raw)==call['gitBlob']==pin['gitBlob'],'caller file pin '+path); need(git('rev-parse',f'{HEAD}:{path}')==call['gitBlob'],'caller Git blob '+path)
   for line in call['excerpt']: need(lines[line['line']-1]==line['text'],'caller excerpt '+path+':'+str(line['line']))
   pinned.add(path)
 rawlines=(inp/'candidate-free-cells.jsonl').read_bytes().splitlines(); cells=[json.loads(x) for x in rawlines]; out=jl(HERE/'review-cells.jsonl')
 need(len(cells)==240 and len(out)==240,'cell count'); need([(r['position'],r['locale']) for r in cells]==[(p,l) for p in range(725,745) for l in LOCALES],'input order'); need([(r['position'],r['locale']) for r in out]==[(r['position'],r['locale']) for r in cells],'output order')
 counts=collections.Counter(r['decision'] for r in out); need(counts=={'retain':227,'proposal':1,'hold':12},'decision counts'); need([(r['position'],r['locale']) for r in out if r['decision']=='proposal']==[(740,'ar')],'proposal position'); need(all(r.get('rationale') and r.get('confidence') in {'high','moderate','low','unknown'} for r in out),'per-cell rationale/confidence'); holds=backed=props=0
 for raw,c,r in zip(rawlines,cells,out):
  need(r['inputCellRowSha256']==sha(raw),'input row hash'); need((r['sourceId'],r['locale'],r['sourceSha256'])==(c['sourceId'],c['locale'],c['sourceSha256']),'cell identity')
  if c['callerless']:
   holds+=1; need(r['decision']=='hold' and r['textIncluded'] is False and not any(k in r for k in ('source','currentTarget','proposedTarget','inputTokenEvidence','proposedTokenEvidence')),'callerless hold redaction'); need(r['currentTargetSha256']==c['currentTargetSha256'],'hold target hash')
  else:
   backed+=1; need(r['textIncluded'] is True and r['source']==c['source'] and r['currentTarget']==c['currentTarget'],'caller-backed text'); need(sha(r['source'])==c['sourceSha256'] and sha(r['currentTarget'])==c['currentTargetSha256']==r['currentTargetSha256'],'source/target hashes')
   need(c['placeholderMultisetMatches'] and c['markupMatches'] and c['numericTokensPreserved'] and c['protectedLiteralsPreserved'],'input token status')
   if r['decision']=='proposal': props+=1; need(token_pass(c['source'],r['proposedTarget']) and r['proposedTokenChecksPass'],'proposal tokens')
   else: need(r['decision']=='retain','caller-backed decision')
 need((holds,backed,props)==(12,228,1),'decision partition')
 need(s['cellCount']==240 and s['callerBackedCellCount']==228 and s['callerlessHashOnlyHoldCellCount']==12 and s['decisionCounts']==dict(counts),'summary counts')
 need(s['inputChecksumsFileSha256']==sha((a.input/'SHA256SUMS.txt').read_bytes()),'summary input checksum hash')
 need(s['proposalTokenResults']['proposalsChecked']==1 and s['proposalTokenResults']['passingProposals']==1 and s['proposalTokenResults']['failingProposals']==0,'summary proposal token results')
 print(json.dumps({'result':'PASS','inputAndOutputChecksums':'PASS','head':HEAD,'tree':TREE,'worktreeClean':True,'callerFilesVerified':sorted(pinned),'cells':240,'decisionCounts':dict(counts),'callerlessTextFreeHolds':12,'proposalTokenChecksPassing':props},indent=2))
if __name__=='__main__': main()
