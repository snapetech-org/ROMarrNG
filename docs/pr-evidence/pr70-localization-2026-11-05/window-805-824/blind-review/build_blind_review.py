#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, shutil, unicodedata
from pathlib import Path

OUT=Path(__file__).resolve().parent
PACKET=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w805-824-candidate-free-20261105')
INPUT=PACKET/'input'
PREDECESSOR=PACKET/'predecessor'
HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'
TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
OUTER_SUMS_SHA='cf34d5b87ae6e06aa09152a09a87da51025c40e47ed2e18d2237c666e912b8ba'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
POSITIONS=list(range(805,825))

REVISIONS={
 (805,'ar'):('عنوان URL لكتالوج الباتشات (اختياري)','Uses the ROM-patch sense rather than generic modifications.'),
 (805,'fr'):('URL du catalogue de patches (facultatif)','Uses the established ROM-patch term rather than generic fixes.'),
 (806,'ar'):('باتشات','Uses the ROM-patch term for this navigation destination.'),
 (806,'fr'):('Patchs','Uses the French ROM-patch term rather than generic fixes.'),
 (807,'ar'):('باتشات — ترجمات وتعديلات وتحسينات','Names the ROM-patch page without implying only bug fixes.'),
 (807,'fr'):('Patchs — traductions, hacks et améliorations','Names ROM patches rather than generic corrective fixes.'),
 (807,'ko'):('패치 — 번역, 개조 및 개선','Uses 개조 for ROM modifications instead of 핵, which reads as “nucleus.”'),
 (809,'ar'):('المسار غير موجود','States that the filesystem path does not exist; avoids the literal “missing road.”'),
 (809,'hi'):('पथ मौजूद नहीं है','States that the filesystem path does not exist.'),
 (809,'id'):('Jalur tidak ditemukan','States that the filesystem path was not found.'),
 (812,'hi'):('ठहराएँ','Uses a pause action rather than a stop action for the queue control.'),
 (814,'pt-BR'):('Peering, por si só, não compartilha nada.','Uses the natural “by itself” construction for the explanatory caution.'),
 (816,'zh-Hans'):('按行指定','Makes the platform value’s per-line scope concise and clear.'),
 (816,'zh-Hant'):('逐行指定','Makes the platform value’s per-line scope concise and clear.'),
 (818,'ar'):('اختر نوعًا.','Corrects the case ending for the singular object “a type.”'),
 (818,'zh-Hans'):('请选择类型。','Uses a clear, polite UI instruction.'),
 (818,'zh-Hant'):('請選擇類型。','Uses a clear, polite UI instruction.'),
 (819,'es'):('Elige {facet} arriba.','Drops the fixed masculine article because {facet} can be feminine or masculine.'),
 (820,'de'):('Wählen Sie einen Weg. Sie können hierher zurückkehren und die anderen Bestandteile später hinzufügen.','Uses “way” for an onboarding path instead of a literal travel route.'),
 (821,'de'):('Eine Spielesammlung planen','Makes clear that the set is a group of games in the collections page.'),
 (821,'es'):('Planifica un conjunto de juegos','Makes clear that the set is a group of games in the collections page.'),
 (821,'fr'):('Planifier un ensemble de jeux','Makes clear that the set is a group of games in the collections page.'),
 (821,'pt-BR'):('Planeje um conjunto de jogos','Makes clear that the set is a group of games in the collections page.'),
}

NOTES={
805:'settings label for the optional URL of a catalogue of ROM translation, hack, and improvement projects',
806:'navigation label for the patches page',
807:'page title describing patches that provide translations, hacks, and improvements',
808:'filesystem path label used with DAT discovery and path mappings',
809:'connection-status label shown when the configured path does not exist',
810:'remote path value reported by a download client',
811:'local path value visible to ROMarr',
812:'queue action that pauses the current operation',
813:'paused download or operation state',
814:'Friends-page caution that peering alone does not share anything; users choose what each friend sees',
815:'download state awaiting further action',
816:'platform value supplied per line in an import list',
817:'proper title of the game Phantasy Star IV',
818:'type-selection instruction in the add-item modal',
819:'instruction to choose a dynamic facet such as genre, franchise, or company',
820:'onboarding prompt to choose one starting path and return later for other pieces',
821:'collections-page action for planning a set against a DAT and library',
822:'in-progress status for the planning operation',
823:'platform field used for game metadata and export formats',
824:'settings label for folder-name mappings to ROM platforms',
}

def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(name,o): (OUT/name).write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def need(ok,msg):
    if not ok: raise SystemExit('REFUSED: '+msg)

def checksums(root, checksum_file):
    listed={}
    for line in checksum_file.read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        need(n not in listed and (root/n).is_file() and sha((root/n).read_bytes())==h,'input checksum '+n)
        listed[n]=h
    actual={x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file() and x.relative_to(root)!=checksum_file.relative_to(root)}
    need(actual==set(listed),'input checksum inventory '+str(root))
    return listed

