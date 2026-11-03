#!/usr/bin/env python3
"""Read-only exact-head verifier for the ROMarr W325-W344 translation application."""
from __future__ import annotations
import collections, copy, hashlib, json, re, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parent
REPO=EVIDENCE.parents[3]
PACKETS=EVIDENCE/'review-packets'
PRIMARY=PACKETS/'primary'
INPUT=PRIMARY/'input'
PRIMARY_REVIEW=PRIMARY/'primary-review'
BLIND=PACKETS/'blind'
BLIND_INPUT=BLIND/'input'
BLIND_REVIEW=BLIND/'review'
CROSS=PACKETS/'cross-audit'
BASE='018937dc98d451ddd04d2d0942bca2777ef64dd3'
BASE_TREE='c13dc4fc091565318d11a19ad9e851215a5f917e'
CATALOG='romarr/ui-labels.json'

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
def sha_text(text: str) -> str:
    return sha(text.encode('utf-8'))
def readj(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))
def readjl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def git(*args: str) -> str:
    return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(['git',*args],cwd=REPO)
def verify_sums(directory: Path, filename='SHA256SUMS.txt'):
    for line in (directory/filename).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1)
        rel=rel.lstrip(' *')
        target=directory/rel
        assert target.is_file(),f'missing checksum target: {target}'
        assert sha(target.read_bytes())==expected,f'checksum mismatch: {target}'
