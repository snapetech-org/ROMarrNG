#!/usr/bin/env python3
from __future__ import annotations
import argparse,collections,hashlib,json,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent; HEAD='5860fce5d546a772b1df995f8f6321c083ed7d5d'; TREE='561835895972a62e9d3b1f2bfe9bcba01187eb98'
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight']
def sha(b): return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def need(v,s):
 if not v: raise SystemExit('FAIL: '+s)
def sums(root,name):
 d={}
 for line in (root/name).read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  h,n=line.split('  ',1); p=(root/n).resolve(); need(p.is_relative_to(root.resolve()) and p.is_file() and sha(p.read_bytes())==h,'checksum '+n); need(n not in d,'duplicate checksum '+n); d[n]=h
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/name}; need(set(d)==actual,'checksum coverage '+str(root)); return d
def protected(s):
 out=[t for t in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',s)]
 if re.search(r'(?<![A-Za-z0-9])DATs?(?![A-Za-z0-9])',s) and 'DAT' not in out: out.append('DAT')
 return sorted(set(out))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True); a=ap.parse_args(); repo=a.repo.resolve(); root_hashes=sums(ROOT,'SHA256SUMS.txt')
 pre=j(ROOT/'PRIMARY-REVIEW-MANIFEST.json'); need((pre.get('head'),pre.get('tree'),pre.get('window'))==(HEAD,TREE,'W625-W644'),'primary pin')
 need(pre.get('otherW625ReviewDecisionsAccessed') is False and pre.get('blindOutputInspected') is False and pre.get('semanticReviewStartedBeforeSeal') is False,'review separation')
 cf=ROOT/'candidate-free-bundle'; cfm=j(cf/'bundle-manifest.json'); need((cfm.get('head'),cfm.get('tree'),cfm.get('window'))==(HEAD,TREE,'W625-W644'),'copied candidate-free pin')
 need(sha((cf/'bundle-manifest.json').read_bytes())==pre['candidateFreeBundleManifestSha256'],'candidate-free manifest hash')
 need(sha((cf/'SHA256SUMS.txt').read_bytes())==pre['copiedCandidateFreeBundleChecksumListSha256'],'candidate-free checksum list')
 subprocess.run([sys.executable,str(cf/'verify_bundle.py'),'--repo',str(repo)],check=True)
 out=ROOT/'primary-output'; sums(out,'SHA256SUMS.txt'); om=j(out/'primary-manifest.json'); actual={p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS.txt'}; expected={x['path']:x for x in om['files']}
 need(set(expected)==actual-{'primary-manifest.json'},'primary output file set')
 for n,x in expected.items(): need((out/n).stat().st_size==x['bytes'] and sha((out/n).read_bytes())==x['sha256'],'primary output manifest '+n)
 ci=cf/'candidate-free/input'; cells=lines(ci/'current-target-cells.jsonl'); contexts={x['sourceId']:x for x in lines(ci/'source-contexts.jsonl')}; cmap={(x['sourceId'],x['locale']):x for x in cells}; dec=lines(out/'dispositions.jsonl')
 need(len(cells)==240 and len(dec)==240,'cell count'); seen=set(); counts=collections.Counter(); changes=[]
 for d in dec:
  key=(d.get('sourceId'),d.get('locale')); need(key in cmap and key not in seen,'unknown/duplicate cell'); seen.add(key); c=cmap[key]; ctx=contexts[key[0]]
  need((d.get('window'),d.get('position'),d.get('sourceSha256'),d.get('currentTargetSha256'),d.get('callerContextSha256'))==('W625-W644',c['position'],c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256']),'cell identity/hash')
  need(d.get('callerContextAvailable') is (not ctx['callerless']),'caller context state')
  disp=d.get('disposition'); counts[disp]+=1
  if disp=='KEEP': need('proposedTarget' not in d and 'reason' not in d,'KEEP has proposal')
  elif disp=='CHANGE':
   t=d.get('proposedTarget'); s=c['source']; need(isinstance(t,str) and t and t!=c['currentTarget'],'missing/no-op proposal'); need(isinstance(d.get('reason'),str) and d['reason'],'missing reason')
   need(collections.Counter(PH.findall(s))==collections.Counter(PH.findall(t)),'proposal placeholder mismatch')
   need(collections.Counter(TAG.findall(s))==collections.Counter(TAG.findall(t)),'proposal markup mismatch')
   need(not (collections.Counter(NUM.findall(s))-collections.Counter(NUM.findall(t))),'proposal numeric token loss')
   for literal in c['sourceProtectedLiterals']: need(literal in t,'proposal protected literal loss '+literal)
   changes.append(d)
  elif disp=='HOLD': need(not any(k in d for k in ('source','currentTarget','target','proposedTarget','reason')),'HOLD contains text')
  else: need(False,'unknown disposition '+str(disp))
 need(seen==set(cmap),'coverage'); holds=lines(out/'hash-only-holds.jsonl'); need(len(holds)==counts['HOLD'],'hold ledger count')
 summary=j(out/'summary.json'); need(summary.get('dispositionCounts')==dict(counts),'summary counts'); need(summary.get('proposedChangeCount')==len(changes),'summary change count')
 need((summary.get('sourceCount'),summary.get('localeCount'),summary.get('cellCount'))==(20,12,240),'summary window counts')
 need(summary.get('blindness',{}).get('blindOutputInspected') is False and summary.get('blindness',{}).get('otherW625ReviewDecisionsAccessed') is False,'blindness declaration')
 need(not any('blind' in p.lower() for p in root_hashes),'blind file in primary packet')
 print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sourceCount':20,'cellCount':240,'dispositionCounts':dict(counts),'proposals':len(changes),'proposalsWithoutCallerContext':summary['callerCoverage']['proposedChangesWithoutCallerContext'],'candidateFreeVerifier':'PASS','checksums':'PASS','blindOutputInspected':False},sort_keys=True))
if __name__=='__main__': main()
