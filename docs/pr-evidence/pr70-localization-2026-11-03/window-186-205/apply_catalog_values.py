#!/usr/bin/env python3
"""Apply only root-ratified ROMarrNG W186-W205 values at the pinned head."""
from __future__ import annotations
import copy, hashlib, json, os, re, subprocess, tempfile
from collections import Counter
from pathlib import Path

ROOT=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
EVIDENCE=ROOT/'docs/pr-evidence/pr70-localization-2026-11-03/window-186-205'
INPUT=EVIDENCE/'input'
LEDGER=EVIDENCE/'root-adjudication/ratified-ledger.jsonl'
PLAN=EVIDENCE/'apply-plan.json'
CATALOG='romarr/ui-labels.json'
EXPECTED_HEAD='55ee760ea9600f71cc27cba35e098a082445dac8'
EXPECTED_TREE='dbc192813f6347f4307ff8417d505624958eb321'


def read_json(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def read_jsonl(p:Path): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def canon(v)->str: return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
def git(*args, binary=False): return subprocess.check_output(['git',*args],cwd=ROOT,text=not binary)
def check_literals(source,target,structure):
    expected=set(structure.get('sourceBundlePlaceholders',[]))|set(structure.get('sourceRegexPlaceholders',[]))
    actual=set(re.findall(r'\{([^{}]+)\}',target))
    assert expected==actual,(expected,actual)
    protected=set(structure.get('sourceProtectedLiterals',[]))|set(structure.get('sourceVersionLiterals',[]))|set(structure.get('sourceMarkupTags',[]))
    for item in protected:
        if item and item in source:
            assert item in target, f'protected literal missing: {item}'

def main():
    manifest=read_json(INPUT/'manifest.json')
    pins=read_json(INPUT/'head-and-file-pins.json')
    plan=read_json(PLAN)
    assert manifest['head']==pins['head']==plan['head']==EXPECTED_HEAD
    assert manifest['tree']==pins['tree']==plan['tree']==EXPECTED_TREE
    assert git('rev-parse','HEAD').strip()==EXPECTED_HEAD
    assert git('rev-parse','HEAD^{tree}').strip()==EXPECTED_TREE
    assert git('status','--porcelain','--untracked-files=no').strip()=='', 'tracked worktree changes existed before apply'
    assert plan['catalogFile']==CATALOG and plan['changeCount']==43
    assert sha((INPUT/'manifest.json').read_bytes())==plan['inputManifestSha256']
    assert sha(LEDGER.read_bytes())==plan['rootLedgerSha256']

    # Recheck every sealed source/caller file against the exact Git tree.
    file_pins=pins['filePins']
    assert len(file_pins)==56
    for path,pin in file_pins.items():
        raw=git('show',f'{EXPECTED_HEAD}:{path}',binary=True)
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        assert blob==pin['gitBlob'] and len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],path

    input_rows=read_jsonl(INPUT/'review-input.jsonl')
    ledger=read_jsonl(LEDGER)
    assert len(input_rows)==len(ledger)==240
    inputs={(r['id'],r['locale']):r for r in input_rows}
    decisions={(r['id'],r['locale']):r for r in ledger}
    assert len(inputs)==len(decisions)==240 and inputs.keys()==decisions.keys()
    plan_items={(r['id'],r['locale']):r for r in plan['items']}
    assert len(plan_items)==43

    catalog_pin=file_pins[CATALOG]
    baseline_raw=git('show',f'HEAD:{CATALOG}',binary=True)
    baseline_blob=git('rev-parse',f'HEAD:{CATALOG}').strip()
    assert sha(baseline_raw)==catalog_pin['sha256']==plan['catalogFileSha256']
    assert baseline_blob==catalog_pin['gitBlob']==plan['catalogGitBlob']
    assert len(baseline_raw)==catalog_pin['bytes']==plan['catalogBytes']
    baseline=json.loads(baseline_raw)
    assert (json.dumps(baseline,ensure_ascii=False,indent=2)+'\n').encode('utf-8')==baseline_raw
    assert 'messages' in baseline and isinstance(baseline['messages'],dict)
    assert len(baseline['messages'])==1837
    catalog=json.loads((ROOT/CATALOG).read_text(encoding='utf-8'))
    assert catalog==baseline, 'catalog changed before guarded apply'
    assert list(catalog['messages'])==list(baseline['messages'])

    updates={}
    by_ordinal={r['sourceOrdinal']:r for r in read_jsonl(INPUT/'source-structure.jsonl')}
    for key,row in inputs.items():
        d=decisions[key]
        entry=baseline['messages'][row['id']]
        assert d['sourceOrdinal']==row['sourceOrdinal']
        assert d['sourceSha256']==row['sourceSha256'] and entry['source']==row['source'] and entry['sourceHash']==row['sourceSha256']
        assert entry['translations'][row['locale']]==row['currentTarget']
        assert entry['translationHashes'][row['locale']]==row['currentTargetSha256']==canon(row['currentTarget'])
        assert entry['translationStatus'][row['locale']]=='draft'==row['translationStatus']
        assert d['currentTarget']==row['currentTarget'] and d['currentTargetSha256']==row['currentTargetSha256']
        disposition=d['rootDisposition']
        assert disposition in ('accept-current','correction','refinement','hold')
        expected=d['adjudicatedTarget']
        assert canon(expected)==d['adjudicatedTargetSha256']
        if disposition in ('correction','refinement'):
            plan_item=plan_items[key]
            assert (plan_item['sourceOrdinal'],plan_item['sourceSha256'],plan_item['currentTarget'],plan_item['currentTargetSha256'])==(row['sourceOrdinal'],row['sourceSha256'],row['currentTarget'],row['currentTargetSha256'])
            assert plan_item['target']==expected and plan_item['targetSha256']==d['adjudicatedTargetSha256']
            assert plan_item['disposition']==disposition and expected!=row['currentTarget']
            check_literals(row['source'],expected,by_ordinal[row['sourceOrdinal']])
            updates[key]=expected
        else:
            assert key not in plan_items and expected==row['currentTarget']
        assert expected==row['currentTarget'] if disposition in ('accept-current','hold') else True
    assert set(plan_items)==set(updates) and len(updates)==43

    updated=copy.deepcopy(baseline)
    for (message_id,locale),target in updates.items():
        updated['messages'][message_id]['translations'][locale]=target
        updated['messages'][message_id]['translationHashes'][locale]=canon(target)
    assert list(updated)==list(baseline) and list(updated['messages'])==list(baseline['messages'])
    assert updated.keys()==baseline.keys()

    # The only allowed differences are the 43 translation and translationHashes leaves.
    allowed={(message_id,field,locale) for message_id,locale in updates for field in ('translations','translationHashes')}
    for message_id,before in baseline['messages'].items():
        after=updated['messages'][message_id]
        assert before.keys()==after.keys()
        for field in before:
            if field in ('translations','translationHashes'):
                assert before[field].keys()==after[field].keys()
                for locale in before[field]:
                    if (message_id,field,locale) not in allowed:
                        assert before[field][locale]==after[field][locale]
            else:
                assert before[field]==after[field],(message_id,field)

    payload=(json.dumps(updated,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    target_path=ROOT/CATALOG
    with tempfile.NamedTemporaryFile(prefix='.ui-labels.w186-205-',dir=target_path.parent,delete=False) as handle:
        temp=Path(handle.name); handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    try: os.replace(temp,target_path)
    finally: temp.unlink(missing_ok=True)

    actual_raw=target_path.read_bytes(); actual=json.loads(actual_raw)
    assert actual==updated
    assert list(actual['messages'])==list(baseline['messages']) and len(actual['messages'])==1837
    assert len(actual['messages'])==len(baseline['messages'])
    before_key_digest=sha('\n'.join(baseline['messages']).encode())
    after_key_digest=sha('\n'.join(actual['messages']).encode())
    assert before_key_digest==after_key_digest
    rows=[]; counts=Counter(); mismatch=0
    for key,row in inputs.items():
        d=decisions[key]; msg=actual['messages'][row['id']]
        expected=d['adjudicatedTarget']; expected_hash=d['adjudicatedTargetSha256']
        actual_value=msg['translations'][row['locale']]; actual_hash=msg['translationHashes'][row['locale']]
        status=msg['translationStatus'][row['locale']]
        match=actual_value==expected and actual_hash==expected_hash==canon(actual_value) and status=='draft'
        assert match,(key,actual_value,expected,actual_hash,expected_hash,status)
        counts[d['rootDisposition']]+=1
        rows.append({
            'sourceOrdinal':row['sourceOrdinal'],'id':row['id'],'locale':row['locale'],
            'rootDisposition':d['rootDisposition'],'sourceSha256':row['sourceSha256'],
            'previousTarget':row['currentTarget'],'previousTargetSha256':row['currentTargetSha256'],
            'expectedTarget':expected,'expectedTargetSha256':expected_hash,
            'actualTarget':actual_value,'actualTranslationHash':actual_hash,'translationStatus':status,
            'changed':actual_value!=row['currentTarget'],'match':match
        })
    assert counts=={'accept-current':137,'correction':17,'refinement':26,'hold':60},counts
    assert sum(r['changed'] for r in rows)==43
    readback={
        'artifact':'ROMarrNG PR #70 W186-W205 catalog readback',
        'repository':'snapetech-org/ROMarrNG','pullRequest':70,
        'baselineHead':EXPECTED_HEAD,'baselineTree':EXPECTED_TREE,'window':'W186-W205',
        'catalogFile':CATALOG,'baselineCatalogSha256':sha(baseline_raw),
        'finalCatalogSha256':sha(actual_raw),'baselineCatalogGitBlob':baseline_blob,
        'messageKeyCountBefore':len(baseline['messages']),'messageKeyCountAfter':len(actual['messages']),
        'orderedMessageKeysSha256Before':before_key_digest,'orderedMessageKeysSha256After':after_key_digest,
        'rootDispositionCounts':dict(counts),'appliedTargetCount':sum(r['changed'] for r in rows),
        'verifiedCellCount':len(rows),'mismatchCount':mismatch,
        'translationStatusPreserved':'draft for all 240 reviewed cells',
        'fieldStructurePreserved':True,'workflowFilesChanged':False,'rows':rows
    }
    (EVIDENCE/'readback.json').write_text(json.dumps(readback,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Applied 43 exact-hash targets and hashes; verified 240 cells, zero mismatches; message keys {before_key_digest} unchanged.")

if __name__=='__main__': main()
