#!/usr/bin/env python3
"""Verify the ROMarrNG PR #70 W545-W564 catalog application evidence."""
import argparse,collections,hashlib,json,pathlib,re,subprocess
HERE=pathlib.Path(__file__).resolve().parent
HEAD='ed82a904e85a95a7f350e6f62d8f06139098054b'; PRODUCT='2a921d8280487f6d172616719f32e3dced243d83'; PRODUCT_TREE='21996ad9dcfcc6535e52920b36d74c8a9357279f'; CATALOG='romarr/ui-labels.json'; WINDOW='W545-W564'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED={('ui.indexer.4a8a73e215','ar'):{'position':557,'target':'المفهرس','sha256':'15af2a1752a1155011026d1f7dbe02f0ffa311d91530da2341f147560825824d'},('ui.info-and-up.c9f2eef041','vi'):{'position':559,'target':'Mức Info trở lên','sha256':'5ff337aaacb7bd9e1dd3a9990d1aa00b87150a39bdff16674f7e8c19d4fddc99'}}
TEXT={'source','sourceText','currentTarget','target','targetText','proposedTarget','selectedTarget','finalTarget'}
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','Moonlight']
def fail(m): raise SystemExit('FAIL: '+m)
def need(v,m):
 if not v: fail(m)
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def j(path): return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def jl(path): return [json.loads(x) for x in pathlib.Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def protected(s):
 out=[]
 for term in PROTECTED:
  if re.search(r'(?<![A-Za-z0-9])'+re.escape(term)+r'(?![A-Za-z0-9])',s): out.append(term)
 if re.search(r'(?<![A-Za-z0-9])DATs?(?![A-Za-z0-9])',s) and 'DAT' not in out: out.append('DAT')
 return sorted(set(out))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True); repo=ap.parse_args().repo.resolve()
 # Packet checksum and inventory.
 sums={}
 for line in (HERE/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  if line.strip():
   h,n=line.split('  ',1); p=(HERE/n).resolve(); need(p.is_relative_to(HERE.resolve()) and p.is_file(),'unsafe/missing checksum '+n); need(sha(p.read_bytes())==h,'checksum '+n); sums[n]=h
 actual={p.name for p in HERE.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}; need(set(sums)==actual,'checksum coverage')
 manifest=j(HERE/'manifest.json'); need((manifest['productCommit'],manifest['head'],manifest['window'])==(PRODUCT,HEAD,WINDOW),'manifest pin')
 listed={x['path']:x for x in manifest['files']}; need(set(listed)==actual-{'manifest.json'},'manifest coverage')
 for n,x in listed.items():
  b=(HERE/n).read_bytes(); need(len(b)==x['bytes'] and sha(b)==x['sha256'],'manifest hash '+n)
 summary=j(HERE/'application-summary.json'); pins=j(HERE/'catalog-pins.json')
 need((summary['preHead'],summary['productCommit'],summary['productTree'],summary['window'])==(HEAD,PRODUCT,PRODUCT_TREE,WINDOW),'application commit/tree')
 need(git(repo,'rev-parse',PRODUCT).decode().strip()==PRODUCT and git(repo,'rev-parse',PRODUCT+'^{tree}').decode().strip()==PRODUCT_TREE,'product commit readback')
 need(git(repo,'rev-parse',PRODUCT+'^').decode().strip()==HEAD,'product parent')
 need(git(repo,'diff-tree','--no-commit-id','--name-only','-r',PRODUCT).decode().splitlines()==[CATALOG],'product commit file scope')
 need(git(repo,'merge-base','--is-ancestor',PRODUCT,'HEAD').decode()=='','product commit ancestry')
 before_raw=git(repo,'show',f'{HEAD}:{CATALOG}'); after_raw=git(repo,'show',f'{PRODUCT}:{CATALOG}')
 before=json.loads(before_raw); after=json.loads(after_raw)
 need(sha(before_raw)==pins['preCatalogSha256'] and sha(after_raw)==pins['postCatalogSha256'],'catalog byte hashes')
 need(git(repo,'rev-parse',f'{HEAD}:{CATALOG}').decode().strip()==pins['preCatalogGitBlob'] and git(repo,'rev-parse',f'{PRODUCT}:{CATALOG}').decode().strip()==pins['postCatalogGitBlob'],'catalog git blobs')
 need(len(before['messages'])==len(after['messages'])==1836 and list(before['messages'])==list(after['messages']),'catalog key order/count')
 need(list(before['locales'])==list(after['locales'])==pins['localeOrder'],'locale order')
 need(sha('\n'.join(before['messages'])+'\n')==pins['catalogKeyOrderSha256'],'catalog key order hash')
 readback=jl(HERE/'application-readback.jsonl'); need(len(readback)==240 and len({(x['sourceId'],x['locale']) for x in readback})==240,'240-cell readback coverage')
 cells={(x['sourceId'],x['locale']):x for x in readback}; selected=jl(HERE/'selected-changes.jsonl'); smap={(x['sourceId'],x['locale']):x for x in selected}; holds=jl(HERE/'holds.jsonl'); hmap={(x['sourceId'],x['locale']):x for x in holds}
 need(set(smap)==set(EXPECTED) and len(selected)==2,'selected changes')
 need(len(hmap)==12 and {k for k,v in cells.items() if v['disposition']=='hold-text-free'}==set(hmap),'text-free hold mapping')
 # The catalog must differ in exactly the two selected translation values.
 normalized=json.loads(json.dumps(before,ensure_ascii=False))
 for sid,old in before['messages'].items():
  new=after['messages'][sid]
  need(list(old)==list(new) and list(old['translations'])==list(new['translations']),'message/locale property order '+sid)
  need(old['source']==new['source'] and old['sourceHash']==new['sourceHash'],'source changed '+sid)
  for field in ('translationHashes','translationStatus','translationReview'):
   need(old.get(field)==new.get(field),'translation metadata changed '+sid+'/'+field)
  for loc in old['translations']:
   k=(sid,loc)
   if k in EXPECTED:
    e=EXPECTED[k]; need(e['position']==list(before['messages']).index(sid),'selected ordinal '+sid)
    need(old['translations'][loc]==smap[k]['currentTarget'] and sha(old['translations'][loc])==smap[k]['currentTargetSha256'],'selected preimage '+sid+'/'+loc)
    need(new['translations'][loc]==e['target'] and sha(new['translations'][loc])==e['sha256']==smap[k]['selectedTargetSha256'],'selected result '+sid+'/'+loc)
    normalized['messages'][sid]['translations'][loc]=new['translations'][loc]
   else: need(old['translations'][loc]==new['translations'][loc],'unselected locale changed '+sid+'/'+loc)
 need(normalized==after,'non-target catalog data changed')
 order=list(before['messages']); order_index={sid:i for i,sid in enumerate(order)}
 # Exact readback source/target hashes and token parity across every reviewed cell.
 for row in readback:
  k=(row['sourceId'],row['locale']); sid,loc=k; need(k in {(sid,l) for sid in order[545:565] for l in LOCALES},'cell outside window '+str(k))
  c=before['messages'][sid]; n=after['messages'][sid]; src=c['source']; old=c['translations'][loc]; new=n['translations'][loc]
  need(row['position']==order_index[sid] and row['catalogZeroBasedIndex']==order_index[sid] and row['sourceSha256']==sha(src)==c['sourceHash'],'readback source/order '+str(k))
  need(row['beforeTargetSha256']==sha(old) and row['afterTargetSha256']==sha(new),'readback target hash '+str(k))
  changed=old!=new; need(row['changed']==changed,'readback changed flag '+str(k))
  expected=EXPECTED.get(k)
  if expected:
   need(row['disposition']=='selected-change' and changed and row['selectedTargetSha256']==expected['sha256'],'readback selected change '+str(k))
  elif row['disposition']=='hold-text-free':
   need(not changed and row['selectedTargetSha256'] is None,'held cell changed '+str(k))
  else: need(row['disposition']=='keep-current' and not changed,'kept cell changed '+str(k))
  st={'ph':collections.Counter(PH.findall(src)),'tag':collections.Counter(TAG.findall(src)),'num':collections.Counter(NUM.findall(src)),'prot':protected(src)}
  for target in (old,new):
   need(collections.Counter(PH.findall(target))==st['ph'],'placeholder parity '+str(k))
   need(collections.Counter(TAG.findall(target))==st['tag'],'markup parity '+str(k))
   tn=collections.Counter(NUM.findall(target)); extra=list((tn-st['num']).elements()); wordzero=bool(re.search(r'\bzero\b',src,re.I)) and not st['num'] and extra==['0']
   need(not(st['num']-tn) and (not extra or wordzero),'numeric parity '+str(k))
   need(all(t in target for t in st['prot']),'protected literal parity '+str(k))
 # Callerless holds are text-free in both application evidence files.
 for k,h in hmap.items():
  need(k[0]=='ui.install-a-plugin-straight-from-its-r.48f09f7ee3' and not(TEXT & set(h)),'hold contains text '+str(k))
  r=cells[k]; need(h['sourceSha256']==r['sourceSha256'] and h['currentTargetSha256']==r['beforeTargetSha256']==r['afterTargetSha256'],'hold hash linkage '+str(k))
 for row in selected:
  k=(row['sourceId'],row['locale']); need(row['selectedTarget']==EXPECTED[k]['target'] and row['selectedTargetSha256']==EXPECTED[k]['sha256'],'selected list target '+str(k))
 # Saved PR attestations show the live refs before changes and after product push.
 for name,expected_head in [('PR-attestation-before.json',HEAD),('PR-attestation-after-product.json',PRODUCT)]:
  a=j(HERE/name); need(a['head']==expected_head and a['branchRefOid']==expected_head and a['pullRefOid']==expected_head and a['state']=='OPEN' and a['draft'] is True and a['mergeable']=='MERGEABLE','saved PR attestation '+name)
  need(a['baseApiRefMismatch']==(a['baseApiSha']!=a['baseLiveRefOid']) and a['checksRerun'] is False,'saved base/check details '+name)
 need(summary['readbackCellCount']==240 and summary['changedCellCount']==2 and summary['keptCurrentCellCount']==226 and summary['textFreeHoldCount']==12,'summary counts')
 need(summary['placeholderMismatches']==summary['markupMismatches']==summary['numericMismatches']==summary['protectedLiteralMismatches']==0,'summary token mismatches')
 print(json.dumps({'result':'PASS','productCommit':PRODUCT,'productTree':PRODUCT_TREE,'cells':240,'changed':2,'unchanged':226,'textFreeHolds':12,'catalogFilesChanged':1,'tokenMismatches':0},sort_keys=True))
if __name__=='__main__': main()
