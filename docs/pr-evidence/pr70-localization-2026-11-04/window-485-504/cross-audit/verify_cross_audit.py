#!/usr/bin/env python3
"""Verify ROMarrNG PR #70 W485-W504 cross-audit against its pinned inputs."""
from pathlib import Path
import collections, hashlib, json, subprocess, sys
OUT=Path(__file__).resolve().parent
def fail(m): raise SystemExit('FAIL: '+m)
def digest(b): return hashlib.sha256(b).hexdigest()
def readjson(p): return json.loads(Path(p).read_text(encoding='utf-8'))
# Verify every supplied input packet file against the exact byte hash inventory.
pins=readjson(OUT/'input-pins.json')
for packet in pins['inputPackets']:
    root=Path(packet['root'])
    for f in packet['files']:
        p=root/f['path']
        if not p.is_file() or digest(p.read_bytes())!=f['sha256']: fail('input hash mismatch: '+str(p))
# Verify the candidate-free, primary, and blind packet manifests and 240 source/cell rows.
cf=Path(pins['inputPackets'][0]['root']); primary=Path(pins['inputPackets'][1]['root']); blind=Path(pins['inputPackets'][2]['root'])
manifest=readjson(cf/'manifest.json'); pm=readjson(primary/'manifest.json'); bm=readjson(blind/'manifest.json')
if (manifest['head'],manifest['tree'])!=(pins['head'],pins['tree']): fail('input pin head/tree mismatch')
if not (pm['head']==bm['head']==manifest['head']): fail('review head mismatch')
if not (pm['tree']==bm['tree']==manifest['tree']): fail('review tree mismatch')
if digest((cf/'manifest.json').read_bytes())!=pins['inputManifests']['candidateFree']: fail('candidate-free manifest digest mismatch')
if digest((primary/'manifest.json').read_bytes())!=pins['inputManifests']['primary']: fail('primary manifest digest mismatch')
if digest((blind/'manifest.json').read_bytes())!=pins['inputManifests']['independentBlind']: fail('blind manifest digest mismatch')
def lines(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines()]
cr=lines(cf/'current-target-cells.jsonl'); pr=lines(primary/'primary-ledger.jsonl'); br=lines(blind/'blind-ledger.jsonl'); xr=lines(OUT/'cross-ledger.jsonl'); contexts={r['position']:r for r in lines(cf/'source-contexts.jsonl')}
if any(len(x)!=240 for x in (cr,pr,br,xr)): fail('expected 240 rows per input/output ledger')
def idx(rows): return {(r['position'],r['locale']):r for r in rows}
C,P,B,X=(idx(rows) for rows in (cr,pr,br,xr))
# expected selected updates independently fixed by this adjudication
expected={(492,'ja'):'GitHub',(492,'pt-BR'):'GitHub',(497,'ar'):'جارٍ الإضافة إلى التنزيلات…',(497,'de'):'Wird zu den Downloads hinzugefügt…',(497,'es'):'Añadiendo a las descargas…',(497,'fr'):'Ajout aux téléchargements…',(497,'hi'):'डाउनलोड में जोड़ा जा रहा है…',(497,'id'):'Menambahkan ke unduhan…',(497,'ja'):'ダウンロードに追加中…',(497,'ko'):'다운로드에 추가 중…',(497,'pt-BR'):'Adicionando aos downloads…',(497,'vi'):'Đang thêm vào hàng đợi tải xuống…',(497,'zh-Hans'):'正在添加到下载队列…',(497,'zh-Hant'):'正在加入下載佇列…',(501,'vi'):'Đầu tệp cho biết'}
if set(X)!=set(C) or set(P)!=set(C) or set(B)!=set(C): fail('cell coverage mismatch')
counts=collections.Counter()
for k,r in X.items():
    c,p,b=C[k],P[k],B[k]
    if r['head']!=manifest['head'] or r['tree']!=manifest['tree']: fail('row head/tree mismatch '+str(k))
    for f in ('source','sourceId','sourceSha256','currentTargetSha256','catalogTranslationHash'):
        want={'sourceId':'sourceId','source':'source','sourceSha256':'sourceSha256','currentTargetSha256':'currentTargetSha256','catalogTranslationHash':'catalogTranslationHash'}[f]
        if r[f]!=c[want]: fail(f'candidate-free mismatch {k} {f}')
    if r['callerContextSha256']!=p['inputCallerContextSha256'] or r['callerContextSha256']!=b['callerContextSha256']: fail('caller-context pin mismatch '+str(k))
    ctx=contexts[k[0]]
    if r['callerContextRefs']!=ctx['callerContextRefs'] or r['sourceIdExactMatchCount']!=ctx['sourceIdExactMatchCount'] or r['sourceTextExactMatchCount']!=ctx['sourceTextExactMatchCount']: fail('caller evidence mismatch '+str(k))
    if r['catalogPath']!=manifest['catalogPath'] or r['catalogSha256']!=manifest['catalogSha256'] or r['catalogKeyOrderSha256']!=manifest['catalogKeyOrderSha256']: fail('catalog pin mismatch '+str(k))
    if r.get('primaryRationale')!=p['rationale'] or r.get('blindRationale')!=b['blindRationale']: fail('review rationale missing or mismatched '+str(k))
    if r.get('primaryConfidence')!=p['confidence'] or r.get('blindConfidence')!=b['confidence']: fail('review confidence missing or mismatched '+str(k))
    if r['primaryDisposition']!=p['disposition'] or r['blindDisposition']!=b['blindDisposition']: fail('review disposition mismatch '+str(k))
    if (p['disposition'],p['proposedTarget'])!=(b['blindDisposition'],b['proposedTarget']): fail('primary/blind conflict recorded incorrectly '+str(k))
    if k in expected:
        if r['crossDisposition']!=p['disposition'] or r.get('selectedTarget')!=expected[k]: fail('selected proposal mismatch '+str(k))
        if r.get('currentTarget')!=c['currentTarget'] or digest(r['currentTarget'].encode())!=r['currentTargetSha256']: fail('current target text/hash mismatch '+str(k))
        if r.get('selectedTargetSha256')!=digest(expected[k].encode()): fail('selected target hash mismatch '+str(k))
        if r.get('primaryProposedTarget')!=expected[k] or r.get('blindProposedTarget')!=expected[k]: fail('review proposal mismatch '+str(k))
        if r.get('primaryProposedTargetSha256')!=digest(expected[k].encode()) or r.get('blindProposedTargetSha256')!=digest(expected[k].encode()): fail('review proposal hash mismatch '+str(k))
    elif r['crossDisposition']=='hold':
        if k[0] not in (493,502): fail('unexpected hold '+str(k))
        if any(field in r for field in ('currentTarget','selectedTarget','primaryProposedTarget','blindProposedTarget')): fail('hold contains target text '+str(k))
        if r.get('selectedTargetSha256') is not None: fail('hold contains selected target hash '+str(k))
        if p.get('proposedTarget') is not None or b.get('proposedTarget') is not None: fail('hold review contains proposal '+str(k))
        if r['sourceIdExactMatchCount'] or r['sourceTextExactMatchCount'] or r['callerContextRefs']: fail('hold is not callerless '+str(k))
    elif r['crossDisposition']=='accept-current':
        if k in expected or r.get('selectedTarget')!=c['currentTarget']: fail('accept-current target mismatch '+str(k))
        if r.get('currentTarget')!=c['currentTarget'] or digest(r['currentTarget'].encode())!=r['currentTargetSha256']: fail('accept-current value/hash mismatch '+str(k))
        if r['primaryDisposition']!='accept-current' or r['blindDisposition']!='accept-current': fail('non-consensus accept-current '+str(k))
        if r.get('selectedTargetSha256')!=digest(c['currentTarget'].encode()): fail('accept-current hash mismatch '+str(k))
    else: fail('unexpected disposition '+str(k))
    if r['crossDisposition'] in ('correction','refinement') and k not in expected: fail('unexpected update '+str(k))
    counts[r['crossDisposition']]+=1
if counts!=collections.Counter({'accept-current':201,'correction':14,'refinement':1,'hold':24}): fail('disposition counts mismatch: '+str(counts))
summary=readjson(OUT/'summary.json')
if summary['head']!=pins['head'] or summary['tree']!=pins['tree'] or summary['inputPinsSha256']!=digest((OUT/'input-pins.json').read_bytes()): fail('summary pin mismatch')
if summary['crossLedgerSha256']!=digest((OUT/'cross-ledger.jsonl').read_bytes()): fail('summary ledger digest mismatch')
if summary['dispositions']!=dict(counts): fail('summary disposition count mismatch')
# Validate the output manifest (which intentionally does not hash itself).
for line in (OUT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    h,name=line.split('  ',1); p=OUT/name
    if not p.is_file() or digest(p.read_bytes())!=h: fail('output checksum mismatch: '+name)
print(json.dumps({'result':'PASS','head':pins['head'],'tree':pins['tree'],'cells':240,'dispositions':dict(counts),'adjudicatedProposalCells':len(expected),'primaryBlindConflicts':0,'holdsTextFree':24},sort_keys=True))