def token_audit(source,target,protected):
    ph=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    sp,tp=ph(source),ph(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target)
    protected=list(protected or [])
    return {'placeholders':{'source':sorted(sp.elements()),'target':sorted(tp.elements()),'matches':sp==tp},
      'markup':{'source':sorted(st.elements()),'target':sorted(tt.elements()),'matches':st==tt},
      'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      'protectedLiterals':{'source':protected,'missing':[x for x in protected if x not in target]}}

def main():
    need({p.name for p in OUT.iterdir()}=={'build_blind_review.py','verify_blind_review.py'},'output directory is not pristine')
    outer=checksums(PACKET,PACKET/'SHA256SUMS.txt')
    need(sha((PACKET/'SHA256SUMS.txt').read_bytes())==OUTER_SUMS_SHA,'outer packet checksum-list digest')
    ins=checksums(INPUT,INPUT/'SHA256SUMS.txt')
    prevs=checksums(PREDECESSOR,PREDECESSOR/'SHA256SUMS.txt')
    manifest=readj(INPUT/'manifest.json')
    need((manifest.get('head'),manifest.get('tree'),manifest.get('window'),manifest.get('cellCount'),manifest.get('sourceCount'),manifest.get('callerBackedCells'),manifest.get('callerlessHashOnlyCells'),manifest.get('priorActiveHashOnlyHoldsReattested'),manifest.get('resultingActiveHashOnlyHolds'),manifest.get('reviewDecisionsIncluded'),manifest.get('proposedTargetsIncluded'))==(HEAD,TREE,'W805-W824',240,20,240,0,1060,1060,False,False),'candidate-free manifest pin')
    selection=readj(INPUT/'selection.json'); sources=selection['selectedSources']
    cells=readjl(INPUT/'candidate-free-cells.jsonl'); contexts=readjl(INPUT/'source-contexts.jsonl')
    need(len(sources)==20 and len(cells)==240 and len(contexts)==20,'candidate-free coverage')
    ctx={r['sourceId']:r for r in contexts}; ledger=[]; counts=collections.Counter()
    for cell in cells:
        pos=cell['position']; loc=cell['locale']; sid=cell['sourceId']; source=cell['source']; current=cell['currentTarget']
        need(pos in POSITIONS and cell['window']=='W805-W824' and cell['candidateFree'] is True and cell['callerless'] is False,'cell identity/candidate-free marker')
        need(tsha(source)==cell['sourceSha256'] and tsha(current)==cell['currentTargetSha256'],'source/current hash '+sid+' '+loc)
        context=ctx[sid]
        need(context['source']==source and context['sourceSha256']==cell['sourceSha256'] and context['head']==HEAD,'caller source pin '+sid)
        need(cell['callerContextSha256']==context['contextSha256'] and context['exactMatchCount']>0,'caller context hash '+sid)
        override=REVISIONS.get((pos,loc)); proposed,rationale=(override[0],override[1]) if override else (current,'Current wording correctly conveys '+NOTES[pos]+' in this caller context; retain it.')
        decision='revise' if override else 'accept-current'
        audit=token_audit(source,proposed,cell.get('sourceProtectedLiterals',[]))
        need(audit['placeholders']['matches'] and audit['markup']['matches'] and audit['numbers']['sourcePreserved'] and not audit['protectedLiterals']['missing'],'proposal token failure '+sid+' '+loc)
        refs=[{'path':r['path'],'line':r['line'],'matchKind':r['matchKind'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob'],
          'lineSha256':r['lineSha256'],'excerptSha256':r['excerptSha256']} for r in context['callers']]
        row={'window':'W805-W824','head':HEAD,'tree':TREE,'position':pos,'catalogZeroBasedIndex':cell['catalogZeroBasedIndex'],
          'catalogOneBasedPosition':cell['catalogOneBasedPosition'],'sourceId':sid,'sourceSha256':cell['sourceSha256'],
          'locale':loc,'source':source,'currentTarget':current,'currentTargetSha256':cell['currentTargetSha256'],
          'callerCount':context['exactMatchCount'],'callerContextSha256':context['contextSha256'],'callerReferences':refs,
          'decision':decision,'proposedTarget':proposed,'proposedTargetSha256':tsha(proposed),'rationale':rationale,
          'confidence':'low' if pos in (805,806,807,814,820,821) else 'moderate',
          'issueFlags':['terminology'] if override else [],'candidateFreeCurrentTokenFlags':{
            'placeholderMultisetMatches':cell['placeholderMultisetMatches'],'markupMatches':cell['markupMatches'],
            'numericTokensPreserved':cell['numericTokensPreserved'],'numericPresentationEquivalent':cell['numericPresentationEquivalent'],
            'protectedLiteralsPreserved':cell['protectedLiteralsPreserved'],'missingProtectedLiterals':cell['missingProtectedLiterals']},
          'proposedTokenAudit':audit,'proposedTokenAuditSha256':sha(canon(audit)),'tokenChecksPass':True}
        ledger.append(row); counts[decision]+=1
    need(len(ledger)==240,'ledger cell count')
    prior=PREDECESSOR/'prior-active-holds-hash-only.jsonl'; previous=PREDECESSOR/'w785-current-window-holds-hash-only.jsonl'
    prior_rows=readjl(prior); previous_rows=readjl(previous)
    need(len(prior_rows)==1012 and len(previous_rows)==48,'predecessor hold count')
    need(not any(any(k in row for k in ('source','sourceText','target','currentTarget','proposedTarget','before','after')) for row in prior_rows+previous_rows),'predecessor hold text disclosure')
    provenance=readj(PREDECESSOR/'active-hold-provenance.json')
    need(provenance.get('activeHoldCount')==1060 and provenance.get('uniqueCells')==1060 and provenance.get('hashOnly') is True,'predecessor hold provenance')
    shutil.copyfile(prior,OUT/'prior-active-holds-hash-only.jsonl')
    shutil.copyfile(previous,OUT/'w785-current-window-holds-hash-only.jsonl')
    writejl('blind-review-ledger.jsonl',ledger)
    boundary=manifest['nextBoundary']
    writej('input-attestation.json',{'candidateFreePacketPath':str(PACKET),'head':HEAD,'tree':TREE,'window':'W805-W824',
      'outerChecksumListSha256':sha((PACKET/'SHA256SUMS.txt').read_bytes()),'outerChecksummedFileCount':len(outer),
      'inputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'inputChecksummedFileCount':len(ins),
      'predecessorChecksumListSha256':sha((PREDECESSOR/'SHA256SUMS.txt').read_bytes()),'predecessorChecksummedFileCount':len(prevs),
      'inputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),'candidateFreeCellFileSha256':sha((INPUT/'candidate-free-cells.jsonl').read_bytes()),
      'callerContextFileSha256':sha((INPUT/'source-contexts.jsonl').read_bytes()),'noOtherReviewOutputsConsulted':True})
    summary={'result':'PASS','artifact':'ROMarrNG PR #70 W805-W824 independent blind semantic review',
      'window':'W805-W824','head':HEAD,'tree':TREE,'catalogZeroBasedIndexRange':[805,824],
      'catalogOneBasedPositionRange':[806,825],'sourceCount':20,'localeCount':12,'cellCount':240,
      'callerBackedCells':240,'revisedCells':counts['revise'],'acceptedCurrentCells':counts['accept-current'],
      'newCallerlessHolds':0,'priorActiveHashOnlyHoldsCopiedAndReattested':1060,'resultingActiveHashOnlyHolds':1060,
      'confidenceCounts':dict(collections.Counter(r['confidence'] for r in ledger)),
      'issueFlagCellCount':sum(bool(r['issueFlags']) for r in ledger),'allTokenChecksPass':True,
      'nativeSpeakerApproval':False,'nextBoundary':boundary,'repositoryEdited':False,'testsBuildsCiRun':False}
    writej('summary.json',summary)
    (OUT/'README.md').write_text('# ROMarrNG PR #70 W805–W824 independent blind semantic review\n\n'
      'This review uses only the sealed candidate-free packet at `/mnt/disks/scratch/task-scratch/romarrng-pr70-w805-824-candidate-free-20261105/`, pinned to head '+HEAD+' / tree '+TREE+'. It covers 240 caller-backed cells (20 sources × 12 locales), with '+str(counts['revise'])+' revisions and '+str(counts['accept-current'])+' accepted-current values.\n\n'
      'The 1,060 predecessor hash-only holds are copied byte-for-byte and retained. Proposed target hashes, caller-context references, issue flags, confidence, and placeholder/markup/number/protected-literal checks are recorded per cell. This machine review is not native-speaker approval. No product files were changed.\n\n'
      'Next boundary: index 825 / position 826, `ui.platform-for-game-available-platform.afd580990f`, source SHA-256 `afd580990fe9a12282ffeeeefa2d1a2c8b632f05bdd58b08e3c03a27ac91fb08`.\n',encoding='utf-8')
    files=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'})
    output_manifest={'schemaVersion':1,'repository':'snapetech-org/ROMarrNG','pullRequest':70,'role':'independent-blind-semantic-review',
      'window':'W805-W824','head':HEAD,'tree':TREE,'candidateFreeOuterChecksumListSha256':sha((PACKET/'SHA256SUMS.txt').read_bytes()),
      'catalogZeroBasedIndexRange':[805,824],'catalogOneBasedPositionRange':[806,825],'sourceCount':20,'localeCount':12,
      'cellCount':240,'callerBackedCells':240,'revisedCells':counts['revise'],'acceptedCurrentCells':counts['accept-current'],
      'newCallerlessHolds':0,'priorActiveHashOnlyHolds':1060,'resultingActiveHashOnlyHolds':1060,
      'nativeSpeakerApproval':False,'files':[{'path':n,'sha256':sha((OUT/n).read_bytes()),'bytes':(OUT/n).stat().st_size} for n in files]}
    writej('manifest.json',output_manifest)
    names=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(sha((OUT/n).read_bytes())+'  '+n+'\n' for n in names),encoding='utf-8')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),'revised':counts['revise'],
      'acceptedCurrent':counts['accept-current'],'priorHolds':1060,'activeHoldsAfter':1060,'nextBoundary':boundary,
      'checksummedFiles':len(names)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
