from pathlib import Path
import hashlib, json

ROOT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w645-664-20261105')
OUT=ROOT/'root-adjudication'
CF=ROOT/'candidate-free/candidate-free/input'
PRIMARY=ROOT/'primary/primary-output'
BLIND=ROOT/'blind-review'
CROSS=ROOT/'cross-review'

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def sha_bytes(value): return hashlib.sha256(value).hexdigest()
def sha_text(value): return sha_bytes(value.encode('utf-8'))
def write_json(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(path,values): Path(path).write_text(''.join(json.dumps(v,ensure_ascii=False,sort_keys=True)+'\n' for v in values),encoding='utf-8')

manifest=load(CF/'manifest.json')
bundle=load(ROOT/'candidate-free/bundle-manifest.json')
primary_summary=load(PRIMARY/'summary.json')
blind_summary=load(BLIND/'SUMMARY.json')
cross_summary=load(CROSS/'cross-review-summary.json')
cells=rows(CF/'current-target-cells.jsonl')
primary=rows(PRIMARY/'dispositions.jsonl')
blind=rows(BLIND/'blind-ledger.jsonl')
blind_proposals=rows(BLIND/'proposals.jsonl')
cross=rows(CROSS/'cross-review-ledger.jsonl')
reconciliations=rows(CROSS/'proposal-reconciliation.jsonl')
key=lambda item:(item['position'],item['locale'])
cell_map={key(item):item for item in cells}
blind_map={key(item):item for item in blind}
cross_map={key(item):item for item in cross}
assert bundle['head']=='9f8832f67195323955172dd4c3c40e29cbabb5da'
assert bundle['tree']=='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
assert len(cell_map)==len(blind_map)==len(cross_map)==240
assert set(cell_map)==set(blind_map)==set(cross_map)

choices={
 (646,'id'):('correction','Tidak ditemukan','The label appears in the Wanted/Missing view and on the missing-title count. “Tidak ditemukan” means not found; the current “Tidak ada” can imply that none exist.'),
 (646,'ja'):('correction','未所持','The caller shows games absent from the local collection. “未所持” describes titles not owned; “不足” means a shortage.'),
 (648,'hi'):('correction','Moonlight होस्ट','The caller labels a configured network/service machine. The technical loanword “होस्ट” is more precise here than “मेजबान,” which can describe a person hosting an event.'),
 (654,'ar'):('correction','تُجمَّع المجموعة متعددة الأقراص لأغراض البيانات الوصفية، وتبقى ملفات الأقراص الخاصة بها معًا','The authored organizer reason describes a grouped multi-disc set and files kept together. “البيانات الوصفية” is the standard metadata term; this avoids the current unnatural wording and the blind alternative “الإصدار,” which changes set to release.'),
 (654,'de'):('correction','Ein Multi-Disc-Set wird für Metadaten gruppiert; seine Disc-Dateien bleiben zusammen','The full sentence needs an article before the singular subject. “Disc-Dateien” keeps the game-media meaning clear.'),
 (654,'es'):('correction','El conjunto de varios discos se agrupa para los metadatos; sus archivos de disco permanecen juntos','This avoids the English hybrid “multidisco” and preserves both the grouped-set purpose and the files-stay-together clause.'),
 (654,'hi'):('correction','मल्टी-डिस्क सेट को मेटाडेटा के लिए एक समूह में रखा जाता है; इसकी डिस्क फ़ाइलें साथ रहती हैं','The source has two clauses: grouping the set for metadata and keeping its disc files together. The selected demonstrative “इसकी” refers directly to the set.'),
 (654,'id'):('correction','Set multi-disk dikelompokkan untuk keperluan metadata; berkas tiap disk tetap bersama','“Dikelompokkan” expresses grouped; “dikumpulkan” would mean collected. The wording retains the metadata purpose and that each disc’s files stay together.'),
 (654,'ja'):('correction','複数枚組はメタデータ用にまとめて扱われ、各ディスクのファイルは一緒に保たれます。','“複数枚組” clearly describes one set containing multiple discs. The current wording can read as multiple separate disc sets.'),
 (654,'ko'):('refinement','다중 디스크 세트는 메타데이터를 위해 그룹화되며 디스크 파일은 함께 유지됩니다','The existing meaning is clear; standard Korean writes “메타데이터” as one compound.'),
 (654,'pt-BR'):('refinement','O conjunto de vários discos é agrupado para fins de metadados; os arquivos de disco permanecem juntos','“Para fins de metadados” states the reason for grouping more naturally while preserving the source meaning.'),
 (654,'vi'):('correction','Bộ nhiều đĩa được nhóm để xử lý siêu dữ liệu; các tệp của từng đĩa vẫn được giữ cùng nhau.','“Bộ nhiều đĩa” identifies a set of multiple discs; the current “Bộ đĩa nhiều phần” can mean a multi-part set.'),
 (654,'zh-Hant'):('refinement','多碟套裝會以一組方式處理中繼資料；各光碟的檔案仍會放在一起。','The current “合併處理” can suggest merging metadata. This wording says the set is handled as one group while its disc files stay together.'),
 (656,'ar'):('correction','مكتبتي','The exact caller is a game-library mode button. “مكتبتي” means my library; “مكتبي” means my desk/office.'),
 (656,'pt-BR'):('correction','Minha biblioteca','This is a compact mode button label, so the existing terminal period is unnecessary.'),
}
assert len(choices)==15
primary_map={key(item):item for item in primary if item.get('disposition')=='CHANGE'}
blind_prop_map={key(item):item for item in blind_proposals}
assert len(primary_map)==12 and len(blind_prop_map)==6

binding_failures=[]
for k,review in blind_map.items():
    current=cell_map[k]
    for field in ('sourceId','sourceSha256','currentTargetSha256','callerContextSha256'):
        if review.get(field)!=current.get(field):
            binding_failures.append({'cell':k,'field':field})
    if review.get('selectedTarget') is not None and sha_text(review['selectedTarget'])!=review.get('selectedTargetSha256'):
        binding_failures.append({'cell':k,'field':'selectedTargetSha256'})
assert not binding_failures,binding_failures

ledger=[]
for k,cell in sorted(cell_map.items()):
    cross_row=cross_map[k]
    caller_count=len(cell.get('callerRefs') or [])
    assert cross_row.get('sourceSha256')==cell['sourceSha256']
    assert cross_row.get('currentTargetSha256')==cell['currentTargetSha256']
    assert cross_row.get('callerContextSha256')==cell.get('callerContextSha256')
    record={'window':'W645-W664','position':cell['position'],'locale':cell['locale'],
      'sourceId':cell['sourceId'],'sourceSha256':cell['sourceSha256'],
      'candidateFreeCellSha256':cross_row['candidateFreeCellSha256'],
      'callerContextSha256':cell.get('callerContextSha256'),'callerCount':caller_count,
      'currentTargetSha256':cell['currentTargetSha256'],'crossDisposition':cross_row['crossDisposition'],
      'primaryProposal':None,'blindProposal':None,'rootDisposition':None,'rootTarget':None,
      'rootTargetSha256':None,'rootRationale':None,'nativeSpeakerApproval':False,'browserReviewPerformed':False}
    p=primary_map.get(k)
    if p:
      record['primaryProposal']={'target':p['proposedTarget'],'targetSha256':p['proposedTargetSha256'],'rationale':p['rationale']}
      assert p['sourceSha256']==cell['sourceSha256'] and p['currentTargetSha256']==cell['currentTargetSha256']
    b=blind_prop_map.get(k)
    if b:
      record['blindProposal']={'target':b['selectedTarget'],'targetSha256':b['selectedTargetSha256'],'rationale':b['reason']}
      assert b['sourceSha256']==cell['sourceSha256'] and b['currentTargetSha256']==cell['currentTargetSha256']
    if caller_count==0:
      assert k not in choices
      record['rootDisposition']='text-free-hold'
      record['rootRationale']='No production caller context was pinned for this target; preserve as a hash-only hold.'
    elif k in choices:
      disposition,target,rationale=choices[k]
      assert sha_text(target)==cross_row['crossRecommendedTargetSha256']
      assert target==cross_row['crossRecommendedTarget']
      record['rootDisposition']=disposition;record['rootTarget']=target
      record['rootTargetSha256']=sha_text(target);record['rootRationale']=rationale
    else:
      assert cross_row['crossDisposition']=='accept-current'
      record['rootDisposition']='accept-current';record['rootTarget']=cell['currentTarget']
      record['rootTargetSha256']=cell['currentTargetSha256']
      record['rootRationale']='The current locale value preserves the source meaning for the pinned caller; no clear language or context defect was identified.'
    ledger.append(record)
counts={}
for item in ledger: counts[item['rootDisposition']]=counts.get(item['rootDisposition'],0)+1
assert counts=={'accept-current':129,'correction':12,'refinement':3,'text-free-hold':96},counts

cf_sum=sha_bytes((CF/'SHA256SUMS.txt').read_bytes())
expected_blind_pin=blind_summary['candidateFreeChecksumListSha256']
assert expected_blind_pin!=cf_sum
warning={'blindSummaryCandidateFreeChecksumListSha256':expected_blind_pin,
 'currentCandidateFreeChecksumListSha256':cf_sum,'mismatch':True,
 'blindPacketOwnChecksums':'PASS','all240BlindRowsBindToCurrentCandidateFreeInputs':True,
 'allSixBlindProposalTargetsHashVerified':True,
 'blindVerifier':'FAIL at candidate-free checksum-list equality assertion',
 'crossReviewVerifier':'PASS_WITH_RECORDED_BLIND_INPUT_PIN_WARNING',
 'disposition':'Keep the sealed blind packet unchanged. Record the stale top-level checksum pointer; use verified row-level source, current-target and caller hashes as documented by the independent cross-review.'}
inputs={'repository':'snapetech-org/ROMarrNG','pullRequest':70,
 'branch':'task/localization-translation-review-20261030','head':bundle['head'],'tree':bundle['tree'],
 'window':'W645-W664','cellCount':240,'candidateFreeInputChecksumListSha256':cf_sum,
 'candidateFreeInputManifestSha256':sha_bytes((CF/'manifest.json').read_bytes()),
 'primaryOuterChecksumListSha256':sha_bytes((ROOT/'primary/SHA256SUMS.txt').read_bytes()),
 'primaryOutputChecksumListSha256':sha_bytes((PRIMARY/'SHA256SUMS.txt').read_bytes()),
 'blindChecksumListSha256':sha_bytes((BLIND/'SHA256SUMS.txt').read_bytes()),
 'crossReviewChecksumListSha256':sha_bytes((CROSS/'SHA256SUMS.txt').read_bytes()),
 'blindInputPinWarning':warning,'blindBindingFailures':binding_failures}
write_json(OUT/'input-attestation.json',inputs)
write_jsonl(OUT/'root-disposition-ledger.jsonl',ledger)
summary={'artifact':'ROMarrNG W645-W664 root/manual adjudication','repository':'snapetech-org/ROMarrNG',
 'pullRequest':70,'branch':inputs['branch'],'head':bundle['head'],'tree':bundle['tree'],
 'sourceCount':20,'localeCount':12,'cellCount':240,'callerBackedCells':144,'callerlessHashOnlyHolds':96,
 'rootDispositionCounts':counts,'primaryProposalCount':12,'blindProposalCount':6,
 'proposalRecordsReconciled':18,'independentCrossReviewAdditionalRecommendations':3,
 'rootChangeCellCount':15,'applicationPerformed':False,
 'nativeSpeakerApproval':False,'browserReviewPerformed':False,'blindInputPinWarning':warning,
 'result':'ROOT_ADJUDICATION_COMPLETE_APPLICATION_PENDING'}
write_json(OUT/'summary.json',summary)
readme='''# ROMarrNG W645–W664 root adjudication\n\nThis packet resolves all 240 cells at PR #70 head `9f8832f67195323955172dd4c3c40e29cbabb5da` (tree `d6066baa3d03d3b4c6034e5af061fc4bc278b0f9`). It reconciles all 12 primary and 6 blind proposals plus 3 additional cross-review findings, selects 15 target cells, retains 129 caller-backed current values, and preserves 96 callerless cells as hash-only holds.\n\nRoot dispositions: 12 corrections, 3 refinements, 129 accept-current, and 96 text-free holds. The 15 target hashes match the independent cross-review recommendations.\n\nThe blind packet’s own checksum list passes, and row-level source, current-target, and caller-context hashes bind for all 240 cells. Its verifier fails because `SUMMARY.json` pins an older candidate-free checksum-list hash (`1ca785d5…` versus current `15dd26e7…`). The independent cross-review verifier passes with this mismatch recorded. The sealed blind packet was not changed.\n\nThis is assistant/root semantic adjudication only. It does not establish qualified native-speaker approval or headed-browser review, and no catalog application has been performed.\n'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

checks=[]
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name!='SHA256SUMS.txt': checks.append(f'{sha_bytes(path.read_bytes())}  {path.name}')
(OUT/'SHA256SUMS.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
print(json.dumps({'output':str(OUT),'counts':counts,'checksum':sha_bytes((OUT/'SHA256SUMS.txt').read_bytes()),'blindInputWarning':warning},ensure_ascii=False,indent=2))
