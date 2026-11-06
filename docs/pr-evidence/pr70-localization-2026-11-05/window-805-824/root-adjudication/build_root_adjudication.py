#!/usr/bin/env python3
"""Build ROMarrNG W805-W824 root decisions from the portable sealed packets."""
import collections, hashlib, json, shutil, subprocess
from pathlib import Path

TASK=Path(__file__).resolve().parent
WINDOW_ROOT=TASK.parent
CF=WINDOW_ROOT/'candidate-free'
PR=WINDOW_ROOT/'primary-review'
BL=WINDOW_ROOT/'blind-review'
CROSS=WINDOW_ROOT/'cross-review'
HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'
TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
CAT='romarr/ui-labels.json'
ROOT_DECISIONS={
 ('ui.patches.1c22815500','ar'):('refinement','The Library navigation label introduces the page described by the next source. Its content includes translations, hacks, and improvements, so التعديلات preserves that broader modification category better than the narrower التصحيحات.'),
 ('ui.patches.1c22815500','zh-Hant'):('refinement','This is a noun label for software/game patches in the Library navigation. 補丁 is the conventional patch noun and matches the catalogue label 補丁目錄 in the same window.'),
 ('ui.patches-translations-hacks-and-impro.b782f10dd3','ar'):('refinement','The page title explicitly covers translations, hacks, and improvements. التعديلات names the broader category; the current التصحيحات suggests corrections alone.'),
 ('ui.patches-translations-hacks-and-impro.b782f10dd3','zh-Hant'):('refinement','The title names a software/game patch page. Use 補丁 consistently with the adjacent navigation and catalogue label, while retaining the listed project types.'),
 ('ui.path-missing.b602374a06','ar'):('correction','The caller selects this status when l.path_exists is false. الطريق means a road; المسار غير موجود correctly describes a missing filesystem path and aligns with the adjacent Path label.'),
 ('ui.path-missing.b602374a06','hi'):('correction','The caller selects this status when the configured filesystem path does not exist. पथ मौजूद नहीं है states that condition directly; पथ लापता is not idiomatic for a path.'),
 ('ui.path-missing.b602374a06','id'):('refinement','The caller reports a filesystem path that does not exist. Jalur uses the localized term in the adjacent Path label, and tidak ditemukan removes the current English-Indonesian mix.'),
 ('ui.pause.858e4ba7a2','hi'):('refinement','The caller toggles this action to Resume when the queue item is paused, with Cancel as a separate action. ठहराएँ expresses temporary pausing more clearly than रोकें, which can read as stopping.'),
 ('ui.peering-shares-nothing-by-itself.8dfca30a01','pt-BR'):('correction','The caller renders the source as bold explanatory help text. The current adds quotation marks absent from the source; por si só is the natural Brazilian Portuguese equivalent of by itself.'),
 ('ui.pick-a-type.be4b3c9327','ar'):('correction','This is the instruction above the available type choices. Correct the imperative spelling to اختر and use the indefinite accusative نوعًا.'),
 ('ui.pick-a-facet-above.95ff025720','de'):('refinement','The placeholder is filled with a translated facet label. Wählen Sie matches the formal Sie register used by the neighboring type and route instructions; Wähle switches to informal du.'),
 ('ui.pick-a-facet-above.95ff025720','es'):('correction','The caller substitutes Género, franquicia, or Empresa. The fixed masculine article un fits only Género; omitting the article keeps the instruction grammatical for every dynamic label.'),
 ('ui.pick-a-facet-above.95ff025720','ko'):('correction','The caller substitutes a dynamic facet label. The current fixed particle 을 does not fit the provided vowel-final labels (장르, 프랜차이즈, 회사), which take 를; omitting the particle avoids a mismatch for fallback labels too.'),
}

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rows(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def write_json(p,v): p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,rs): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in rs),encoding='utf-8')
def write_sums(root):
    files=sorted(p for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS.txt')
    (root/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}\n' for p in files),encoding='utf-8')
def verify_sums(root):
    p=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=root,text=True,capture_output=True)
    if p.returncode: raise SystemExit(f'FAIL checksums {root}: {p.stderr}')
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def git_json(repo,rev,path): return json.loads(subprocess.check_output(['git','-C',str(repo),'show',f'{rev}:{path}']))

