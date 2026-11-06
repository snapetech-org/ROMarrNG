#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,re
ROOT=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-erratum-20261105')
ORIG=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-integrated-cross-review-20261105')
BLIND=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-independent-blind-20261105/blind-review')
KEY=('ui.optional-connections-to-the-rest-of.636208f858','fr')
def sha(v):
 if isinstance(v,str):v=v.encode('utf-8')
 return hashlib.sha256(v).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def load(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rows(p):return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_dir(root):
 root=pathlib.Path(root); sums=root/'SHA256SUMS.txt'; found={}
 for line in sums.read_text(encoding='utf-8').splitlines():
  if not line:continue
  digest,name=line.split('  ',1); p=(root/name).resolve()
  if name in found or not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=digest:raise SystemExit('checksum failure '+str(root/name))
  found[name]=digest
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}
 if actual!=set(found):raise SystemExit('checksum inventory mismatch '+str(root))
 return {'checksumListSha256':sha(sums.read_bytes()),'files':len(found)}
def main():
 op=verify_dir(ORIG); bp=verify_dir(BLIND); ep=verify_dir(ROOT)
 if op['checksumListSha256']!='45ad89aa23ef002858e25e63f1633ff30e1f2088db3b45b9bc4dd365bb2597e9':raise SystemExit('original packet checksum list changed')
 if bp['checksumListSha256']!='bd04db544a64f81b827d90ed4de93b1806d9efc61ad77d2d15fcf6427bf2651d':raise SystemExit('blind packet checksum list changed')
 if sha((ORIG/'integrated-cross-ledger.jsonl').read_bytes())!='fb5c18ce6f7d55b92d5b626d6bae2d09f2e6c717496951a220b299c83ee058f9':raise SystemExit('original cross ledger file hash changed')
 if sha((BLIND/'blind-locale-review.jsonl').read_bytes())!='ad68f4e63e37ee52140bb969747b6aad8dba9f477d7205df62f2bfddd40ff23e':raise SystemExit('blind proposal file hash changed')
 cross=next(x for x in rows(ORIG/'integrated-cross-ledger.jsonl') if (x['sourceId'],x['locale'])==KEY)
 blind=next(x for x in rows(BLIND/'blind-locale-review.jsonl') if (x['sourceId'],x['locale'])==KEY)
 evidence=rows(ROOT/'evidence-rows.jsonl')
 if len(evidence)!=2 or evidence[0].get('role')!='integrated-cross-ledger-row' or evidence[1].get('role')!='blind-locale-review-row':raise SystemExit('evidence row inventory mismatch')
 if evidence[0].get('record')!=cross or evidence[1].get('record')!=blind:raise SystemExit('evidence rows differ from sealed inputs')
 err=load(ROOT/'erratum.json')
 if err.get('originalCrossRowSha256')!=sha(canon(cross)) or err.get('blindRowSha256')!=sha(canon(blind)):raise SystemExit('row hash binding mismatch')
 if cross.get('blindProposal')!=blind.get('proposal') or cross.get('blindProposalSha256')!=blind.get('proposalSha256') or sha(blind.get('proposal',''))!=blind.get('proposalSha256'):raise SystemExit('proposal text/hash mismatch')
 phrase='Connexions facultatives au reste de la pile.'
 if not blind.get('proposal','').startswith(phrase):raise SystemExit('blind proposal plural wording mismatch')
 if re.search(r'Connexions facultative(?!s)',blind.get('proposal','')):raise SystemExit('blind proposal unexpectedly has singular agreement error')
 if 'Connexions facultative” should be “Connexions facultatives' not in cross.get('blindAlternativeFinding',''):raise SystemExit('reported stale finding not present')
 if 'facultatives' not in cross.get('currentTarget',''):raise SystemExit('current French target plural form missing')
 if cross.get('crossDisposition')!='accept-current' or cross.get('rootSelectionChangeRequired') is not False:raise SystemExit('root treatment changed')
 if err.get('findingStatus')!='unsupported-stale-finding' or err.get('correctRootTreatment')!='retain-accept-current-no-change':raise SystemExit('erratum disposition mismatch')
 manifest=load(ROOT/'manifest.json')
 if manifest.get('originalCrossPacketChecksumListSha256')!=op['checksumListSha256'] or manifest.get('head')!='9714d7cf69c687685b4f65cbd9627a56830bab85':raise SystemExit('erratum manifest input binding mismatch')
 files={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
 if files!=manifest.get('files'):raise SystemExit('erratum manifest file inventory/hash mismatch')
 print(json.dumps({'result':'PASS','findingStatus':'unsupported-stale-finding','cellId':cross['cellId'],'crossRowSha256':sha(canon(cross)),'blindRowSha256':sha(canon(blind)),'proposalSha256':blind['proposalSha256'],'rootTreatment':'retain accept-current; no change','originalChecksumListSha256':op['checksumListSha256'],'erratumChecksumListSha256':ep['checksumListSha256']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
