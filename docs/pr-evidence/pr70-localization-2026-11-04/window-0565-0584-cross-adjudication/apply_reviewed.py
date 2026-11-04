#!/usr/bin/env python3
"""Apply only the cross-selected ROMarrNG W565-W584 cell with exact hash guards."""
import argparse, hashlib, json, re
from pathlib import Path
PIN_HEAD = '726db9138af2fc716056c7c36a9e842de04265e0'
CATALOG_PATH = 'romarr/ui-labels.json'
def sha(b): return hashlib.sha256(b if isinstance(b, bytes) else b.encode('utf-8')).hexdigest()
def key_order_hash(keys): return sha(('\n'.join(keys)+'\n').encode('utf-8'))
def object_end(text, start):
    depth=0; quoted=False; escaped=False
    for i in range(start, len(text)):
        ch=text[i]
        if quoted:
            if escaped: escaped=False
            elif ch=='\\': escaped=True
            elif ch=='"': quoted=False
        else:
            if ch=='"': quoted=True
            elif ch=='{': depth += 1
            elif ch=='}':
                depth -= 1
                if depth==0: return i+1
    raise ValueError('unterminated JSON object')
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--cross-packet',type=Path,required=True)
    ap.add_argument('--candidate-free',type=Path,required=True)
    args=ap.parse_args(); repo=args.repo.resolve(); cross=args.cross_packet.resolve(); cf=args.candidate_free.resolve()
    selected=[json.loads(x) for x in (cross/'selected-changes.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(selected)!=1: raise SystemExit('expected exactly one cross-selected change')
    row=selected[0]
    if row['window']!='W565-W584' or row['catalogZeroBasedIndex']!=573 or row['sourceId']!='ui.invitation.af4ea02852' or row['locale']!='de': raise SystemExit('unexpected selected-cell identity')
    path=repo/CATALOG_PATH
    raw=path.read_bytes(); before_sha=sha(raw)
    manifest=json.loads((cf/'manifest.json').read_text(encoding='utf-8'))
    if manifest['head']!=PIN_HEAD or manifest['catalogPath']!=CATALOG_PATH or before_sha!=manifest['catalogSha256']: raise SystemExit('catalog preimage pin mismatch')
    data=json.loads(raw.decode('utf-8'))
    if list(data['messages'])[573]!=row['sourceId'] or data['messages'][row['sourceId']]['source']!=row['sourceText'] or data['messages'][row['sourceId']]['sourceHash']!=row['sourceSha256']: raise SystemExit('source/order/hash guard failed')
    if key_order_hash(list(data['messages']))!=manifest['catalogKeyOrderSha256']: raise SystemExit('catalog key order guard failed')
    if manifest['locales']!=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant'] or not all(loc in data['locales'] for loc in manifest['locales']): raise SystemExit('review locale inventory guard failed')
    locale_registry_order=list(data['locales'])
    item=data['messages'][row['sourceId']]
    old=item['translations'][row['locale']]
    new=row['recommendedTarget']
    if old!=row['currentTarget'] or sha(old)!=row['currentTargetSha256']: raise SystemExit('exact current-target hash guard failed')
    if sha(new)!=row['recommendedTargetSha256']: raise SystemExit('selected target hash mismatch')
    marker=json.dumps(row['sourceId'],ensure_ascii=False)
    matches=list(re.finditer(re.escape(marker)+r'\s*:\s*\{',raw.decode('utf-8')))
    if len(matches)!=1: raise SystemExit('source object textual location is not unique')
    text=raw.decode('utf-8'); start=matches[0].end()-1; end=object_end(text,start)
    segment=text[start:end]
    old_literal=json.dumps(old,ensure_ascii=False)
    target_pattern=re.compile(r'("'+re.escape(row['locale'])+r'"\s*:\s*)'+re.escape(old_literal))
    found=list(target_pattern.finditer(segment))
    if len(found)!=1: raise SystemExit('selected translation literal is not unique within source object')
    replaced=target_pattern.sub(lambda m:m.group(1)+json.dumps(new,ensure_ascii=False),segment,count=1)
    updated=text[:start]+replaced+text[end:]
    after_data=json.loads(updated)
    if after_data['messages'][row['sourceId']]['translations'][row['locale']]!=new: raise SystemExit('write simulation failed')
    before_copy=json.loads(raw)
    before_copy['messages'][row['sourceId']]['translations'][row['locale']]=new
    if before_copy!=after_data: raise SystemExit('write simulation changes additional JSON data')
    path.write_bytes(updated.encode('utf-8'))
    final=path.read_bytes(); actual=json.loads(final.decode('utf-8'))
    if actual['messages'][row['sourceId']]['translations'][row['locale']]!=new or sha(new)!=row['recommendedTargetSha256']: raise SystemExit('post-write readback failed')
    if list(actual['locales'])!=locale_registry_order: raise SystemExit('locale registry order changed')
    print(json.dumps({'result':'APPLIED','catalogPath':CATALOG_PATH,'catalogPreSha256':before_sha,'catalogPostSha256':sha(final),'catalogKeyOrderPreserved':key_order_hash(list(actual['messages']))==manifest['catalogKeyOrderSha256'],'sourceId':row['sourceId'],'locale':row['locale'],'index':row['catalogZeroBasedIndex'],'beforeTargetSha256':sha(old),'afterTargetSha256':sha(new),'changedCellCount':1},ensure_ascii=False))
if __name__=='__main__': main()