def main():
    repo=Path(__file__).resolve().parents[5]
    if git(repo,'rev-parse',HEAD+'^{tree}')!=TREE: raise SystemExit('FAIL input tree pin')
    for d in (CF,CF/'input',CF/'predecessor',PR,BL,CROSS): verify_sums(d)
    input_checks= json.loads((CROSS/'input-packet-checksums.json').read_text(encoding='utf-8'))
    copies={'candidate-free':CF,'primary':PR,'independent-blind':BL}
    for item in input_checks['inputs']:
        dst=copies[item['name']]
        if len(item['files'])!=item['fileCount']: raise SystemExit('FAIL input file-count attestation '+item['name'])
        for f in item['files']:
            q=dst/f['path']
            if not q.is_file() or q.stat().st_size!=f['byteCount'] or sha(q.read_bytes())!=f['sha256']:
                raise SystemExit(f'FAIL portable input copy {item["name"]}/{f["path"]}')
    cf=rows(CF/'input/candidate-free-cells.jsonl')
    ctx_rows=rows(CF/'input/source-contexts.jsonl'); contexts={r['sourceId']:r for r in ctx_rows}
    cross=rows(CROSS/'integrated-cross-review-ledger.jsonl')
    unresolved=rows(CROSS/'unresolved-language-holds.jsonl')
    if (len(cf),len(cross),len(unresolved))!=(240,240,10): raise SystemExit('FAIL input row counts')
    cfmap={(r['sourceId'],r['locale']):r for r in cf}
    if len(cfmap)!=240: raise SystemExit('FAIL candidate-free duplicate cells')
    unresolved_map={(r['sourceId'],r['locale']):r for r in unresolved}
    if len(unresolved_map)!=10: raise SystemExit('FAIL unresolved language hold uniqueness')
    if set(ROOT_DECISIONS)!={(r['sourceId'],r['locale']) for r in cross if r['integratedDecision']=='adopt_proposal'}:
        raise SystemExit('FAIL root decision coverage differs from integrated target set')
    catalog=git_json(repo,HEAD,CAT); messages=catalog['messages']; order=list(messages)
    if len(messages)!=1836: raise SystemExit('FAIL exact input catalog count')
    # Reattest all active holds against the exact pre-application catalog and preserve source bytes.
    source_hold1=CROSS/'prior-active-holds-hash-only.jsonl'; source_hold2=CROSS/'current-window-holds-hash-only.jsonl'
    shutil.copyfile(source_hold1,TASK/'prior-active-holds-hash-only.jsonl')
    shutil.copyfile(source_hold2,TASK/'w785-current-window-holds-hash-only.jsonl')
    hold1=rows(TASK/'prior-active-holds-hash-only.jsonl'); hold2=rows(TASK/'w785-current-window-holds-hash-only.jsonl')
    holds=hold1+hold2
    if (len(hold1),len(hold2),len(holds))!=(1012,48,1060): raise SystemExit('FAIL inherited hash-only hold counts')
    if len({(r['sourceId'],r['locale']) for r in holds})!=1060: raise SystemExit('FAIL inherited hold uniqueness')
    forbidden={'source','sourceText','currentTarget','target','targetText','proposedTarget','translation','reviewDecision','decision'}
    if any(r.get('textOmitted') is not True or forbidden.intersection(r) for r in holds): raise SystemExit('FAIL inherited hold text/decision leak')
    for h in holds:
        m=messages.get(h['sourceId']); loc=h['locale']
        if not m or loc not in m['translations'] or sha(m['source'])!=h['sourceSha256'] or sha(m['translations'][loc])!=h['currentTargetSha256']:
            raise SystemExit(f'FAIL active hold exact-head hash {h["sourceId"]}/{loc}')
        idx=order.index(h['sourceId'])
        if h.get('catalogZeroBasedIndex') is not None and h['catalogZeroBasedIndex']!=idx: raise SystemExit('FAIL active hold position')
    root_rows=[]; selected=[]; counts=collections.Counter(); holdkeys=set(unresolved_map)
    activekeys={(r['sourceId'],r['locale']) for r in holds}
    if set(ROOT_DECISIONS)&activekeys: raise SystemExit('FAIL selected target overlaps active hash-only hold')
    for x in cross:
        key=(x['sourceId'],x['locale']); c=cfmap[key]; ctx=contexts[x['sourceId']]
        if (x['sourceSha256'],x['currentTargetSha256'],x['callerContextSha256'])!=(c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256']): raise SystemExit('FAIL candidate/cross source-current-context mismatch '+str(key))
        if (x['source'],x['currentTarget'])!=(c['source'],c['currentTarget']): raise SystemExit('FAIL candidate/cross source text mismatch '+str(key))
        if x['callerless'] or c['callerless'] or ctx['callerless']: raise SystemExit('FAIL unexpected callerless cell '+str(key))
        expected_refs=[{'path':q['path'],'line':q['line'],'matchKind':q['matchKind'],'lineSha256':q['lineSha256'],'excerptSha256':q['excerptSha256'],'fileSha256':q['fileSha256'],'gitBlob':q['gitBlob']} for q in ctx['callers']]
        if x['callerReferenceCount']!=ctx['exactMatchCount'] or x['callerReferences']!=expected_refs: raise SystemExit('FAIL exact caller references '+str(key))
        if key in ROOT_DECISIONS:
            disposition,why=ROOT_DECISIONS[key]
            target=x['integratedTarget']
            if x['integratedDecision']!='adopt_proposal' or target==c['currentTarget'] or sha(target)!=x['integratedTargetSha256']:
                raise SystemExit('FAIL unsupported integrated target '+str(key))
            ta=x['tokenAudit']
            if not all(ta.get(k) for k in ('placeholdersMatch','markupMatches','numbersMatch','protectedLiteralsMatch')): raise SystemExit('FAIL selected target token audit '+str(key))
            root_target=target; root_sha=sha(target)
            rec_disposition=disposition; confidence='moderate'
        elif key in holdkeys:
            h=unresolved_map[key]
            if x['integratedDecision']!='retain_current' or x['integratedTarget']!=c['currentTarget'] or x['integratedTargetSha256']!=c['currentTargetSha256']:
                raise SystemExit('FAIL low-confidence hold changed current '+str(key))
            if h['currentTargetSha256']!=c['currentTargetSha256'] or h['integratedTargetSha256']!=c['currentTargetSha256']:
                raise SystemExit('FAIL held current target hash '+str(key))
            root_target=c['currentTarget']; root_sha=c['currentTargetSha256']; rec_disposition='hold-low-confidence-current'; confidence='low'; why=h['reason']
        else:
            if x['integratedDecision']!='retain_current' or x['integratedTarget']!=c['currentTarget'] or x['integratedTargetSha256']!=c['currentTargetSha256']:
                raise SystemExit('FAIL non-selected current target '+str(key))
            root_target=c['currentTarget']; root_sha=c['currentTargetSha256']; rec_disposition='accept-current'; confidence=x.get('confidence','moderate'); why='Retain the exact-head current translation; the source meaning and pinned caller context establish no material issue.'
        if key in ROOT_DECISIONS and ROOT_DECISIONS[key][0]!=rec_disposition: raise SystemExit('FAIL root disposition mismatch '+str(key))
        rec={'schemaVersion':1,'reviewStage':'root-adjudication','exactHead':HEAD,'exactTree':TREE,'position':x['position'],'catalogZeroBasedIndex':x['catalogZeroBasedIndex'],'catalogOneBasedPosition':x['catalogOneBasedPosition'],'sourceId':x['sourceId'],'locale':x['locale'],'callerless':False,'source':c['source'],'sourceSha256':c['sourceSha256'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerReferenceCount':ctx['exactMatchCount'],'callerReferences':expected_refs,'candidateFreeCellRecordSha256':sha(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':'))),'primaryDisposition':x['primaryDisposition'],'blindDecision':x['blindDecision'],'integratedDecision':x['integratedDecision'],'integratedTargetSource':x['integratedTargetSource'],'integratedTargetSha256':x['integratedTargetSha256'],'rootDisposition':rec_disposition,'rootTarget':root_target,'rootTargetSha256':root_sha,'confidence':confidence,'rationale':why,'tokenAudit':x['tokenAudit'],'nativeSpeakerApproval':False}
        if key in holdkeys:
            h=unresolved_map[key]
            rec['lowConfidenceHold']=True; rec['heldProposalSha256']=h['heldProposalSha256']; rec['heldProposalEvidenceSha256']=sha(json.dumps(h,ensure_ascii=False,sort_keys=True,separators=(',',':')))
        else: rec['lowConfidenceHold']=False
        root_rows.append(rec); counts[rec_disposition]+=1
        if key in ROOT_DECISIONS:
            selected.append({'position':x['position'],'catalogZeroBasedIndex':x['catalogZeroBasedIndex'],'catalogOneBasedPosition':x['catalogOneBasedPosition'],'sourceId':x['sourceId'],'locale':x['locale'],'callerless':False,'source':c['source'],'sourceSha256':c['sourceSha256'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'rootTarget':root_target,'rootTargetSha256':root_sha,'rootDisposition':rec_disposition,'callerContextSha256':c['callerContextSha256'],'callerReferenceCount':ctx['exactMatchCount'],'callerReferences':expected_refs,'integratedTargetSource':x['integratedTargetSource'],'integratedTargetSha256':x['integratedTargetSha256'],'confidence':confidence,'rationale':why,'nativeSpeakerApproval':False})
    if counts!=collections.Counter({'accept-current':217,'hold-low-confidence-current':10,'correction':6,'refinement':7}): raise SystemExit('FAIL root disposition totals '+repr(counts))
    if len(selected)!=13: raise SystemExit('FAIL selected target total')
    write_jsonl(TASK/'root-disposition-ledger.jsonl',root_rows)
    write_jsonl(TASK/'selected-targets.jsonl',selected)
    shutil.copyfile(CROSS/'unresolved-language-holds.jsonl',TASK/'low-confidence-language-holds.jsonl')
    hold_lineage={'artifact':'ROMarrNG W805-W824 inherited active hash-only hold lineage','predecessorWindow':'W785-W804','priorActiveHoldCount':1012,'w785CurrentWindowHoldCount':48,'totalActiveHashOnlyHoldCount':1060,'byteForByteCopied':True,'allRowsTextOmitted':True,'allTargetHashesMatchExactInputHead':True,'groups':[{'path':'prior-active-holds-hash-only.jsonl','source':'cross-review/prior-active-holds-hash-only.jsonl','rowCount':len(hold1),'sha256':sha((TASK/'prior-active-holds-hash-only.jsonl').read_bytes())},{'path':'w785-current-window-holds-hash-only.jsonl','source':'cross-review/current-window-holds-hash-only.jsonl','rowCount':len(hold2),'sha256':sha((TASK/'w785-current-window-holds-hash-only.jsonl').read_bytes())}]}
    write_json(TASK/'hold-lineage.json',hold_lineage)
    att={'artifact':'ROMarrNG PR #70 W805-W824 root-adjudication input attestation','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W805-W824','exactHead':HEAD,'exactTree':TREE,'inputCatalogPath':CAT,'inputCatalogSha256':sha(subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{CAT}'])),'candidateFreeOuterChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),'candidateFreeInputChecksumListSha256':sha((CF/'input/SHA256SUMS.txt').read_bytes()),'primaryChecksumListSha256':sha((PR/'SHA256SUMS.txt').read_bytes()),'blindChecksumListSha256':sha((BL/'SHA256SUMS.txt').read_bytes()),'integratedCrossChecksumListSha256':sha((CROSS/'SHA256SUMS.txt').read_bytes()),'integratedCrossInputPacketChecksumsSha256':sha((CROSS/'input-packet-checksums.json').read_bytes()),'candidateFreeCellCount':len(cf),'integratedCrossCellCount':len(cross),'selectedTargetCount':len(selected),'lowConfidenceLanguageHoldCount':len(unresolved),'activeHashOnlyHolds':len(holds),'nativeSpeakerApproval':False,'productApplicationPerformed':False}
    write_json(TASK/'input-attestation.json',att)
    summary={'artifact':'ROMarrNG PR #70 W805-W824 root adjudication','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W805-W824','exactHead':HEAD,'exactTree':TREE,'cellCount':240,'rootDispositionCounts':dict(sorted(counts.items())),'selectedTargetCount':len(selected),'selectedCorrectionCount':counts['correction'],'selectedRefinementCount':counts['refinement'],'lowConfidenceLanguageHolds':len(unresolved),'activePriorHashOnlyHoldsPreserved':len(holds),'resultingActiveHashOnlyHolds':len(holds),'newCallerlessHolds':0,'nextBoundary':json.loads((CF/'input/manifest.json').read_text())['nextBoundary'],'confidence':'moderate','nativeSpeakerApproval':False,'productApplicationPerformed':False,'rootAdjudicationPerformed':True}
    write_json(TASK/'summary.json',summary)
    readme=f'''# ROMarrNG W805–W824 root adjudication

Root decisions are pinned to input head `{HEAD}` / tree `{TREE}`. The portable candidate-free, primary, independent blind, and integrated cross-review packets are adjacent under this evidence directory and retain their original checksums.

All 13 integrated target suggestions were adjudicated against the exact source text, production caller references, and token audit. Six are corrections and seven are refinements. The other 217 cells retain current targets. The 10 low-confidence language alternatives remain on their current targets and are copied, with hashes, to `low-confidence-language-holds.jsonl` pending qualified native review.

The 1,012 older active hash-only holds and 48 W785 current-window hash-only holds are copied byte-for-byte in separate files. Their 1,060 exact-head target hashes were reattested; no selected target overlaps an active hash-only hold. No new callerless holds are added. These root recommendations authorize application only of the 13 listed targets.

Confidence is moderate overall; this is machine review, not native-speaker approval. Product application and its readback are recorded in the sibling `application/` packet after the product commit.

Verify with `python3 -B verify_root_adjudication.py --repo /home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685`.
'''
    (TASK/'README.md').write_text(readme,encoding='utf-8')
    write_sums(TASK)
    print(json.dumps({'result':'BUILT','cells':240,'rootDispositions':dict(sorted(counts.items())),'selectedTargets':len(selected),'lowConfidenceLanguageHolds':len(unresolved),'activeHashOnlyHolds':len(holds),'nextBoundary':summary['nextBoundary']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