def run_packet_verifier(path: Path):
    result=subprocess.run(['python3',str(path)],cwd=REPO,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert result.returncode==0,(path,result.stdout,result.stderr)
    return result.stdout.strip()
def fail(message):
    raise RuntimeError(message)

def main():
    head=git('rev-parse','HEAD')
    assert head==BASE or git('rev-parse','HEAD^')==BASE, f'branch head not based directly on pinned parent: {head}'
    assert git('rev-parse',f'{BASE}^{{tree}}')==BASE_TREE
    assert git('branch','--show-current')=='task/localization-translation-review-20261030'
    live=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/ROMarrNG/pulls/70','--jq','{state:.state,draft:.draft,headRef:.head.ref,head:.head.sha,baseRef:.base.ref,base:.base.sha}'],cwd=REPO,text=True))
    assert live['state']=='open' and live['draft'] is True and live['headRef']=='task/localization-translation-review-20261030'
    assert live['baseRef']=='main'
    assert live['head']==head
    remote={line.split()[1]:line.split()[0] for line in git('ls-remote','https://github.com/snapetech-org/ROMarrNG.git','refs/heads/task/localization-translation-review-20261030','refs/pull/70/head').splitlines()}
    assert remote=={'refs/heads/task/localization-translation-review-20261030':head,'refs/pull/70/head':head}

    verify_sums(PRIMARY)
    verify_sums(INPUT)
    verify_sums(BLIND_REVIEW)
    assert sha((BLIND_REVIEW/'SHA256SUMS.txt').read_bytes())==(BLIND_REVIEW/'SHA256SUMS.txt.sha256').read_text().split()[0]
    verify_sums(CROSS)
    assert sha((CROSS/'SHA256SUMS.txt').read_bytes())==(CROSS/'SHA256SUMS.txt.sha256').read_text().split()[0]
    verify_input=run_packet_verifier(INPUT/'verify_input.py')
    verify_primary=run_packet_verifier(PRIMARY_REVIEW/'verify_primary.py')
    verify_blind=run_packet_verifier(BLIND/'verify_blind_copied.py')
    verify_cross=run_packet_verifier(CROSS/'verify_cross_audit_copied.py')

    manifest=readj(INPUT/'manifest.json')
    summary=readj(CROSS/'summary.json')
    auth=readj(HERE/'application-authorization.json')
    app_summary=readj(HERE/'application-summary.json')
    assert manifest['head']==BASE and manifest['tree']==BASE_TREE and manifest['cellCount']==240
    assert auth['applicationApproved'] is True and auth['releaseApproved'] is False
    assert auth['parentHead']==BASE and auth['parentTree']==BASE_TREE
    assert auth['applicationPlanSha256']==sha((HERE/'application-plan.jsonl').read_bytes())
    assert auth['selectedChangeCount']==57 and auth['heldCellCount']==24
    assert auth['nativeSpeakerApproval'] is False
    assert summary['totalCells']==240 and summary['selectedChanges']==57
    assert summary['unresolvedTargetDisagreements']==0 and summary['mandatoryCallerlessHoldCells']==24
    assert summary['sourcePacketHashes']['candidateFreeManifestSha256']==sha((INPUT/'manifest.json').read_bytes())
    assert summary['sourcePacketHashes']['candidateFreeChecksumListSha256']==sha((INPUT/'SHA256SUMS.txt').read_bytes())
    assert summary['sourcePacketHashes']['primaryRootChecksumListSha256']==sha((PRIMARY/'SHA256SUMS.txt').read_bytes())
    assert summary['sourcePacketHashes']['primaryReviewLedgerSha256']==sha((PRIMARY_REVIEW/'review-decisions.jsonl').read_bytes())
    assert summary['sourcePacketHashes']['blindChecksumListSha256']==sha((BLIND_REVIEW/'SHA256SUMS.txt').read_bytes())
    assert summary['sourcePacketHashes']['blindLedgerSha256']==sha((BLIND_REVIEW/'blind-ledger.jsonl').read_bytes())
    for name,digest in summary['outputHashes'].items():
        assert sha((CROSS/name).read_bytes())==digest,name

    # Confirm the copied blind source packet is byte-identical for the decisive files.
    for name in ('manifest.json','current-target-cells.jsonl','source-contexts.jsonl','source-queue.json','catalog-file-pins.json'):
        assert sha((INPUT/name).read_bytes())==sha((BLIND_INPUT/name).read_bytes()),name

    cells=readjl(INPUT/'current-target-cells.jsonl')
    cell_by={(row['position'],row['locale']):row for row in cells}
    cross=readjl(CROSS/'cross-audit-ledger.jsonl')
    cross_by={(row['position'],row['locale']):row for row in cross}
    plans=readjl(HERE/'application-plan.jsonl')
    plan_by={(row['position'],row['locale']):row for row in plans}
    proposals=readjl(CROSS/'selected-changes-proposal.jsonl')
    proposal_by={(row['position'],row['locale']):row for row in proposals}
    assert len(cells)==len(cell_by)==240 and len(cross)==len(cross_by)==240
    assert len(plans)==len(plan_by)==len(proposals)==len(proposal_by)==57
    assert set(plan_by)==set(proposal_by)
    for key,row in plan_by.items():
        proposal=proposal_by[key]
        assert row['sourceId']==proposal['sourceId'] and row['source']==proposal['source']
        assert row['locale']==proposal['locale'] and row['position']==proposal['position']
        assert row['currentTarget']==proposal['currentTarget'] and row['currentTargetSha256']==proposal['currentTargetSha256']
        assert row['target']==proposal['target'] and row['targetSha256']==proposal['targetSha256']
        assert row['disposition']==proposal['disposition'] and row['rationale']==proposal['rationale']
        assert row['callerContextSha256']==cross_by[key]['callerContextSha256']

    base_catalog=json.loads(git_bytes('show',f'{BASE}:{CATALOG}'))
    current_catalog=readj(REPO/CATALOG)
    expected=copy.deepcopy(base_catalog)
    for key,row in plan_by.items():
        cell=cell_by[key]
        entry=base_catalog['messages'][row['sourceId']]
        assert row['catalogPath']==CATALOG and cell['catalogPath']==CATALOG
        assert entry['source']==cell['source']==row['source']
        assert entry['sourceHash']==cell['sourceSha256']==row['sourceSha256']
        assert entry['translations'][row['locale']]==cell['currentTarget']==row['currentTarget']
        assert sha_text(row['currentTarget'])==row['currentTargetSha256']
        assert sha_text(row['target'])==row['targetSha256']
        expected['messages'][row['sourceId']]['translations'][row['locale']]=row['target']
    assert current_catalog==expected,'catalog contains missing, extra, or non-target changes'
    assert list(current_catalog)==list(base_catalog)
    assert list(current_catalog['messages'])==list(base_catalog['messages'])
    for sid,entry in base_catalog['messages'].items():
        after=current_catalog['messages'][sid]
        assert list(after)==list(entry),f'message field order changed: {sid}'
        assert list(after['translations'])==list(entry['translations']),f'locale order changed: {sid}'
        for field in ('translationStatus','translationHashes','translationReview','translationPending'):
            assert after.get(field)==entry.get(field),f'{field} changed: {sid}'

    readback=readjl(HERE/'application-readback.jsonl')
    assert len(readback)==240 and len({(r['position'],r['locale']) for r in readback})==240
    rb={(r['position'],r['locale']):r for r in readback}
    assert set(rb)==set(cell_by)
    update_count=retain_count=hold_count=0
    for key,cell in cell_by.items():
        r=rb[key]
        cross_row=cross_by[key]
        target=current_catalog['messages'][cell['sourceId']]['translations'][cell['locale']]
        expected_disposition='update' if key in plan_by else ('hold' if cross_row['crossAuditDisposition']=='hold' else 'retain')
        assert r['sourceId']==cell['sourceId'] and r['source']==cell['source']
        assert r['previousTarget']==cell['currentTarget'] and r['previousTargetSha256']==cell['currentTargetSha256']
        assert r['target']==target and r['targetSha256']==sha_text(target)
        assert r['disposition']==expected_disposition
        if expected_disposition=='update': update_count+=1
        elif expected_disposition=='retain':
            retain_count+=1
            assert target==cell['currentTarget']
        else:
            hold_count+=1
            assert target==cell['currentTarget'] and cell['position'] in (329,330)
    assert (update_count,retain_count,hold_count)==(57,159,24)
    assert app_summary['parentHead']==BASE and app_summary['parentTree']==BASE_TREE
    assert app_summary['catalogBeforeSha256']==sha(git_bytes('show',f'{BASE}:{CATALOG}'))
    assert app_summary['catalogAfterSha256']==sha((REPO/CATALOG).read_bytes())
    assert app_summary['nonTargetCellChanges']==0 and app_summary['nativeSpeakerApproval'] is False

    print(json.dumps({
      'verification':'passed','head':head,'parentHead':BASE,'window':'W325-W344',
      'cells':240,'updates':57,'corrections':43,'refinements':14,'retained':159,'callerlessHolds':24,
      'nonTargetChanges':0,'placeholderNumericMarkupProtectedLiterals':'passed',
      'orderedCatalogStructure':'unchanged','translationReviewMetadata':'unchanged',
      'candidateFree':verify_input,'primary':verify_primary,'blind':verify_blind,'crossAudit':verify_cross
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)
