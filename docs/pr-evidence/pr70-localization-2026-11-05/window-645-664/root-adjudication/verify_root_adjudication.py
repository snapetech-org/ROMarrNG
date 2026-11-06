from pathlib import Path
import hashlib, json

ROOT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w645-664-20261105')
OUT=ROOT/'root-adjudication'
CF=ROOT/'candidate-free/candidate-free/input'
CROSS=ROOT/'cross-review'
BLIND=ROOT/'blind-review'
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def sha_bytes(value): return hashlib.sha256(value).hexdigest()
def sha_text(value): return sha_bytes(value.encode('utf-8'))

summary=load(OUT/'summary.json')
ledger=rows(OUT/'root-disposition-ledger.jsonl')
cells=rows(CF/'current-target-cells.jsonl')
cross=rows(CROSS/'cross-review-ledger.jsonl')
blind=rows(BLIND/'blind-ledger.jsonl')
key=lambda x:(x['position'],x['locale'])
cell_map={key(x):x for x in cells};cross_map={key(x):x for x in cross};blind_map={key(x):x for x in blind}
assert summary['head']=='9f8832f67195323955172dd4c3c40e29cbabb5da'
assert summary['tree']=='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
assert len(ledger)==len(cell_map)==len(cross_map)==len(blind_map)==240
assert len({key(x) for x in ledger})==240
counts={}
for row in ledger:
    k=key(row);cell=cell_map[k];cross_row=cross_map[k];blind_row=blind_map[k]
    assert row['sourceId']==cell['sourceId'] and row['sourceSha256']==cell['sourceSha256']
    assert row['currentTargetSha256']==cell['currentTargetSha256']
    assert row['callerContextSha256']==cell.get('callerContextSha256')
    assert row['candidateFreeCellSha256']==cross_row['candidateFreeCellSha256']
    assert row['crossDisposition']==cross_row['crossDisposition']
    for field in ('sourceId','sourceSha256','currentTargetSha256','callerContextSha256'):
        assert blind_row.get(field)==cell.get(field)
    if row['rootDisposition']=='text-free-hold':
        assert not cell.get('callerRefs') and row['rootTarget'] is None and row['rootTargetSha256'] is None
        assert blind_row.get('selectedTarget') is None
    else:
        assert cell.get('callerRefs')
        assert row['rootTarget'] is not None
        assert sha_text(row['rootTarget'])==row['rootTargetSha256']
        if row['rootDisposition'] in ('correction','refinement'):
            assert row['rootTarget']==cross_row['crossRecommendedTarget']
            assert row['rootTargetSha256']==cross_row['crossRecommendedTargetSha256']
        else:
            assert row['rootTarget']==cell['currentTarget']
            assert row['rootTargetSha256']==cell['currentTargetSha256']
    counts[row['rootDisposition']]=counts.get(row['rootDisposition'],0)+1
assert counts==summary['rootDispositionCounts']=={'accept-current':129,'correction':12,'refinement':3,'text-free-hold':96}
blind_summary=load(BLIND/'SUMMARY.json')
actual_cf=sha_bytes((CF/'SHA256SUMS.txt').read_bytes())
assert blind_summary['candidateFreeChecksumListSha256']!=actual_cf
assert summary['blindInputPinWarning']['all240BlindRowsBindToCurrentCandidateFreeInputs']
# Check this packet's checksum list, including the verifier itself.
for line in (OUT/'SHA256SUMS.txt').read_text().splitlines():
    expected,name=line.split('  ',1)
    assert sha_bytes((OUT/name).read_bytes())==expected,(name,expected)
print(json.dumps({'result':'PASS_WITH_RECORDED_BLIND_INPUT_PIN_WARNING','head':summary['head'],'tree':summary['tree'],'cells':len(ledger),'counts':counts,'rootTargetHashesMatchCrossReview':True,'blindRowsBindToCurrentInput':True,'blindSummaryChecksumPinMismatch':'RECORDED'},ensure_ascii=False,indent=2))
